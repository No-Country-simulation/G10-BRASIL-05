import time
import uuid
import hmac
from typing import Optional

from fastapi import BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config.logger import logger
from app.config.settings import settings
from app.repositories.database import DatabaseRepository, get_db
from app.services.evolution_service import EvolutionService
from app.services.evolution_triage_worker import worker_processar_triagem_whatsapp
from app.services.redis_service import RedisAuditService


def verificar_status_webhook():
    """Endpoint de checagem de saúde e conectividade do Webhook da Evolution API."""
    return {
        "status": "online",
        "provedor": "Evolution API (WhatsApp)",
        "instancia_configurada": settings.EVOLUTION_INSTANCE_NAME,
    }

async def receber_webhook_evolution(
    request: Request,
    background_tasks: BackgroundTasks,
    evento_path: Optional[str] = None,
    x_webhook_token: Optional[str] = Header(None, alias="x-webhook-token"),
    apikey: Optional[str] = Header(None, alias="apikey"),
    db: Session = Depends(get_db),
):
    """Recebe eventos disparados pela Evolution API (especialmente MESSAGES_UPSERT).

    - Valida o segredo de autenticação configurado.
    - Garante idempotência via Redis (evita processamento duplicado).
    - Responde HTTP 200 imediatamente.
    - Processa o documento e responde no WhatsApp de forma assíncrona.
    """
    print(f"[WEBHOOK HIT] path={request.url.path} subpath={evento_path} headers={dict(request.headers)}", flush=True)

    # 2. Leitura do Payload JSON
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}

    # 1. Validação de Segurança do Webhook (aceita token dedicado ou apikey da Evolution)
    secret_esperado = settings.EVOLUTION_WEBHOOK_SECRET
    api_key_esperada = settings.EVOLUTION_API_KEY
    token_recebido = (
        x_webhook_token
        or apikey
        or request.headers.get("x-webhook-token")
        or request.headers.get("apikey")
        or (payload.get("apikey") if isinstance(payload, dict) else None)
    )

    token_valido = False
    if token_recebido:
        if secret_esperado and hmac.compare_digest(token_recebido, secret_esperado):
            token_valido = True
        elif api_key_esperada and hmac.compare_digest(token_recebido, api_key_esperada):
            token_valido = True

    print(f"[WEBHOOK AUTH] token_valido={token_valido} token_recebido={'SIM' if token_recebido else 'NAO'}", flush=True)

    if not token_valido:
        logger.warning("Tentativa de webhook não autorizada; credencial não reconhecida.")
        print("[WEBHOOK AUTH FAILED] Retornando 401 Unauthorized", flush=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de webhook inválido ou não informado.",
        )

    # 3. Filtragem de Eventos
    evento = (payload.get("event") or evento_path or "").lower().replace("_", ".").replace("-", ".")
    print(f"[WEBHOOK EVENTO] evento={evento}", flush=True)
    if evento and not any(ev in evento for ev in ("messages.upsert", "message.upsert", "message", "send.message")):
        print(f"[WEBHOOK EVENTO IGNORADO] evento={evento}", flush=True)
        return {"status": "ignored", "event": evento}

    # 4. Extração e Normalização
    dados = EvolutionService.extrair_dados_mensagem(payload)
    print(f"[WEBHOOK DADOS EXTRAIDOS] dados={dados}", flush=True)
    if not dados:
        print("[WEBHOOK DADOS VAZIOS OU FROM_ME] Ignorando", flush=True)
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

    # 6. Mídia segue para triagem; texto simples orienta o envio de documento ou consulta protocolo.
    if dados.get("tipo") == "midia":
        doc_id = f"DOC-WPP-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"Enfileirando triagem WhatsApp: {doc_id} para o número {numero}")
        if numero:
            redis_service.salvar_sessao_whatsapp(
                numero,
                {"ultimo_documento_id": doc_id, "tipo": "midia", "timestamp": time.time()},
            )
        background_tasks.add_task(worker_processar_triagem_whatsapp, dados, doc_id)
        return {
            "status": "queued",
            "documento_id": doc_id,
            "message_id": message_id,
            "numero": numero,
        }

    texto_recebido = dados.get("texto") or ""
    if numero:
        redis_service.salvar_sessao_whatsapp(
            numero,
            {"ultimo_texto": texto_recebido[:100], "tipo": "texto", "timestamp": time.time()},
        )
    protocolo_consultado = EvolutionService.extrair_protocolo_do_texto(texto_recebido)
    mensagem_resposta = EvolutionService.responder_mensagem_texto_autonomo(
        texto=texto_recebido,
        push_name=dados.get("push_name") or "Paciente",
        db_repo=DatabaseRepository(db),
    )
    destinatario = dados.get("numero") or dados.get("remote_jid")
    print(f"[WEBHOOK ENVIANDO RESPOSTA] destinatario={destinatario} resposta={mensagem_resposta[:60]}...", flush=True)
    background_tasks.add_task(EvolutionService().enviar_resposta, destinatario, mensagem_resposta)
    return {
        "status": "replied_info",
        "message_id": message_id,
        "numero": numero,
        **({"protocolo_consultado": protocolo_consultado} if protocolo_consultado else {}),
    }
