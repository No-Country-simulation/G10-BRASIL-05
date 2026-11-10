import streamlit as st

from services.configuracao import obter_url_do_backend, usar_dados_simulados

AVISO_DA_PAGINA = (
    "**MODO DEMONSTRAÇÃO:** os dados desta tela são fictícios. Decisões de auditoria e a "
    "integração com o WhatsApp não funcionam neste modo. "
    "Para usar a API real, deixe `MODO_DEMONSTRACAO` vazio no `.env`."
)


def exibir_modo_na_barra_lateral() -> None:
    with st.sidebar:
        if usar_dados_simulados():
            st.warning("**Modo demonstração**\n\nDados fictícios. Nada é enviado nem salvo.", icon="🧪")
        else:
            st.success("**Modo API (dados reais)**", icon="🔌")
            st.caption(obter_url_do_backend())


def exibir_aviso_de_demonstracao() -> None:
    if usar_dados_simulados():
        st.warning(AVISO_DA_PAGINA, icon="🧪")
