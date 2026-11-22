from pathlib import Path

import streamlit as st

from components.estilos import aplicar_css
from components.barra_lateral import (
    CAMINHO_DA_LOGO,
    CAMINHO_DO_ICONE,
    exibir_barra_lateral,
)
from services.autenticacao import (
    deslogar,
    esta_autenticado,
    obter_token_jwt,
    obter_usuario_autenticado,
    precisa_trocar_senha,
    restaurar_sessao_por_token,
    validar_sessao_api,
)
from services.browser_session import (
    limpar_token_persistido,
    obter_token_persistido,
    salvar_token_persistido,
)
from services.cookie_sessao import sincronizar_cookie_sessao
from utils.usuarios import NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO, eh_conta_institucional_whatsapp

st.set_page_config(page_title="MediFlow", layout="wide")
aplicar_css(Path(__file__).resolve().parent / "assets" / "app.css")
if esta_autenticado(st.session_state):
    st.logo(CAMINHO_DA_LOGO, size="large", icon_image=CAMINHO_DO_ICONE)

# Tenta restaurar a sessão a partir do cookie ou browser storage se não estiver na memória
if not esta_autenticado(st.session_state) and not st.session_state.get("logout_efetuado"):
    token_recuperado = None
    cookies = getattr(st.context, "cookies", {}) or {}
    token_cookie = cookies.get("mediflow_access_token")
    if token_cookie:
        token_recuperado = token_cookie
    else:
        token_browser = obter_token_persistido()
        if token_browser:
            token_recuperado = token_browser

    if token_recuperado:
        if restaurar_sessao_por_token(token_recuperado, st.session_state):
            st.session_state["cookie_sessao_migracao_pendente"] = True
            salvar_token_persistido(token_recuperado)

if esta_autenticado(st.session_state):
    token_ativo = obter_token_jwt(st.session_state)
    if token_ativo:
        salvar_token_persistido(token_ativo)

# Converte cookies legados criados pelo frontend em cookie HttpOnly emitido pela API.
if st.session_state.get("cookie_sessao_migracao_pendente"):
    token_sessao = obter_token_jwt(st.session_state)
    resultado_migracao = sincronizar_cookie_sessao(
        "definir",
        token=token_sessao,
        tentativa=0,
    )
    if resultado_migracao and resultado_migracao.get("ok"):
        st.session_state.pop("cookie_sessao_migracao_pendente", None)
    elif resultado_migracao and not resultado_migracao.get("ok"):
        st.session_state.pop("cookie_sessao_migracao_pendente", None)
        st.warning("A sessão atual foi restaurada, mas não foi possível atualizar a proteção do cookie.")

# Finaliza o cookie HttpOnly após o logout solicitado na interface.
if st.session_state.get("logout_efetuado"):
    tentativa_logout = st.session_state.get("logout_cookie_tentativa", 0)
    resultado_logout = sincronizar_cookie_sessao("limpar", tentativa=tentativa_logout)
    if resultado_logout and resultado_logout.get("ok"):
        st.session_state.pop("logout_efetuado", None)
        st.session_state.pop("logout_cookie_tentativa", None)
    elif resultado_logout and not resultado_logout.get("ok"):
        st.warning("Não foi possível remover o cookie da sessão. Verifique a conexão e tente novamente.")
        if st.button("Tentar sair novamente", key="tentar_limpar_cookie_sessao"):
            st.session_state["logout_cookie_tentativa"] = tentativa_logout + 1
            st.rerun()

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
        ]
        paginas.append(
            st.Page(
                "pages/analise.py",
                title="Análise",
                icon=":material/analytics:",
                url_path="analise",
            )
        )
        if nivel in {NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO, NIVEL_ENFERMEIRO}:
            paginas.append(
                st.Page(
                    "pages/2_Auditoria_Humana.py",
                    title="Revisão",
                    icon=":material/verified_user:",
                ),
            )
        paginas.append(
            st.Page(
                "pages/3_Historico.py",
                title="Histórico",
                icon=":material/history:",
            )
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
