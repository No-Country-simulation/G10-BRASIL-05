import pytest

from services.configuracao import (
    TEMPO_LIMITE_PADRAO_EM_SEGUNDOS,
    URL_PADRAO_DA_API,
    obter_ambiente,
    obter_tempo_limite_em_segundos,
    obter_url_do_backend,
    usar_dados_simulados,
)
from services.erros import ErroDeConfiguracao


@pytest.fixture(autouse=True)
def ambiente_local(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("MODO_DEMONSTRACAO", raising=False)
    monkeypatch.delenv("API_URL_PRODUCTION", raising=False)
    monkeypatch.delenv("API_URL_LOCAL", raising=False)


def test_sem_configuracao_usa_api_local_e_nao_demonstracao():
    assert obter_ambiente() == "local"
    assert usar_dados_simulados() is False
    assert obter_url_do_backend() == URL_PADRAO_DA_API


@pytest.mark.parametrize("valor", ["true", "TRUE", " 1 ", "sim"])
def test_modo_demonstracao_so_liga_quando_pedido_em_local(monkeypatch, valor):
    monkeypatch.setenv("MODO_DEMONSTRACAO", valor)

    assert usar_dados_simulados() is True


@pytest.mark.parametrize("valor", ["", "false", "0", "nao", "talvez"])
def test_outros_valores_nao_ligam_a_demonstracao(monkeypatch, valor):
    monkeypatch.setenv("MODO_DEMONSTRACAO", valor)

    assert usar_dados_simulados() is False


def test_ambiente_local_seleciona_url_local(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("API_URL_LOCAL", " http://localhost:9000/ ")
    monkeypatch.setenv("API_URL_PRODUCTION", "https://api.exemplo.invalid")

    assert obter_url_do_backend() == "http://localhost:9000"


def test_ambiente_producao_seleciona_url_producao(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_URL_LOCAL", "http://localhost:8000")
    monkeypatch.setenv("API_URL_PRODUCTION", " https://api.exemplo.invalid/ ")

    assert obter_ambiente() == "production"
    assert obter_url_do_backend() == "https://api.exemplo.invalid"
    assert usar_dados_simulados() is False


def test_producao_sem_url_nao_cai_para_url_local(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_URL_LOCAL", "http://localhost:8000")
    monkeypatch.delenv("API_URL_PRODUCTION", raising=False)

    with pytest.raises(ErroDeConfiguracao, match="não usará a URL local"):
        obter_url_do_backend()


def test_producao_bloqueia_dados_simulados(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MODO_DEMONSTRACAO", "true")

    with pytest.raises(ErroDeConfiguracao, match="só pode ser ativado"):
        usar_dados_simulados()


def test_ambiente_desconhecido_falha_claramente(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ErroDeConfiguracao, match="APP_ENV inválido"):
        obter_ambiente()


@pytest.mark.parametrize("ambiente", ["production", "prod"])
def test_aliases_de_producao_sao_aceitos(monkeypatch, ambiente):
    monkeypatch.setenv("APP_ENV", ambiente)
    monkeypatch.setenv("API_URL_PRODUCTION", "https://api.exemplo.invalid")

    assert obter_ambiente() == "production"
    assert obter_url_do_backend() == "https://api.exemplo.invalid"


@pytest.mark.parametrize("valor", ["30", "2.5"])
def test_le_tempo_limite_positivo(monkeypatch, valor):
    monkeypatch.setenv("API_TIMEOUT", valor)

    assert obter_tempo_limite_em_segundos() == float(valor)


@pytest.mark.parametrize("valor", ["abc", "0", "-5", ""])
def test_tempo_limite_invalido_usa_padrao(monkeypatch, valor):
    monkeypatch.setenv("API_TIMEOUT", valor)

    assert obter_tempo_limite_em_segundos() == TEMPO_LIMITE_PADRAO_EM_SEGUNDOS
