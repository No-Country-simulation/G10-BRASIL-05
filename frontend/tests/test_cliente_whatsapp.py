import json

import httpx
import pytest

from services import cliente_whatsapp
from services.erros import ErroDeApi

PREFIXO = "/api/v1/webhook/evolution"


def _ok(corpo: dict):
    return lambda requisicao: httpx.Response(200, json=corpo)


def test_consulta_o_status_da_instancia(simular_api):
    status = {"instancia": "mediflow", "conectado": True, "estado": "open"}
    requisicoes = simular_api(_ok(status))

    assert cliente_whatsapp.obter_status() == status
    assert requisicoes[0].method == "GET"
    assert requisicoes[0].url.path == f"{PREFIXO}/status-instancia"


def test_status_com_a_evolution_fora_do_ar_e_devolvido_como_estado(simular_api):
    simular_api(_ok({"conectado": False, "estado": "offline"}))

    assert cliente_whatsapp.obter_status()["estado"] == "offline"


def test_status_com_o_backend_fora_do_ar_levanta_erro(simular_api):
    def falhar(requisicao):
        raise httpx.ConnectError("sem conexão")

    simular_api(falhar)

    with pytest.raises(ErroDeApi, match="Não foi possível conectar"):
        cliente_whatsapp.obter_status()


def test_gera_o_qrcode(simular_api):
    resposta = {"conectado": False, "sucesso": True, "base64": "QUJD"}
    requisicoes = simular_api(_ok(resposta))

    assert cliente_whatsapp.gerar_qrcode() == resposta
    assert requisicoes[0].method == "POST"
    assert requisicoes[0].url.path == f"{PREFIXO}/conectar"


def test_qrcode_de_instancia_ja_conectada_nao_e_erro(simular_api):
    simular_api(_ok({"conectado": True, "estado": "open"}))

    assert cliente_whatsapp.gerar_qrcode()["conectado"] is True


@pytest.mark.parametrize(
    "corpo",
    [
        {"conectado": False, "sucesso": False, "erro": "Instância indisponível"},
        {"conectado": False, "sucesso": True, "base64": None},
    ],
)
def test_qrcode_sem_imagem_levanta_erro(simular_api, corpo):
    simular_api(_ok(corpo))

    with pytest.raises(ErroDeApi, match="Não foi possível obter o QR Code"):
        cliente_whatsapp.gerar_qrcode()


@pytest.mark.parametrize("url, corpo_esperado", [(None, {}), ("http://backend/webhook", {"url": "http://backend/webhook"})])
def test_configura_o_webhook_com_ou_sem_url(simular_api, url, corpo_esperado):
    requisicoes = simular_api(_ok({"sucesso": True}))

    cliente_whatsapp.configurar_webhook(url)

    assert requisicoes[0].url.path == f"{PREFIXO}/configurar-webhook"
    assert json.loads(requisicoes[0].content) == corpo_esperado


@pytest.mark.parametrize(
    "funcao, mensagem",
    [
        (cliente_whatsapp.configurar_webhook, "Não foi possível configurar o webhook"),
        (cliente_whatsapp.desconectar, "Não foi possível desconectar o WhatsApp"),
    ],
)
def test_http_200_com_sucesso_falso_e_tratado_como_falha(simular_api, funcao, mensagem):
    simular_api(_ok({"sucesso": False, "erro": "Evolution recusou"}))

    with pytest.raises(ErroDeApi, match=f"{mensagem}.*Evolution recusou"):
        funcao()


def test_desconecta_a_sessao(simular_api):
    requisicoes = simular_api(_ok({"sucesso": True, "resposta": ""}))

    cliente_whatsapp.desconectar()

    assert requisicoes[0].url.path == f"{PREFIXO}/desconectar"


def test_envia_a_mensagem_de_teste(simular_api):
    requisicoes = simular_api(_ok({"status": "enviado", "numero": "5511999999999"}))

    resposta = cliente_whatsapp.enviar_mensagem_de_teste("5511999999999", "olá")

    assert resposta["status"] == "enviado"
    assert requisicoes[0].url.path == f"{PREFIXO}/enviar-teste"
    assert json.loads(requisicoes[0].content) == {"numero": "5511999999999", "texto": "olá"}


def test_falha_de_envio_do_backend_levanta_erro(simular_api):
    corpo = {"erro": {"codigo": "HTTP_502", "mensagem": "Não foi possível enviar a mensagem."}}
    simular_api(lambda r: httpx.Response(502, json=corpo))

    with pytest.raises(ErroDeApi, match="Não foi possível enviar a mensagem"):
        cliente_whatsapp.enviar_mensagem_de_teste("5511999999999", "olá")


def test_resposta_que_nao_e_objeto_levanta_erro(simular_api):
    simular_api(_ok([]))

    with pytest.raises(ErroDeApi, match="resposta inválida"):
        cliente_whatsapp.obter_status()


def test_detalhe_muito_longo_e_cortado(simular_api):
    simular_api(_ok({"sucesso": False, "erro": "x" * 1000}))

    with pytest.raises(ErroDeApi) as erro:
        cliente_whatsapp.desconectar()

    assert len(str(erro.value)) < 300
