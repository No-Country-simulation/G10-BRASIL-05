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
    /* ========================================================
       LOGO & CABEÇALHO DO SIDEBAR
       ======================================================== */
    [data-testid="stSidebarHeader"] {
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
    }
    [data-testid="stSidebarHeader"] img {
        width: 220px !important;
        max-width: 100% !important;
        height: auto !important;
        max-height: 95px !important;
        object-fit: contain;
        transition: all 200ms ease;
    }

    /* ========================================================
       SIDEBAR RECOLHIDA: MODO COMPACTO (80px)
       ======================================================== */
    [data-testid="stSidebar"][data-collapsed="true"],
    [data-testid="stSidebar"][aria-expanded="false"] {
        width: 80px !important;
        min-width: 80px !important;
        max-width: 80px !important;
        transition: width 200ms ease;
    }

    /* Logo quando recolhida: ícone centralizado */
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarHeader"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarHeader"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarHeader"] img,
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarHeader"] img {
        width: 48px !important;
        max-width: 48px !important;
        height: 48px !important;
        max-height: 48px !important;
        object-fit: cover !important;
        object-position: 22% center !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    }

    /* ========================================================
       LINKS DE NAVEGAÇÃO (EXPANDIDO)
       ======================================================== */
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

    /* ========================================================
       LINKS DE NAVEGAÇÃO QUANDO RECOLHIDO (ÍCONES CENTRALIZADOS)
       ======================================================== */
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavItems"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavItems"] {
        align-items: center !important;
        gap: 8px !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavLink"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 46px !important;
        height: 46px !important;
        padding: 0 !important;
        margin: 0 auto !important;
        border-radius: 12px !important;
        border: 1px solid transparent !important;
        font-size: 0 !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavLink"] *,
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] * {
        font-size: 1.35rem !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavLink"] span:last-child:not(:only-child),
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] span:last-child:not(:only-child) {
        display: none !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: #D8EAF2 !important;
        color: #0B3C7A !important;
        border-left: 1px solid transparent !important;
        box-shadow: 0 0 0 2px #009DBB !important;
    }

    /* ========================================================
       CONTEÚDO SECUNDÁRIO & RODAPÉ (EXPANDIDO)
       ======================================================== */
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

    /* Oculta o conteúdo secundário e footer quando recolhido */
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarUserContent"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"] {
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
