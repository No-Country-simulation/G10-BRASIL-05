"""Módulo de processamento e sanitização de texto.

Contém funções para remoção de acentos, normalização de espaços
e higienização de textos clínicos para processamento em NLP/LLMs.
"""

import re
import unicodedata


def remover_acentos(texto: str) -> str:
    """Remove a acentuação de uma string mantendo os caracteres base (NFKD).

    Args:
        texto: Texto a ter os acentos removidos.

    Returns:
        str: Texto sem caracteres acentuados.
    """
    if not texto or not isinstance(texto, str):
        return ""

    # Decomposição em forma NFKD e filtragem de marcas diacríticas
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalizar_espacos(texto: str) -> str:
    """Remove espaços duplicados, quebras consecutivas e espaçamentos no início e fim.

    Args:
        texto: Texto original com possíveis múltiplos espaços.

    Returns:
        str: Texto formatado com espaços simples entre as palavras.
    """
    if not texto or not isinstance(texto, str):
        return ""

    return re.sub(r"\s+", " ", texto).strip()


def sanitizar_texto_clinico(texto: str) -> str:
    """Higieniza e padroniza anotações, prontuários e textos clínicos gerais.

    Executa:
    - Normalização Unicode (NFC)
    - Remoção de caracteres de controle invisíveis e nulos (exceto quebras de linha e tabs)
    - Remoção de quebras de linha redundantes excessivas (mantendo no máximo duas quebras consecutivas)
    - Remoção de espaços em branco no início e final de cada linha e do texto como um todo.

    Args:
        texto: Texto clínico bruto a ser higienizado.

    Returns:
        str: Texto clínico sanitizado e estruturado.
    """
    if not texto or not isinstance(texto, str):
        return ""

    # Normalização de representação Unicode canônica
    texto_limpo = unicodedata.normalize("NFC", texto)

    # Remove caracteres nulos e de controle indesejados (mantendo \n, \r, \t)
    texto_limpo = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", texto_limpo)

    # Padroniza quebras de linha no formato UNIX (\n)
    texto_limpo = texto_limpo.replace("\r\n", "\n").replace("\r", "\n")

    # Remove espaços em branco redundantes no final/início de cada linha
    linhas = [re.sub(r"[ \t]+", " ", linha).strip() for linha in texto_limpo.split("\n")]

    # Agrupa quebras de linha consecutivas para no máximo duas
    texto_final = "\n".join(linhas)
    texto_final = re.sub(r"\n{3,}", "\n\n", texto_final)

    return texto_final.strip()
