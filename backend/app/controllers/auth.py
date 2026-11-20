from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.triagem import UsuarioSistemaModel
from app.repositories.database import get_db
from app.schemas.auth import (
    AlterarSenhaRequest,
    LoginRequest,
    LoginResponse,
    UsuarioAtualizarRequest,
    UsuarioAutenticado,
    UsuarioProvisionarRequest,
)
from app.services.autenticacao import (
    autenticar_usuario,
    emitir_token,
    exigir_papeis,
    exigir_usuario_atual,
    gerar_hash_senha,
    usuario_publico,
)





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
    db.commit()
    db.refresh(usuario)
    return usuario_publico(usuario)


def listar_usuarios(
    usuario: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    consulta = db.query(UsuarioSistemaModel).filter(UsuarioSistemaModel.ativo.is_(True))
    if usuario.papel == "MEDICO":
        consulta = consulta.filter(UsuarioSistemaModel.papel == "ENFERMEIRO")
    else:
        consulta = consulta.filter(UsuarioSistemaModel.papel.in_(["DIRETOR", "MEDICO", "ENFERMEIRO"]))
    return [usuario_publico(item) for item in consulta.order_by(UsuarioSistemaModel.nome).all()]


def provisionar_usuario(
    payload: UsuarioProvisionarRequest,
    ator: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    if ator.papel == "MEDICO" and payload.nivel != "ENFERMEIRO":
        raise HTTPException(status_code=403, detail="Médicos podem provisionar somente enfermeiros.")
    if db.query(UsuarioSistemaModel).filter_by(email=payload.email).first():
        raise HTTPException(status_code=409, detail="Já existe uma conta com esse e-mail.")
    novo = UsuarioSistemaModel(
        email=payload.email,
        nome=payload.nome.strip(),
        senha_hash=gerar_hash_senha(payload.senha),
        papel=payload.nivel,
        trocar_senha_obrigatorio=False,
        registro=payload.registro.strip() or None,
        especialidade=payload.especialidade.strip() or None,
        ativo=True,
        pode_gerenciar_whatsapp=False,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return usuario_publico(novo)


def atualizar_usuario(
    usuario_id: int,
    payload: UsuarioAtualizarRequest,
    ator: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    alvo = db.query(UsuarioSistemaModel).filter_by(id=usuario_id).first()
    if not alvo or alvo.papel == "INSTITUCIONAL_WHATSAPP":
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if alvo.papel == "ADMIN_GERAL" and ator.papel != "ADMIN_GERAL":
        raise HTTPException(status_code=403, detail="Somente o Administrador Geral pode gerenciar esse perfil.")
    if ator.papel == "MEDICO" and alvo.papel != "ENFERMEIRO":
        raise HTTPException(status_code=403, detail="Médicos podem gerenciar somente enfermeiros.")
    alteracoes = payload.model_dump(exclude_unset=True)
    if "email" in alteracoes:
        existente = db.query(UsuarioSistemaModel).filter_by(email=alteracoes["email"]).first()
        if existente and existente.id != alvo.id:
            raise HTTPException(status_code=409, detail="Já existe uma conta com esse e-mail.")
    if ator.id == alvo.id and alteracoes.get("ativo") is False:
        raise HTTPException(status_code=400, detail="Não é possível desativar a própria conta.")
    if ator.id == alvo.id and alteracoes.get("nivel", alvo.papel) != alvo.papel:
        raise HTTPException(status_code=400, detail="Não é possível alterar o próprio perfil.")
    if ator.papel == "MEDICO" and alteracoes.get("nivel", "ENFERMEIRO") != "ENFERMEIRO":
        raise HTTPException(status_code=403, detail="Médicos não podem alterar o papel de enfermeiro.")
    papel_final = alteracoes.get("nivel", alvo.papel)
    remove_direcao_ativa = (
        alvo.papel == "DIRETOR"
        and alvo.ativo
        and (papel_final != "DIRETOR" or alteracoes.get("ativo") is False)
    )
    if remove_direcao_ativa:
        diretores_ativos = db.query(UsuarioSistemaModel).filter_by(papel="DIRETOR", ativo=True).count()
        if diretores_ativos <= 1:
            raise HTTPException(status_code=409, detail="É necessário manter ao menos um diretor ativo.")
    if alteracoes.get("senha"):
        alvo.senha_hash = gerar_hash_senha(alteracoes.pop("senha"))
    if "nivel" in alteracoes:
        alteracoes["papel"] = alteracoes.pop("nivel")
    for campo in ("nome", "email", "papel", "registro", "especialidade", "ativo"):
        if campo in alteracoes:
            setattr(alvo, campo, alteracoes[campo])
    if alvo.papel not in {"INSTITUCIONAL_WHATSAPP", "ADMIN_GERAL"}:
        alvo.pode_gerenciar_whatsapp = False
    db.commit()
    db.refresh(alvo)
    return usuario_publico(alvo)


def desativar_usuario(
    usuario_id: int,
    ator: UsuarioSistemaModel = Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    alvo = db.query(UsuarioSistemaModel).filter_by(id=usuario_id).first()
    if not alvo or alvo.papel == "INSTITUCIONAL_WHATSAPP":
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if alvo.papel == "ADMIN_GERAL" and ator.papel != "ADMIN_GERAL":
        raise HTTPException(status_code=403, detail="Somente o Administrador Geral pode gerenciar esse perfil.")
    if ator.id == alvo.id:
        raise HTTPException(status_code=400, detail="Não é possível desativar a própria conta.")
    if ator.papel == "MEDICO" and alvo.papel != "ENFERMEIRO":
        raise HTTPException(status_code=403, detail="Médicos podem gerenciar somente enfermeiros.")
    if alvo.papel == "DIRETOR":
        diretores_ativos = db.query(UsuarioSistemaModel).filter_by(papel="DIRETOR", ativo=True).count()
        if diretores_ativos <= 1:
            raise HTTPException(status_code=409, detail="É necessário manter ao menos um diretor ativo.")
    alvo.ativo = False
    db.commit()
