from pathlib import Path

import streamlit as st

from components.modo_de_execucao import exibir_modo_na_barra_lateral

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
        st.image(CAMINHO_DA_LOGO, width=250)

        st.caption(DESCRICAO)

        st.markdown("**Como usar**")

        st.markdown(
            "\n".join(
                f"{numero}. {passo}"
                for numero, passo in enumerate(PASSOS, start=1)
            )
        )

        st.caption(AVISO)

        st.markdown("---")

        st.markdown(
            "<p style='text-align: center; font-size: 0.75rem; opacity: 0.8;'>"
            "Hackathon ONE G10 • Brasil 05"
            "</p>",
            unsafe_allow_html=True,
        )

        exibir_modo_na_barra_lateral()
