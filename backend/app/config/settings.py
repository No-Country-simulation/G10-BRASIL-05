from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("DOCUMENTOS/.env", "backend/.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicação
    APP_NAME: str = "MediFlow API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]

    # Banco de Dados (PostgreSQL)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/mediflow_db"

    # Cache & Fila de Auditoria (Redis)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True

    # Banco Não-Relacional de Auditoria (MongoDB)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "mediflow_auditoria"
    MONGODB_ENABLED: bool = True

    # IA & LLM
    LLM_PROVIDER: str = "gemini"
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    CONFIDENCE_THRESHOLD: float = 0.75

    # OCI Object Storage Always Free
    OCI_USER_OCID: str = ""
    OCI_TENANCY_OCID: str = ""
    OCI_FINGERPRINT: str = ""
    OCI_KEY_FILE: str = ""
    OCI_REGION: str = "sa-saopaulo-1"
    OCI_NAMESPACE: str = ""
    OCI_BUCKET_NAME: str = "mediflow-documentos-clinicos"


settings = Settings()
