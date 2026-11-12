import pytest
from pydantic import ValidationError

from app.schemas.requisicao_documento import RequisicaoDocumento


@pytest.fixture
def payload_valido():
    return {
        "documento_id": "DOC-001",
        "tipo_arquivo": "PDF",
        "documento_texto": "Conteúdo de exemplo do documento.",
        "canal_origem": "WEB",
    }


def test_payload_valido_do_briefing(payload_valido):
    requisicao = RequisicaoDocumento.model_validate(payload_valido)

    assert requisicao.documento_id == "DOC-001"
    assert requisicao.tipo_arquivo == "PDF"
    assert requisicao.documento_texto == "Conteúdo de exemplo do documento."
    assert requisicao.canal_origem == "WEB"


@pytest.mark.parametrize("tipo", ["PDF", "IMAGEM", "TEXTO", "JSON"])
def test_aceita_tipos_de_arquivo_permitidos(payload_valido, tipo):
    payload_valido["tipo_arquivo"] = tipo

    requisicao = RequisicaoDocumento.model_validate(payload_valido)

    assert requisicao.tipo_arquivo == tipo


@pytest.mark.parametrize("tipo", ["pdf", "imagem", "XML", "", "DOCX"])
def test_rejeita_tipos_de_arquivo_invalidos(payload_valido, tipo):
    payload_valido["tipo_arquivo"] = tipo

    with pytest.raises(ValidationError):
        RequisicaoDocumento.model_validate(payload_valido)


@pytest.mark.parametrize(
    "campo",
    [
        "documento_id",
        "tipo_arquivo",
        "documento_texto",
        "canal_origem",
    ],
)
def test_rejeita_campo_obrigatorio_ausente(payload_valido, campo):
    del payload_valido[campo]

    with pytest.raises(ValidationError):
        RequisicaoDocumento.model_validate(payload_valido)


@pytest.mark.parametrize(
    "campo",
    ["documento_id", "documento_texto", "canal_origem"],
)
@pytest.mark.parametrize("valor", ["", "   ", "\t\n"])
def test_rejeita_strings_vazias_ou_com_espacos(
    payload_valido, campo, valor
):
    payload_valido[campo] = valor

    with pytest.raises(ValidationError):
        RequisicaoDocumento.model_validate(payload_valido)


def test_rejeita_campos_adicionais(payload_valido):
    payload_valido["campo_inexistente"] = "valor extra"

    with pytest.raises(ValidationError):
        RequisicaoDocumento.model_validate(payload_valido)


def test_aceita_canal_origem_sem_lista_predefinida(payload_valido):
    payload_valido["canal_origem"] = "CANAL_PERSONALIZADO_123"

    requisicao = RequisicaoDocumento.model_validate(payload_valido)

    assert requisicao.canal_origem == "CANAL_PERSONALIZADO_123"


def test_documento_id_nao_exige_formato_especifico(payload_valido):
    payload_valido["documento_id"] = "qualquer identificador válido"

    requisicao = RequisicaoDocumento.model_validate(payload_valido)

    assert requisicao.documento_id == "qualquer identificador válido"


def test_json_nao_interpreta_o_conteudo_do_documento(payload_valido):
    texto = "{ isto não é um JSON válido"

    payload_valido["tipo_arquivo"] = "JSON"
    payload_valido["documento_texto"] = texto

    requisicao = RequisicaoDocumento.model_validate(payload_valido)

    assert requisicao.documento_texto == texto
    assert isinstance(requisicao.documento_texto, str)
