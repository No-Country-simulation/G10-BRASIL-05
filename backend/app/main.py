from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.config.logger import setup_logging, logger
from app.config.error_handlers import register_error_handlers
from app.api.router import api_router
from app.repositories.database import init_db
from app.agent.graph import configurar_checkpointer
from app.seeders.errors import BootstrapAdminError

# Inicializa sistema de logging estruturado JSON
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} em ambiente [{settings.APP_ENV}]...")
    ambiente_producao = settings.APP_ENV.lower() in {"production", "prod"}
    if ambiente_producao and len(settings.JWT_SECRET_KEY) < 32:
        raise RuntimeError("Produção exige JWT_SECRET_KEY com pelo menos 32 caracteres.")
    init_db()
    logger.info("Conexão e inicialização com o banco de dados concluídas.")

    checkpoint_context = None
    if "sqlite" in settings.DATABASE_URL.lower():
        raise RuntimeError("O checkpointer persistente exige uma URL PostgreSQL.")
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        checkpoint_context = PostgresSaver.from_conn_string(settings.DATABASE_URL)
        checkpointer = checkpoint_context.__enter__()
        checkpointer.setup()
        configurar_checkpointer(checkpointer)
        logger.info("Checkpoint durável do LangGraph conectado ao PostgreSQL.")
    except Exception as erro:
        if checkpoint_context is not None:
            checkpoint_context.__exit__(type(erro), erro, erro.__traceback__)
        raise RuntimeError("Checkpoint PostgreSQL do LangGraph indisponível; inicialização cancelada.") from erro
    yield
    if checkpoint_context is not None:
        checkpoint_context.__exit__(None, None, None)
    logger.info(f"Encerrando {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="API de Triagem, Extração e Roteamento de Documentos Clínicos - MediFlow",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configuração de CORS para permitir requisições do frontend Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Handlers Globais de Erro (RFC / JSON Envelope)
register_error_handlers(app)

app.include_router(api_router)
