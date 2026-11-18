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
    [data-testid="stSidebarNav"] {
        padding-top: 0.75rem !important;
        padding-bottom: 0.75rem !important;
    }
    [data-testid="stSidebarNavItems"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
    }
    [data-testid="stSidebarNavItems"] li {
        margin: 0 !important;
    }
    [data-testid="stSidebarNavLink"] {
        padding: 0.60rem 0.85rem !important;
        border-radius: 8px !important;
        transition: all 150ms ease !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        border: 1px solid transparent !important;
    }
    [data-testid="stSidebarNavLink"]:hover {
        background-color: rgba(0, 157, 187, 0.08) !important;
        border-color: rgba(0, 157, 187, 0.18) !important;
    }
    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: #D8EAF2 !important;
        color: #0B3C7A !important;
        font-weight: 700 !important;
        border-left: 4px solid #009DBB !important;
        border-radius: 3px 8px 8px 3px !important;
    }
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
        height: 100% !important;
    }
    [data-testid="stSidebarUserContent"] {
        display: flex !important;
        flex-direction: column !important;
        flex-grow: 1 !important;
        height: 100% !important;
    }
    [data-testid="stSidebarUserContent"] > div:last-child,
    [data-testid="stSidebarUserContent"] > div:has(.sidebar-footer) {
        margin-top: auto !important;
        padding-top: 20px !important;
        padding-bottom: 12px !important;
    }
    .sidebar-footer {
        position: sticky;
        bottom: 12px;
        text-align: center;
        width: 100%;
        z-index: 10;
    }
    .sidebar-badge {
        display: inline-block;
        background: #D8EAF2;
        color: #0B2A5B;
        font-size: 0.73rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        padding: 5px 12px;
        border-radius: 999px;
        border: 1px solid rgba(11, 60, 122, 0.12);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    [data-testid="stSidebar"][data-collapsed="true"] .sidebar-footer,
    [data-testid="stSidebar"][aria-expanded="false"] .sidebar-footer {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.logo(CAMINHO_DA_LOGO, size="large", icon_image=CAMINHO_DA_LOGO)
validar_configuracao_frontend()

paginas = [
    st.Page(
        "pages/1_Triagem_Clinica.py",
        title="Triagem Clínica",
        icon=":material/stethoscope:",
        default=True,
    ),
    st.Page(
        "pages/2_Auditoria_Humana.py",
        title="Auditoria",
        icon=":material/verified_user:",
    ),
    st.Page(
        "pages/3_Historico.py",
        title="Histórico",
        icon=":material/history:",
    ),
    st.Page(
        "pages/4_WhatsApp_Evolution.py",
        title="Conectar",
        icon=":material/chat:",
    ),
]

exibir_barra_lateral()
exibir_aviso_de_dados_ficticios()
st.navigation(paginas).run()
