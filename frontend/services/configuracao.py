import os
from pathlib import Path

from dotenv import load_dotenv
from services.erros import ErroDeConfiguracao

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

AMBIENTES_LOCAIS = {"local", "development", "dev"}
AMBIENTES_PRODUCAO = {"production", "prod"}


def obter_ambiente() -> str:
    valor = os.getenv("APP_ENV")
    if valor is None:
        raise ErroDeConfiguracao("APP_ENV precisa estar configurado.")
    ambiente = valor.strip().lower()
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
        url = os.getenv("API_URL_LOCAL", "").strip().rstrip("/")
        if not url:
            raise ErroDeConfiguracao("APP_ENV=local exige API_URL_LOCAL.")
    if not url.startswith(("http://", "https://")):
        raise ErroDeConfiguracao("A URL configurada para a API deve começar com http:// ou https://.")
    return url


def obter_tempo_limite_em_segundos() -> float:
    valor = os.getenv("API_TIMEOUT")
    if valor is None:
        raise ErroDeConfiguracao("API_TIMEOUT precisa estar configurado.")
    try:
        tempo = float(valor)
    except ValueError as erro:
        raise ErroDeConfiguracao("API_TIMEOUT precisa ser um número positivo.") from erro
    if tempo <= 0:
        raise ErroDeConfiguracao("API_TIMEOUT precisa ser um número positivo.")
    return tempo
