from datetime import datetime, timezone
import unicodedata

import pandas as pd

from utils.aparencia import cor_da_confianca, cor_da_prioridade
from utils.formatadores import (
    formatar_data_hora_brasil,
    normalizar_prioridade,
    rotular_prioridade,
    rotular_tipo_documento,
)

FILTRO_TODOS = "Todos"
STATUS_APROVADO = "Aprovado"
STATUS_URGENCIA = "Urgência"
STATUS_EM_AUDITORIA = "Aguardando revisão"
STATUS_REJEITADO = "Rejeitado"
STATUS_DESCONHECIDO = "Não classificado"
SEM_VALOR = "-"

FILTROS_DE_STATUS = [FILTRO_TODOS, STATUS_APROVADO, STATUS_URGENCIA, STATUS_EM_AUDITORIA, STATUS_REJEITADO]
OPCOES_FILTRO_STATUS = FILTROS_DE_STATUS

FILTROS_DE_PRIORIDADE = ["Todas", "Emergência", "Urgente", "Rotina"]

FILTROS_DE_TIPO = [
    "Todos",
    "Laudo de Exame",
    "Receituário Médico",
    "Guia TISS",
    "Relatório de Alta",
    "Atestado Médico",
]

OPCOES_ORDENACAO = [
    "Mais recentes primeiro",
    "Mais antigos primeiro",
    "Maior prioridade",
    "Maior confiança",
]

STATUS_POR_DESTINO = {
    "Fluxo_Padrao": STATUS_APROVADO,
    "Farmacia_Hospitalar": STATUS_APROVADO,
    "Fila_Emergencia_Medica": STATUS_URGENCIA,
    "Auditoria_Humana": STATUS_EM_AUDITORIA,
    "Nao_Elegivel": STATUS_REJEITADO,
    "Descarte": STATUS_REJEITADO,
}

STATUS_POR_DECISAO_DE_AUDITORIA = {
    "auditoria_aprovado": STATUS_APROVADO,
    "auditoria_corrigido": STATUS_APROVADO,
    "auditoria_rejeitado": STATUS_REJEITADO,
    "REJEITADO": STATUS_REJEITADO,
    "rejeitado": STATUS_REJEITADO,
    "auditoria_rejeitado": STATUS_REJEITADO,
    "APROVADO": STATUS_APROVADO,
    "aprovado": STATUS_APROVADO,
    "CORRIGIDO": STATUS_APROVADO,
    "corrigido": STATUS_APROVADO,
}

ICONE_POR_STATUS = {
    STATUS_APROVADO: "",
    STATUS_URGENCIA: "",
    STATUS_EM_AUDITORIA: "",
    STATUS_REJEITADO: "",
}

FUNDO_POR_STATUS = {
    STATUS_URGENCIA: "#FDECEA",
    STATUS_EM_AUDITORIA: "#FFF4E0",
    STATUS_APROVADO: "#EAF7EF",
    STATUS_REJEITADO: "#EEEEEE",
}

PESO_PRIORIDADE = {
    "EMERGENCIA": 3,
    "URGENTE": 2,
    "ROTINA": 1,
}


def remover_acentos(texto: str | None) -> str:
    if not texto:
        return ""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8").lower().strip()


def identificar_status(documento: dict) -> str:
    try:
        from utils.alertas_clinicos import alerta_esta_desativado
        if alerta_esta_desativado(documento.get("documento_id")):
            return STATUS_APROVADO
    except Exception:
        pass
    status_da_auditoria = STATUS_POR_DECISAO_DE_AUDITORIA.get(documento.get("status_processamento"))
    if status_da_auditoria:
        return status_da_auditoria
    revisao = documento.get("revisao")
    if isinstance(revisao, dict) and revisao.get("decisao"):
        dec = str(revisao.get("decisao")).lower()
        if "rejeit" in dec:
            return STATUS_REJEITADO
        if "aprov" in dec or "corrig" in dec:
            return STATUS_APROVADO
    return STATUS_POR_DESTINO.get(documento.get("destino_principal"), STATUS_DESCONHECIDO)


