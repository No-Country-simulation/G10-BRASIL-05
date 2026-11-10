from copy import deepcopy

import pytest

from utils.auditoria import (
    DECISAO_APROVAR,
    DECISAO_CORRIGIR,
    DECISAO_REJEITAR,
    aplicar_correcoes,
    calcular_correcoes,
    extrair_valores_editaveis,
    montar_decisao,
    montar_rotulo_da_fila,
    ordenar_fila,
    validar_decisao,
)

ACOES = [DECISAO_APROVAR, DECISAO_REJEITAR, DECISAO_CORRIGIR]
CORRECAO = {"crm": "145892-SP"}
DADOS = {
    "paciente": {"nome": "Maria", "idade": 34},
    "medico_solicitante": {"nome": "Dr. Paulo", "crm": None},
    "diagnostico_principal": "Faringite aguda",
    "cid_sugerido": "J02.9",
}


def _correcoes_para(acao: str) -> dict:
    return CORRECAO if acao == DECISAO_CORRIGIR else {}


def test_extrai_valores_do_formato_do_backend():
    item = {
        "dados_extraidos": {
            "paciente": {"nome": "Maria", "idade": 34},
            "medico_solicitante": {"nome": "Dr. Paulo", "crm": "123456-SP"},
            "diagnostico_principal": "Faringite aguda",
            "cid_sugerido": "J02.9",
        }
    }

    assert extrair_valores_editaveis(item) == {
        "paciente_nome": "Maria",
        "medico_nome": "Dr. Paulo",
        "crm": "123456-SP",
        "diagnostico_principal": "Faringite aguda",
        "cid_sugerido": "J02.9",
    }


def test_extrai_valores_do_formato_do_schema_do_p1():
    item = {
        "dados_extraidos": {
            "paciente": "Maria Silva",
            "medico_solicitante": {"nome": "João Souza", "crm_uf": "12345-SP"},
        }
    }

    valores = extrair_valores_editaveis(item)

    assert valores["paciente_nome"] == "Maria Silva"
    assert valores["crm"] == "12345-SP"


def test_extrai_valores_vazios_quando_os_dados_estao_ausentes():
    assert set(extrair_valores_editaveis({}).values()) == {""}


def test_calcula_apenas_os_campos_alterados():
    atuais = {"crm": "", "medico_nome": "Dr. Paulo"}
    editados = {"crm": "145892-SP", "medico_nome": "Dr. Paulo"}

    assert calcular_correcoes(atuais, editados) == {"crm": "145892-SP"}


def test_ignora_espacos_nas_bordas_ao_comparar():
    assert calcular_correcoes({"crm": "145892-SP"}, {"crm": "  145892-SP  "}) == {}


def test_guarda_o_valor_corrigido_sem_espacos_nas_bordas():
    assert calcular_correcoes({"crm": ""}, {"crm": "  145892-SP "}) == {"crm": "145892-SP"}


def test_aplicar_correcoes_preserva_o_que_nao_mudou():
    corrigidos = aplicar_correcoes(DADOS, CORRECAO)

    assert corrigidos["medico_solicitante"] == {"nome": "Dr. Paulo", "crm": "145892-SP"}
    assert corrigidos["paciente"] == {"nome": "Maria", "idade": 34}
    assert corrigidos["diagnostico_principal"] == "Faringite aguda"
    assert corrigidos["cid_sugerido"] == "J02.9"


def test_aplicar_correcoes_nao_altera_o_original():
    original = deepcopy(DADOS)

    aplicar_correcoes(DADOS, CORRECAO)

    assert DADOS == original


def test_aplicar_correcoes_cria_o_medico_quando_ausente():
    corrigidos = aplicar_correcoes({}, {"crm": "145892-SP", "medico_nome": "Dra. Ana"})

    assert corrigidos["medico_solicitante"] == {"nome": "Dra. Ana", "crm": "145892-SP"}


def test_aplicar_correcoes_atualiza_diagnostico_e_cid():
    corrigidos = aplicar_correcoes(
        DADOS, {"diagnostico_principal": "Amigdalite", "cid_sugerido": "J03.9"}
    )

    assert corrigidos["diagnostico_principal"] == "Amigdalite"
    assert corrigidos["cid_sugerido"] == "J03.9"


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


@pytest.mark.parametrize(
    "acao, status_esperado",
    [
        (DECISAO_APROVAR, "aprovado"),
        (DECISAO_REJEITAR, "rejeitado"),
        (DECISAO_CORRIGIR, "corrigido"),
    ],
)
def test_status_segue_o_contrato_da_api(acao, status_esperado):
    decisao = montar_decisao(acao, "Dra. Ana", "motivo", DADOS, _correcoes_para(acao))

    assert decisao["status_aprovacao"] == status_esperado


@pytest.mark.parametrize("acao", [DECISAO_APROVAR, DECISAO_REJEITAR])
def test_aprovar_e_rejeitar_nao_enviam_dados_corrigidos(acao):
    decisao = montar_decisao(acao, "Dra. Ana", "motivo", DADOS, {})

    assert decisao["dados_corrigidos"] is None


