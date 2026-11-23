"""Fluxo de interface da tela triagem clínica remodelada."""

def render() -> None:
    import base64
    from datetime import datetime, timezone
    from pathlib import Path
    import time

    import streamlit as st

    from services.autenticacao import esta_autenticado

    if not esta_autenticado(st.session_state):
        st.switch_page("app.py")
        st.stop()

    from components.estilos import aplicar_css
    from components.triagem_uploader import render_triagem_uploader
    from telas.triagem.arquivos import ArquivoCarregado
    from api.cliente_http import enfileirar_documentos, enfileirar_texto_documento
    from services.erros import ErroDeApi
    from utils.alertas_clinicos import verificar_e_disparar_modal_alerta
    from utils.requisicao import montar_requisicao

    aplicar_css(Path(__file__).with_name("style.css"))

    # Verifica se há alertas de emergência ativos para alertar de imediato
    verificar_e_disparar_modal_alerta(st.session_state.get("trabalhos_triagem", []))

    st.title("Triagem clínica")
    st.markdown(
        '<div class="triagem-subtitulo">Envie um documento clínico para análise e roteamento automático.</div>',
        unsafe_allow_html=True,
    )

    # Renderiza o card único centralizado com o componente de upload
    resultado = render_triagem_uploader(key="triagem_card_uploader")

    if resultado and isinstance(resultado, dict):
        acao = resultado.get("acao")
        agora_formatado = datetime.now().strftime("%d/%m/%Y %H:%M")
        agora_iso = datetime.now(timezone.utc).isoformat()
        novos_trabalhos = []

        if acao in ("analisar_arquivos", "analisar_texto"):
            agora_ts = time.time()
            ultimo_envio = st.session_state.get("ultimo_envio_triagem_ts")
            # Debounce simples (0.5s) para evitar submissões duplicadas acidentais por clique duplo
            if ultimo_envio is not None and (agora_ts - ultimo_envio) < 0.5:
                return

            st.session_state["ultimo_envio_triagem_ts"] = agora_ts

            info_envio = None
            if acao == "analisar_arquivos":
                arquivos_recebidos = resultado.get("arquivos") or []
                if arquivos_recebidos:
                    arquivos_carregados = [
                        ArquivoCarregado(
                            name=item["name"],
                            size=item["size"],
                            type=item.get("type") or "",
                            dados=base64.b64decode(item["data_b64"]),
                        )
                        for item in arquivos_recebidos
                        if item.get("data_b64")
                    ]
                    arquivos_validos = [a for a in arquivos_carregados if a.valido]
                    if arquivos_validos:
                        limite_lote_bytes = 75 * 1024 * 1024
                        if sum(a.size for a in arquivos_validos) > limite_lote_bytes:
                            if ultimo_envio is None:
                                st.session_state.pop("ultimo_envio_triagem_ts", None)
                            else:
                                st.session_state["ultimo_envio_triagem_ts"] = ultimo_envio
                            st.error(
                                "O tamanho total do lote excede o limite permitido para análise. Envie em lotes menores."
                            )
                            return
                        info_envio = {
                            "tipo": "arquivos",
                            "arquivos_validos": arquivos_validos,
                            "total": len(arquivos_validos),
                        }
            elif acao == "analisar_texto":
                texto = resultado.get("texto", "").strip()
                if texto:
                    canal_origem_texto = "Interno"
                    if texto.startswith("{"):
                        try:
                            import json
                            dados_json = json.loads(texto, strict=False)
                            if isinstance(dados_json, dict) and "documento_texto" in dados_json:
                                texto = str(dados_json["documento_texto"])
                                if dados_json.get("canal_origem"):
                                    canal_origem_texto = str(dados_json["canal_origem"])
                        except Exception:
                            pass
                        if '"documento_texto"' in texto:
                            import re
                            match_texto = re.search(r'"documento_texto"\s*:\s*"((?:[^"\\]|\\.)*)"', texto, re.DOTALL)
                            if match_texto:
                                try:
                                    texto = match_texto.group(1).encode("utf-8").decode("unicode_escape").strip()
                                except Exception:
                                    texto = match_texto.group(1).strip()
                                match_canal = re.search(r'"canal_origem"\s*:\s*"([^"]+)"', texto)
                                if match_canal:
                                    canal_origem_texto = match_canal.group(1).strip()
                    info_envio = {
                        "tipo": "texto",
                        "texto": texto,
                        "canal_origem": canal_origem_texto,
                        "total": 1,
                    }

            if info_envio:
                @st.dialog("Envio de Documentos")
                def modal_processamento_envio(dados_envio: dict):
                    total = dados_envio["total"]
                    rotulo_arqs = f"{total} documento(s)" if total > 1 else "1 documento"
                    container_modal = st.empty()
                    barra = st.progress(15)

                    # Etapa 1: Carregando com a mesma barra de progresso
                    with container_modal.container():
                        st.markdown(
                            f"""
                            <div style="text-align: center; padding: 12px 0;">
                                <div style="width: 52px; height: 52px; border-radius: 50%; background: #EFF8FF; border: 1px solid #B2DDFF; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center;">
                                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#175CD3" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                        <polyline points="17 8 12 3 7 8"></polyline>
                                        <line x1="12" y1="3" x2="12" y2="15"></line>
                                    </svg>
                                </div>
                                <div style="font-size: 1.15rem; font-weight: 700; color: #12304A; margin-bottom: 6px;">
                                    Enviando Documentos
                                </div>
                                <div style="font-size: 0.88rem; color: #475467; line-height: 1.45; margin-bottom: 16px;">
                                    Preparando e enviando {rotulo_arqs} para a inteligência clínica. Por favor, aguarde...
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    for pct in range(15, 45, 5):
                        barra.progress(pct)
                        time.sleep(0.01)

                    sucesso = False
                    erro_msg = None
                    novos_trabalhos = []

                    try:
                        if dados_envio["tipo"] == "arquivos":
                            resposta_lote = enfileirar_documentos(dados_envio["arquivos_validos"])
                            lote_id = resposta_lote.get("lote_id")
                            resultados_lote = resposta_lote.get("trabalhos") or [resposta_lote]
                            for indice, res in enumerate(resultados_lote):
                                nome = res.get("arquivo") or dados_envio["arquivos_validos"][indice].name
                                if res.get("status") == "na_fila":
                                    doc_id = res["documento_id"]
                                    novos_trabalhos.append({
                                        "documento_id": doc_id,
                                        "arquivo": doc_id,
                                        "nome_original": nome,
                                        "paciente_nome": "Aguardando identificação",
                                        "paciente_cpf": "-",
                                        "data_envio": agora_formatado,
                                        "data_iso": agora_iso,
                                        "status": "na_fila",
                                        "canal_origem": "Interno",
                                        "lote_id": lote_id,
                                    })
                                else:
                                    erro_msg = res.get("erro", "Não foi possível enfileirar o arquivo.")
                            sucesso = len(novos_trabalhos) > 0
                        else:
                            texto_envio = dados_envio["texto"]
                            canal_origem = dados_envio.get("canal_origem") or "Interno"
                            if texto_envio.startswith("{"):
                                try:
                                    import json
                                    dados_json = json.loads(texto_envio, strict=False)
                                    if isinstance(dados_json, dict) and "documento_texto" in dados_json:
                                        texto_envio = str(dados_json["documento_texto"])
                                        if dados_json.get("canal_origem"):
                                            canal_origem = str(dados_json["canal_origem"])
                                except Exception:
                                    pass
                                if '"documento_texto"' in texto_envio:
                                    import re
                                    match_texto = re.search(r'"documento_texto"\s*:\s*"((?:[^"\\]|\\.)*)"', texto_envio, re.DOTALL)
                                    if match_texto:
                                        try:
                                            texto_envio = match_texto.group(1).encode("utf-8").decode("unicode_escape").strip()
                                        except Exception:
                                            texto_envio = match_texto.group(1).strip()
                                        match_canal = re.search(r'"canal_origem"\s*:\s*"([^"]+)"', texto_envio)
                                        if match_canal:
                                            canal_origem = match_canal.group(1).strip()
                            requisicao = montar_requisicao(None, texto_envio, canal_origem=canal_origem)
                            resposta = enfileirar_texto_documento(requisicao)
                            doc_id = resposta["documento_id"]
                            novos_trabalhos.append({
                                "documento_id": doc_id,
                                "arquivo": doc_id,
                                "nome_original": "Texto clínico digitado",
                                "paciente_nome": "Aguardando identificação",
                                "paciente_cpf": "-",
                                "data_envio": agora_formatado,
                                "data_iso": agora_iso,
                                "status": "na_fila",
                                "canal_origem": canal_origem,
                                "lote_id": resposta.get("lote_id"),
                            })
                            sucesso = True
                    except ErroDeApi as erro:
                        erro_msg = str(erro)
                    except Exception as erro:
                        erro_msg = f"Erro no processamento: {erro}"

                    if sucesso:
                        if "trabalhos_triagem" not in st.session_state:
                            st.session_state["trabalhos_triagem"] = []
                        st.session_state["trabalhos_triagem"] = novos_trabalhos + st.session_state["trabalhos_triagem"]

                        # Etapa 2: Sucesso no mesmo card do modal com a mesma barra
                        rotulo_sucesso = f"{len(novos_trabalhos)} documento(s) enviado(s)" if len(novos_trabalhos) > 1 else "1 documento enviado"
                        with container_modal.container():
                            st.markdown(
                                f"""
                                <div style="text-align: center; padding: 12px 0;">
                                    <div style="width: 52px; height: 52px; border-radius: 50%; background: #ECFDF3; border: 1px solid #A6F4C5; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center;">
                                        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#027A48" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                            <polyline points="20 6 9 17 4 12"></polyline>
                                        </svg>
                                    </div>
                                    <div style="font-size: 1.15rem; font-weight: 700; color: #12304A; margin-bottom: 6px;">
                                        Documentos em Análise
                                    </div>
                                    <div style="font-size: 0.88rem; color: #475467; line-height: 1.45; margin-bottom: 16px;">
                                        {rotulo_sucesso} com sucesso. Os arquivos estão em análise pela inteligência clínica. Redirecionando para a tela de Análise...
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        for pct in range(45, 101, 5):
                            barra.progress(pct)
                            time.sleep(0.01)
                        st.switch_page("pages/analise.py")
                    else:
                        with container_modal.container():
                            st.error(f"Falha no envio: {erro_msg or 'Não foi possível processar o envio.'}")
                            if st.button("Fechar e tentar novamente", use_container_width=True):
                                st.rerun()

                modal_processamento_envio(info_envio)
