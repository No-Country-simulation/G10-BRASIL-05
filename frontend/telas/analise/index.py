"""Fluxo de interface da tela analise."""

def render() -> None:
    import streamlit as st
    from services.autenticacao import esta_autenticado

    if not esta_autenticado(st.session_state):
        st.switch_page("app.py")
        st.stop()

    from pathlib import Path
    from components.estilos import aplicar_css
    import base64
    from datetime import datetime
    from html import escape
    import io
    from PIL import Image, ImageOps
    import streamlit as st
    import streamlit.components.v1 as components

    from components.cards import exibir_resultado_da_triagem
    from components.erros import chamar_api_ou_parar
    from api import listar_documentos, obter_fonte_original, obter_status_triagem
    from telas.analise.dados import corresponde_filtro
    from services.triagem_event_stream import escutar_eventos_triagem, obter_url_stream_triagem

    st.title("Análise de Documentos")
    st.caption("Acompanhamento do processamento e extração clínica dos documentos.")

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
            # O acompanhamento por consulta autenticada continua disponível se SSE falhar.
            pass

    # Atualiza o estado ao abrir a página e quando um evento SSE provoca nova renderização.
    for item in trabalhos_sessao:
        if item.get("status") in {"na_fila", "processando"}:
            try:
                status_api = obter_status_triagem(item["documento_id"])
                if status_api:
                    novo_status = status_api.get("status", item["status"])
                    item["status"] = novo_status
                    if status_api.get("etapa_atual"):
                        item["etapa_atual"] = status_api["etapa_atual"]
                
                    # Se obteve resultado parcial de identificação cadastral
                    resultado_parcial = status_api.get("resultado_parcial") or {}
                    paciente_parcial = resultado_parcial.get("Paciente", {}).get("dados_documento", {})
                    if paciente_parcial.get("nome"):
                        item["paciente_nome"] = paciente_parcial["nome"]
                    if paciente_parcial.get("cpf"):
                        item["paciente_cpf"] = paciente_parcial["cpf"]

                    # Se concluiu
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

                    # Se falhou
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

    # Mapeamento unificado
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
                "paciente_nome": item.get("paciente_nome") or "Aguardando identificação",
                "paciente_cpf": item.get("paciente_cpf") or "-",
                "data_hora": item.get("data_envio") or "-",
                "status": item.get("status") or "na_fila",
                "canal_origem": item.get("canal_origem") or "Pronto Socorro",
                "resultado": item.get("resultado"),
                "erro": item.get("erro"),
            })

    for doc in docs_api:
        doc_id = doc.get("documento_id")
        if doc_id and doc_id not in ids_vistos:
            ids_vistos.add(doc_id)
            # Formata data
            criado_em = doc.get("created_at")
            data_formatada = "-"
            if criado_em:
                try:
                    data_formatada = datetime.fromisoformat(criado_em).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    data_formatada = str(criado_em)[:16]

            status_original = doc.get("status_processamento") or "concluido"
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
                "paciente_nome": doc.get("paciente_nome") or "Identificado",
                "paciente_cpf": doc.get("paciente_cpf") or "-",
                "data_hora": data_formatada,
                "status": status_normalizado,
                "canal_origem": doc.get("canal_origem") or "Pronto Socorro",
                "resultado": None,
                "erro": None,
            })

    # Barra de filtros
    aplicar_css(Path(__file__).with_name("style.css"))

    col_busca, col_filtro = st.columns([3, 2], vertical_alignment="bottom")

    with col_busca:
        termo_busca = st.text_input(
            "Buscar por nome ou palavra",
            placeholder="Buscar por paciente, arquivo, CPF ou ID...",
            label_visibility="visible",
        ).strip().lower()

    with col_filtro:
        opcoes_status = ["Todos", "Na fila", "Processando", "Concluído", "Falhou"]
        filtro_status = st.selectbox(
            "Filtrar por status",
            opcoes_status,
            index=0,
        )

    documentos_filtrados = [
        documento
        for documento in todos_documentos
        if corresponde_filtro(documento, filtro_status, termo_busca)
    ]

    # Modal para visualização de detalhes
    @st.dialog("Detalhes do Documento", width="large")
    def exibir_modal_detalhes(doc_info: dict):
        doc_id = doc_info.get("documento_id")
        st.caption(f"Identificador: {doc_id}")
    
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"**ID do Documento:** `{doc_info.get('documento_id', '-')}`")
            nome_orig = doc_info.get("nome_original")
            if nome_orig and nome_orig != doc_info.get("documento_id"):
                st.markdown(f"**Arquivo Original:** {nome_orig}")
            st.markdown(f"**Paciente:** {doc_info.get('paciente_nome', '-')}")
            st.markdown(f"**CPF:** {doc_info.get('paciente_cpf', '-')}")
        with col_d2:
            st.markdown(f"**Data de Envio:** {doc_info.get('data_hora', '-')}")
            st.markdown(f"**Canal de Origem:** {doc_info.get('canal_origem', '-')}")
            st.markdown(f"**Status:** {doc_info.get('status', '-').upper()}")

        st.divider()

        aba_clinica, aba_documento = st.tabs(["Resultado Clínico", "Documento Original"])

        with aba_clinica:
            resultado = doc_info.get("resultado")
            if not resultado and doc_info.get("status") == "concluido":
                # Tenta obter direto da API
                try:
                    status_api = obter_status_triagem(doc_id)
                    if status_api and status_api.get("resultado"):
                        resultado = status_api["resultado"]
                except Exception:
                    pass

            if resultado:
                exibir_resultado_da_triagem(resultado)
            elif doc_info.get("status") == "falhou":
                erro_msg = doc_info.get("erro") or "Ocorreu um erro no processamento deste documento."
                st.error(f"Motivo da falha: {erro_msg}")
            elif doc_info.get("status") == "processando":
                st.info("O documento ainda está sendo processado pela inteligência clínica.")
            else:
                st.info("Documento aguardando na fila de processamento.")

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
                st.info("Documento original não disponível ou ainda em processamento pelo servidor.")

    # Renderização da Tabela
    st.caption(f"{len(documentos_filtrados)} documento(s) encontrado(s)")

    if not documentos_filtrados:
        st.info("Nenhum documento encontrado para os filtros selecionados.")
    else:
        # Cabeçalho da tabela
        st.markdown(
            """
            <div class="tabela-container">
                <div class="tabela-cabecalho">
                    <div>Arquivo</div>
                    <div>Paciente</div>
                    <div>CPF</div>
                    <div>Data/Hora</div>
                    <div>Status</div>
                    <div style="text-align: right;">Ações</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        mapa_rotulos_status = {
            "na_fila": ("status-na-fila", "Na fila"),
            "processando": ("status-processando", "Processando"),
            "concluido": ("status-concluido", "Concluído"),
            "falhou": ("status-falhou", "Falhou"),
        }

        for indice, doc in enumerate(documentos_filtrados):
            doc_id = doc["documento_id"]
            status_chave = doc.get("status", "na_fila")
            classe_badge, rotulo_status = mapa_rotulos_status.get(
                status_chave, ("status-na-fila", status_chave.capitalize())
            )

            with st.container():
                c_arq, c_pac, c_cpf, c_data, c_status, c_acao = st.columns(
                    [2.5, 2.5, 1.5, 1.5, 1.4, 1],
                    vertical_alignment="center",
                )
                with c_arq:
                    st.markdown(
                        f"<span style='font-size:0.86rem; font-weight:600; color:#12304A;' title='{escape(doc_id)}'>{escape(doc['arquivo'])}</span>",
                        unsafe_allow_html=True,
                    )
                with c_pac:
                    st.markdown(
                        f"<span style='font-size:0.84rem; color:#344054;'>{escape(doc['paciente_nome'])}</span>",
                        unsafe_allow_html=True,
                    )
                with c_cpf:
                    st.markdown(
                        f"<span style='font-size:0.82rem; color:#475467;'>{escape(doc['paciente_cpf'])}</span>",
                        unsafe_allow_html=True,
                    )
                with c_data:
                    st.markdown(
                        f"<span style='font-size:0.80rem; color:#475467;'>{escape(doc['data_hora'])}</span>",
                        unsafe_allow_html=True,
                    )
                with c_status:
                    st.markdown(
                        f"<span class='badge-status {classe_badge}'>{rotulo_status}</span>",
                        unsafe_allow_html=True,
                    )
                with c_acao:
                    if st.button("Detalhes", key=f"btn_det_{doc_id}_{indice}", use_container_width=True):
                        exibir_modal_detalhes(doc)
            
                st.markdown(
                    '<div style="height:1px; background:#F2F4F7; margin:4px 0 6px 0;"></div>',
                    unsafe_allow_html=True,
                )
