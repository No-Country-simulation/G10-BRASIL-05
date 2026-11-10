import pytest

from services.configuracao import (
    URL_PADRAO_DA_API,
    obter_tempo_limite_em_segundos,
    obter_url_do_backend,
    usar_dados_simulados,
)


@pytest.fixture
def ambiente_limpo(monkeypatch):
    monkeypatch.delenv("MODO_DEMONSTRACAO", raising=False)


@pytest.mark.usefixtures("ambiente_limpo")
def test_sem_configuracao_usa_a_api_real_e_nao_a_demonstracao():
    assert usar_dados_simulados() is False
    assert obter_url_do_backend() == URL_PADRAO_DA_API


@pytest.mark.parametrize("valor", ["true", "TRUE", " 1 ", "sim"])
def test_modo_demonstracao_so_liga_quando_pedido(monkeypatch, valor):
    monkeypatch.setenv("MODO_DEMONSTRACAO", valor)

    assert usar_dados_simulados() is True


@pytest.mark.parametrize("valor", ["", "false", "0", "nao", "talvez"])
def test_outros_valores_nao_ligam_a_demonstracao(monkeypatch, valor):
    monkeypatch.setenv("MODO_DEMONSTRACAO", valor)

    assert usar_dados_simulados() is False


@pytest.mark.usefixtures("ambiente_limpo")
def test_url_preenchida_nao_liga_a_demonstracao(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://localhost:9000")

    assert usar_dados_simulados() is False


@pytest.mark.parametrize("valor", ["", "   "])
def test_url_vazia_usa_a_url_padrao(monkeypatch, valor):
    monkeypatch.setenv("API_BASE_URL", valor)

    assert obter_url_do_backend() == URL_PADRAO_DA_API


def test_remove_espacos_e_barra_final_da_url(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", " http://servidor:9000/ ")

    assert obter_url_do_backend() == "http://servidor:9000"


def test_tempo_limite_padrao_e_de_60_segundos():
    assert obter_tempo_limite_em_segundos() == 60.0


@pytest.mark.parametrize(
    "valor, esperado",
    [("30", 30.0), ("2.5", 2.5), ("abc", 60.0), ("0", 60.0), ("-5", 60.0), ("", 60.0)],
)
def test_le_o_tempo_limite_da_variavel(monkeypatch, valor, esperado):
    monkeypatch.setenv("API_TIMEOUT", valor)

    assert obter_tempo_limite_em_segundos() == esperado
