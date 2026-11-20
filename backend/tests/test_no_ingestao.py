import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.agent.nodes.ingestao import node_ingestao
from app.schemas.ingestao import DocumentoIngerido
from app.services.document_parser import DocumentParserService

PDF_COM_TEXTO = Path(__file__).resolve().parents[2] / "DOCUMENTOS" / "mediflow (1).pdf"
CHAVES_PADRONIZADAS = {"tipo_arquivo", "documento_texto", "imagens_documento", "requer_ocr", "erros", "status"}


def _imagem_digitalizada(formato: str) -> bytes:
    imagem = Image.new("RGB", (400, 200), "white")
    ImageDraw.Draw(imagem).text((10, 10), "Receita: Amoxicilina 500mg", fill="black")
    buffer = io.BytesIO()
    imagem.save(buffer, format=formato)
    return buffer.getvalue()


def _ingerir_arquivo(conteudo: bytes, extensao: str) -> dict:
    documento = DocumentParserService.preparar_documento(conteudo, extensao, f"documento{extensao}")
    return node_ingestao(
        {
            "tipo_arquivo": documento.formato.value,
            "documento_texto": documento.texto,
            "imagens_documento": [imagem.model_dump() for imagem in documento.imagens],
        }
    )


def _assert_formato_padronizado(resultado: dict):
    assert CHAVES_PADRONIZADAS <= set(resultado)
    DocumentoIngerido(
        formato=resultado["tipo_arquivo"],
        texto=resultado["documento_texto"],
        imagens=resultado["imagens_documento"],
    )


def test_texto_chega_padronizado():
    resultado = node_ingestao({"tipo_arquivo": "texto", "documento_texto": "Receita:   uso oral\n\n\n\nLosartana 50mg"})

    _assert_formato_padronizado(resultado)
    assert resultado["tipo_arquivo"] == "TEXTO"
    assert resultado["documento_texto"] == "Receita: uso oral\n\nLosartana 50mg"
    assert resultado["imagens_documento"] == []
    assert resultado["requer_ocr"] is False


def test_pdf_com_camada_de_texto_chega_como_texto():
    resultado = _ingerir_arquivo(PDF_COM_TEXTO.read_bytes(), ".pdf")

    _assert_formato_padronizado(resultado)
    assert resultado["tipo_arquivo"] == "PDF"
    assert resultado["documento_texto"]
    assert resultado["requer_ocr"] is False


def test_pdf_escaneado_chega_como_imagem_para_ocr():
    resultado = _ingerir_arquivo(_imagem_digitalizada("PDF"), ".pdf")

    _assert_formato_padronizado(resultado)
    assert resultado["tipo_arquivo"] == "PDF"
    assert resultado["documento_texto"] == ""
    assert len(resultado["imagens_documento"]) == 1
    assert resultado["requer_ocr"] is True


@pytest.mark.parametrize("extensao, formato_pil, mime", [(".png", "PNG", "image/png"), (".jpg", "JPEG", "image/jpeg")])
def test_imagem_chega_como_imagem_para_ocr(extensao, formato_pil, mime):
    resultado = _ingerir_arquivo(_imagem_digitalizada(formato_pil), extensao)

    _assert_formato_padronizado(resultado)
    assert resultado["tipo_arquivo"] == "IMAGEM"
    assert resultado["imagens_documento"][0]["mime_type"] == mime
    assert resultado["requer_ocr"] is True


def test_tipo_desconhecido_e_tratado_como_texto():
    resultado = node_ingestao({"tipo_arquivo": "docx", "documento_texto": "Atestado"})

    assert resultado["tipo_arquivo"] == "TEXTO"


def test_documento_vazio_registra_erro():
    resultado = node_ingestao({"tipo_arquivo": "TEXTO", "documento_texto": "   ", "erros": []})

    assert "Texto do documento está vazio após higienização." in resultado["erros"]


def test_imagem_em_formato_invalido_e_descartada_com_erro():
    resultado = node_ingestao(
        {
            "tipo_arquivo": "IMAGEM",
            "documento_texto": "",
            "imagens_documento": [{"mime_type": "application/zip", "dados_base64": "AAAA"}],
        }
    )

    assert resultado["imagens_documento"] == []
    assert resultado["requer_ocr"] is False
    assert "Imagens do documento em formato inválido foram descartadas na ingestão." in resultado["erros"]
