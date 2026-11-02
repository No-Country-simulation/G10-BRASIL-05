ROTULOS_TIPO_DOCUMENTO = {
    "RECEITA": "Receituário Médico",
    "LAUDO": "Laudo de Exame",
    "GUIA_TISS": "Guia TISS",
    "RELATORIO_ALTA": "Relatório de Alta",
    "ATESTADO": "Atestado Médico",
}

ROTULOS_PRIORIDADE = {
    "ROTINA": "Rotina",
    "URGENTE": "Urgente",
    "EMERGENCIA": "Emergência",
}


def rotular_tipo_documento(tipo_documento: str | None) -> str | None:
    return ROTULOS_TIPO_DOCUMENTO.get(tipo_documento, tipo_documento)


def rotular_prioridade(nivel_prioridade: str | None) -> str | None:
    return ROTULOS_PRIORIDADE.get(nivel_prioridade, nivel_prioridade)