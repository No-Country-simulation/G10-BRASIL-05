from contextlib import asynccontextmanager
from fastapi import FastAPI
from langgraph.checkpoint.memory import InMemorySaver
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.config.logger import setup_logging, logger
from app.config.error_handlers import register_error_handlers
from app.controllers.triagem import router as triagem_router
from app.controllers.triagem_upload import router as triagem_upload_router
from app.controllers.historico import router as historico_router
from app.controllers.auditoria import router as auditoria_router
from app.controllers.ecossistema import router as ecossistema_router
from app.controllers.evolution import router as evolution_router
from app.controllers.evolution_webhook import router as evolution_webhook_router
from app.repositories.database import init_db
from app.agent.graph import configurar_checkpointer

# Inicializa sistema de logging estruturado JSON
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} em ambiente [{settings.APP_ENV}]...")
    # Inicializa tabelas se o banco estiver acessível
    try:
        init_db()
        logger.info("Conexão e inicialização com o banco de dados concluídas.")
    except Exception as e:
        logger.warning(f"Não foi possível conectar ao banco de dados no startup: {e}")

    checkpoint_context = None
    ambiente_producao = settings.APP_ENV.lower() in {"production", "prod"}
    if "sqlite" in settings.DATABASE_URL.lower():
        if ambiente_producao:
            raise RuntimeError("Produção exige PostgreSQL para persistência durável do checkpoint.")
        configurar_checkpointer(InMemorySaver())
        logger.info("Testes/ambiente local com SQLite usam checkpoint em memória.")
    else:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            checkpoint_context = PostgresSaver.from_conn_string(settings.DATABASE_URL)
            checkpointer = checkpoint_context.__enter__()
            checkpointer.setup()
            configurar_checkpointer(checkpointer)
            logger.info("Checkpoint durável do LangGraph conectado ao PostgreSQL.")
        except Exception as e:
            if checkpoint_context is not None:
                checkpoint_context.__exit__(type(e), e, e.__traceback__)
                checkpoint_context = None
            if ambiente_producao:
                raise RuntimeError("Checkpoint PostgreSQL do LangGraph indisponível em produção.") from e
            configurar_checkpointer(InMemorySaver())
            logger.warning(
                "Checkpoint PostgreSQL indisponível; usando memória apenas neste ambiente. "
                "Revisões pendentes não sobrevivem a reinicializações."
            )
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

# Registro de Routers
app.include_router(triagem_router, prefix=settings.API_V1_PREFIX)
app.include_router(triagem_router)  # Suporte direto a /triagem sem prefixo para compatibilidade
app.include_router(triagem_upload_router, prefix=settings.API_V1_PREFIX)
app.include_router(triagem_upload_router)
app.include_router(historico_router, prefix=settings.API_V1_PREFIX)
app.include_router(historico_router)
app.include_router(auditoria_router, prefix=settings.API_V1_PREFIX)
app.include_router(auditoria_router)
app.include_router(ecossistema_router, prefix=settings.API_V1_PREFIX)
app.include_router(ecossistema_router)  # Suporte direto a /pacientes, /medicos, /hospitais
app.include_router(evolution_router, prefix=settings.API_V1_PREFIX)
app.include_router(evolution_router)  # Suporte direto a /webhook/evolution
app.include_router(evolution_webhook_router, prefix=settings.API_V1_PREFIX)
app.include_router(evolution_webhook_router)


@app.get("/", tags=["Root"])
def root():
    """Rota raiz com metadados básicos da API MediFlow."""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint de verificação de saúde da aplicação."""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "database": "configured",
    }
