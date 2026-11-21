"""Filtros puros usados pela tela de análise."""


def corresponde_filtro(doc: dict, filtro_status: str, termo_busca: str) -> bool:
    """Indica se um documento atende ao filtro de status e à busca textual."""
    if filtro_status != "Todos":
        status_esperado = {
            "Na fila": "na_fila",
            "Processando": "processando",
            "Concluído": "concluido",
            "Falhou": "falhou",
        }.get(filtro_status)
        if doc.get("status") != status_esperado:
            return False

    if termo_busca:
        campos = (
            doc.get("arquivo", ""),
            doc.get("paciente_nome", ""),
            doc.get("paciente_cpf", ""),
            doc.get("documento_id", ""),
            doc.get("canal_origem", ""),
        )
        if termo_busca not in " ".join(campos).lower():
            return False

    return True