def filtrar_por_status(documentos: list[dict], filtro: str) -> list[dict]:
    if filtro == FILTRO_TODOS:
        return documentos
    return [documento for documento in documentos if identificar_status(documento) == filtro]


def corresponde_busca(documento: dict, termo: str) -> bool:
    termo_norm = remover_acentos(termo)
    if not termo_norm:
        return True

    campos_para_busca = [
        documento.get("documento_id") or "",
        documento.get("paciente_nome") or "",
        documento.get("paciente_cpf") or "",
        rotular_tipo_documento(documento.get("tipo_documento")) or "",
        documento.get("tipo_documento") or "",
        rotular_prioridade(documento.get("nivel_prioridade")) or "",
        documento.get("nivel_prioridade") or "",
        identificar_status(documento),
        documento.get("destino_principal") or "",
    ]

    for campo in campos_para_busca:
        if termo_norm in remover_acentos(str(campo)):
            return True
    return False


def calcular_metricas_historico(documentos: list[dict]) -> dict:
    metricas = {
        "total": len(documentos),
        "aprovados": 0,
        "urgencias": 0,
        "em_auditoria": 0,
        "rejeitados": 0,
    }
    for doc in documentos:
        status = identificar_status(doc)
        if status == STATUS_APROVADO:
            metricas["aprovados"] += 1
        elif status == STATUS_URGENCIA:
            metricas["urgencias"] += 1
        elif status == STATUS_EM_AUDITORIA:
            metricas["em_auditoria"] += 1
        elif status == STATUS_REJEITADO:
            metricas["rejeitados"] += 1
    return metricas


def filtrar_historico_completo(
    documentos: list[dict],
    termo_busca: str = "",
    filtro_status: str = FILTRO_TODOS,
    filtro_prioridade: str = "Todas",
    filtro_tipo: str = "Todos",
    ordenacao: str = "Mais recentes primeiro",
) -> list[dict]:
    resultado = []
    for doc in documentos:
        # 1. Filtro de busca textual
        if termo_busca and not corresponde_busca(doc, termo_busca):
            continue

        # 2. Filtro de status
        if filtro_status != FILTRO_TODOS and identificar_status(doc) != filtro_status:
            continue

        # 3. Filtro de prioridade
        if filtro_prioridade != "Todas":
            prioridade_rotulada = rotular_prioridade(doc.get("nivel_prioridade"))
            if prioridade_rotulada != filtro_prioridade:
                continue

        # 4. Filtro de tipo de documento
        if filtro_tipo != "Todos":
            tipo_rotulado = rotular_tipo_documento(doc.get("tipo_documento"))
            if tipo_rotulado != filtro_tipo:
                continue

        resultado.append(doc)

    # Ordenação
    def chave_data(d: dict) -> datetime:
        val = d.get("created_at") or d.get("data_iso") or ""
        if isinstance(val, datetime):
            if val.tzinfo is not None:
                return val.astimezone(timezone.utc).replace(tzinfo=None)
            return val
        if isinstance(val, str):
            val = val.strip()
            if not val or val == "-":
                return datetime.min
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    return dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except Exception:
                pass
            for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
                try:
                    return datetime.strptime(val, fmt)
                except Exception:
                    pass
        return datetime.min

    if ordenacao == "Mais recentes primeiro":
        resultado.sort(key=chave_data, reverse=True)
    elif ordenacao == "Mais antigos primeiro":
        resultado.sort(key=chave_data)
    elif ordenacao == "Maior prioridade":
        def chave_prioridade(d: dict):
            pri = normalizar_prioridade(d.get("nivel_prioridade"))
            return PESO_PRIORIDADE.get(pri, 0)
        resultado.sort(key=chave_prioridade, reverse=True)
    elif ordenacao == "Maior confiança":
        resultado.sort(key=lambda d: d.get("score_confianca") or 0.0, reverse=True)

    return resultado


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
    return formatar_data_hora_brasil(valor)


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
