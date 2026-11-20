"""Filtro conservador de documentos médicos versus conteúdo fora de escopo."""

from app.agent.state import GraphState
from app.agent.harness import avaliar_escopo
from app.schemas.escopo_documento import ResultadoEscopoDocumento


def avaliar_elegibilidade(texto: str) -> tuple[str, float, str]:
    """Mantém a assinatura legada enquanto o contrato usa o resultado estruturado."""
    resultado = avaliar_escopo(texto)
    confianca = 1.0 if resultado.escopo in {"medico", "nao_medico"} else 0.0
    return resultado.escopo, confianca, resultado.justificativa


def node_filtro_elegibilidade(state: GraphState) -> GraphState:
    """Nó LangGraph que grava no estado a avaliação de escopo."""
    avaliacao_salva = state.get("avaliacao_escopo")
    if avaliacao_salva:
        resultado = ResultadoEscopoDocumento.model_validate(avaliacao_salva)
    else:
        resultado = avaliar_escopo(state.get("documento_texto") or "")
    return {
        **state,
        "elegibilidade": resultado.escopo,
        "legibilidade_documento": resultado.legibilidade,
        "avaliacao_escopo": resultado.model_dump(mode="json"),
        "justificativa_elegibilidade": resultado.justificativa,
        "etapa_revisao": None,
        "motivo_revisao": (
            resultado.justificativa
            if resultado.escopo == "medico" and resultado.legibilidade != "legivel"
            else None
        ),
        "requer_auditoria_humana": False,
        "status": "elegibilidade_avaliada",
    }
