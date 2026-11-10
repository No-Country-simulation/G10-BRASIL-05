import httpx
import pytest

from services import cliente_http
from services.erros import ErroDeApi

REQUISICAO = {
    "documento_id": "DOC-1",
    "tipo_arquivo": "TEXTO",
    "documento_texto": "suspeita de TEP",
    "canal_origem": "Pronto_Socorro",
}


class ArquivoFalso:
    def __init__(self, nome: str, tipo: str | None, conteudo: bytes):
        self.name = nome
        self.type = tipo
        self._conteudo = conteudo

    def getvalue(self) -> bytes:
        return self._conteudo


def test_envia_texto_em_json_para_a_triagem(simular_api):
    requisicoes = simular_api(lambda r: httpx.Response(200, json={"status": "processado"}))

    resposta = cliente_http.enviar_documento(REQUISICAO)

    assert resposta == {"status": "processado"}
    assert requisicoes[0].method == "POST"
    assert requisicoes[0].url.path == "/api/v1/triagem"
    assert b"suspeita de TEP" in requisicoes[0].content


@pytest.mark.parametrize("tipo_arquivo", ["PDF", "IMAGEM"])
def test_envia_pdf_e_imagem_por_upload_multipart(simular_api, tipo_arquivo):
    requisicoes = simular_api(lambda r: httpx.Response(200, json={"status": "processado"}))
    arquivo = ArquivoFalso("laudo.pdf", "application/pdf", b"%PDF-1.4")

    cliente_http.enviar_documento({**REQUISICAO, "tipo_arquivo": tipo_arquivo}, arquivo)

    requisicao = requisicoes[0]
    assert requisicao.url.path == "/api/v1/triagem/upload"
    assert requisicao.headers["content-type"].startswith("multipart/form-data")
    for trecho in (b"laudo.pdf", b"%PDF-1.4", b"Pronto_Socorro", b"DOC-1"):
        assert trecho in requisicao.content


@pytest.mark.parametrize(
    "nome, tipo_esperado",
    [
        ("foto.png", b"image/png"),
        ("foto.JPG", b"image/jpeg"),
        ("foto.webp", b"image/webp"),
        ("laudo.pdf", b"application/pdf"),
    ],
)
def test_upload_deduz_o_tipo_pela_extensao_quando_o_navegador_nao_informa(simular_api, nome, tipo_esperado):
    requisicoes = simular_api(lambda r: httpx.Response(200, json={}))
    arquivo = ArquivoFalso(nome, None, b"conteudo")

    cliente_http.enviar_documento({**REQUISICAO, "tipo_arquivo": "IMAGEM"}, arquivo)

    assert b"Content-Type: " + tipo_esperado in requisicoes[0].content


def test_upload_respeita_o_tipo_informado_pelo_navegador(simular_api):
    requisicoes = simular_api(lambda r: httpx.Response(200, json={}))
    arquivo = ArquivoFalso("foto.png", "image/png", b"conteudo")

    cliente_http.enviar_documento({**REQUISICAO, "tipo_arquivo": "IMAGEM"}, arquivo)

    assert b"Content-Type: image/png" in requisicoes[0].content


def test_upload_usa_tipo_generico_quando_a_extensao_e_desconhecida(simular_api):
    requisicoes = simular_api(lambda r: httpx.Response(200, json={}))
    arquivo = ArquivoFalso("arquivo.zzz", None, b"conteudo")

    cliente_http.enviar_documento({**REQUISICAO, "tipo_arquivo": "PDF"}, arquivo)

    assert b"application/octet-stream" in requisicoes[0].content


@pytest.mark.parametrize("tipo_arquivo", ["TEXTO", "JSON"])
def test_arquivo_de_texto_e_json_vai_pelo_endpoint_normal(simular_api, tipo_arquivo):
    requisicoes = simular_api(lambda r: httpx.Response(200, json={}))
    arquivo = ArquivoFalso("laudo.txt", "text/plain", b"texto")

    cliente_http.enviar_documento({**REQUISICAO, "tipo_arquivo": tipo_arquivo}, arquivo)

    assert requisicoes[0].url.path == "/api/v1/triagem"


