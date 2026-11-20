"""Busca literal tolerante a diferenças de acentuação e espaçamento do OCR."""

import unicodedata


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
