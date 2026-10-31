import streamlit as st

from components.cards import exibir_item_de_auditoria
from services.api_client import listar_fila_auditoria, registrar_decisao
from utils.auditoria import (
    CAMPOS_EDITAVEIS,
    DECISAO_APROVAR,
    DECISAO_CORRIGIR,
    DECISAO_REJEITAR,
    calcular_correcoes,
    extrair_valores_editaveis,
    montar_decisao,
    validar_decisao,
)

DOCUMENTO_INDISPONIVEL = "Documento original não disponível."

st.title("Auditoria")
st.write("Revise os documentos que a triagem encaminhou para análise.")

fila = listar_fila_auditoria()
if not fila:
    st.info("Nenhum documento aguardando auditoria.")
    st.stop()

st.caption(f"{len(fila)} documento(s) aguardando auditoria")
escolhido = st.selectbox(
    "Documento para revisar",
    [item.get("documento_id") for item in fila],
    index=None,
    placeholder="Selecione um documento",
)
if escolhido is None:
    st.stop()

item = next(item for item in fila if item.get("documento_id") == escolhido)

coluna_documento, coluna_resultado = st.columns(2, gap="large")
with coluna_documento:
    st.subheader("Documento original")
    st.text_area(
        "Texto do documento",
        value=item.get("documento_texto") or DOCUMENTO_INDISPONIVEL,
        height=320,
        disabled=True,
        key=f"documento_{escolhido}",
    )
with coluna_resultado:
    exibir_item_de_auditoria(item)

st.subheader("Decisão do auditor")
valores_atuais = extrair_valores_editaveis(item)

with st.form(f"decisao_{escolhido}"):
    auditor = st.text_input("Identificação do auditor", key="auditor")
    justificativa = st.text_area("Justificativa", height=100, key=f"justificativa_{escolhido}")
    with st.expander("Corrigir dados extraídos"):
        valores_editados = {
            campo: st.text_input(rotulo, value=valores_atuais[campo], key=f"{campo}_{escolhido}")
            for campo, rotulo in CAMPOS_EDITAVEIS.items()
        }
    coluna_aprovar, coluna_rejeitar, coluna_corrigir = st.columns(3)
    with coluna_aprovar:
        aprovou = st.form_submit_button("Aprovar", type="primary")
    with coluna_rejeitar:
        rejeitou = st.form_submit_button("Rejeitar")
    with coluna_corrigir:
        corrigiu = st.form_submit_button("Corrigir")

cliques = {DECISAO_APROVAR: aprovou, DECISAO_REJEITAR: rejeitou, DECISAO_CORRIGIR: corrigiu}
acao = next((nome for nome, clicou in cliques.items() if clicou), None)
if acao is None:
    st.stop()

correcoes = calcular_correcoes(valores_atuais, valores_editados)
problema = validar_decisao(acao, auditor, justificativa, correcoes)
if problema:
    st.warning(problema)
    st.stop()

decisao = montar_decisao(acao, auditor, justificativa, item.get("dados_extraidos") or {}, correcoes)
confirmacao = registrar_decisao(escolhido, decisao)
st.success(f"{confirmacao.get('mensagem', 'Decisão registrada.')} Documento {escolhido}.")
with st.expander("Ver decisão enviada (JSON)"):
    st.json(decisao)