"""Módulo centralizado para gestão e renderização de alertas clínicos de gravidade e pop-ups modais."""
from html import escape
import streamlit as st

ESTADO_EMERGENCIA = "emergencia"
ESTADO_PERIGO = "perigo"
ESTADO_ESTAVEL = "estavel"

CHAVE_ALERTAS_CIENTES = "alertas_clinicos_cientes"


def classificar_estado_clinico(doc: dict) -> tuple[str, str, str]:
    """Retorna (chave_estado, rotulo, classe_css).

    - emergencia: Estado crítico emergencial (risco iminente à vida, IAM, politrauma).
    - perigo: Estado de perigo / atenção (casos moderados, dor aguda, conflito medicamentoso, alergia).
    - estavel: Casos de rotina ou preventivos sem alterações críticas.
    """
    pri = str(doc.get("nivel_prioridade") or "").upper()
    dest = str(doc.get("destino_principal") or "")
    motivo = str(
        doc.get("motivo_revisao")
        or doc.get("justificativa_roteamento")
        or doc.get("erro")
        or ""
    ).lower()

    if (
        "EMERGENCIA" in pri
        or "Fila_Emergencia_Medica" in dest
        or "iam" in motivo
        or "infarto" in motivo
        or "parada" in motivo
        or "choque" in motivo
        or "grave" in motivo
    ):
        return ESTADO_EMERGENCIA, "EMERGÊNCIA", "badge-estado-emergencia"

    if (
        "URGENTE" in pri
        or "alergia" in motivo
        or "conflito" in motivo
        or "cuidado" in motivo
        or "risco" in motivo
        or "atenção" in motivo
        or "atencao" in motivo
    ):
        return ESTADO_PERIGO, "PERIGO", "badge-estado-perigo"

    return ESTADO_ESTAVEL, "ESTÁVEL", "badge-estado-estavel"


def obter_badge_estado_html(doc: dict) -> str:
    """Retorna o snippet HTML da badge de estado clínico para tabelas e modais."""
    _, rotulo, classe_css = classificar_estado_clinico(doc)
    return f'<span class="badge-estado {classe_css}">{escape(rotulo)}</span>'


