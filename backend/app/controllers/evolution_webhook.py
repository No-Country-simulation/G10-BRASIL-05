import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request, status

from app.config.logger import logger
from app.config.settings import settings
from app.services.evolution_service import EvolutionService
from app.services.evolution_triage_worker import worker_processar_triagem_whatsapp
from app.services.redis_service import RedisAuditService

router = APIRouter(prefix="/webhook/evolution", tags=["WhatsApp (Evolution API)"])

@router.get("", status_code=status.HTTP_200_OK)
def verificar_status_webhook():
    """Endpoint de checagem de saúde e conectividade do Webhook da Evolution API."""
    return {
        "status": "online",
        "provedor": "Evolution API (WhatsApp)",
        "instancia_configurada": settings.EVOLUTION_INSTANCE_NAME,
        "evolution_url": settings.EVOLUTION_API_URL,
    }

@router.post("", status_code=status.HTTP_200_OK)
async def receber_webhook_evolution(
    request: Request,
    background_tasks: BackgroundTasks,
    token: Optional[str] = Query(None, description="Token de autenticação do webhook"),
    x_webhook_token: Optional[str] = Header(None, alias="x-webhook-token"),
    apikey: Optional[str] = Header(None, alias="apikey"),
):
    """Recebe eventos disparados pela Evolution API (especialmente MESSAGES_UPSERT).

    - Valida o segredo de autenticação configurado.
    - Garante idempotência via Redis (evita processamento duplicado).
    - Responde HTTP 200 imediatamente.
    - Processa o documento e responde no WhatsApp de forma assíncrona.
    """
    # 1. Validação de Segurança do Webhook
    secret_esperado = settings.EVOLUTION_WEBHOOK_SECRET
    token_recebido = token or x_webhook_token or apikey

    if secret_esperado and token_recebido != secret_esperado:
        logger.warning(f"Tentativa de webhook não autorizada com token: '{token_recebido}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de webhook inválido ou não informado.",
        )

    # 2. Leitura do Payload JSON
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload JSON inválido.",
        )

    # 3. Filtragem de Eventos
    evento = (payload.get("event") or "").lower().replace("_", ".")
    logger.info(f"Recebido evento webhook da Evolution API: '{evento}'")
    if evento and not any(ev in evento for ev in ("messages.upsert", "message.upsert", "message", "send.message")):
        logger.debug(f"Evento ignorado no webhook: {evento}")
        return {"status": "ignored", "event": evento}

    # 4. Extração e Normalização
    dados = EvolutionService.extrair_dados_mensagem(payload)
    if not dados:
        return {"status": "ignored", "motivo": "mensagem_propria_ou_invalida"}

    message_id = dados.get("message_id")
    numero = dados.get("numero")

    # 5. Garantia de Idempotência com Redis
    redis_service = RedisAuditService()
    if message_id:
        chave_idempotencia = f"evolution:msg:{message_id}"
        eh_novo = redis_service.registrar_idempotencia(chave_idempotencia, ttl_segundos=86400)
        if not eh_novo:
            logger.info(f"Mensagem {message_id} já processada anteriormente (idempotência acionada).")
            return {"status": "ignored", "motivo": "já_processado", "message_id": message_id}

    # 6. Roteamento: Mídia vs Texto Simples
    evolution = EvolutionService()

    if dados.get("tipo") == "midia":
        doc_id = f"DOC-WPP-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"Enfileirando triagem WhatsApp: {doc_id} para o número {numero}")
        background_tasks.add_task(worker_processar_triagem_whatsapp, dados, doc_id)
        return {
            "status": "queued",
            "documento_id": doc_id,
            "message_id": message_id,
            "numero": numero,
        }

    # Se for mensagem de texto comum, responde com informações de ajuda
    background_tasks.add_task(
        evolution.enviar_resposta,
        numero,
        EvolutionService.formatar_mensagem_ajuda(),
    )
    return {
        "status": "replied_info",
        "message_id": message_id,
        "numero": numero,
    }
