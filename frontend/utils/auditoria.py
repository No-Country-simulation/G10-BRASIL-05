DECISAO_APROVAR = "Aprovar"
DECISAO_REJEITAR = "Rejeitar"
DECISAO_CORRIGIR = "Corrigir"

RESULTADO_APROVADO = "APROVADO"
RESULTADO_REJEITADO = "REJEITADO"

CAMPOS_EDITAVEIS = {
    "paciente_nome": "Nome do paciente",
    "medico_nome": "Nome do médico solicitante",
    "crm": "CRM",
    "diagnostico_principal": "Diagnóstico principal",
    "cid_sugerido": "CID-10 sugerido",
}

ACOES_QUE_EXIGEM_JUSTIFICATIVA = (DECISAO_REJEITAR, DECISAO_CORRIGIR)


def extrair_valores_editaveis(documento: dict) -> dict:
    dados = documento.get("dados_extraidos") or {}
    medico = dados.get("medico_solicitante") or {}
    return {
        "paciente_nome": _nome_do_paciente(dados.get("paciente")),
        "medico_nome": medico.get("nome") or "",
        "crm": medico.get("crm") or medico.get("crm_uf") or "",
        "diagnostico_principal": dados.get("diagnostico_principal") or "",
        "cid_sugerido": dados.get("cid_sugerido") or "",
    }


def calcular_correcoes(valores_atuais: dict, valores_editados: dict) -> dict:
    return {
        campo: novo_valor.strip()
        for campo, novo_valor in valores_editados.items()
        if novo_valor.strip() != valores_atuais.get(campo, "").strip()
    }


def validar_decisao(acao: str, auditor: str, justificativa: str, correcoes: dict) -> str | None:
    if not auditor.strip():
        return "Informe a identificação do auditor."
    if acao == DECISAO_CORRIGIR and not correcoes:
        return "Altere ao menos um campo para corrigir."
    if acao != DECISAO_CORRIGIR and correcoes:
        return "Você alterou campos. Use 'Corrigir' para enviar as correções ou desfaça as alterações."
    if acao in ACOES_QUE_EXIGEM_JUSTIFICATIVA and not justificativa.strip():
        return f"Informe a justificativa para {acao.lower()} o documento."
    return None


def montar_decisao(acao: str, auditor: str, justificativa: str, correcoes: dict) -> dict:
    return {
        "decisao": RESULTADO_REJEITADO if acao == DECISAO_REJEITAR else RESULTADO_APROVADO,
        "dados_corrigidos": correcoes if acao == DECISAO_CORRIGIR else {},
        "justificativa": justificativa.strip(),
        "auditor": auditor.strip(),
    }


def _nome_do_paciente(paciente) -> str:
    if isinstance(paciente, dict):
        return paciente.get("nome") or ""
    return paciente or ""