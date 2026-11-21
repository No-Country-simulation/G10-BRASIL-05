"""Operações puras de cadastro e revisão de usuários."""
from utils.usuarios_politicas import (
    NIVEL_ADMIN_GERAL,
    NIVEL_DIRETOR,
    NIVEL_ENFERMEIRO,
    NIVEL_MEDICO,
    ROTULOS_DE_NIVEL,
    pode_analisar_documentos_da_enfermagem,
    pode_gerenciar_alvo,
    validar_cadastro_usuario,
)

__all__ = [
    "cadastrar_usuario",
    "editar_usuario",
    "remover_usuario",
    "registrar_analise_medica",
    "encaminhar_hitl_enfermagem",
]


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
