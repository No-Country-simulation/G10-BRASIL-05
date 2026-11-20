"""Configuração isolada para testes locais sem dependência de containers."""

import os
import secrets
import asyncio

import pytest

try:
    import uvloop
except ImportError:
    uvloop = None

if uvloop is not None:
    # O loop asyncio padrão desta imagem não acorda quando um worker notifica
    # uma Future via call_soon_threadsafe; TestClient fica bloqueado. Uvicorn
    # já usa uvloop no Linux quando instalado com o extra [standard].
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# Definir antes dos imports da aplicação força o engine de teste a usar SQLite
# em memória, sem tocar no PostgreSQL configurado no .env do desenvolvedor.
os.environ["APP_ENV"] = "local"
os.environ["DATABASE_URL"] = "sqlite://"
# Testes usam storage local e nunca devem enviar fixtures para um bucket real.
os.environ["OCI_AUTH_MODE"] = "local_only"
os.environ["JWT_SECRET_KEY"] = "unit-test-only-secret-key-not-for-deployment"
os.environ["EVOLUTION_WEBHOOK_SECRET"] = "test-only-webhook-secret-not-for-deployment"

SENHA_WPP_TESTE = secrets.token_urlsafe(24)
SENHA_DIRETOR_TESTE = secrets.token_urlsafe(24)
SENHA_ADMIN_INICIAL_TESTE = secrets.token_urlsafe(24)
os.environ["ADMIN_BOOTSTRAP_EMAIL"] = "admin.bootstrap@example.org"
os.environ["ADMIN_BOOTSTRAP_PASSWORD"] = SENHA_ADMIN_INICIAL_TESTE
os.environ["ADMIN_BOOTSTRAP_NAME"] = "Administrador de Teste"


@pytest.fixture(autouse=True)
def autenticar_clientes_de_teste(request):
    """Fornece credenciais efêmeras aos testes legados que já exercitam rotas privadas."""
    from fastapi.testclient import TestClient

    from app.config.settings import settings
    from app.models.triagem import UsuarioSistemaModel
    from app.repositories.database import SessionLocal, init_db
    from app.services.autenticacao import emitir_token, gerar_hash_senha

    settings.JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
    settings.EVOLUTION_WEBHOOK_SECRET = os.environ["EVOLUTION_WEBHOOK_SECRET"]
    init_db()
    with SessionLocal() as db:
        diretor = db.query(UsuarioSistemaModel).filter_by(email="teste.diretor@example.org").first()
        if not diretor:
            diretor = UsuarioSistemaModel(
                email="teste.diretor@example.org",
                nome="Diretor de Teste",
                senha_hash=gerar_hash_senha(SENHA_DIRETOR_TESTE),
                papel="DIRETOR",
                ativo=True,
                pode_gerenciar_whatsapp=False,
            )
            db.add(diretor)
        else:
            diretor.senha_hash = gerar_hash_senha(SENHA_DIRETOR_TESTE)
            diretor.papel = "DIRETOR"
            diretor.ativo = True
        institucional = db.query(UsuarioSistemaModel).filter_by(email="mediflow@equipe.com.br").first()
        if not institucional:
            institucional = UsuarioSistemaModel(
                email="mediflow@equipe.com.br",
                nome="Conta WhatsApp de Teste",
                senha_hash=gerar_hash_senha(SENHA_WPP_TESTE),
                papel="INSTITUCIONAL_WHATSAPP",
                ativo=True,
                pode_gerenciar_whatsapp=True,
            )
            db.add(institucional)
        else:
            institucional.senha_hash = gerar_hash_senha(SENHA_WPP_TESTE)
            institucional.papel = "INSTITUCIONAL_WHATSAPP"
            institucional.ativo = True
            institucional.pode_gerenciar_whatsapp = True
        db.commit()
        db.refresh(diretor)
        db.refresh(institucional)
        token_diretor = emitir_token(diretor)
        token_institucional = emitir_token(institucional)

    request.module.TEST_TOKEN_DIRETOR = token_diretor
    request.module.TEST_TOKEN_INSTITUCIONAL = token_institucional
    request.module.SENHA_WPP_TESTE = SENHA_WPP_TESTE
    request.module.SENHA_DIRETOR_TESTE = SENHA_DIRETOR_TESTE
    request.module.SENHA_ADMIN_INICIAL_TESTE = SENHA_ADMIN_INICIAL_TESTE
    for objeto in vars(request.module).values():
        if isinstance(objeto, TestClient):
            objeto.headers["Authorization"] = f"Bearer {token_diretor}"
    yield
