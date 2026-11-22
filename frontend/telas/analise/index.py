"""Fluxo de interface da tela de análise de documentos."""
import base64
from datetime import datetime
from html import escape
import io
from pathlib import Path
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

from api.cliente_http import (
    buscar_documento,
    listar_documentos,
    obter_fonte_original,
    obter_status_triagem,
)
from components.cards import exibir_resultado_da_triagem
from components.erros import chamar_api_ou_parar
from components.estilos import aplicar_css
from components.visualizador_documento import (
    DOCUMENTO_INDISPONIVEL,
    _renderizar_folha_textual,
    _renderizar_visualizador_pdf,
)
from services.autenticacao import esta_autenticado
from services.triagem_event_stream import escutar_eventos_triagem, obter_url_stream_triagem
from telas.analise.dados import corresponde_filtro
from utils.alertas_clinicos import (
    exibir_alerta_global_se_necessario,
    exibir_alerta_individual,
    obter_badge_estado_html,
    renderizar_acao_desativar_alerta,
    verificar_e_disparar_modal_alerta,
)


def _formatar_badge_status(status_chave: str) -> tuple[str, str]:
    mapa = {
        "na_fila": ("status-na-fila", "Na fila"),
        "em_auditoria": ("status-na-fila", "Aguardando revisão"),
        "processando": ("status-processando", "Processando"),
        "concluido": ("status-concluido", "Concluído"),
        "falhou": ("status-falhou", "Falhou"),
    }
    return mapa.get(status_chave, ("status-na-fila", status_chave.capitalize()))


def _formatar_badge_canal(canal: str | None) -> str:
    canal_str = (canal or "Interno").strip()
    if "whatsapp" in canal_str.lower():
        return '<span class="badge-canal badge-canal-wpp">WhatsApp</span>'
    return f'<span class="badge-canal badge-canal-ps">{escape(canal_str.replace("_", " "))}</span>'


def _formatar_paciente_exibicao(doc: dict) -> str:
    """Formata o nome do paciente para exibição, considerando o status da esteira."""
    status = str(doc.get("status") or doc.get("status_processamento") or "").strip().lower()
    nome = (doc.get("paciente_nome") or "").strip()

    if status in {"falhou", "erro"}:
        if not nome or nome in {"Aguardando identificação", "Identificado", "-"}:
            return "-"
        return nome

    if status in {"na_fila", "processando", "pendente", "iniciado"}:
        if not nome or nome in {"Aguardando identificação", "Identificado", "-"}:
            return "Em andamento..."
        return nome

    if not nome or nome in {"Aguardando identificação", "Identificado"}:
        return "-"
    return nome


def _aguarda_revisao_humana(doc: dict) -> bool:
    """Indica se o documento ainda precisa de intervenção na fila de revisão."""
    status_processamento = str(doc.get("status_processamento") or "").strip().lower()
    destino = str(doc.get("destino_principal") or "").strip().lower()

    if status_processamento.startswith("auditoria_"):
        return False

    return (
        doc.get("requer_auditoria_humana") is True
        or status_processamento in {"em_auditoria", "aguardando_revisao", "aguardando_revisão"}
        or destino == "auditoria_humana"
    )


