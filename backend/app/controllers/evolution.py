import uuid
from typing import Optional, Dict, Any
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    Query,
    Request,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.config.logger import logger
from app.services.evolution_service import EvolutionService
from app.services.redis_service import RedisAuditService
from app.services.document_parser import DocumentParserService
from app.services.triagem import TriagemService
from app.schemas.triagem import RequisicaoTriagem
from app.repositories.database import SessionLocal
from app.repositories.storage import StorageRepository

router = APIRouter(prefix="/webhook/evolution", tags=["WhatsApp (Evolution API)"])


class EnvioManualWhatsApp(BaseModel):
    numero: str = Field(..., example="5511999999999", description="Número de telefone com DDI e DDD")
    texto: str = Field(..., example="Olá! Teste de integração MediFlow.", description="Conteúdo da mensagem")


async def worker_processar_triagem_whatsapp(dados: Dict[str, Any], doc_id: str):
    """Worker assíncrono executado em background para processar mídia e devolver triagem."""
    evolution = EvolutionService()
    numero = dados["numero"]

    try:
        # 1. Envia confirmação imediata de recebimento no chat
        msg_recebido = EvolutionService.formatar_mensagem_recebido(doc_id)
        await evolution.enviar_resposta(numero, msg_recebido)

        # 2. Baixa o arquivo binário (via base64 direto ou pela Evolution API)
        conteudo = await evolution.baixar_midia_bytes(
            message_id=dados["message_id"],
            base64_direto=dados.get("base64"),
        )

        if not conteudo:
            logger.error(f"Falha ao obter mídia da mensagem {dados['message_id']} ({doc_id})")
            msg_erro = EvolutionService.formatar_mensagem_erro("Não foi possível recuperar a mídia enviada.")
            await evolution.enviar_resposta(numero, msg_erro)
            return

        # 3. Validação do arquivo e extração de texto clínico
        extensao = DocumentParserService.validar_bytes(
            conteudo=conteudo,
            nome_arquivo=dados.get("filename") or "documento_clinico",
            content_type=dados.get("mimetype"),
        )

        # 3.1. Persistência e renomeação do arquivo na pasta local Storage
        storage_repo = StorageRepository()
        info_storage = storage_repo.salvar_arquivo_whatsapp(
            documento_id=doc_id,
            conteudo=conteudo,
            nome_original=dados.get("filename"),
            extensao=extensao,
            mimetype=dados.get("mimetype"),
        )
        logger.info(
            f"Arquivo do WhatsApp persistido na pasta Storage: '{info_storage['nome_arquivo']}' "
            f"({info_storage['tamanho_bytes']} bytes) em {info_storage['caminho_local']}"
        )

        texto_extraido, tipo_arquivo = DocumentParserService.extrair_texto(
            conteudo=conteudo,
            extensao=extensao,
            nome_arquivo=dados.get("filename") or "documento_clinico",
        )

        # Se houver legenda enviada pelo usuário, anexa ao texto clínico
        legenda = dados.get("legenda")
        if legenda:
            texto_extraido = f"{texto_extraido}\n\n[Observação/Mensagem do Usuário]: {legenda}"

        # 4. Execução da Triagem Clínica via Agente LangGraph e Persistência
        db = SessionLocal()
        try:
            service = TriagemService(db)
            requisicao = RequisicaoTriagem(
                documento_id=doc_id,
                tipo_arquivo=tipo_arquivo,
                canal_origem="WhatsApp",
                documento_texto=texto_extraido,
            )
            resposta_triagem = service.processar_triagem(requisicao)
        finally:
            db.close()

        # 5. Formatação da Devolutiva e Envio ao Paciente/Médico no WhatsApp
        msg_devolutiva = EvolutionService.formatar_devolutiva_triagem(resposta_triagem)
        await evolution.enviar_resposta(numero, msg_devolutiva)
        logger.info(f"Triagem clínica {doc_id} concluída e entregue via WhatsApp para {numero}.")

    except Exception as exc:
        logger.exception(f"Erro inesperado no worker de WhatsApp para documento {doc_id}: {exc}")
        detalhe = getattr(exc, "detail", str(exc))
        msg_falha = EvolutionService.formatar_mensagem_erro(str(detalhe))
        await evolution.enviar_resposta(numero, msg_falha)


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


@router.post("/enviar-teste", status_code=status.HTTP_200_OK)
async def enviar_mensagem_teste(payload: EnvioManualWhatsApp):
    """Endpoint utilitário para disparo manual de mensagens de teste pelo WhatsApp."""
    evolution = EvolutionService()
    sucesso = await evolution.enviar_resposta(payload.numero, payload.texto)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível enviar a mensagem através da Evolution API.",
        )
    return {"status": "enviado", "numero": payload.numero}


class ConfigurarWebhookRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL pública ou interna do backend para o webhook")


@router.get("/status-instancia", status_code=status.HTTP_200_OK)
async def consultar_status_instancia():
    """Consulta o estado de conexão e saúde da instância do WhatsApp na Evolution API."""
    evolution = EvolutionService()
    estado = await evolution.obter_estado_conexao()
    return {
        "instancia": settings.EVOLUTION_INSTANCE_NAME,
        "api_url": settings.EVOLUTION_API_URL,
        **estado,
    }


@router.post("/conectar", status_code=status.HTTP_200_OK)
async def conectar_whatsapp_qrcode():
    """Gera ou obtém o QR Code para conectar o WhatsApp no frontend."""
    evolution = EvolutionService()
    # Verifica se já está conectado
    estado = await evolution.obter_estado_conexao()
    if estado.get("conectado"):
        return {
            "conectado": True,
            "estado": "open",
            "mensagem": "WhatsApp já está conectado e pronto para uso.",
        }

    # Se não existe, cria
    if estado.get("estado") == "not_found":
        await evolution.criar_instancia()

    # Obtém o QR Code
    resultado_qr = await evolution.obter_qrcode()
    if not resultado_qr.get("sucesso"):
        # Tenta criar instância e obter novamente
        await evolution.criar_instancia()
        resultado_qr = await evolution.obter_qrcode()

    return {
        "conectado": False,
        "instancia": settings.EVOLUTION_INSTANCE_NAME,
        **resultado_qr,
    }


@router.post("/configurar-webhook", status_code=status.HTTP_200_OK)
async def auto_configurar_webhook(payload: ConfigurarWebhookRequest = None):
    """Configura o webhook na Evolution API apontando para o backend."""
    evolution = EvolutionService()
    url = payload.url if payload else None
    resultado = await evolution.configurar_webhook(url)
    return resultado


@router.post("/desconectar", status_code=status.HTTP_200_OK)
async def desconectar_whatsapp():
    """Desconecta a sessão atual do WhatsApp."""
    evolution = EvolutionService()
    return await evolution.desconectar()
