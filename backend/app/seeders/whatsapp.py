from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.triagem import InstanciaWhatsAppModel


def semear_instancia_whatsapp(db: Session) -> None:
    nome = settings.EVOLUTION_INSTANCE_NAME or "mediflow"
    existe = db.query(InstanciaWhatsAppModel).filter_by(instance_name=nome).first()
    if existe:
        return
    db.add(
        InstanciaWhatsAppModel(
            instance_name=nome,
            status_conexao="close",
            conectado=False,
            modo_operacao="AGENTE_AUTONOMO_UNICO",
        )
    )
