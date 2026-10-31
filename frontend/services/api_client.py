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
    return [_resumir_documento(documento, posicao) for posicao, documento in enumerate(HISTORICO_MOCK)]


def buscar_documento(documento_id: str) -> dict | None:
    for documento in HISTORICO_MOCK:
        if documento["documento_id"] == documento_id:
            return deepcopy(documento)
    return None


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


def _resumir_documento(documento: dict, posicao: int) -> dict:
    classificacao = documento["classificacao"]
    decisao = documento["decisao_roteamento"]
    requer_auditoria = decisao["requer_auditoria_humana"]
    return {
        "documento_id": documento["documento_id"],
        "tipo_documento": classificacao["tipo_documento"],
        "nivel_prioridade": classificacao["nivel_prioridade"],
        "score_confianca": classificacao["score_confianca_classificacao"],
        "destino_principal": decisao["destino_principal"],
        "status_processamento": "em_auditoria" if requer_auditoria else "processado",
        "requer_auditoria_humana": requer_auditoria,
        "created_at": f"2026-10-27T{9 + posicao:02d}:00:00",
    }