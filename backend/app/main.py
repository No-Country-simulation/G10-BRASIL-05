from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="API de Triagem, Extração e Roteamento de Documentos Clínicos - MediFlow",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração de CORS para permitir requisições do frontend Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
