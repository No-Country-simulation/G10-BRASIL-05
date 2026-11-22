"""Repositório de persistência para o ecossistema WhatsApp (Evolution API)."""

from typing import Optional
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.whatsapp.models import (
    ContatoWhatsappModel,
    InstanciaWhatsappModel,
    DocumentoOrigemWhatsappModel,
)

EMAIL_INSTITUCIONAL_WHATSAPP = "mediflow@equipe.com.br"


class WhatsappRepository:
    """Persiste e gerencia o estado da instância e vínculos do WhatsApp."""

    def __init__(self, db: Session):
        self.db = db

    def garantir_instancia_whatsapp(self) -> InstanciaWhatsappModel:
        """Garante somente o registro da instância, nunca uma conta ou senha."""
        nome_instancia = settings.EVOLUTION_INSTANCE_NAME or "mediflow"
        instancia = (
            self.db.query(InstanciaWhatsappModel)
            .filter(InstanciaWhatsappModel.instance_name == nome_instancia)
            .first()
        )
        if not instancia:
            instancia = InstanciaWhatsappModel(
                instance_name=nome_instancia,
                status_conexao="close",
                conectado=False,
                gerenciado_por_email=EMAIL_INSTITUCIONAL_WHATSAPP,
                modo_operacao="AGENTE_AUTONOMO_UNICO",
            )
            self.db.add(instancia)
            self.db.flush()

        self.db.commit()
        return instancia

    def obter_ou_criar_instancia_whatsapp(
        self,
        instance_name: Optional[str] = None,
    ) -> InstanciaWhatsappModel:
        nome = (instance_name or settings.EVOLUTION_INSTANCE_NAME or "mediflow").strip()
        instancia = (
            self.db.query(InstanciaWhatsappModel)
            .filter(InstanciaWhatsappModel.instance_name == nome)
            .first()
        )
        if not instancia:
            instancia = InstanciaWhatsappModel(
                instance_name=nome,
                status_conexao="close",
                conectado=False,
                gerenciado_por_email=EMAIL_INSTITUCIONAL_WHATSAPP,
                modo_operacao="AGENTE_AUTONOMO_UNICO",
            )
            self.db.add(instancia)
            self.db.commit()
            self.db.refresh(instancia)
        return instancia

    def atualizar_estado_instancia_whatsapp(
        self,
        conectado: bool,
        status_conexao: str,
        webhook_url: Optional[str] = None,
        numero_conectado: Optional[str] = None,
        instance_name: Optional[str] = None,
    ) -> InstanciaWhatsappModel:
        """Sincroniza no banco de dados o estado da instância única do agente WhatsApp."""
        instancia = self.obter_ou_criar_instancia_whatsapp(instance_name)
        instancia.conectado = bool(conectado)
        instancia.status_conexao = (status_conexao or "close").strip()
        if webhook_url is not None:
            instancia.webhook_url = webhook_url
        if numero_conectado is not None:
            instancia.numero_conectado = numero_conectado
        self.db.commit()
        self.db.refresh(instancia)
        return instancia

    def obter_ou_criar_contato(
        self,
        numero: str,
        nome: Optional[str] = None,
    ) -> ContatoWhatsappModel:
        """Busca ou cadastra um contato WhatsApp pelo número."""
        numero_limpo = numero.strip()
        contato = (
            self.db.query(ContatoWhatsappModel)
            .filter(ContatoWhatsappModel.numero == numero_limpo)
            .first()
        )
        if not contato:
            contato = ContatoWhatsappModel(numero=numero_limpo, nome=nome)
            self.db.add(contato)
            self.db.commit()
            self.db.refresh(contato)
        elif nome and contato.nome != nome:
            contato.nome = nome
            self.db.commit()
            self.db.refresh(contato)
        return contato

    def vincular_documento_origem(
        self,
        documento_id: int,
        contato_id: int,
        instancia_id: int,
        message_id: str,
    ) -> DocumentoOrigemWhatsappModel:
        """Registra a rastreabilidade do documento originado via WhatsApp."""
        origem = (
            self.db.query(DocumentoOrigemWhatsappModel)
            .filter(DocumentoOrigemWhatsappModel.documento_id == documento_id)
            .first()
        )
        if not origem:
            origem = DocumentoOrigemWhatsappModel(
                documento_id=documento_id,
                contato_id=contato_id,
                instancia_id=instancia_id,
                message_id=message_id,
            )
            self.db.add(origem)
            self.db.commit()
            self.db.refresh(origem)
        return origem


# Alias para retrocompatibilidade
InstanciasWhatsAppRepository = WhatsappRepository
