import base64
from html import escape
import streamlit as st
import streamlit.components.v1 as components

from components.cards import exibir_item_de_auditoria
from components.erros import chamar_api_ou_parar
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


def _renderizar_visualizador_pdf(conteudo_pdf: bytes, altura: int = 420) -> None:
    b64 = base64.b64encode(conteudo_pdf).decode("utf-8")
    html_pdf = f"""
    <div id="pdf-wrap" style="width:100%;height:{altura - 8}px;border:1px solid #CBD5E1;
         border-radius:10px;overflow:hidden;background:#F1F5F9;"></div>
    <script>
    (function() {{
        try {{
            const b64 = "{b64}";
            const bin = atob(b64);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            const blob = new Blob([bytes], {{ type: "application/pdf" }});
            const url = URL.createObjectURL(blob);
            const iframe = document.createElement("iframe");
            iframe.src = url + "#toolbar=1&navpanes=0&view=FitH";
            iframe.style.width = "100%";
            iframe.style.height = "100%";
            iframe.style.border = "none";
            document.getElementById("pdf-wrap").appendChild(iframe);
        }} catch (e) {{
            document.getElementById("pdf-wrap").innerHTML =
                '<div style="padding:20px;color:#475569;font-family:sans-serif;font-size:14px;">' +
                'Não foi possível renderizar o PDF incorporado neste navegador. Utilize o botão de download acima.</div>';
        }}
    }})();
    </script>
    """
    components.html(html_pdf, height=altura, scrolling=False)


def _renderizar_folha_textual(documento_id: str, texto: str, nome_arquivo: str | None = None) -> None:
    linhas_escapadas = "<br>".join(escape(linha) for linha in (texto or DOCUMENTO_INDISPONIVEL).splitlines())
    subtitulo = escape(nome_arquivo or f"Transcrição Clínica • {documento_id}")
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #CBD5E1;border-top:4px solid #0B3C7A;
                    border-radius:10px;padding:16px 18px;max-height:380px;overflow-y:auto;
                    box-shadow:inset 0 1px 2px rgba(15,23,42,0.03);">
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding-bottom:10px;margin-bottom:12px;border-bottom:1px solid #E2E8F0;">
                <span style="font-size:0.76rem;font-weight:700;color:#0B3C7A;text-transform:uppercase;
                             letter-spacing:0.05em;">{subtitulo}</span>
                <span style="font-size:0.73rem;color:#64748B;background:#F1F5F9;padding:2px 8px;
                             border-radius:999px;font-weight:600;">{escape(documento_id)}</span>
            </div>
            <div style="font-family:'Inter',system-ui,sans-serif;font-size:0.86rem;color:#1E293B;
                        line-height:1.55;white-space:normal;">
                {linhas_escapadas}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("Pré-visualização do Documento Original", width="large")
def _modal_preview_documento(
    documento_id: str,
    fonte: tuple[bytes, str, str | None] | None,
    texto_extraido: str,
) -> None:
    if fonte:
        conteudo, mime, nome = fonte
        st.caption(f"Documento: `{documento_id}` • Arquivo: **{nome or 'documento_original'}** (`{mime}`)")
        if mime.startswith("image/"):
            st.image(conteudo, caption=nome or "Fonte original", width="stretch")
        elif mime == "application/pdf" or (nome and nome.lower().endswith(".pdf")):
            _renderizar_visualizador_pdf(conteudo, altura=600)
        else:
            _renderizar_folha_textual(documento_id, texto_extraido, nome)
    else:
        st.caption(f"Documento: `{documento_id}` • Visualização da transcrição textual")
        _renderizar_folha_textual(documento_id, texto_extraido)


