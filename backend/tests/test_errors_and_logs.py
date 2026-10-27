import json
import logging
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.config.settings import settings
from app.config.logger import JSONLogFormatter, sanitizar_dados_lgpd
from app.repositories.database import init_db

# Inicializa banco em memória para testes
init_db()

# Adiciona rota de teste para forçar exceções 500 e 503
test_router = APIRouter(prefix="/test-errors", tags=["Test Errors"])


@test_router.get("/database-error")
def trigger_db_error():
    raise SQLAlchemyError("SELECT * FROM secret_table WHERE password = '123'")


@test_router.get("/unhandled-error")
def trigger_unhandled_error():
    raise ZeroDivisionError("Divisão por zero inesperada no backend")


app.include_router(test_router)
client = TestClient(app, raise_server_exceptions=False)


def test_erro_validacao_payload_422():
    """Valida o envelope padronizado para erro de validação Pydantic (HTTP 422)."""
    response = client.post("/triagem", json={})
    assert response.status_code == 422
    dados = response.json()
    assert "erro" in dados
    erro = dados["erro"]
    assert erro["codigo"] == "ERRO_VALIDACAO_PAYLOAD"
    assert "campos inválidos" in erro["mensagem"]
    assert len(erro["detalhes"]) > 0
    assert "timestamp" in erro
    assert erro["path"] == "/triagem"


def test_erro_http_customizado_400():
    """Valida o envelope padronizado para HTTPException 400 (ex: formato de arquivo inválido)."""
    response = client.post(
        "/triagem/upload",
        files={"file": ("arquivo.exe", b"malware", "application/octet-stream")},
    )
    assert response.status_code == 400
    dados = response.json()
    assert "erro" in dados
    erro = dados["erro"]
    assert erro["codigo"] == "REQUISICAO_INVALIDA"
    assert "não suportado" in erro["mensagem"]
    assert erro["path"] == "/triagem/upload"


def test_erro_recurso_nao_encontrado_404():
    """Valida o envelope para rotas inexistentes (HTTP 404)."""
    response = client.get("/rota-totalmente-inexistente-123")
    assert response.status_code == 404
    dados = response.json()
    assert "erro" in dados
    erro = dados["erro"]
    assert erro["codigo"] == "RECURSO_NAO_ENCONTRADO"
    assert "path" in erro


def test_erro_banco_dados_503_sem_vazar_sql():
    """Valida que falhas de banco retornam 503 e não vazam queries SQL no payload."""
    response = client.get("/test-errors/database-error")
    assert response.status_code == 503
    dados = response.json()
    assert "erro" in dados
    erro = dados["erro"]
    assert erro["codigo"] == "ERRO_BANCO_DADOS"
    assert "secret_table" not in str(dados)  # Não vaza query SQL
    assert "password" not in str(dados)


def test_erro_interno_500_sem_vazar_stack_trace():
    """Valida que exceções não tratadas retornam 500 sem vazar stack trace no payload."""
    response = client.get("/test-errors/unhandled-error")
    assert response.status_code == 500
    dados = response.json()
    assert "erro" in dados
    erro = dados["erro"]
    assert erro["codigo"] == "ERRO_INTERNO_SERVIDOR"
    assert "ZeroDivisionError" not in str(dados)  # Protege o cliente de detalhes internos


def test_sanitizacao_lgpd_em_producao():
    """Valida mascaramento de CPF e e-mail sob APP_ENV=production."""
    original_env = settings.APP_ENV
    try:
        settings.APP_ENV = "production"
        texto_sensivel = "Paciente CPF 123.456.789-00 com email paciente@hospital.com compareceu."
        sanitizado = sanitizar_dados_lgpd(texto_sensivel)
        assert "123.456.789-00" not in sanitizado
        assert "***.***.***-**" in sanitizado
        assert "paciente@hospital.com" not in sanitizado
        assert "***@***.***" in sanitizado
    finally:
        settings.APP_ENV = original_env


def test_json_log_formatter_estrutura():
    """Valida que o formatador emite JSON válido com metadados estruturados."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="mediflow.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Teste de log estruturado",
        args=(),
        exc_info=None,
    )
    setattr(record, "documento_id", "DOC-LOG-999")
    setattr(record, "status_code", 200)

    json_str = formatter.format(record)
    log_dict = json.loads(json_str)

    assert log_dict["level"] == "INFO"
    assert log_dict["message"] == "Teste de log estruturado"
    assert log_dict["documento_id"] == "DOC-LOG-999"
    assert log_dict["status_code"] == 200
    assert "timestamp" in log_dict
