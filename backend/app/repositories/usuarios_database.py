from typing import Optional

from sqlalchemy.orm import Session

from app.models.triagem import UsuarioSistemaModel

class UsuariosDatabaseRepository:
    """Busca uma conta pelo email normalizado."""

    def __init__(self, db: Session):
        self.db = db

    def buscar_usuario_sistema_por_email(self, email: str) -> Optional[UsuarioSistemaModel]:
        email_normalizado = (email or "").strip().lower()
        return (
            self.db.query(UsuarioSistemaModel)
            .filter(UsuarioSistemaModel.email == email_normalizado)
            .first()
        )