@st.dialog("Alerta Clínico da IA", width="medium")
def modal_alerta_clinico_popup(doc: dict, chave_estado: str):
    """Modal pop-up que pula na frente da tela quando a IA detecta um paciente em emergência ou perigo."""
    doc_id = doc.get("documento_id", "DOC")
    nome_pac = doc.get("paciente_nome") or "Paciente não identificado"
    cpf_pac = doc.get("paciente_cpf") or "-"
    motivo = doc.get("justificativa_roteamento") or doc.get("motivo_revisao") or "Necessidade de avaliação médica prioritária."

    if chave_estado == ESTADO_EMERGENCIA:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 6px 0 16px 0;">
                <div style="width: 58px; height: 58px; border-radius: 50%; background: #FEE4E2; border: 2px solid #FDA29B; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center;">
                    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#D92D20" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                </div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #991B1B; letter-spacing: 0.02em; margin-bottom: 6px;">
                    ESTADO CRÍTICO EMERGENCIAL
                </div>
                <div style="font-size: 0.90rem; color: #475467; line-height: 1.45; margin-bottom: 14px;">
                    A inteligência clínica identificou um paciente em situação de emergência com risco imediato à saúde.
                </div>
            </div>
            <div style="background: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 8px; padding: 14px 16px; margin-bottom: 18px;">
                <div style="font-size: 0.86rem; color: #1E293B; line-height: 1.5;">
                    <div><strong>Paciente:</strong> {escape(nome_pac)}</div>
                    <div><strong>CPF:</strong> {escape(cpf_pac)}</div>
                    <div><strong>Protocolo:</strong> <code>{escape(doc_id)}</code></div>
                    <div style="margin-top: 8px; color: #991B1B; font-weight: 600;">
                        <strong>Conduta / Alerta:</strong> {escape(motivo)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Estou ciente / Atender paciente", type="primary", use_container_width=True, key=f"btn_ciente_modal_{doc_id}"):
                if CHAVE_ALERTAS_CIENTES not in st.session_state:
                    st.session_state[CHAVE_ALERTAS_CIENTES] = set()
                st.session_state[CHAVE_ALERTAS_CIENTES].add(doc_id)
                st.rerun()
        with c2:
            if st.button("Dispensar da sessão", use_container_width=True, key=f"btn_dispensar_modal_{doc_id}"):
                if CHAVE_ALERTAS_CIENTES not in st.session_state:
                    st.session_state[CHAVE_ALERTAS_CIENTES] = set()
                st.session_state[CHAVE_ALERTAS_CIENTES].add(doc_id)
                st.rerun()

    elif chave_estado == ESTADO_PERIGO:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 6px 0 16px 0;">
                <div style="width: 58px; height: 58px; border-radius: 50%; background: #FEF0C7; border: 2px solid #FEDF89; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center;">
                    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                </div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #92400E; letter-spacing: 0.02em; margin-bottom: 6px;">
                    ALERTA DE PERIGO E CUIDADO
                </div>
                <div style="font-size: 0.90rem; color: #475467; line-height: 1.45; margin-bottom: 14px;">
                    A inteligência clínica identificou inconformidades, conflito medicamentoso ou necessidade de cuidado especial.
                </div>
            </div>
            <div style="background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 8px; padding: 14px 16px; margin-bottom: 18px;">
                <div style="font-size: 0.86rem; color: #1E293B; line-height: 1.5;">
                    <div><strong>Paciente:</strong> {escape(nome_pac)}</div>
                    <div><strong>CPF:</strong> {escape(cpf_pac)}</div>
                    <div><strong>Protocolo:</strong> <code>{escape(doc_id)}</code></div>
                    <div style="margin-top: 8px; color: #92400E; font-weight: 600;">
                        <strong>Ponto de atenção:</strong> {escape(motivo)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Estou ciente / Verificar prescrição", type="primary", use_container_width=True, key=f"btn_ciente_modal_{doc_id}"):
                if CHAVE_ALERTAS_CIENTES not in st.session_state:
                    st.session_state[CHAVE_ALERTAS_CIENTES] = set()
                st.session_state[CHAVE_ALERTAS_CIENTES].add(doc_id)
                st.rerun()
        with c2:
            if st.button("Dispensar da sessão", use_container_width=True, key=f"btn_dispensar_modal_{doc_id}"):
                if CHAVE_ALERTAS_CIENTES not in st.session_state:
                    st.session_state[CHAVE_ALERTAS_CIENTES] = set()
                st.session_state[CHAVE_ALERTAS_CIENTES].add(doc_id)
                st.rerun()


def verificar_e_disparar_modal_alerta(documentos: list[dict]) -> None:
    """Verifica se há novos documentos críticos ou em perigo não visualizados e dispara o modal pop-up."""
    if CHAVE_ALERTAS_CIENTES not in st.session_state:
        st.session_state[CHAVE_ALERTAS_CIENTES] = set()

    cientes = st.session_state[CHAVE_ALERTAS_CIENTES]

    # Prioriza casos de emergência primeiro, depois casos de perigo
    for doc in documentos:
        doc_id = doc.get("documento_id")
        if not doc_id or doc_id in cientes:
            continue
        chave, _, _ = classificar_estado_clinico(doc)
        if chave == ESTADO_EMERGENCIA:
            modal_alerta_clinico_popup(doc, chave)
            return

    for doc in documentos:
        doc_id = doc.get("documento_id")
        if not doc_id or doc_id in cientes:
            continue
        chave, _, _ = classificar_estado_clinico(doc)
        if chave == ESTADO_PERIGO:
            modal_alerta_clinico_popup(doc, chave)
            return


def exibir_alerta_global_se_necessario(documentos: list[dict]) -> None:
    """Verifica uma lista de documentos e renderiza alertas no topo da tela se houver casos críticos."""
    criticos = []
    perigos = []

    for doc in documentos:
        chave, _, _ = classificar_estado_clinico(doc)
        if chave == ESTADO_EMERGENCIA and doc.get("status") in {"na_fila", "processando", "concluido", "esperando_auditar"}:
            criticos.append(doc)
        elif chave == ESTADO_PERIGO and doc.get("status") in {"na_fila", "processando", "concluido", "esperando_auditar"}:
            perigos.append(doc)

    if criticos:
        pacientes_txt = ", ".join(
            doc.get("paciente_nome") or doc.get("documento_id") for doc in criticos[:3]
        )
        sufixo = f" e outros {len(criticos) - 3}" if len(criticos) > 3 else ""
        st.markdown(
            f"""
            <div class="banner-alerta-emergencia">
                <div class="banner-alerta-titulo">ALERTA CRÍTICO: PACIENTE EM ESTADO DE EMERGÊNCIA DETECTADO</div>
                <div class="banner-alerta-corpo">
                    A inteligência clínica identificou <strong>{len(criticos)} paciente(s) em estado crítico emergencial</strong> ({escape(pacientes_txt)}{sufixo}).
                    Requer prioridade imediata no fluxo de atendimento.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if perigos and not criticos:
        pacientes_txt = ", ".join(
            doc.get("paciente_nome") or doc.get("documento_id") for doc in perigos[:3]
        )
        sufixo = f" e outros {len(perigos) - 3}" if len(perigos) > 3 else ""
        st.markdown(
            f"""
            <div class="banner-alerta-perigo">
                <div class="banner-alerta-titulo">ALERTA DE PERIGO: PACIENTE REQUER CUIDADO E ATENÇÃO CLÍNICA</div>
                <div class="banner-alerta-corpo">
                    Identificado(s) <strong>{len(perigos)} caso(s) com alerta de perigo / risco</strong> ({escape(pacientes_txt)}{sufixo}).
                    Verifique as inconsistências ou necessidades de monitoramento antes da conduta.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def exibir_alerta_individual(doc: dict) -> None:
    """Renderiza alerta detalhado individual para a tela de triagem ou modal."""
    chave, _, _ = classificar_estado_clinico(doc)
    paciente = doc.get("paciente_nome") or doc.get("documento_id", "Paciente")
    motivo = doc.get("justificativa_roteamento") or doc.get("motivo_revisao")

    if chave == ESTADO_EMERGENCIA:
        st.markdown(
            f"""
            <div class="banner-alerta-emergencia">
                <div class="banner-alerta-titulo">ESTADO CRÍTICO EMERGENCIAL DETECTADO</div>
                <div class="banner-alerta-corpo">
                    Paciente <strong>{escape(paciente)}</strong> classificado com risco imediato.
                    {f'<br><strong>Conduta / Alerta:</strong> {escape(motivo)}' if motivo else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif chave == ESTADO_PERIGO:
        st.markdown(
            f"""
            <div class="banner-alerta-perigo">
                <div class="banner-alerta-titulo">ALERTA DE PERIGO E ATENÇÃO CLÍNICA</div>
                <div class="banner-alerta-corpo">
                    Paciente <strong>{escape(paciente)}</strong> requer atenção moderada e cuidado farmacológico/diagnóstico.
                    {f'<br><strong>Ponto de atenção:</strong> {escape(motivo)}' if motivo else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
