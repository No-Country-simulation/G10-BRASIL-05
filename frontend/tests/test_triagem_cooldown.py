import time
from unittest.mock import MagicMock, patch

import pytest

from services.autenticacao import (
    CHAVE_IS_AUTENTICADO,
    CHAVE_JWT_TOKEN,
    CHAVE_USUARIO_LOGADO,
)


def test_cooldown_bloqueia_segundo_envio_em_menos_de_30_segundos(monkeypatch):
    from telas.triagem.index import render

    mock_st = MagicMock()
    agora = time.time()
    mock_st.session_state = {
        CHAVE_IS_AUTENTICADO: True,
        CHAVE_JWT_TOKEN: "token_teste",
        CHAVE_USUARIO_LOGADO: {"id": "u1", "nome": "Dr. Teste"},
        "ultimo_envio_triagem_ts": agora - 10,  # 10s atras -> ainda em cooldown
    }

    monkeypatch.setattr(
        "components.triagem_uploader.render_triagem_uploader",
        lambda key: {"acao": "analisar_arquivos", "arquivos": []},
    )
    mock_enfileirar = MagicMock()
    monkeypatch.setattr("api.enfileirar_documentos", mock_enfileirar)

    with patch("streamlit.session_state", mock_st.session_state), \
         patch("streamlit.warning") as mock_warning, \
         patch("streamlit.title"), \
         patch("streamlit.markdown"):
        render()

    assert not mock_enfileirar.called
    assert mock_warning.called
    msg_aviso = mock_warning.call_args[0][0]
    assert "Aguarde" in msg_aviso or "aguarde" in msg_aviso


def test_cooldown_permite_envio_apos_30_segundos(monkeypatch):
    from telas.triagem.index import render

    agora = time.time()
    mock_session_state = {
        CHAVE_IS_AUTENTICADO: True,
        CHAVE_JWT_TOKEN: "token_teste",
        CHAVE_USUARIO_LOGADO: {"id": "u1", "nome": "Dr. Teste"},
        "ultimo_envio_triagem_ts": agora - 35,  # 35s atras -> fora do cooldown
    }

    monkeypatch.setattr(
        "components.triagem_uploader.render_triagem_uploader",
        lambda key: {"acao": "analisar_texto", "texto": "Paciente com febre e tosse"},
    )
    mock_enfileirar_texto = MagicMock(return_value={"documento_id": "doc123", "lote_id": "lote1"})
    monkeypatch.setattr("api.enfileirar_texto_documento", mock_enfileirar_texto)
    monkeypatch.setattr("utils.requisicao.montar_requisicao", lambda x, y: MagicMock())

    with patch("streamlit.session_state", mock_session_state), \
         patch("streamlit.title"), \
         patch("streamlit.markdown"), \
         patch("streamlit.dialog", lambda title: (lambda f: f)), \
         patch("streamlit.switch_page") as mock_switch_page:
        render()

    assert mock_enfileirar_texto.called
    assert mock_session_state["ultimo_envio_triagem_ts"] >= agora
    assert mock_switch_page.called
    assert mock_switch_page.call_args[0][0] == "pages/analise.py"


def test_triagem_bloqueia_lote_acima_de_75mb(monkeypatch):
    import base64
    from telas.triagem.index import render

    mock_session_state = {
        CHAVE_IS_AUTENTICADO: True,
        CHAVE_JWT_TOKEN: "token_teste",
        CHAVE_USUARIO_LOGADO: {"id": "u1", "nome": "Dr. Teste"},
    }

    conteudo_b64 = base64.b64encode(b"dummy").decode("utf-8")
    tamanho_cada = int(9.5 * 1024 * 1024)
    arquivos_excesso = [
        {
            "name": f"doc_{i}.pdf",
            "size": tamanho_cada,
            "type": "application/pdf",
            "data_b64": conteudo_b64,
        }
        for i in range(8)
    ]

    monkeypatch.setattr(
        "components.triagem_uploader.render_triagem_uploader",
        lambda key: {"acao": "analisar_arquivos", "arquivos": arquivos_excesso},
    )
    mock_enfileirar = MagicMock()
    monkeypatch.setattr("api.enfileirar_documentos", mock_enfileirar)

    with patch("streamlit.session_state", mock_session_state), \
         patch("streamlit.title"), \
         patch("streamlit.markdown"), \
         patch("streamlit.error") as mock_error:
        render()

    assert not mock_enfileirar.called
    assert mock_error.called
    msg_erro = mock_error.call_args[0][0]
    assert "O tamanho total do lote excede o limite permitido para análise. Envie em lotes menores." in msg_erro
    assert "ultimo_envio_triagem_ts" not in mock_session_state
