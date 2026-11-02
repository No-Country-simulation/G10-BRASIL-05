import base64
import streamlit as st

from services.api_client import (
    obter_status_whatsapp,
    obter_qrcode_whatsapp,
    configurar_webhook_whatsapp,
    enviar_teste_whatsapp,
    desconectar_whatsapp,
)

st.set_page_config(page_title="WhatsApp - MediFlow", page_icon="📲", layout="wide")

st.title("📲 Integração WhatsApp (Evolution API)")
st.write(
    "Gerencie a conexão do bot de triagem clínica com o WhatsApp. "
    "Escaneie o QR Code para conectar e habilitar o recebimento automático de laudos e exames."
)

st.divider()

# Colunas para layout principal
col_status, col_acoes = st.columns([1, 1], gap="medium")

# 1. Consulta Status Atual
with col_status:
    st.subheader("Estado da Conexão")
    status_dados = obter_status_whatsapp()

    conectado = status_dados.get("conectado", False)
    estado = status_dados.get("estado", "desconhecido")
    instancia = status_dados.get("instancia", "mediflow")

    if conectado:
        st.success("🟢 **WHATSAPP CONECTADO E ONLINE**")
        st.info(f"Instância: **{instancia}** · Estado: **{estado.upper()}**")
    elif estado == "connecting":
        st.warning("🟡 **AGUARDANDO LEITURA DO QR CODE**")
        st.caption("A sessão está ativa aguardando o escaneamento no celular.")
    else:
        st.error(f"🔴 **DESCONECTADO** (Estado: {estado})")
        st.caption("A instância precisa ser conectada escaneando o QR Code abaixo.")

    if st.button("🔄 Atualizar Status", key="btn_refresh_status"):
        st.rerun()

    if conectado:
        if st.button("🚪 Desconectar WhatsApp", type="secondary"):
            with st.spinner("Desconectando..."):
                resp = desconectar_whatsapp()
                st.warning("Sessão desconectada.")
                st.rerun()

with col_acoes:
    st.subheader("Configuração do Webhook")
    url_webhook_default = "http://172.24.0.1:8000/webhook/evolution?token=mediflow_webhook_token"
    webhook_url_input = st.text_input(
        "URL de Destino do Webhook",
        value=url_webhook_default,
        help="URL onde a Evolution API enviará os eventos MESSAGES_UPSERT para o MediFlow.",
    )

    if st.button("⚙️ Salvar / Ativar Webhook", type="secondary"):
        with st.spinner("Configurando webhook na Evolution API..."):
            res_hook = configurar_webhook_whatsapp(webhook_url_input)
            if res_hook.get("sucesso"):
                st.success("Webhook configurado com sucesso!")
            else:
                st.error(f"Falha ao configurar webhook: {res_hook.get('erro')}")

st.divider()

# 2. Seção do QR Code
st.subheader("📲 Conectar Dispositivo (QR Code)")

if conectado:
    st.success("🎉 O aparelho já está pareado! Para reconectar ou trocar de número, clique em 'Desconectar WhatsApp' acima.")
else:
    st.write(
        "Siga os passos abaixo para conectar o WhatsApp de triagem clínica:\n"
        "1. No seu celular (use um **número/chip de teste**), abra o **WhatsApp**.\n"
        "2. Acesse **Configurações** (ou 3 pontinhos) ➡️ **Aparelhos Conectados** ➡️ **Conectar um aparelho**.\n"
        "3. Clique no botão abaixo para gerar o QR Code e aponte a câmera do celular."
    )

    col_qr, col_instrucoes = st.columns([1, 1], gap="large")

    with col_qr:
        if st.button("📷 Gerar / Atualizar QR Code", type="primary", key="btn_get_qr"):
            with st.spinner("Obtendo QR Code da Evolution API..."):
                resultado_qr = obter_qrcode_whatsapp()

                if resultado_qr.get("conectado"):
                    st.success("WhatsApp já conectado!")
                    st.rerun()
                elif resultado_qr.get("sucesso") and resultado_qr.get("base64"):
                    st.session_state["qr_base64"] = resultado_qr["base64"]
                    st.session_state["qr_code_raw"] = resultado_qr.get("code")
                else:
                    st.error(
                        f"Não foi possível obter o QR Code. "
                        f"Certifique-se de que a Evolution API está em execução no Docker. "
                        f"Detalhe: {resultado_qr.get('erro', 'Instância indisponível')}"
                    )

        # Exibe o QR Code persistido no estado da sessão se disponível
        if "qr_base64" in st.session_state:
            qr_b64 = st.session_state["qr_base64"]
            # Limpa prefixo caso exista
            if "base64," in qr_b64:
                qr_b64 = qr_b64.split("base64,")[1]

            try:
                img_bytes = base64.b64decode(qr_b64)
                st.image(img_bytes, caption="Escaneie este QR Code no WhatsApp", width=280)
                st.info("Após escanear no celular, clique no botão '🔄 Atualizar Status' acima.")
            except Exception as e:
                st.warning(f"Erro ao renderizar imagem do QR Code: {e}")

    with col_instrucoes:
        st.markdown(
            """
            > **⚠️ Dica de Segurança:**  
            > Utilize sempre um número ou chip dedicado para homologação de testes.  
            > O fluxo de triagem responde automaticamente assim que um exame (PDF ou Imagem) for recebido!
            """
        )

st.divider()

# 3. Teste Manual de Envio
st.subheader("🧪 Teste de Envio de Mensagem")
st.write("Teste o disparo de mensagem para confirmar a integridade de envio do WhatsApp.")

col_t1, col_t2 = st.columns([1, 2])
with col_t1:
    numero_teste = st.text_input("Número de Destino (DDI + DDD + Número)", value="55", placeholder="Ex: 5511999999999")
with col_t2:
    msg_teste = st.text_area("Texto de Teste", value="🏥 *MediFlow:* Teste de comunicação via WhatsApp concluído com sucesso!")

if st.button("📤 Disparar Mensagem de Teste"):
    if len(numero_teste.strip()) < 10:
        st.warning("Por favor, informe um número válido com DDI e DDD (ex: 5511999999999).")
    else:
        with st.spinner("Enviando mensagem..."):
            res_envio = enviar_teste_whatsapp(numero_teste.strip(), msg_teste)
            if res_envio.get("sucesso"):
                st.success(f"Mensagem enviada com sucesso para {numero_teste}!")
            else:
                st.error(f"Falha ao enviar mensagem: {res_envio.get('erro')}")
