"""Chamadas HTTP do fluxo de autenticação."""
import httpx

from services.configuracao import obter_url_do_backend

ROTA_LOGIN_API = "/api/v1/auth/login"
ROTA_SESSAO_API = "/api/v1/auth/me"
ROTA_TROCAR_SENHA_API = "/api/v1/auth/password"


def autenticar(email: str, senha: str) -> httpx.Response:
    with httpx.Client(base_url=obter_url_do_backend(), timeout=8.0) as cliente:
        return cliente.post(ROTA_LOGIN_API, json={"email": email, "senha": senha})


def consultar_sessao(token: str) -> httpx.Response:
    with httpx.Client(base_url=obter_url_do_backend(), timeout=5.0) as cliente:
        return cliente.get(ROTA_SESSAO_API, headers={"Authorization": f"Bearer {token}"})


def alterar_senha(token: str, payload: dict) -> httpx.Response:
    with httpx.Client(base_url=obter_url_do_backend(), timeout=8.0) as cliente:
        return cliente.put(
            ROTA_TROCAR_SENHA_API,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
