import unicodedata

NIVEL_SUCESSO = "sucesso"
NIVEL_AVISO = "aviso"
NIVEL_ERRO = "erro"

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


def normalizar_prioridade(nivel_prioridade: str | None) -> str | None:
    """Devolve ROTINA, URGENTE ou EMERGENCIA, ou None se o nível for desconhecido.

    O backend responde em formatos diferentes ("Urgente", "URGENTE", "Emergência"),
    então a comparação ignora maiúsculas, minúsculas e acentos.
    """
    if not nivel_prioridade:
        return None
    sem_acentos = unicodedata.normalize("NFKD", nivel_prioridade).encode("ascii", "ignore").decode()
    nivel = sem_acentos.strip().upper()
    return nivel if nivel in ROTULOS_PRIORIDADE else None


def rotular_prioridade(nivel_prioridade: str | None) -> str | None:
    nivel = normalizar_prioridade(nivel_prioridade)
    return ROTULOS_PRIORIDADE[nivel] if nivel else nivel_prioridade


def nome_do_paciente(paciente) -> str | None:
    """O paciente chega como objeto ({"nome", "idade"}) ou apenas como texto."""
    if isinstance(paciente, dict):
        return paciente.get("nome")
    return paciente


def crm_do_medico(medico: dict) -> str | None:
    """O CRM chega em "crm" (API de triagem) ou em "crm_uf" (schema de dados extraídos)."""
    return medico.get("crm") or medico.get("crm_uf")


def descrever_armazenamento(armazenamento: dict | None) -> tuple[str, str] | None:
    """Devolve (nível, texto) sobre o salvamento do documento, ou None se a API não informou."""
    if not armazenamento:
        return None
    status = (armazenamento.get("status_backup") or "").strip().lower()
    caminho = "/".join(
        parte for parte in (armazenamento.get("bucket"), armazenamento.get("caminho_objeto")) if parte
    )
    if status.startswith("falha"):
        return NIVEL_ERRO, "O documento foi triado, mas o backup não foi gravado no armazenamento."
    if "local" in status:
        return NIVEL_AVISO, f"Salvo apenas localmente, sem usar o OCI: {caminho or 'sem caminho informado'}"
    if status.startswith("sucesso"):
        return NIVEL_SUCESSO, f"Documento salvo em {caminho or 'sem caminho informado'}"
    return NIVEL_AVISO, f"Status do backup não reconhecido: {armazenamento.get('status_backup') or 'ausente'}"
