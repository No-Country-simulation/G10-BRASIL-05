"""Filtro conservador de documentos médicos versus conteúdo fora de escopo."""

import re

from app.agent.state import GraphState


_SINAIS_CLINICOS = (
    r"\bcrm\b", r"\bcid\b", r"posologia", r"receitu[aá]rio", r"prescri[cç][aã]o", r"receita\s+m[eé]dica",
    r"laudo", r"atestado", r"paciente", r"diagn[oó]stico", r"medicamento",
    r"hospital", r"cl[ií]nica", r"exame m[eé]dico", r"solicitante",
)
_SINAIS_CULINARIOS = (
    r"\bingredientes\b", r"\bmodo de preparo\b", r"\bforno\b", r"\bx[ií]cara[s]?\b",
    r"\bcolher(?:es)?\b", r"\bmiojo\b", r"\bpudim\b", r"\bcozinhar\b",
)


def avaliar_elegibilidade(texto: str) -> tuple[str, float, str]:
    """Retorna uma decisão conservadora sem afirmar autenticidade ou validade legal."""
    clinicos = [s for s in _SINAIS_CLINICOS if re.search(s, texto, re.IGNORECASE)]
    culinarios = [s for s in _SINAIS_CULINARIOS if re.search(s, texto, re.IGNORECASE)]

    if culinarios and not clinicos:
        resultado, confianca = "nao_medico", 0.95
        justificativa = "Conteúdo culinário identificado sem sinais clínicos explícitos."
    elif clinicos and not culinarios:
        resultado, confianca = "medico", min(0.95, 0.60 + 0.10 * len(clinicos))
        justificativa = "Foram encontrados sinais explícitos de conteúdo médico/clínico."
    else:
        resultado, confianca = "incerto", 0.0
        justificativa = "Não há sinais suficientes para determinar o escopo com segurança."

    return resultado, confianca, justificativa


def node_filtro_elegibilidade(state: GraphState) -> GraphState:
    """Nó LangGraph que grava no estado a avaliação de escopo."""
    resultado, confianca, justificativa = avaliar_elegibilidade(state.get("documento_texto") or "")
    return {
        **state,
        "elegibilidade": resultado,
        "confianca_elegibilidade": confianca,
        "justificativa_elegibilidade": justificativa,
        "etapa_revisao": "elegibilidade" if resultado == "incerto" else None,
        "motivo_revisao": justificativa if resultado == "incerto" else None,
        "requer_auditoria_humana": resultado == "incerto",
        "status": "elegibilidade_avaliada",
    }
