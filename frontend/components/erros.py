import streamlit as st

from services.erros import ErroDeApi


def chamar_api_ou_parar(chamada, *argumentos, complemento: str | None = None, **opcoes):
    try:
        return chamada(*argumentos, **opcoes)
    except ErroDeApi as erro:
        mensagem = f"{erro} {complemento}" if complemento else str(erro)
        st.error(mensagem)

        nome_func = getattr(chamada, "__name__", "api")
        col_tentar, col_voltar = st.columns(2)
        with col_tentar:
            if st.button("Tentar novamente", icon=":material/refresh:", key=f"btn_erro_tentar_{nome_func}"):
                st.rerun()
        with col_voltar:
            if st.button("Voltar para o início", icon=":material/arrow_back:", key=f"btn_erro_voltar_{nome_func}"):
                for chave in (
                    "auditoria_documento_selecionado",
                    "lock_auditoria_atual",
                    "documento_expandido_id",
                ):
                    st.session_state.pop(chave, None)
                st.rerun()
        st.stop()
