from typing import Any, Dict, List
from app.agent.state import GraphState
from app.agent.config import TERMOS_URGENCIA_CRITICA, DEFAULT_CONFIDENCE_THRESHOLD
from app.schemas.classificacao import TipoDocumento


def node_avaliacao(state: GraphState) -> GraphState:
    """Nó 4: Avaliação de consistência, score ponderado 15/20/15/50 e motor de regras (Excalidraw)."""
    texto = (state.get("documento_texto") or "").lower()
    diag = (state.get("diagnostico_principal") or "").lower()
    pri_classificada = str(state.get("nivel_prioridade") or "").upper()
    decisao_humana = state.get("decisao_humana") or {}

    inconsistencias: List[str] = []

    # 1. Detecção de Urgência Médica
    termo_urgencia_encontrado = None

    # Se já houve decisão humana de rotina, respeitar a decisão médica
    if decisao_humana.get("fila_encaminhamento") == "Rotina" or decisao_humana.get("nivel_prioridade") == "ROTINA":
        is_urgente = False
    else:
        # Busca primeiro no diagnóstico clínico identificado
        for termo in TERMOS_URGENCIA_CRITICA:
            if termo in diag:
                termo_urgencia_encontrado = termo
                break

        # Se não houver termo crítico no diagnóstico e o modelo classificou como ROTINA, não força emergência
        if not termo_urgencia_encontrado and pri_classificada != "ROTINA":
            for termo in TERMOS_URGENCIA_CRITICA:
                if termo in texto:
                    idx = texto.find(termo)
                    trecho_anterior = texto[max(0, idx - 120):idx]
                    termos_exclusao = (
                        "valores de referência", "referência", "referencia",
                        "indicações", "indicacoes", "prevenção", "prevencao",
                        "afastado", "afastada", "sem sinais", "ausência de",
                        "ausencia de", "não há", "nao ha", "negativo para"
                    )
                    if not any(exc in trecho_anterior for exc in termos_exclusao):
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

    # Etapa 3: Validação Regulatória (CRM tem prioridade clínica máxima; CPF não é obrigatório nem reduz pontos)
    score_regulatorio = 0.0
    tem_crm = bool(medico.get("crm") or medico.get("crm_uf"))
    tem_cpf = bool(paciente.get("cpf"))
    tem_cns = bool(paciente.get("cns"))

    if tem_crm:
        score_regulatorio = 15.0
    elif tem_cpf or tem_cns:
        score_regulatorio = 10.0
    else:
        score_regulatorio = 5.0

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

    destino_principal = state.get("destino_principal")
    if pri_classificada == "ROTINA" and (score_total >= 85.0 or faixa == "CONFIAVEL_DIRETO"):
        requer_auditoria = False
        motivo_revisao = None
        inconsistencias = []
        destino_principal = "Fluxo_Padrao"
    else:
        motivo_revisao = (
            motivo_urgencia
            if is_urgente and requer_auditoria
            else "; ".join(inconsistencias)
            if inconsistencias
            else "Pontuação do motor de regras exige revisão humana."
            if faixa == "REVISAO_HUMANA" and requer_auditoria
            else "Pontuação insuficiente no motor de regras (< 60 pts). Solicitar novo documento."
            if faixa == "PEDE_NOVO_DOCUMENTO" and requer_auditoria
            else None
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
        "motivo_revisao": motivo_revisao,
        "destino_principal": destino_principal,
        "etapa_revisao": "risco" if requer_auditoria else None,
        "status": "avaliado",
    }
