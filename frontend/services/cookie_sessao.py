"""Sincroniza o cookie HttpOnly da sessão pelo próprio navegador."""

from pathlib import Path
import hashlib

import streamlit.components.v1 as components

from services.triagem_event_stream import obter_url_api_browser


_COMPONENT_PATH = Path(__file__).resolve().parents[1] / "components" / "session_cookie"
_session_cookie = components.declare_component(
    "mediflow_session_cookie",
    path=str(_COMPONENT_PATH),
)


def sincronizar_cookie_sessao(
    acao: str,
    *,
    token: str | None = None,
    tentativa: int = 0,
) -> dict | None:
    """Executa emissão ou remoção do cookie HttpOnly no browser."""
    if acao not in {"definir", "limpar"}:
        raise ValueError("Ação de cookie de sessão inválida.")
    identificador = (
        hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
        if token
        else str(tentativa)
    )
    resultado = _session_cookie(
        action=acao,
        token=token or "",
        api_base=obter_url_api_browser(),
        attempt=tentativa,
        default=None,
        key=f"cookie_sessao_{acao}_{identificador}_{tentativa}",
    )
    return resultado if isinstance(resultado, dict) else None
