import streamlit as st

from components.barra_lateral import CAMINHO_DA_LOGO, exibir_barra_lateral
from components.modo_de_execucao import (
    exibir_aviso_de_dados_ficticios,
    validar_configuracao_frontend,
)

st.set_page_config(page_title="MediFlow", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stSidebarHeader"] img {
        width: 230px !important;
        max-width: 100% !important;
        height: auto !important;
        max-height: 105px !important;
        object-fit: contain;
        transition: width 180ms ease, height 180ms ease;
    }
    [data-testid="stSidebar"][data-collapsed="true"],
    [data-testid="stSidebar"][aria-expanded="false"] {
        width: 88px !important;
        min-width: 88px !important;
        max-width: 88px !important;
        transition: width 180ms ease;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarHeader"] img,
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarHeader"] img {
        width: 80px !important;
        max-width: none !important;
        height: 80px !important;
        max-height: none !important;
        object-fit: cover;
        object-position: 25% center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.logo(CAMINHO_DA_LOGO, size="large", icon_image=CAMINHO_DA_LOGO)
validar_configuracao_frontend()

paginas = [
    st.Page("pages/1_Triagem_Clinica.py", title="Triagem Clínica", default=True),
    st.Page("pages/2_Auditoria_Humana.py", title="Auditoria"),
    st.Page("pages/3_Historico.py", title="Histórico"),
    st.Page("pages/4_WhatsApp_Evolution.py", title="Conectar"),
]

exibir_barra_lateral()
exibir_aviso_de_dados_ficticios()
st.navigation(paginas).run()
