"""Filtros puros usados pela tela de análise."""
from datetime import datetime


def corresponde_filtro(
    doc: dict,
    filtro_status: str,
    termo_busca: str,
    filtro_canal: str = "Todos",
) -> bool:
    """Indica se um documento atende ao filtro de status, canal e à busca textual."""
    if filtro_status != "Todos":
        status_esperado = {
            "Na fila": "na_fila",
            "Processando": "processando",
            "Concluído": "concluido",
            "Falhou": "falhou",
        }.get(filtro_status)
        if doc.get("status") != status_esperado:
            return False

    if filtro_canal != "Todos":
        canal_doc = (doc.get("canal_origem") or "").lower()
        filtro_canal_norm = filtro_canal.lower().replace(" ", "_")
        if (
            filtro_canal.lower() not in canal_doc
            and filtro_canal_norm not in canal_doc
        ):
            return False

    if termo_busca:
        campos = (
            doc.get("arquivo", ""),
            doc.get("nome_original", ""),
            doc.get("paciente_nome", ""),
            doc.get("paciente_cpf", ""),
            doc.get("documento_id", ""),
            doc.get("canal_origem", ""),
            doc.get("tipo_documento", ""),
        )
        if termo_busca.lower() not in " ".join(str(c) for c in campos).lower():
            return False

    return True
