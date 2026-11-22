"""Ponte do Streamlit para receber eventos SSE enviados pelo backend."""

from pathlib import Path
import os

import streamlit.components.v1 as components

from services.configuracao import obter_ambiente, obter_url_do_backend

_COMPONENT_PATH = Path(__file__).resolve().parents[1] / "components" / "triage_event_stream"
_triagem_event_stream = components.declare_component(
    "mediflow_triagem_event_stream",
    path=str(_COMPONENT_PATH),
)


def escutar_eventos_triagem(url: str, chave: str) -> dict | None:
    """Mantém uma conexão SSE no navegador e devolve o evento mais recente ao Streamlit."""
    evento = _triagem_event_stream(stream_url=url, default=None, key=chave)
    return evento if isinstance(evento, dict) else None


def obter_url_stream_triagem() -> str:
    """Monta uma URL acessível pelo navegador, inclusive no Docker Compose local."""
    caminho = "/api/v1/triagem/eventos/stream"
    base = obter_url_api_browser()
    return f"{base}{caminho}" if base else caminho


def obter_url_api_browser() -> str:
    """Retorna a base pública da API para chamadas executadas dentro do navegador."""
    base = os.getenv("API_BROWSER_URL", "").strip().rstrip("/")
    if base:
        return base
    if obter_ambiente() == "production":
        base_prod = os.getenv("API_BROWSER_URL_PRODUCTION", "").strip().rstrip("/")
        if base_prod:
            return base_prod
        return obter_url_do_backend().rstrip("/")
    base_local = os.getenv("API_BROWSER_URL_LOCAL", "").strip().rstrip("/")
    if base_local:
        return base_local
    return obter_url_do_backend().rstrip("/")
