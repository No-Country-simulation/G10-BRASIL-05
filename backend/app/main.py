from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.config.logger import setup_logging, logger
from app.config.error_handlers import register_error_handlers
from app.controllers.triagem import router as triagem_router
from app.repositories.database import init_db

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
    yield
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
