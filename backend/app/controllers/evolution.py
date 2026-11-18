from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.evolution_service import EvolutionService

router = APIRouter(prefix="/webhook/evolution", tags=["WhatsApp (Evolution API)"])

class EnvioManualWhatsApp(BaseModel):
    numero: str = Field(..., json_schema_extra={"example": "5511999999999"}, description="Número de telefone com DDI e DDD")
    texto: str = Field(..., json_schema_extra={"example": "Olá! Teste de integração MediFlow."}, description="Conteúdo da mensagem")

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
