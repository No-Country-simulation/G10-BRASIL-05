"""Componente Streamlit para a nova área de upload e triagem de documentos."""

from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT_PATH = Path(__file__).resolve().parent / "triagem_uploader"

_triagem_uploader = components.declare_component(
    "mediflow_triagem_uploader",
    path=str(_COMPONENT_PATH),
)


def render_triagem_uploader(key: str = "triagem_uploader") -> dict | None:
    """Renderiza a área de upload da Triagem Clínica com eventos reais de XHR onprogress."""
    return _triagem_uploader(key=key, default=None)
