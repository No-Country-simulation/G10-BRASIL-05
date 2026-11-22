from typing import Any, Dict, List
from app.agent.state import GraphState
from app.agent.config import TERMOS_URGENCIA_CRITICA, DEFAULT_CONFIDENCE_THRESHOLD
from app.schemas.classificacao import TipoDocumento


def node_avaliacao(state: GraphState) -> GraphState:
    """Nó 4: Avaliação de consistência, score ponderado 15/20/15/50 e motor de regras (Excalidraw)."""
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

    # 2. Avaliação de Consistência e Limiares
    paciente = state.get("paciente") or {}
    medico = state.get("medico_solicitante") or {}

    if not paciente.get("nome"):
        inconsistencias.append("Nome do paciente ausente ou não identificado com segurança.")

    if not (medico.get("crm") or medico.get("crm_uf")):
        inconsistencias.append("Número de CRM do médico ausente ou inconsistente.")

    tipo_documento = state.get("tipo_documento")
    diagnostico_exigido = tipo_documento in {
        TipoDocumento.RELATORIO_ALTA,
        TipoDocumento.RELATORIO_ALTA.value,
    }
    if len(texto) < 40 or (diagnostico_exigido and not state.get("diagnostico_principal")):
        inconsistencias.append("Documento com dados insuficientes ou hipótese diagnóstica ausente.")

    # -------------------------------------------------------------
    # Motor de Regras e Ponderação MediFlow (Excalidraw: 15/20/15/50 = 100)
    # -------------------------------------------------------------
    # Etapa 1: Qualidade Visual (Máx: 15 pts | Corte >= 12)
    qualidade = state.get("qualidade_documento") or {}
    legibilidade = state.get("legibilidade_documento") or ""
    if qualidade.get("status") == "adequada" and legibilidade == "legivel":
        score_qualidade = 15.0
    elif legibilidade == "legivel" or len(texto) >= 60:
        score_qualidade = 12.0
    elif len(texto) >= 40:
        score_qualidade = 8.0
    else:
        score_qualidade = 4.0

    # Etapa 2: Extração de Dados do Médico e Paciente (Máx: 20 pts | Corte >= 8)
    score_cadastro = 0.0
    if paciente.get("nome"):
        score_cadastro += 10.0
    if paciente.get("idade") is not None or paciente.get("data_nascimento"):
        score_cadastro += 3.0
    if medico.get("nome"):
        score_cadastro += 7.0

    # Etapa 3: Validação Regulatória de CPF, CRM, CNS (Máx: 15 pts | Corte >= 10)
    score_regulatorio = 0.0
    if paciente.get("cpf") and not state.get("cpf_validacao_falhou", False):
        score_regulatorio += 8.0
    if medico.get("crm") or medico.get("crm_uf"):
        score_regulatorio += 7.0

    # Etapa 4: Interpretação de Sinais Clínicos e Diagnósticos (Máx: 50 pts | Corte >= 16)
    score_clinico = 0.0
    if tipo_documento:
        score_clinico += 10.0
    if state.get("diagnostico_principal") or state.get("exame_realizado"):
        score_clinico += 15.0
    if state.get("medicamentos") or len(texto) > 100:
        score_clinico += 15.0
    if state.get("cid_sugerido"):
        score_clinico += 10.0

    if is_urgente and len(texto) >= 40:
        score_clinico = max(score_clinico, 50.0)

    score_total = round(score_qualidade + score_cadastro + score_regulatorio + score_clinico, 1)

    cortes_aprovados = (
        score_qualidade >= 12.0
        and score_cadastro >= 8.0
        and score_regulatorio >= 10.0
        and score_clinico >= 16.0
    )

    # Classificação nas 3 Faixas do Motor de Regras:
    # 85 - 100: Confiável + encaminhamento direto
    # 60 - 85: Revisão humana
    # 0 - 60: Pede novo documento
    if score_total >= 85.0 and cortes_aprovados:
        faixa = "CONFIAVEL_DIRETO"
    elif score_total >= 60.0:
        faixa = "REVISAO_HUMANA"
    else:
        faixa = "PEDE_NOVO_DOCUMENTO"

    score_detalhes = {
        "etapa_1_qualidade": {
            "pontos": score_qualidade,
            "maximo": 15,
            "corte": 12,
            "aprovado": score_qualidade >= 12.0,
        },
        "etapa_2_cadastro": {
            "pontos": score_cadastro,
            "maximo": 20,
            "corte": 8,
            "aprovado": score_cadastro >= 8.0,
        },
        "etapa_3_regulatorio": {
            "pontos": score_regulatorio,
            "maximo": 15,
            "corte": 10,
            "aprovado": score_regulatorio >= 10.0,
        },
        "etapa_4_clinico": {
            "pontos": score_clinico,
            "maximo": 50,
            "corte": 16,
            "aprovado": score_clinico >= 16.0,
        },
        "score_total": score_total,
        "cortes_aprovados": cortes_aprovados,
        "faixa": faixa,
    }

    # Score normalizado de 0.0 a 1.0 para compatibilidade
    score_final = max(0.10, min(1.0, score_total / 100.0))

    revisao_ja_concluida = bool(state.get("revisao_concluida"))
    requer_auditoria = not revisao_ja_concluida and (
        faixa != "CONFIAVEL_DIRETO"
        or not cortes_aprovados
        or len(inconsistencias) > 0
    )

    return {
        **state,
        "is_urgente": is_urgente,
        "motivo_urgencia": motivo_urgencia,
        "inconsistencias": inconsistencias,
        "score_qualidade": score_qualidade,
        "score_cadastro": score_cadastro,
        "score_regulatorio": score_regulatorio,
        "score_clinico": score_clinico,
        "score_total": score_total,
        "faixa_motor_regras": faixa,
        "score_detalhes": score_detalhes,
        "score_confianca_classificacao": score_final,
        "requer_auditoria_humana": requer_auditoria,
        "motivo_revisao": (
            motivo_urgencia
            if is_urgente and requer_auditoria
            else "; ".join(inconsistencias)
            if inconsistencias
            else "Pontuação do motor de regras exige revisão humana."
            if faixa == "REVISAO_HUMANA"
            else "Pontuação insuficiente no motor de regras (< 60 pts). Solicitar novo documento."
            if faixa == "PEDE_NOVO_DOCUMENTO"
            else None
        ),
        "etapa_revisao": "risco" if requer_auditoria else None,
        "status": "avaliado",
    }
