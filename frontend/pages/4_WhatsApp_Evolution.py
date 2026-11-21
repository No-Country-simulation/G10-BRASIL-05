import logging

import streamlit as st

from components.erros import chamar_api_ou_parar
from api.cliente_whatsapp import (
    desconectar_whatsapp,
    enviar_teste_whatsapp,
    gerar_qrcode_whatsapp,
    obter_status_whatsapp,
)
from utils.whatsapp import (
    NIVEL_AVISO,
    NIVEL_SUCESSO,
    decodificar_qrcode,
    descrever_conexao,
    normalizar_numero,
    validar_numero,
)

CHAVE_DO_QR_CODE = "whatsapp_qr_code"
CHAVE_DO_AVISO = "whatsapp_aviso"
MENSAGEM_DE_TESTE = "🏥 *MediFlow:* teste de comunicação via WhatsApp."
logger = logging.getLogger(__name__)

st.title("Conectar WhatsApp")
st.write(
    "Gerencie a conexão do bot de triagem clínica com o WhatsApp. "
    "Escaneie o QR Code para conectar e habilitar o recebimento automático de laudos e exames."
)

aviso = st.session_state.pop(CHAVE_DO_AVISO, None)
if aviso:
    st.toast(aviso, icon="ℹ️")

status = chamar_api_ou_parar(obter_status_whatsapp)
conectado = bool(status.get("conectado"))
nivel, titulo, ajuda = descrever_conexao(status)

coluna_status, _ = st.columns([1, 1], gap="large")

with coluna_status:
    st.subheader("Estado da conexão")
    if nivel == NIVEL_SUCESSO:
        st.success(f"**{titulo}**")
        st.caption(f"Instância: {status.get('instancia', '-')}")
    elif nivel == NIVEL_AVISO:
        st.warning(f"**{titulo}**")
    else:
        st.error(f"**{titulo}**")
    if ajuda:
        st.caption(ajuda)

    if conectado and st.button("Desconectar WhatsApp"):
        with st.spinner("Desconectando..."):
            chamar_api_ou_parar(desconectar_whatsapp)
        st.session_state.pop(CHAVE_DO_QR_CODE, None)
        st.session_state[CHAVE_DO_AVISO] = "Sessão do WhatsApp desconectada."
        st.rerun()

if not conectado:
    st.divider()
    st.subheader("Conectar dispositivo")
    st.markdown(
        "1. No celular (use um **número de teste**), abra o **WhatsApp**.\n"
        "2. Vá em **Aparelhos conectados** e toque em **Conectar um aparelho**.\n"
        "3. Clique em **Gerar QR Code** e aponte a câmera para a imagem."
    )
    if st.button("Gerar QR Code", type="primary"):
        logger.info("Clique em Gerar QR Code recebido pelo frontend.")
        with st.spinner("Obtendo o QR Code..."):
            resultado = chamar_api_ou_parar(gerar_qrcode_whatsapp)
        if resultado.get("conectado"):
            st.session_state[CHAVE_DO_AVISO] = "O WhatsApp já estava conectado."
            st.rerun()
        st.session_state[CHAVE_DO_QR_CODE] = resultado["base64"]

    qr_code = st.session_state.get(CHAVE_DO_QR_CODE)
    if qr_code:
        try:
            st.image(decodificar_qrcode(qr_code), caption="Escaneie no WhatsApp", width=280)
        except ValueError as erro:
            st.error(str(erro))

st.divider()
st.subheader("Mensagem de teste")

coluna_numero, coluna_texto = st.columns([1, 2])
with coluna_numero:
    numero = st.text_input("Número de destino (DDI + DDD + número)", placeholder="5511999999999")
with coluna_texto:
    texto = st.text_area("Texto", value=MENSAGEM_DE_TESTE)

if st.button("Enviar mensagem de teste"):
    problema = validar_numero(numero)
    if problema is None and not texto.strip():
        problema = "Escreva o texto da mensagem."
    if problema:
        st.warning(problema)
        st.stop()
    with st.spinner("Enviando..."):
        chamar_api_ou_parar(enviar_teste_whatsapp, normalizar_numero(numero), texto.strip())
    st.toast(f"Mensagem enviada para {normalizar_numero(numero)}.", icon="✅")
