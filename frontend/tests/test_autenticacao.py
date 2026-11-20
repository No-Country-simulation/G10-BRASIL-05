from pathlib import Path

from streamlit.testing.v1 import AppTest

from services.autenticacao import (
    CHAVE_IS_AUTENTICADO,
    CHAVE_JWT_TOKEN,
    CHAVE_USUARIO_LOGADO,
    autenticar_com_api,
    decodificar_payload_jwt,
    deslogar,
    esta_autenticado,
    obter_cabecalho_autorizacao,
    obter_token_jwt,
    obter_usuario_autenticado,
    precisa_trocar_senha,
    validar_sessao_api,
)


class Resposta:
    status_code = 200
    is_error = False

    def json(self):
        return {"access_token": "servidor.assinatura", "usuario": {"id": "u1", "nome": "Ana", "email": "ana@example.org", "nivel": "MEDICO"}}


def test_login_usa_api_e_guarda_token_na_sessao(monkeypatch):
    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, path, json):
            assert path == "/api/v1/auth/login"
            assert json == {"email": "ana@example.org", "senha": "password"}
            return Resposta()

    monkeypatch.setattr("services.autenticacao.httpx.Client", Client)
    state = {}
    ok, _, user, token = autenticar_com_api(" Ana@Example.org ", "password", state)
    assert ok and user["id"] == "u1" and token == "servidor.assinatura"
    assert obter_token_jwt(state) == token
    assert obter_cabecalho_autorizacao(state) == {"Authorization": f"Bearer {token}"}


def test_login_falha_fechado_quando_api_indisponivel(monkeypatch):
    import httpx

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr("services.autenticacao.httpx.Client", Client)
    state = {}
    ok, _, user, token = autenticar_com_api("ana@example.org", "password", state)
    assert not ok and user is None and token is None and not state


def test_sessao_e_encerrada_se_api_nao_validar_token(modo_api_real, monkeypatch):
    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            response = Resposta()
            response.is_error = True
            return response

    monkeypatch.setattr("services.autenticacao.httpx.Client", Client)
    state = {CHAVE_IS_AUTENTICADO: True, CHAVE_JWT_TOKEN: "expired", CHAVE_USUARIO_LOGADO: {"id": "u1"}}
    assert not validar_sessao_api(state)
    assert not esta_autenticado(state)


def test_deslogar_limpa_sessao():
    state = {CHAVE_IS_AUTENTICADO: True, CHAVE_JWT_TOKEN: "token", CHAVE_USUARIO_LOGADO: {"id": "u1"}}
    deslogar(state)
    assert not esta_autenticado(state)
    assert obter_token_jwt(state) is None
    assert obter_usuario_autenticado(state) is None
    assert obter_cabecalho_autorizacao(state) == {}


def test_login_page_opens_without_errors():
    path = Path(__file__).resolve().parents[1] / "pages" / "0_Login.py"
    app = AppTest.from_file(str(path), default_timeout=30).run()
    assert not app.exception


def test_precisa_trocar_senha_identifica_flag_usuario_e_jwt():
    import base64
    import json

    # Caso 1: Sem usuário ou sessão vazia
    assert not precisa_trocar_senha({})
    assert not precisa_trocar_senha(None)

    # Caso 2: trocar_senha_obrigatorio = False
    state_ok = {
        CHAVE_IS_AUTENTICADO: True,
        CHAVE_USUARIO_LOGADO: {"id": "u1", "trocar_senha_obrigatorio": False},
    }
    assert not precisa_trocar_senha(state_ok)

    # Caso 3: trocar_senha_obrigatorio = True no usuario
    state_trocar = {
        CHAVE_IS_AUTENTICADO: True,
        CHAVE_USUARIO_LOGADO: {"id": "u1", "trocar_senha_obrigatorio": True},
    }
    assert precisa_trocar_senha(state_trocar)

    # Caso 4: Flag presente nas claims do JWT
    payload = {"sub": "1", "role": "MEDICO", "trocar_senha_obrigatorio": True}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    fake_token = f"header.{payload_b64}.signature"
    state_jwt = {
        CHAVE_IS_AUTENTICADO: True,
        CHAVE_USUARIO_LOGADO: {"id": "u1"},
        CHAVE_JWT_TOKEN: fake_token,
    }
    assert precisa_trocar_senha(state_jwt)

    # Caso 5: Se já trocou a senha na sessão
    state_jwt["mediflow_senha_trocada"] = True
    assert not precisa_trocar_senha(state_jwt)


def test_trocar_senha_page_opens_without_errors():
    path = Path(__file__).resolve().parents[1] / "pages" / "6_Trocar_Senha.py"
    app = AppTest.from_file(str(path), default_timeout=30).run()
    assert not app.exception
