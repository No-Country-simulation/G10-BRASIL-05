"""Pacote autônomo para o ecossistema WhatsApp (Evolution API)."""

from app.whatsapp.controller import router
from app.whatsapp.models import (
    ContatoWhatsAppModel,
    ContatoWhatsappModel,
    DocumentoOrigemWhatsAppModel,
    DocumentoOrigemWhatsappModel,
    InstanciaWhatsAppModel,
    InstanciaWhatsappModel,
)
from app.whatsapp.repository import InstanciasWhatsAppRepository, WhatsappRepository
from app.whatsapp.service import EvolutionService, WhatsappEvolutionService
from app.whatsapp.worker import (
    processar_triagem_whatsapp,
    worker_processar_triagem_whatsapp,
)

__all__ = [
    "router",
    "WhatsappEvolutionService",
    "EvolutionService",
    "WhatsappRepository",
    "InstanciasWhatsAppRepository",
    "ContatoWhatsappModel",
    "ContatoWhatsAppModel",
    "InstanciaWhatsappModel",
    "InstanciaWhatsAppModel",
    "DocumentoOrigemWhatsappModel",
    "DocumentoOrigemWhatsAppModel",
    "worker_processar_triagem_whatsapp",
    "processar_triagem_whatsapp",
]
