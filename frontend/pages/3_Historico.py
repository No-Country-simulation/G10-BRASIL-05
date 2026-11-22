"""Ponto de entrada Streamlit da tela de histórico."""
import streamlit as st
from services.autenticacao import esta_autenticado

if not esta_autenticado(st.session_state):
    st.switch_page("app.py")
    st.stop()

from telas.historico.index import render

render()
