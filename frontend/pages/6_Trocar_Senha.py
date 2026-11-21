import streamlit as st

from services.autenticacao import deslogar, trocar_senha_inicial


CSS_TROCA_SENHA = """
<style>
/* Centralização e largura confortável da página */
.block-container {
    max-width: 880px !important;
    padding-top: 3.5rem !important;
    padding-bottom: 3rem !important;
    margin: 0 auto !important;
}

/* Oculta toolbar e status padrão */
[data-testid="stStatusWidget"],
[data-testid="stToolbar"],
.stAppToolbar {
    display: none !important;
}

/* Título principal */
.troca-senha-titulo {
    color: #0B2A5B !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    margin-bottom: 1.25rem !important;
    letter-spacing: -0.01em !important;
}

/* Faixa de aviso azul claro */
.troca-senha-aviso {
    background-color: #EEF7FC !important;
    color: #0B3C7A !important;
    border: 1px solid #D8EBF7 !important;
    border-radius: 12px !important;
    padding: 14px 20px !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    margin-bottom: 1.5rem !important;
    line-height: 1.4 !important;
}

/* Card delimitado do formulário */
div[data-testid="stForm"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important;
    padding: 24px 24px 20px 24px !important;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.02) !important;
}

/* Campos de entrada com fundo azul claro e borda suave */
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

div[data-testid="stTextInput"] input {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #0F172A !important;
    font-size: 0.90rem !important;
    padding: 10px 14px !important;
}

div[data-testid="stTextInput"] label p {
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    color: #1E293B !important;
    margin-bottom: 4px !important;
}

/* Botão de salvar */
div[data-testid="stFormSubmitButton"] button {
    background-color: #0B3C7A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 20px !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    margin-top: 10px !important;
    transition: background-color 0.2s ease !important;
}

div[data-testid="stFormSubmitButton"] button:hover {
    background-color: #082E5E !important;
    color: #FFFFFF !important;
}
</style>
"""

st.markdown(CSS_TROCA_SENHA, unsafe_allow_html=True)

# Título e aviso conforme identidade visual solicitada
st.markdown(
    """
    <div class="troca-senha-titulo">Troca obrigatória de senha</div>
    <div class="troca-senha-aviso">
        Antes de continuar, defina uma senha pessoal com pelo menos 12 caracteres.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("form_trocar_senha_inicial", border=True):
    senha_atual = st.text_input(
        "Senha temporária",
        type="password",
        placeholder="Digite sua senha temporária",
        key="troca_senha_temporaria",
    )
    nova_senha = st.text_input(
        "Nova senha",
        type="password",
        placeholder="Mínimo de 12 caracteres",
        key="troca_nova_senha",
    )
    confirmar = st.text_input(
        "Confirme a nova senha",
        type="password",
        placeholder="Repita a nova senha",
        key="troca_confirmar_senha",
    )

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    enviar = st.form_submit_button("Salvar nova senha", type="primary")

if enviar:
    if not senha_atual:
        st.error("Informe a senha temporária.", icon=":material/lock:")
    elif not nova_senha:
        st.error("Informe a nova senha.", icon=":material/key:")
    elif len(nova_senha) < 12:
        st.error("A nova senha precisa ter pelo menos 12 caracteres.", icon=":material/warning:")
    elif nova_senha != confirmar:
        st.error("As novas senhas não coincidem.", icon=":material/warning:")
    elif nova_senha == senha_atual:
        st.error("A nova senha deve ser diferente da senha temporária.", icon=":material/warning:")
    else:
        with st.spinner("Atualizando sua senha com segurança..."):
            sucesso, mensagem = trocar_senha_inicial(
                senha_atual,
                nova_senha,
                st.session_state,
            )
        if sucesso:
            st.success(mensagem, icon=":material/check_circle:")
            st.rerun()
        else:
            st.error(mensagem, icon=":material/error:")

# Opção auxiliar de logout
st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
_, col_logout = st.columns([3, 1])
with col_logout:
    if st.button("Sair da conta", icon=":material/logout:", type="secondary", use_container_width=True):
        deslogar(st.session_state)
        st.rerun()
