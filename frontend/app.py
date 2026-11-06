import streamlit as st

from components.barra_lateral import exibir_barra_lateral
from components.modo_de_execucao import exibir_aviso_de_demonstracao

st.set_page_config(page_title="MediFlow", layout="wide")

paginas = [
    st.Page("pages/1_Triagem_Clinica.py", title="Triagem Clínica", default=True),
    st.Page("pages/2_Auditoria_Humana.py", title="Auditoria"),
    st.Page("pages/3_Historico.py", title="Histórico"),
    st.Page("pages/4_WhatsApp_Evolution.py", title="Conectar"),
]

exibir_barra_lateral()
exibir_aviso_de_demonstracao()
st.navigation(paginas).run()
