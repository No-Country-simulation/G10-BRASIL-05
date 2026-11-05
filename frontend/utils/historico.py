from datetime import datetime

import pandas as pd

from utils.aparencia import cor_da_confianca, cor_da_prioridade
from utils.formatadores import rotular_prioridade, rotular_tipo_documento

FILTRO_TODOS = "Todos"
STATUS_APROVADO = "Aprovado"
STATUS_URGENCIA = "Urgência"
STATUS_EM_AUDITORIA = "Em Auditoria"
STATUS_REJEITADO = "Rejeitado"
STATUS_DESCONHECIDO = "Não classificado"
SEM_VALOR = "-"

FILTROS_DE_STATUS = [FILTRO_TODOS, STATUS_APROVADO, STATUS_URGENCIA, STATUS_EM_AUDITORIA, STATUS_REJEITADO]

STATUS_POR_DESTINO = {
    "Fluxo_Padrao": STATUS_APROVADO,
    "Farmacia_Hospitalar": STATUS_APROVADO,
    "Fila_Emergencia_Medica": STATUS_URGENCIA,
    "Auditoria_Humana": STATUS_EM_AUDITORIA,
}

STATUS_POR_DECISAO_DE_AUDITORIA = {
    "auditoria_aprovado": STATUS_APROVADO,
    "auditoria_corrigido": STATUS_APROVADO,
    "auditoria_rejeitado": STATUS_REJEITADO,
}

ICONE_POR_STATUS = {
    STATUS_APROVADO: "✅",
    STATUS_URGENCIA: "🚨",
    STATUS_EM_AUDITORIA: "👨‍⚕️",
    STATUS_REJEITADO: "⛔",
}

FUNDO_POR_STATUS = {
    STATUS_URGENCIA: "#FDECEA",
    STATUS_EM_AUDITORIA: "#FFF4E0",
    STATUS_APROVADO: "#EAF7EF",
    STATUS_REJEITADO: "#EEEEEE",
}


def identificar_status(documento: dict) -> str:
    status_da_auditoria = STATUS_POR_DECISAO_DE_AUDITORIA.get(documento.get("status_processamento"))
    if status_da_auditoria:
        return status_da_auditoria
    return STATUS_POR_DESTINO.get(documento.get("destino_principal"), STATUS_DESCONHECIDO)


def filtrar_por_status(documentos: list[dict], filtro: str) -> list[dict]:
    if filtro == FILTRO_TODOS:
        return documentos
    return [documento for documento in documentos if identificar_status(documento) == filtro]


def montar_tabela_estilizada(documentos: list[dict]):
    tabela = pd.DataFrame(montar_linhas_da_tabela(documentos))
    estilos = pd.DataFrame(
        montar_estilos_da_tabela(documentos, list(tabela.columns)),
        columns=tabela.columns,
    )
    return tabela.style.apply(lambda _: estilos, axis=None)


def montar_linhas_da_tabela(documentos: list[dict]) -> list[dict]:
    return [_montar_linha(documento) for documento in documentos]


def montar_estilos_da_tabela(documentos: list[dict], colunas: list[str]) -> list[list[str]]:
    return [_montar_estilos_da_linha(documento, colunas) for documento in documentos]


def _montar_linha(documento: dict) -> dict:
    status = identificar_status(documento)
    score = documento.get("score_confianca")
    return {
        "Documento": documento.get("documento_id") or SEM_VALOR,
        "Status": f"{ICONE_POR_STATUS.get(status, '')} {status}".strip(),
        "Tipo": rotular_tipo_documento(documento.get("tipo_documento")) or SEM_VALOR,
        "Prioridade": rotular_prioridade(documento.get("nivel_prioridade")) or SEM_VALOR,
        "Confiança": f"{score:.0%}" if score is not None else SEM_VALOR,
        "Data": _formatar_data(documento.get("created_at")),
    }


def _formatar_data(valor: str | None) -> str:
    if not valor:
        return SEM_VALOR
    try:
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return valor


def _montar_estilos_da_linha(documento: dict, colunas: list[str]) -> list[str]:
    fundo = FUNDO_POR_STATUS.get(identificar_status(documento))
    base = f"background-color: {fundo};" if fundo else ""
    cores = {
        "Prioridade": cor_da_prioridade(documento.get("nivel_prioridade")),
        "Confiança": cor_da_confianca(documento.get("score_confianca")),
    }
    return [_montar_estilo_da_celula(base, cores.get(coluna)) for coluna in colunas]


def _montar_estilo_da_celula(base: str, cor: str | None) -> str:
    return f"{base} color: {cor}; font-weight: 700;" if cor else base
