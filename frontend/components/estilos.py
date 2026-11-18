from pathlib import Path

import streamlit as st

PASTA_DE_IMAGENS = Path(__file__).resolve().parents[1] / "assets"
CAMINHO_DA_LOGO = PASTA_DE_IMAGENS / "logo_barra.png"
CAMINHO_DO_ICONE = PASTA_DE_IMAGENS / "icone.png"
CAMINHO_DO_CSS = PASTA_DE_IMAGENS / "estilo.css"


def aplicar_estilos() -> None:
    css = CAMINHO_DO_CSS.read_text(encoding="utf-8")
    st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)
