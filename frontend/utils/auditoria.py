from copy import deepcopy
import re

from utils.formatadores import (
    crm_do_medico,
    nome_do_paciente,
    normalizar_prioridade,
    rotular_prioridade,
)

DECISAO_APROVAR = "Aprovar"
DECISAO_REJEITAR = "Rejeitar"
DECISAO_CORRIGIR = "Corrigir"
DECISAO_REENVIAR = "Solicitar novo documento/imagem"

STATUS_POR_ACAO = {
    DECISAO_APROVAR: "aprovado",
    DECISAO_REJEITAR: "rejeitado",
    DECISAO_CORRIGIR: "corrigido",
    DECISAO_REENVIAR: "solicitar_reenvio",
}

CAMPOS_EDITAVEIS = {
    "paciente_nome": "Nome do paciente",
    "medico_nome": "Nome do médico solicitante",
    "crm": "CRM",
    "diagnostico_principal": "Diagnóstico principal",
    "cid_sugerido": "CID-10 sugerido",
}

ACOES_QUE_EXIGEM_JUSTIFICATIVA = (DECISAO_REJEITAR, DECISAO_CORRIGIR, DECISAO_REENVIAR)
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
    paciente = dados.get("paciente")
    cpf = ""
    if isinstance(paciente, dict):
        cpf = paciente.get("cpf") or ""
    if not cpf:
        cpf = item.get("paciente_cpf") or ""
    return {
        "paciente_nome": nome_do_paciente(paciente) or "",
        "paciente_cpf": cpf or "",
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
    if "paciente_nome" in correcoes or "paciente_cpf" in correcoes:
        dados["paciente"] = _paciente_corrigido(dados.get("paciente"), correcoes)
    if "medico_nome" in correcoes or "crm" in correcoes:
        dados["medico_solicitante"] = _medico_corrigido(dados.get("medico_solicitante"), correcoes)
    if "medico_solicitante" in dados and dados["medico_solicitante"]:
        medico = dict(dados["medico_solicitante"])
        if "crm" in medico:
            crm_uf = medico.get("crm_uf") or medico.get("crm")
            medico.pop("crm")
            medico["crm_uf"] = crm_uf
            dados["medico_solicitante"] = medico
    for campo in ("diagnostico_principal", "cid_sugerido"):
        if campo in correcoes:
            dados[campo] = correcoes[campo]
    return dados


def _paciente_corrigido(paciente, correcoes: dict):
    if isinstance(paciente, str):
        if "paciente_cpf" in correcoes:
            return {"nome": correcoes.get("paciente_nome", paciente), "cpf": correcoes["paciente_cpf"]}
        return correcoes.get("paciente_nome", paciente)
    pac = dict(paciente or {})
    if "paciente_nome" in correcoes:
        pac["nome"] = correcoes["paciente_nome"]
    if "paciente_cpf" in correcoes:
        pac["cpf"] = correcoes["paciente_cpf"]
    return pac


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
        corrigido["crm_uf"] = correcoes["crm"]
        corrigido.pop("crm", None)
    return corrigido


_MAPEAMENTO_CLINICO = [
    (re.compile(r"extra inputs are not permitted", re.IGNORECASE), None),
    (re.compile(r"o campo ['\"]paciente\.nome['\"] é obrigatório", re.IGNORECASE), "Nome do paciente não identificado no documento."),
    (re.compile(r"o campo ['\"]exame_realizado['\"] é obrigatório", re.IGNORECASE), "Exame realizado não identificado no documento."),
    (re.compile(r"o campo ['\"]medico_solicitante\.nome['\"] é obrigatório", re.IGNORECASE), "Nome do médico solicitante não identificado no documento."),
    (re.compile(r"o campo ['\"]medico_solicitante\.crm_uf['\"] é obrigatório", re.IGNORECASE), "CRM do médico solicitante não identificado no documento."),
    (re.compile(r"o campo ['\"]medico_solicitante\.crm_uf['\"] tem formato inválido", re.IGNORECASE), "CRM do médico com formato não reconhecido."),
    (re.compile(r"o campo ['\"]diagnostico_principal['\"] é obrigatório", re.IGNORECASE), "Diagnóstico principal não identificado no documento."),
    (re.compile(r"o campo ['\"]cid_sugerido['\"] não está no formato cid-10", re.IGNORECASE), "Código CID-10 informado com formato inválido."),
    (re.compile(r"o campo ['\"]paciente\.idade['\"] deve ser um inteiro", re.IGNORECASE), "Idade do paciente fora da faixa clínica esperada (0 a 120 anos)."),
    (re.compile(r"receita requer ao menos um medicamento", re.IGNORECASE), "Receita sem medicamentos válidos com dose identificada."),
    (re.compile(r"a evidência textual ainda não foi verificada contra uma fonte", re.IGNORECASE), "Necessária conferência visual contra o documento original."),
    (re.compile(r"há valores extraídos sem correspondência literal", re.IGNORECASE), "Dados extraídos requerem confirmação com o documento original."),
]


def humanizar_motivos_revisao(texto: str | None) -> list[str]:
    """Converte mensagens técnicas de validação e Pydantic em linguagem clínica amigável."""
    if not texto:
        return ["Revisão humana necessária para validação clínica."]

    texto_limpo = texto.strip()
    if texto_limpo.startswith("Encaminhado para fila médica Human-in-the-Loop:"):
        texto_limpo = texto_limpo.replace("Encaminhado para fila médica Human-in-the-Loop:", "").strip()

    partes = [p.strip() for p in texto_limpo.split(";") if p.strip()]
    motivos_humanizados: list[str] = []

    for parte in partes:
        traduzido = None
        for padrao, substituicao in _MAPEAMENTO_CLINICO:
            if padrao.search(parte):
                traduzido = substituicao
                break

        if traduzido is None:
            if any(p.search(parte) for p, sub in _MAPEAMENTO_CLINICO if sub is None):
                continue
            msg = parte.rstrip(".") + "."
            if msg and msg not in motivos_humanizados:
                motivos_humanizados.append(msg)
        elif traduzido and traduzido not in motivos_humanizados:
            motivos_humanizados.append(traduzido)

    return motivos_humanizados or ["Revisão humana necessária para validação clínica."]
