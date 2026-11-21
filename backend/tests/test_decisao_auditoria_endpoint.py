import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.main import app
from app.controllers.auditoria import registrar_decisao_auditoria
from app.repositories.database import get_db
from app.schemas.triagem import DecisaoAuditoriaRequest


@pytest.fixture
def client():
    async def banco_de_teste():
        yield None

    app.dependency_overrides[get_db] = banco_de_teste
    try:
        yield app
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


def _post_com_timeout(app, path, payload, timeout_segundos=3):
    """Envia POST assíncrono e cancela a chamada se exceder o prazo."""
    async def executar_post():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                try:
                    return await asyncio.wait_for(
                        client.post(path, json=payload),
                        timeout=timeout_segundos,
                    )
                except asyncio.TimeoutError:
                    pytest.fail(
                        f"POST {path} não respondeu em {timeout_segundos} segundos.",
                        pytrace=False,
                    )

    return asyncio.run(executar_post())


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
        "app.controllers.auditoria.TriagemService", servico_nao_deve_ser_chamado
    )

    resposta = _post_com_timeout(client, "/triagem/auditoria/DOC-1/decisao", payload)

    assert resposta.status_code == 422


def test_handler_encaminha_correcao_parcial_validada_ao_servico(monkeypatch):
    payload = _payload("corrigido", {"cid_sugerido": "I20.0"})
    chamada = {}

    class ServicoFalso:
        def __init__(self, _db):
            pass

        def registrar_decisao_medica(self, documento_id, decisao):
            chamada["documento_id"] = documento_id
            chamada["decisao"] = decisao
            return SimpleNamespace(status_processamento="auditoria_corrigido")

    monkeypatch.setattr("app.controllers.auditoria.TriagemService", ServicoFalso)

    resposta = registrar_decisao_auditoria(
        "DOC-1",
        DecisaoAuditoriaRequest.model_validate(payload),
        db=None,
    )

    assert resposta["documento_id"] == "DOC-1"
    assert resposta["novo_status"] == "auditoria_corrigido"
    assert chamada["documento_id"] == "DOC-1"
    assert chamada["decisao"].dados_corrigidos.cid_sugerido == "I20.0"
