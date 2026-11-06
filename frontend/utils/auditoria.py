from copy import deepcopy

from utils.formatadores import (
    crm_do_medico,
    nome_do_paciente,
    normalizar_prioridade,
    rotular_prioridade,
)

DECISAO_APROVAR = "Aprovar"
DECISAO_REJEITAR = "Rejeitar"
DECISAO_CORRIGIR = "Corrigir"

STATUS_POR_ACAO = {
    DECISAO_APROVAR: "aprovado",
    DECISAO_REJEITAR: "rejeitado",
    DECISAO_CORRIGIR: "corrigido",
}

CAMPOS_EDITAVEIS = {
    "paciente_nome": "Nome do paciente",
    "medico_nome": "Nome do médico solicitante",
    "crm": "CRM",
    "diagnostico_principal": "Diagnóstico principal",
    "cid_sugerido": "CID-10 sugerido",
}

ACOES_QUE_EXIGEM_JUSTIFICATIVA = (DECISAO_REJEITAR, DECISAO_CORRIGIR)
ORDEM_POR_PRIORIDADE = {"EMERGENCIA": 0, "URGENTE": 1, "ROTINA": 3}
ORDEM_DA_PRIORIDADE_DESCONHECIDA = 2


def ordenar_fila(fila: list[dict]) -> list[dict]:
    return sorted(fila, key=_chave_de_ordenacao)


def montar_rotulo_da_fila(item: dict) -> str:
    documento_id = item.get("documento_id") or "-"
    prioridade = rotular_prioridade(item.get("nivel_prioridade"))
    return f"{documento_id} · {prioridade}" if prioridade else documento_id


def extrair_valores_editaveis(item: dict) -> dict:
    dados = item.get("dados_extraidos") or {}
    medico = dados.get("medico_solicitante") or {}
    return {
        "paciente_nome": nome_do_paciente(dados.get("paciente")) or "",
        "medico_nome": medico.get("nome") or "",
        "crm": crm_do_medico(medico) or "",
        "diagnostico_principal": dados.get("diagnostico_principal") or "",
        "cid_sugerido": dados.get("cid_sugerido") or "",
    }


def calcular_correcoes(valores_atuais: dict, valores_editados: dict) -> dict:
    return {
        campo: novo_valor.strip()
        for campo, novo_valor in valores_editados.items()
        if novo_valor.strip() != valores_atuais.get(campo, "").strip()
    }


def aplicar_correcoes(dados_extraidos: dict, correcoes: dict) -> dict:
    dados = deepcopy(dados_extraidos)
    if "paciente_nome" in correcoes:
        dados["paciente"] = _paciente_com_nome(dados.get("paciente"), correcoes["paciente_nome"])
    if "medico_nome" in correcoes or "crm" in correcoes:
        dados["medico_solicitante"] = _medico_corrigido(dados.get("medico_solicitante"), correcoes)
    for campo in ("diagnostico_principal", "cid_sugerido"):
        if campo in correcoes:
            dados[campo] = correcoes[campo]
    return dados


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


def montar_decisao(
    acao: str,
    auditor: str,
    justificativa: str,
    dados_extraidos: dict,
    correcoes: dict,
) -> dict:
    return {
        "status_aprovacao": STATUS_POR_ACAO[acao],
        "auditor_nome": auditor.strip(),
        "justificativa": justificativa.strip(),
        "dados_corrigidos": (
            aplicar_correcoes(dados_extraidos, correcoes) if acao == DECISAO_CORRIGIR else None
        ),
    }


def _chave_de_ordenacao(item: dict) -> tuple[int, float, str]:
    nivel = normalizar_prioridade(item.get("nivel_prioridade"))
    ordem = ORDEM_POR_PRIORIDADE.get(nivel, ORDEM_DA_PRIORIDADE_DESCONHECIDA)
    score = item.get("score_confianca")
    return ordem, score if score is not None else 0.0, item.get("created_at") or ""


def _paciente_com_nome(paciente, nome: str):
    # Mantém o formato recebido: texto continua texto e objeto continua objeto
    if isinstance(paciente, str):
        return nome
    return {**(paciente or {}), "nome": nome}


def _medico_corrigido(medico: dict | None, correcoes: dict) -> dict:
    corrigido = dict(medico or {})
    if "medico_nome" in correcoes:
        corrigido["nome"] = correcoes["medico_nome"]
    if "crm" in correcoes:
        corrigido[_campo_do_crm(corrigido)] = correcoes["crm"]
    return corrigido


def _campo_do_crm(medico: dict) -> str:
    # Escreve no mesmo campo em que o CRM veio, pois o schema não aceita campos extras
    return "crm_uf" if "crm_uf" in medico and "crm" not in medico else "crm"
