import pytest

from utils.formatadores import (
    crm_do_medico,
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
