import pytest

from app.schemas.classificacao import TipoDocumento
from app.schemas.dados_extraidos import DadosExtraidos
from app.agent.nodes.validadores_clinicos import (
    validar_cid10,
    validar_crm,
    validar_dados_extraidos,
    validar_idade_plausivel,
)


@pytest.mark.parametrize(
    "crm",
    [
        "CRM 00108769",
        "CRM-00108769",
        "CRM/SP 145892",
        "CRM-SP 145892",
        "145892-SP",
        "145892",
        "crm-sp 145892",
        " 145892-sp ",
    ],
)
def test_aceita_formatos_de_crm_previstos(crm):
    assert validar_crm(crm)


@pytest.mark.parametrize(
    "crm",
    ["", "SP-145892", "CRM-XX 145892", "CRM-SP abc", 145892],
)
def test_rejeita_formatos_de_crm_invalidos(crm):
    assert not validar_crm(crm)


def test_aceita_crm_ausente_quando_nao_exigido():
    assert validar_crm(None)


@pytest.mark.parametrize("cid", ["I26.9", "R69", "U07.1", "a00.0", " J18.9 "])
def test_aceita_sintaxe_cid10_valida(cid):
    assert validar_cid10(cid)


@pytest.mark.parametrize(
    "cid",
    ["", "I2.9", "I260.9", "I26.", "I26.123", "CID-10 I26.9", 269],
)
def test_rejeita_sintaxe_cid10_invalida(cid):
    assert not validar_cid10(cid)


def test_aceita_cid10_ausente():
    assert validar_cid10(None)


@pytest.mark.parametrize("idade", [0, 1, 52, 120])
def test_aceita_idade_plausivel(idade):
    assert validar_idade_plausivel(idade)


@pytest.mark.parametrize("idade", [-1, 121, 52.5, True, "52"])
def test_rejeita_idade_implausivel(idade):
    assert not validar_idade_plausivel(idade)


def test_aceita_idade_ausente():
    assert validar_idade_plausivel(None)


@pytest.mark.parametrize(
    ("tipo_documento", "payload"),
    [
        (
            TipoDocumento.RECEITA,
            {
                "paciente": {"nome": "Ana Silva", "idade": 40},
                "medico_solicitante": {"nome": "Dr. João", "crm_uf": "CRM-SP 145892"},
                "medicamentos": [{"medicamento": "Dipirona", "dosagem": "500 mg"}],
            },
        ),
        (
            TipoDocumento.LAUDO,
            {"paciente": {"nome": "Ana Silva"}, "exame_realizado": "Hemograma"},
        ),
        (
            TipoDocumento.GUIA_TISS,
            {
                "paciente": {"nome": "Ana Silva"},
                "medico_solicitante": {"nome": "Dr. João", "crm_uf": "145892-SP"},
                "exame_realizado": "Hemograma",
            },
        ),
        (
            TipoDocumento.RELATORIO_ALTA,
            {
                "paciente": {"nome": "Ana Silva"},
                "diagnostico_principal": "Pneumonia",
            },
        ),
        (
            TipoDocumento.ATESTADO,
            {
                "paciente": {"nome": "Ana Silva"},
                "medico_solicitante": {"nome": "Dra. Maria", "crm_uf": "CRM-SP 145892"},
            },
        ),
    ],
)
def test_aceita_campos_obrigatorios_por_tipo(tipo_documento, payload):
    dados = DadosExtraidos.model_validate(payload)

    assert validar_dados_extraidos(dados, tipo_documento) == []


@pytest.mark.parametrize("tipo_documento", list(TipoDocumento))
def test_mensagem_de_paciente_ausente_e_legivel(tipo_documento):
    erros = validar_dados_extraidos(DadosExtraidos(), tipo_documento)

    assert "Nome do paciente não identificado no documento." in erros
    assert all("paciente.nome" not in erro for erro in erros)


def test_receita_exige_medicamento_com_nome_e_dosagem():
    dados = DadosExtraidos.model_validate(
        {
            "paciente": {"nome": "Ana Silva"},
            "medico_solicitante": {"nome": "Dr. João", "crm_uf": "145892-SP"},
            "medicamentos": [{"medicamento": "Dipirona"}],
        }
    )

    assert "Medicamento e dosagem não identificados na receita." in (
        validar_dados_extraidos(dados, TipoDocumento.RECEITA)
    )


def test_acumula_erros_de_crm_cid_idade_e_campos_obrigatorios():
    dados = DadosExtraidos.model_validate(
        {
            "paciente": {"nome": "Ana Silva", "idade": 121},
            "medico_solicitante": {"nome": "Dr. João", "crm_uf": "CRM-XX 12"},
            "exame_realizado": "Tomografia",
            "cid_sugerido": "I26.123",
        }
    )

    erros = validar_dados_extraidos(dados, TipoDocumento.GUIA_TISS)

    assert "O CRM do médico solicitante está em formato inválido." in erros
    assert "O CID informado está em formato inválido." in erros
    assert "A idade do paciente deve estar entre 0 e 120 anos." in erros
    assert all("." not in erro.split(" ", 3)[0] for erro in erros)
    assert len(erros) == 3


@pytest.mark.parametrize(
    ("tipo_documento", "campo_esperado"),
    [
        (TipoDocumento.RECEITA, "Nome do médico solicitante não identificado no documento."),
        (TipoDocumento.RECEITA, "CRM do médico solicitante não identificado no documento."),
        (TipoDocumento.RECEITA, "Medicamento e dosagem não identificados na receita."),
        (TipoDocumento.LAUDO, "Exame realizado não identificado no documento."),
        (TipoDocumento.GUIA_TISS, "Nome do médico solicitante não identificado no documento."),
        (TipoDocumento.GUIA_TISS, "CRM do médico solicitante não identificado no documento."),
        (TipoDocumento.GUIA_TISS, "Exame realizado não identificado no documento."),
        (TipoDocumento.RELATORIO_ALTA, "Diagnóstico principal não identificado no documento."),
        (TipoDocumento.ATESTADO, "Nome do médico solicitante não identificado no documento."),
        (TipoDocumento.ATESTADO, "CRM do médico solicitante não identificado no documento."),
    ],
)
def test_rejeita_campo_essencial_ausente_por_tipo(tipo_documento, campo_esperado):
    dados = DadosExtraidos.model_validate({"paciente": {"nome": "Ana Silva"}})

    erros = validar_dados_extraidos(dados, tipo_documento)

    assert campo_esperado in erros
    assert all("." not in erro.split(" ", 3)[0] for erro in erros)


def test_campos_opcionais_ausentes_nao_invalidam_documento():
    dados = DadosExtraidos.model_validate(
        {
            "paciente": {"nome": "Ana Silva"},
            "diagnostico_principal": "Pneumonia",
        }
    )

    assert validar_dados_extraidos(dados, TipoDocumento.RELATORIO_ALTA) == []
