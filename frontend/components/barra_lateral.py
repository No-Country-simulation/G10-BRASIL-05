from pathlib import Path

import streamlit as st

CAMINHO_DA_LOGO = Path(__file__).resolve().parents[1] / "assets" / "logo.png"

DESCRICAO = "Triagem inteligente de documentos clínicos."

PASSOS = (
    "Envie o documento na **Triagem Clínica**.",
    "Veja a classificação, os dados extraídos e o destino.",
    "Casos duvidosos seguem para a **Auditoria**.",
)

AVISO = "O MediFlow apoia a triagem e não substitui a decisão do médico."


def exibir_barra_lateral() -> None:
    with st.sidebar:
        st.caption(DESCRICAO)

        with st.expander("Guia rápido de uso", expanded=False):
            passos_html = "".join(
                f"""
                <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:8px;">
                    <span style="background:#009DBB; color:#ffffff; font-size:0.68rem; font-weight:700; border-radius:50%; min-width:18px; height:18px; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; margin-top:2px;">{num}</span>
                    <span style="font-size:0.78rem; color:#12304A; line-height:1.35;">{passo}</span>
                </div>
                """
                for num, passo in (
                    ("1", "Envie o documento na <strong>Triagem Clínica</strong>."),
                    ("2", "Confira a classificação, dados extraídos e destino."),
                    ("3", "Casos com alertas ou inconsistências seguem para a <strong>Auditoria</strong>."),
                )
            )
            st.markdown(passos_html, unsafe_allow_html=True)

        st.markdown(
            """
            <div style="background: rgba(11, 60, 122, 0.04); border-left: 3px solid #009DBB; border-radius: 6px; padding: 10px 12px; margin: 12px 0 16px 0;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #0B3C7A; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#009DBB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        <path d="M12 8v4"/>
                        <path d="M12 16h.01"/>
                    </svg>
                    Apoio à Decisão Clínica
                </div>
                <div style="font-size: 0.75rem; color: #334E68; line-height: 1.35;">
                    Ferramenta de suporte à triagem. A validação e a conduta final cabem ao médico responsável.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-footer">
                <span class="sidebar-badge">
                    <svg width="8" height="8" viewBox="0 0 24 24" fill="#009DBB" style="display:inline-block; vertical-align:middle; margin-right:5px;">
                        <circle cx="12" cy="12" r="10" />
                    </svg>
                    Hackathon ONE G10 • Brasil 05
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
