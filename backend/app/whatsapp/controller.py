"""Controlador FastAPI com rotas padrão para o módulo autônomo WhatsApp (Evolution API)."""

import hmac
import time
import uuid
from typing import Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config.logger import logger
from app.config.settings import settings
from app.repositories.database import DatabaseRepository, get_db
from app.services.autenticacao import exigir_papeis
from app.services.redis_service import RedisAuditService
from app.whatsapp.repository import WhatsappRepository
from app.whatsapp.schemas import (
    ConfigurarWebhookRequest,
    EnvioManualWhatsApp,
    EnvioManualWhatsAppRequest,
    InstanciaStatusResponse,
    QRCodeResponse,
)
from app.whatsapp.service import WhatsappEvolutionService
from app.whatsapp.worker import worker_processar_triagem_whatsapp

router = APIRouter(tags=["WhatsApp (Evolution API)"])


def _exigir_conta_institucional_whatsapp(
    _usuario=Depends(exigir_papeis("ADMIN_GERAL", "INSTITUCIONAL_WHATSAPP")),
    db: Session = Depends(get_db),
) -> DatabaseRepository:
    """Exige JWT de conta institucional do WhatsApp e retorna seu repositório."""
    return DatabaseRepository(db)


@router.get("", include_in_schema=False)
@router.get("/", summary="Verificar status do webhook", status_code=status.HTTP_200_OK)
def verificar_status_webhook():
    """Endpoint de checagem de saúde e conectividade do Webhook da Evolution API."""
    return {
        "status": "online",
        "provedor": "Evolution API (WhatsApp)",
        "instancia_configurada": settings.EVOLUTION_INSTANCE_NAME,
    }


@router.post("", include_in_schema=False)
@router.post("/", summary="Receber webhook Evolution", status_code=status.HTTP_200_OK)
@router.post("/{evento_path}", summary="Receber webhook Evolution por evento", status_code=status.HTTP_200_OK)
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

    if not token_valido:
        logger.warning("Tentativa de webhook não autorizada; credencial não reconhecida.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de webhook inválido ou não informado.",
        )

    # 3. Filtragem de Eventos
    evento = (payload.get("event") or evento_path or "").lower().replace("_", ".").replace("-", ".")
    if evento and not any(ev in evento for ev in ("messages.upsert", "message.upsert", "message", "send.message")):
        return {"status": "ignored", "event": evento}

    # 4. Extração e Normalização
    dados = WhatsappEvolutionService.extrair_dados_mensagem(payload)
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
    protocolo_consultado = WhatsappEvolutionService.extrair_protocolo_do_texto(texto_recebido)
    mensagem_resposta = WhatsappEvolutionService.responder_mensagem_texto_autonomo(
        texto=texto_recebido,
        push_name=dados.get("push_name") or "Paciente",
        db_repo=DatabaseRepository(db),
    )
    destinatario = dados.get("numero") or dados.get("remote_jid")
    background_tasks.add_task(WhatsappEvolutionService().enviar_resposta, destinatario, mensagem_resposta)
    return {
        "status": "replied_info",
        "message_id": message_id,
        "numero": numero,
        **({"protocolo_consultado": protocolo_consultado} if protocolo_consultado else {}),
    }


@router.get("/status-instancia", summary="Consultar status da instância WhatsApp", status_code=status.HTTP_200_OK)
async def consultar_status_instancia(
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Consulta o estado de conexão e saúde da instância única do WhatsApp e sincroniza no banco."""
    evolution = WhatsappEvolutionService()
    estado = await evolution.obter_estado_conexao()
    instancia_db = repo.atualizar_estado_instancia_whatsapp(
        conectado=bool(estado.get("conectado")),
        status_conexao=str(estado.get("estado") or "close"),
    )
    return {
        "instancia": instancia_db.instance_name,
        "api_url": settings.EVOLUTION_API_URL,
        "gerenciado_por_email": instancia_db.gerenciado_por_email,
        "modo_operacao": instancia_db.modo_operacao,
        **estado,
    }


@router.post("/conectar", summary="Conectar WhatsApp QR Code", status_code=status.HTTP_200_OK)
async def conectar_whatsapp_qrcode(
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Gera ou obtém o QR Code para conectar a instância única do WhatsApp no frontend."""
    logger.info("Solicitação de geração de QR Code recebida.", extra={"path": "/webhook/evolution/conectar"})
    evolution = WhatsappEvolutionService()
    estado = await evolution.obter_estado_conexao()
    if estado.get("conectado"):
        instancia_db = repo.atualizar_estado_instancia_whatsapp(
            conectado=True,
            status_conexao="open",
        )
        return {
            "conectado": True,
            "estado": "open",
            "instancia": instancia_db.instance_name,
            "gerenciado_por_email": instancia_db.gerenciado_por_email,
            "mensagem": "WhatsApp já está conectado e pronto para uso.",
        }

    if estado.get("estado") == "not_found":
        await evolution.criar_instancia()

    resultado_qr = await evolution.obter_qrcode()

    instancia_db = repo.atualizar_estado_instancia_whatsapp(
        conectado=False,
        status_conexao="connecting" if resultado_qr.get("sucesso") else "close",
    )
    return {
        "conectado": False,
        "instancia": instancia_db.instance_name,
        "gerenciado_por_email": instancia_db.gerenciado_por_email,
        **resultado_qr,
    }


@router.post("/configurar-webhook", summary="Configurar Webhook no Evolution API", status_code=status.HTTP_200_OK)
async def auto_configurar_webhook(
    payload: Optional[ConfigurarWebhookRequest] = None,
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Configura o webhook na Evolution API apontando para o backend e persiste a URL no banco."""
    evolution = WhatsappEvolutionService()
    url = payload.url if payload else None
    resultado = await evolution.configurar_webhook(url)
    if not resultado.get("sucesso"):
        detalhe = resultado.get("erro") or "Não foi possível configurar o webhook na Evolution API."
        codigo = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if resultado.get("status_code") == 503
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=codigo, detail=detalhe)

    atual = repo.obter_ou_criar_instancia_whatsapp()
    repo.atualizar_estado_instancia_whatsapp(
        conectado=atual.conectado,
        status_conexao=atual.status_conexao,
        webhook_url=resultado.get("url"),
    )
    return resultado


@router.post("/desconectar", summary="Desconectar WhatsApp", status_code=status.HTTP_200_OK)
async def desconectar_whatsapp(
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Desconecta a sessão atual do WhatsApp e atualiza o estado no banco."""
    evolution = WhatsappEvolutionService()
    resultado = await evolution.desconectar()
    if resultado.get("sucesso"):
        repo.atualizar_estado_instancia_whatsapp(
            conectado=False,
            status_conexao="close",
        )
    return resultado


@router.post("/enviar-teste", summary="Disparo manual de mensagem de teste", status_code=status.HTTP_200_OK)
async def enviar_mensagem_teste(
    payload: EnvioManualWhatsApp,
    _repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Endpoint utilitário para disparo manual de mensagens de teste pelo WhatsApp."""
    evolution = WhatsappEvolutionService()
    sucesso = await evolution.enviar_resposta(payload.numero, payload.texto)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível enviar a mensagem através da Evolution API.",
        )
    return {"status": "enviado", "numero": payload.numero}
