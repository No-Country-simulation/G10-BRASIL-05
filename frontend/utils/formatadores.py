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


def formatar_cpf(valor: str | None) -> str:
    """Formata sequência de dígitos no padrão 000.000.000-00."""
    if not valor:
        return ""
    digitos = "".join(c for c in str(valor) if c.isdigit())
    if len(digitos) > 11:
        digitos = digitos[:11]
    if len(digitos) <= 3:
        return digitos
    if len(digitos) <= 6:
        return f"{digitos[:3]}.{digitos[3:]}"
    if len(digitos) <= 9:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:]}"
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def validar_cpf_algoritmo(cpf: str | None) -> bool:
    """Valida o CPF através do cálculo oficial dos dígitos verificadores (módulo 11)."""
    if not cpf:
        return False
    digitos = [int(c) for c in str(cpf) if c.isdigit()]
    if len(digitos) != 11:
        return False
    if len(set(digitos)) == 1:
        return False

    soma_1 = sum(d * peso for d, peso in zip(digitos[:9], range(10, 1, -1)))
    resto_1 = (soma_1 * 10) % 11
    d1 = 0 if resto_1 >= 10 else resto_1
    if digitos[9] != d1:
        return False

    soma_2 = sum(d * peso for d, peso in zip(digitos[:10], range(11, 1, -1)))
    resto_2 = (soma_2 * 10) % 11
    d2 = 0 if resto_2 >= 10 else resto_2
    return digitos[10] == d2

