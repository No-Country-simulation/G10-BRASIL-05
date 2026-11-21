import base64
from datetime import datetime
import json
import logging
from typing import Any

import httpx

from api import autenticacao as api_autenticacao

logger = logging.getLogger(__name__)


CHAVE_JWT_TOKEN = "mediflow_jwt_token"
CHAVE_USUARIO_LOGADO = "mediflow_usuario_logado"
CHAVE_IS_AUTENTICADO = "mediflow_autenticado"
CHAVE_DATA_LOGIN = "mediflow_data_login"
ROTA_LOGIN_API = api_autenticacao.ROTA_LOGIN_API
ROTA_SESSAO_API = api_autenticacao.ROTA_SESSAO_API
ROTA_TROCAR_SENHA_API = api_autenticacao.ROTA_TROCAR_SENHA_API


def decodificar_payload_jwt(token: str | None) -> dict:
    """Decodifica as claims do payload JWT de maneira segura e tolerante a falhas."""
    if not token or not isinstance(token, str):
        return {}
    try:
        partes = token.split(".")
        if len(partes) >= 2:
            payload_b64 = partes[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            dados = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
            if isinstance(dados, dict):
                return dados
    except Exception:
        pass
    return {}


def precisa_trocar_senha(session_state: Any = None) -> bool:
    """Verifica se o usuário autenticado deve obrigatoriamente trocar a senha inicial."""
    if session_state is None:
        return False
    if session_state.get("mediflow_senha_trocada", False):
        return False

    usuario = obter_usuario_autenticado(session_state)
    if usuario and isinstance(usuario, dict) and usuario.get("trocar_senha_obrigatorio") is True:
        return True

    token = obter_token_jwt(session_state)
    if token:
        claims = decodificar_payload_jwt(token)
        if claims.get("trocar_senha_obrigatorio") is True:
            return True

    return False


def autenticar_com_api(
    identificador: str,
    senha: str,
    session_state: Any = None,
) -> tuple[bool, str, dict | None, str | None]:
    """Valida credenciais e recebe o token exclusivamente do FastAPI."""
    email = (identificador or "").strip().lower()
    if not email:
        return False, "Informe o e-mail institucional.", None, None
    if not senha:
        return False, "Informe a senha de acesso.", None, None

    try:
        resposta = api_autenticacao.autenticar(email, senha)
    except httpx.HTTPError:
        return False, "Não foi possível conectar ao serviço de autenticação.", None, None

    if resposta.status_code == 401:
        return False, "E-mail ou senha inválidos.", None, None
    if resposta.is_error:
        return False, "A API não conseguiu concluir a autenticação.", None, None
    try:
        dados = resposta.json()
        token = dados.get("access_token")
        usuario = dados.get("usuario")
    except (ValueError, AttributeError):
        return False, "A API devolveu uma resposta inválida.", None, None
    if not isinstance(token, str) or not token or not isinstance(usuario, dict):
        return False, "A API devolveu uma resposta inválida.", None, None

    _salvar_sessao_autenticada(session_state, usuario, token)
    return True, "Autenticação concluída.", usuario, token


def validar_sessao_api(session_state: Any = None) -> bool:
    """Revalida a sessão no servidor mantendo tolerância a oscilações temporárias de rede."""
    token = obter_token_jwt(session_state)
    if not token or session_state is None:
        return False
    try:
        resposta = api_autenticacao.consultar_sessao(token)
    except httpx.HTTPError as erro:
        logger.warning("Falha de rede ou timeout ao validar sessão na API: %s. Mantendo sessão ativa.", erro)
        return True

    status_code = getattr(resposta, "status_code", None)

    # Somente deslogar se a resposta da API for explicitamente HTTP 401 (token expirado/inválido)
    if status_code == 401 or (status_code == 200 and getattr(resposta, "is_error", False)):
        logger.info("Sessão encerrada pela API: token expirado ou inválido (HTTP 401).")
        deslogar(session_state)
        return False

    # Erro de servidor temporário (5xx): não deslogar
    if status_code is not None and 500 <= status_code < 600:
        logger.warning("Erro temporário do servidor ao validar sessão (HTTP %s). Mantendo sessão ativa.", status_code)
        return True

    # Se a resposta foi outro tipo de erro que não 401
    if getattr(resposta, "is_error", False):
        logger.warning("Resposta com erro ao validar sessão (HTTP %s). Mantendo sessão ativa.", status_code)
        return True

    try:
        usuario = resposta.json()
    except (ValueError, AttributeError):
        logger.warning("Não foi possível decodificar JSON do usuário retornado pela API. Mantendo sessão ativa.")
        return True

    if not isinstance(usuario, dict):
        logger.warning("Formato inesperado para dados do usuário retornado pela API. Mantendo sessão ativa.")
        return True

    session_state[CHAVE_USUARIO_LOGADO] = usuario
    session_state["usuario_ativo_id"] = usuario.get("id", "")
    session_state["usuario_autenticado_email"] = usuario.get("email", "")
    return True


def trocar_senha_inicial(
    arg1: str,
    arg2: Any,
    arg3: Any = None,
) -> tuple[bool, str]:
    if arg3 is None and not isinstance(arg2, str):
        senha_atual = ""
        nova_senha = str(arg1 or "")
        session_state = arg2
    else:
        senha_atual = str(arg1 or "")
        nova_senha = str(arg2 or "")
        session_state = arg3

    token = obter_token_jwt(session_state)
    if not token:
        return False, "Entre novamente para trocar sua senha."

    payload = {"nova_senha": nova_senha}
    if senha_atual:
        payload["senha_atual"] = senha_atual

    try:
        resposta = api_autenticacao.alterar_senha(token, payload)
    except httpx.HTTPError:
        return False, "Não foi possível conectar ao serviço de autenticação."
    if resposta.is_error:
        try:
            detalhe = resposta.json().get("detail")
        except (ValueError, AttributeError):
            detalhe = None
        return False, detalhe or "A API não conseguiu alterar a senha."
    try:
        usuario = resposta.json()
    except ValueError:
        return False, "A API devolveu uma resposta inválida."
    if not isinstance(usuario, dict):
        return False, "A API devolveu uma resposta inválida."

    usuario["trocar_senha_obrigatorio"] = False
    if session_state is not None:
        session_state[CHAVE_USUARIO_LOGADO] = usuario
        session_state["usuario_ativo_id"] = usuario.get("id", "")
        session_state["usuario_autenticado_email"] = usuario.get("email", "")
        session_state["mediflow_senha_trocada"] = True
    return True, "Senha alterada com sucesso! Seu acesso está liberado."


def _salvar_sessao_autenticada(session_state: Any, usuario: dict, token: str) -> None:
    if session_state is None:
        return
    session_state.pop("logout_efetuado", None)
    session_state[CHAVE_JWT_TOKEN] = token
    claims = decodificar_payload_jwt(token)
    if "trocar_senha_obrigatorio" in claims:
        usuario["trocar_senha_obrigatorio"] = bool(claims["trocar_senha_obrigatorio"])
    session_state[CHAVE_USUARIO_LOGADO] = usuario
    session_state[CHAVE_IS_AUTENTICADO] = True
    session_state[CHAVE_DATA_LOGIN] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    session_state["usuario_ativo_id"] = usuario.get("id", "")
    session_state["usuario_autenticado_email"] = usuario.get("email", "")


def deslogar(session_state: Any = None) -> None:
    if session_state is None:
        return
    session_state["logout_efetuado"] = True
    for chave in (
        CHAVE_JWT_TOKEN,
        CHAVE_USUARIO_LOGADO,
        CHAVE_IS_AUTENTICADO,
        CHAVE_DATA_LOGIN,
        "usuario_ativo_id",
        "usuario_autenticado_email",
        "rbac_lista_usuarios",
        "mediflow_senha_trocada",
    ):
        session_state.pop(chave, None)


def restaurar_sessao_por_token(token: str, session_state: Any) -> bool:
    if not token or not isinstance(token, str) or session_state is None:
        return False
    try:
        resposta = api_autenticacao.consultar_sessao(token)
    except httpx.HTTPError:
        return False
    if resposta.is_error:
        return False
    try:
        usuario = resposta.json()
    except ValueError:
        return False
    if not isinstance(usuario, dict):
        return False
    _salvar_sessao_autenticada(session_state, usuario, token)
    return True


def esta_autenticado(session_state: Any = None) -> bool:
    return bool(
        session_state is not None
        and session_state.get(CHAVE_IS_AUTENTICADO)
        and session_state.get(CHAVE_JWT_TOKEN)
        and session_state.get(CHAVE_USUARIO_LOGADO)
    )


def obter_token_jwt(session_state: Any = None) -> str | None:
    return session_state.get(CHAVE_JWT_TOKEN) if session_state is not None else None


def obter_usuario_autenticado(session_state: Any = None) -> dict | None:
    return session_state.get(CHAVE_USUARIO_LOGADO) if session_state is not None else None


def obter_cabecalho_autorizacao(session_state: Any = None) -> dict[str, str]:
    token = obter_token_jwt(session_state)
    return {"Authorization": f"Bearer {token}"} if token else {}


__all__ = [
    "CHAVE_DATA_LOGIN",
    "CHAVE_IS_AUTENTICADO",
    "CHAVE_JWT_TOKEN",
    "CHAVE_USUARIO_LOGADO",
    "ROTA_LOGIN_API",
    "ROTA_SESSAO_API",
    "ROTA_TROCAR_SENHA_API",
    "autenticar_com_api",
    "decodificar_payload_jwt",
    "deslogar",
    "esta_autenticado",
    "obter_cabecalho_autorizacao",
    "obter_token_jwt",
    "obter_usuario_autenticado",
    "precisa_trocar_senha",
    "restaurar_sessao_por_token",
    "validar_sessao_api",
    "trocar_senha_inicial",
]

