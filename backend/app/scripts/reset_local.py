"""Reset explícito das bases locais do MediFlow (nunca Evolution/produção)."""
import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from pymongo import MongoClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config.settings import settings
from app.repositories.database import SessionLocal
from app.repositories.nosql_auditoria import MongoAuditoriaRepository
from app.seeders.execucao import executar_seeders


HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1", "postgres", "mongodb"}
NOMES_POSTGRES_PERMITIDOS = {"mediflow_db", "mediflow_local_test"}
NOMES_MONGO_PERMITIDOS = {"mediflow_auditoria", "mediflow_auditoria_local_test"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="executa o reset; sem isso só mostra o alvo")
    parser.add_argument("--confirm-postgres", default="")
    parser.add_argument("--confirm-mongo", default="")
    args = parser.parse_args()

    pg = make_url(settings.DATABASE_URL)
    mongo = make_url(settings.MONGODB_URL)
    pg_name = pg.database or ""
    mongo_name = settings.MONGODB_DATABASE
    if settings.APP_ENV.lower() not in {"local", "development", "dev", "test", "testing"}:
        raise SystemExit("Reset bloqueado: APP_ENV precisa indicar ambiente local/dev/test.")
    if pg.host not in HOSTS_LOCAIS or pg_name not in NOMES_POSTGRES_PERMITIDOS:
        raise SystemExit("Reset bloqueado: o PostgreSQL não corresponde a uma base local MediFlow permitida.")
    if mongo.host not in HOSTS_LOCAIS or mongo_name not in NOMES_MONGO_PERMITIDOS:
        raise SystemExit("Reset bloqueado: o MongoDB não corresponde à base local de auditoria permitida.")

    print(f"PostgreSQL alvo: {pg.host}/{pg_name} (schema public)")
    print(f"MongoDB alvo: {mongo.host}/{mongo_name} (auditoria MediFlow)")
    print("Evolution e Redis não serão acessados.")
    if not args.execute:
        print("Simulação. Para executar, informe --execute e confirme os dois nomes exatos.")
        return
    if args.confirm_postgres != pg_name or args.confirm_mongo != mongo_name:
        raise SystemExit("Reset bloqueado: as confirmações precisam coincidir com os bancos exibidos.")
    if len(settings.ADMIN_BOOTSTRAP_PASSWORD) < 12:
        raise SystemExit("Reset bloqueado: configure ADMIN_BOOTSTRAP_PASSWORD com pelo menos 12 caracteres antes de reaplicar seeds.")

    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
        try:
            client.admin.command("ping")
        finally:
            client.close()

        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()

    client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
    try:
        client.drop_database(mongo_name)
    finally:
        client.close()
    mongo_repo = MongoAuditoriaRepository(criar_indices=True)
    mongo_repo.fechar()

    backend = Path(__file__).resolve().parents[2]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    command.upgrade(config, "head")
    with SessionLocal() as db:
        executar_seeders(db)
    print("Reset concluído: migrations e seeds aplicadas.")


if __name__ == "__main__":
    main()
