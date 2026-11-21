"""Fluxo de interface da tela login."""

def render() -> None:
    from components.estilos import aplicar_css
    import base64
    from functools import lru_cache
    from html import escape
    from pathlib import Path
    import streamlit as st
    import streamlit.components.v1 as components

    from components.barra_lateral import CAMINHO_DA_LOGO
    from services.autenticacao import (
        autenticar_com_api,
        esta_autenticado,
        obter_token_jwt,
        obter_usuario_autenticado,
        precisa_trocar_senha,
    )
    from services.cookie_sessao import sincronizar_cookie_sessao

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
                    sucesso, mensagem, _usuario, _token_jwt = autenticar_com_api(
                        identificador=identificador,
                        senha=senha,
                        session_state=st.session_state,
                    )
                    if sucesso:
                        st.session_state["cookie_login_pendente"] = True
                    else:
                        st.error(mensagem, icon=":material/error:")

                if st.session_state.get("cookie_login_pendente"):
                    token_sessao = obter_token_jwt(st.session_state)
                    tentativa_cookie = st.session_state.get("cookie_login_tentativa", 0)
                    resultado_cookie = sincronizar_cookie_sessao(
                        "definir",
                        token=token_sessao,
                        tentativa=tentativa_cookie,
                    )
                    if resultado_cookie and resultado_cookie.get("ok"):
                        st.session_state.pop("cookie_login_pendente", None)
                        st.session_state.pop("cookie_login_tentativa", None)
                        _redirecionar_usuario_autenticado()
                        st.rerun()
                    elif resultado_cookie and not resultado_cookie.get("ok"):
                        st.error("Não foi possível proteger a sessão no navegador.")
                        if st.button("Tentar novamente", key="tentar_definir_cookie_sessao"):
                            st.session_state["cookie_login_tentativa"] = tentativa_cookie + 1
                            st.rerun()

                # Linha horizontal sutil abaixo do formulário
                st.markdown("<hr style='border:none;border-top:1px solid #F1F5F9;margin:18px 0 6px 0;'/>", unsafe_allow_html=True)


    # Injeção de CSS
    aplicar_css(Path(__file__).with_name("style.css"))

    # Título da página (mantido para conformidade técnica e testes automatizados)
    st.title("Autenticação & Controle de Acesso")

    if esta_autenticado(st.session_state) and not st.session_state.get("cookie_login_pendente"):
        _redirecionar_usuario_autenticado()
        st.stop()
    else:
        _renderizar_tela_login()
