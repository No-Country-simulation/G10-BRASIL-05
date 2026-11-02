import os
from copy import deepcopy
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

from services.respostas_mock import (
    HISTORICO_MOCK,
    RESPOSTA_AMBIGUA,
    RESPOSTA_ROTINA,
    RESPOSTA_URGENCIA,
)

TERMOS_DE_URGENCIA = ("tep", "embolia", "urgente")
TERMOS_DE_AMBIGUIDADE = ("ilegível", "ilegivel", "rasurado", "crm ausente")


def enviar_documento(requisicao: dict) -> dict:
    # Tenta enviar para a API real do backend
    try:
        url = f"{BACKEND_URL}/api/v1/triagem"
        resp = httpx.post(url, json=requisicao, timeout=30.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return deepcopy(_escolher_resposta_mock(requisicao["documento_texto"]))


def listar_documentos() -> list[dict]:
    try:
        url = f"{BACKEND_URL}/api/v1/triagem/documentos"
        resp = httpx.get(url, timeout=10.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return deepcopy(HISTORICO_MOCK)


def _escolher_resposta_mock(documento_texto: str) -> dict:
    texto = documento_texto.lower()
    if any(termo in texto for termo in TERMOS_DE_URGENCIA):
        return RESPOSTA_URGENCIA
    if any(termo in texto for termo in TERMOS_DE_AMBIGUIDADE):
        return RESPOSTA_AMBIGUA
    return RESPOSTA_ROTINA


# ------------------------------------------------------------------------------
# WhatsApp / Evolution API Client
# ------------------------------------------------------------------------------
def obter_status_whatsapp() -> dict:
    """Consulta o status da conexão do WhatsApp via backend."""
    try:
        url = f"{BACKEND_URL}/api/v1/webhook/evolution/status-instancia"
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        return {"conectado": False, "estado": f"HTTP {resp.status_code}", "detalhes": resp.text}
    except Exception as e:
        return {"conectado": False, "estado": "offline", "detalhes": f"Backend indisponível: {e}"}


def obter_qrcode_whatsapp() -> dict:
    """Solicita a geração ou leitura do QR Code do WhatsApp."""
    try:
        url = f"{BACKEND_URL}/api/v1/webhook/evolution/conectar"
        resp = httpx.post(url, timeout=15.0)
        if resp.status_code == 200:
            return resp.json()
        return {"sucesso": False, "erro": resp.text}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def configurar_webhook_whatsapp(webhook_url: str = None) -> dict:
    """Configura o webhook de escuta na Evolution API."""
    try:
        url = f"{BACKEND_URL}/api/v1/webhook/evolution/configurar-webhook"
        payload = {"url": webhook_url} if webhook_url else {}
        resp = httpx.post(url, json=payload, timeout=10.0)
        if resp.status_code == 200:
            return resp.json()
        return {"sucesso": False, "erro": resp.text}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def enviar_teste_whatsapp(numero: str, texto: str) -> dict:
    """Dispara uma mensagem de teste para o WhatsApp informado."""
    try:
        url = f"{BACKEND_URL}/api/v1/webhook/evolution/enviar-teste"
        resp = httpx.post(url, json={"numero": numero, "texto": texto}, timeout=15.0)
        if resp.status_code == 200:
            return {"sucesso": True, "dados": resp.json()}
        return {"sucesso": False, "erro": resp.text}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def desconectar_whatsapp() -> dict:
    """Desconecta a sessão ativa do WhatsApp."""
    try:
        url = f"{BACKEND_URL}/api/v1/webhook/evolution/desconectar"
        resp = httpx.post(url, timeout=10.0)
        return resp.json()
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
