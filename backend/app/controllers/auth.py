from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.users import UsuarioSistemaModel
from app.repositories.database import get_db
from app.repositories.medicos_repository import MedicosRepository
from app.repositories.users_repository import UsersRepository
from app.schemas.auth import (
    AlterarSenhaRequest,
    LoginRequest,
    UsuarioAtualizarRequest,
    UsuarioProvisionarRequest,
)
from app.services.autenticacao import (
    autenticar_usuario,
    emitir_token,
    exigir_papeis,
    exigir_usuario_atual,
    exigir_usuario_atual_cookie,
    gerar_hash_senha,
    usuario_publico,
)
from app.services.medicos_service import MedicosService
from app.services.users_service import UsersService


NOME_COOKIE_SESSAO = "mediflow_access_token"


def login(payload: LoginRequest, db: Session = Depends(get_db)):
    usuario = autenticar_usuario(db, payload.email, payload.senha)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = emitir_token(usuario)
    except RuntimeError as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A autenticação da API não está configurada.",
        ) from erro
    return {"access_token": token, "token_type": "bearer", "usuario": usuario_publico(usuario)}


def obter_sessao(usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual)):
    return usuario_publico(usuario)


def definir_cookie_sessao(
    request: Request,
    response: Response,
    usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual),
):
    """Emite cookie HttpOnly após validar o Bearer apresentado pelo frontend."""
    autorizacao = request.headers.get("authorization", "")
    esquema, _, token = autorizacao.partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Autenticação necessária.")
    response.set_cookie(
        key=NOME_COOKIE_SESSAO,
        value=token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.APP_ENV.lower() in {"production", "prod"},
        samesite="lax",
        path="/",
    )
    return {"ok": True}


def encerrar_sessao_cookie(
    response: Response,
    _usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual_cookie),
):
    """Remove o cookie HttpOnly da sessão autenticada no navegador."""
    response.delete_cookie(
        key=NOME_COOKIE_SESSAO,
        httponly=True,
        secure=settings.APP_ENV.lower() in {"production", "prod"},
        samesite="lax",
        path="/",
    )
    return {"ok": True}


def alterar_senha(
    payload: AlterarSenhaRequest,
    usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual),
    db: Session = Depends(get_db),
):
    if not usuario.trocar_senha_obrigatorio:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A alteração sem senha atual só é permitida na troca obrigatória do primeiro acesso.",
        )
    usuario.senha_hash = gerar_hash_senha(payload.nova_senha)
    usuario.trocar_senha_obrigatorio = False
    users_repo = UsersRepository(db)
    salvo = users_repo.salvar(usuario)
    return usuario_publico(salvo)


def listar_usuarios(
    usuario: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    users_repo = UsersRepository(db)
    service = UsersService(users_repo=users_repo)
    return service.listar_usuarios(ator=usuario)


def provisionar_usuario(
    payload: UsuarioProvisionarRequest,
    ator: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    users_repo = UsersRepository(db)
    medicos_repo = MedicosRepository(db)
    service = MedicosService(users_repo=users_repo, medicos_repo=medicos_repo)
    return service.provisionar_profissional(payload=payload, ator=ator)


def atualizar_usuario(
    usuario_id: int,
    payload: UsuarioAtualizarRequest,
    ator: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO", "ENFERMEIRO")),
    db: Session = Depends(get_db),
):
    users_repo = UsersRepository(db)
    service = UsersService(users_repo=users_repo)
    return service.atualizar_usuario(usuario_id=usuario_id, dados=payload, ator=ator)


def desativar_usuario(
    usuario_id: int,
    ator: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    users_repo = UsersRepository(db)
    service = UsersService(users_repo=users_repo)
    service.desativar_usuario(usuario_id=usuario_id, ator=ator)
