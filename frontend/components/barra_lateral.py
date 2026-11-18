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

        with st.expander("💡 Como usar", expanded=False):
            for numero, passo in enumerate(PASSOS, start=1):
                st.markdown(f"**{numero}.** {passo}")

        st.markdown(
            """
            <div style="background: rgba(11, 60, 122, 0.05); border-left: 3px solid #009DBB; border-radius: 6px; padding: 10px 12px; margin: 12px 0 16px 0;">
                <div style="font-size: 0.72rem; font-weight: 700; color: #0B3C7A; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
                    ⚖️ Apoio à Decisão Clínica
                </div>
                <div style="font-size: 0.76rem; color: #334E68; line-height: 1.35;">
                    Ferramenta de suporte à triagem. A validação final cabe ao médico responsável.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-footer">
                <span class="sidebar-badge">
                    🏥 Hackathon ONE G10 • Brasil 05
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
