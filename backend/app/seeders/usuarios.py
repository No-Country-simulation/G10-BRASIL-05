from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.triagem import UsuarioSistemaModel
from app.services.autenticacao import gerar_hash_senha
from app.seeders.errors import BootstrapAdminError


# Adicione usuários provisionados como pares email/nome. Todos começam como ENFERMEIRO.
USUARIOS_A_SEMEAR: tuple[dict[str, str], ...] = ()


def semear_usuarios_configurados(db: Session) -> None:
    if not USUARIOS_A_SEMEAR:
        return
    senha = settings.ADMIN_BOOTSTRAP_PASSWORD
    if len(senha) < 12:
        raise BootstrapAdminError("ADMIN_BOOTSTRAP_PASSWORD deve ter pelo menos 12 caracteres.")

    emails_vistos: set[str] = set()
    for dados in USUARIOS_A_SEMEAR:
        email = dados["email"].strip().lower()
        nome = dados["nome"].strip()
        if not email or "@" not in email or not nome:
            raise BootstrapAdminError("Cada usuário seed precisa de email e nome válidos.")
        if email in emails_vistos:
            raise BootstrapAdminError(f"O email {email} aparece mais de uma vez na lista de seed.")
        emails_vistos.add(email)
        if db.query(UsuarioSistemaModel).filter_by(email=email).first():
            continue
        db.add(
            UsuarioSistemaModel(
                email=email,
                nome=nome,
                senha_hash=gerar_hash_senha(senha),
                papel="ENFERMEIRO",
                trocar_senha_obrigatorio=True,
                pode_gerenciar_whatsapp=False,
                ativo=True,
            )
        )
