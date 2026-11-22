from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _CONFIG_DIR.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_PROJECT_ROOT / ".env"),
            str(_BACKEND_DIR / ".env"),
            str(_PROJECT_ROOT / "DOCUMENTOS" / ".env"),
            ".env",
            "../.env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicação
    APP_NAME: str
    APP_ENV: str
    APP_DEBUG: bool
    APP_HOST: str
    APP_PORT: int
    API_V1_PREFIX: str

    # CORS
    CORS_ORIGINS: list[str]

    # Banco de Dados (PostgreSQL)
    DATABASE_URL: str

    # Autenticação: chave aleatória de pelo menos 32 caracteres fornecida via ambiente.
    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Identidade do administrador inicial e senha temporária compartilhada por seeds.
    ADMIN_BOOTSTRAP_EMAIL: str
    ADMIN_BOOTSTRAP_PASSWORD: str
    ADMIN_BOOTSTRAP_NAME: str

    # Cache & Fila de Auditoria (Redis)
    REDIS_URL: str

    # Banco Não-Relacional de Auditoria (MongoDB)
    MONGODB_URL: str
    MONGODB_DATABASE: str

    # LLM fixo: OpenRouter Free Models Router
    OPENROUTER_API_KEY: str
    OPENROUTER_API_KEY_2: str = ""
    OPENROUTER_API_KEY_3: str = ""
    OPENROUTER_API_KEY_4: str = ""
    OPENROUTER_MODEL: str
    CONFIDENCE_THRESHOLD: float

    @property
    def openrouter_api_keys(self) -> list[str]:
        chaves: list[str] = []
        if self.OPENROUTER_API_KEY and self.OPENROUTER_API_KEY.strip():
            chaves.append(self.OPENROUTER_API_KEY.strip())
        if self.OPENROUTER_API_KEY_2 and self.OPENROUTER_API_KEY_2.strip():
            chaves.append(self.OPENROUTER_API_KEY_2.strip())
        if self.OPENROUTER_API_KEY_3 and self.OPENROUTER_API_KEY_3.strip():
            chaves.append(self.OPENROUTER_API_KEY_3.strip())
        if self.OPENROUTER_API_KEY_4 and self.OPENROUTER_API_KEY_4.strip():
            chaves.append(self.OPENROUTER_API_KEY_4.strip())
        return chaves

    # OCI Object Storage Always Free
    OCI_AUTH_MODE: str
    OCI_USER_OCID: str
    OCI_TENANCY_OCID: str
    OCI_FINGERPRINT: str
    OCI_KEY_FILE: str
    OCI_REGION: str
    OCI_NAMESPACE: str
    OCI_BUCKET_NAME: str

    # WhatsApp & Evolution API
    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str
    EVOLUTION_INSTANCE_NAME: str
    EVOLUTION_WEBHOOK_SECRET: str
    EVOLUTION_WEBHOOK_URL: str


settings = Settings()
