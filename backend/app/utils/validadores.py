"""Módulo de validação e formatação de documentos e identificadores.

Contém funções para validação de CPF, CRM, COREN, E-mail e formatação de CPF.
"""

import re

# Lista oficial de Unidades Federativas do Brasil
UFS_BRASIL = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
}

# Regex para validação de formato de E-mail padrão
REGEX_EMAIL = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Regex para CRM: aceita formatos como 'CRM 123456-SP', 'CRM/SP 123456', '123456-SP', '123456/SP'
REGEX_CRM = re.compile(
    r"^(?:CRM\s*[-/]?\s*)?(?:(?P<uf1>[A-Z]{2})\s*[-/]?\s*)?(?P<num>\d{4,10})\s*[-/]?\s*(?:(?P<uf2>[A-Z]{2}))?$",
    re.IGNORECASE
)

# Regex para COREN: aceita formatos como 'COREN-SP 123456', 'COREN 123456-SP', '123456-ENF', 'COREN-SP 123456-ENF'
REGEX_COREN = re.compile(
    r"^(?:COREN\s*[-/]?\s*)?(?:(?P<uf1>[A-Z]{2})\s*[-/]?\s*)?(?P<num>\d{3,10})\s*[-/.]?\s*(?:(?P<cat>ENF|TE|AE|OBST|PAR)\s*[-/.]?\s*)?(?:(?P<uf2>[A-Z]{2}))?$",
    re.IGNORECASE
)


def validar_cpf(cpf: str) -> bool:
    """Valida um número de CPF utilizando o cálculo oficial do Módulo 11.

    Aceita CPF formatado (com pontos e hífen) ou apenas dígitos numéricos.
    Rejeita sequências com dígitos repetidos (ex: '111.111.111-11').

    Args:
        cpf: String contendo o CPF a ser validado.

    Returns:
        bool: True se o CPF for válido, False caso contrário.
    """
    if not cpf or not isinstance(cpf, str):
        return False

    # Remove todos os caracteres que não sejam dígitos
    numeros = re.sub(r"\D", "", cpf)

    if len(numeros) != 11:
        return False

    # Rejeita dígitos todos iguais (ex.: '00000000000', '11111111111')
    if numeros == numeros[0] * 11:
        return False

    digitos = [int(d) for d in numeros]

    # Cálculo do 1º dígito verificador
    soma_1 = sum(digitos[i] * (10 - i) for i in range(9))
    resto_1 = soma_1 % 11
    d1 = 0 if resto_1 < 2 else 11 - resto_1

    if digitos[9] != d1:
        return False

    # Cálculo do 2º dígito verificador
    soma_2 = sum(digitos[i] * (11 - i) for i in range(10))
    resto_2 = soma_2 % 11
    d2 = 0 if resto_2 < 2 else 11 - resto_2

    return digitos[10] == d2


def formatar_cpf(cpf: str) -> str:
    """Formata uma string numérica de 11 dígitos no padrão oficial 'XXX.XXX.XXX-XX'.

    Args:
        cpf: String contendo os dígitos ou texto do CPF.

    Returns:
        str: CPF formatado como 'XXX.XXX.XXX-XX'.

    Raises:
        ValueError: Se o CPF não contiver exatamente 11 dígitos numéricos.
    """
    if not cpf or not isinstance(cpf, str):
        raise ValueError("O CPF fornecido deve ser uma string não vazia.")

    numeros = re.sub(r"\D", "", cpf)

    if len(numeros) != 11:
        raise ValueError(
            f"CPF inválido para formatação: esperados 11 dígitos, recebidos {len(numeros)}."
        )

    return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"


def validar_crm(crm: str) -> bool:
    """Valida o registro no Conselho Regional de Medicina (CRM).

    Aceita variações como:
    - 'CRM 123456-SP'
    - 'CRM/SP 123456'
    - '123456-SP'
    - '123456/SP'

    Args:
        crm: String contendo o registro do CRM.

    Returns:
        bool: True se for um CRM com formato e UF válidos, False caso contrário.
    """
    if not crm or not isinstance(crm, str):
        return False

    match = REGEX_CRM.match(crm.strip())
    if not match:
        return False

    uf = match.group("uf1") or match.group("uf2")
    if not uf:
        return False

    return uf.upper() in UFS_BRASIL


def validar_coren(coren: str) -> bool:
    """Valida o registro no Conselho Regional de Enfermagem (COREN).

    Aceita formatos como:
    - 'COREN-SP 123456'
    - 'COREN 123456-SP'
    - 'COREN-SP 123456-ENF'
    - '123456-ENF'
    - '123456-SP'

    Args:
        coren: String contendo o registro do COREN.

    Returns:
        bool: True se o formato for válido, False caso contrário.
    """
    if not coren or not isinstance(coren, str):
        return False

    match = REGEX_COREN.match(coren.strip())
    if not match:
        return False

    uf = match.group("uf1") or match.group("uf2")
    if uf and uf.upper() not in UFS_BRASIL:
        return False

    # Deve ter ao menos número e (UF ou Categoria ou prefixo COREN)
    tem_prefixo = "coren" in coren.lower()
    tem_cat = bool(match.group("cat"))
    tem_uf = bool(uf)

    return tem_prefixo or tem_cat or tem_uf


def validar_email(email: str) -> bool:
    """Valida o formato padrão de um endereço de e-mail.

    Args:
        email: String contendo o endereço de e-mail.

    Returns:
        bool: True se o formato for válido, False caso contrário.
    """
    if not email or not isinstance(email, str):
        return False

    email_limpo = email.strip()
    if len(email_limpo) > 254:
        return False

    return bool(REGEX_EMAIL.match(email_limpo))
