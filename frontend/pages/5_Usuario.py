import streamlit as st

from services.api_client import (
    atualizar_usuario,
    desativar_usuario,
    listar_usuarios,
    provisionar_usuario,
)
from services.autenticacao import obter_usuario_autenticado
from services.erros import ErroDeApi
from utils.usuarios import NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_ENFERMEIRO, NIVEL_MEDICO, ROTULOS_DE_NIVEL


st.title("Usuário & Controle de Acesso")
usuario_atual = obter_usuario_autenticado(st.session_state) or {}
nivel_atual = usuario_atual.get("nivel")

st.subheader("Meu perfil")
col_nome, col_papel, col_email = st.columns(3)
col_nome.metric("Nome", usuario_atual.get("nome", "—"))
col_papel.metric("Perfil", ROTULOS_DE_NIVEL.get(nivel_atual, nivel_atual or "—"))
col_email.metric("E-mail", usuario_atual.get("email", "—"))

if nivel_atual not in {NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO}:
    st.info("A administração de contas é restrita a Diretores Clínicos e Médicos autorizados.")
    st.stop()

try:
    usuarios = listar_usuarios()
except ErroDeApi as erro:
    st.error(str(erro))
    st.stop()

st.divider()
st.subheader("Contas profissionais provisionadas")
if usuarios:
    st.dataframe(
        [
            {
                "Código": usuario["id"],
                "Nome": usuario["nome"],
                "E-mail": usuario["email"],
                "Perfil": ROTULOS_DE_NIVEL.get(usuario["nivel"], usuario["nivel"]),
                "Registro": usuario.get("registro", ""),
                "Especialidade": usuario.get("especialidade", ""),
            }
            for usuario in usuarios
        ],
        hide_index=True,
        use_container_width=True,
    )
else:
    st.caption("Ainda não há contas profissionais ativas além da sua.")

if nivel_atual == NIVEL_MEDICO:
    opcoes_papel = [NIVEL_ENFERMEIRO]
elif nivel_atual == NIVEL_ADMIN_GERAL:
    opcoes_papel = [NIVEL_DIRETOR, NIVEL_MEDICO, NIVEL_ENFERMEIRO]
else:
    opcoes_papel = [NIVEL_MEDICO, NIVEL_ENFERMEIRO]
with st.expander("Provisionar nova conta", expanded=False):
    with st.form("form_provisionar_usuario"):
        nome = st.text_input("Nome completo")
        email = st.text_input("E-mail institucional")
        papel = st.selectbox(
            "Perfil",
            opcoes_papel,
            format_func=lambda item: ROTULOS_DE_NIVEL[item],
        )
        registro = st.text_input("Registro profissional (opcional)")
        especialidade = st.text_input("Departamento ou especialidade (opcional)")
        senha = st.text_input("Senha inicial (mínimo 12 caracteres)", type="password")
        confirmar_senha = st.text_input("Confirmar senha", type="password")
        enviar = st.form_submit_button("Provisionar conta", type="primary")
    if enviar:
        if senha != confirmar_senha:
            st.error("As senhas não coincidem.")
        else:
            try:
                provisionar_usuario(
                    {
                        "nome": nome,
                        "email": email,
                        "senha": senha,
                        "nivel": papel,
                        "registro": registro,
                        "especialidade": especialidade,
                    }
                )
            except ErroDeApi as erro:
                st.error(str(erro))
            else:
                st.success("Conta provisionada com sucesso.")
                st.rerun()

if usuarios:
    st.divider()
    st.subheader("Atualizar ou desativar conta")
    mapa_usuarios = {f'{item["nome"]} — {item["email"]}': item for item in usuarios}
    rotulo = st.selectbox("Conta", list(mapa_usuarios))
    alvo = mapa_usuarios[rotulo]
    id_numerico = int(alvo["id"].split("-")[-1])
    with st.form("form_atualizar_usuario"):
        novo_nome = st.text_input("Nome", value=alvo["nome"])
        novo_email = st.text_input("E-mail", value=alvo["email"])
        novo_papel = st.selectbox(
            "Perfil",
            opcoes_papel,
            index=opcoes_papel.index(alvo["nivel"]) if alvo["nivel"] in opcoes_papel else 0,
            format_func=lambda item: ROTULOS_DE_NIVEL[item],
        )
        novo_registro = st.text_input("Registro profissional", value=alvo.get("registro", ""))
        nova_especialidade = st.text_input("Departamento ou especialidade", value=alvo.get("especialidade", ""))
        senha_nova = st.text_input("Nova senha (opcional; mínimo 12 caracteres)", type="password")
        salvar = st.form_submit_button("Salvar alterações")
    if salvar:
        dados = {
            "nome": novo_nome,
            "email": novo_email,
            "nivel": novo_papel,
            "registro": novo_registro,
            "especialidade": nova_especialidade,
        }
        if senha_nova:
            dados["senha"] = senha_nova
        try:
            atualizar_usuario(id_numerico, dados)
        except ErroDeApi as erro:
            st.error(str(erro))
        else:
            st.success("Conta atualizada.")
            st.rerun()
    if alvo["id"] != usuario_atual.get("id") and st.button("Desativar conta selecionada", type="secondary"):
        try:
            desativar_usuario(id_numerico)
        except ErroDeApi as erro:
            st.error(str(erro))
        else:
            st.success("Conta desativada.")
            st.rerun()
