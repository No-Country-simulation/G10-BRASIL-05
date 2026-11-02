import os
from copy import deepcopy
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

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
    return [_resumir_documento(documento, posicao) for posicao, documento in enumerate(HISTORICO_MOCK)]


def buscar_documento(documento_id: str) -> dict | None:
    try:
        url = f"{BACKEND_URL}/api/v1/triagem/documentos"
        resp = httpx.get(url, timeout=10.0)
        if resp.status_code == 200:
            for doc in resp.json():
                if doc.get("documento_id") == documento_id:
                    return deepcopy(doc)
    except Exception:
        pass

    for documento in HISTORICO_MOCK:
        if documento["documento_id"] == documento_id:
            return deepcopy(documento)
    return None


def listar_fila_auditoria() -> list[dict]:
    try:
        url = f"{BACKEND_URL}/api/v1/triagem/auditoria"
        resp = httpx.get(url, timeout=10.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return deepcopy(FILA_AUDITORIA_MOCK)


def registrar_decisao(documento_id: str, decisao: dict) -> dict:
    try:
        url = f"{BACKEND_URL}/api/v1/triagem/auditoria/{documento_id}/decisao"
        resp = httpx.post(url, json=decisao, timeout=10.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass

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
