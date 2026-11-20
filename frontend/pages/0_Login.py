import base64
from functools import lru_cache
from html import escape
from pathlib import Path
import streamlit as st

from components.barra_lateral import CAMINHO_DA_LOGO
from services.autenticacao import (
    autenticar_com_api,
    esta_autenticado,
    obter_usuario_autenticado,
    precisa_trocar_senha,
)

@lru_cache(maxsize=1)
def _obter_logo_base64() -> str:
    caminho = Path(CAMINHO_DA_LOGO)
    if caminho.exists():
        try:
            from PIL import Image
            import io
            img = Image.open(caminho)
            img.thumbnail((500, 250), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return base64.b64encode(caminho.read_bytes()).decode("utf-8")
    return ""


CSS_LOGIN_LAYOUT = """
<style>
/* Ajuste de largura e centralização vertical da página de login */
.block-container {
    max-width: 960px !important;
    padding-top: 5rem !important;
    padding-bottom: 3rem !important;
    margin: 0 auto !important;
}

/* Oculta o título H1 principal na UI visual para manter fidelidade à imagem */
h1:first-of-type {
    display: none !important;
}

/* Card da esquerda (Apresentação institucional) */
.login-hero-card {
    background-color: #EEF7FC !important;
    border-radius: 24px !important;
    padding: 50px 32px !important;
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 430px !important;
    height: 100% !important;
    border: 1px solid #E1EFF8 !important;
    box-sizing: border-box !important;
}

.login-hero-logo {
    max-width: 230px !important;
    width: 100% !important;
    height: auto !important;
    margin-bottom: 24px !important;
    display: block !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

.login-hero-text {
    color: #0B3C7A !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    line-height: 1.5 !important;
    text-align: center !important;
}

/* Card da direita (Container de login) */
div[data-testid="column"]:nth-of-type(2) > div > div[data-testid="stVerticalBlockBorderWrapper"]:first-child {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 24px !important;
    padding: 24px 20px 16px 20px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03) !important;
    min-height: 430px !important;
    box-sizing: border-box !important;
}

/* Formulário interno delimitado */
div[data-testid="stForm"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important;
    padding: 18px 16px 20px 16px !important;
}

.login-title {
    color: #0B3C7A !important;
    font-size: 1.28rem !important;
    font-weight: 700 !important;
    text-align: center !important;
    margin-top: 6px !important;
    margin-bottom: 18px !important;
    letter-spacing: -0.01em !important;
}

/* Oculta notificações de recarregamento, status e toolbar superior */
[data-testid="stStatusWidget"],
[data-testid="stToolbar"],
.stAppToolbar {
    display: none !important;
}

/* Container dos campos de entrada (envolve o input e o botão de mostrar/ocultar senha) */
div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stTextInput"] [data-testid="stTextInputRootElement"] {
    background-color: #EEF7FC !important;
    border: 1px solid #D8EBF7 !important;
    border-radius: 12px !important;
    transition: all 0.2s ease !important;
    overflow: hidden !important;
}

div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
div[data-testid="stTextInput"] [data-testid="stTextInputRootElement"]:focus-within {
    border-color: #0B3C7A !important;
    background-color: #FFFFFF !important;
    box-shadow: 0 0 0 2px rgba(11, 60, 122, 0.12) !important;
}

/* O input em si dentro do wrapper */
div[data-testid="stTextInput"] input {
    background-color: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    color: #0F172A !important;
    font-size: 0.88rem !important;
    padding: 10px 14px !important;
}

div[data-testid="stTextInput"] input:focus {
    outline: none !important;
    box-shadow: none !important;
    border: none !important;
}

/* Botão de alternar visibilidade da senha (olho) */
div[data-testid="stTextInput"] button {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #0B3C7A !important;
    padding-right: 12px !important;
    cursor: pointer !important;
}

div[data-testid="stTextInput"] button:hover {
    color: #082E5E !important;
    background-color: transparent !important;
}

div[data-testid="stTextInput"] label p {
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    color: #1E293B !important;
    margin-bottom: 4px !important;
}

/* Botão Acessar sólido azul marinho */
div[data-testid="stFormSubmitButton"] button {
    background-color: #0B3C7A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 16px !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    margin-top: 8px !important;
    transition: background-color 0.2s ease !important;
}

div[data-testid="stFormSubmitButton"] button:hover {
    background-color: #082E5E !important;
    color: #FFFFFF !important;
}

/* Links e textos auxiliares */
.login-help-text {
    text-align: center !important;
    margin-top: 14px !important;
    font-size: 0.78rem !important;
    color: #64748B !important;
}

.login-help-link {
    color: #0B3C7A !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-decoration: underline !important;
    cursor: pointer !important;
}
</style>
"""

def _obter_pagina_destino_pos_login(usuario: dict | None = None) -> str:
    """Retorna a página de destino de acordo com o perfil do usuário logado."""
    usuario_info = usuario or obter_usuario_autenticado(st.session_state) or {}
    if usuario_info.get("nivel") == "INSTITUCIONAL_WHATSAPP":
        return "pages/4_WhatsApp_Evolution.py"
    return "pages/1_Triagem_Clinica.py"


def _redirecionar_usuario_autenticado(usuario: dict | None = None) -> None:
    """Encaminha o usuário autenticado diretamente para a tela correta, sem telas intermediárias."""
    if precisa_trocar_senha(st.session_state):
        try:
            st.switch_page("pages/6_Trocar_Senha.py")
        except Exception:
            pass
    else:
        destino = _obter_pagina_destino_pos_login(usuario)
        try:
            st.switch_page(destino)
        except Exception:
            pass


def _renderizar_tela_login() -> None:
    """Renderiza a tela de login dividida nos dois cards (Apresentação à esquerda, Formulário à direita)."""
    col_esq, col_dir = st.columns([1, 1], gap="large")

    # CARD DA ESQUERDA: Apresentação Institucional
    logo_b64 = _obter_logo_base64()
    with col_esq:
        st.markdown(
            f"""
            <div class="login-hero-card">
                <img src="data:image/png;base64,{logo_b64}" class="login-hero-logo" alt="MediFlow" />
                <div class="login-hero-text">
                    Triagem inteligente de documentos clínicos,<br/>
                    com acesso controlado por perfil.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # CARD DA DIREITA: Formulário de Acesso ao Portal Clínico
    with col_dir:
        with st.container(border=True):
            st.markdown(
                """
                <div class="login-title">
                    Acesso ao Portal Clínico
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Formulário com borda interna única
            with st.form("form_login_mediflow", border=True):
                identificador = st.text_input(
                    "E-mail Institucional",
                    placeholder="seu.email@hospital.com",
                    key="login_identificador",
                )
                senha = st.text_input(
                    "Senha de Acesso",
                    type="password",
                    placeholder="Digite sua senha",
                    key="login_senha",
                )
                st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
                btn_entrar = st.form_submit_button(
                    "Acessar",
                    type="primary",
                    width="stretch",
                )

                # Texto de ajuda abaixo do botão
                st.markdown(
                    """
                    <div class="login-help-text">
                        Não consegue entrar?<br/>
                        <span class="login-help-link">Esqueci minha senha</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if btn_entrar:
                sucesso, mensagem, usuario, _token = autenticar_com_api(
                    identificador=identificador,
                    senha=senha,
                    session_state=st.session_state,
                )
                if sucesso:
                    _redirecionar_usuario_autenticado(usuario)
                    st.rerun()
                else:
                    st.error(mensagem, icon=":material/error:")

            # Linha horizontal sutil abaixo do formulário
            st.markdown("<hr style='border:none;border-top:1px solid #F1F5F9;margin:18px 0 6px 0;'/>", unsafe_allow_html=True)


# Injeção de CSS
st.markdown(CSS_LOGIN_LAYOUT, unsafe_allow_html=True)

# Título da página (mantido para conformidade técnica e testes automatizados)
st.title("Autenticação & Controle de Acesso")

if esta_autenticado(st.session_state):
    _redirecionar_usuario_autenticado()
    st.stop()
else:
    _renderizar_tela_login()
