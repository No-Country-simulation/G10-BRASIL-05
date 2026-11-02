import streamlit as st

from components.barra_lateral import exibir_barra_lateral

st.set_page_config(page_title="MediFlow", layout="wide")

paginas = [
    st.Page("pages/1_Triagem_Clinica.py", title="Triagem Clínica", default=True),
    st.Page("pages/2_Auditoria_Humana.py", title="Auditoria"),
    st.Page("pages/3_Historico.py", title="Histórico"),
]

with st.sidebar:
    st.image("assets/logo.png", width=250)

exibir_barra_lateral()
st.navigation(paginas).run()