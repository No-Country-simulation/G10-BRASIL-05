from typing import List
from app.agent.state import GraphState
from app.agent.config import TERMOS_URGENCIA_CRITICA, DEFAULT_CONFIDENCE_THRESHOLD


def node_avaliacao(state: GraphState) -> GraphState:
    """Nó 4: Avaliação de consistência, score de confiança e detecção de urgência (SCRUM-59, SCRUM-60)."""
    texto = (state.get("documento_texto") or "").lower()
    diag = (state.get("diagnostico_principal") or "").lower()

    inconsistencias: List[str] = []

    # 1. Detecção de Urgência Médica
    termo_urgencia_encontrado = None
    for termo in TERMOS_URGENCIA_CRITICA:
        if termo in texto or termo in diag:
            termo_urgencia_encontrado = termo
            break

    is_urgente = termo_urgencia_encontrado is not None
    motivo_urgencia = (
        f"Achado crítico de emergência médica detectado: '{termo_urgencia_encontrado}'."
        if is_urgente
        else None
    )

    # 2. Avaliação de Consistência e Limiares (Human-in-the-Loop - SCRUM-76)
    paciente = state.get("paciente") or {}
    medico = state.get("medico_solicitante") or {}

    if not paciente.get("nome"):
        inconsistencias.append("Nome do paciente ausente ou não identificado com segurança.")

    if not medico.get("crm"):
        inconsistencias.append("Número de CRM do médico ausente ou inconsistente.")

    if len(texto) < 40 or not state.get("diagnostico_principal"):
        inconsistencias.append("Documento com dados insuficientes ou hipótese diagnóstica ausente.")

    # 3. Cálculo de Score de Confiança Ponderado
    score_base = state.get("score_confianca_classificacao", 0.85) or 0.85

    # Penalizações por inconsistências
    penalidade = len(inconsistencias) * 0.20
    score_final = max(0.10, min(1.0, score_base - penalidade))

    # Se for urgência confirmada e tiver documento legível, score de urgência é alto
    if is_urgente and len(texto) > 40:
        score_final = max(0.95, score_final)

    requer_auditoria = (score_final < DEFAULT_CONFIDENCE_THRESHOLD) or (len(inconsistencias) > 0 and not is_urgente)

    return {
        **state,
        "is_urgente": is_urgente,
        "motivo_urgencia": motivo_urgencia,
        "inconsistencias": inconsistencias,
        "score_confianca_classificacao": score_final,
        "requer_auditoria_humana": requer_auditoria,
        "status": "avaliado",
    }
