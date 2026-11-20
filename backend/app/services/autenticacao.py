import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.triagem import UsuarioSistemaModel
from app.repositories.database import get_db


ITERACOES_PBKDF2 = 600_000
ALGORITMO_JWT = "HS256"
EMISSOR_JWT = "mediflow-auth"
PAPEIS_PROFISSIONAIS = {"DIRETOR", "MEDICO", "ENFERMEIRO"}
PAPEL_ADMIN_GERAL = "ADMIN_GERAL"
PAPEL_WHATSAPP = "INSTITUCIONAL_WHATSAPP"
_bearer = HTTPBearer(auto_error=False)
_hash_isca: str | None = None


def gerar_hash_senha(senha: str) -> str:
    """Cria hash PBKDF2 com salt aleatório no formato usado pela migration."""
    salt = os.urandom(16)
    derivado = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, ITERACOES_PBKDF2
    )
    return "pbkdf2_sha256${}${}${}".format(
        ITERACOES_PBKDF2,
        _codificar_base64(salt),
        _codificar_base64(derivado),
    )


def verificar_senha_hash(senha: str, hash_armazenado: str) -> bool:
    """Valida hashes PBKDF2 sem aceitar formatos malformados."""
    try:
        algoritmo, iteracoes, salt_texto, digest_texto = hash_armazenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        iteracoes_int = int(iteracoes)
        if iteracoes_int < 1:
            return False
        salt = _decodificar_base64(salt_texto)
        digest_esperado = _decodificar_base64(digest_texto)
        digest_calculado = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt, iteracoes_int
        )
        return hmac.compare_digest(digest_calculado, digest_esperado)
    except (AttributeError, TypeError, ValueError):
        return False


def autenticar_usuario(db: Session, email: str, senha: str) -> UsuarioSistemaModel | None:
    global _hash_isca
    email_normalizado = (email or "").strip().lower()
    usuario = (
        db.query(UsuarioSistemaModel)
        .filter(UsuarioSistemaModel.email == email_normalizado)
        .first()
    )
    if usuario:
        senha_valida = verificar_senha_hash(senha or "", usuario.senha_hash)
    else:
        if _hash_isca is None:
            _hash_isca = gerar_hash_senha("senha-isca-nao-utilizada")
        verificar_senha_hash(senha or "", _hash_isca)
        senha_valida = False
    if not usuario or not usuario.ativo or not senha_valida:
        return None
    return usuario


def emitir_token(usuario: UsuarioSistemaModel) -> str:
    chave = settings.JWT_SECRET_KEY
    if len(chave) < 32:
        raise RuntimeError("JWT_SECRET_KEY deve conter pelo menos 32 caracteres.")
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "role": usuario.papel,
        "trocar_senha_obrigatorio": bool(usuario.trocar_senha_obrigatorio),
        "iss": EMISSOR_JWT,
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": _codificar_base64(os.urandom(16)),
    }
    return jwt.encode(payload, chave, algorithm=ALGORITMO_JWT)


def validar_token(token: str) -> dict:
    chave = settings.JWT_SECRET_KEY
    if len(chave) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A autenticação da API não está configurada.",
        )
    try:
        return jwt.decode(
            token,
            chave,
            algorithms=[ALGORITMO_JWT],
            issuer=EMISSOR_JWT,
            options={"require": ["sub", "role", "iss", "iat", "exp", "jti"]},
        )
    except jwt.InvalidTokenError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais ausentes ou inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from erro


def usuario_publico(usuario: UsuarioSistemaModel) -> dict:
    return {
        "id": f"USR-{usuario.id:03d}",
        "nome": usuario.nome,
        "email": usuario.email,
        "nivel": usuario.papel,
        "trocar_senha_obrigatorio": usuario.trocar_senha_obrigatorio,
        "registro": usuario.registro or "",
        "especialidade": usuario.especialidade or "",
    }


def exigir_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> UsuarioSistemaModel:
    if not credenciais or credenciais.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = validar_token(credenciais.credentials)
    try:
        usuario_id = int(claims["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Credenciais ausentes ou inválidas.")
    usuario = db.query(UsuarioSistemaModel).filter_by(id=usuario_id).first()
    if not usuario or not usuario.ativo or usuario.papel != claims.get("role"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais ausentes ou inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def exigir_papeis(*papeis: str):
    def dependencia(usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual)):
        if usuario.trocar_senha_obrigatorio:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Troque a senha inicial antes de acessar o sistema.",
            )
        if usuario.papel not in papeis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem permissão para esta operação.",
            )
        return usuario

    return dependencia


def _codificar_base64(valor: bytes) -> str:
    return base64.urlsafe_b64encode(valor).decode("ascii").rstrip("=")


def _decodificar_base64(valor: str) -> bytes:
    return base64.urlsafe_b64decode(valor + "=" * (-len(valor) % 4))
