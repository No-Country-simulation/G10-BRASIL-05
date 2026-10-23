import streamlit as st

from components.cards import exibir_resultado_da_triagem
from services.api_client import listar_documentos
from utils.historico import FILTROS_DE_STATUS, filtrar_por_status, montar_linhas_da_tabela

st.title("Histórico")
st.write("Consulte os documentos já processados pelo MediFlow.")

documentos = listar_documentos()
filtro = st.radio("Filtrar por status", FILTROS_DE_STATUS, horizontal=True)
documentos_filtrados = filtrar_por_status(documentos, filtro)

if not documentos_filtrados:
    st.info("Nenhum documento encontrado para este filtro.")
    st.stop()

st.caption(f"{len(documentos_filtrados)} documento(s)")
st.dataframe(montar_linhas_da_tabela(documentos_filtrados), hide_index=True, width="stretch")

identificadores = [documento.get("documento_id") for documento in documentos_filtrados]
escolhido = st.selectbox(
    "Ver detalhes do documento",
    identificadores,
    index=None,
    placeholder="Selecione um documento",
)
if escolhido is None:
    st.stop()

documento = next(d for d in documentos_filtrados if d.get("documento_id") == escolhido)
st.subheader(f"Documento {escolhido}")
exibir_resultado_da_triagem(documento)