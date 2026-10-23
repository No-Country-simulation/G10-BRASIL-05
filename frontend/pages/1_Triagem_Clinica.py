import streamlit as st

from components.cards import exibir_resultado_da_triagem
from services.api_client import enviar_documento
from utils.requisicao import (
    CANAIS_DE_ORIGEM,
    EXTENSOES_ACEITAS,
    OPCAO_ARQUIVO,
    OPCAO_TEXTO,
    montar_requisicao,
    validar_envio,
)

st.title("Triagem Clínica")
st.write("Envie um documento clínico para análise e roteamento automático.")

arquivo = None
texto_digitado = ""

coluna_envio, coluna_opcoes = st.columns([2, 1], gap="large")

with coluna_envio:
    fonte = st.radio(
        "Como deseja enviar o documento?",
        [OPCAO_ARQUIVO, OPCAO_TEXTO],
        horizontal=True,
    )
    if fonte == OPCAO_ARQUIVO:
        arquivo = st.file_uploader("Documento clínico", type=EXTENSOES_ACEITAS)
    else:
        texto_digitado = st.text_area("Texto do documento", height=200)

with coluna_opcoes:
    canal_origem = st.selectbox(
        "Canal de origem",
        CANAIS_DE_ORIGEM,
        index=None,
        placeholder="Selecione o canal",
    )
    analisar = st.button("Analisar documento", type="primary")

if analisar:
    problema = validar_envio(fonte, arquivo, texto_digitado, canal_origem)
    if problema:
        st.warning(problema)
        st.stop()

    try:
        requisicao = montar_requisicao(arquivo, texto_digitado, canal_origem)
    except ValueError as erro:
        st.error(str(erro))
        st.stop()

    with st.spinner("Analisando documento..."):
        resposta = enviar_documento(requisicao)

    st.caption(
        f"Documento analisado: {resposta.get('documento_id') or 'sem identificação'}"
        f" · Canal de origem: {requisicao['canal_origem']}"
    )
    exibir_resultado_da_triagem(resposta)