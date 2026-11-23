import os
from typing import Callable, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.config.logger import logger
from app.config.settings import settings
from app.schemas.triagem import (
    RequisicaoTriagem,
    RespostaTriagem,
    ClassificacaoDocumento,
    DadosExtraidos,
    Paciente,
    MedicoSolicitante,
    DecisaoRoteamento,
    NotificacaoAlerta,
    ArmazenamentoOCI,
    DecisaoAuditoriaRequest,
)
from app.models.triagem import DocumentoTriagemModel
from app.repositories.database import DatabaseRepository
from app.repositories.storage import StorageRepository
from app.services.auditoria_outbox import enfileirar_evento
from app.services.evolution_service import EvolutionService
from app.services.redis_service import RedisAuditService
from app.agent.graph import (
    excluir_checkpoint_triagem,
    executar_agente_triagem,
    retomar_agente_triagem,
)


class TriagemService:
    """Orquestrador do fluxo completo de triagem clínica (API -> LangGraph -> Banco -> OCI)."""

    def __init__(self, db: Session):
        self.db_repo = DatabaseRepository(db)
        self.storage_repo = StorageRepository()
        self.redis_service = RedisAuditService()

    def processar_triagem(
        self,
        requisicao: RequisicaoTriagem,
        referencia_fonte: Optional[str] = None,
        avaliacao_escopo: Optional[Dict[str, Any]] = None,
        metadados_documento: Optional[Dict[str, Any]] = None,
        campos_rotulados: Optional[list[Dict[str, str]]] = None,
        on_etapa: Optional[Callable[[str], None]] = None,
    ) -> RespostaTriagem:
        if self.db_repo.buscar_por_documento_id(requisicao.documento_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma triagem com esse identificador.",
            )
        self.db_repo.db.rollback()

        # 1. Execução do Agente Autônomo LangGraph (StateGraph)
        estado_inicial = {
            "documento_id": requisicao.documento_id,
            "tipo_arquivo": requisicao.tipo_arquivo,
            "canal_origem": requisicao.canal_origem,
            "documento_texto": requisicao.documento_texto,
            "referencia_fonte": referencia_fonte or (
                "texto_informado"
                if requisicao.tipo_arquivo.lower() in {"texto", "json"}
                else None
            ),
            "avaliacao_escopo": avaliacao_escopo,
        }
        resultado_grafo = executar_agente_triagem(
            estado_inicial,
            resolver_cadastro=self._resolver_cadastro_identificacao,
            on_etapa=on_etapa,
        )

        if resultado_grafo.get("status") in {"recusado", "comprovacao_solicitada"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=resultado_grafo.get("mensagem_usuario", "Documento fora do escopo médico."),
            )

        execucao_pausada = bool(resultado_grafo.get("__interrupt__"))

        # 2. Extração dos resultados estruturados do grafo
        tipo_documento = resultado_grafo.get("tipo_documento") or "Não classificado"
        especialidade = resultado_grafo.get("especialidade") or "Clínica Geral"
        nivel_prioridade = resultado_grafo.get("nivel_prioridade") or "Rotina"
        score_confianca = float(resultado_grafo.get("score_confianca_classificacao") or 0.0)
        is_urgente = bool(resultado_grafo.get("is_urgente", False))
        requer_auditoria = execucao_pausada or bool(resultado_grafo.get("requer_auditoria_humana", False))
        eh_medico_ilegivel = (
            (avaliacao_escopo or {}).get("escopo") == "medico"
            and (avaliacao_escopo or {}).get("legibilidade") != "legivel"
        ) or (
            (avaliacao_escopo or {}).get("legibilidade") == "ilegivel"
        )
        if eh_medico_ilegivel:
            requer_auditoria = True
            destino_principal = "Auditoria_Humana"
            justificativa = "Documento médico com caligrafia ilegível — requer transcrição por auditor humano"
        else:
            destino_principal = resultado_grafo.get("destino_principal") or (
                "Auditoria_Humana" if requer_auditoria else "Fluxo_Padrao"
            )
            justificativa = (
                resultado_grafo.get("justificativa_roteamento")
                or resultado_grafo.get("motivo_revisao")
                or "Processamento concluído."
            )

        # Dados clínicos extraídos pelo grafo
        paciente_dict = resultado_grafo.get("paciente") or {}
        medico_dict = resultado_grafo.get("medico_solicitante") or {}

        # 3. Modelagem dos Contratos Pydantic
        classificacao = ClassificacaoDocumento(
            tipo_documento=tipo_documento,
            especialidade=especialidade,
            nivel_prioridade=nivel_prioridade,
            score_confianca_classificacao=score_confianca,
        )

        dados_extraidos = DadosExtraidos(
            paciente=Paciente(
                nome=paciente_dict.get("nome"),
                cpf=paciente_dict.get("cpf"),
                idade=paciente_dict.get("idade"),
                data_nascimento=paciente_dict.get("data_nascimento"),
            ),
            medico_solicitante=MedicoSolicitante(
                nome=medico_dict.get("nome"),
                crm=medico_dict.get("crm"),
            ),
            exame_realizado=resultado_grafo.get("exame_realizado"),
            diagnostico_principal=resultado_grafo.get("diagnostico_principal"),
            cid_sugerido=resultado_grafo.get("cid_sugerido"),
            medicamentos=resultado_grafo.get("medicamentos") or [],
        )

        notificacao_dict = resultado_grafo.get("notificacao_gerada")
        notificacao_obj = (
            NotificacaoAlerta(
                canal=notificacao_dict.get("canal", "Alerta_Plantao_Medico"),
                mensagem=notificacao_dict.get("mensagem", "Alerta clínico urgente gerado."),
            )
            if notificacao_dict
            else None
        )

        decisao_roteamento = DecisaoRoteamento(
            destino_principal=destino_principal,
            requer_auditoria_humana=requer_auditoria,
            justificativa_roteamento=justificativa,
            notificacao_gerada=notificacao_obj,
        )

        resultado_oci = None
        try:
            # Persiste o JSON antes do commit SQL; em falha relacional, remove o artefato criado.
            resultado_oci = self.storage_repo.salvar_triagem_json(
                documento_id=requisicao.documento_id,
                dados_resultado={
                    "status": "processado" if not requer_auditoria else "em_auditoria",
                    "documento_id": requisicao.documento_id,
                    "classificacao": classificacao.model_dump(),
                    "dados_extraidos": dados_extraidos.model_dump(),
                    "decisao_roteamento": decisao_roteamento.model_dump(),
                },
                is_urgente=is_urgente,
                requer_auditoria=requer_auditoria,
            )
            armazenamento_oci = ArmazenamentoOCI(**resultado_oci)

            model = DocumentoTriagemModel(
                documento_id=requisicao.documento_id,
                tipo_arquivo=requisicao.tipo_arquivo,
                canal_origem=requisicao.canal_origem,
                documento_texto=requisicao.documento_texto,
                paciente_id=(resultado_grafo.get("identificacao_cadastral") or {})
                .get("paciente", {})
                .get("registro_id"),
                medico_id=(resultado_grafo.get("identificacao_cadastral") or {})
                .get("medico_solicitante", {})
                .get("registro_id"),
                tipo_documento=classificacao.tipo_documento,
                especialidade=classificacao.especialidade,
                nivel_prioridade=classificacao.nivel_prioridade,
                score_confianca=classificacao.score_confianca_classificacao,
                destino_principal=destino_principal,
                requer_auditoria_humana=requer_auditoria,
                status_processamento="EM_REVISAO_HUMANA" if requer_auditoria else "processado",
                justificativa_roteamento=justificativa,
                dados_extraidos=dados_extraidos.model_dump(),
                bucket_oci=armazenamento_oci.bucket,
                caminho_objeto_oci=armazenamento_oci.caminho_objeto,
                evidencias_campos=resultado_grafo.get("evidencias_campos"),
                metadados_documento=metadados_documento,
                campos_rotulados=campos_rotulados,
                escopo_documento=(avaliacao_escopo or {}).get("escopo"),
                legibilidade_documento=(avaliacao_escopo or {}).get("legibilidade"),
                evidencias_escopo=(avaliacao_escopo or {}).get("evidencias"),
                justificativa_escopo=(avaliacao_escopo or {}).get("justificativa"),
                motivo_revisao=(
                    "Documento médico com caligrafia ilegível — requer transcrição por auditor humano"
                    if eh_medico_ilegivel
                    else (resultado_grafo.get("motivo_revisao") or justificativa if requer_auditoria else None)
                ),
                etapa_revisao=resultado_grafo.get("etapa_revisao"),
                caminho_fonte=(referencia_fonte if referencia_fonte != "texto_informado" else None),
                whatsapp_numero=requisicao.whatsapp_numero,
                whatsapp_nome=requisicao.whatsapp_nome,
                whatsapp_message_id=requisicao.whatsapp_message_id,
            )
            self.db_repo.salvar(model)
            resposta_triagem = RespostaTriagem(
                status="processado" if not requer_auditoria else "em_auditoria",
                documento_id=requisicao.documento_id,
                classificacao=classificacao,
                dados_extraidos=dados_extraidos,
                decisao_roteamento=decisao_roteamento,
                armazenamento_oci=armazenamento_oci,
                evidencias_campos=resultado_grafo.get("evidencias_campos"),
                motivo_revisao=justificativa if requer_auditoria else None,
                faixa_motor_regras=resultado_grafo.get("faixa_motor_regras"),
                score_detalhes=resultado_grafo.get("score_detalhes"),
            )
            self.db_repo.db.commit()
        except Exception:
            self.db_repo.db.rollback()
            if resultado_oci:
                self.storage_repo.rollback_tentativa(
                    caminho_json_local=resultado_oci.get("caminho_local"),
                    objetos_oci=[resultado_oci.get("caminho_objeto")],
                )
            try:
                excluir_checkpoint_triagem(requisicao.documento_id)
            except Exception:
                logger.exception("Falha ao limpar checkpoint após persistência incompleta: %s", requisicao.documento_id)
            raise

        # O evento auditável já está no outbox, dentro da mesma transação PostgreSQL.
        try:
            self.redis_service.publicar_evento(
                "mediflow:auditoria:eventos",
                {
                    "tipo": "TRIAGEM_PROCESSADA",
                    "documento_id": requisicao.documento_id,
                    "requer_auditoria": requer_auditoria,
                    "prioridade": classificacao.nivel_prioridade,
                },
            )
        except Exception:
            pass

        return resposta_triagem

    def _resolver_cadastro_identificacao(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Consulta cadastros por identificadores exatos e nunca cria registros nesta etapa."""
        identificacao = state.get("identificacao_documento") or {}
        paciente_documento = identificacao.get("paciente") or {}
        medico_documento = identificacao.get("medico_solicitante") or {}

        nome_paciente = (paciente_documento.get("nome") or "").strip()
        idade_paciente = paciente_documento.get("idade")
        candidatos_paciente = (
            self.db_repo.buscar_pacientes_por_nome(nome_paciente) if nome_paciente else []
        )
        if not nome_paciente:
            paciente_cadastro = {"status": "dados_insuficientes"}
        elif len(candidatos_paciente) == 1:
            paciente = candidatos_paciente[0]
            paciente_cadastro = {
                "status": "encontrado",
                "registro_id": paciente.id,
                "cadastro": {
                    "nome": paciente.nome,
                    "idade": paciente.idade,
                    "data_nascimento": paciente.data_nascimento.isoformat() if paciente.data_nascimento else None,
                    "cadastro_provisorio": paciente.cadastro_provisorio,
                },
            }
        elif len(candidatos_paciente) > 1:
            paciente_cadastro = {"status": "ambiguo", "candidatos": len(candidatos_paciente)}
        else:
            paciente_cadastro = {"status": "nao_encontrado"}
        cpf_paciente = paciente_documento.get("cpf")
        paciente_cadastro.update({"dados_documento": {
            "nome": nome_paciente or None,
            "cpf": cpf_paciente,
            "idade": idade_paciente,
        }})

        nome_medico = (medico_documento.get("nome") or "").strip()
        crm_medico = (medico_documento.get("crm") or "").strip().upper()
        if not crm_medico:
            medico_cadastro = {"status": "crm_ausente"}
        else:
            medico = self.db_repo.buscar_medico_por_crm(crm_medico)
            medico_cadastro = (
                {
                    "status": "encontrado",
                    "registro_id": medico.id,
                    "cadastro": {
                        "nome": medico.nome,
                        "crm": medico.crm,
                        "especialidade": medico.especialidade,
                        "uf": medico.uf,
                    },
                }
                if medico
                else {"status": "nao_encontrado"}
            )
        medico_cadastro["dados_documento"] = {
            "nome": nome_medico or None,
            "crm": crm_medico or None,
        }

        return {
            "identificacao_cadastral": {
                "paciente": paciente_cadastro,
                "medico_solicitante": medico_cadastro,
            }
        }

    def registrar_decisao_medica(
        self, documento_id: str, payload: DecisaoAuditoriaRequest, revisor_id: int | None = None
    ):
        """Aprova, corrige ou rejeita um item na fila de Human-in-the-Loop."""
        dados_corrigidos = (
            payload.dados_corrigidos.model_dump()
            if payload.dados_corrigidos is not None
            else None
        )
        doc_original = self.db_repo.buscar_por_documento_id(documento_id)
        if not doc_original:
            return None
        raw_wpp = getattr(doc_original, "whatsapp_numero", None)
        whatsapp_numero = raw_wpp if isinstance(raw_wpp, str) and raw_wpp.strip() else None
        try:
            resultado_grafo = retomar_agente_triagem(
                documento_id,
                payload.model_dump(exclude_none=True),
            )
        except Exception as erro:
            logger.warning(
                "Não foi possível retomar checkpoint do grafo para %s (%s). Aplicando decisão diretamente no banco.",
                documento_id,
                erro,
            )
            resultado_grafo = {
                "status": "rejeitado" if payload.status_aprovacao == "rejeitado" else "aguardando_reenvio" if payload.status_aprovacao == "solicitar_reenvio" else "roteado",
                "dados_extraidos": dados_corrigidos or getattr(doc_original, "dados_extraidos", {}),
                "destino_principal": getattr(doc_original, "destino_principal", None) or "FLUXO_PADRAO",
            }

        interrompido_novamente = bool(resultado_grafo.get("__interrupt__"))
        if interrompido_novamente:
            novo_status = "EM_REVISAO_HUMANA"
        elif resultado_grafo.get("status") == "aguardando_reenvio":
            novo_status = "AGUARDANDO_REENVIO"
        elif resultado_grafo.get("status") == "rejeitado":
            novo_status = "REJEITADO"
        else:
            novo_status = "ROTEADO"

        doc_id_val = getattr(doc_original, "id", None)
        if doc_id_val is not None and hasattr(self.db_repo, "db") and hasattr(self.db_repo.db, "query"):
            try:
                linhas = (
                    self.db_repo.db.query(DocumentoTriagemModel)
                    .filter(
                        DocumentoTriagemModel.id == doc_id_val,
                        DocumentoTriagemModel.status_processamento == "EM_REVISAO_HUMANA",
                        DocumentoTriagemModel.versao == payload.versao,
                    )
                    .update(
                        {
                            DocumentoTriagemModel.status_processamento: novo_status,
                            DocumentoTriagemModel.versao: DocumentoTriagemModel.versao + 1,
                            DocumentoTriagemModel.ultima_sequencia: DocumentoTriagemModel.ultima_sequencia + 1,
                        },
                        synchronize_session=False,
                    )
                )
                if isinstance(linhas, int) and linhas != 1:
                    self.db_repo.db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="O documento mudou desde que foi aberto. Recarregue a revisão antes de decidir.",
                    )
                self.db_repo.db.refresh(doc_original)
            except HTTPException:
                raise
            except Exception:
                pass

        if resultado_grafo.get("status") == "recusado":
            caminho_fonte = doc_original.caminho_fonte
            caminho_objeto = doc_original.caminho_objeto_oci
            caminhos_objetos_fonte = []
            if caminho_fonte:
                extensao_fonte = os.path.splitext(caminho_fonte)[1]
                caminhos_objetos_fonte = [
                    self.storage_repo.gerar_caminho_objeto_original(
                        documento_id,
                        extensao_fonte,
                    ),
                    # Compatibilidade com originais salvos antes da separação por tipo.
                    f"recebidos/{documento_id}{extensao_fonte}",
                ]
            extra_kwargs = {"revisor_id": revisor_id} if revisor_id is not None else {}
            self.db_repo.registrar_decisao(
                documento_id=documento_id,
                decisao=payload.status_aprovacao,
                auditor_nome=payload.auditor_nome,
                justificativa=payload.justificativa,
                dados_corrigidos=None,
                **extra_kwargs,
            )
            enfileirar_evento(
                self.db_repo.db,
                documento=doc_original,
                tipo_evento=f"DECISAO_MEDICA_{payload.status_aprovacao.upper()}",
                autor=payload.auditor_nome,
                payload={"status_processamento": "REJEITADO", "motivo": "documento fora do escopo"},
                justificativa=payload.justificativa,
                incrementar_versao=False,
                incrementar_sequencia=False,
            )
            self.db_repo.excluir_documento_e_auditoria(documento_id)
            self.db_repo.db.commit()
            self.storage_repo.excluir_artefatos_triagem(
                documento_id,
                caminho_fonte=caminho_fonte,
                caminho_objeto=caminho_objeto,
                caminhos_objetos=caminhos_objetos_fonte,
            )
            excluir_checkpoint_triagem(documento_id)
            self.redis_service.liberar_lock(documento_id, payload.auditor_nome)
            if whatsapp_numero:
                EvolutionService().enviar_resposta_sincrona(
                    whatsapp_numero,
                    EvolutionService.formatar_mensagem_erro(
                        "A revisão confirmou que o documento enviado não é médico. O protocolo foi encerrado."
                    ),
                )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A revisão confirmou que o documento não é médico. O processamento foi recusado e os dados transitórios foram removidos.",
            )

        resultado_oci = None
        try:
            extra_kwargs = {"revisor_id": revisor_id} if revisor_id is not None else {}
            doc_atualizado = self.db_repo.registrar_decisao(
                documento_id=documento_id,
                decisao=payload.status_aprovacao,
                auditor_nome=payload.auditor_nome,
                justificativa=payload.justificativa,
                dados_corrigidos=dados_corrigidos,
                **extra_kwargs,
            )

            if doc_atualizado:
                if interrompido_novamente:
                    doc_atualizado.status_processamento = "em_auditoria"
                    doc_atualizado.requer_auditoria_humana = True
                    doc_atualizado.motivo_revisao = resultado_grafo.get("motivo_revisao") or payload.justificativa
                    doc_atualizado.etapa_revisao = resultado_grafo.get("etapa_revisao")
                    doc_atualizado.evidencias_campos = resultado_grafo.get("evidencias_campos")
                else:
                    doc_atualizado.status_processamento = (
                        "aguardando_reenvio"
                        if resultado_grafo.get("status") == "aguardando_reenvio"
                        else "auditoria_rejeitado"
                        if resultado_grafo.get("status") == "rejeitado"
                        else "processado"
                    )
                    doc_atualizado.requer_auditoria_humana = False
                    doc_atualizado.tipo_documento = resultado_grafo.get("tipo_documento") or doc_atualizado.tipo_documento
                    doc_atualizado.especialidade = resultado_grafo.get("especialidade") or doc_atualizado.especialidade
                    doc_atualizado.nivel_prioridade = resultado_grafo.get("nivel_prioridade") or doc_atualizado.nivel_prioridade
                    doc_atualizado.score_confianca = resultado_grafo.get("score_confianca_classificacao") or doc_atualizado.score_confianca
                    
                    # Decisão do revisor humano tem prevalência máxima
                    if payload.destino_principal:
                        doc_atualizado.destino_principal = payload.destino_principal
                    elif payload.fila_encaminhamento == "Rotina":
                        doc_atualizado.destino_principal = "Fluxo_Padrao"
                    elif payload.fila_encaminhamento == "Urgente":
                        doc_atualizado.destino_principal = "Fila_Emergencia_Medica"
                    else:
                        doc_atualizado.destino_principal = resultado_grafo.get("destino_principal") or doc_atualizado.destino_principal or "FLUXO_PADRAO"

                    if payload.nivel_prioridade:
                        doc_atualizado.nivel_prioridade = payload.nivel_prioridade
                    elif payload.fila_encaminhamento == "Rotina":
                        doc_atualizado.nivel_prioridade = "ROTINA"
                    elif payload.fila_encaminhamento == "Urgente":
                        doc_atualizado.nivel_prioridade = "URGENTE"
                    else:
                        doc_atualizado.nivel_prioridade = resultado_grafo.get("nivel_prioridade") or doc_atualizado.nivel_prioridade

                    self.db_repo.vincular_destino(doc_atualizado)
                    doc_atualizado.justificativa_roteamento = payload.justificativa or resultado_grafo.get("justificativa_roteamento") or "Revisão humana concluída."
                    if resultado_grafo.get("dados_extraidos"):
                        doc_atualizado.dados_extraidos = resultado_grafo["dados_extraidos"]
                    doc_atualizado.motivo_revisao = None
                    doc_atualizado.etapa_revisao = None
                    doc_atualizado.evidencias_campos = resultado_grafo.get("evidencias_campos")

                    if resultado_grafo.get("status") == "roteado":
                        eh_urgente_final = bool(resultado_grafo.get("is_urgente"))
                        if doc_atualizado.destino_principal != "Fila_Emergencia_Medica" and doc_atualizado.nivel_prioridade != "EMERGENCIA":
                            eh_urgente_final = False

                        resultado_oci = self.storage_repo.salvar_triagem_json(
                            documento_id=documento_id,
                            dados_resultado={
                                "status": "processado",
                                "documento_id": documento_id,
                                "classificacao": {
                                    "tipo_documento": doc_atualizado.tipo_documento,
                                    "especialidade": doc_atualizado.especialidade,
                                    "nivel_prioridade": doc_atualizado.nivel_prioridade,
                                    "score_confianca_classificacao": doc_atualizado.score_confianca,
                                },
                                "dados_extraidos": doc_atualizado.dados_extraidos,
                                "decisao_roteamento": {
                                    "destino_principal": doc_atualizado.destino_principal,
                                    "requer_auditoria_humana": False,
                                    "justificativa_roteamento": doc_atualizado.justificativa_roteamento,
                                    "notificacao_gerada": None,
                                },
                            },
                            is_urgente=eh_urgente_final,
                            requer_auditoria=False,
                        )
                        doc_atualizado.bucket_oci = resultado_oci["bucket"]
                        doc_atualizado.caminho_objeto_oci = resultado_oci["caminho_objeto"]

                enfileirar_evento(
                    self.db_repo.db,
                    documento=doc_atualizado,
                    tipo_evento=f"DECISAO_MEDICA_{payload.status_aprovacao.upper()}",
                    autor=payload.auditor_nome,
                    payload={
                        "status_processamento": doc_atualizado.status_processamento,
                        "dados_extraidos": doc_atualizado.dados_extraidos or {},
                        "versao": getattr(doc_atualizado, "versao", 1),
                    },
                    justificativa=payload.justificativa,
                    incrementar_versao=False,
                    incrementar_sequencia=False,
                )
                self.db_repo.db.flush()
                if hasattr(doc_atualizado, "id"):
                    self.db_repo.db.refresh(doc_atualizado)
                self.db_repo.db.commit()
        except Exception:
            self.db_repo.db.rollback()
            if resultado_oci:
                self.storage_repo.rollback_tentativa(
                    caminho_json_local=resultado_oci.get("caminho_local"),
                    objetos_oci=[resultado_oci.get("caminho_objeto")],
                )
            raise

        if doc_atualizado:
            try:
                # Libera lock no Redis
                self.redis_service.liberar_lock(documento_id, payload.auditor_nome)
                if hasattr(self, "nosql_repo") and self.nosql_repo:
                    self.nosql_repo.gravar_evento(
                        documento_id=documento_id,
                        tipo_evento=f"DECISAO_MEDICA_{payload.status_aprovacao.upper()}",
                        autor=payload.auditor_nome,
                        payload=dados_corrigidos or {},
                        justificativa=payload.justificativa,
                    )
            except Exception:
                logger.exception("Falha ao registrar evento após decisão de auditoria: %s", documento_id)

            # Disparo ativo para o WhatsApp de origem quando a revisão humana é concluída
            raw_num = getattr(doc_atualizado, "whatsapp_numero", None)
            numero_wpp = (raw_num if isinstance(raw_num, str) and raw_num.strip() else None) or whatsapp_numero
            if numero_wpp and not bool(getattr(doc_atualizado, "requer_auditoria_humana", False) is True):
                try:
                    mensagem_wpp = EvolutionService.formatar_notificacao_pos_auditoria(
                        doc_atualizado,
                        status_aprovacao=payload.status_aprovacao,
                        justificativa=payload.justificativa,
                    )
                    EvolutionService().enviar_resposta_sincrona(numero_wpp, mensagem_wpp)
                except Exception:
                    logger.exception("Falha ao notificar WhatsApp após decisão médica: %s", documento_id)

        return doc_atualizado
