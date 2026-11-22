from typing import Dict, Any, Optional
from app.agent.state import GraphState
from app.agent.config import (
    DESTINO_EMERGENCIA,
    DESTINO_AUDITORIA_HUMANA,
    DESTINO_FLUXO_PADRAO,
    DESTINO_FARMACIA,
    DESTINO_AUTORIZACOES,
    DESTINO_ATESTADOS,
    DESTINO_EXAMES,
    DESTINO_ATENDIMENTO_GERAL,
)
from app.schemas.classificacao import TipoDocumento


def node_roteamento(state: GraphState) -> GraphState:
    """Nó 5: Decisão final de roteamento, geração de alerta e consolidação (SCRUM-61, SCRUM-63)."""
    is_urgente = state.get("is_urgente", False)
    requer_auditoria = state.get("requer_auditoria_humana", False)
    tipo_doc = state.get("tipo_documento", "")
    doc_id = state.get("documento_id", "DOC-SEM-ID")
    canal = state.get("canal_origem", "Interno")

    notificacao: Optional[Dict[str, Any]] = None

    if is_urgente:
        destino = DESTINO_EMERGENCIA
        justificativa = state.get("motivo_urgencia") or "Achado crítico de alta gravidade detectado em triagem."
        notificacao = {
            "canal": "Alerta_Plantao_Medico",
            "mensagem": f"ALERTA URGENTE: Documento {doc_id} encaminhado para Emergência Médica Imediata via {canal}.",
        }
    elif requer_auditoria:
        destino = DESTINO_AUDITORIA_HUMANA
        motivo = "; ".join(state.get("inconsistencias", [])) or "Score de confiança abaixo do limiar de segurança."
        justificativa = f"Encaminhado para fila médica Human-in-the-Loop: {motivo}"
    elif tipo_doc == TipoDocumento.RECEITA.value:
        destino = DESTINO_FARMACIA
        justificativa = "Receituário médico em conformidade encaminhado para dispensação farmacêutica."
    elif tipo_doc == TipoDocumento.GUIA_TISS.value:
        destino = DESTINO_AUTORIZACOES
        justificativa = "Guia TISS validada encaminhada para análise de autorizações."
    elif tipo_doc == TipoDocumento.ATESTADO.value:
        destino = DESTINO_ATESTADOS
        justificativa = "Atestado validado encaminhado para a fila de atestados."
    elif tipo_doc == TipoDocumento.LAUDO.value:
        destino = DESTINO_EXAMES
        justificativa = "Laudo validado encaminhado para a fila de exames."
    elif tipo_doc == TipoDocumento.RELATORIO_ALTA.value:
        destino = DESTINO_ATENDIMENTO_GERAL
        justificativa = "Relatório de alta validado encaminhado para atendimento geral."
    else:
        destino = DESTINO_FLUXO_PADRAO
        justificativa = "Documento clínico analisado com sucesso, sem achados críticos pendentes."

    decisao_roteamento = {
        "destino_principal": destino,
        "requer_auditoria_humana": requer_auditoria,
        "justificativa_roteamento": justificativa,
        "notificacao_gerada": notificacao,
    }

    return {
        **state,
        "destino_principal": destino,
        "justificativa_roteamento": justificativa,
        "notificacao_gerada": notificacao,
        "decisao_roteamento": decisao_roteamento,
        "status": "roteado",
    }
