import asyncio
import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config.settings import settings
from app.controllers.evolution import ConfigurarWebhookRequest
from app.main import app
from app.models.triagem import UsuarioSistemaModel
from app.repositories.database import SessionLocal
from app.seeders.administrador import semear_administrador_inicial
from app.seeders.errors import BootstrapAdminError
from app.services.autenticacao import (
    emitir_token,
    gerar_hash_senha,
    validar_token,
    verificar_senha_hash,
)
from app.services.evolution_service import EvolutionService


client = TestClient(app)


def test_hash_usa_salt_aleatorio_e_verifica_senha():
    senha = secrets.token_urlsafe(18)
    hash_um = gerar_hash_senha(senha)
    hash_dois = gerar_hash_senha(senha)

    assert hash_um != hash_dois
    assert verificar_senha_hash(senha, hash_um)
    assert not verificar_senha_hash("senha-incorreta", hash_um)


def test_seed_admin_e_idempotente_e_usa_hash_de_senha(request):
    with SessionLocal() as db:
        admin = db.query(UsuarioSistemaModel).filter_by(papel="ADMIN_GERAL").one()
        hash_original = admin.senha_hash
        assert admin.email == "admin.bootstrap@example.org"
        assert verificar_senha_hash(request.module.SENHA_ADMIN_INICIAL_TESTE, hash_original)

        senha_configurada = settings.ADMIN_BOOTSTRAP_PASSWORD
        try:
            settings.ADMIN_BOOTSTRAP_PASSWORD = "outra-senha-que-nao-pode-substituir"
            semear_administrador_inicial(db)
            db.commit()
            db.refresh(admin)
        finally:
            settings.ADMIN_BOOTSTRAP_PASSWORD = senha_configurada

        assert admin.senha_hash == hash_original


def test_seed_cria_admin_ativo_se_o_admin_legado_esta_inativo():
    email_original = settings.ADMIN_BOOTSTRAP_EMAIL
    senha_original = settings.ADMIN_BOOTSTRAP_PASSWORD
    email_novo = f"bootstrap-novo-{secrets.token_hex(4)}@example.org"
    usuario_novo = None

    with SessionLocal() as db:
        admin_legado = db.query(UsuarioSistemaModel).filter_by(papel="ADMIN_GERAL").one()
        admin_legado.ativo = False
        db.flush()
        settings.ADMIN_BOOTSTRAP_EMAIL = email_novo
        settings.ADMIN_BOOTSTRAP_PASSWORD = secrets.token_urlsafe(24)
        try:
            semear_administrador_inicial(db)
            db.flush()
            usuario_novo = db.query(UsuarioSistemaModel).filter_by(email=email_novo).one()
            assert usuario_novo.ativo is True
            assert usuario_novo.papel == "ADMIN_GERAL"
        finally:
            if usuario_novo is not None:
                db.delete(usuario_novo)
            admin_legado.ativo = True
            db.commit()
            settings.ADMIN_BOOTSTRAP_EMAIL = email_original
            settings.ADMIN_BOOTSTRAP_PASSWORD = senha_original


def test_seed_informa_conflito_com_admin_inativo_sem_criar_duplicata():
    with SessionLocal() as db:
        admin = db.query(UsuarioSistemaModel).filter_by(papel="ADMIN_GERAL").one()
        email_original = settings.ADMIN_BOOTSTRAP_EMAIL
        senha_original = settings.ADMIN_BOOTSTRAP_PASSWORD
        admin.ativo = False
        db.flush()
        settings.ADMIN_BOOTSTRAP_EMAIL = admin.email
        settings.ADMIN_BOOTSTRAP_PASSWORD = secrets.token_urlsafe(24)
        try:
            with pytest.raises(BootstrapAdminError, match="existe, mas está inativa"):
                semear_administrador_inicial(db)
            assert db.query(UsuarioSistemaModel).filter_by(papel="ADMIN_GERAL").count() == 1
        finally:
            admin.ativo = True
            db.commit()
            settings.ADMIN_BOOTSTRAP_EMAIL = email_original
            settings.ADMIN_BOOTSTRAP_PASSWORD = senha_original


def test_seed_sem_admin_ativo_exige_credenciais_de_bootstrap():
    with SessionLocal() as db:
        admin = db.query(UsuarioSistemaModel).filter_by(papel="ADMIN_GERAL").one()
        email_original = settings.ADMIN_BOOTSTRAP_EMAIL
        senha_original = settings.ADMIN_BOOTSTRAP_PASSWORD
        admin.ativo = False
        db.flush()
        settings.ADMIN_BOOTSTRAP_EMAIL = ""
        settings.ADMIN_BOOTSTRAP_PASSWORD = ""
        try:
            with pytest.raises(BootstrapAdminError, match="ADMIN_BOOTSTRAP_EMAIL"):
                semear_administrador_inicial(db)
        finally:
            admin.ativo = True
            db.commit()
            settings.ADMIN_BOOTSTRAP_EMAIL = email_original
            settings.ADMIN_BOOTSTRAP_PASSWORD = senha_original


