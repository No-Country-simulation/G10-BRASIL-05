import pytest

from utils.formatadores import rotular_prioridade, rotular_tipo_documento


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