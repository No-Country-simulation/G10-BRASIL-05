import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from app.main import app
from app.repositories.database import init_db
from app.schemas.escopo_documento import ResultadoEscopoDocumento
from app.schemas.triagem import (
    ArmazenamentoOCI,
    ClassificacaoDocumento,
    DadosExtraidos,
    DecisaoRoteamento,
    RespostaTriagem,
)
from app.services.redis_service import (
    adquirir_lock_upload_lote,
    liberar_lock_upload_lote,
    limpar_locks_upload_memoria,
)

# Garante inicializacao das tabelas de teste
init_db()
client = TestClient(app)


def gerar_pdf_em_memoria(texto: str) -> bytes:
    """Gera um PDF em memoria contendo o texto fornecido utilizando pypdf."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": texto, "/Subject": "Laudo Clinico"})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def gerar_imagem_em_memoria(formato: str = "PNG") -> bytes:
    """Gera uma imagem valida em memoria utilizando Pillow."""
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format=formato)
    return buf.getvalue()


def test_upload_imagem_valida(monkeypatch):
    """Valida o upload de uma imagem PNG para triagem."""
    monkeypatch.setattr(
        "app.controllers.triagem_upload.DocumentParserService.inspecionar_arquivo_com_metadados",
        lambda *args, **kwargs: (
            "Texto clinico de receita medica.",
            "imagem",
            ResultadoEscopoDocumento(
                escopo="medico", legibilidade="legivel", justificativa="Documento medico de teste", evidencias=[]
            ),
            {},
        ),
    )
    monkeypatch.setattr(
        "app.controllers.triagem_upload.priorizar_revisao_medica_ilegivel",
        lambda r: ResultadoEscopoDocumento(
            escopo="medico", legibilidade="legivel", justificativa="Documento medico de teste", evidencias=[]
        ),
    )
    monkeypatch.setattr(
        "app.controllers.triagem_upload.TriagemService.__init__",
        lambda self, db: None,
    )
    monkeypatch.setattr(
        "app.controllers.triagem_upload.TriagemService.processar_triagem",
        lambda *args, **kwargs: RespostaTriagem(
            documento_id="TEST-IMG-001",
            tipo_arquivo="imagem",
            status="processado",
            persistido=True,
            triagem_iniciada=True,
            classificacao=ClassificacaoDocumento(
                tipo_documento="Receita Medica",
                especialidade="Clinica Geral",
                nivel_prioridade="Rotina",
                score_confianca_classificacao=0.95,
            ),
            dados_extraidos=DadosExtraidos(),
            decisao_roteamento=DecisaoRoteamento(
                destino_principal="Farmacia",
                requer_auditoria_humana=False,
                justificativa_roteamento="Receita valida.",
            ),
            armazenamento_oci=ArmazenamentoOCI(
                bucket="mediflow-documentos-clinicos",
                caminho_objeto="test.json",
                status_backup="sucesso",
            ),
        ),
    )
    img_bytes = gerar_imagem_em_memoria("PNG")
    response = client.post(
        "/triagem/upload",
        files={"file": ("receita_medica.png", img_bytes, "image/png")},
        data={"canal_origem": "Telemedicina", "documento_id": "TEST-IMG-001"},
    )
    assert response.status_code in [200, 201]
    dados = response.json()
    assert dados["documento_id"] == "TEST-IMG-001"
    assert "classificacao" in dados
    assert "decisao_roteamento" in dados


def test_upload_pdf_real_valido(monkeypatch):
    """Valida o upload de um arquivo PDF real com extracao de texto vetorial."""
    caminho = Path("DOCUMENTOS/mediflow (1).pdf")
    if not caminho.exists():
        caminho = Path(__file__).resolve().parents[2] / "DOCUMENTOS" / "mediflow (1).pdf"
    if not caminho.exists():
        pytest.skip("Arquivo DOCUMENTOS/mediflow (1).pdf nao encontrado")

    with open(caminho, "rb") as f:
        pdf_bytes = f.read()

    monkeypatch.setattr(
        "app.controllers.triagem_upload.DocumentParserService.inspecionar_arquivo_com_metadados",
        lambda *args, **kwargs: (
            "Texto clinico de laudo medico extraido.",
            "pdf",
            ResultadoEscopoDocumento(
                escopo="medico", legibilidade="legivel", justificativa="Laudo clinico", evidencias=[]
            ),
            {},
        ),
    )
    monkeypatch.setattr(
        "app.controllers.triagem_upload.priorizar_revisao_medica_ilegivel",
        lambda r: ResultadoEscopoDocumento(
            escopo="medico", legibilidade="legivel", justificativa="Laudo clinico", evidencias=[]
        ),
    )
    monkeypatch.setattr(
        "app.controllers.triagem_upload.TriagemService.__init__",
        lambda self, db: None,
    )
    monkeypatch.setattr(
        "app.controllers.triagem_upload.TriagemService.processar_triagem",
        lambda *args, **kwargs: RespostaTriagem(
            documento_id="TEST-PDF-002",
            tipo_arquivo="pdf",
            status="processado",
            persistido=True,
            triagem_iniciada=True,
            classificacao=ClassificacaoDocumento(
                tipo_documento="Laudo de Exame",
                especialidade="Clinica Geral",
                nivel_prioridade="Rotina",
                score_confianca_classificacao=0.98,
            ),
            dados_extraidos=DadosExtraidos(),
            decisao_roteamento=DecisaoRoteamento(
                destino_principal="Arquivo",
                requer_auditoria_humana=False,
                justificativa_roteamento="Laudo processado.",
            ),
            armazenamento_oci=ArmazenamentoOCI(
                bucket="mediflow-documentos-clinicos",
                caminho_objeto="test.json",
                status_backup="sucesso",
            ),
        ),
    )

    response = client.post(
        "/triagem/upload",
        files={"file": ("mediflow_doc.pdf", pdf_bytes, "application/pdf")},
        data={"canal_origem": "Pronto_Socorro", "documento_id": "TEST-PDF-002"},
    )
    assert response.status_code in [200, 201]
    dados = response.json()
    assert dados["documento_id"] == "TEST-PDF-002"
    assert dados["status"] in ["processado", "em_auditoria"]
    assert "classificacao" in dados
    assert "dados_extraidos" in dados
    assert "decisao_roteamento" in dados


def test_upload_formato_invalido():
    """Valida que formatos nao permitidos (.txt, .exe, etc) sao rejeitados com 400."""
    response = client.post(
        "/triagem/upload",
        files={"file": ("arquivo_invalido.txt", b"Texto simples", "text/plain")},
    )
    assert response.status_code == 400
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem") or dados.get("detail", "")
    assert "não suportado" in msg or "nao suportado" in msg


def test_upload_arquivo_vazio():
    """Valida que arquivos de 0 bytes sao rejeitados com 400."""
    response = client.post(
        "/triagem/upload",
        files={"file": ("vazio.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem") or dados.get("detail", "")
    assert "vazio" in msg


def test_upload_tamanho_excedido():
    """Valida que arquivos acima de 10 MB sao rejeitados com 413."""
    conteudo_grande = b"0" * (10 * 1024 * 1024 + 1024)
    response = client.post(
        "/triagem/upload",
        files={"file": ("laudo_gigante.pdf", conteudo_grande, "application/pdf")},
    )
    assert response.status_code == 413
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem") or dados.get("detail", "")
    assert "limite máximo" in msg or "limite maximo" in msg


# ==============================================================================
# TESTES DE ENFILEIRAMENTO EM LOTE E RATE-LIMIT / COOLDOWN DE 30s
# ==============================================================================


def test_upload_enfileirar_lote_sucesso():
    """Valida o enfileiramento assincrono de um lote de arquivos sem execucao pesada sincrona."""
    limpar_locks_upload_memoria()
    pdf_bytes = gerar_pdf_em_memoria("Receita medica de teste")
    img_bytes = gerar_imagem_em_memoria("PNG")

    response = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[
            ("files", ("receita.pdf", pdf_bytes, "application/pdf")),
            ("files", ("foto.png", img_bytes, "image/png")),
        ],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert response.status_code == 202
    dados = response.json()
    assert "lote_id" in dados
    assert "trabalhos" in dados
    assert len(dados["trabalhos"]) == 2
    for trabalho in dados["trabalhos"]:
        assert trabalho["status"] == "na_fila"


def test_upload_enfileirar_cooldown_30s_bloqueia_duplo_envio():
    """Valida que o mesmo usuario recebe 429 ao submeter novo lote antes de 30 segundos."""
    limpar_locks_upload_memoria()
    pdf_bytes = gerar_pdf_em_memoria("Receita 1")

    # 1. Primeiro envio com sucesso
    res1 = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc1.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res1.status_code == 202

    # 2. Segundo envio imediato do mesmo usuario (duplo clique / repeticao)
    res2 = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc2.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res2.status_code == 429
    dados_erro = res2.json()
    mensagem_esperada = "Um lote de documentos já foi enviado recentemente. Por favor, aguarde 30 segundos antes de enviar um novo lote."
    assert dados_erro.get("detail") == mensagem_esperada
    assert dados_erro.get("erro", {}).get("mensagem") == mensagem_esperada


def test_upload_enfileirar_libera_lock_apos_expirar_cooldown(monkeypatch):
    """Valida que o usuario pode enviar novo lote apos o cooldown de 30s expirar."""
    limpar_locks_upload_memoria()
    pdf_bytes = gerar_pdf_em_memoria("Receita 1")

    # Primeiro envio
    res1 = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc1.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res1.status_code == 202

    # Simula passagem de mais de 30 segundos avancando o tempo no modulo time
    tempo_original = time.time()
    monkeypatch.setattr(time, "time", lambda: tempo_original + 35)

    # Segundo envio apos decorridos 30 segundos
    res2 = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc2.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res2.status_code == 202
    assert "lote_id" in res2.json()


def test_upload_enfileirar_usuarios_diferentes_nao_se_bloqueiam():
    """Valida que o cooldown de 30s e isolado por usuario e nao afeta outros usuarios."""
    limpar_locks_upload_memoria()
    from app.models.triagem import UsuarioSistemaModel
    from app.repositories.database import SessionLocal
    from app.services.autenticacao import emitir_token, gerar_hash_senha

    # Cria ou obtem segundo usuario de teste
    with SessionLocal() as db:
        medico = db.query(UsuarioSistemaModel).filter_by(email="medico.teste@example.org").first()
        if not medico:
            medico = UsuarioSistemaModel(
                email="medico.teste@example.org",
                nome="Medico Teste",
                senha_hash=gerar_hash_senha("senha123"),
                papel="MEDICO",
                trocar_senha_obrigatorio=False,
                ativo=True,
                pode_gerenciar_whatsapp=False,
            )
            db.add(medico)
            db.commit()
            db.refresh(medico)
        token_medico = emitir_token(medico)

    pdf_bytes = gerar_pdf_em_memoria("Receita Medico")

    # Usuario 1 (Diretor padrao do client) envia
    res1 = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc1.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res1.status_code == 202

    # Usuario 2 (Medico) envia imediatamente com seu proprio token
    res2 = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc2.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
        headers={"Authorization": f"Bearer {token_medico}"},
    )
    assert res2.status_code == 202

    # Usuario 1 tenta reenviar imediatamente -> Bloqueado com 429
    res3 = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc3.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res3.status_code == 429


def test_upload_enfileirar_libera_lock_quando_validacao_falha():
    """Valida que se o formulario for invalido (ex: sem arquivos), o lock e liberado imediatamente."""
    limpar_locks_upload_memoria()

    # Requisicao invalida sem arquivos -> 400
    res_invalida = client.post(
        "/api/v1/triagem/upload/enfileirar",
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res_invalida.status_code == 400

    # Usuario corrige e envia arquivo valido imediatamente -> Deve ser aceito sem bloqueio de 429
    pdf_bytes = gerar_pdf_em_memoria("Receita Corrigida")
    res_valida = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("doc_corrigido.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Pronto_Socorro"},
    )
    assert res_valida.status_code == 202


def test_adquirir_e_liberar_lock_upload_lote_fallback():
    """Valida as funcoes de lock e fallback diretamente em nivel de servico."""
    limpar_locks_upload_memoria()
    user_id = 9999

    assert adquirir_lock_upload_lote(user_id, ttl_segundos=30) is True
    # Segunda tentativa imediata deve retornar False
    assert adquirir_lock_upload_lote(user_id, ttl_segundos=30) is False

    # Liberacao manual
    liberar_lock_upload_lote(user_id)
    # Apos liberacao, deve conseguir adquirir novamente
    assert adquirir_lock_upload_lote(user_id, ttl_segundos=30) is True
