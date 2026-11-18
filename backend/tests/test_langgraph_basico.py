"""Testes unitários do fluxo LangGraph sem subir API ou banco de dados."""

from uuid import uuid4

from app.agent.graph import executar_agente_triagem, retomar_agente_triagem


def _documento_medico(documento_id: str) -> dict:
    return {
        "documento_id": documento_id,
        "tipo_arquivo": "texto",
        "canal_origem": "Ambulatorio",
        "documento_texto": (
            "Receituário Médico. Paciente: Mariana Souza, 35 anos. "
            "Médico: Dr. Lucas Ramos CRM: 87654-SP. "
            "Uso oral: Losartana 50mg, tomar um comprimido pela manhã."
        ),
    }


def test_documento_culinario_e_recusado_sem_rota():
    resultado = executar_agente_triagem(
        {
            "documento_id": f"culinario-{uuid4()}",
            "tipo_arquivo": "texto",
            "documento_texto": "Receita de pudim: ingredientes e modo de preparo no forno.",
        }
    )

    assert resultado["status"] == "recusado"
    assert resultado.get("destino_principal") is None


def test_documento_medico_pausa_para_revisao_e_retorna():
    documento_id = f"revisao-{uuid4()}"
    resultado = executar_agente_triagem(_documento_medico(documento_id))

    assert resultado.get("__interrupt__")
    retomado = retomar_agente_triagem(
        documento_id,
        {"status_aprovacao": "aprovado", "auditor_nome": "Teste"},
    )

    assert retomado.get("status") in {"roteado", "aguardando_revisao"}
    assert not retomado.get("__interrupt__")


def test_elegibilidade_incerta_pausa_e_rejeicao_recusa():
    documento_id = f"incerto-{uuid4()}"
    resultado = executar_agente_triagem(
        {
            "documento_id": documento_id,
            "tipo_arquivo": "texto",
            "documento_texto": "Documento com conteúdo insuficiente para identificar o tipo.",
        }
    )

    assert resultado.get("__interrupt__")
    retomado = retomar_agente_triagem(
        documento_id,
        {"status_aprovacao": "rejeitado", "auditor_nome": "Teste"},
    )

    assert retomado["status"] == "recusado"
