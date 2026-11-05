import streamlit as st

from components.erros import chamar_api_ou_parar
from services.api_client import (
    configurar_webhook_whatsapp,
    desconectar_whatsapp,
    enviar_teste_whatsapp,
    gerar_qrcode_whatsapp,
    obter_status_whatsapp,
)
from services.configuracao import usar_dados_simulados
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

st.title("Conectar WhatsApp")
st.write(
    "Gerencie a conexão do bot de triagem clínica com o WhatsApp. "
    "Escaneie o QR Code para conectar e habilitar o recebimento automático de laudos e exames."
)

if usar_dados_simulados():
    st.info("A integração com o WhatsApp não está disponível no modo demonstração.")
    st.stop()

aviso = st.session_state.pop(CHAVE_DO_AVISO, None)
if aviso:
    st.success(aviso)

status = chamar_api_ou_parar(obter_status_whatsapp)
conectado = bool(status.get("conectado"))
nivel, titulo, ajuda = descrever_conexao(status)

coluna_status, coluna_webhook = st.columns(2, gap="large")

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

    if st.button("Atualizar status"):
        st.rerun()

    if conectado and st.button("Desconectar WhatsApp"):
        with st.spinner("Desconectando..."):
            chamar_api_ou_parar(desconectar_whatsapp)
        st.session_state.pop(CHAVE_DO_QR_CODE, None)
        st.session_state[CHAVE_DO_AVISO] = "Sessão do WhatsApp desconectada."
        st.rerun()

with coluna_webhook:
    st.subheader("Webhook")
    url_do_webhook = st.text_input(
        "URL do webhook (opcional)",
        help=(
            "Deixe em branco para usar a URL padrão do backend. Se a Evolution API não alcançar "
            "essa URL, informe o endereço do backend visível para o container, com o token do webhook."
        ),
    )
    if st.button("Salvar e ativar webhook"):
        with st.spinner("Configurando o webhook..."):
            chamar_api_ou_parar(configurar_webhook_whatsapp, url_do_webhook.strip() or None)
        st.success("Webhook configurado.")

st.divider()
st.subheader("Conectar dispositivo")

if conectado:
    st.success("O aparelho já está pareado. Para trocar de número, desconecte o WhatsApp acima.")
else:
    st.markdown(
        "1. No celular (use um **número de teste**), abra o **WhatsApp**.\n"
        "2. Vá em **Aparelhos conectados** e toque em **Conectar um aparelho**.\n"
        "3. Clique em **Gerar QR Code** e aponte a câmera para a imagem."
    )
    if st.button("Gerar QR Code", type="primary"):
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
        else:
            st.info("Depois de escanear, clique em **Atualizar status**.")

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
    st.success(f"Mensagem enviada para {normalizar_numero(numero)}.")
