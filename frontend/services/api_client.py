from services.respostas_mock import (
    RESPOSTA_AMBIGUA,
    RESPOSTA_ROTINA,
    RESPOSTA_URGENCIA,
)

TERMOS_DE_URGENCIA = ("tep", "embolia", "urgente")
TERMOS_DE_AMBIGUIDADE = ("ilegível", "ilegivel", "rasurado", "crm ausente")


def enviar_documento(requisicao: dict) -> dict:
    return _escolher_resposta_mock(requisicao["documento_texto"])


def _escolher_resposta_mock(documento_texto: str) -> dict:
    texto = documento_texto.lower()
    if any(termo in texto for termo in TERMOS_DE_URGENCIA):
        return RESPOSTA_URGENCIA
    if any(termo in texto for termo in TERMOS_DE_AMBIGUIDADE):
        return RESPOSTA_AMBIGUA
    return RESPOSTA_ROTINA