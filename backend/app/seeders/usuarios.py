from typing import Any
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.triagem import UsuarioSistemaModel
from app.services.autenticacao import gerar_hash_senha
from app.seeders.errors import BootstrapAdminError


MEMBROS_EQUIPE: tuple[dict[str, str], ...] = (
    {"slug": "pedro", "nome": "Pedro Araujo", "crm": "CRM 101001-SP", "coren": "COREN 202001-SP"},
    {"slug": "lianna", "nome": "Lianna Ribeiro", "crm": "CRM 101002-SP", "coren": "COREN 202002-SP"},
    {"slug": "marcio", "nome": "Marcio Jose de Morais", "crm": "CRM 101003-SP", "coren": "COREN 202003-SP"},
    {"slug": "joao", "nome": "Joao Pedro Alves Botelho", "crm": "CRM 101004-SP", "coren": "COREN 202004-SP"},
    {"slug": "pedrohenrique", "nome": "Pedro Henrique Marinho Euzebio", "crm": "CRM 101005-SP", "coren": "COREN 202005-SP"},
    {"slug": "otavio", "nome": "Otávio Oliveira Santos", "crm": "CRM 101006-SP", "coren": "COREN 202006-SP"},
    {"slug": "adilson", "nome": "Adilson Gaspar Morais Manuel", "crm": "CRM 101007-SP", "coren": "COREN 202007-SP"},
    {"slug": "patrick", "nome": "Patrick Gutenberg Gomes Duarte", "crm": "CRM 101008-SP", "coren": "COREN 202008-SP"},
)


def _gerar_contas_equipe() -> list[dict[str, Any]]:
    contas: list[dict[str, Any]] = []
    for m in MEMBROS_EQUIPE:
        contas.extend([
            {
                "nome": f"{m['nome']} (Diretor)",
                "email": f"{m['slug']}.diretor@mediflow.com.br",
                "papel": "DIRETOR",
                "registro": m["crm"],
                "especialidade": "Diretoria Clínica & Governança",
                "trocar_senha_obrigatorio": False,
                "pode_gerenciar_whatsapp": False,
            },
            {
                "nome": f"Dr(a). {m['nome']}",
                "email": f"{m['slug']}.medico@mediflow.com.br",
                "papel": "MEDICO",
                "registro": m["crm"],
                "especialidade": "Clínica Médica & Auditoria",
                "trocar_senha_obrigatorio": False,
                "pode_gerenciar_whatsapp": False,
            },
            {
                "nome": f"Enf. {m['nome']}",
                "email": f"{m['slug']}.enfermeiro@mediflow.com.br",
                "papel": "ENFERMEIRO",
                "registro": m["coren"],
                "especialidade": "Triagem Clínica (Human-in-the-Loop)",
                "trocar_senha_obrigatorio": False,
                "pode_gerenciar_whatsapp": False,
            },
        ])
    return contas


USUARIOS_A_SEMEAR: tuple[dict[str, Any], ...] = (
    # Contas genéricas por cargo
    {
        "nome": "Diretor Geral",
        "email": "diretor@mediflow.com.br",
        "papel": "DIRETOR",
        "registro": "CRM 110022-SP",
        "especialidade": "Gestão Hospitalar",
        "trocar_senha_obrigatorio": False,
        "pode_gerenciar_whatsapp": False,
    },
    {
        "nome": "Dr. Médico Plantonista",
        "email": "medico@mediflow.com.br",
        "papel": "MEDICO",
        "registro": "CRM 123456-SP",
        "especialidade": "Clínica Médica",
        "trocar_senha_obrigatorio": False,
        "pode_gerenciar_whatsapp": False,
    },
    {
        "nome": "Enfermeiro Triagem",
        "email": "enfermeiro@mediflow.com.br",
        "papel": "ENFERMEIRO",
        "registro": "COREN 654321-SP",
        "especialidade": "Triagem e Emergência",
        "trocar_senha_obrigatorio": False,
        "pode_gerenciar_whatsapp": False,
    },
    *_gerar_contas_equipe(),
)


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
        papel = dados.get("papel", "ENFERMEIRO").strip().upper()
        registro = (dados.get("registro") or "").strip() or None
        especialidade = (dados.get("especialidade") or "").strip() or None
        trocar_senha_obrigatorio = bool(dados.get("trocar_senha_obrigatorio", False))
        pode_gerenciar_whatsapp = bool(dados.get("pode_gerenciar_whatsapp", False))

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
                papel=papel,
                registro=registro,
                especialidade=especialidade,
                trocar_senha_obrigatorio=trocar_senha_obrigatorio,
                pode_gerenciar_whatsapp=pode_gerenciar_whatsapp,
                ativo=True,
            )
        )
