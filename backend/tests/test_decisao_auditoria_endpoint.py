from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.database import get_db


@pytest.fixture
def client():
    def banco_de_teste():
        yield None

    app.dependency_overrides[get_db] = banco_de_teste
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _payload(status_aprovacao, dados_corrigidos="ausente"):
    payload = {
        "status_aprovacao": status_aprovacao,
        "auditor_nome": "Dra. Ana Silva",
        "justificativa": "Revisão clínica concluída.",
    }
    if dados_corrigidos != "ausente":
        payload["dados_corrigidos"] = dados_corrigidos
    return payload


@pytest.mark.parametrize(
    "payload",
    [
        _payload("desconhecido"),
        _payload("corrigido"),
        _payload("corrigido", {}),
        _payload("corrigido", {"dados_desconhecidos": "valor"}),
        _payload("aprovado", {"cid_sugerido": "I20.0"}),
    ],
)
def test_endpoint_retorna_422_sem_invocar_servico_para_decisao_invalida(
    client, monkeypatch, payload
):
    def servico_nao_deve_ser_chamado(_db):
        pytest.fail("Payload inválido não pode chegar à camada de serviço.")

    monkeypatch.setattr(
        "app.controllers.triagem.TriagemService", servico_nao_deve_ser_chamado
    )

    resposta = client.post("/triagem/auditoria/DOC-1/decisao", json=payload)

    assert resposta.status_code == 422


def test_endpoint_encaminha_correcao_parcial_validada_ao_servico(client, monkeypatch):
    payload = _payload("corrigido", {"cid_sugerido": "I20.0"})
    chamada = {}

    class ServicoFalso:
        def __init__(self, _db):
            pass

        def registrar_decisao_medica(self, documento_id, decisao):
            chamada["documento_id"] = documento_id
            chamada["decisao"] = decisao
            return SimpleNamespace(status_processamento="auditoria_corrigido")

    monkeypatch.setattr("app.controllers.triagem.TriagemService", ServicoFalso)

    resposta = client.post("/triagem/auditoria/DOC-1/decisao", json=payload)

    assert resposta.status_code == 200
    assert chamada["documento_id"] == "DOC-1"
    assert chamada["decisao"].dados_corrigidos.cid_sugerido == "I20.0"
