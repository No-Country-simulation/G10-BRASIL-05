from typing import Any

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


def cadastrar_usuario(
    usuarios: list[dict],
    nivel_ator: str,
    nome: str,
    nivel_novo: str,
    registro: str,
    especialidade: str,
    cpf: str = "000.000.000-00",
    email: str = "",
    telefone: str = "",
    documento_departamento: str = "",
    cns: str = "",
    cep: str = "",
    endereco: str = "Não informado",
    cidade_uf: str = "São Paulo/SP",
) -> tuple[list[dict], dict | None, str | None]:
    erro = validar_cadastro_usuario(
        nivel_ator=nivel_ator,
        nome=nome,
        nivel_novo=nivel_novo,
        registro=registro,
        especialidade=especialidade,
        cpf=cpf,
        endereco=endereco,
    )
    if erro:
        return usuarios, None, erro

    existentes = [
        int(u["id"].split("-")[-1])
        for u in usuarios
        if u.get("id", "").startswith("USR-") and u["id"].split("-")[-1].isdigit()
    ]
    proximo_num = (max(existentes) + 1) if existentes else (len(usuarios) + 1)
    novo = {
        "id": f"USR-{proximo_num:03d}",
        "nome": nome.strip(),
        "cpf": cpf.strip(),
        "email": email.strip(),
        "telefone": telefone.strip(),
        "nivel": nivel_novo,
        "registro": registro.strip(),
        "documento_departamento": documento_departamento.strip() or "Validado",
        "cns": cns.strip(),
        "especialidade": especialidade.strip(),
        "cep": cep.strip(),
        "endereco": endereco.strip(),
        "cidade_uf": cidade_uf.strip(),
    }
    nova_lista = [*usuarios, novo]
    return nova_lista, novo, None


def editar_usuario(
    usuarios: list[dict],
    nivel_ator: str,
    id_ator: str,
    id_alvo: str,
    nome: str,
    registro: str,
    especialidade: str,
    cpf: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    documento_departamento: str | None = None,
    cns: str | None = None,
    cep: str | None = None,
    endereco: str | None = None,
    cidade_uf: str | None = None,
) -> tuple[list[dict], str | None]:
    alvo = next((u for u in usuarios if u["id"] == id_alvo), None)
    if alvo is None:
        return usuarios, "Usuário não encontrado."

    editando_proprio_perfil = id_ator == id_alvo
    if not editando_proprio_perfil and not pode_gerenciar_alvo(nivel_ator, alvo["nivel"]):
        return (
            usuarios,
            f"O perfil {ROTULOS_DE_NIVEL.get(nivel_ator, nivel_ator)} não tem permissão "
            f"para editar um {ROTULOS_DE_NIVEL.get(alvo['nivel'], alvo['nivel'])}.",
        )
    if not nome or not nome.strip():
        return usuarios, "O nome do profissional não pode ficar vazio."
    if not registro or not registro.strip():
        return usuarios, "O registro profissional não pode ficar vazio."

    nova_lista = []
    for u in usuarios:
        if u["id"] == id_alvo:
            nova_lista.append(
                {
                    **u,
                    "nome": nome.strip(),
                    "registro": registro.strip(),
                    "especialidade": especialidade.strip() or u["especialidade"],
                    "cpf": cpf.strip() if cpf is not None and cpf.strip() else u.get("cpf", ""),
                    "email": email.strip() if email is not None else u.get("email", ""),
                    "telefone": telefone.strip() if telefone is not None else u.get("telefone", ""),
                    "documento_departamento": (
                        documento_departamento.strip()
                        if documento_departamento is not None and documento_departamento.strip()
                        else u.get("documento_departamento", "")
                    ),
                    "cns": cns.strip() if cns is not None else u.get("cns", ""),
                    "cep": cep.strip() if cep is not None else u.get("cep", ""),
                    "endereco": (
                        endereco.strip()
                        if endereco is not None and endereco.strip()
                        else u.get("endereco", "")
                    ),
                    "cidade_uf": (
                        cidade_uf.strip()
                        if cidade_uf is not None and cidade_uf.strip()
                        else u.get("cidade_uf", "")
                    ),
                }
            )
        else:
            nova_lista.append(u)
    return nova_lista, None


def remover_usuario(
    usuarios: list[dict],
    nivel_ator: str,
    id_ator: str,
    id_alvo: str,
) -> tuple[list[dict], str | None]:
    if id_ator == id_alvo:
        return usuarios, "Não é possível remover o usuário que está ativo na sessão atual."

    alvo = next((u for u in usuarios if u["id"] == id_alvo), None)
    if alvo is None:
        return usuarios, "Usuário não encontrado."

    if not pode_gerenciar_alvo(nivel_ator, alvo["nivel"]):
        return (
            usuarios,
            f"O perfil {ROTULOS_DE_NIVEL.get(nivel_ator, nivel_ator)} não tem permissão "
            f"para remover um {ROTULOS_DE_NIVEL.get(alvo['nivel'], alvo['nivel'])}.",
        )

    nova_lista = [u for u in usuarios if u["id"] != id_alvo]
    return nova_lista, None


def registrar_analise_medica(
    documentos: list[dict],
    nivel_ator: str,
    nome_medico: str,
    registro_medico: str,
    documento_id: str,
    decisao: str,
    parecer: str,
) -> tuple[list[dict], str | None]:
    if not pode_analisar_documentos_da_enfermagem(nivel_ator):
        return (
            documentos,
            "Apenas Médicos e Diretores podem realizar a análise final de documentos triados pela enfermagem.",
        )
    if not parecer or not parecer.strip():
        return documentos, "Informe o parecer médico antes de finalizar a análise."

    encontrado = False
    nova_lista = []
    for doc in documentos:
        if doc["documento_id"] == documento_id:
            encontrado = True
            nova_lista.append(
                {
                    **doc,
                    "status_revisao": decisao,
                    "medico_revisor": f"{nome_medico} ({registro_medico})",
                    "parecer_medico": parecer.strip(),
                }
            )
        else:
            nova_lista.append(doc)

    if not encontrado:
        return documentos, "Documento não encontrado na fila de supervisão médica."
    return nova_lista, None


def encaminhar_hitl_enfermagem(
    documentos: list[dict],
    nome_enfermeiro: str,
    registro_enfermeiro: str,
    documento_id: str,
    paciente: str,
    tipo_documento: str,
    prioridade: str,
    nota_enfermagem: str,
) -> tuple[list[dict], str | None]:
    if not documento_id or not documento_id.strip():
        return documentos, "Informe o código do documento."
    if not paciente or not paciente.strip():
        return documentos, "Informe o nome do paciente."
    if not nota_enfermagem or not nota_enfermagem.strip():
        return documentos, "Descreva a conferência realizada no Human-in-the-Loop."

    novo_doc = {
        "documento_id": documento_id.strip().upper(),
        "paciente": paciente.strip(),
        "tipo_documento": tipo_documento,
        "prioridade": prioridade,
        "enfermeiro_responsavel": f"{nome_enfermeiro} ({registro_enfermeiro})",
        "nota_enfermagem": nota_enfermagem.strip(),
        "status_revisao": "Aguardando análise médica",
        "medico_revisor": None,
        "parecer_medico": None,
    }
    return [novo_doc, *documentos], None
