from pathlib import Path
from streamlit.testing.v1 import AppTest

from utils.usuarios import (
    NIVEL_DIRETOR,
    NIVEL_ENFERMEIRO,
    NIVEL_MEDICO,
    cadastrar_usuario,
    clonar_documentos_pre_triados_iniciais,
    clonar_usuarios_iniciais,
    editar_usuario,
    encaminhar_hitl_enfermagem,
    niveis_que_pode_gerenciar,
    pode_analisar_documentos_da_enfermagem,
    registrar_analise_medica,
    remover_usuario,
)

PAGINA_USUARIO = Path(__file__).resolve().parents[1] / "pages" / "5_Usuario.py"


def test_hierarquia_de_gerenciamento():
    assert niveis_que_pode_gerenciar(NIVEL_DIRETOR) == (
        NIVEL_DIRETOR,
        NIVEL_MEDICO,
        NIVEL_ENFERMEIRO,
    )
    assert niveis_que_pode_gerenciar(NIVEL_MEDICO) == (NIVEL_ENFERMEIRO,)
    assert niveis_que_pode_gerenciar(NIVEL_ENFERMEIRO) == ()


def test_diretor_pode_cadastrar_e_remover_medico_e_enfermeiro():
    usuarios = clonar_usuarios_iniciais()
    usuarios, novo_med, erro = cadastrar_usuario(
        usuarios,
        nivel_ator=NIVEL_DIRETOR,
        nome="Dra. Helena Costa",
        nivel_novo=NIVEL_MEDICO,
        registro="CRM/SP 210000",
        especialidade="Cardiologia",
    )
    assert erro is None
    assert novo_med["nivel"] == NIVEL_MEDICO

    usuarios, erro_rem = remover_usuario(
        usuarios,
        nivel_ator=NIVEL_DIRETOR,
        id_ator="USR-001",
        id_alvo=novo_med["id"],
    )
    assert erro_rem is None


def test_medico_pode_gerenciar_enfermeiro_mas_nao_medico_ou_diretor():
    usuarios = clonar_usuarios_iniciais()

    # Médico cadastra enfermeiro -> permitido
    usuarios, novo_enf, erro_enf = cadastrar_usuario(
        usuarios,
        nivel_ator=NIVEL_MEDICO,
        nome="Enf. Bruno Dias",
        nivel_novo=NIVEL_ENFERMEIRO,
        registro="COREN/SP 778899",
        especialidade="Triagem",
    )
    assert erro_enf is None
    assert novo_enf["nivel"] == NIVEL_ENFERMEIRO

    # Médico tenta cadastrar outro médico -> bloqueado
    _, _, erro_med = cadastrar_usuario(
        usuarios,
        nivel_ator=NIVEL_MEDICO,
        nome="Dr. Outro Médico",
        nivel_novo=NIVEL_MEDICO,
        registro="CRM/SP 999999",
        especialidade="Clínica",
    )
    assert erro_med is not None

    # Médico edita enfermeiro -> permitido
    usuarios, erro_edit = editar_usuario(
        usuarios,
        nivel_ator=NIVEL_MEDICO,
        id_ator="USR-002",
        id_alvo=novo_enf["id"],
        nome="Enf. Bruno Dias Atualizado",
        registro="COREN/SP 778899-ENF",
        especialidade="Triagem Clínica (Human-in-the-Loop)",
        cpf="123.456.789-00",
        endereco="Rua das Flores, 100 - Centro",
    )
    assert erro_edit is None

    # Médico tenta remover diretor -> bloqueado
    _, erro_rem_dir = remover_usuario(
        usuarios,
        nivel_ator=NIVEL_MEDICO,
        id_ator="USR-002",
        id_alvo="USR-001",
    )
    assert erro_rem_dir is not None


def test_enfermeiro_possui_apenas_acesso_hitl_e_encaminha_para_medico():
    usuarios = clonar_usuarios_iniciais()
    docs = clonar_documentos_pre_triados_iniciais()

    assert not pode_analisar_documentos_da_enfermagem(NIVEL_ENFERMEIRO)
    assert pode_analisar_documentos_da_enfermagem(NIVEL_MEDICO)
    assert pode_analisar_documentos_da_enfermagem(NIVEL_DIRETOR)

    # Enfermeiro não pode cadastrar ninguém
    _, _, erro_cad = cadastrar_usuario(
        usuarios,
        nivel_ator=NIVEL_ENFERMEIRO,
        nome="Enf. Novo",
        nivel_novo=NIVEL_ENFERMEIRO,
        registro="COREN/SP 111",
        especialidade="Triagem",
    )
    assert erro_cad is not None

    # Enfermeiro encaminha documento revisado no Human-in-the-Loop para análise médica
    docs, erro_hitl = encaminhar_hitl_enfermagem(
        docs,
        nome_enfermeiro="Enf. Lucas Ferreira",
        registro_enfermeiro="COREN/SP 451920",
        documento_id="DOC-HITL-2026-0999",
        paciente="Paciente Teste, 50 anos",
        tipo_documento="Receituário Médico",
        prioridade="Urgente",
        nota_enfermagem="CRM e posologia conferidos na imagem.",
    )
    assert erro_hitl is None
    assert docs[0]["documento_id"] == "DOC-HITL-2026-0999"
    assert docs[0]["status_revisao"] == "Aguardando análise médica"

    # Médico analisa o documento que o enfermeiro passou
    docs, erro_med = registrar_analise_medica(
        docs,
        nivel_ator=NIVEL_MEDICO,
        nome_medico="Dra. Ana Silva",
        registro_medico="CRM/SP 142857",
        documento_id="DOC-HITL-2026-0999",
        decisao="Aprovado pelo médico",
        parecer="Validado e liberado para dispensação.",
    )
    assert erro_med is None
    assert docs[0]["status_revisao"] == "Aprovado pelo médico"


def test_pagina_usuario_renderiza_nos_tres_niveis_de_acesso():
    at = AppTest.from_file(str(PAGINA_USUARIO), default_timeout=30)
    at.session_state["mediflow_autenticado"] = True
    at.session_state["mediflow_jwt_token"] = "mock.jwt.valido"
    at.session_state["mediflow_usuario_logado"] = {
        "id": "USR-001",
        "nome": "Dr. Roberto Almeida",
        "email": "roberto.almeida@mediflow.com.br",
        "nivel": NIVEL_DIRETOR,
    }
    at.run()
    assert not at.exception
    assert at.title[0].value == "Usuário & Controle de Acesso"
