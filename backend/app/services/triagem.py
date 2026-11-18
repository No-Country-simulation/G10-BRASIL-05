from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
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
from app.repositories.nosql_auditoria import MongoAuditoriaRepository
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
        self.nosql_repo = MongoAuditoriaRepository()
        self.redis_service = RedisAuditService()

    def processar_triagem(
        self,
        requisicao: RequisicaoTriagem,
        referencia_fonte: Optional[str] = None,
    ) -> RespostaTriagem:
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
        }
        resultado_grafo = executar_agente_triagem(estado_inicial)

        if resultado_grafo.get("status") == "recusado":
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
                idade=paciente_dict.get("idade"),
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

        # 4. Persistência de Auditoria no OCI Object Storage
        resultado_oci = self.storage_repo.salvar_triagem_json(
            documento_id=requisicao.documento_id,
            dados_resultado={
                "documento_id": requisicao.documento_id,
                "classificacao": classificacao.model_dump(),
                "dados_extraidos": dados_extraidos.model_dump(),
                "decisao_roteamento": decisao_roteamento.model_dump(),
            },
            is_urgente=is_urgente,
            requer_auditoria=requer_auditoria,
        )
        armazenamento_oci = ArmazenamentoOCI(**resultado_oci)

        # 5. Persistência Relacional no PostgreSQL
        model = DocumentoTriagemModel(
            documento_id=requisicao.documento_id,
            tipo_arquivo=requisicao.tipo_arquivo,
            canal_origem=requisicao.canal_origem,
            documento_texto=requisicao.documento_texto,
            tipo_documento=classificacao.tipo_documento,
            especialidade=classificacao.especialidade,
            nivel_prioridade=classificacao.nivel_prioridade,
            score_confianca=classificacao.score_confianca_classificacao,
            destino_principal=destino_principal,
            requer_auditoria_humana=requer_auditoria,
            status_processamento="em_auditoria" if requer_auditoria else "processado",
            justificativa_roteamento=justificativa,
            dados_extraidos=dados_extraidos.model_dump(),
            bucket_oci=armazenamento_oci.bucket,
            caminho_objeto_oci=armazenamento_oci.caminho_objeto,
            evidencias_campos=resultado_grafo.get("evidencias_campos"),
            motivo_revisao=resultado_grafo.get("motivo_revisao") or justificativa if requer_auditoria else None,
            etapa_revisao=resultado_grafo.get("etapa_revisao"),
            caminho_fonte=(referencia_fonte if referencia_fonte != "texto_informado" else None),
        )
        self.db_repo.salvar(model)

        # 6. Registro NoSQL no MongoDB & Publicação de Telemetria no Redis
        try:
            self.nosql_repo.gravar_evento(
                documento_id=requisicao.documento_id,
                tipo_evento="TRIAGEM_INICIAL",
                autor="Sistema_IA",
                payload={
                    "classificacao": classificacao.model_dump(),
                    "dados_extraidos": dados_extraidos.model_dump(),
                    "decisao_roteamento": decisao_roteamento.model_dump(),
                },
                justificativa=justificativa,
            )
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

        return RespostaTriagem(
            status="processado" if not requer_auditoria else "em_auditoria",
            documento_id=requisicao.documento_id,
            classificacao=classificacao,
            dados_extraidos=dados_extraidos,
            decisao_roteamento=decisao_roteamento,
            armazenamento_oci=armazenamento_oci,
            evidencias_campos=resultado_grafo.get("evidencias_campos"),
            motivo_revisao=justificativa if requer_auditoria else None,
        )

    def registrar_decisao_medica(self, documento_id: str, payload: DecisaoAuditoriaRequest):
        """Aprova, corrige ou rejeita um item na fila de Human-in-the-Loop."""
        dados_corrigidos = (
            payload.dados_corrigidos.model_dump()
            if payload.dados_corrigidos is not None
            else None
        )
        doc_original = self.db_repo.buscar_por_documento_id(documento_id)
        if not doc_original:
            return None
        try:
            resultado_grafo = retomar_agente_triagem(
                documento_id,
                payload.model_dump(exclude_none=True),
            )
        except ValueError:
            # Um caso antigo ou um checkpoint expirado não pode avançar sem retomada verificável.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A execução pausada não está disponível para retomada. Mantenha o caso pendente e solicite reprocessamento.",
            )

        if resultado_grafo.get("status") == "recusado":
            caminho_fonte = doc_original.caminho_fonte
            caminho_objeto = doc_original.caminho_objeto_oci
            self.db_repo.excluir_documento_e_auditoria(documento_id)
            self.storage_repo.excluir_artefatos_triagem(
                documento_id,
                caminho_fonte=caminho_fonte,
                caminho_objeto=caminho_objeto,
            )
            excluir_checkpoint_triagem(documento_id)
            self.redis_service.liberar_lock(documento_id, payload.auditor_nome)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A revisão confirmou que o documento não é médico. O processamento foi recusado e os dados transitórios foram removidos.",
            )

        doc_atualizado = self.db_repo.registrar_decisao(
            documento_id=documento_id,
            decisao=payload.status_aprovacao,
            auditor_nome=payload.auditor_nome,
            justificativa=payload.justificativa,
            dados_corrigidos=dados_corrigidos,
        )

        if doc_atualizado:
            interrompido_novamente = bool(resultado_grafo.get("__interrupt__"))
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
                doc_atualizado.destino_principal = resultado_grafo.get("destino_principal") or doc_atualizado.destino_principal
                doc_atualizado.justificativa_roteamento = resultado_grafo.get("justificativa_roteamento") or payload.justificativa
                if resultado_grafo.get("dados_extraidos"):
                    doc_atualizado.dados_extraidos = resultado_grafo["dados_extraidos"]
                doc_atualizado.motivo_revisao = None
                doc_atualizado.etapa_revisao = None
                doc_atualizado.evidencias_campos = resultado_grafo.get("evidencias_campos")

                if resultado_grafo.get("status") == "roteado":
                    resultado_oci = self.storage_repo.salvar_triagem_json(
                        documento_id=documento_id,
                        dados_resultado={
                            "documento_id": documento_id,
                            "classificacao": {
                                "tipo_documento": doc_atualizado.tipo_documento,
                                "especialidade": doc_atualizado.especialidade,
                                "nivel_prioridade": doc_atualizado.nivel_prioridade,
                                "score_confianca_classificacao": doc_atualizado.score_confianca,
                            },
                            "dados_extraidos": doc_atualizado.dados_extraidos,
                            "destino_principal": doc_atualizado.destino_principal,
                            "justificativa_roteamento": doc_atualizado.justificativa_roteamento,
                        },
                        is_urgente=bool(resultado_grafo.get("is_urgente")),
                        requer_auditoria=False,
                    )
                    doc_atualizado.bucket_oci = resultado_oci["bucket"]
                    doc_atualizado.caminho_objeto_oci = resultado_oci["caminho_objeto"]
                self.db_repo.db.commit()
                self.db_repo.db.refresh(doc_atualizado)

            try:
                # Libera lock no Redis
                self.redis_service.liberar_lock(documento_id, payload.auditor_nome)

                # Grava na trilha imutável NoSQL
                self.nosql_repo.gravar_evento(
                    documento_id=documento_id,
                    tipo_evento=f"DECISAO_MEDICA_{payload.status_aprovacao.upper()}",
                    autor=payload.auditor_nome,
                    payload=dados_corrigidos or {},
                    justificativa=payload.justificativa,
                )
            except Exception:
                pass

        return doc_atualizado
