"""Carregamento de folhas CSS locais para a interface Streamlit."""
from pathlib import Path

import streamlit as st


def aplicar_css(caminho: str | Path, substituicoes: dict[str, str] | None = None) -> None:
    """Lê uma folha CSS e a aplica à página atual."""
    css = Path(caminho).read_text(encoding="utf-8").strip()
    for marcador, valor in (substituicoes or {}).items():
        css = css.replace(marcador, valor)
    if not css.startswith("<style>"):
        css = f"<style>\n{css}\n</style>"
    st.markdown(css, unsafe_allow_html=True)
