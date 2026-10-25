import pytest

from utils.requisicao import (
    OPCAO_ARQUIVO,
    OPCAO_TEXTO,
    montar_requisicao,
    validar_envio,
)


class ArquivoFalso:
    def __init__(self, nome: str, conteudo: bytes):
        self.name = nome
        self._conteudo = conteudo

    def getvalue(self) -> bytes:
        return self._conteudo


def test_monta_requisicao_a_partir_de_texto_digitado():
    requisicao = montar_requisicao(None, "suspeita de TEP", "Pronto_Socorro")

    assert requisicao["tipo_arquivo"] == "TEXTO"
    assert requisicao["documento_texto"] == "suspeita de TEP"
    assert requisicao["canal_origem"] == "Pronto_Socorro"
    assert requisicao["documento_id"].startswith("DOC-CLIN-")


def test_requisicao_tem_exatamente_os_campos_do_contrato():
    requisicao = montar_requisicao(None, "texto", "Pronto_Socorro")

    assert set(requisicao) == {"documento_id", "tipo_arquivo", "documento_texto", "canal_origem"}


@pytest.mark.parametrize(
    "nome_arquivo, tipo_esperado",
    [
        ("laudo.txt", "TEXTO"),
        ("laudo.json", "JSON"),
        ("LAUDO.TXT", "TEXTO"),
    ],
)
def test_identifica_tipo_de_arquivo_de_texto(nome_arquivo, tipo_esperado):
    arquivo = ArquivoFalso(nome_arquivo, b"conteudo do documento")

    requisicao = montar_requisicao(arquivo, "", "Pronto_Socorro")

    assert requisicao["tipo_arquivo"] == tipo_esperado
    assert requisicao["documento_texto"] == "conteudo do documento"


@pytest.mark.parametrize(
    "nome_arquivo, tipo_esperado",
    [
        ("laudo.pdf", "PDF"),
        ("receita.png", "IMAGEM"),
        ("receita.jpg", "IMAGEM"),
        ("receita.jpeg", "IMAGEM"),
    ],
)
def test_pdf_e_imagem_enviam_o_nome_do_arquivo_por_enquanto(nome_arquivo, tipo_esperado):
    arquivo = ArquivoFalso(nome_arquivo, b"\x00\x01binario")

    requisicao = montar_requisicao(arquivo, "", "Pronto_Socorro")

    assert requisicao["tipo_arquivo"] == tipo_esperado
    assert requisicao["documento_texto"] == nome_arquivo


@pytest.mark.parametrize("texto_vazio", ["", "   ", "\n\t"])
def test_rejeita_texto_digitado_vazio(texto_vazio):
    with pytest.raises(ValueError, match="vazio"):
        montar_requisicao(None, texto_vazio, "Pronto_Socorro")


def test_rejeita_arquivo_vazio():
    arquivo = ArquivoFalso("rotina.txt", b"")

    with pytest.raises(ValueError, match="vazio"):
        montar_requisicao(arquivo, "", "Pronto_Socorro")


def test_rejeita_arquivo_de_texto_fora_do_utf8():
    arquivo = ArquivoFalso("laudo.txt", "açúcar".encode("latin-1"))

    with pytest.raises(ValueError, match="UTF-8"):
        montar_requisicao(arquivo, "", "Pronto_Socorro")


def test_ignora_marcador_bom_no_inicio_do_arquivo():
    arquivo = ArquivoFalso("laudo.txt", b"\xef\xbb\xbfsuspeita de TEP")

    requisicao = montar_requisicao(arquivo, "", "Pronto_Socorro")

    assert requisicao["documento_texto"] == "suspeita de TEP"


def test_exige_arquivo_quando_a_fonte_e_arquivo():
    problema = validar_envio(OPCAO_ARQUIVO, None, "", "Pronto_Socorro")

    assert problema == "Selecione um arquivo para analisar."


def test_exige_texto_quando_a_fonte_e_texto():
    problema = validar_envio(OPCAO_TEXTO, None, "   ", "Pronto_Socorro")

    assert problema == "Cole o texto do documento para analisar."


def test_exige_canal_de_origem():
    problema = validar_envio(OPCAO_TEXTO, None, "texto", None)

    assert problema == "Selecione o canal de origem do documento."


def test_aceita_envio_completo():
    arquivo = ArquivoFalso("laudo.txt", b"texto")

    assert validar_envio(OPCAO_TEXTO, None, "texto", "Pronto_Socorro") is None
    assert validar_envio(OPCAO_ARQUIVO, arquivo, "", "Pronto_Socorro") is None