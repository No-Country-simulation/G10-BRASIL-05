import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

URL_PADRAO_DA_API = "http://localhost:8000"
TEMPO_LIMITE_PADRAO_EM_SEGUNDOS = 60.0
VALORES_QUE_ATIVAM_A_DEMONSTRACAO = ("1", "true", "sim")


def obter_url_do_backend() -> str:
    url = os.getenv("API_BASE_URL", "").strip().rstrip("/")
    return url or URL_PADRAO_DA_API


def usar_dados_simulados() -> bool:
    # O modo demonstração só liga quando pedido de forma explícita no .env
    valor = os.getenv("MODO_DEMONSTRACAO", "").strip().lower()
    return valor in VALORES_QUE_ATIVAM_A_DEMONSTRACAO


def obter_tempo_limite_em_segundos() -> float:
    try:
        tempo = float(os.getenv("API_TIMEOUT", ""))
    except ValueError:
        return TEMPO_LIMITE_PADRAO_EM_SEGUNDOS
    return tempo if tempo > 0 else TEMPO_LIMITE_PADRAO_EM_SEGUNDOS
