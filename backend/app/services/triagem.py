from typing import Optional, Dict, Any
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
from app.agent.graph import executar_agente_triagem


class TriagemService:
    """Orquestrador do fluxo completo de triagem clínica (API -> LangGraph -> Banco -> OCI)."""

    def __init__(self, db: Session):
        self.db_repo = DatabaseRepository(db)
        self.storage_repo = StorageRepository()

    def processar_triagem(self, requisicao: RequisicaoTriagem) -> RespostaTriagem:
        # 1. Execução do Agente Autônomo LangGraph (StateGraph)
        estado_inicial = {
            "documento_id": requisicao.documento_id,
            "tipo_arquivo": requisicao.tipo_arquivo,
            "canal_origem": requisicao.canal_origem,
            "documento_texto": requisicao.documento_texto,
        }
        resultado_grafo = executar_agente_triagem(estado_inicial)

        # 2. Extração dos resultados estruturados do grafo
        tipo_documento = resultado_grafo.get("tipo_documento") or "Documento Clínico"
        especialidade = resultado_grafo.get("especialidade") or "Clínica Geral"
        nivel_prioridade = resultado_grafo.get("nivel_prioridade") or "Rotina"
        score_confianca = float(resultado_grafo.get("score_confianca_classificacao", 0.95))
        is_urgente = bool(resultado_grafo.get("is_urgente", False))
        requer_auditoria = bool(resultado_grafo.get("requer_auditoria_humana", False))
        destino_principal = resultado_grafo.get("destino_principal") or "Fluxo_Padrao"
        justificativa = resultado_grafo.get("justificativa_roteamento") or "Processamento concluído."

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
                nome=paciente_dict.get("nome") or "Paciente Identificado",
                idade=paciente_dict.get("idade") or 45,
            ),
            medico_solicitante=MedicoSolicitante(
                nome=medico_dict.get("nome") or "Médico Solicitante",
                crm=medico_dict.get("crm") or "145892-SP",
            ),
            exame_realizado=resultado_grafo.get("exame_realizado") or "Avaliação Clínica",
            diagnostico_principal=resultado_grafo.get("diagnostico_principal") or "Avaliação Clínica",
            cid_sugerido=resultado_grafo.get("cid_sugerido") or "Z00.0",
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
        )
        self.db_repo.salvar(model)

        return RespostaTriagem(
            status="processado" if not requer_auditoria else "em_auditoria",
            documento_id=requisicao.documento_id,
            classificacao=classificacao,
            dados_extraidos=dados_extraidos,
            decisao_roteamento=decisao_roteamento,
            armazenamento_oci=armazenamento_oci,
        )

    def registrar_decisao_medica(self, documento_id: str, payload: DecisaoAuditoriaRequest):
        """Aprova, corrige ou rejeita um item na fila de Human-in-the-Loop."""
        return self.db_repo.registrar_decisao(
            documento_id=documento_id,
            decisao=payload.status_aprovacao,
            auditor_nome=payload.auditor_nome,
            justificativa=payload.justificativa,
            dados_corrigidos=payload.dados_corrigidos,
        )
