import datetime
import json
import logging
import re
import sys
from typing import Any, Dict
from app.config.settings import settings

# Expressões regulares para detecção de dados pessoais sensíveis (LGPD)
PADRAO_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
PADRAO_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def sanitizar_dados_lgpd(texto: str) -> str:
    """Aplica mascaramento de dados identificáveis em conformidade com a LGPD.

    Em ambiente de desenvolvimento ('development'), preserva o log para fins de depuração.
    Em produção ou homologação, ofusca CPFs e e-mails sensíveis.
    """
    if not isinstance(texto, str):
        texto = str(texto)

    # Não mascara em ambiente local de desenvolvimento
    if settings.APP_ENV.lower() == "development":
        return texto

    # Mascaramento em produção
    texto = PADRAO_CPF.sub("***.***.***-**", texto)
    texto = PADRAO_EMAIL.sub("***@***.***", texto)
    return texto


class JSONLogFormatter(logging.Formatter):
    """Formatador de log estruturado em JSON para saída padrão (stdout / Docker / OCI)."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitizar_dados_lgpd(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": settings.APP_ENV,
        }

        # Inclui metadados extras se passados via extra={...}
        if hasattr(record, "documento_id"):
            log_payload["documento_id"] = getattr(record, "documento_id")
        if hasattr(record, "status_code"):
            log_payload["status_code"] = getattr(record, "status_code")
        if hasattr(record, "path"):
            log_payload["path"] = getattr(record, "path")

        # Se houver exceção, serializa traceback
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, ensure_ascii=False)


def setup_logging():
    """Configura o sistema global de logs estruturados em JSON."""
    root_logger = logging.getLogger()

    # Define nível
    nivel = logging.DEBUG if settings.APP_DEBUG else logging.INFO
    root_logger.setLevel(nivel)

    # Limpa handlers anteriores para evitar duplicações
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Cria handler com saída para sys.stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter())
    root_logger.addHandler(handler)

    # Evita ruído excessivo de bibliotecas de terceiros
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("mediflow")
