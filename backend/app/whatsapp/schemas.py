"""Esquemas Pydantic para validação e serialização de dados do WhatsApp (Evolution API)."""

from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit
from pydantic import BaseModel, Field, field_validator


class EnvioManualWhatsAppRequest(BaseModel):
    numero: str = Field(
        ...,
        description="Número de telefone com DDI e DDD (ex: 5511999999999)",
        json_schema_extra={"example": "5511999999999"},
    )
    texto: str = Field(
        ...,
        description="Conteúdo da mensagem de texto",
        json_schema_extra={"example": "Olá! Teste de integração MediFlow."},
    )


# Alias para retrocompatibilidade
EnvioManualWhatsApp = EnvioManualWhatsAppRequest


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


class InstanciaStatusResponse(BaseModel):
    instancia: str = Field(..., description="Nome da instância no Evolution API")
    api_url: Optional[str] = Field(None, description="URL base da Evolution API")
    gerenciado_por_email: Optional[str] = Field(None, description="E-mail institucional gestor")
    modo_operacao: Optional[str] = Field(None, description="Modo operacional (ex: AGENTE_AUTONOMO_UNICO)")
    conectado: bool = Field(False, description="Status booleano de conexão ativa")
    estado: str = Field("close", description="Estado bruto retornado pela Evolution (open, close, connecting, etc.)")
    numero_conectado: Optional[str] = Field(None, description="Número de telefone associado à sessão conectada")

    model_config = {"extra": "allow"}


class QRCodeResponse(BaseModel):
    conectado: bool = Field(..., description="Indica se a instância já está conectada")
    instancia: str = Field(..., description="Nome da instância")
    gerenciado_por_email: Optional[str] = Field(None, description="E-mail gestor")
    mensagem: Optional[str] = Field(None, description="Mensagem descritiva")
    sucesso: Optional[bool] = Field(None, description="Sucesso na requisição à Evolution API")
    qrcode: Optional[str] = Field(None, description="String ou base64 do QR Code para exibição")
    base64: Optional[str] = Field(None, description="Payload base64 do QR Code se fornecido")
    code: Optional[str] = Field(None, description="Código de pareamento alfanumérico se aplicável")
    pairing_code: Optional[str] = Field(None, description="Pairing code alternativo")
    count: Optional[int] = Field(None, description="Contagem de tentativas do QR Code")

    model_config = {"extra": "allow"}


class WebhookKeyData(BaseModel):
    remoteJid: Optional[str] = None
    fromMe: Optional[bool] = None
    id: Optional[str] = None
    participant: Optional[str] = None

    model_config = {"extra": "allow"}


class WebhookMessageData(BaseModel):
    conversation: Optional[str] = None
    imageMessage: Optional[Dict[str, Any]] = None
    documentMessage: Optional[Dict[str, Any]] = None
    documentWithCaptionMessage: Optional[Dict[str, Any]] = None
    extendedTextMessage: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class WebhookEventPayload(BaseModel):
    event: Optional[str] = Field(None, description="Tipo do evento (ex: messages.upsert, connection.update)")
    instance: Optional[str] = Field(None, description="Nome da instância Evolution")
    data: Optional[Dict[str, Any]] = Field(None, description="Dados do evento enviado pela Evolution API")
    destination: Optional[str] = None
    date_time: Optional[str] = None
    sender: Optional[str] = None
    apikey: Optional[str] = None

    model_config = {"extra": "allow"}


class WebhookResponse(BaseModel):
    status: str
    message_id: Optional[str] = None
    numero: Optional[str] = None
    documento_id: Optional[str] = None
    event: Optional[str] = None
    motivo: Optional[str] = None
    protocolo_consultado: Optional[str] = None

    model_config = {"extra": "allow"}
