"""Fluxo de interface da tela de histórico de triagem."""
from datetime import datetime
from html import escape
import io
from pathlib import Path
from PIL import Image, ImageOps
import streamlit as st

from api.cliente_http import buscar_documento, listar_documentos, obter_fonte_original
from components.cards import (
    exibir_alerta_de_roteamento,
    exibir_classificacao,
    exibir_dados_extraidos,
    exibir_resultado_da_triagem,
)
from components.erros import chamar_api_ou_parar
from components.estilos import aplicar_css
from components.visualizador_documento import (
    DOCUMENTO_INDISPONIVEL,
    _renderizar_folha_textual,
    _renderizar_visualizador_pdf,
)
from services.autenticacao import esta_autenticado
from utils.aparencia import cor_da_confianca
from utils.formatadores import (
    normalizar_prioridade,
    rotular_prioridade,
    rotular_tipo_documento,
)
from utils.alertas_clinicos import (
    exibir_alerta_global_se_necessario,
    exibir_alerta_individual,
    obter_badge_estado_html,
    verificar_e_disparar_modal_alerta,
)
from utils.historico import (
    FILTROS_DE_PRIORIDADE,
    FILTROS_DE_STATUS,
    FILTROS_DE_TIPO,
    FILTRO_TODOS,
    OPCOES_ORDENACAO,
    STATUS_APROVADO,
    STATUS_DESCONHECIDO,
    STATUS_EM_AUDITORIA,
    STATUS_REJEITADO,
    STATUS_URGENCIA,
    calcular_metricas_historico,
    filtrar_historico_completo,
    identificar_status,
)


def _obter_badge_status_html(status: str) -> str:
    mapa_classes = {
        STATUS_APROVADO: "badge-status-aprovado",
        STATUS_URGENCIA: "badge-status-urgencia",
        STATUS_EM_AUDITORIA: "badge-status-auditoria",
        STATUS_REJEITADO: "badge-status-rejeitado",
        STATUS_DESCONHECIDO: "badge-status-desconhecido",
    }
    classe = mapa_classes.get(status, "badge-status-desconhecido")
    return f'<span class="badge-status {classe}">{escape(status)}</span>'


def _obter_badge_prioridade_html(prioridade_bruta: str | None) -> str:
    pri_norm = normalizar_prioridade(prioridade_bruta)
    pri_rot = rotular_prioridade(prioridade_bruta) or "Não informado"
    if pri_norm == "EMERGENCIA":
        classe = "badge-pri-emergencia"
    elif pri_norm == "URGENTE":
        classe = "badge-pri-urgente"
    else:
        classe = "badge-pri-rotina"
    return f'<span class="badge-pri {classe}">{escape(pri_rot)}</span>'


def _formatar_data_hora(valor: str | None) -> str:
    if not valor:
        return "-"
    try:
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)[:16]


