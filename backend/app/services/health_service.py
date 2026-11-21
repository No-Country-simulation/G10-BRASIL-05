"""Serviço de verificação de integridade e prontidão das dependências."""

from typing import Any, Dict, Tuple
from sqlalchemy import text

from app.config.logger import logger
from app.config.settings import settings
from app.repositories.database import engine


def checar_postgres() -> Tuple[bool, str]:
    """Testa conexão rápida com o banco relacional."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "conectado"
    except Exception as erro:
        logger.warning("Falha no healthcheck PostgreSQL: %s", erro)
        return False, str(erro)


def checar_redis() -> Tuple[bool, str]:
    """Testa conectividade com o Redis de fila e locks."""
    try:
        from app.services.triagem_queue import obter_redis_fila

        client = obter_redis_fila()
        if client.ping():
            return True, "conectado"
        return False, "sem resposta ao ping"
    except Exception as erro:
        logger.warning("Falha no healthcheck Redis: %s", erro)
        return False, str(erro)


def checar_mongodb() -> Tuple[bool, str]:
    """Testa conectividade com o MongoDB de auditoria."""
    try:
        import pymongo

        client = pymongo.MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
        )
        client.admin.command("ping")
        client.close()
        return True, "conectado"
    except Exception as erro:
        logger.warning("Falha no healthcheck MongoDB: %s", erro)
        return False, str(erro)


def verificar_prontidao_sistema() -> Dict[str, Any]:
    """Executa checagem de prontidão (readiness) em todos os bancos requeridos."""
    is_sqlite_teste = "sqlite" in settings.DATABASE_URL.lower()

    pg_ok, pg_msg = checar_postgres()
    redis_ok, redis_msg = checar_redis()
    mongo_ok, mongo_msg = checar_mongodb()

    # Em testes unitários locais com SQLite em memória, Redis e Mongo podem não estar ativos
    if is_sqlite_teste:
        pronto = pg_ok
    else:
        pronto = pg_ok and redis_ok and mongo_ok

    return {
        "status": "ready" if pronto else "unready",
        "ambiente": settings.APP_ENV,
        "dependencias": {
            "postgres": {"status": "ok" if pg_ok else "erro", "detalhe": pg_msg},
            "redis": {"status": "ok" if redis_ok else "erro", "detalhe": redis_msg},
            "mongodb": {"status": "ok" if mongo_ok else "erro", "detalhe": mongo_msg},
        },
    }
