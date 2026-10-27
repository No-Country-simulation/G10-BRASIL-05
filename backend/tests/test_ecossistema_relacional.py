import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.database import init_db

init_db()
client = TestClient(app)


def test_seed_hospitais_e_medicos():
    """Valida que o seed inicial do banco populou hospitais de referência."""
    response = client.get("/hospitais")
    assert response.status_code == 200
    hospitais = response.json()
    assert len(hospitais) >= 1
    nomes = [h["nome"] for h in hospitais]
    assert any("Hospital Central MediFlow" in n for n in nomes)


def test_listar_medicos_inicial():
    """Valida consulta de médicos cadastrados."""
    response = client.get("/medicos")
    assert response.status_code == 200
    medicos = response.json()
    assert isinstance(medicos, list)
    assert len(medicos) >= 1


def test_upsert_paciente_e_medico_na_triagem():
    """Valida que a triagem de um laudo cria automaticamente o paciente e o médico relacionalmente."""
    payload = {
        "documento_id": "TEST-REL-001",
        "tipo_arquivo": "TEXTO",
        "canal_origem": "Pronto_Socorro",
        "documento_texto": (
            "HOSPITAL CENTRAL - LAUDO DE TOMOGRAFIA\n"
            "Paciente: Juliana Prado Ferreira, 42 anos, CPF: 234.567.890-11\n"
            "Médico Solicitante: Dr. Fernando Albuquerque, CRM: 112233-SP\n"
            "Diagnóstico: Apendicite aguda fase supurativa.\n"
            "Conduta: Encaminhamento cirúrgico imediato de emergência."
        ),
    }

    response_triagem = client.post("/triagem", json=payload)
    assert response_triagem.status_code == 200
    res_json = response_triagem.json()
    assert res_json["documento_id"] == "TEST-REL-001"

    # 1. Verifica se o paciente foi criado no ecossistema
    resp_pacientes = client.get("/pacientes")
    assert resp_pacientes.status_code == 200
    pacientes = resp_pacientes.json()
    paciente_encontrado = next((p for p in pacientes if "Juliana Prado Ferreira" in p["nome"]), None)
    assert paciente_encontrado is not None
    assert paciente_encontrado["idade"] == 42
    paciente_id = paciente_encontrado["id"]

    # 2. Verifica detalhes cadastrais do paciente
    resp_detalhes = client.get(f"/pacientes/{paciente_id}")
    assert resp_detalhes.status_code == 200
    assert resp_detalhes.json()["nome"] == "Juliana Prado Ferreira"

    # 3. Consulta histórico longitudinal do paciente
    resp_hist = client.get(f"/pacientes/{paciente_id}/historico")
    assert resp_hist.status_code == 200
    hist_data = resp_hist.json()
    assert hist_data["total_documentos"] >= 1
    docs = [d["documento_id"] for d in hist_data["historico"]]
    assert "TEST-REL-001" in docs

    # 4. Verifica se o médico foi cadastrado no corpo clínico
    resp_medicos = client.get("/medicos")
    assert resp_medicos.status_code == 200
    medicos = resp_medicos.json()
    medico_encontrado = next((m for m in medicos if "112233-SP" in m["crm"]), None)
    assert medico_encontrado is not None


def test_reutilizacao_paciente_segundo_documento():
    """Valida que um segundo laudo do mesmo paciente vincula ao mesmo paciente_id (sem duplicar)."""
    # Primeiro documento já gerou Juliana Prado Ferreira
    payload2 = {
        "documento_id": "TEST-REL-002",
        "tipo_arquivo": "TEXTO",
        "canal_origem": "Ambulatorio",
        "documento_texto": (
            "RECEITUÁRIO MÉDICO PÓS-OPERATÓRIO\n"
            "Paciente: Juliana Prado Ferreira, 42 anos, CPF: 234.567.890-11\n"
            "Médico Solicitante: Dr. Fernando Albuquerque, CRM: 112233-SP\n"
            "Prescrição: Ciprofloxacino 500mg por 7 dias."
        ),
    }

    res2 = client.post("/triagem", json=payload2)
    assert res2.status_code == 200

    # Busca o paciente novamente
    resp_pacientes = client.get("/pacientes")
    pacientes = [p for p in resp_pacientes.json() if "Juliana Prado Ferreira" in p["nome"]]
    # Não deve haver duplicatas de paciente
    assert len(pacientes) == 1
    paciente_id = pacientes[0]["id"]

    # Histórico agora deve ter ambos os documentos (TEST-REL-001 e TEST-REL-002)
    resp_hist = client.get(f"/pacientes/{paciente_id}/historico")
    assert resp_hist.status_code == 200
    hist_data = resp_hist.json()
    doc_ids = [d["documento_id"] for d in hist_data["historico"]]
    assert "TEST-REL-001" in doc_ids
    assert "TEST-REL-002" in doc_ids
    assert hist_data["total_documentos"] >= 2


def test_paciente_nao_encontrado_404():
    """Valida retorno 404 para paciente inexistente."""
    resp = client.get("/pacientes/999999")
    assert resp.status_code == 404

    resp_hist = client.get("/pacientes/999999/historico")
    assert resp_hist.status_code == 404
