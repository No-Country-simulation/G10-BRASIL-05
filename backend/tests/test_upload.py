import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from app.main import app
from app.repositories.database import init_db

# Garante inicialização das tabelas de teste
init_db()
client = TestClient(app)


def gerar_pdf_em_memoria(texto: str) -> bytes:
    """Gera um PDF em memória contendo o texto fornecido utilizando pypdf."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # Adiciona metadados / annotation para simular documento clínico
    writer.add_metadata({"/Title": texto, "/Subject": "Laudo Clínico"})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def gerar_imagem_em_memoria(formato: str = "PNG") -> bytes:
    """Gera uma imagem válida em memória utilizando Pillow."""
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format=formato)
    return buf.getvalue()


def test_upload_imagem_valida():
    """Valida o upload de uma imagem PNG para triagem."""
    img_bytes = gerar_imagem_em_memoria("PNG")
    response = client.post(
        "/triagem/upload",
        files={"file": ("receita_medica.png", img_bytes, "image/png")},
        data={"canal_origem": "Telemedicina", "documento_id": "TEST-IMG-001"},
    )
    assert response.status_code == 200
    dados = response.json()
    assert dados["documento_id"] == "TEST-IMG-001"
    assert "classificacao" in dados
    assert "decisao_roteamento" in dados


def test_upload_pdf_real_valido():
    """Valida o upload de um arquivo PDF real com extração de texto vetorial."""
    with open("DOCUMENTOS/mediflow (1).pdf", "rb") as f:
        pdf_bytes = f.read()

    response = client.post(
        "/triagem/upload",
        files={"file": ("mediflow_doc.pdf", pdf_bytes, "application/pdf")},
        data={"canal_origem": "Pronto_Socorro", "documento_id": "TEST-PDF-002"},
    )
    assert response.status_code == 200
    dados = response.json()
    assert dados["documento_id"] == "TEST-PDF-002"
    assert dados["status"] in ["processado", "em_auditoria"]
    assert "classificacao" in dados
    assert "dados_extraidos" in dados
    assert "decisao_roteamento" in dados


def test_upload_formato_invalido():
    """Valida que formatos não permitidos (.txt, .exe, etc) são rejeitados com 400."""
    response = client.post(
        "/triagem/upload",
        files={"file": ("arquivo_invalido.txt", b"Texto simples", "text/plain")},
    )
    assert response.status_code == 400
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem") or dados.get("detail", "")
    assert "não suportado" in msg


def test_upload_arquivo_vazio():
    """Valida que arquivos de 0 bytes são rejeitados com 400."""
    response = client.post(
        "/triagem/upload",
        files={"file": ("vazio.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem") or dados.get("detail", "")
    assert "vazio" in msg


def test_upload_tamanho_excedido():
    """Valida que arquivos acima de 10 MB são rejeitados com 413."""
    conteudo_grande = b"0" * (10 * 1024 * 1024 + 1024)
    response = client.post(
        "/triagem/upload",
        files={"file": ("laudo_gigante.pdf", conteudo_grande, "application/pdf")},
    )
    assert response.status_code == 413
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem") or dados.get("detail", "")
    assert "limite máximo" in msg
