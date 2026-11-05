import httpx
import pytest

from services import cliente_http

URL_DA_API_DE_TESTE = "http://api.teste"


@pytest.fixture(autouse=True)
def usar_modo_demonstracao_nos_testes(monkeypatch):
    monkeypatch.setenv("MODO_DEMONSTRACAO", "true")
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("API_TIMEOUT", raising=False)


@pytest.fixture
def modo_api_real(monkeypatch):
    monkeypatch.delenv("MODO_DEMONSTRACAO", raising=False)
    monkeypatch.setenv("API_BASE_URL", URL_DA_API_DE_TESTE)


@pytest.fixture
def simular_api(monkeypatch):
    def simular(tratador) -> list[httpx.Request]:
        requisicoes = []

        def registrar(requisicao: httpx.Request) -> httpx.Response:
            requisicoes.append(requisicao)
            return tratador(requisicao)

        def criar_cliente() -> httpx.Client:
            return httpx.Client(base_url=URL_DA_API_DE_TESTE, transport=httpx.MockTransport(registrar))

        monkeypatch.setattr(cliente_http, "_criar_cliente", criar_cliente)
        return requisicoes

    return simular


@pytest.fixture
def simular_rotas(simular_api):
    """Simula a API por rota: {(método, caminho): (status, corpo) ou função(requisição)}."""

    def simular(rotas: dict) -> list[httpx.Request]:
        def tratador(requisicao: httpx.Request) -> httpx.Response:
            rota = rotas.get((requisicao.method, requisicao.url.path))
            if rota is None:
                corpo = {"erro": {"codigo": "NAO_ENCONTRADO", "mensagem": f"Rota inesperada: {requisicao.method} {requisicao.url.path}"}}
                return httpx.Response(404, json=corpo)
            if callable(rota):
                return rota(requisicao)
            status, corpo = rota
            return httpx.Response(status, json=corpo)

        return simular_api(tratador)

    return simular
