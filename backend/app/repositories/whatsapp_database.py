from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.triagem import InstanciaWhatsAppModel

EMAIL_INSTITUCIONAL_WHATSAPP = "mediflow@equipe.com.br"

class InstanciasWhatsAppRepository:
    """Persiste o estado da instância institucional do WhatsApp."""

    def __init__(self, db: Session):
        self.db = db

    def garantir_instancia_whatsapp(self) -> InstanciaWhatsAppModel:
        """Garante somente o registro da instância, nunca uma conta ou senha."""
        nome_instancia = settings.EVOLUTION_INSTANCE_NAME or "mediflow"
        instancia = (
            self.db.query(InstanciaWhatsAppModel)
            .filter(InstanciaWhatsAppModel.instance_name == nome_instancia)
            .first()
        )
        if not instancia:
            instancia = InstanciaWhatsAppModel(
                instance_name=nome_instancia,
                status_conexao="close",
                conectado=False,
                modo_operacao="AGENTE_AUTONOMO_UNICO",
            )
            self.db.add(instancia)
            self.db.flush()

        self.db.commit()
        return instancia

    def obter_ou_criar_instancia_whatsapp(
        self,
        instance_name: Optional[str] = None,
    ) -> InstanciaWhatsAppModel:
        nome = (instance_name or settings.EVOLUTION_INSTANCE_NAME or "mediflow").strip()
        instancia = (
            self.db.query(InstanciaWhatsAppModel)
            .filter(InstanciaWhatsAppModel.instance_name == nome)
            .first()
        )
        if not instancia:
            instancia = InstanciaWhatsAppModel(
                instance_name=nome,
                status_conexao="close",
                conectado=False,
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
    ) -> InstanciaWhatsAppModel:
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
