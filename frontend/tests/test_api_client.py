import pytest

from services import api_client, cliente_http, cliente_mock, cliente_whatsapp
from services.erros import ErroDeApi

ROTEADAS_PELO_MODO = [
    ("enviar_documento", ({"documento_texto": "x"}, "arquivo-falso")),
    ("listar_documentos", ()),
    ("buscar_documento", ("DOC-1",)),
    ("listar_fila_auditoria", ()),
]

# (nome no api_client, módulo que atende com a API real, nome nesse módulo, argumentos)
EXIGEM_API_REAL = [
    ("registrar_decisao", cliente_http, "registrar_decisao", ("DOC-1", {"status_aprovacao": "aprovado"})),
    ("obter_status_whatsapp", cliente_whatsapp, "obter_status", ()),
    ("gerar_qrcode_whatsapp", cliente_whatsapp, "gerar_qrcode", ()),
    ("configurar_webhook_whatsapp", cliente_whatsapp, "configurar_webhook", ("http://backend/webhook",)),
    ("desconectar_whatsapp", cliente_whatsapp, "desconectar", ()),
    ("enviar_teste_whatsapp", cliente_whatsapp, "enviar_mensagem_de_teste", ("5511999999999", "teste")),
]


def _registrar_chamadas(monkeypatch, modulo, nome: str, resposta: str) -> list:
    chamadas = []

    def funcao_falsa(*argumentos):
        chamadas.append(argumentos)
        return resposta

    monkeypatch.setattr(modulo, nome, funcao_falsa)
    return chamadas


@pytest.mark.parametrize("nome, argumentos", ROTEADAS_PELO_MODO)
def test_modo_demonstracao_encaminha_para_o_cliente_simulado(monkeypatch, nome, argumentos):
    chamadas_http = _registrar_chamadas(monkeypatch, cliente_http, nome, "http")
    chamadas_mock = _registrar_chamadas(monkeypatch, cliente_mock, nome, "mock")

    assert getattr(api_client, nome)(*argumentos) == "mock"
    assert chamadas_mock == [argumentos]
    assert chamadas_http == []


@pytest.mark.usefixtures("modo_api_real")
@pytest.mark.parametrize("nome, argumentos", ROTEADAS_PELO_MODO)
def test_modo_real_encaminha_para_o_cliente_http(monkeypatch, nome, argumentos):
    chamadas_http = _registrar_chamadas(monkeypatch, cliente_http, nome, "http")
    chamadas_mock = _registrar_chamadas(monkeypatch, cliente_mock, nome, "mock")

    assert getattr(api_client, nome)(*argumentos) == "http"
    assert chamadas_http == [argumentos]
    assert chamadas_mock == []


@pytest.mark.parametrize("nome, modulo, nome_no_modulo, argumentos", EXIGEM_API_REAL)
def test_modo_demonstracao_recusa_acoes_que_gravam_ou_enviam(monkeypatch, nome, modulo, nome_no_modulo, argumentos):
    chamadas = _registrar_chamadas(monkeypatch, modulo, nome_no_modulo, "real")

    with pytest.raises(ErroDeApi, match="Nada foi salvo nem enviado"):
        getattr(api_client, nome)(*argumentos)

    assert chamadas == []


@pytest.mark.usefixtures("modo_api_real")
@pytest.mark.parametrize("nome, modulo, nome_no_modulo, argumentos", EXIGEM_API_REAL)
def test_modo_real_encaminha_acoes_para_a_api(monkeypatch, nome, modulo, nome_no_modulo, argumentos):
    chamadas = _registrar_chamadas(monkeypatch, modulo, nome_no_modulo, "real")
    chamadas_mock = _registrar_chamadas(monkeypatch, cliente_mock, nome_no_modulo, "mock") if hasattr(cliente_mock, nome_no_modulo) else []

    assert getattr(api_client, nome)(*argumentos) == "real"
    assert chamadas == [argumentos]
    assert chamadas_mock == []


@pytest.mark.usefixtures("modo_api_real")
def test_modo_real_nunca_cai_no_mock_quando_a_api_falha(simular_api):
    import httpx

    def falhar(requisicao):
        raise httpx.ConnectError("sem conexão")

    simular_api(falhar)

    for chamada in (api_client.listar_documentos, api_client.listar_fila_auditoria):
        with pytest.raises(ErroDeApi, match="Não foi possível conectar"):
            chamada()
    with pytest.raises(ErroDeApi, match="Não foi possível conectar"):
        api_client.enviar_documento({"tipo_arquivo": "TEXTO", "documento_texto": "TEP"})
    with pytest.raises(ErroDeApi, match="Não foi possível conectar"):
        api_client.registrar_decisao("DOC-1", {"status_aprovacao": "aprovado"})