def test_corrigir_envia_os_dados_extraidos_completos_ja_corrigidos():
    decisao = montar_decisao(DECISAO_CORRIGIR, "Dra. Ana", "CRM conferido", DADOS, CORRECAO)

    assert decisao["dados_corrigidos"]["medico_solicitante"]["crm"] == "145892-SP"
    assert decisao["dados_corrigidos"]["paciente"] == {"nome": "Maria", "idade": 34}
    assert decisao["dados_corrigidos"]["cid_sugerido"] == "J02.9"


def test_decisao_tem_exatamente_os_campos_do_contrato():
    decisao = montar_decisao(DECISAO_APROVAR, "Dra. Ana", "", DADOS, {})

    assert set(decisao) == {"status_aprovacao", "auditor_nome", "justificativa", "dados_corrigidos"}


def test_remove_espacos_do_auditor_e_da_justificativa():
    decisao = montar_decisao(DECISAO_APROVAR, "  Dra. Ana ", "  ok  ", DADOS, {})

    assert decisao["auditor_nome"] == "Dra. Ana"
    assert decisao["justificativa"] == "ok"

def test_aplicar_correcoes_mantem_paciente_como_texto_quando_veio_como_texto():
    corrigidos = aplicar_correcoes({"paciente": "Maria Silva"}, {"paciente_nome": "Maria Souza"})

    assert corrigidos["paciente"] == "Maria Souza"


def test_aplicar_correcoes_preserva_a_idade_ao_corrigir_o_nome():
    corrigidos = aplicar_correcoes(DADOS, {"paciente_nome": "Maria Souza"})

    assert corrigidos["paciente"] == {"nome": "Maria Souza", "idade": 34}


def test_aplicar_correcoes_escreve_o_crm_no_campo_em_que_ele_veio():
    dados = {"medico_solicitante": {"nome": "João", "crm_uf": "12345-SP"}}

    corrigidos = aplicar_correcoes(dados, {"crm": "99999-SP"})

    assert corrigidos["medico_solicitante"] == {"nome": "João", "crm_uf": "99999-SP"}


def test_aplicar_correcoes_nao_cria_medico_sem_correcao_do_medico():
    corrigidos = aplicar_correcoes({}, {"cid_sugerido": "J03.9"})

    assert "medico_solicitante" not in corrigidos


def _item(documento_id: str, prioridade: str | None, score: float | None, criado_em: str = "2026-10-27T09:00:00") -> dict:
    return {
        "documento_id": documento_id,
        "nivel_prioridade": prioridade,
        "score_confianca": score,
        "created_at": criado_em,
    }


def _ids(fila: list[dict]) -> list[str]:
    return [item["documento_id"] for item in fila]


def test_ordena_de_emergencia_para_rotina():
    fila = [_item("A", "ROTINA", 0.5), _item("B", "URGENTE", 0.5), _item("C", "EMERGENCIA", 0.5)]

    assert _ids(ordenar_fila(fila)) == ["C", "B", "A"]


def test_ordena_prioridade_em_qualquer_formato_de_texto():
    fila = [_item("A", "Rotina", 0.5), _item("B", "Urgente", 0.5), _item("C", "Emergência", 0.5)]

    assert _ids(ordenar_fila(fila)) == ["C", "B", "A"]


def test_desempata_pela_menor_confianca():
    fila = [_item("A", "URGENTE", 0.9), _item("B", "URGENTE", 0.4)]

    assert _ids(ordenar_fila(fila)) == ["B", "A"]


def test_desempata_pelo_mais_antigo():
    fila = [
        _item("NOVO", "URGENTE", 0.5, "2026-10-27T10:00:00"),
        _item("ANTIGO", "URGENTE", 0.5, "2026-10-27T08:00:00"),
    ]

    assert _ids(ordenar_fila(fila)) == ["ANTIGO", "NOVO"]


def test_prioridade_desconhecida_fica_entre_urgente_e_rotina():
    fila = [_item("A", "ROTINA", 0.5), _item("B", "Indefinido", 0.5), _item("C", "URGENTE", 0.5)]

    assert _ids(ordenar_fila(fila)) == ["C", "B", "A"]


def test_ordena_sem_quebrar_com_campos_ausentes():
    fila = [{"documento_id": "A"}, {"documento_id": "B"}]

    assert sorted(_ids(ordenar_fila(fila))) == ["A", "B"]


def test_ordenar_nao_altera_a_lista_original():
    fila = [_item("A", "ROTINA", 0.5), _item("B", "EMERGENCIA", 0.5)]

    ordenar_fila(fila)

    assert _ids(fila) == ["A", "B"]


def test_rotulo_mostra_a_prioridade():
    assert montar_rotulo_da_fila(_item("DOC-1", "EMERGENCIA", 0.5)) == "DOC-1 · Emergência"


def test_rotulo_sem_prioridade_mostra_so_o_codigo():
    assert montar_rotulo_da_fila(_item("DOC-1", None, 0.5)) == "DOC-1"
