from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.controllers.triagem import router as triagem_router
from app.repositories.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa tabelas se o banco estiver acessível
    try:
        init_db()
    except Exception as e:
        print(f"[Database Warning] Não foi possível conectar ao banco de dados no startup: {e}")
    yield


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