def test_lista_os_documentos(simular_api):
    requisicoes = simular_api(lambda r: httpx.Response(200, json=[{"documento_id": "DOC-1"}]))

    assert cliente_http.listar_documentos() == [{"documento_id": "DOC-1"}]
    assert requisicoes[0].method == "GET"
    assert requisicoes[0].url.path == "/api/v1/triagem/documentos"


def test_lista_a_fila_de_auditoria(simular_api):
    requisicoes = simular_api(lambda r: httpx.Response(200, json=[]))

    assert cliente_http.listar_fila_auditoria() == []
    assert requisicoes[0].url.path == "/api/v1/triagem/auditoria"


def test_registra_a_decisao_do_auditor(simular_api):
    requisicoes = simular_api(lambda r: httpx.Response(200, json={"novo_status": "auditoria_aprovado"}))
    decisao = {"status_aprovacao": "aprovado", "auditor_nome": "Dra. Ana", "justificativa": "", "dados_corrigidos": None}

    resposta = cliente_http.registrar_decisao("DOC-1", decisao)

    assert resposta == {"novo_status": "auditoria_aprovado"}
    assert requisicoes[0].method == "POST"
    assert requisicoes[0].url.path == "/api/v1/triagem/auditoria/DOC-1/decisao"
    assert b"Dra. Ana" in requisicoes[0].content


def test_detalhe_do_documento_ainda_nao_existe_no_backend():
    assert cliente_http.buscar_documento("DOC-1") is None


def test_mostra_a_mensagem_de_erro_do_backend(simular_api):
    corpo = {"erro": {"codigo": "ARQUIVO_GRANDE", "mensagem": "Arquivo acima de 10 MB."}}
    simular_api(lambda r: httpx.Response(413, json=corpo))

    with pytest.raises(ErroDeApi, match="Arquivo acima de 10 MB."):
        cliente_http.enviar_documento(REQUISICAO)


def test_inclui_os_detalhes_do_erro_de_validacao(simular_api):
    corpo = {"erro": {"mensagem": "Dados inválidos.", "detalhes": [{"campo": "canal_origem", "motivo": "obrigatório"}]}}
    simular_api(lambda r: httpx.Response(422, json=corpo))

    with pytest.raises(ErroDeApi) as erro:
        cliente_http.enviar_documento(REQUISICAO)

    assert str(erro.value) == "Dados inválidos. (canal_origem: obrigatório)"


@pytest.mark.parametrize("resposta", [
    httpx.Response(500, text="falha"),
    httpx.Response(500, json={"detail": "x"}),
    httpx.Response(500, json={"erro": "texto"}),
    httpx.Response(500, json=["a"]),
])
def test_usa_mensagem_padrao_quando_o_erro_nao_segue_o_formato(simular_api, resposta):
    simular_api(lambda r: resposta)

    with pytest.raises(ErroDeApi, match="A API respondeu com erro 500."):
        cliente_http.listar_documentos()


def test_avisa_quando_a_api_esta_fora_do_ar(simular_api):
    def falhar(requisicao):
        raise httpx.ConnectError("sem conexão")

    simular_api(falhar)

    with pytest.raises(ErroDeApi, match="Não foi possível conectar à API"):
        cliente_http.listar_documentos()


def test_avisa_quando_a_api_demora_demais(simular_api):
    def demorar(requisicao):
        raise httpx.ReadTimeout("lenta")

    simular_api(demorar)

    with pytest.raises(ErroDeApi, match="demorou demais"):
        cliente_http.listar_documentos()


def test_avisa_quando_a_resposta_nao_e_json(simular_api):
    simular_api(lambda r: httpx.Response(200, text="<html>"))

    with pytest.raises(ErroDeApi, match="resposta inválida"):
        cliente_http.listar_documentos()


def test_cliente_usa_a_url_e_o_tempo_limite_configurados(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://servidor:9000/")
    monkeypatch.setenv("API_TIMEOUT", "15")

    with cliente_http._criar_cliente() as cliente:
        assert str(cliente.base_url).rstrip("/") == "http://servidor:9000"
        assert cliente.timeout.read == 15.0