import re
from app.agent.state import GraphState


def node_ingestao(state: GraphState) -> GraphState:
    """Nó 1: Normalização e higienização do documento clínico (SCRUM-56)."""
    texto = state.get("documento_texto") or ""

    # Normalização de espaçamentos e quebras de linha múltiplas
    texto_limpo = re.sub(r"[ \t]+", " ", texto)
    texto_limpo = re.sub(r"\n{3,}", "\n\n", texto_limpo).strip()

    erros = list(state.get("erros", []))
    if not texto_limpo:
        erros.append("Texto do documento está vazio após higienização.")

    return {
        **state,
        "documento_texto": texto_limpo,
        "erros": erros,
        "status": "ingestado",
    }
