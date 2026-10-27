import datetime
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.logger import logger


def montar_envelope_erro(
    codigo: str,
    mensagem: str,
    path: str,
    detalhes: List[Any] = None,
) -> Dict[str, Any]:
    """Cria a estrutura de resposta JSON padrão para todas as falhas da API."""
    return {
        "erro": {
            "codigo": codigo,
            "mensagem": mensagem,
            "detalhes": detalhes or [],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "path": path,
        }
    }


def obter_codigo_http(status_code: int) -> str:
    """Mapeia status code para código de erro padronizado legível."""
    mapa_codigos = {
        status.HTTP_400_BAD_REQUEST: "REQUISICAO_INVALIDA",
        status.HTTP_401_UNAUTHORIZED: "NAO_AUTORIZADO",
        status.HTTP_403_FORBIDDEN: "ACESSO_NEGADO",
        status.HTTP_404_NOT_FOUND: "RECURSO_NAO_ENCONTRADO",
        status.HTTP_409_CONFLICT: "CONFLITO_DADOS",
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "TAMANHO_ARQUIVO_EXCEDIDO",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "ENTIDADE_NAO_PROCESSAVEL",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "ERRO_INTERNO_SERVIDOR",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICO_INDISPONIVEL",
    }
    return mapa_codigos.get(status_code, f"ERRO_HTTP_{status_code}")


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler global para falhas de validação de schemas Pydantic (HTTP 422)."""
    detalhes_erros = []
    for err in exc.errors():
        campo = " -> ".join(str(loc) for loc in err.get("loc", []))
        detalhes_erros.append({
            "campo": campo,
            "motivo": err.get("msg", "Valor inválido"),
            "tipo": err.get("type", "validation_error"),
        })

    logger.warning(
        f"Falha de validação em {request.url.path}: {len(detalhes_erros)} campos com erro.",
        extra={"path": request.url.path, "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY},
    )

    payload = montar_envelope_erro(
        codigo="ERRO_VALIDACAO_PAYLOAD",
        mensagem="Os dados enviados na requisição contêm campos inválidos ou obrigatórios ausentes.",
        path=request.url.path,
        detalhes=detalhes_erros,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler global para exceções HTTP intencionais (4xx / 5xx) disparadas pela aplicação."""
    codigo = obter_codigo_http(exc.status_code)
    mensagem = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    logger.warning(
        f"HTTP {exc.status_code} em {request.url.path}: {mensagem}",
        extra={"path": request.url.path, "status_code": exc.status_code},
    )

    payload = montar_envelope_erro(
        codigo=codigo,
        mensagem=mensagem,
        path=request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content=payload)


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handler global para falhas de banco de dados (mascara queries e SQL internos por segurança)."""
    logger.error(
        f"Falha crítica no banco de dados durante requisição para {request.url.path}",
        exc_info=exc,
        extra={"path": request.url.path, "status_code": status.HTTP_503_SERVICE_UNAVAILABLE},
    )

    payload = montar_envelope_erro(
        codigo="ERRO_BANCO_DADOS",
        mensagem="O serviço de banco de dados está temporariamente instável ou indisponível. Tente novamente em instantes.",
        path=request.url.path,
    )
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler catch-all para qualquer exceção não tratada (HTTP 500). Evita vazamento de stack trace."""
    logger.critical(
        f"Exceção não tratada interceptada em {request.url.path}: {str(exc)}",
        exc_info=exc,
        extra={"path": request.url.path, "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR},
    )

    payload = montar_envelope_erro(
        codigo="ERRO_INTERNO_SERVIDOR",
        mensagem="Ocorreu um erro interno inesperado no servidor. O evento foi registrado para análise técnica.",
        path=request.url.path,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


def register_error_handlers(app: FastAPI):
    """Registra todos os handlers globais de erro na instância do FastAPI."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
