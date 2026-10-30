import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.database import init_db
from app.services.redis_service import RedisAuditService
from app.repositories.nosql_auditoria import MongoAuditoriaRepository

init_db()
client = TestClient(app)


def test_lock_distribuido_concorrencia_redis():
    """Valida aquisição de lock exclusivo, bloqueio contra segundo médico (409) e liberação."""
    doc_id = "DOC-LOCK-TEST-001"

    # Cria documento prévio no sistema
    res_triagem = client.post(
        "/triagem",
        json={
            "documento_id": doc_id,
            "tipo_arquivo": "TEXTO",
            "canal_origem": "Pronto_Socorro",
            "documento_texto": "Paciente com suspeita leve. Encaminhar para observação.",
        },
    )
    assert res_triagem.status_code == 200

    # 1. Dr. Roberto adquire o lock de auditoria
    res_lock1 = client.post(
        f"/triagem/auditoria/{doc_id}/bloquear",
        json={"auditor_nome": "Dr. Roberto Silva", "ttl_segundos": 120},
    )
    assert res_lock1.status_code == 200
    assert res_lock1.json()["bloqueado"] is True
    assert res_lock1.json()["auditor"] == "Dr. Roberto Silva"

    # 2. Dra. Renata tenta auditar simultaneamente o mesmo laudo -> Deve receber 409 Conflito
    res_lock2 = client.post(
        f"/triagem/auditoria/{doc_id}/bloquear",
        json={"auditor_nome": "Dra. Renata Silveira", "ttl_segundos": 120},
    )
    assert res_lock2.status_code == 409
    payload_erro = res_lock2.json().get("erro", {})
    msg_erro = payload_erro.get("mensagem", "") or res_lock2.json().get("detail", "")
    assert "Dr. Roberto Silva" in msg_erro

    # 3. Consulta status do lock
    res_status = client.get(f"/triagem/auditoria/{doc_id}/status-lock")
    assert res_status.status_code == 200
    assert res_status.json()["bloqueado"] is True
    assert res_status.json()["auditor"] == "Dr. Roberto Silva"

    # 4. Outro médico tenta desbloquear sem possuir o lock -> 403 Forbidden
    res_desbloqueio_indevido = client.post(
        f"/triagem/auditoria/{doc_id}/desbloquear",
        json={"auditor_nome": "Dra. Renata Silveira"},
    )
    assert res_desbloqueio_indevido.status_code == 403

    # 5. Dr. Roberto libera o lock
    res_desbloqueio = client.post(
        f"/triagem/auditoria/{doc_id}/desbloquear",
        json={"auditor_nome": "Dr. Roberto Silva"},
    )
    assert res_desbloqueio.status_code == 200
    assert res_desbloqueio.json()["bloqueado"] is False

    # 6. Agora Dra. Renata consegue adquirir o lock
    res_lock3 = client.post(
        f"/triagem/auditoria/{doc_id}/bloquear",
        json={"auditor_nome": "Dra. Renata Silveira", "ttl_segundos": 120},
    )
    assert res_lock3.status_code == 200
    assert res_lock3.json()["bloqueado"] is True


def test_trilha_auditoria_nosql_mongodb():
    """Valida a persistência imutável de eventos clínicos na base NoSQL (MongoDB)."""
    doc_id = "DOC-NOSQL-AUDIT-002"

    # 1. Ingestão do documento na triagem -> deve gerar evento TRIAGEM_INICIAL no NoSQL
    res_triagem = client.post(
        "/triagem",
        json={
            "documento_id": doc_id,
            "tipo_arquivo": "TEXTO",
            "canal_origem": "Telemedicina",
            "documento_texto": "Receituário para dor torácica. Requer conferência médica urgente.",
        },
    )
    assert res_triagem.status_code == 200

    # 2. Médico adquire lock
    client.post(
        f"/triagem/auditoria/{doc_id}/bloquear",
        json={"auditor_nome": "Dr. Lucas Ramos", "ttl_segundos": 300},
    )

    # 3. Médico submete decisão médica
    res_decisao = client.post(
        f"/triagem/auditoria/{doc_id}/decisao",
        json={
            "status_aprovacao": "corrigido",
            "auditor_nome": "Dr. Lucas Ramos",
            "justificativa": "Ajustado CID para I20 e prescrito anticoagulante.",
            "dados_corrigidos": {"cid_sugerido": "I20.0"},
        },
    )
    assert res_decisao.status_code == 200

    # 4. Lock deve ter sido liberado automaticamente após decisão médica
    status_lock = client.get(f"/triagem/auditoria/{doc_id}/status-lock").json()
    assert status_lock["bloqueado"] is False

    # 5. Consulta trilha de auditoria NoSQL
    res_trilha = client.get(f"/triagem/auditoria/{doc_id}/trilha-nosql")
    assert res_trilha.status_code == 200
    eventos = res_trilha.json()
    assert len(eventos) >= 3

    tipos = [e["tipo_evento"] for e in eventos]
    assert "TRIAGEM_INICIAL" in tipos
    assert "BLOQUEIO_EXCLUSIVO" in tipos
    assert "DECISAO_MEDICA_CORRIGIDO" in tipos


def test_resiliencia_fallback_desconectado():
    """Valida que instanciar serviços com portas inválidas ativa fallback transparente sem quebrar."""
    redis_mock = RedisAuditService(redis_url="redis://localhost:59999/0")
    assert redis_mock.is_conectado is False
    # Operações em fallback continuam funcionando
    assert redis_mock.adquirir_lock("DOC-FALLBACK-1", "Dr. Teste", 60) is True
    assert redis_mock.adquirir_lock("DOC-FALLBACK-1", "Outro Médico", 60) is False
    assert redis_mock.liberar_lock("DOC-FALLBACK-1", "Dr. Teste") is True

    mongo_mock = MongoAuditoriaRepository(mongo_url="mongodb://localhost:59999")
    assert mongo_mock.is_conectado is False
    # Operações NoSQL em fallback continuam funcionando
    ev = mongo_mock.gravar_evento("DOC-FALLBACK-1", "TESTE", "Sistema", {"chave": "valor"})
    assert ev["tipo_evento"] == "TESTE"
    lista = mongo_mock.listar_por_documento("DOC-FALLBACK-1")
    assert len(lista) >= 1
    assert lista[0]["documento_id"] == "DOC-FALLBACK-1"
