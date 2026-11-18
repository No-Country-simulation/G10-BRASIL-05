import streamlit as st

from services.erros import ErroDeApi

ICONE_DE_ERRO = ":material/error:"


def chamar_api_ou_parar(chamada, *argumentos, complemento: str | None = None, **opcoes):
    try:
        return chamada(*argumentos, **opcoes)
    except ErroDeApi as erro:
        st.error(f"{erro} {complemento}" if complemento else str(erro), icon=ICONE_DE_ERRO)
        st.stop()
