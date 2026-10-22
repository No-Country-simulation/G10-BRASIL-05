import streamlit as st

from services.api_client import enviar_documento
from utils.requisicao import CANAIS_DE_ORIGEM, EXTENSOES_ACEITAS, montar_requisicao

st.title("Triagem Clínica")
st.write("Envie um documento clínico para análise e roteamento automático.")

coluna_envio, coluna_opcoes = st.columns([2, 1], gap="large")

with coluna_envio:
    arquivo = st.file_uploader("Documento clínico", type=EXTENSOES_ACEITAS)
    texto_digitado = st.text_area("Ou cole o texto do documento", height=200)

with coluna_opcoes:
    canal_origem = st.selectbox("Canal de origem", CANAIS_DE_ORIGEM)
    analisar = st.button("Analisar documento", type="primary")

if analisar:
    if arquivo is None and not texto_digitado.strip():
        st.warning("Envie um arquivo ou cole o texto do documento.")
        st.stop()

    try:
        requisicao = montar_requisicao(arquivo, texto_digitado, canal_origem)
    except ValueError as erro:
        st.error(str(erro))
        st.stop()

    with st.spinner("Analisando documento..."):
        resposta = enviar_documento(requisicao)

    st.json(resposta)