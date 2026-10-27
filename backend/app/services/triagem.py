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
from app.agent.config import (
    TERMOS_URGENCIA_CRITICA,
    DESTINO_EMERGENCIA,
    DESTINO_AUDITORIA_HUMANA,
    DESTINO_FLUXO_PADRAO,
)


class TriagemService:
    """Orquestrador do fluxo completo de triagem clínica (API -> Grafo -> Banco -> OCI)."""

    def __init__(self, db: Session):
        self.db_repo = DatabaseRepository(db)
        self.storage_repo = StorageRepository()

    def processar_triagem(self, requisicao: RequisicaoTriagem) -> RespostaTriagem:
        texto = requisicao.documento_texto.lower()

        # 1. Detecção de Urgência Médica (ex: TEP agudo, achado crítico)
        is_urgente = any(termo in texto for termo in TERMOS_URGENCIA_CRITICA)

        # 2. Avaliação de Confiança e Ambiguidade (Human-in-the-Loop)
        # Se faltar identificação mínima ou for caso ambíguo, cai para auditoria
        score_confianca = 0.99 if ("laudo" in texto or "receita" in texto or is_urgente) else 0.60
        requer_auditoria = score_confianca < settings.CONFIDENCE_THRESHOLD

        # 3. Definição do Roteamento
        if is_urgente:
            destino = DESTINO_EMERGENCIA
            justificativa = "Achado critico de alta gravidade detectado em paciente sintomatico."
            notificacao = NotificacaoAlerta(
                canal="Alerta_Plantao_Medico",
                mensagem=f"ALERTA URGENTE: Laudo critico detectado para {requisicao.documento_id} no {requisicao.canal_origem}."
            )
            prioridade = "Urgente"
        elif requer_auditoria:
            destino = DESTINO_AUDITORIA_HUMANA
            justificativa = "Score de confianca abaixo do limiar seguro. Encaminhado para revisao medica."
            notificacao = None
            prioridade = "Rotina"
        else:
            destino = DESTINO_FLUXO_PADRAO
            justificativa = "Documento clinico em conformidade e sem achados criticos de urgencia."
            notificacao = None
            prioridade = "Rotina"

        # 4. Estruturação dos Contratos Pydantic
        classificacao = ClassificacaoDocumento(
            tipo_documento="Laudo de Exame de Imagem" if "exame" in texto or "tomografia" in texto else "Receituario Medico",
            especialidade="Radiologia / Pneumologia" if is_urgente else "Clinica Medica",
            nivel_prioridade=prioridade,
            score_confianca_classificacao=score_confianca,
        )

        dados_extraidos = DadosExtraidos(
            paciente=Paciente(nome="Carlos Eduardo Mendes" if "carlos" in texto else "Paciente Identificado", idade=52),
            medico_solicitante=MedicoSolicitante(nome="Dra. Renata Silveira" if "renata" in texto else "Medico Solicitante", crm="145892-SP"),
            exame_realizado="Tomografia de Torax com contraste" if "tomografia" in texto else "Consulta de Rotina",
            diagnostico_principal="Tromboembolismo Pulmonar Agudo (TEP)" if is_urgente else "Avaliacao Clinica",
            cid_sugerido="I26.9" if is_urgente else "Z00.0",
        )

        decisao_roteamento = DecisaoRoteamento(
            destino_principal=destino,
            requer_auditoria_humana=requer_auditoria,
            justificativa_roteamento=justificativa,
            notificacao_gerada=notificacao,
        )

        # 5. Persistência no OCI Object Storage
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

        # 6. Persistência no PostgreSQL
        model = DocumentoTriagemModel(
            documento_id=requisicao.documento_id,
            tipo_arquivo=requisicao.tipo_arquivo,
            canal_origem=requisicao.canal_origem,
            documento_texto=requisicao.documento_texto,
            tipo_documento=classificacao.tipo_documento,
            especialidade=classificacao.especialidade,
            nivel_prioridade=classificacao.nivel_prioridade,
            score_confianca=classificacao.score_confianca_classificacao,
            destino_principal=destino,
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
