import os
from pathlib import Path

from dotenv import load_dotenv
from services.erros import ErroDeConfiguracao

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

URL_PADRAO_DA_API = "http://localhost:8000"
TEMPO_LIMITE_PADRAO_EM_SEGUNDOS = 60.0
VALORES_QUE_ATIVAM_A_DEMONSTRACAO = ("1", "true", "sim")
AMBIENTES_LOCAIS = {"local", "development", "dev"}
AMBIENTES_PRODUCAO = {"production", "prod"}


def obter_ambiente() -> str:
    ambiente = os.getenv("APP_ENV", "local").strip().lower()
    if ambiente in AMBIENTES_LOCAIS:
        return "local"
    if ambiente in AMBIENTES_PRODUCAO:
        return "production"
    raise ErroDeConfiguracao(
        "APP_ENV inválido. Use 'local' para desenvolvimento ou 'production' para produção."
    )


def obter_url_do_backend() -> str:
    ambiente = obter_ambiente()
    if ambiente == "production":
        url = os.getenv("API_URL_PRODUCTION", "").strip().rstrip("/")
        if not url:
            raise ErroDeConfiguracao(
                "APP_ENV=production exige API_URL_PRODUCTION. "
                "Configure a URL de produção; o frontend não usará a URL local."
            )
    else:
        url = os.getenv("API_URL_LOCAL", URL_PADRAO_DA_API).strip().rstrip("/")
        if not url:
            raise ErroDeConfiguracao("APP_ENV=local exige API_URL_LOCAL.")
    if not url.startswith(("http://", "https://")):
        raise ErroDeConfiguracao("A URL configurada para a API deve começar com http:// ou https://.")
    return url


def usar_dados_simulados() -> bool:
    valor = os.getenv("MODO_DEMONSTRACAO", "").strip().lower()
    ativado = valor in VALORES_QUE_ATIVAM_A_DEMONSTRACAO
    if ativado and obter_ambiente() != "local":
        raise ErroDeConfiguracao(
            "MODO_DEMONSTRACAO só pode ser ativado em APP_ENV=local."
        )
    return ativado


def obter_tempo_limite_em_segundos() -> float:
    try:
        tempo = float(os.getenv("API_TIMEOUT", ""))
    except ValueError:
        return TEMPO_LIMITE_PADRAO_EM_SEGUNDOS
    return tempo if tempo > 0 else TEMPO_LIMITE_PADRAO_EM_SEGUNDOS
