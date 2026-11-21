"""Fluxo de interface da tela auditoria."""

def render() -> None:
    from datetime import datetime
    from html import escape
    import io
    from pathlib import Path
    from PIL import Image, ImageOps
    import streamlit as st
    import streamlit.components.v1 as components

    from services.autenticacao import esta_autenticado, obter_usuario_autenticado

    if not esta_autenticado(st.session_state):
        st.switch_page("app.py")
        st.stop()

    from components.estilos import aplicar_css
    from components.visualizador_documento import (
        modal_preview_documento,
        _renderizar_visualizador_pdf,
        _renderizar_folha_textual,
        DOCUMENTO_INDISPONIVEL,
    )
    from components.cards import exibir_item_de_auditoria
    from components.erros import chamar_api_ou_parar
    from services.erros import ErroDeApi
    from api import (
        bloquear_documento_auditoria,
        listar_fila_auditoria,
        listar_documentos,
        obter_fonte_original,
        registrar_decisao,
        desbloquear_documento_auditoria,
    )
    from utils.formatadores import nome_do_paciente, rotular_tipo_documento
    from utils.auditoria import (
        CAMPOS_EDITAVEIS,
        DECISAO_APROVAR,
        DECISAO_CORRIGIR,
        DECISAO_REJEITAR,
        DECISAO_REENVIAR,
        calcular_correcoes,
        extrair_valores_editaveis,
        humanizar_motivos_revisao,
        montar_decisao,
        ordenar_fila,
        validar_decisao,
    )

    CHAVE_DA_CONFIRMACAO = "confirmacao_da_auditoria"
    CHAVE_DO_LOCK_ATUAL = "lock_auditoria_atual"
    CHAVE_DOC_SELECIONADO = "auditoria_documento_selecionado"
    AVISO_DE_DECISAO_PENDENTE = (
        "O documento continua pendente na fila. Atualize a página para conferir antes de tentar de novo."
    )

    aplicar_css(Path(__file__).with_name("style.css"))

    def registrar_lock_auditor(documento_id: str) -> tuple[str, str]:
        """Obtém o auditor logado e registra o bloqueio em segundo plano."""
        usuario_logado = obter_usuario_autenticado(st.session_state) or {}
        nome_usuario = (usuario_logado.get("nome") or "Admin").strip()
        registro_usuario = (usuario_logado.get("registro") or "").strip()
        auditor = nome_usuario

        chave_auditor = f"auditor_{documento_id}"
        st.session_state[chave_auditor] = auditor

        # Registra lock automático de auditoria em segundo plano
        if auditor and st.session_state.get(CHAVE_DO_LOCK_ATUAL) != documento_id:
            try:
                bloquear_documento_auditoria(documento_id, auditor)
                st.session_state[CHAVE_DO_LOCK_ATUAL] = documento_id
            except Exception:
                pass

        return auditor, registro_usuario

    # Diálogo de detalhes para documentos já auditados
    @st.dialog("Detalhes da Auditoria", width="large")
    def exibir_modal_detalhes_auditado(doc_info: dict):
        doc_id = doc_info.get("documento_id")
        st.caption(f"Identificador: {doc_id}")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"**ID do Documento:** `{doc_id}`")
            st.markdown(f"**Paciente:** {doc_info.get('paciente_nome', '-')}")
            st.markdown(f"**CPF:** {doc_info.get('paciente_cpf', '-')}")
        with col_d2:
            st.markdown(f"**Tipo:** {doc_info.get('tipo_rotulado', '-')}")
            st.markdown(f"**Data de Registro:** {doc_info.get('data_hora', '-')}")
            st.markdown(
                "**Status da Auditoria:** <span class='badge-status status-auditado'>Já auditado</span>",
                unsafe_allow_html=True,
            )

        st.divider()

        aba_doc, aba_info = st.tabs(["Documento Original", "Informações da Auditoria"])
        with aba_doc:
            fonte = None
            try:
                fonte = obter_fonte_original(doc_id)
            except Exception:
                fonte = None

            if fonte:
                conteudo, mime, nome = fonte
                st.download_button(
                    "Baixar original",
                    data=conteudo,
                    file_name=nome or "documento_original",
                    mime=mime,
                    icon=":material/download:",
                    key=f"dl_aud_modal_{doc_id}",
                    use_container_width=True,
                )
                if mime.startswith("image/"):
                    try:
                        img = Image.open(io.BytesIO(conteudo))
                        img = ImageOps.exif_transpose(img)
                        st.image(img, caption=nome or "Documento original", use_container_width=True)
                    except Exception:
                        st.image(conteudo, caption=nome or "Documento original", use_container_width=True)
                elif mime == "application/pdf" or (nome and nome.lower().endswith(".pdf")):
                    _renderizar_visualizador_pdf(conteudo, altura=520)
                else:
                    try:
                        texto = conteudo.decode("utf-8")
                        st.text_area("Texto do documento", value=texto, height=400, disabled=True)
                    except Exception:
                        st.info("Arquivo disponível para visualização via download.")
            else:
                st.info("Documento original não disponível.")

        with aba_info:
            raw_doc = doc_info.get("item_completo") or {}
            st.markdown(f"**Status interno do processamento:** `{raw_doc.get('status_processamento', 'auditoria_concluida')}`")
            if raw_doc.get("dados_extraidos"):
                st.markdown("**Dados Clínicos Extraídos:**")
                st.json(raw_doc.get("dados_extraidos"))
            else:
                st.info("A auditoria deste documento foi concluída e a decisão humana foi integrada ao prontuário clínico.")

    # Carregamento de dados da API
    fila = []
    try:
        fila = ordenar_fila(listar_fila_auditoria() or [])
    except ErroDeApi as erro:
        st.title("Auditoria")
        st.caption("Revise os documentos que a triagem encaminhou para análise humana.")
        st.error(f"Não foi possível carregar a fila de auditoria no momento: {erro}")
        col_tentar, col_voltar = st.columns(2)
        with col_tentar:
            if st.button("Tentar novamente", icon=":material/refresh:", key="btn_erro_fila_tentar"):
                st.rerun()
        with col_voltar:
            if st.button("Voltar para a lista", icon=":material/arrow_back:", key="btn_erro_fila_voltar"):
                st.session_state.pop(CHAVE_DOC_SELECIONADO, None)
                st.session_state.pop(CHAVE_DO_LOCK_ATUAL, None)
                st.rerun()
        st.stop()
    docs_geral = []
    try:
        docs_geral = listar_documentos() or []
    except Exception:
        docs_geral = []

    # =========================================================================
    # ÁREA DE DETALHE / REVISÃO DO DOCUMENTO SELECIONADO
    # =========================================================================
    escolhido = st.session_state.get(CHAVE_DOC_SELECIONADO)
    if escolhido:
        item = next((i for i in fila if i.get("documento_id") == escolhido), None)
        if not item:
            st.session_state.pop(CHAVE_DOC_SELECIONADO, None)
            st.info(f"O documento {escolhido} não está mais aguardando auditoria.")
            st.rerun()

        # Link de retorno superior limpo
        st.markdown('<div class="auditoria-voltar-link">', unsafe_allow_html=True)
        if st.button("< Voltar para a lista", key="btn_voltar_auditoria"):
            st.session_state.pop(CHAVE_DOC_SELECIONADO, None)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Cabeçalho da revisão com metadados do documento
        dados_item = item.get("dados_extraidos") or {}
        paciente_nome_item = nome_do_paciente(dados_item.get("paciente")) or item.get("paciente_nome") or "Não identificado"
        tipo_item_rotulado = rotular_tipo_documento(item.get("tipo_documento")) or item.get("tipo_documento") or "Documento"

        # Auditor autenticado (fixo com base no usuário logado)
        auditor, registro_usuario = registrar_lock_auditor(escolhido)
        auditor_rotulo = f"{auditor} ({registro_usuario})" if registro_usuario else auditor

        col_tit, col_meta = st.columns([4, 2], vertical_alignment="bottom")
        with col_tit:
            st.markdown(f'<div class="auditoria-header-titulo">Auditoria do Documento: {escolhido}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="auditoria-header-sub">'
                f'Paciente: <strong>{escape(paciente_nome_item)}</strong> · '
                f'Tipo: <strong>{escape(tipo_item_rotulado)}</strong> · '
                f'Auditor: <strong>{escape(auditor_rotulo)}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_meta:
            st.markdown(
                """
                <div style="text-align:right; margin-bottom:16px;">
                    <span class="badge-status status-esperando">Aguardando Auditoria</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Motivo da revisão exibido logo abaixo do cabeçalho
        motivo_doc = item.get("motivo_revisao") or item.get("justificativa_roteamento")
        itens_humanizados = humanizar_motivos_revisao(motivo_doc)
        if len(itens_humanizados) > 1:
            corpo_motivo_banner = "".join(
                f"<div class='auditoria-motivo-item'>• {escape(m)}</div>"
                for m in itens_humanizados
            )
        else:
            corpo_motivo_banner = f"<div class='auditoria-motivo-item'>{escape(itens_humanizados[0])}</div>"

        st.markdown(
            f"""
            <div class="auditoria-banner-motivo">
                <div class="auditoria-banner-motivo-cabecalho">
                    <span class="auditoria-banner-motivo-tag">Motivo da revisão</span>
                </div>
                <div class="auditoria-banner-motivo-texto">
                    {corpo_motivo_banner}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Duas colunas equilibradas (50% / 50%)
        coluna_documento, coluna_resultado = st.columns(2, gap="large")

        # --- Coluna da Esquerda: Documento Original ---
        with coluna_documento:
            st.markdown(
                """
                <div class="auditoria-secao-titulo">
                    <span>Documento original</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            texto_doc = item.get("documento_texto") or DOCUMENTO_INDISPONIVEL
            fonte = None
            if item.get("fonte_original_disponivel"):
                fonte = chamar_api_ou_parar(obter_fonte_original, escolhido)

            # Barra de ferramentas do visualizador
            col_preview, col_down = st.columns(2, vertical_alignment="center")
            with col_preview:
                if st.button("Ampliar", icon=":material/visibility:", use_container_width=True, key=f"btn_preview_modal_{escolhido}"):
                    modal_preview_documento(escolhido, fonte, texto_doc)
            with col_down:
                if fonte:
                    conteudo, mime, nome = fonte
                    st.download_button(
                        "Baixar original",
                        data=conteudo,
                        file_name=nome or "documento_original.pdf",
                        mime=mime,
                        icon=":material/download:",
                        use_container_width=True,
                    )

            aba_visual, aba_texto = st.tabs(
                [
                    "Pré-visualização",
                    "Texto Extraído (OCR)",
                ]
            )
            with aba_visual:
                if fonte:
                    conteudo, mime, nome = fonte
                    if mime.startswith("image/"):
                        try:
                            img = Image.open(io.BytesIO(conteudo))
                            img = ImageOps.exif_transpose(img)
                            st.image(img, caption=nome or "Fonte original", use_container_width=True)
                        except Exception:
                            st.image(conteudo, caption=nome or "Fonte original", use_container_width=True)
                    elif mime == "application/pdf" or (nome and nome.lower().endswith(".pdf")):
                        _renderizar_visualizador_pdf(conteudo, altura=520)
                    else:
                        _renderizar_folha_textual(escolhido, texto_doc, nome)
                else:
                    _renderizar_folha_textual(escolhido, texto_doc)

            with aba_texto:
                st.text_area(
                    "Conteúdo textual OCR",
                    value=texto_doc,
                    height=450,
                    disabled=True,
                    key=f"documento_{escolhido}",
                    label_visibility="collapsed",
                )

        # --- Coluna da Direita: Decisão e Dados Clínicos ---
        with coluna_resultado:
            st.markdown(
                """
                <div class="auditoria-secao-titulo">
                    <span>Decisão do auditor</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            valores_atuais = extrair_valores_editaveis(item)
            tipo_doc_norm = str(item.get("tipo_documento") or "").strip().lower()
            eh_atestado = "atestado" in tipo_doc_norm

            with st.form(f"decisao_{escolhido}"):
                justificativa = st.text_area(
                    "Justificativa médica da decisão",
                    height=80,
                    key=f"justificativa_{escolhido}",
                    placeholder="Informe a justificativa médica (obrigatória para Rejeitar, Corrigir ou Pedir reenvio)...",
                )
                val_diag = st.text_area(
                    "Diagnóstico principal",
                    value=valores_atuais.get("diagnostico_principal", ""),
                    height=80,
                    key=f"ed_diag_{escolhido}",
                    placeholder="Diagnóstico principal identificado ou corrigido...",
                )

                with st.expander("Corrigir campos do paciente e médico"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        val_pac = st.text_input("Nome do paciente", value=valores_atuais.get("paciente_nome", ""), key=f"ed_pac_{escolhido}")
                        val_cpf = st.text_input("CPF do paciente", value=valores_atuais.get("paciente_cpf", ""), key=f"ed_cpf_{escolhido}")
                    with col_e2:
                        val_med = st.text_input("Médico solicitante", value=valores_atuais.get("medico_nome", ""), key=f"ed_med_{escolhido}")
                        val_crm = st.text_input("CRM", value=valores_atuais.get("crm", ""), key=f"ed_crm_{escolhido}")
                    val_cid = ""
                    if eh_atestado:
                        val_cid = st.text_input("CID-10 sugerido", value=valores_atuais.get("cid_sugerido", ""), key=f"ed_cid_{escolhido}")

                valores_editados = {
                    "paciente_nome": val_pac,
                    "paciente_cpf": val_cpf,
                    "medico_nome": val_med,
                    "crm": val_crm,
                    "diagnostico_principal": val_diag,
                    "cid_sugerido": val_cid if eh_atestado else valores_atuais.get("cid_sugerido", ""),
                }

                coluna_aprovar, coluna_rejeitar, coluna_corrigir, coluna_reenviar = st.columns(4)
                with coluna_aprovar:
                    aprovou = st.form_submit_button("Aprovar", type="primary", use_container_width=True)
                with coluna_rejeitar:
                    rejeitou = st.form_submit_button("Rejeitar", use_container_width=True)
                with coluna_corrigir:
                    corrigiu = st.form_submit_button("Corrigir", use_container_width=True)
                with coluna_reenviar:
                    pediu_reenvio = st.form_submit_button("Pedir reenvio", use_container_width=True)

            cliques = {
                DECISAO_APROVAR: aprovou,
                DECISAO_REJEITAR: rejeitou,
                DECISAO_CORRIGIR: corrigiu,
                DECISAO_REENVIAR: pediu_reenvio,
            }
            acao = next((nome for nome, clicou in cliques.items() if clicou), None)
            if acao is not None:
                correcoes = calcular_correcoes(valores_atuais, valores_editados)
                problema = validar_decisao(acao, auditor, justificativa, correcoes)
                if problema:
                    st.warning(problema)
                else:
                    decisao = montar_decisao(acao, auditor, justificativa, item.get("dados_extraidos") or {}, correcoes)
                    try:
                        resposta = registrar_decisao(escolhido, decisao)
                        st.session_state.pop(CHAVE_DO_LOCK_ATUAL, None)
                        st.session_state.pop(CHAVE_DOC_SELECIONADO, None)

                        st.session_state[CHAVE_DA_CONFIRMACAO] = {
                            "mensagem": f"{resposta.get('mensagem', 'Decisão registrada.')} Documento {escolhido}.",
                            "decisao": decisao,
                        }
                        st.rerun()
                    except ErroDeApi as erro:
                        st.error(f"{erro} {AVISO_DE_DECISAO_PENDENTE}")

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            st.markdown(
                """
                <div class="auditoria-secao-titulo">
                    <span>Extração clínica e triagem</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            exibir_item_de_auditoria(item)

        st.stop()

    # =========================================================================
    # VISÃO PADRÃO: LISTAGEM E TABELA DE AUDITORIA
    # =========================================================================
    st.title("Auditoria")
    st.caption("Revise os documentos que a triagem encaminhou para análise humana.")

    confirmacao_anterior = st.session_state.pop(CHAVE_DA_CONFIRMACAO, None)
    if confirmacao_anterior:
        st.success(confirmacao_anterior["mensagem"], icon=":material/check_circle:")
        with st.expander("Ver decisão enviada (JSON)"):
            st.json(confirmacao_anterior["decisao"])

    # Consolidação dos itens em lista unificada
    itens_auditoria = []
    ids_vistos = set()

    # 1. Documentos esperando auditoria
    for item_fila in fila:
        doc_id = item_fila.get("documento_id")
        if not doc_id:
            continue
        ids_vistos.add(doc_id)

        dados = item_fila.get("dados_extraidos") or {}
        paciente = dados.get("paciente")
        pac_nome = nome_do_paciente(paciente) or item_fila.get("paciente_nome") or "Não identificado"
        pac_cpf = (paciente.get("cpf") if isinstance(paciente, dict) else None) or item_fila.get("paciente_cpf") or "-"

        tipo_bruto = item_fila.get("tipo_documento") or "DOCUMENTO"
        tipo_fmt = rotular_tipo_documento(tipo_bruto) or tipo_bruto

        motivos_lista = humanizar_motivos_revisao(
            item_fila.get("motivo_revisao") or item_fila.get("justificativa_roteamento")
        )
        motivo_resumo = " · ".join(motivos_lista)

        criado_em = item_fila.get("created_at")
        data_fmt = "-"
        if criado_em:
            try:
                data_fmt = datetime.fromisoformat(str(criado_em)).strftime("%d/%m/%Y %H:%M")
            except Exception:
                data_fmt = str(criado_em)[:16]

        itens_auditoria.append({
            "documento_id": doc_id,
            "arquivo": doc_id,
            "paciente_nome": pac_nome,
            "paciente_cpf": pac_cpf,
            "tipo_rotulado": tipo_fmt,
            "motivo_revisao": motivo_resumo,
            "motivos_lista": motivos_lista,
            "data_hora": data_fmt,
            "status": "esperando_auditar",
            "status_rotulo": "Esperando auditar",
            "badge_classe": "status-esperando",
            "item_completo": item_fila,
        })

    # 2. Documentos já auditados
    for doc in docs_geral:
        doc_id = doc.get("documento_id")
        if not doc_id or doc_id in ids_vistos:
            continue

        st_proc = str(doc.get("status_processamento") or "")
        if st_proc.startswith("auditoria_"):
            ids_vistos.add(doc_id)

            criado_em = doc.get("created_at")
            data_fmt = "-"
            if criado_em:
                try:
                    data_fmt = datetime.fromisoformat(str(criado_em)).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    data_fmt = str(criado_em)[:16]

            tipo_bruto = doc.get("tipo_documento") or "DOCUMENTO"
            tipo_fmt = rotular_tipo_documento(tipo_bruto) or tipo_bruto

            motivos_lista = humanizar_motivos_revisao(
                doc.get("motivo_revisao") or doc.get("justificativa_roteamento")
            )
            motivo_resumo = " · ".join(motivos_lista)

            itens_auditoria.append({
                "documento_id": doc_id,
                "arquivo": doc_id,
                "paciente_nome": doc.get("paciente_nome") or "Não identificado",
                "paciente_cpf": doc.get("paciente_cpf") or "-",
                "tipo_rotulado": tipo_fmt,
                "motivo_revisao": motivo_resumo,
                "motivos_lista": motivos_lista,
                "data_hora": data_fmt,
                "status": "ja_auditado",
                "status_rotulo": "Já auditado",
                "badge_classe": "status-auditado",
                "item_completo": doc,
            })

    # Barra de busca e filtros
    col_busca, col_filtro = st.columns([3, 2], vertical_alignment="bottom")

    with col_busca:
        termo_busca = st.text_input(
            "Buscar por nome ou palavra",
            placeholder="Buscar por paciente, arquivo, tipo ou ID...",
            label_visibility="visible",
        ).strip().lower()

    with col_filtro:
        opcoes_status = ["Todos", "Esperando auditar", "Já auditado"]
        filtro_status = st.selectbox(
            "Filtrar por status",
            opcoes_status,
            index=0,
        )

    # Filtragem
    documentos_filtrados = []
    for doc in itens_auditoria:
        if filtro_status == "Esperando auditar" and doc["status"] != "esperando_auditar":
            continue
        if filtro_status == "Já auditado" and doc["status"] != "ja_auditado":
            continue
        if termo_busca:
            campos_busca = [
                doc.get("documento_id", ""),
                doc.get("arquivo", ""),
                doc.get("paciente_nome", ""),
                doc.get("paciente_cpf", ""),
                doc.get("tipo_rotulado", ""),
                doc.get("motivo_revisao", ""),
            ]
            if not any(termo_busca in str(c).lower() for c in campos_busca):
                continue
        documentos_filtrados.append(doc)

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
                    <div>Tipo</div>
                    <div>Motivo da Revisão</div>
                    <div>Data/Hora</div>
                    <div>Status</div>
                    <div style="text-align: right;">Ações</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for indice, doc in enumerate(documentos_filtrados):
            doc_id = doc["documento_id"]
            eh_esperando = doc["status"] == "esperando_auditar"

            with st.container():
                c_arq, c_pac, c_tipo, c_motivo, c_data, c_status, c_acao = st.columns(
                    [1.8, 1.8, 1.4, 3.0, 1.3, 1.3, 1.1],
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
                with c_tipo:
                    st.markdown(
                        f"<span style='font-size:0.82rem; color:#475467;'>{escape(doc['tipo_rotulado'])}</span>",
                        unsafe_allow_html=True,
                    )
                with c_motivo:
                    motivo_texto = doc["motivo_revisao"]
                    itens_motivo = doc.get("motivos_lista") or [motivo_texto]
                    if len(itens_motivo) > 1:
                        corpo_modal = "".join(
                            f"<div style='margin-bottom:6px;'>• {escape(item)}</div>"
                            for item in itens_motivo
                        )
                    else:
                        corpo_modal = f"<div>{escape(motivo_texto)}</div>"

                    html_motivo = f"""
                    <div class="motivo-hover-wrapper">
                        <div class="motivo-hover-trigger">
                            <span class="motivo-texto-resumo">{escape(motivo_texto)}</span>
                        </div>
                        <div class="motivo-modal-card">
                            <div class="motivo-modal-header">
                                <span class="motivo-modal-tag">Auditoria Clínica</span>
                                <span class="motivo-modal-titulo">Motivo da Revisão</span>
                            </div>
                            <div class="motivo-modal-body">
                                {corpo_modal}
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(html_motivo, unsafe_allow_html=True)
                with c_data:
                    st.markdown(
                        f"<span style='font-size:0.80rem; color:#475467;'>{escape(doc['data_hora'])}</span>",
                        unsafe_allow_html=True,
                    )
                with c_status:
                    st.markdown(
                        f"<span class='badge-status {doc['badge_classe']}'>{doc['status_rotulo']}</span>",
                        unsafe_allow_html=True,
                    )
                with c_acao:
                    if eh_esperando:
                        if st.button("Auditar", type="primary", key=f"btn_auditar_{doc_id}_{indice}", use_container_width=True):
                            st.session_state[CHAVE_DOC_SELECIONADO] = doc_id
                            st.rerun()
                    else:
                        if st.button("Detalhes", key=f"btn_det_aud_{doc_id}_{indice}", use_container_width=True):
                            exibir_modal_detalhes_auditado(doc)

                st.markdown(
                    '<div style="height:1px; background:#F2F4F7; margin:4px 0 6px 0;"></div>',
                    unsafe_allow_html=True,
                )
