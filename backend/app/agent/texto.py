"""Utilitários de texto compartilhados pelos nós do agente."""

import json
import unicodedata
from typing import Any, Dict


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparações tolerantes a grafia."""
    sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acentos.lower()


def extrair_json(resposta: str) -> Dict[str, Any]:
    """Extrai o objeto JSON da resposta da LLM, aceitando blocos ```json."""
    inicio, fim = resposta.find("{"), resposta.rfind("}")
    if inicio == -1 or fim < inicio:
        raise ValueError("Resposta da LLM não contém um objeto JSON.")
    return json.loads(resposta[inicio : fim + 1])
