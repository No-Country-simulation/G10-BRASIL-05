import streamlit as st

from components.barra_lateral import (
    CAMINHO_DA_LOGO,
    CAMINHO_DO_ICONE,
    exibir_barra_lateral,
)
from services.autenticacao import (
    esta_autenticado,
    obter_usuario_autenticado,
    precisa_trocar_senha,
    validar_sessao_api,
)
from utils.usuarios import NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO, eh_conta_institucional_whatsapp

st.set_page_config(page_title="MediFlow", layout="wide")
st.markdown(
    """
    <style>
    /* ========================================================
       CABEÇALHO SUPERIOR (LIMPO E SEM LINHA)
       ======================================================== */
    header[data-testid="stHeader"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    .stAppToolbar {
        background-color: transparent !important;
        border-bottom: none !important;
        box-shadow: none !important;
        height: 3.5rem !important;
        pointer-events: none !important;
        overflow: visible !important;
    }
    /* Oculta botão Deploy, notificação de reload e actions secundárias do Streamlit */
    .stDeployButton,
    [data-testid="stDeployButton"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbarActions"],
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    /* Remove imagem duplicada no cabeçalho superior quando recolhido */
    header[data-testid="stHeader"] img {
        display: none !important;
    }

    /* ========================================================
       BOTÕES DE RECOLHER/EXPANDIR (ESTILO OFICINA)
       Idênticos nos dois casos: botão redondo na divisória da barra com a tela (-right-3 top-5)
       ======================================================== */
    /* Garante que ambos os botões e seus containers fiquem visíveis e clicáveis */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapsedControl"] button {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 1050 !important;
    }

    /* Estilo compartilhado para o botão em ambos os estados (expandido << e recolhido >>) */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"] button {
        width: 24px !important;
        height: 24px !important;
        min-width: 24px !important;
        min-height: 24px !important;
        border-radius: 9999px !important;
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.15) !important;
        color: #64748B !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        padding: 0 !important;
        transition: all 150ms ease-in-out !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover,
    [data-testid="stExpandSidebarButton"]:hover,
    button[data-testid="stExpandSidebarButton"]:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover {
        color: #0F172A !important;
        border-color: #94A3B8 !important;
        transform: scale(1.1) !important;
        background-color: #F8FAFC !important;
    }
    [data-testid="stSidebarCollapseButton"] button svg,
    [data-testid="stSidebarCollapseButton"] button span,
    [data-testid="stExpandSidebarButton"] svg,
    button[data-testid="stExpandSidebarButton"] svg,
    [data-testid="stExpandSidebarButton"] span,
    button[data-testid="stExpandSidebarButton"] span,
    [data-testid="stSidebarCollapsedControl"] button svg,
    [data-testid="stSidebarCollapsedControl"] button span {
        font-size: 13px !important;
        line-height: 1 !important;
        color: #64748B !important;
    }

    /* Quando a barra está EXPANDIDA: seta << na divisória direita entre a barra e a tela */
    [data-testid="stSidebarCollapseButton"] {
        position: absolute !important;
        right: -12px !important; /* Exatamente na divisória da barra expandida e a tela */
        top: 20px !important;
        margin: 0 !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Quando a barra está RECOLHIDA:
       Seta >> flutuante na divisória entre a barra de 80px e a tela (80px - 12px = 68px) */
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"] button {
        position: fixed !important;
        left: 68px !important; /* 80px - 12px: centralizado sobre a divisória de 80px */
        top: 20px !important;  /* Alinhado na mesma altura do centro da logo */
        margin: 0 !important;
    }

    /* ========================================================
       CABEÇALHO DA SIDEBAR EXPANDIDA & RECOLHIDA (ESTILO OFICINA)
       ======================================================== */
    /* Expandido: logo na esquerda e botão << na divisória direita, alinhados perfeitamente */
    [data-testid="stSidebarHeader"] {
        position: relative !important;
        overflow: visible !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        height: 64px !important;
        padding: 0 1rem !important;
        width: 100% !important;
    }
    [data-testid="stSidebarHeader"] img {
        width: auto !important;
        max-width: 195px !important;
        height: auto !important;
        max-height: 55px !important;
        object-fit: contain !important;
        transition: all 350ms cubic-bezier(0.2, 0.8, 0.2, 1) !important;
    }

    /* ========================================================
       OPÇÃO B: SIDEBAR PERMANENTE DE 80px QUANDO RECOLHIDA
       ======================================================== */
    [data-testid="stSidebar"] {
        overflow: visible !important;
        transition: width 350ms cubic-bezier(0.2, 0.8, 0.2, 1),
                    min-width 350ms cubic-bezier(0.2, 0.8, 0.2, 1),
                    max-width 350ms cubic-bezier(0.2, 0.8, 0.2, 1),
                    transform 350ms cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        will-change: width, min-width, max-width, transform;
    }
    [data-testid="stSidebar"] > div:first-child {
        overflow: visible !important;
        transition: width 350ms cubic-bezier(0.2, 0.8, 0.2, 1) !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"],
    [data-testid="stSidebar"][aria-expanded="false"] {
        display: block !important;
        visibility: visible !important;
        transform: none !important;
        margin-left: 0 !important;
        width: 80px !important;
        min-width: 80px !important;
        max-width: 80px !important;
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        height: 100vh !important;
        z-index: 100 !important;
        background-color: #EAF4F8 !important;
        border-right: 1px solid rgba(11, 60, 122, 0.10) !important;
        box-shadow: 2px 0 10px rgba(11, 42, 91, 0.04) !important;
    }

    /* Cabeçalho da sidebar recolhida: exibe a logo compacta centralizada no topo */
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarHeader"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarHeader"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 64px !important;
        min-height: 64px !important;
        padding: 0 !important;
        margin: 0 auto !important;
        visibility: visible !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarHeader"] img,
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarHeader"] img {
        display: block !important;
        visibility: visible !important;
        width: 38px !important;
        max-width: 38px !important;
        height: 38px !important;
        max-height: 38px !important;
        object-fit: contain !important;
        margin: 0 auto !important;
    }

    /* Links de navegação centralizados na faixa de 80px */
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNav"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNav"] {
        display: block !important;
        visibility: visible !important;
        padding-top: 14px !important;
        border-top: 1px solid rgba(11, 60, 122, 0.08) !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavItems"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavItems"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 12px !important;
        padding: 0 !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavItems"] li,
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavItems"] li {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        margin: 0 !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavLink"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 48px !important;
        height: 48px !important;
        padding: 0 !important;
        margin: 0 auto !important;
        border-radius: 12px !important;
        border: 1px solid transparent !important;
        font-size: 0 !important;
        transition: all 250ms cubic-bezier(0.2, 0.8, 0.2, 1) !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavLink"] *,
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] * {
        font-size: 1.45rem !important;
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
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"]:hover {
        background-color: rgba(0, 157, 187, 0.12) !important;
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
    [data-testid="stSidebar"]:not([data-collapsed="true"]):not([aria-expanded="false"]) {
        min-width: 295px !important;
    }
    [data-testid="stSidebarNavLink"] {
        padding: 0.60rem 0.85rem !important;
        border-radius: 8px !important;
        transition: all 250ms cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        border: 1px solid transparent !important;
    }
    [data-testid="stSidebarNavLink"] span {
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
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
       CONTEÚDO SECUNDÁRIO & RODAPÉ (EXPANDIDO)
       ======================================================== */
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
        height: 100% !important;
        overflow: visible !important;
    }
    [data-testid="stSidebarUserContent"] {
        display: flex !important;
        flex-direction: column !important;
        flex-grow: 1 !important;
        height: 100% !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
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

    /* Transição suave do conteúdo secundário e footer */
    [data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarUserContent"],
    [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"] {
        opacity: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
        max-height: 0 !important;
        overflow: hidden !important;
        transition: opacity 180ms ease, visibility 180ms !important;
    }
    [data-testid="stSidebar"]:not([data-collapsed="true"]):not([aria-expanded="false"]) [data-testid="stSidebarUserContent"] {
        opacity: 1 !important;
        visibility: visible !important;
        transition: opacity 320ms cubic-bezier(0.2, 0.8, 0.2, 1) 100ms !important;
    }

    /* ========================================================
       SEPARAÇÃO E RESPIRO DO CONTEÚDO PRINCIPAL
       ======================================================== */
    /* Quando a barra estiver recolhida (80px), dá margem e respiro generoso com transição perfeitamente sincronizada */
    section.main,
    [data-testid="stMain"] {
        transition: margin-left 350ms cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        will-change: margin-left;
    }
    [data-testid="stSidebar"][data-collapsed="true"] ~ section.main,
    [data-testid="stSidebar"][data-collapsed="true"] ~ [data-testid="stMain"],
    [data-testid="stSidebar"][aria-expanded="false"] ~ section.main,
    [data-testid="stSidebar"][aria-expanded="false"] ~ [data-testid="stMain"] {
        margin-left: 80px !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] ~ section.main [data-testid="stMainBlockContainer"],
    [data-testid="stSidebar"][data-collapsed="true"] ~ [data-testid="stMain"] [data-testid="stMainBlockContainer"],
    [data-testid="stSidebar"][data-collapsed="true"] ~ section.main .block-container,
    [data-testid="stSidebar"][data-collapsed="true"] ~ [data-testid="stMain"] .block-container,
    [data-testid="stSidebar"][aria-expanded="false"] ~ section.main [data-testid="stMainBlockContainer"],
    [data-testid="stSidebar"][aria-expanded="false"] ~ [data-testid="stMain"] [data-testid="stMainBlockContainer"],
    [data-testid="stSidebar"][aria-expanded="false"] ~ section.main .block-container,
    [data-testid="stSidebar"][aria-expanded="false"] ~ [data-testid="stMain"] .block-container {
        padding-left: 3.5rem !important;
        padding-right: 3.5rem !important;
        padding-top: 2rem !important;
        max-width: 1400px !important;
    }

    /* Quando a barra estiver expandida, mantém respiro harmônico com transição suave */
    .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        padding-top: 2rem !important;
        max-width: 1400px !important;
        transition: padding 350ms cubic-bezier(0.2, 0.8, 0.2, 1) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.logo(CAMINHO_DA_LOGO, size="large", icon_image=CAMINHO_DO_ICONE)
if esta_autenticado(st.session_state) and not validar_sessao_api(st.session_state):
    st.info("Sua sessão expirou ou não pôde ser validada. Entre novamente.")

if not esta_autenticado(st.session_state):
    pagina_login = st.Page(
        "pages/0_Login.py",
        title="Login",
        icon=":material/login:",
        default=True,
    )
    st.navigation([pagina_login], position="hidden").run()
elif precisa_trocar_senha(st.session_state):
    pagina_trocar_senha = st.Page(
        "pages/6_Trocar_Senha.py",
        title="Troca obrigatória de senha",
        icon=":material/key:",
        default=True,
    )
    st.navigation([pagina_trocar_senha], position="hidden").run()
else:
    usuario = obter_usuario_autenticado(st.session_state) or {}
    nivel = usuario.get("nivel", "")
    if nivel == "INSTITUCIONAL_WHATSAPP" and eh_conta_institucional_whatsapp(st.session_state):
        paginas = [
            st.Page(
                "pages/4_WhatsApp_Evolution.py",
                title="Conectar",
                icon=":material/chat:",
                default=True,
            )
        ]
    else:
        paginas = [
            st.Page(
                "pages/1_Triagem_Clinica.py",
                title="Triagem Clínica",
                icon=":material/stethoscope:",
                default=True,
            ),
            st.Page(
                "pages/3_Historico.py",
                title="Histórico",
                icon=":material/history:",
            ),
        ]
        if nivel in {NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO}:
            paginas.insert(
                1,
                st.Page(
                    "pages/2_Auditoria_Humana.py",
                    title="Auditoria",
                    icon=":material/verified_user:",
                ),
            )
        paginas.append(
            st.Page(
                "pages/5_Usuario.py",
                title="Usuário",
                icon=":material/person:",
            )
        )
        if nivel == NIVEL_ADMIN_GERAL:
            paginas.append(
                st.Page(
                    "pages/4_WhatsApp_Evolution.py",
                    title="Conectar WhatsApp",
                    icon=":material/chat:",
                )
            )

    exibir_barra_lateral()
    st.navigation(paginas).run()
