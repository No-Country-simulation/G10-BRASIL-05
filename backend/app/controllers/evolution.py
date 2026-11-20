from typing import Optional

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from urllib.parse import urlsplit

from app.config.settings import settings
from app.config.logger import logger
from app.repositories.database import (
    DatabaseRepository,
    get_db,
)
from app.services.autenticacao import exigir_papeis
from app.services.evolution_service import EvolutionService



def _exigir_conta_institucional_whatsapp(
    _usuario=Depends(exigir_papeis("ADMIN_GERAL", "INSTITUCIONAL_WHATSAPP")),
    db: Session = Depends(get_db),
) -> DatabaseRepository:
    """Exige JWT de conta institucional do WhatsApp e retorna seu repositório."""
    return DatabaseRepository(db)


class EnvioManualWhatsApp(BaseModel):
    numero: str = Field(..., json_schema_extra={"example": "5511999999999"}, description="Número de telefone com DDI e DDD")
    texto: str = Field(..., json_schema_extra={"example": "Olá! Teste de integração MediFlow."}, description="Conteúdo da mensagem")


async def enviar_mensagem_teste(
    payload: EnvioManualWhatsApp,
    _repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
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

    @field_validator("url")
    @classmethod
    def validar_url_sem_credenciais(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        partes = urlsplit(valor.strip())
        if (
            partes.scheme not in {"http", "https"}
            or not partes.hostname
            or partes.username
            or partes.password
            or partes.query
            or partes.fragment
        ):
            raise ValueError("Informe uma URL HTTP(S) sem credenciais, query ou fragmento.")
        return valor.strip()


async def consultar_status_instancia(
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Consulta o estado de conexão e saúde da instância única do WhatsApp e sincroniza no banco."""
    evolution = EvolutionService()
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


async def conectar_whatsapp_qrcode(
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Gera ou obtém o QR Code para conectar a instância única do WhatsApp no frontend."""
    logger.info("Solicitação de geração de QR Code recebida.", extra={"path": "/webhook/evolution/conectar"})
    evolution = EvolutionService()
    # Verifica se já está conectado
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

    # Se não existe, cria
    if estado.get("estado") == "not_found":
        await evolution.criar_instancia()

    # Obtém o QR Code
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


async def auto_configurar_webhook(
    payload: ConfigurarWebhookRequest = None,
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Configura o webhook na Evolution API apontando para o backend e persiste a URL no banco."""
    evolution = EvolutionService()
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


async def desconectar_whatsapp(
    repo: DatabaseRepository = Depends(_exigir_conta_institucional_whatsapp),
):
    """Desconecta a sessão atual do WhatsApp e atualiza o estado no banco."""
    evolution = EvolutionService()
    resultado = await evolution.desconectar()
    if resultado.get("sucesso"):
        repo.atualizar_estado_instancia_whatsapp(
            conectado=False,
            status_conexao="close",
        )
    return resultado
