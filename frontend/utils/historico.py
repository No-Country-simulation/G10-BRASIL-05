FILTRO_TODOS = "Todos"
STATUS_APROVADO = "Aprovado"
STATUS_URGENCIA = "Urgência"
STATUS_EM_AUDITORIA = "Em Auditoria"
STATUS_DESCONHECIDO = "Não classificado"

FILTROS_DE_STATUS = [FILTRO_TODOS, STATUS_APROVADO, STATUS_URGENCIA, STATUS_EM_AUDITORIA]

STATUS_POR_DESTINO = {
    "Fluxo_Padrao": STATUS_APROVADO,
    "Fila_Emergencia_Medica": STATUS_URGENCIA,
    "Auditoria_Humana": STATUS_EM_AUDITORIA,
}

ICONE_POR_STATUS = {
    STATUS_APROVADO: "✅",
    STATUS_URGENCIA: "🚨",
    STATUS_EM_AUDITORIA: "👨‍⚕️",
}


def identificar_status(documento: dict) -> str:
    decisao = documento.get("decisao_roteamento") or {}
    return STATUS_POR_DESTINO.get(decisao.get("destino_principal"), STATUS_DESCONHECIDO)


def filtrar_por_status(documentos: list[dict], filtro: str) -> list[dict]:
    if filtro == FILTRO_TODOS:
        return documentos
    return [documento for documento in documentos if identificar_status(documento) == filtro]


def montar_linhas_da_tabela(documentos: list[dict]) -> list[dict]:
    return [_montar_linha(documento) for documento in documentos]


def _montar_linha(documento: dict) -> dict:
    classificacao = documento.get("classificacao") or {}
    paciente = (documento.get("dados_extraidos") or {}).get("paciente") or {}
    status = identificar_status(documento)
    score = classificacao.get("score_confianca_classificacao")
    return {
        "Documento": documento.get("documento_id") or "-",
        "Status": f"{ICONE_POR_STATUS.get(status, '')} {status}".strip(),
        "Tipo": classificacao.get("tipo_documento") or "-",
        "Paciente": paciente.get("nome") or "-",
        "Confiança": f"{score:.0%}" if score is not None else "-",
    }