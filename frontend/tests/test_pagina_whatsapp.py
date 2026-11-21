import base64
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

PAGINA = Path(__file__).resolve().parents[1] / "pages" / "4_WhatsApp_Evolution.py"
PREFIXO = "/api/v1/webhook/evolution"
STATUS = ("GET", f"{PREFIXO}/status-instancia")
QR_CODE_EM_BASE64 = base64.b64encode(
    base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
).decode()

CONECTADO = {"instancia": "mediflow", "conectado": True, "estado": "open"}
DESCONECTADO = {"instancia": "mediflow", "conectado": False, "estado": "close"}
EVOLUTION_FORA_DO_AR = {"instancia": "mediflow", "conectado": False, "estado": "offline"}


def _abrir() -> AppTest:
    return AppTest.from_file(str(PAGINA), default_timeout=30).run()


def _clicar(at: AppTest, rotulo: str) -> AppTest:
    return next(botao for botao in at.button if botao.label == rotulo).click().run()


def _campo(at: AppTest, rotulo: str):
    return next(campo for campo in at.text_input if campo.label.startswith(rotulo))


def _erros(at: AppTest) -> list[str]:
    return [erro.value for erro in at.error]


def _erro_de_conexao(requisicao):
    raise httpx.ConnectError("sem conexão")


def test_em_demonstracao_informa_que_nao_ha_whatsapp():
    at = _abrir()

    assert not at.exception
    assert "não está disponível no modo demonstração" in at.info[0].value
    assert not at.button


@pytest.mark.usefixtures("modo_api_real")
def test_com_o_backend_fora_do_ar_mostra_o_erro(simular_api):
    simular_api(_erro_de_conexao)

    at = _abrir()

    assert not at.exception
    assert "Não foi possível conectar à API" in at.error[0].value
    assert not at.button


@pytest.mark.usefixtures("modo_api_real")
def test_com_a_evolution_fora_do_ar_mostra_o_estado_real(simular_rotas):
    simular_rotas({STATUS: (200, EVOLUTION_FORA_DO_AR)})

    at = _abrir()

    assert "Evolution API indisponível" in at.error[0].value
    assert not at.success


@pytest.mark.usefixtures("modo_api_real")
def test_conectado_mostra_sucesso_e_o_botao_de_desconectar(simular_rotas):
    simular_rotas({STATUS: (200, CONECTADO)})

    at = _abrir()

    assert "WhatsApp conectado" in at.success[0].value
    assert any(b.label == "Desconectar WhatsApp" for b in at.button)
    assert not any(b.label == "Gerar QR Code" for b in at.button)


@pytest.mark.usefixtures("modo_api_real")
def test_desconectar_confirma_somente_quando_a_api_confirma(simular_rotas):
    simular_rotas({STATUS: (200, CONECTADO), ("POST", f"{PREFIXO}/desconectar"): (200, {"sucesso": True})})

    at = _clicar(_abrir(), "Desconectar WhatsApp")

    assert at.success[0].value == "Sessão do WhatsApp desconectada."


@pytest.mark.usefixtures("modo_api_real")
@pytest.mark.parametrize(
    "rota",
    [(200, {"sucesso": False, "resposta": "falhou"}), (500, {"erro": {"codigo": "X", "mensagem": "Erro interno."}})],
)
def test_desconectar_com_falha_nao_confirma(simular_rotas, rota):
    simular_rotas({STATUS: (200, CONECTADO), ("POST", f"{PREFIXO}/desconectar"): rota})

    at = _clicar(_abrir(), "Desconectar WhatsApp")

    assert any("Não foi possível desconectar" in e or "Erro interno." in e for e in _erros(at))
    assert not any("desconectada" in s.value for s in at.success)


@pytest.mark.usefixtures("modo_api_real")
def test_gera_e_mostra_o_qrcode(simular_rotas):
    resposta = {"conectado": False, "sucesso": True, "base64": QR_CODE_EM_BASE64}
    simular_rotas({STATUS: (200, DESCONECTADO), ("POST", f"{PREFIXO}/conectar"): (200, resposta)})

    at = _clicar(_abrir(), "Gerar QR Code")

    assert not at.exception
    assert _erros(at) == ["**WhatsApp desconectado**"]
    assert len(at.get("image")) == 1


@pytest.mark.usefixtures("modo_api_real")
def test_qrcode_invalido_mostra_erro_em_vez_de_imagem(simular_rotas):
    resposta = {"conectado": False, "sucesso": True, "base64": "isto não é base64!"}
    simular_rotas({STATUS: (200, DESCONECTADO), ("POST", f"{PREFIXO}/conectar"): (200, resposta)})

    at = _clicar(_abrir(), "Gerar QR Code")

    assert any("QR Code recebido da API é inválido" in erro for erro in _erros(at))
    assert not at.get("image")


