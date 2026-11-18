import streamlit as st

from services.configuracao import obter_url_do_backend, usar_dados_simulados
from services.erros import ErroDeConfiguracao

AVISO_DA_PAGINA = (
    "Dados fictícios para teste. Nenhum documento é processado, salvo ou enviado para auditoria ou WhatsApp."
)


def validar_configuracao_frontend() -> None:
    if _usar_mock_ou_interromper():
        return
    try:
        obter_url_do_backend()
    except ErroDeConfiguracao as erro:
        st.error(str(erro))
        st.stop()


def exibir_aviso_de_dados_ficticios() -> None:
    if _usar_mock_ou_interromper():
        st.warning(AVISO_DA_PAGINA, icon="ℹ️")


def _usar_mock_ou_interromper() -> bool:
    try:
        return usar_dados_simulados()
    except ErroDeConfiguracao as erro:
        st.error(str(erro))
        st.stop()
