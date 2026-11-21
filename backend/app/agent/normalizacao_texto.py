"""Busca literal tolerante a diferenças de acentuação e espaçamento do OCR."""

import re
import unicodedata


def normalizar_cpf(valor: object) -> str | None:
    """Retorna CPF com 11 dígitos ou None quando ausente/inválido."""
    if not isinstance(valor, str):
        return None
    digitos = re.sub(r"\D", "", valor)
    return digitos if len(digitos) == 11 else None


def validar_cpf(valor: object) -> bool:
    """Valida os dois dígitos verificadores sem corrigir o valor recebido."""
    cpf = normalizar_cpf(valor)
    if cpf is None or cpf == cpf[0] * 11:
        return False

    digitos = [int(digito) for digito in cpf]
    primeiro = (sum(d * peso for d, peso in zip(digitos[:9], range(10, 1, -1))) * 10) % 11
    primeiro = 0 if primeiro == 10 else primeiro
    if digitos[9] != primeiro:
        return False

    segundo = (sum(d * peso for d, peso in zip(digitos[:10], range(11, 1, -1))) * 10) % 11
    segundo = 0 if segundo == 10 else segundo
    return digitos[10] == segundo


def localizar_trecho_cpf(texto: str, cpf: str) -> tuple[int, int] | None:
    """Localiza CPF mesmo quando o OCR alterna entre pontuação e dígitos contínuos."""
    cpf_limpo = normalizar_cpf(cpf)
    if cpf_limpo is None:
        return None
    padrao_cpf = re.compile(r"(?<!\d)\d(?:[\s.\-/]?\d){10}(?!\d)")
    for correspondencia in padrao_cpf.finditer(texto or ""):
        if re.sub(r"\D", "", correspondencia.group()) == cpf_limpo:
            return correspondencia.span()
    return None


def _normalizar_com_posicoes(texto: str) -> tuple[str, list[int]]:
    caracteres: list[str] = []
    posicoes: list[int] = []
    espaco_pendente: int | None = None
    for indice, caractere in enumerate(texto or ""):
        if caractere.isspace():
            if caracteres:
                espaco_pendente = indice
            continue
        if espaco_pendente is not None:
            caracteres.append(" ")
            posicoes.append(espaco_pendente)
            espaco_pendente = None
        decomposicao = unicodedata.normalize("NFKD", caractere)
        base = "".join(item for item in decomposicao if not unicodedata.combining(item))
        for normalizado in base.casefold():
            caracteres.append(normalizado)
            posicoes.append(indice)
    return "".join(caracteres), posicoes


def localizar_trecho(texto: str, valor: str) -> tuple[int, int] | None:
    """Localiza valor ignorando apenas acentos, caixa e repetições de espaço."""
    origem, posicoes = _normalizar_com_posicoes(texto)
    alvo, _ = _normalizar_com_posicoes(valor)
    if not alvo:
        return None
    inicio = origem.find(alvo)
    if inicio < 0:
        return None
    fim_normalizado = inicio + len(alvo) - 1
    return posicoes[inicio], posicoes[fim_normalizado] + 1
