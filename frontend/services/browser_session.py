from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


_COMPONENT_PATH = Path(__file__).resolve().parents[1] / "components" / "browser_session_storage"
_browser_session_storage = components.declare_component(
    "mediflow_browser_session_storage",
    path=str(_COMPONENT_PATH),
)


def obter_token_persistido() -> str | None:
    valor = _browser_session_storage(action="read", default=None, key="mediflow-token-read")
    return valor if isinstance(valor, str) and valor else None


def salvar_token_persistido(token: str) -> None:
    if st.session_state.get("_token_browser_salvo") == token:
        return
    st.session_state["_token_browser_salvo"] = token
    _browser_session_storage(
        action="write",
        token=token,
        default=None,
        key="mediflow-token-write",
    )


def limpar_token_persistido() -> None:
    tentativa = 1
    if hasattr(st, "session_state"):
        st.session_state.pop("_token_browser_salvo", None)
        tentativa = st.session_state.get("_limpar_token_counter", 0) + 1
        st.session_state["_limpar_token_counter"] = tentativa
    try:
        _browser_session_storage(
            action="clear",
            default=None,
            key=f"mediflow-token-clear-{tentativa}",
        )
    except Exception:
        pass
