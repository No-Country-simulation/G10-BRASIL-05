import streamlit as st

from components.cards import exibir_item_de_auditoria
from components.erros import chamar_api_ou_parar
from services.configuracao import usar_dados_simulados
from services.api_client import (
    bloquear_documento_auditoria,
    listar_fila_auditoria,
    obter_fonte_original,
    obter_status_lock_auditoria,
    registrar_decisao,
    desbloquear_documento_auditoria,
)
from utils.auditoria import (
    CAMPOS_EDITAVEIS,
    DECISAO_APROVAR,
    DECISAO_CORRIGIR,
    DECISAO_REJEITAR,
    DECISAO_REENVIAR,
    calcular_correcoes,
    extrair_valores_editaveis,
    montar_decisao,
    montar_rotulo_da_fila,
    ordenar_fila,
    validar_decisao,
)

DOCUMENTO_INDISPONIVEL = "Documento original não disponível."
CHAVE_DA_CONFIRMACAO = "confirmacao_da_auditoria"
CHAVE_DO_LOCK_ATUAL = "lock_auditoria_atual"
AVISO_DE_DECISAO_PENDENTE = (
    "O documento continua pendente na fila. Atualize a página para conferir antes de tentar de novo."
)


def gerenciar_lock_auditoria(documento_id: str) -> str:
    auditor = st.text_input(
        "Identificação do auditor",
        key=f"auditor_{documento_id}",
        help="Identificação informada para registrar o bloqueio e a decisão; ainda não é um login.",
    )
    if usar_dados_simulados():
        return auditor

    lock_anterior = st.session_state.get(CHAVE_DO_LOCK_ATUAL)
    if lock_anterior and lock_anterior.get("documento_id") != documento_id:
        status_anterior = chamar_api_ou_parar(
            obter_status_lock_auditoria, lock_anterior["documento_id"]
        )
        if (
            status_anterior.get("bloqueado")
            and status_anterior.get("auditor") == lock_anterior.get("auditor_nome")
        ):
            chamar_api_ou_parar(
                desbloquear_documento_auditoria,
                lock_anterior["documento_id"],
                lock_anterior["auditor_nome"],
            )
        st.session_state.pop(CHAVE_DO_LOCK_ATUAL, None)

    status_lock = chamar_api_ou_parar(obter_status_lock_auditoria, documento_id)
    auditor_do_lock = status_lock.get("auditor")
    if status_lock.get("bloqueado") and auditor_do_lock != auditor.strip():
        ttl_restante = status_lock.get("ttl_restante") or 0
        st.warning(
            f"Este documento está em revisão por **{auditor_do_lock or 'outro revisor'}**. "
            f"O bloqueio expira em aproximadamente {ttl_restante // 60} min."
        )
        st.stop()

    if not status_lock.get("bloqueado"):
        st.info("Inicie a revisão para bloquear este documento antes de registrar uma decisão.")
        if st.button(
            "Iniciar revisão",
            type="primary",
            disabled=not auditor.strip(),
            key=f"iniciar_revisao_{documento_id}",
        ):
            chamar_api_ou_parar(bloquear_documento_auditoria, documento_id, auditor.strip())
            st.session_state[CHAVE_DO_LOCK_ATUAL] = {
                "documento_id": documento_id,
                "auditor_nome": auditor.strip(),
            }
            st.rerun()
        st.stop()

    st.success(f"Revisão bloqueada para **{auditor_do_lock}**.")
    if st.button("Liberar revisão", key=f"liberar_revisao_{documento_id}"):
        chamar_api_ou_parar(
            desbloquear_documento_auditoria,
            documento_id,
            auditor.strip(),
        )
        st.session_state.pop(CHAVE_DO_LOCK_ATUAL, None)
        st.rerun()
    return auditor


st.title("Auditoria")
st.write("Revise os documentos que a triagem encaminhou para análise humana.")

confirmacao_anterior = st.session_state.pop(CHAVE_DA_CONFIRMACAO, None)
if confirmacao_anterior:
    st.success(confirmacao_anterior["mensagem"])
    with st.expander("Ver decisão enviada (JSON)"):
        st.json(confirmacao_anterior["decisao"])

fila = ordenar_fila(chamar_api_ou_parar(listar_fila_auditoria))
if not fila:
    st.info("Nenhum documento aguardando auditoria.")
    st.stop()

st.caption(f"{len(fila)} documento(s) aguardando auditoria")
rotulos = {item.get("documento_id"): montar_rotulo_da_fila(item) for item in fila}
escolhido = st.selectbox(
    "Documento para revisar",
    list(rotulos),
    format_func=rotulos.get,
    index=None,
    placeholder="Selecione um documento",
)
if escolhido is None:
    st.stop()

item = next(item for item in fila if item.get("documento_id") == escolhido)
auditor = gerenciar_lock_auditoria(escolhido)

coluna_documento, coluna_resultado = st.columns(2, gap="large")
with coluna_documento:
    st.subheader("Documento original")
    if item.get("fonte_original_disponivel"):
        fonte = chamar_api_ou_parar(obter_fonte_original, escolhido)
        if fonte:
            conteudo, mime, nome = fonte
            if mime.startswith("image/"):
                st.image(conteudo, caption=nome or "Fonte original", width="stretch")
            else:
                st.download_button(
                    "Baixar fonte original para conferência",
                    data=conteudo,
                    file_name=nome or "documento_original.pdf",
                    mime=mime,
                )
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
    justificativa = st.text_area("Justificativa", height=100, key=f"justificativa_{escolhido}")
    with st.expander("Corrigir dados extraídos"):
        valores_editados = {
            campo: st.text_input(rotulo, value=valores_atuais[campo], key=f"{campo}_{escolhido}")
            for campo, rotulo in CAMPOS_EDITAVEIS.items()
        }
    coluna_aprovar, coluna_rejeitar, coluna_corrigir, coluna_reenviar = st.columns(4)
    with coluna_aprovar:
        aprovou = st.form_submit_button("Aprovar", type="primary")
    with coluna_rejeitar:
        rejeitou = st.form_submit_button("Rejeitar")
    with coluna_corrigir:
        corrigiu = st.form_submit_button("Corrigir")
    with coluna_reenviar:
        pediu_reenvio = st.form_submit_button("Pedir novo documento")

cliques = {
    DECISAO_APROVAR: aprovou,
    DECISAO_REJEITAR: rejeitou,
    DECISAO_CORRIGIR: corrigiu,
    DECISAO_REENVIAR: pediu_reenvio,
}
acao = next((nome for nome, clicou in cliques.items() if clicou), None)
if acao is None:
    st.stop()

correcoes = calcular_correcoes(valores_atuais, valores_editados)
problema = validar_decisao(acao, auditor, justificativa, correcoes)
if problema:
    st.warning(problema)
    st.stop()

decisao = montar_decisao(acao, auditor, justificativa, item.get("dados_extraidos") or {}, correcoes)
resposta = chamar_api_ou_parar(
    registrar_decisao, escolhido, decisao, complemento=AVISO_DE_DECISAO_PENDENTE
)
st.session_state.pop(CHAVE_DO_LOCK_ATUAL, None)

# Recarrega a página para o documento decidido sair da fila e não receber uma segunda decisão
st.session_state[CHAVE_DA_CONFIRMACAO] = {
    "mensagem": f"{resposta.get('mensagem', 'Decisão registrada.')} Documento {escolhido}.",
    "decisao": decisao,
}
st.rerun()
