"""Checagens conservadoras de legibilidade antes da classificação clínica."""

from app.agent.state import GraphState
from app.agent.harness import texto_clinico_sem_metadados


_MARCADORES_SEM_TEXTO_CONFIAVEL = (
    "sem camada de texto nativa",
    "aguardando auditoria médica manual",
    "sem texto legível",
    "texto ilegível",
)


def node_qualidade_documento(state: GraphState) -> GraphState:
    """Avalia sinais disponíveis; não trata OCR como prova da imagem original."""
    texto = texto_clinico_sem_metadados(state.get("documento_texto") or "")
    tipo_arquivo = (state.get("tipo_arquivo") or "").lower()
    marcadores = [m for m in _MARCADORES_SEM_TEXTO_CONFIAVEL if m in texto.lower()]
    motivos = []

    if len(texto) < 40:
        motivos.append("Texto insuficiente para classificação e extração confiáveis.")
    if marcadores:
        motivos.append("A origem informa ausência de texto nativo ou legibilidade insuficiente.")
    if state.get("legibilidade_documento") != "legivel":
        motivos.append("Documento médico com caligrafia ilegível — requer transcrição por auditor humano")
    if tipo_arquivo not in {"texto", "json"} and not state.get("referencia_fonte"):
        motivos.append(
            "A fonte original não está vinculada para conferência humana."
        )

    adequado = not motivos
    motivo_revisao = None
    if not adequado:
        if state.get("legibilidade_documento") != "legivel" or "caligrafia ilegível" in texto.lower():
            motivo_revisao = "Documento médico com caligrafia ilegível — requer transcrição por auditor humano"
        else:
            motivo_revisao = "; ".join(motivos)

    qualidade = {
        "status": "adequada" if adequado else "insuficiente",
        "texto_caracteres": len(texto),
        "marcadores_detectados": marcadores,
        "motivos": motivos,
        "fonte_visual_verificavel": bool(state.get("referencia_fonte")),
    }
    return {
        **state,
        "qualidade_documento": qualidade,
        "motivo_revisao": motivo_revisao,
        "etapa_revisao": None if adequado else "qualidade",
        "requer_auditoria_humana": not adequado,
        "status": "qualidade_verificada",
    }