@pytest.mark.usefixtures("modo_api_real")
def test_falha_ao_gerar_o_qrcode_mostra_o_detalhe(simular_rotas):
    resposta = {"conectado": False, "sucesso": False, "erro": "Instância indisponível"}
    simular_rotas({STATUS: (200, DESCONECTADO), ("POST", f"{PREFIXO}/conectar"): (200, resposta)})

    at = _clicar(_abrir(), "Gerar QR Code")

    assert any("Não foi possível obter o QR Code" in erro and "Instância indisponível" in erro for erro in _erros(at))


@pytest.mark.usefixtures("modo_api_real")
def test_instancia_ja_conectada_ao_gerar_o_qrcode_avisa_e_recarrega(simular_rotas):
    simular_rotas(
        {
            STATUS: (200, DESCONECTADO),
            ("POST", f"{PREFIXO}/conectar"): (200, {"conectado": True, "estado": "open"}),
        }
    )

    at = _clicar(_abrir(), "Gerar QR Code")

    assert at.success[0].value == "O WhatsApp já estava conectado."


@pytest.mark.usefixtures("modo_api_real")
@pytest.mark.parametrize("url, corpo_esperado", [("", b"{}"), (" http://backend:8000/webhook ", b'"url":"http://backend:8000/webhook"')])
def test_configura_o_webhook_sem_exigir_token_no_front(simular_rotas, url, corpo_esperado):
    requisicoes = simular_rotas(
        {STATUS: (200, DESCONECTADO), ("POST", f"{PREFIXO}/configurar-webhook"): (200, {"sucesso": True})}
    )
    at = _abrir()
    _campo(at, "URL do webhook").set_value(url)

    at = _clicar(at, "Salvar e ativar webhook")

    assert at.success[0].value == "Webhook configurado."
    assert corpo_esperado in requisicoes[-1].content.replace(b" ", b"")


@pytest.mark.usefixtures("modo_api_real")
def test_webhook_recusado_pela_evolution_nao_confirma(simular_rotas):
    simular_rotas(
        {
            STATUS: (200, DESCONECTADO),
            ("POST", f"{PREFIXO}/configurar-webhook"): (200, {"sucesso": False, "erro": "Evolution recusou"}),
        }
    )

    at = _clicar(_abrir(), "Salvar e ativar webhook")

    assert any("Evolution recusou" in erro for erro in _erros(at))
    assert not any("Webhook configurado" in s.value for s in at.success)


@pytest.mark.usefixtures("modo_api_real")
@pytest.mark.parametrize("numero", ["", "abc", "55119"])
def test_numero_invalido_nao_chama_a_api(simular_rotas, numero):
    requisicoes = simular_rotas({STATUS: (200, CONECTADO)})
    at = _abrir()
    _campo(at, "Número de destino").set_value(numero)

    at = _clicar(at, "Enviar mensagem de teste")

    assert at.warning
    assert [r.url.path for r in requisicoes].count(f"{PREFIXO}/enviar-teste") == 0


@pytest.mark.usefixtures("modo_api_real")
def test_envia_a_mensagem_de_teste_e_confirma(simular_rotas):
    requisicoes = simular_rotas(
        {STATUS: (200, CONECTADO), ("POST", f"{PREFIXO}/enviar-teste"): (200, {"status": "enviado", "numero": "5511999999999"})}
    )
    at = _abrir()
    _campo(at, "Número de destino").set_value("+55 (11) 99999-9999")

    at = _clicar(at, "Enviar mensagem de teste")

    assert not at.exception
    assert at.success[-1].value == "Mensagem enviada para 5511999999999."
    assert b'"numero":"5511999999999"' in requisicoes[-1].content.replace(b" ", b"")


@pytest.mark.usefixtures("modo_api_real")
def test_falha_no_envio_de_teste_nao_confirma(simular_rotas):
    corpo = {"erro": {"codigo": "HTTP_502", "mensagem": "Não foi possível enviar a mensagem."}}
    simular_rotas({STATUS: (200, CONECTADO), ("POST", f"{PREFIXO}/enviar-teste"): (502, corpo)})
    at = _abrir()
    _campo(at, "Número de destino").set_value("5511999999999")

    at = _clicar(at, "Enviar mensagem de teste")

    assert any("Não foi possível enviar a mensagem." in erro for erro in _erros(at))
    assert not any("Mensagem enviada" in s.value for s in at.success)
