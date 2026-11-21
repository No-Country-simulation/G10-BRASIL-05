"""Perfis, permissões e validação de cadastro de usuários."""
from typing import Any

__all__ = [
    "NIVEL_ADMIN_GERAL", "NIVEL_DIRETOR", "NIVEL_MEDICO", "NIVEL_ENFERMEIRO",
    "EMAIL_INSTITUCIONAL_WHATSAPP", "CHAVE_EMAIL_SESSAO", "CHAVE_LISTA_USUARIOS",
    "eh_conta_institucional_whatsapp", "NIVEIS_DE_ACESSO", "ROTULOS_DE_NIVEL",
    "UFS_BRASIL", "DEPARTAMENTOS_POR_NIVEL", "REQUISITO_POR_DEPARTAMENTO",
    "PERMISSOES_POR_NIVEL", "obter_permissoes", "niveis_que_pode_gerenciar",
    "pode_gerenciar_alvo", "pode_analisar_documentos_da_enfermagem",
    "validar_cadastro_usuario",
]

NIVEL_ADMIN_GERAL = "ADMIN_GERAL"
NIVEL_DIRETOR = "DIRETOR"
NIVEL_MEDICO = "MEDICO"
NIVEL_ENFERMEIRO = "ENFERMEIRO"

EMAIL_INSTITUCIONAL_WHATSAPP = "mediflow@equipe.com.br"
CHAVE_EMAIL_SESSAO = "usuario_autenticado_email"
CHAVE_LISTA_USUARIOS = "rbac_lista_usuarios"


def eh_conta_institucional_whatsapp(email_ou_sessao: Any = None) -> bool:
    """Retorna True somente quando a sessão ou e-mail pertence à conta institucional (mediflow@equipe.com.br)."""
    if email_ou_sessao is None:
        return False
    if isinstance(email_ou_sessao, str):
        return email_ou_sessao.strip().lower() == EMAIL_INSTITUCIONAL_WHATSAPP
    if hasattr(email_ou_sessao, "get"):
        email = (
            email_ou_sessao.get(CHAVE_EMAIL_SESSAO)
            or email_ou_sessao.get("email")
            or ""
        )
        return str(email).strip().lower() == EMAIL_INSTITUCIONAL_WHATSAPP
    return False

NIVEIS_DE_ACESSO = (
    NIVEL_ADMIN_GERAL,
    NIVEL_DIRETOR,
    NIVEL_MEDICO,
    NIVEL_ENFERMEIRO,
)

ROTULOS_DE_NIVEL = {
    NIVEL_ADMIN_GERAL: "Administrador Geral",
    NIVEL_DIRETOR: "Diretor Clínico",
    NIVEL_MEDICO: "Médico",
    NIVEL_ENFERMEIRO: "Enfermeiro(a)",
    "INSTITUCIONAL_WHATSAPP": "Conta institucional",
}

UFS_BRASIL = (
    "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "CE", "DF",
    "GO", "ES", "PA", "AM", "MA", "MT", "MS", "PB", "RN", "AL",
    "PI", "SE", "RO", "TO", "AC", "AP", "RR",
)

DEPARTAMENTOS_POR_NIVEL = {
    NIVEL_DIRETOR: (
        "Diretoria Clínica & Governança",
        "Diretoria Técnica Hospitalar",
        "Coordenação Geral de Auditoria Médica",
    ),
    NIVEL_MEDICO: (
        "Clínica Médica & Auditoria",
        "Radiologia & Diagnóstico por Imagem",
        "Emergência / Pronto Socorro",
        "Cardiologia",
    ),
    NIVEL_ENFERMEIRO: (
        "Triagem Clínica (Human-in-the-Loop)",
        "Pronto Socorro & Classificação de Risco",
        "Auditoria de Enfermagem & Guias TISS",
        "Unidade de Terapia Intensiva (UTI)",
    ),
}

