from sqlalchemy.orm import Session

from app.seeders.administrador import semear_administrador_inicial
from app.seeders.destinos import semear_destinos
from app.seeders.hospitais import semear_hospitais
from app.seeders.medicos import semear_medicos
from app.seeders.usuarios import semear_usuarios_configurados
from app.seeders.whatsapp import semear_instancia_whatsapp


def executar_seeders(db: Session) -> None:
    """Executa os seeds de cada domínio em uma transação."""
    try:
        semear_hospitais(db)
        semear_medicos(db)
        semear_destinos(db)
        semear_administrador_inicial(db)
        semear_usuarios_configurados(db)
        semear_instancia_whatsapp(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
