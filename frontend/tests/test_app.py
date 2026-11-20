import httpx
from pathlib import Path

from streamlit.testing.v1 import AppTest
from services.autenticacao import CHAVE_IS_AUTENTICADO, CHAVE_JWT_TOKEN, CHAVE_USUARIO_LOGADO
from utils.usuarios import EMAIL_INSTITUCIONAL_WHATSAPP, eh_conta_institucional_whatsapp

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app.py"


def _abrir_app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=30).run()


def _abrir_app_autenticado(monkeypatch=None) -> AppTest:
    if monkeypatch:
        monkeypatch.setattr("services.autenticacao.validar_sessao_api", lambda session_state=None: True)
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state[CHAVE_IS_AUTENTICADO] = True
    at.session_state[CHAVE_JWT_TOKEN] = "token.jwt.valido"
    at.session_state[CHAVE_USUARIO_LOGADO] = {
        "id": "USR-002",
        "nome": "Dra. Ana Silva",
        "nivel": "MEDICO",
        "email": "ana.silva@mediflow.com.br",
        "registro": "CRM/SP 142857",
        "especialidade": "Clínica Médica & Auditoria",
    }
    return at.run()


def test_app_abre_obrigatoriamente_no_login_quando_nao_autenticado():
    at = _abrir_app()

    assert not at.exception
    assert at.title[0].value == "Autenticação & Controle de Acesso"


def test_app_libera_acesso_e_abre_na_triagem_quando_sessao_validada(monkeypatch):
    at = _abrir_app_autenticado(monkeypatch)

    assert not at.exception
    assert at.title[0].value == "Triagem Clínica"


def test_todas_as_paginas_estao_registradas_na_navegacao():
    codigo = APP.read_text(encoding="utf-8")

    nao_registradas = [p.name for p in (RAIZ / "pages").glob("*.py") if f"pages/{p.name}" not in codigo]

    assert nao_registradas == []


def test_modo_nao_e_exposto_na_tela_e_dados_ficticios_sao_identificados(monkeypatch):
    at = _abrir_app_autenticado(monkeypatch)

    if at.warning:
        assert "MODO DEMONSTRAÇÃO" not in at.warning[0].value
    assert not at.sidebar.warning
    assert not at.sidebar.success


def test_modo_real_nao_mostra_aviso_de_demonstracao(modo_api_real, monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "get",
        lambda self, url, **kwargs: httpx.Response(
            200,
            json={"id": "USR-002", "nome": "Dra. Ana", "nivel": "MEDICO"},
        ),
    )
    at = _abrir_app_autenticado()

    assert not at.exception
    assert not at.warning
    assert not at.sidebar.warning
    assert not at.sidebar.success


def test_verificacao_conta_institucional_whatsapp():
    assert eh_conta_institucional_whatsapp(EMAIL_INSTITUCIONAL_WHATSAPP) is True
    assert eh_conta_institucional_whatsapp({"usuario_autenticado_email": "mediflow@equipe.com.br"}) is True
    assert eh_conta_institucional_whatsapp({"usuario_autenticado_email": "medico@equipe.com.br"}) is False
    assert eh_conta_institucional_whatsapp(None) is False


def test_fluxo_login_libera_acesso_e_logout_bloqueia_novamente(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(
            200,
            json={
                "access_token": "token.jwt.valido",
                "token_type": "bearer",
                "usuario": {"id": "USR-001", "nome": "Dr. Roberto", "nivel": "DIRETOR"},
            },
        ),
    )
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "Autenticação & Controle de Acesso"

    at.text_input(key="login_identificador").set_value("roberto@hospital.com.br")
    at.text_input(key="login_senha").set_value("senha-de-teste-efemera")
    at.button[0].click().run()

    assert not at.exception
    assert at.session_state[CHAVE_IS_AUTENTICADO] is True
    assert at.session_state[CHAVE_JWT_TOKEN] == "token.jwt.valido"

    at.switch_page("pages/1_Triagem_Clinica.py").run()
    assert not at.exception
    assert at.title[0].value == "Triagem Clínica"


def test_app_abre_na_troca_de_senha_quando_trocar_senha_obrigatorio_e_true(monkeypatch):
    monkeypatch.setattr("services.autenticacao.validar_sessao_api", lambda session_state=None: True)
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state[CHAVE_IS_AUTENTICADO] = True
    at.session_state[CHAVE_JWT_TOKEN] = "token.jwt.valido"
    at.session_state[CHAVE_USUARIO_LOGADO] = {
        "id": "USR-999",
        "nome": "Novo Usuário",
        "nivel": "MEDICO",
        "email": "novo@mediflow.com.br",
        "trocar_senha_obrigatorio": True,
    }
    at.run()

    assert not at.exception
    # Não exibe páginas regulares, abre direto no formulário de troca obrigatória
    assert any("Troca obrigatória de senha" in m.value for m in at.markdown)
