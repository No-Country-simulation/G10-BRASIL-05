import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.main import app
from app.errors import QueueUnavailableError
from app.services.redis_service import limpar_locks_upload_memoria
from app.services.triagem_queue import (
    enfileirar_documento,
    enfileirar_texto,
    obter_lote_triagem,
    registrar_lote_triagem,
    reservar_trabalho,
)

client = TestClient(app)


def test_reservar_trabalho_falha_redis_lanca_excecao(monkeypatch):
    """Garante que falhas de conexão no Redis não retornem falso sucesso (1)."""
    def redis_falho():
        mock = MagicMock()
        mock.eval.side_effect = RedisConnectionError("Conexão recusada")
        return mock

    monkeypatch.setattr("app.services.triagem_queue.obter_redis_fila", redis_falho)

    with pytest.raises(QueueUnavailableError):
        reservar_trabalho(usuario_id=1, documento_id="DOC-FAIL-01")


def test_enfileirar_documento_falha_rq_lanca_excecao(monkeypatch):
    """Garante que falhas de enqueue no RQ não retornem None silenciosamente."""
    def fila_falha():
        mock = MagicMock()
        mock.enqueue.side_effect = RuntimeError("RQ cluster inativo")
        return mock

    monkeypatch.setattr("app.services.triagem_queue.obter_fila_triagem", fila_falha)

    with pytest.raises(QueueUnavailableError):
        enfileirar_documento(
            documento_id="DOC-FAIL-02",
            caminho_arquivo="/tmp/arquivo.pdf",
            caminho_objeto_fonte="oci://bucket/arquivo.pdf",
            nome_arquivo="arquivo.pdf",
            extensao=".pdf",
            canal_origem="Interno",
            usuario_id=1,
        )


def test_enfileirar_texto_falha_rq_lanca_excecao(monkeypatch):
    """Garante que falhas de enqueue de texto no RQ propaguem erro explícito."""
    def fila_falha():
        mock = MagicMock()
        mock.enqueue.side_effect = RuntimeError("RQ falhou ao serializar")
        return mock

    monkeypatch.setattr("app.services.triagem_queue.obter_fila_triagem", fila_falha)

    with pytest.raises(QueueUnavailableError):
        enfileirar_texto(
            documento_id="DOC-FAIL-03",
            documento_texto="Texto clínico de teste",
            tipo_arquivo="texto",
            canal_origem="Interno",
            usuario_id=1,
        )


def test_registrar_lote_falha_redis_lanca_excecao(monkeypatch):
    """Garante que não haja fallback para memória durável se o Redis falhar."""
    def redis_falho():
        mock = MagicMock()
        mock.set.side_effect = RedisConnectionError("Sem conexão com Redis")
        return mock

    monkeypatch.setattr("app.services.triagem_queue.obter_redis_fila", redis_falho)

    with pytest.raises(QueueUnavailableError):
        registrar_lote_triagem(
            lote_id="LOTE-001",
            usuario_id=1,
            trabalhos=[{"documento_id": "DOC-1", "status": "na_fila"}],
        )


def test_endpoint_enfileirar_texto_falha_redis_responde_503(monkeypatch):
    """Endpoint de enfileirar texto responde 503 quando Redis não consegue reservar vaga."""
    def reservar_falho(*args, **kwargs):
        raise QueueUnavailableError("Redis indisponível")

    monkeypatch.setattr("app.controllers.triagem_jobs.reservar_trabalho", reservar_falho)

    response = client.post(
        "/api/v1/triagem/texto/enfileirar",
        json={"documento_texto": "Paciente com cefaleia intensa há 3 dias."},
    )
    assert response.status_code == 503
    dados = response.json()
    assert dados.get("erro", {}).get("codigo") == "SERVICO_INDISPONIVEL"


def test_endpoint_upload_enfileirar_falha_rq_marca_falhou(monkeypatch):
    """Garante que falha no enqueue de upload marque status falhou sem retornar falso na_fila."""
    limpar_locks_upload_memoria()

    eventos_publicados = []
    monkeypatch.setattr(
        "app.controllers.triagem_jobs.publicar_evento_triagem",
        lambda uid, tipo, payload: eventos_publicados.append((tipo, payload)),
    )
    monkeypatch.setattr("app.controllers.triagem_jobs.reservar_trabalho", lambda *args: 1)
    monkeypatch.setattr("app.controllers.triagem_jobs.liberar_reserva", lambda *args: None)
    monkeypatch.setattr(
        "app.controllers.triagem_jobs.StorageRepository.salvar_arquivo_original",
        lambda *args, **kwargs: {"caminho_local": "/tmp/dummy", "caminho_objeto_fonte": "oci://b/o"},
    )
    monkeypatch.setattr(
        "app.controllers.triagem_jobs.StorageRepository.rollback_tentativa",
        lambda *args, **kwargs: None,
    )

    def enqueue_falho(*args, **kwargs):
        raise QueueUnavailableError("RQ down")

    monkeypatch.setattr("app.controllers.triagem_jobs.enfileirar_documento", enqueue_falho)

    from tests.test_upload import gerar_pdf_em_memoria
    pdf_bytes = gerar_pdf_em_memoria("Receita de teste")

    response = client.post(
        "/api/v1/triagem/upload/enfileirar",
        files=[("files", ("receita.pdf", pdf_bytes, "application/pdf"))],
        data={"canal_origem": "Interno"},
    )
    assert response.status_code == 200 or response.status_code == 202
    dados = response.json()
    assert "trabalhos" in dados
    trabalho = dados["trabalhos"][0]
    assert trabalho["status"] == "falhou"
    assert trabalho["erro_codigo"] == "FALHA_ENFILEIRAMENTO"

    # Confere que evento SSE emitido foi de 'falha', e NUNCA 'status_update' com 'na_fila'
    assert len(eventos_publicados) == 1
    assert eventos_publicados[0][0] == "falha"
    assert eventos_publicados[0][1]["status"] == "falhou"
