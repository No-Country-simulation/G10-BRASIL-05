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

    eh_imagem = bool(state.get("avaliacao_visual")) or (state.get("tipo_arquivo") or "").lower() in {".png", ".jpg", ".jpeg", "imagem"}
    legibilidade = resultado.legibilidade
    if resultado.escopo == "medico" and not eh_imagem:
        legibilidade = "legivel"

    dados_escopo = resultado.model_dump(mode="json")
    dados_escopo["legibilidade"] = legibilidade

    return {
        **state,
        "elegibilidade": resultado.escopo,
        "legibilidade_documento": legibilidade,
        "avaliacao_escopo": dados_escopo,
        "justificativa_elegibilidade": resultado.justificativa,
        "etapa_revisao": None,
        "motivo_revisao": (
            "Documento médico com caligrafia ilegível — requer transcrição por auditor humano"
            if resultado.escopo == "medico" and legibilidade == "ilegivel" and eh_imagem
            else None
        ),
        "requer_auditoria_humana": False,
        "status": "elegibilidade_avaliada",
    }
