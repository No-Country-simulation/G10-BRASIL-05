import streamlit as st

from services.erros import ErroDeApi


def chamar_api_ou_parar(chamada, *argumentos, complemento: str | None = None, **opcoes):
    try:
        return chamada(*argumentos, **opcoes)
    except ErroDeApi as erro:
        st.error(f"{erro} {complemento}" if complemento else str(erro))
        st.stop()