def test_startup_propaga_erro_de_bootstrap_e_mantem_tolerancia_a_falha_de_banco(monkeypatch):
    from app import main

    def falha_bootstrap():
        raise BootstrapAdminError("credenciais iniciais ausentes")

    monkeypatch.setattr(main, "init_db", falha_bootstrap)

    async def iniciar_api():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(BootstrapAdminError, match="credenciais iniciais"):
        asyncio.run(iniciar_api())

    def falha_transitoria_banco():
        raise ConnectionError("banco temporariamente indisponível")

    monkeypatch.setattr(main, "init_db", falha_transitoria_banco)
    monkeypatch.setattr(main, "configurar_checkpointer", lambda checkpointer: None)
    asyncio.run(iniciar_api())


def test_login_rejeita_senha_incorreta_e_conta_inativa(request):
    senha_incorreta = client.post(
        "/api/v1/auth/login",
        json={"email": "teste.diretor@example.org", "senha": "incorreta"},
    )
    assert senha_incorreta.status_code == 401

    with SessionLocal() as db:
        diretor = db.query(UsuarioSistemaModel).filter_by(email="teste.diretor@example.org").one()
        diretor.ativo = False
        db.commit()

    conta_inativa = client.post(
        "/api/v1/auth/login",
        json={"email": "teste.diretor@example.org", "senha": request.module.SENHA_DIRETOR_TESTE},
    )
    assert conta_inativa.status_code == 401


def test_login_emite_jwt_minimo_e_me_retorna_perfil_publico(request):
    resposta = client.post(
        "/api/v1/auth/login",
        json={"email": "TESTE.DIRETOR@example.org", "senha": request.module.SENHA_DIRETOR_TESTE},
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    claims = validar_token(dados["access_token"])
    assert set(claims) == {"sub", "role", "iss", "iat", "exp", "jti"}
    assert claims["role"] == "DIRETOR"
    assert "senha" not in dados and "senha_hash" not in dados["usuario"]
    assert "cpf" not in dados["usuario"] and "telefone" not in dados["usuario"]

    perfil = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {dados['access_token']}"},
    )
    assert perfil.status_code == 200
    assert perfil.json()["email"] == "teste.diretor@example.org"


def test_aliases_privados_negam_chamadas_sem_bearer():
    for rota in ("/auth/me", "/api/v1/auth/me", "/triagem/documentos", "/api/v1/triagem/documentos"):
        resposta = client.get(rota, headers={"Authorization": ""})
        assert resposta.status_code == 401, (rota, resposta.text)


def test_diretor_provisiona_conta_profissional_sem_expor_hash(request):
    email = f"enfermeiro-{secrets.token_hex(5)}@example.org"
    resposta = client.post(
        "/api/v1/auth/usuarios",
        headers={"Authorization": f"Bearer {request.module.TEST_TOKEN_DIRETOR}"},
        json={
            "nome": "Enfermeiro de Teste",
            "email": email,
            "senha": secrets.token_urlsafe(16),
            "nivel": "ENFERMEIRO",
        },
    )
    assert resposta.status_code == 201
    assert resposta.json()["email"] == email
    assert "senha_hash" not in resposta.json()


def test_medico_so_pode_provisionar_enfermeiros():
    email = f"medico-{secrets.token_hex(5)}@example.org"
    with SessionLocal() as db:
        medico = UsuarioSistemaModel(
            email=email,
            nome="Médico de Teste",
            senha_hash=gerar_hash_senha(secrets.token_urlsafe(16)),
            papel="MEDICO",
            ativo=True,
            pode_gerenciar_whatsapp=False,
        )
        db.add(medico)
        db.commit()
        db.refresh(medico)
        token_medico = emitir_token(medico)

    resposta = client.post(
        "/auth/usuarios",
        headers={"Authorization": f"Bearer {token_medico}"},
        json={
            "nome": "Diretor Indevido",
            "email": f"diretor-{secrets.token_hex(5)}@example.org",
            "senha": secrets.token_urlsafe(16),
            "nivel": "DIRETOR",
        },
    )
    assert resposta.status_code == 403


def test_conta_whatsapp_nao_acessa_triagem_e_acessa_gestao(request, monkeypatch):
    async def estado_falso(self):
        return {"conectado": False, "estado": "close"}

    monkeypatch.setattr(EvolutionService, "obter_estado_conexao", estado_falso)
    cabecalho = {"Authorization": f"Bearer {request.module.TEST_TOKEN_INSTITUCIONAL}"}

    assert client.get("/api/v1/triagem/documentos", headers=cabecalho).status_code == 403
    assert client.get("/api/v1/webhook/evolution/status-instancia", headers=cabecalho).status_code == 200


def test_webhook_exige_segredo_no_header_e_ignora_query():
    payload = {"event": "OTHER"}
    via_query = client.post(
        "/api/v1/webhook/evolution",
        params={"token": settings.EVOLUTION_WEBHOOK_SECRET},
        json=payload,
    )
    via_header = client.post(
        "/api/v1/webhook/evolution",
        headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
        json=payload,
    )

    assert via_query.status_code == 401
    assert via_header.status_code == 200


def test_url_de_webhook_rejeita_token_ou_credencial_na_query():
    with pytest.raises(ValidationError):
        ConfigurarWebhookRequest(url="https://user:password@host.example/hook?token=secret")
    assert ConfigurarWebhookRequest(url="https://backend.example/hook").url == "https://backend.example/hook"