def gerenciar_lock_auditoria(documento_id: str) -> str:
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
    bloqueado = bool(status_lock.get("bloqueado"))
    auditor_do_lock = status_lock.get("auditor")

    with st.container(border=True):
        col_input, col_status, col_acao = st.columns([2.2, 2.1, 1.1], vertical_alignment="bottom")
        with col_input:
            auditor = st.text_input(
                "Identificação do auditor",
                key=f"auditor_{documento_id}",
                help="Identificação informada para registrar o bloqueio e a decisão; ainda não é um login.",
            )

        if bloqueado and auditor_do_lock != auditor.strip():
            ttl_restante = status_lock.get("ttl_restante") or 0
            with col_status:
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:8px;background:#FEF3C7;
                                border:1px solid #FCD34D;color:#92400E;padding:8px 12px;
                                border-radius:8px;font-size:0.83rem;height:38px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#D97706"
                             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                        <span>Em revisão por <strong>{escape(auditor_do_lock or 'outro revisor')}</strong> (~{ttl_restante // 60} min)</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_acao:
                st.button(
                    "Bloqueado",
                    disabled=True,
                    width="stretch",
                    icon=":material/lock:",
                    key=f"btn_lock_ocupado_{documento_id}",
                )
            st.stop()

        if not bloqueado:
            with col_status:
                st.markdown(
                    """
                    <div style="display:flex;align-items:center;gap:8px;background:#F1F5F9;
                                border:1px solid #CBD5E1;color:#334155;padding:8px 12px;
                                border-radius:8px;font-size:0.82rem;height:38px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0B3C7A"
                             stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 9.9-1"/>
                        </svg>
                        <span>Disponível — inicie a revisão para bloquear este documento</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_acao:
                if st.button(
                    "Iniciar revisão",
                    type="primary",
                    width="stretch",
                    icon=":material/lock:",
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

        with col_status:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;background:#ECFDF5;
                            border:1px solid #A7F3D0;color:#065F46;padding:8px 12px;
                            border-radius:8px;font-size:0.83rem;height:38px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#059669"
                         stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                    </svg>
                    <span>Em revisão ativa por <strong>{escape(auditor_do_lock or auditor.strip())}</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_acao:
            if st.button(
                "Liberar revisão",
                width="stretch",
                icon=":material/lock_open:",
                key=f"liberar_revisao_{documento_id}",
            ):
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
    st.success(confirmacao_anterior["mensagem"], icon=":material/check_circle:")
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
    texto_doc = item.get("documento_texto") or DOCUMENTO_INDISPONIVEL
    fonte = None
    if item.get("fonte_original_disponivel"):
        fonte = chamar_api_ou_parar(obter_fonte_original, escolhido)

    col_btn_preview, col_btn_download = st.columns(2)
    with col_btn_preview:
        if st.button(
            "Ampliar pré-visualização",
            icon=":material/visibility:",
            width="stretch",
            key=f"btn_preview_modal_{escolhido}",
        ):
            _modal_preview_documento(escolhido, fonte, texto_doc)
    with col_btn_download:
        if fonte:
            conteudo, mime, nome = fonte
            st.download_button(
                "Baixar fonte original",
                data=conteudo,
                file_name=nome or "documento_original.pdf",
                mime=mime,
                icon=":material/download:",
                width="stretch",
            )

    aba_visual, aba_texto = st.tabs(
        [
            ":material/preview: Pré-visualização do Documento",
            ":material/article: Texto Extraído (OCR)",
        ]
    )
    with aba_visual:
        if fonte:
            conteudo, mime, nome = fonte
            if mime.startswith("image/"):
                st.image(conteudo, caption=nome or "Fonte original", width="stretch")
            elif mime == "application/pdf" or (nome and nome.lower().endswith(".pdf")):
                _renderizar_visualizador_pdf(conteudo, altura=410)
            else:
                _renderizar_folha_textual(escolhido, texto_doc, nome)
        else:
            _renderizar_folha_textual(escolhido, texto_doc)

    with aba_texto:
        st.text_area(
            "Texto do documento",
            value=texto_doc,
            height=340,
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
