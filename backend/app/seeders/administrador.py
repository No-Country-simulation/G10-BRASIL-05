from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config.settings import settings
from app.models.triagem import UsuarioSistemaModel
from app.services.autenticacao import gerar_hash_senha
from app.seeders.errors import BootstrapAdminError


def semear_administrador_inicial(db: Session) -> None:
    administrador_ativo = (
        db.query(UsuarioSistemaModel)
        .filter_by(papel="ADMIN_GERAL", ativo=True)
        .first()
    )
    if administrador_ativo:
        return

    email = settings.ADMIN_BOOTSTRAP_EMAIL.strip().lower()
    senha = settings.ADMIN_BOOTSTRAP_PASSWORD
    nome = settings.ADMIN_BOOTSTRAP_NAME.strip()
    if not email or not senha:
        raise BootstrapAdminError(
            "Nenhum ADMIN_GERAL existe. Configure ADMIN_BOOTSTRAP_EMAIL e "
            "ADMIN_BOOTSTRAP_PASSWORD no ambiente para criar o administrador inicial."
        )
    if len(senha) < 12:
        raise BootstrapAdminError("ADMIN_BOOTSTRAP_PASSWORD deve ter pelo menos 12 caracteres.")
    email_existente = (
        db.query(UsuarioSistemaModel)
        .filter(func.lower(func.trim(UsuarioSistemaModel.email)) == email)
        .first()
    )
    if email_existente:
        if email_existente.papel == "ADMIN_GERAL" and not email_existente.ativo:
            mensagem = (
                "A conta ADMIN_GERAL configurada existe, mas está inativa. "
                "Use outro ADMIN_BOOTSTRAP_EMAIL ou reative a conta após redefinir a credencial."
            )
        else:
            mensagem = (
                "ADMIN_BOOTSTRAP_EMAIL já pertence a outra conta. "
                "Escolha um email não cadastrado."
            )
        raise BootstrapAdminError(mensagem)

    db.add(
        UsuarioSistemaModel(
            email=email,
            nome=nome,
            senha_hash=gerar_hash_senha(senha),
            papel="ADMIN_GERAL",
            trocar_senha_obrigatorio=True,
            ativo=True,
            pode_gerenciar_whatsapp=True,
        )
    )
