import pytest

from utils.auditoria import (
    DECISAO_APROVAR,
    DECISAO_CORRIGIR,
    DECISAO_REJEITAR,
    calcular_correcoes,
    extrair_valores_editaveis,
    montar_decisao,
    validar_decisao,
)

ACOES = [DECISAO_APROVAR, DECISAO_REJEITAR, DECISAO_CORRIGIR]
CORRECAO = {"crm": "145892-SP"}


def _correcoes_para(acao: str) -> dict:
    return CORRECAO if acao == DECISAO_CORRIGIR else {}


def test_extrai_valores_do_formato_do_briefing():
    documento = {
        "dados_extraidos": {
            "paciente": {"nome": "Maria", "idade": 34},
            "medico_solicitante": {"nome": "Dr. Paulo", "crm": "123456-SP"},
            "diagnostico_principal": "Faringite aguda",
            "cid_sugerido": "J02.9",
        }
    }

    assert extrair_valores_editaveis(documento) == {
        "paciente_nome": "Maria",
        "medico_nome": "Dr. Paulo",
        "crm": "123456-SP",
        "diagnostico_principal": "Faringite aguda",
        "cid_sugerido": "J02.9",
    }


def test_extrai_valores_do_formato_do_schema():
    documento = {
        "dados_extraidos": {
            "paciente": "Maria Silva",
            "medico_solicitante": {"nome": "João Souza", "crm_uf": "12345-SP"},
        }
    }

    valores = extrair_valores_editaveis(documento)

    assert valores["paciente_nome"] == "Maria Silva"
    assert valores["crm"] == "12345-SP"


def test_extrai_valores_vazios_quando_os_dados_estao_ausentes():
    valores = extrair_valores_editaveis({})

    assert set(valores.values()) == {""}


def test_calcula_apenas_os_campos_alterados():
    atuais = {"crm": "", "medico_nome": "Dr. Paulo"}
    editados = {"crm": "145892-SP", "medico_nome": "Dr. Paulo"}

    assert calcular_correcoes(atuais, editados) == {"crm": "145892-SP"}


def test_ignora_espacos_nas_bordas_ao_comparar():
    assert calcular_correcoes({"crm": "145892-SP"}, {"crm": "  145892-SP  "}) == {}


def test_guarda_o_valor_corrigido_sem_espacos_nas_bordas():
    assert calcular_correcoes({"crm": ""}, {"crm": "  145892-SP "}) == {"crm": "145892-SP"}


@pytest.mark.parametrize("acao", ACOES)
def test_exige_identificacao_do_auditor(acao):
    problema = validar_decisao(acao, "  ", "motivo", _correcoes_para(acao))

    assert problema == "Informe a identificação do auditor."


@pytest.mark.parametrize("acao", [DECISAO_REJEITAR, DECISAO_CORRIGIR])
def test_rejeitar_e_corrigir_exigem_justificativa(acao):
    problema = validar_decisao(acao, "Dra. Ana", "  ", _correcoes_para(acao))

    assert problema == f"Informe a justificativa para {acao.lower()} o documento."


def test_aprovar_nao_exige_justificativa():
    assert validar_decisao(DECISAO_APROVAR, "Dra. Ana", "", {}) is None


def test_corrigir_exige_ao_menos_uma_correcao():
    problema = validar_decisao(DECISAO_CORRIGIR, "Dra. Ana", "motivo", {})

    assert problema == "Altere ao menos um campo para corrigir."


@pytest.mark.parametrize("acao", [DECISAO_APROVAR, DECISAO_REJEITAR])
def test_aprovar_e_rejeitar_recusam_campos_alterados(acao):
    problema = validar_decisao(acao, "Dra. Ana", "motivo", CORRECAO)

    assert problema == "Você alterou campos. Use 'Corrigir' para enviar as correções ou desfaça as alterações."


@pytest.mark.parametrize(
    "acao, justificativa, correcoes",
    [
        (DECISAO_APROVAR, "", {}),
        (DECISAO_REJEITAR, "Dados ilegíveis", {}),
        (DECISAO_CORRIGIR, "CRM conferido", CORRECAO),
    ],
)
def test_aceita_decisoes_completas(acao, justificativa, correcoes):
    assert validar_decisao(acao, "Dra. Ana", justificativa, correcoes) is None


def test_aprovar_nao_leva_correcoes():
    decisao = montar_decisao(DECISAO_APROVAR, "Dra. Ana", "", CORRECAO)

    assert decisao == {
        "decisao": "APROVADO",
        "dados_corrigidos": {},
        "justificativa": "",
        "auditor": "Dra. Ana",
    }


def test_rejeitar_marca_o_documento_como_rejeitado():
    decisao = montar_decisao(DECISAO_REJEITAR, "Dra. Ana", "Dados ilegíveis", {})

    assert decisao["decisao"] == "REJEITADO"
    assert decisao["dados_corrigidos"] == {}


def test_corrigir_aprova_com_os_dados_corrigidos():
    decisao = montar_decisao(DECISAO_CORRIGIR, "Dra. Ana", "CRM conferido", CORRECAO)

    assert decisao["decisao"] == "APROVADO"
    assert decisao["dados_corrigidos"] == CORRECAO


def test_remove_espacos_do_auditor_e_da_justificativa():
    decisao = montar_decisao(DECISAO_APROVAR, "  Dra. Ana ", "  ok  ", {})

    assert decisao["auditor"] == "Dra. Ana"
    assert decisao["justificativa"] == "ok"