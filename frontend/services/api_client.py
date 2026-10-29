from copy import deepcopy

from services.respostas_mock import (
    FILA_AUDITORIA_MOCK,
    HISTORICO_MOCK,
    RESPOSTA_AMBIGUA,
    RESPOSTA_ROTINA,
    RESPOSTA_URGENCIA,
)

TERMOS_DE_URGENCIA = ("tep", "embolia", "urgente")
TERMOS_DE_AMBIGUIDADE = ("ilegível", "ilegivel", "rasurado", "crm ausente")


def enviar_documento(requisicao: dict) -> dict:
    return deepcopy(_escolher_resposta_mock(requisicao["documento_texto"]))


def listar_documentos() -> list[dict]:
    return deepcopy(HISTORICO_MOCK)


def listar_fila_auditoria() -> list[dict]:
    return deepcopy(FILA_AUDITORIA_MOCK)


def registrar_decisao(documento_id: str, decisao: dict) -> dict:
    return {
        "mensagem": "Decisão de auditoria registrada com sucesso.",
        "documento_id": documento_id,
        "novo_status": f"auditoria_{decisao['status_aprovacao']}",
    }


def _escolher_resposta_mock(documento_texto: str) -> dict:
    texto = documento_texto.lower()
    if any(termo in texto for termo in TERMOS_DE_URGENCIA):
        return RESPOSTA_URGENCIA
    if any(termo in texto for termo in TERMOS_DE_AMBIGUIDADE):
        return RESPOSTA_AMBIGUA
    return RESPOSTA_ROTINA