@st.dialog("Detalhes do Documento", width="large")
def exibir_modal_detalhes_historico(doc_resumo: dict):
    doc_id = doc_resumo.get("documento_id", "-")
    status = identificar_status(doc_resumo)
    pri_bruta = doc_resumo.get("nivel_prioridade")
    nome_pac = doc_resumo.get("paciente_nome") or "Não identificado"
    cpf_pac = doc_resumo.get("paciente_cpf") or "Não informado"
    tipo_rot = rotular_tipo_documento(doc_resumo.get("tipo_documento")) or "Não classificado"
    data_formatada = _formatar_data_hora(doc_resumo.get("created_at"))

    # Banner do Documento
    st.markdown(
        f"""
        <div class="modal-header-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span style="font-size:0.75rem; color:#64748B; font-weight:700; text-transform:uppercase;">Protocolo</span>
                    <h3 style="margin:2px 0 0 0; color:#0F172A; font-size:1.15rem; font-weight:700;">{escape(doc_id)}</h3>
                </div>
                <div style="display:flex; gap:8px; align-items:center;">
                    {obter_badge_estado_html(doc_resumo)}
                    {_obter_badge_prioridade_html(pri_bruta)}
                    {_obter_badge_status_html(status)}
                </div>
            </div>
            <div style="margin-top:12px; display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:10px; font-size:0.84rem;">
                <div><span style="color:#64748B;">Paciente:</span> <strong>{escape(nome_pac)}</strong></div>
                <div><span style="color:#64748B;">CPF:</span> <strong>{escape(cpf_pac)}</strong></div>
                <div><span style="color:#64748B;">Tipo:</span> <strong>{escape(tipo_rot)}</strong></div>
                <div><span style="color:#64748B;">Data:</span> <strong>{escape(data_formatada)}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    aba_clinica, aba_documento, aba_tecnica = st.tabs(
        [
            "Resultado da Triagem",
            "Documento Original",
            "Trilha & Metadados",
        ]
    )

    with aba_clinica:
        detalhe_completo = None
        try:
            detalhe_completo = buscar_documento(doc_id)
        except Exception:
            detalhe_completo = None

        if detalhe_completo:
            exibir_resultado_da_triagem(detalhe_completo)
        else:
            # Apresentação formatada com dados disponíveis do histórico
            st.info("Visualização consolidada do registro de triagem:")
            decisao_mock = {
                "destino_principal": doc_resumo.get("destino_principal"),
                "justificativa_roteamento": doc_resumo.get("justificativa_roteamento") or "Processamento concluído com sucesso.",
            }
            exibir_alerta_de_roteamento(decisao_mock)

            classificacao_mock = {
                "tipo_documento": doc_resumo.get("tipo_documento"),
                "especialidade": doc_resumo.get("especialidade") or "Clínica Geral",
                "nivel_prioridade": doc_resumo.get("nivel_prioridade"),
                "score_confianca_classificacao": doc_resumo.get("score_confianca"),
            }
            exibir_classificacao(classificacao_mock)

            if doc_resumo.get("dados_extraidos"):
                st.subheader("Entidades extraídas")
                exibir_dados_extraidos(doc_resumo["dados_extraidos"])

    with aba_documento:
        fonte = None
        try:
            fonte = obter_fonte_original(doc_id)
        except Exception:
            fonte = None

        texto_doc = doc_resumo.get("documento_texto") or doc_resumo.get("texto_extraido")

        if fonte:
            conteudo, mime, nome = fonte
            col_down, col_rot, col_tam = st.columns([1.8, 1.4, 2.5], vertical_alignment="center")
            with col_down:
                st.download_button(
                    "Baixar arquivo original",
                    data=conteudo,
                    file_name=nome or f"{doc_id}_original",
                    mime=mime,
                    icon=":material/download:",
                    key=f"dl_hist_{doc_id}",
                    use_container_width=True,
                )

            if mime.startswith("image/"):
                with col_rot:
                    if st.button("Girar 90°", icon=":material/rotate_right:", key=f"btn_rot_hist_{doc_id}", use_container_width=True):
                        st.session_state[f"rot_hist_{doc_id}"] = (st.session_state.get(f"rot_hist_{doc_id}", 0) - 90) % 360
                        st.rerun()
                with col_tam:
                    largura = st.slider(
                        "Tamanho da imagem",
                        min_value=300,
                        max_value=900,
                        value=560,
                        step=40,
                        key=f"slide_w_hist_{doc_id}",
                        label_visibility="collapsed",
                    )
                try:
                    img = Image.open(io.BytesIO(conteudo))
                    img = ImageOps.exif_transpose(img)
                    angulo = st.session_state.get(f"rot_hist_{doc_id}", 0)
                    if angulo:
                        img = img.rotate(angulo, expand=True)
                    st.image(img, caption=nome or "Documento original", width=largura)
                except Exception:
                    st.image(conteudo, caption=nome or "Documento original", width=560)
            elif mime == "application/pdf" or (nome and nome.lower().endswith(".pdf")):
                _renderizar_visualizador_pdf(conteudo, altura=520)
            else:
                _renderizar_folha_textual(doc_id, texto_doc or conteudo.decode("utf-8", errors="ignore"), nome)
        elif texto_doc:
            _renderizar_folha_textual(doc_id, texto_doc)
        else:
            st.info("Arquivo original ou transcrição OCR não arquivados para este documento.")

    with aba_tecnica:
        st.markdown(f"**Identificador no Sistema:** `{doc_id}`")
        st.markdown(f"**Destino do Fluxo:** `{doc_resumo.get('destino_principal') or '-'}`")
        st.markdown(f"**Status de Processamento:** `{doc_resumo.get('status_processamento') or '-'}`")
        st.markdown(f"**Requer Revisão Humana:** `{'Sim' if doc_resumo.get('requer_auditoria_humana') else 'Não'}`")
        if doc_resumo.get("score_confianca") is not None:
            st.markdown(f"**Score de Confiança:** `{doc_resumo['score_confianca']:.2%}`")
        if doc_resumo.get("canal_origem"):
            st.markdown(f"**Canal de Entrada:** `{doc_resumo.get('canal_origem')}`")


def render() -> None:
    if not esta_autenticado(st.session_state):
        st.switch_page("app.py")
        st.stop()

    aplicar_css(Path(__file__).with_name("style.css"))

    # Cabeçalho da Página
    st.title("Histórico")
    st.caption("Consulte, filtre e acompanhe os prontuários, laudos e receitas processados pelo MediFlow.")

    # Carga de Documentos
    documentos = chamar_api_ou_parar(listar_documentos) or []

    # Alerta clínico no topo da tela para casos de Emergência ou Perigo
    exibir_alerta_global_se_necessario(documentos)
    verificar_e_disparar_modal_alerta(documentos)

    # KPI Summary Cards
    metricas = calcular_metricas_historico(documentos)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f"""
            <div class="historico-kpi-card">
                <span class="historico-kpi-label">Total de Documentos</span>
                <span class="historico-kpi-valor">{metricas['total']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="historico-kpi-card">
                <span class="historico-kpi-label" style="color:#027A48;">Aprovados</span>
                <span class="historico-kpi-valor" style="color:#027A48;">{metricas['aprovados']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="historico-kpi-card">
                <span class="historico-kpi-label" style="color:#B54708;">Aguardando revisão</span>
                <span class="historico-kpi-valor" style="color:#B54708;">{metricas['em_auditoria']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="historico-kpi-card">
                <span class="historico-kpi-label" style="color:#B42318;">Urgência / Emergência</span>
                <span class="historico-kpi-valor" style="color:#B42318;">{metricas['urgencias']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f"""
            <div class="historico-kpi-card">
                <span class="historico-kpi-label" style="color:#475467;">Rejeitados</span>
                <span class="historico-kpi-valor" style="color:#475467;">{metricas['rejeitados']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Painel de Filtros e Busca em Container com Borda Nativa
    with st.container(border=True):
        # Linha 1: Campo de Busca principal
        termo_busca = st.text_input(
            "Buscar no histórico",
            placeholder="Buscar por paciente, CPF, identificador (DOC-...), tipo ou condição...",
            key="filtro_termo_historico",
        ).strip()

        # Linha 2: Filtros Específicos
        f_status, f_pri, f_tipo, f_ord = st.columns(4)

        with f_status:
            filtro_status = st.selectbox(
                "Status",
                FILTROS_DE_STATUS,
                key="sel_status_hist",
            )

        with f_pri:
            filtro_prioridade = st.selectbox(
                "Prioridade",
                FILTROS_DE_PRIORIDADE,
                key="sel_pri_hist",
            )

        with f_tipo:
            filtro_tipo = st.selectbox(
                "Tipo de Documento",
                FILTROS_DE_TIPO,
                key="sel_tipo_hist",
            )

        with f_ord:
            ordenacao = st.selectbox(
                "Ordenar por",
                OPCOES_ORDENACAO,
                key="sel_ord_hist",
            )

        # Linha 3: Botões de ação posicionados embaixo da lista de filtros
        tem_filtros_ativos = bool(
            termo_busca
            or st.session_state.get("sel_status_hist", FILTRO_TODOS) != FILTRO_TODOS
            or st.session_state.get("sel_pri_hist", "Todas") != "Todas"
            or st.session_state.get("sel_tipo_hist", "Todos") != "Todos"
        )
        col_espaco, col_btn_limpar, col_btn_buscar = st.columns([3.6, 1.2, 1.2], vertical_alignment="center")
        with col_btn_limpar:
            if st.button("Limpar filtros", icon=":material/filter_alt_off:", use_container_width=True, disabled=not tem_filtros_ativos):
                st.session_state["filtro_termo_historico"] = ""
                st.session_state["sel_status_hist"] = FILTRO_TODOS
                st.session_state["sel_pri_hist"] = "Todas"
                st.session_state["sel_tipo_hist"] = "Todos"
                st.session_state["sel_ord_hist"] = "Mais recentes primeiro"
                st.rerun()
        with col_btn_buscar:
            if st.button("Buscar", icon=":material/search:", type="primary", use_container_width=True):
                st.rerun()

    # Filtragem dos Documentos
    documentos_filtrados = filtrar_historico_completo(
        documentos=documentos,
        termo_busca=termo_busca,
        filtro_status=filtro_status,
        filtro_prioridade=filtro_prioridade,
        filtro_tipo=filtro_tipo,
        ordenacao=ordenacao,
    )

    # Se veio de redirecionamento para verificar paciente, abre automaticamente os detalhes
    doc_selecionado_hist = st.session_state.pop("documento_selecionado_historico", None)
    if doc_selecionado_hist:
        doc_alvo = next((d for d in documentos if d.get("documento_id") == doc_selecionado_hist), None)
        if doc_alvo:
            exibir_modal_detalhes_historico(doc_alvo)

    # Subtítulo com contagem
    total_docs = len(documentos)
    filtrados_count = len(documentos_filtrados)
    if total_docs == filtrados_count:
        st.caption(f"Mostrando todos os {filtrados_count} documento(s) cadastrados.")
    else:
        st.caption(f"Mostrando {filtrados_count} de {total_docs} documento(s) com base nos filtros selecionados.")

    if not documentos_filtrados:
        st.info("Nenhum documento encontrado com os critérios de filtro e busca aplicados.")
        return

    # Cabeçalho da Tabela
    st.markdown(
        """
        <div class="historico-tabela-container">
            <div class="historico-tabela-cabecalho">
                <div>Documento</div>
                <div>Paciente</div>
                <div>Tipo</div>
                <div>Prioridade</div>
                <div>Confiança</div>
                <div>Data/Hora</div>
                <div>Status</div>
                <div style="text-align: right;">Ação</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Linhas de Documentos
    for indice, doc in enumerate(documentos_filtrados):
        doc_id = doc.get("documento_id", "-")
        status = identificar_status(doc)
        nome_pac = doc.get("paciente_nome") or "Não identificado"
        cpf_pac = doc.get("paciente_cpf") or ""
        tipo_rot = rotular_tipo_documento(doc.get("tipo_documento")) or "Não classificado"
        pri_bruta = doc.get("nivel_prioridade")
        data_formatada = _formatar_data_hora(doc.get("created_at"))
        score = doc.get("score_confianca")
        cor_score = cor_da_confianca(score)
        score_texto = f"{score:.0%}" if score is not None else "-"

        with st.container():
            c_doc, c_pac, c_tipo, c_pri, c_conf, c_data, c_status, c_acao = st.columns(
                [2.2, 2.3, 1.6, 1.3, 1.1, 1.5, 1.4, 1.1],
                vertical_alignment="center",
            )

            with c_doc:
                st.markdown(
                    f"<span style='font-size:0.86rem; font-weight:700; color:#0F172A; font-family:monospace;' title='{escape(doc_id)}'>{escape(doc_id)}</span>",
                    unsafe_allow_html=True,
                )

            with c_pac:
                cpf_tag = f"<br><span style='font-size:0.75rem; color:#64748B;'>CPF: {escape(cpf_pac)}</span>" if cpf_pac else ""
                st.markdown(
                    f"<div style='line-height:1.25;'><span style='font-size:0.86rem; font-weight:600; color:#1E293B;'>{escape(nome_pac)}</span>{cpf_tag}</div>",
                    unsafe_allow_html=True,
                )

            with c_tipo:
                st.markdown(
                    f"<span style='font-size:0.82rem; color:#334155;'>{escape(tipo_rot)}</span>",
                    unsafe_allow_html=True,
                )

            with c_pri:
                st.markdown(obter_badge_estado_html(doc), unsafe_allow_html=True)

            with c_conf:
                st.markdown(
                    f"<span style='font-size:0.84rem; font-weight:700; color:{cor_score};'>{score_texto}</span>",
                    unsafe_allow_html=True,
                )

            with c_data:
                st.markdown(
                    f"<span style='font-size:0.80rem; color:#475467;'>{escape(data_formatada)}</span>",
                    unsafe_allow_html=True,
                )

            with c_status:
                st.markdown(_obter_badge_status_html(status), unsafe_allow_html=True)

            with c_acao:
                if st.button("Detalhes", key=f"btn_detalhes_hist_{doc_id}_{indice}", use_container_width=True):
                    exibir_modal_detalhes_historico(doc)

            st.markdown(
                '<div style="height:1px; background:#F1F5F9; margin:4px 0 6px 0;"></div>',
                unsafe_allow_html=True,
            )