@st.dialog("Detalhes do Documento", width="large")
def exibir_modal_detalhes(doc_info: dict) -> None:
    """Modal para visualização completa de detalhes do documento."""
    try:
        doc_id = doc_info.get("documento_id")
        resultado = doc_info.get("resultado")
        if not resultado:
            # 1. Tenta obter pelo status da fila em memória
            try:
                status_api = obter_status_triagem(doc_id)
                if status_api and status_api.get("resultado"):
                    resultado = status_api["resultado"]
            except Exception:
                pass

            # 2. Se não estiver no Redis, busca os detalhes persistidos do documento
            if not resultado:
                try:
                    resultado = buscar_documento(doc_id)
                except Exception:
                    pass

        # Hidrata metadados do resultado no doc_info para manter cabeçalho e badges 100% sincronizados
        if resultado:
            doc_info["resultado"] = resultado
            classif = resultado.get("classificacao") or {}
            decisao = resultado.get("decisao_roteamento") or {}
            dados = resultado.get("dados_extraidos") or {}
            pac = dados.get("paciente")
            if isinstance(pac, dict):
                if pac.get("nome") and (not doc_info.get("paciente_nome") or doc_info.get("paciente_nome") == "Identificado"):
                    doc_info["paciente_nome"] = pac.get("nome")
                if pac.get("cpf") and doc_info.get("paciente_cpf") in {None, "-"}:
                    doc_info["paciente_cpf"] = pac.get("cpf")
            if classif.get("nivel_prioridade"):
                doc_info["nivel_prioridade"] = classif.get("nivel_prioridade")
            if decisao.get("destino_principal"):
                doc_info["destino_principal"] = decisao.get("destino_principal")
            if decisao.get("justificativa_roteamento"):
                doc_info["justificativa_roteamento"] = decisao.get("justificativa_roteamento")

        classe_badge, rotulo_status = _formatar_badge_status(doc_info.get("status", "na_fila"))
        nome_pac_modal = _formatar_paciente_exibicao(doc_info)
        cpf_modal = doc_info.get('paciente_cpf', '-') if doc_info.get("status") != "falhou" else "-"

        st.markdown(
            f"""
            <div class="modal-header-card">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span style="font-size:0.75rem; color:#64748B; font-weight:700; text-transform:uppercase;">Protocolo</span>
                        <h3 style="margin:2px 0 0 0; color:#0F172A; font-size:1.15rem; font-weight:700;">{escape(str(doc_id))}</h3>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        {obter_badge_estado_html(doc_info)}
                        {_formatar_badge_canal(doc_info.get('canal_origem'))}
                        <span class="badge-status {classe_badge}">{rotulo_status}</span>
                    </div>
                </div>
                <div style="margin-top:12px; display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:10px; font-size:0.84rem;">
                    <div><span style="color:#64748B;">Paciente:</span> <strong>{escape(str(nome_pac_modal))}</strong></div>
                    <div><span style="color:#64748B;">CPF:</span> <strong>{escape(str(cpf_modal))}</strong></div>
                    <div><span style="color:#64748B;">Data de Envio:</span> <strong>{escape(str(doc_info.get('data_hora', '-')))}</strong></div>
                    <div><span style="color:#64748B;">Canal:</span> <strong>{escape(str(doc_info.get('canal_origem', '-')))}</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        renderizar_acao_desativar_alerta(doc_info)

        aba_clinica, aba_documento = st.tabs(["Resultado Clínico", "Documento Original"])

        with aba_clinica:
            if resultado:
                exibir_resultado_da_triagem(resultado)
            elif doc_info.get("status") == "falhou":
                erro_msg = doc_info.get("erro") or "Ocorreu um erro no processamento deste documento."
                st.error(f"Motivo da falha: {erro_msg}")
            elif doc_info.get("status") == "processando":
                etapa = doc_info.get("etapa_atual", "Extração e classificação")
                st.info(f"O documento está sendo processado pela inteligência clínica. Etapa atual: **{etapa}**.")
            else:
                st.info("Documento aguardando na fila de processamento da esteira.")

        with aba_documento:
            fonte = None
            try:
                fonte = obter_fonte_original(doc_id)
            except Exception:
                fonte = None

            if fonte:
                conteudo, mime, nome = fonte
                col_down, col_rot, col_tam = st.columns([1.8, 1.4, 2.5], vertical_alignment="center")
                with col_down:
                    st.download_button(
                        "Baixar original",
                        data=conteudo,
                        file_name=nome or "documento_original",
                        mime=mime,
                        icon=":material/download:",
                        key=f"dl_fonte_{doc_id}",
                        use_container_width=True,
                    )

                if mime.startswith("image/"):
                    with col_rot:
                        if st.button("Girar 90°", icon=":material/rotate_right:", key=f"btn_rot_{doc_id}", use_container_width=True):
                            st.session_state[f"rot_{doc_id}"] = (st.session_state.get(f"rot_{doc_id}", 0) - 90) % 360
                            st.rerun()
                    with col_tam:
                        largura = st.slider(
                            "Tamanho da imagem",
                            min_value=300,
                            max_value=900,
                            value=520,
                            step=40,
                            key=f"slide_w_{doc_id}",
                            label_visibility="collapsed",
                        )
                    try:
                        img = Image.open(io.BytesIO(conteudo))
                        img = ImageOps.exif_transpose(img)
                        angulo = st.session_state.get(f"rot_{doc_id}", 0)
                        if angulo:
                            img = img.rotate(angulo, expand=True)
                        st.image(img, caption=nome or "Documento original", width=largura)
                    except Exception:
                        st.image(conteudo, caption=nome or "Documento original", width=520)
                elif mime == "application/pdf" or (nome and nome.lower().endswith(".pdf")):
                    b64 = base64.b64encode(conteudo).decode("utf-8")
                    html_pdf = f"""
                    <iframe src="data:application/pdf;base64,{b64}#toolbar=1" width="100%" height="520px" style="border:1px solid #CBD5E1; border-radius:8px;"></iframe>
                    """
                    components.html(html_pdf, height=530)
                else:
                    try:
                        texto = conteudo.decode("utf-8")
                        st.text_area("Conteúdo do documento", value=texto, height=400, disabled=True)
                    except Exception:
                        st.info("Formato binário disponível para visualização via download.")
            else:
                st.info("Documento original não disponível ou arquivado apenas como transcrição.")
    except Exception as erro:
        st.error(f"Erro ao exibir detalhes do documento: {erro}")


def render() -> None:
    if not esta_autenticado(st.session_state):
        st.switch_page("app.py")
        st.stop()

    aplicar_css(Path(__file__).with_name("style.css"))

    # Cabeçalho da Página
    st.title("Análise de Documentos")
    st.caption("Acompanhamento do processamento, extração clínica e status em tempo real da esteira inteligente.")

    # Chave de estado para itens enviados nesta sessão ou recentes
    if "trabalhos_triagem" not in st.session_state:
        st.session_state["trabalhos_triagem"] = []

    trabalhos_sessao = st.session_state["trabalhos_triagem"]
    existem_trabalhos_ativos = any(
        item.get("status") in {"na_fila", "processando"}
        for item in trabalhos_sessao
    )
    if existem_trabalhos_ativos:
        try:
            url_stream = obter_url_stream_triagem()
            evento = escutar_eventos_triagem(
                url_stream,
                chave=f"stream_triagem_{st.session_state.get('usuario_ativo_id', 'usuario')}",
            )
            if evento and evento.get("id"):
                chave_ultimo_evento = "ultimo_evento_sse_triagem"
                if st.session_state.get(chave_ultimo_evento) != evento["id"]:
                    st.session_state[chave_ultimo_evento] = evento["id"]
        except Exception:
            pass

    # Atualiza o estado ao abrir a página
    for item in trabalhos_sessao:
        if item.get("status") in {"na_fila", "processando"}:
            try:
                status_api = obter_status_triagem(item["documento_id"])
                if status_api:
                    novo_status = status_api.get("status", item["status"])
                    item["status"] = novo_status
                    if status_api.get("etapa_atual"):
                        item["etapa_atual"] = status_api["etapa_atual"]

                    resultado_parcial = status_api.get("resultado_parcial") or {}
                    paciente_parcial = resultado_parcial.get("Paciente", {}).get("dados_documento", {})
                    if paciente_parcial.get("nome"):
                        item["paciente_nome"] = paciente_parcial["nome"]
                    if paciente_parcial.get("cpf"):
                        item["paciente_cpf"] = paciente_parcial["cpf"]

                    if novo_status == "concluido" and status_api.get("resultado"):
                        resultado = status_api["resultado"]
                        item["resultado"] = resultado
                        dados = resultado.get("dados_extraidos", {})
                        paciente = dados.get("paciente", {})
                        if isinstance(paciente, dict):
                            if paciente.get("nome"):
                                item["paciente_nome"] = paciente["nome"]
                            if paciente.get("cpf"):
                                item["paciente_cpf"] = paciente["cpf"]
                        elif isinstance(paciente, str) and paciente.strip():
                            item["paciente_nome"] = paciente

                    if novo_status == "falhou":
                        item["erro"] = status_api.get("erro", "Falha no processamento.")
            except Exception:
                pass

    # Carrega documentos persistidos para unificar visualização
    docs_api = []
    try:
        docs_api = listar_documentos() or []
    except Exception:
        docs_api = []

    ids_vistos = set()
    todos_documentos = []

    for item in trabalhos_sessao:
        doc_id = item.get("documento_id")
        if doc_id and doc_id not in ids_vistos:
            ids_vistos.add(doc_id)
            todos_documentos.append({
                "documento_id": doc_id,
                "arquivo": doc_id,
                "nome_original": item.get("nome_original") or item.get("arquivo") or doc_id,
                "paciente_nome": item.get("paciente_nome") or "",
                "paciente_cpf": item.get("paciente_cpf") or "-",
                "data_hora": item.get("data_envio") or "-",
                "data_iso": item.get("data_envio") or "",
                "status": item.get("status") or "na_fila",
                "status_processamento": item.get("status_processamento"),
                "canal_origem": item.get("canal_origem") or "Interno",
                "requer_auditoria_humana": item.get("requer_auditoria_humana"),
                "resultado": item.get("resultado"),
                "erro": item.get("erro"),
                "etapa_atual": item.get("etapa_atual"),
            })

    for doc in docs_api:
        doc_id = doc.get("documento_id")
        if doc_id and doc_id in ids_vistos:
            documento_existente = next(
                (item for item in todos_documentos if item.get("documento_id") == doc_id),
                None,
            )
            if documento_existente is not None:
                documento_existente.update({
                    "status_processamento": doc.get("status_processamento"),
                    "requer_auditoria_humana": doc.get("requer_auditoria_humana"),
                    "destino_principal": doc.get("destino_principal"),
                    "motivo_revisao": doc.get("motivo_revisao"),
                    "justificativa_roteamento": doc.get("justificativa_roteamento"),
                })
        elif doc_id:
            ids_vistos.add(doc_id)
            criado_em = doc.get("created_at")
            data_formatada = "-"
            if criado_em:
                try:
                    data_formatada = datetime.fromisoformat(criado_em).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    data_formatada = str(criado_em)[:16]

            status_original = (doc.get("status_processamento") or "concluido").lower()
            status_normalizado = "concluido"
            if status_original in {"na_fila", "pendente"}:
                status_normalizado = "na_fila"
            elif status_original in {"processando", "iniciado"}:
                status_normalizado = "processando"
            elif status_original in {"falhou", "erro"}:
                status_normalizado = "falhou"

            todos_documentos.append({
                "documento_id": doc_id,
                "arquivo": doc_id,
                "nome_original": doc.get("arquivo") or doc_id,
                "paciente_nome": doc.get("paciente_nome") or "",
                "paciente_cpf": doc.get("paciente_cpf") or "-",
                "data_hora": data_formatada,
                "data_iso": criado_em or "",
                "status": status_normalizado,
                "status_processamento": doc.get("status_processamento"),
                "canal_origem": doc.get("canal_origem") or "Interno",
                "requer_auditoria_humana": doc.get("requer_auditoria_humana"),
                "tipo_documento": doc.get("tipo_documento"),
                "nivel_prioridade": doc.get("nivel_prioridade"),
                "score_confianca": doc.get("score_confianca"),
                "destino_principal": doc.get("destino_principal"),
                "motivo_revisao": doc.get("motivo_revisao"),
                "justificativa_roteamento": doc.get("justificativa_roteamento"),
                "resultado": None,
                "erro": doc.get("erro"),
                "etapa_atual": doc.get("etapa_atual"),
            })

    # Alerta clínico no topo da tela para casos de Emergência ou Perigo
    exibir_alerta_global_se_necessario(todos_documentos)
    verificar_e_disparar_modal_alerta(todos_documentos)

    # KPI Summary Cards
    total_docs = len(todos_documentos)
    qtd_concluidos = sum(1 for d in todos_documentos if d.get("status") == "concluido")
    qtd_processando = sum(1 for d in todos_documentos if d.get("status") == "processando")
    qtd_revisao = sum(1 for d in todos_documentos if _aguarda_revisao_humana(d))
    qtd_falhas = sum(1 for d in todos_documentos if d.get("status") == "falhou")

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f"""
            <div class="analise-kpi-card">
                <span class="analise-kpi-label">Total de Documentos</span>
                <span class="analise-kpi-valor">{total_docs}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="analise-kpi-card">
                <span class="analise-kpi-label" style="color:#027A48;">Concluídos</span>
                <span class="analise-kpi-valor" style="color:#027A48;">{qtd_concluidos}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="analise-kpi-card">
                <span class="analise-kpi-label" style="color:#175CD3;">Processando</span>
                <span class="analise-kpi-valor" style="color:#175CD3;">{qtd_processando}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="analise-kpi-card">
                <span class="analise-kpi-label" style="color:#B54708;">Revisão</span>
                <span class="analise-kpi-valor" style="color:#B54708;">{qtd_revisao}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f"""
            <div class="analise-kpi-card">
                <span class="analise-kpi-label" style="color:#B42318;">Falhas</span>
                <span class="analise-kpi-valor" style="color:#B42318;">{qtd_falhas}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Painel de Filtros e Busca em Container Nativo
    with st.container(border=True):
        termo_busca = st.text_input(
            "Buscar na análise",
            placeholder="Buscar por paciente, arquivo, CPF, identificador (DOC-...) ou canal...",
            key="filtro_termo_analise",
        ).strip().lower()

        f_status, f_canal, f_ord = st.columns(3)

        with f_status:
            opcoes_status = ["Todos", "Concluído", "Processando", "Na fila", "Falhou"]
            filtro_status = st.selectbox(
                "Status",
                opcoes_status,
                key="sel_status_analise",
            )

        with f_canal:
            opcoes_canal = ["Todos", "WhatsApp", "Interno"]
            filtro_canal = st.selectbox(
                "Canal de Origem",
                opcoes_canal,
                key="sel_canal_analise",
            )

        with f_ord:
            filtro_ord = st.selectbox(
                "Ordenar por",
                ["Mais recentes primeiro", "Mais antigos primeiro"],
                key="sel_ord_analise",
            )

        tem_filtros_ativos = bool(
            termo_busca
            or st.session_state.get("sel_status_analise", "Todos") != "Todos"
            or st.session_state.get("sel_canal_analise", "Todos") != "Todos"
        )
        col_espaco, col_btn_limpar, col_btn_buscar = st.columns([3.6, 1.2, 1.2], vertical_alignment="center")
        with col_btn_limpar:
            if st.button("Limpar filtros", icon=":material/filter_alt_off:", use_container_width=True, disabled=not tem_filtros_ativos):
                st.session_state["filtro_termo_analise"] = ""
                st.session_state["sel_status_analise"] = "Todos"
                st.session_state["sel_canal_analise"] = "Todos"
                st.session_state["sel_ord_analise"] = "Mais recentes primeiro"
                st.rerun()
        with col_btn_buscar:
            if st.button("Buscar", icon=":material/search:", type="primary", use_container_width=True):
                st.rerun()

    # Aplica os filtros
    documentos_filtrados = [
        documento
        for documento in todos_documentos
        if corresponde_filtro(documento, filtro_status, termo_busca, filtro_canal)
    ]

    # Ordenação
    def chave_data(d: dict):
        val = d.get("data_iso") or ""
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return datetime.min

    if filtro_ord == "Mais recentes primeiro":
        documentos_filtrados.sort(key=chave_data, reverse=True)
    else:
        documentos_filtrados.sort(key=chave_data)

    # Ordenação estável: mantém a ordem temporal atual dentro de cada grupo.
    documentos_filtrados.sort(key=_aguarda_revisao_humana, reverse=True)

    # Se veio de redirecionamento para verificar paciente, abre automaticamente os detalhes
    doc_selecionado_analise = st.session_state.pop("documento_selecionado_analise", None)
    if doc_selecionado_analise:
        doc_alvo = next((d for d in todos_documentos if d.get("documento_id") == doc_selecionado_analise), None)
        if doc_alvo:
            exibir_modal_detalhes(doc_alvo)

    # Renderização da Tabela
    filtrados_count = len(documentos_filtrados)
    if total_docs == filtrados_count:
        st.caption(f"Mostrando todos os {filtrados_count} documento(s) encontrados.")
    else:
        st.caption(f"Mostrando {filtrados_count} de {total_docs} documento(s) com base nos filtros selecionados.")

    if not documentos_filtrados:
        st.info("Nenhum documento encontrado para os filtros selecionados.")
    else:
        proporcoes_colunas = [2.0, 1.95, 1.55, 1.4, 1.5, 1.2, 1.8]
        rotulos_colunas = [
            "Arquivo / Protocolo",
            "Paciente",
            "Estado Clínico",
            "Canal de Entrada",
            "Data/Hora",
            "Status",
            "Ações",
        ]

        with st.container():
            with st.container():
                cabecalho = st.columns(proporcoes_colunas, gap="small")
                for coluna, rotulo in zip(cabecalho, rotulos_colunas):
                    with coluna:
                        classe_titulo = "analise-tabela-titulo analise-tabela-titulo-acoes" if rotulo == "Ações" else "analise-tabela-titulo"
                        st.markdown(f"<div class='{classe_titulo}'>{rotulo}</div>", unsafe_allow_html=True)

            for indice, doc in enumerate(documentos_filtrados):
                with st.container():
                    colunas_linha = st.columns(proporcoes_colunas, gap="small", vertical_alignment="center")
                    c_arq, c_pac, c_estado, c_canal, c_data, c_status, c_acao = colunas_linha
                    doc_id = doc["documento_id"]
                    status_chave = doc.get("status", "na_fila")
                    classe_badge, rotulo_status = _formatar_badge_status(status_chave)
                    canal = doc.get("canal_origem", "Interno")
                    cpf_txt = doc.get("paciente_cpf", "-")
                    nome_pac_exibicao = _formatar_paciente_exibicao(doc)
                    cpf_html = (
                        f"<br><span style='font-size:0.75rem; color:#64748B;'>CPF: {escape(cpf_txt)}</span>"
                        if cpf_txt and cpf_txt != "-" and status_chave != "falhou" and nome_pac_exibicao not in {"-", "Em andamento..."}
                        else ""
                    )

                    with c_arq:
                        st.markdown(
                            f"<span class='analise-celula-truncada' style='font-size:0.86rem; font-weight:700; color:#0F172A; font-family:monospace;' title='{escape(doc_id)}'>{escape(doc['arquivo'])}</span>",
                            unsafe_allow_html=True,
                        )
                    with c_pac:
                        st.markdown(
                            f"<div style='line-height:1.25;'><span class='analise-celula-truncada' style='font-size:0.86rem; font-weight:600; color:#1E293B;' title='{escape(nome_pac_exibicao)}'>{escape(nome_pac_exibicao)}</span>{cpf_html}</div>",
                            unsafe_allow_html=True,
                        )
                    with c_estado:
                        st.markdown(obter_badge_estado_html(doc), unsafe_allow_html=True)
                    with c_canal:
                        st.markdown(_formatar_badge_canal(canal), unsafe_allow_html=True)
                    with c_data:
                        st.markdown(
                            f"<span style='font-size:0.80rem; color:#475467; white-space:nowrap;'>{escape(doc['data_hora'])}</span>",
                            unsafe_allow_html=True,
                        )
                    with c_status:
                        st.markdown(
                            f"<span class='badge-status {classe_badge}'>{rotulo_status}</span>",
                            unsafe_allow_html=True,
                        )
                    with c_acao:
                        with st.container(
                            horizontal=True,
                            horizontal_alignment="center",
                            gap="xxsmall",
                            vertical_alignment="center",
                        ):
                            if st.button(
                                "Detalhes",
                                key=f"btn_det_{doc_id}_{indice}",
                                type="tertiary",
                                width="content",
                            ):
                                exibir_modal_detalhes(doc)
                            if _aguarda_revisao_humana(doc):
                                if st.button(
                                    "/ Revisar",
                                    key=f"btn_revisar_{doc_id}_{indice}",
                                    type="tertiary",
                                    width="content",
                                ):
                                    st.session_state["auditoria_documento_selecionado"] = doc_id
                                    st.switch_page("pages/2_Auditoria_Humana.py")

                    st.markdown(
                        '<div style="height:1px; background:#F2F4F7; margin:4px 0 6px 0;"></div>',
                        unsafe_allow_html=True,
                    )
