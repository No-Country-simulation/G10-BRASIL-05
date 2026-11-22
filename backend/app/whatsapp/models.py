"""Modelos SQLAlchemy para o ecossistema WhatsApp (Evolution API)."""

from app.models.triagem import (
    Base,
    ContatoWhatsAppModel,
    InstanciaWhatsAppModel,
    DocumentoOrigemWhatsAppModel,
)

# Aliases para conformidade com a convenção de nomenclatura ContatoWhatsappModel / ContatoWhatsAppModel
ContatoWhatsappModel = ContatoWhatsAppModel
InstanciaWhatsappModel = InstanciaWhatsAppModel
DocumentoOrigemWhatsappModel = DocumentoOrigemWhatsAppModel

__all__ = [
    "Base",
    "ContatoWhatsappModel",
    "InstanciaWhatsappModel",
    "DocumentoOrigemWhatsappModel",
    "ContatoWhatsAppModel",
    "InstanciaWhatsAppModel",
    "DocumentoOrigemWhatsAppModel",
]
