from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app.py"


def _abrir_app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=30).run()


def test_app_abre_na_triagem_clinica():
    at = _abrir_app()

    assert not at.exception
    assert at.title[0].value == "Triagem Clínica"


def test_todas_as_paginas_estao_registradas_na_navegacao():
    codigo = APP.read_text(encoding="utf-8")

    nao_registradas = [p.name for p in (RAIZ / "pages").glob("*.py") if f"pages/{p.name}" not in codigo]

    assert nao_registradas == []


def test_modo_nao_e_exposto_na_tela_e_dados_ficticios_sao_identificados():
    at = _abrir_app()

    assert "MODO DEMONSTRAÇÃO" not in at.warning[0].value
    assert "Dados fictícios para teste" in at.warning[0].value
    assert not at.sidebar.warning
    assert not at.sidebar.success


def test_modo_real_nao_mostra_aviso_de_demonstracao(modo_api_real):
    at = _abrir_app()

    assert not at.exception
    assert not at.warning
    assert not at.sidebar.warning
    assert not at.sidebar.success
