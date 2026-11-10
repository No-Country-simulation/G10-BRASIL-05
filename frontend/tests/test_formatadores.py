import pytest

from utils.formatadores import (
    NIVEL_AVISO,
    NIVEL_ERRO,
    NIVEL_SUCESSO,
    crm_do_medico,
    descrever_armazenamento,
    nome_do_paciente,
    normalizar_prioridade,
    rotular_prioridade,
    rotular_tipo_documento,
)


@pytest.mark.parametrize(
    "codigo, rotulo",
    [
        ("RECEITA", "Receituário Médico"),
        ("LAUDO", "Laudo de Exame"),
        ("GUIA_TISS", "Guia TISS"),
        ("RELATORIO_ALTA", "Relatório de Alta"),
        ("ATESTADO", "Atestado Médico"),
    ],
)
def test_traduz_codigo_do_tipo_de_documento(codigo, rotulo):
    assert rotular_tipo_documento(codigo) == rotulo


@pytest.mark.parametrize(
    "codigo, rotulo",
    [("ROTINA", "Rotina"), ("URGENTE", "Urgente"), ("EMERGENCIA", "Emergência")],
)
def test_traduz_codigo_da_prioridade(codigo, rotulo):
    assert rotular_prioridade(codigo) == rotulo


def test_mantem_o_texto_quando_nao_e_um_codigo_conhecido():
    assert rotular_tipo_documento("Laudo de Exame de Imagem") == "Laudo de Exame de Imagem"
    assert rotular_prioridade("Urgente") == "Urgente"


def test_aceita_valor_ausente():
    assert rotular_tipo_documento(None) is None
    assert rotular_prioridade(None) is None

@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("ROTINA", "ROTINA"),
        ("Rotina", "ROTINA"),
        ("urgente", "URGENTE"),
        ("  Urgente ", "URGENTE"),
        ("Emergência", "EMERGENCIA"),
        ("EMERGENCIA", "EMERGENCIA"),
        ("Indefinido", None),
        ("", None),
        (None, None),
    ],
)
def test_normaliza_a_prioridade_ignorando_caixa_e_acentos(valor, esperado):
    assert normalizar_prioridade(valor) == esperado


@pytest.mark.parametrize(
    "valor, rotulo",
    [("Rotina", "Rotina"), ("urgente", "Urgente"), ("Emergência", "Emergência"), ("Indefinido", "Indefinido")],
)
def test_rotula_a_prioridade_em_qualquer_formato(valor, rotulo):
    assert rotular_prioridade(valor) == rotulo


@pytest.mark.parametrize(
    "paciente, esperado",
    [({"nome": "Maria", "idade": 34}, "Maria"), ("Maria Silva", "Maria Silva"), ({}, None), (None, None)],
)
def test_le_o_nome_do_paciente_em_objeto_ou_texto(paciente, esperado):
    assert nome_do_paciente(paciente) == esperado


@pytest.mark.parametrize(
    "medico, esperado",
    [({"crm": "145892-SP"}, "145892-SP"), ({"crm_uf": "12345-SP"}, "12345-SP"), ({"crm": None}, None), ({}, None)],
)
def test_le_o_crm_em_qualquer_um_dos_dois_campos(medico, esperado):
    assert crm_do_medico(medico) == esperado


@pytest.mark.parametrize(
    "status, nivel",
    [
        ("sucesso", NIVEL_SUCESSO),
        ("SUCESSO", NIVEL_SUCESSO),
        ("sucesso_local", NIVEL_AVISO),
        ("sucesso (local_simulado)", NIVEL_AVISO),
        ("falha: conexão recusada", NIVEL_ERRO),
        ("Falha", NIVEL_ERRO),
        ("algo novo", NIVEL_AVISO),
        (None, NIVEL_AVISO),
    ],
)
def test_classifica_o_status_do_backup(status, nivel):
    armazenamento = {"bucket": "mediflow", "caminho_objeto": "processados/DOC-1.json", "status_backup": status}

    assert descrever_armazenamento(armazenamento)[0] == nivel


def test_armazenamento_com_sucesso_mostra_bucket_e_caminho():
    armazenamento = {"bucket": "mediflow", "caminho_objeto": "processados/DOC-1.json", "status_backup": "sucesso"}

    assert descrever_armazenamento(armazenamento)[1] == "Documento salvo em mediflow/processados/DOC-1.json"


def test_falha_de_backup_nao_vaza_o_erro_interno():
    armazenamento = {"status_backup": "falha: /etc/segredo permission denied", "caminho_objeto": "x.json"}

    assert "segredo" not in descrever_armazenamento(armazenamento)[1]


@pytest.mark.parametrize("armazenamento", [None, {}])
def test_sem_informacao_de_armazenamento_nao_mostra_nada(armazenamento):
    assert descrever_armazenamento(armazenamento) is None
