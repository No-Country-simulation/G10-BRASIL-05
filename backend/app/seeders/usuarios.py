from typing import Any
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.triagem import UsuarioSistemaModel
from app.services.autenticacao import gerar_hash_senha
from app.seeders.errors import BootstrapAdminError
from migrations.seeders.usuarios import obter_dados_usuarios


def semear_usuarios_configurados(db: Session) -> None:
    usuarios = obter_dados_usuarios()
    if not usuarios:
        return
    senha = settings.ADMIN_BOOTSTRAP_PASSWORD
    if len(senha) < 12:
        raise BootstrapAdminError("ADMIN_BOOTSTRAP_PASSWORD deve ter pelo menos 12 caracteres.")

    emails_vistos: set[str] = set()
    for dados in usuarios:
        email = dados["email"].strip().lower()
        nome = dados["nome"].strip()
        papel = dados.get("papel", "ENFERMEIRO").strip().upper()
        registro = (dados.get("registro") or "").strip() or None
        especialidade = (dados.get("especialidade") or "").strip() or None
        trocar_senha_obrigatorio = bool(dados.get("trocar_senha_obrigatorio", True))
        pode_gerenciar_whatsapp = bool(dados.get("pode_gerenciar_whatsapp", False))
        senha_hash = dados.get("senha_hash") or gerar_hash_senha(senha)

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
                senha_hash=senha_hash,
                papel=papel,
                registro=registro,
                especialidade=especialidade,
                trocar_senha_obrigatorio=trocar_senha_obrigatorio,
                pode_gerenciar_whatsapp=pode_gerenciar_whatsapp,
                ativo=True,
            )
        )