REQUISITO_POR_DEPARTAMENTO = {
    # Diretor
    "Diretoria Clínica & Governança": (
        "Portaria de Nomeação / Ata de Eleição do Corpo Clínico (Res. CFM 2.147/2016)",
        "Ex.: Portaria Diretoria nº 014/2026",
    ),
    "Diretoria Técnica Hospitalar": (
        "CRT — Certidão de Responsabilidade Técnica no CRM",
        "Ex.: CRT-CRM/SP 2026-0891",
    ),
    "Coordenação Geral de Auditoria Médica": (
        "Registro de Coordenação de Auditoria Médica / RQE",
        "Ex.: Portaria Auditoria nº 008/2026",
    ),
    # Médico
    "Clínica Médica & Auditoria": (
        "RQE (Registro de Qualificação de Especialista) / Habilitação TISS",
        "Ex.: RQE 84512",
    ),
    "Radiologia & Diagnóstico por Imagem": (
        "RQE em Radiologia / Certificação CBR (Colégio Brasileiro de Radiologia)",
        "Ex.: RQE 71204 • CBR Ativo",
    ),
    "Emergência / Pronto Socorro": (
        "RQE / Certificação ACLS & ATLS (Suporte Avançado de Vida)",
        "Ex.: RQE 90112 • ACLS/ATLS",
    ),
    "Cardiologia": (
        "RQE em Cardiologia (SBC / CFM)",
        "Ex.: RQE 65320",
    ),
    # Enfermeiro
    "Triagem Clínica (Human-in-the-Loop)": (
        "Certificação em Classificação de Risco (Protocolo de Manchester / HITL)",
        "Ex.: Cert. Manchester GBCR #44910",
    ),
    "Pronto Socorro & Classificação de Risco": (
        "Habilitação em Urgência/Emergência & Protocolo de Manchester",
        "Ex.: Cert. Manchester / BLS #31802",
    ),
    "Auditoria de Enfermagem & Guias TISS": (
        "Registro de Especialização em Auditoria em Saúde (COFEN)",
        "Ex.: Reg. COFEN-AUD #19204",
    ),
    "Unidade de Terapia Intensiva (UTI)": (
        "Título de Especialista em Terapia Intensiva (ABENTI / COFEN)",
        "Ex.: Reg. COFEN-UTI #28411",
    ),
}

PERMISSOES_POR_NIVEL = {
    NIVEL_ADMIN_GERAL: {
        "cadastrar_medicos": True,
        "remover_medicos": True,
        "editar_medicos": True,
        "cadastrar_enfermeiros": True,
        "editar_enfermeiros": True,
        "remover_enfermeiros": True,
        "analisar_documentos_enfermagem": True,
        "human_in_the_loop": True,
        "gerenciar_whatsapp": True,
    },
    NIVEL_DIRETOR: {
        "cadastrar_medicos": True,
        "remover_medicos": True,
        "editar_medicos": True,
        "cadastrar_enfermeiros": True,
        "editar_enfermeiros": True,
        "remover_enfermeiros": True,
        "analisar_documentos_enfermagem": True,
        "human_in_the_loop": True,
    },
    NIVEL_MEDICO: {
        "cadastrar_medicos": False,
        "remover_medicos": False,
        "editar_medicos": False,
        "cadastrar_enfermeiros": True,
        "editar_enfermeiros": True,
        "remover_enfermeiros": True,
        "analisar_documentos_enfermagem": True,
        "human_in_the_loop": True,
    },
    NIVEL_ENFERMEIRO: {
        "cadastrar_medicos": False,
        "remover_medicos": False,
        "editar_medicos": False,
        "cadastrar_enfermeiros": False,
        "editar_enfermeiros": False,
        "remover_enfermeiros": False,
        "analisar_documentos_enfermagem": False,
        "human_in_the_loop": True,
    },
}



def obter_permissoes(nivel: str) -> dict[str, bool]:
    return dict(PERMISSOES_POR_NIVEL.get(nivel, PERMISSOES_POR_NIVEL[NIVEL_ENFERMEIRO]))


def niveis_que_pode_gerenciar(nivel_ator: str) -> tuple[str, ...]:
    if nivel_ator == NIVEL_ADMIN_GERAL:
        return (NIVEL_DIRETOR, NIVEL_MEDICO, NIVEL_ENFERMEIRO)
    if nivel_ator == NIVEL_DIRETOR:
        return (NIVEL_DIRETOR, NIVEL_MEDICO, NIVEL_ENFERMEIRO)
    if nivel_ator == NIVEL_MEDICO:
        return (NIVEL_ENFERMEIRO,)
    return ()


def pode_gerenciar_alvo(nivel_ator: str, nivel_alvo: str) -> bool:
    return nivel_alvo in niveis_que_pode_gerenciar(nivel_ator)


def pode_analisar_documentos_da_enfermagem(nivel_ator: str) -> bool:
    return obter_permissoes(nivel_ator).get("analisar_documentos_enfermagem", False)


def validar_cadastro_usuario(
    nivel_ator: str,
    nome: str,
    nivel_novo: str,
    registro: str,
    especialidade: str,
    cpf: str = "000.000.000-00",
    endereco: str = "Não informado",
) -> str | None:
    if not pode_gerenciar_alvo(nivel_ator, nivel_novo):
        return (
            f"O perfil {ROTULOS_DE_NIVEL.get(nivel_ator, nivel_ator)} não tem permissão "
            f"para cadastrar usuários do nível {ROTULOS_DE_NIVEL.get(nivel_novo, nivel_novo)}."
        )
    if not nome or not nome.strip():
        return "Informe o nome completo do profissional."
    if not cpf or not cpf.strip():
        return "Informe o CPF do profissional."
    if not registro or not registro.strip():
        return "Informe o registro no conselho de classe (CRM ou COREN)."
    if not especialidade or not especialidade.strip():
        return "Informe o departamento ou especialidade de atuação."
    if not endereco or not endereco.strip():
        return "Informe o endereço do profissional."
    return None


