"""Conexão com o banco, migrações e inicialização de dados."""

from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.config.settings import settings
from app.models.triagem import Base
from app.repositories.database_repository import DatabaseRepository


if "sqlite" in settings.DATABASE_URL.lower():
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Aplica migrations antes das seeds; SQLite permanece conveniente em dev/testes."""
    from app.seeders import executar_seeders

    if "sqlite" in settings.DATABASE_URL.lower():
        Base.metadata.create_all(bind=engine)
    else:
        diretorio_backend = Path(__file__).resolve().parents[2]
        configuracao = Config(str(diretorio_backend / "alembic.ini"))
        configuracao.set_main_option("script_location", str(diretorio_backend / "migrations"))
        command.upgrade(configuracao, "head")

    with SessionLocal() as db:
        executar_seeders(db)


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI para fornecer e fechar uma sessão."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
