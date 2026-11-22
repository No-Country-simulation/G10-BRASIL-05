"""Modelo de usuários do sistema."""

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, func, text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class UsuarioSistemaModel(Base):
    __tablename__ = "usuarios_sistema"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(150), nullable=False, unique=True)
    nome = Column(String(150), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    papel = Column(String(50), nullable=False, default="SOMENTE_LEITURA", server_default="SOMENTE_LEITURA")
    # Metadados do perfil de acesso preservam os valores das seeds; não substituem
    # os registros normalizados em medicos/enfermeiros.
    registro = Column(String(80))
    especialidade = Column(String(150))
    trocar_senha_obrigatorio = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    medico_id = Column(Integer, ForeignKey("medicos.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    enfermeiro_id = Column(Integer, ForeignKey("enfermeiros.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    pode_gerenciar_whatsapp = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    ativo = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    medico = relationship("MedicoModel")
    enfermeiro = relationship("EnfermeiroModel")


__all__ = ["UsuarioSistemaModel"]
