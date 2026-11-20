import json

import pytest

from app.agent.nodes.extrator import criar_node_extracao
from app.schemas.dados_extraidos import DadosExtraidos

RECEITA = (
    "Receituário Médico - Clínica Médica\n"
    "Paciente: Fulano de Teste, 35 anos. Médico: Dr. Ciclano Exemplo CRM: 87654-SP.\n"
    "Uso oral: Losartana Potássica 50mg - Tomar 1 comprimido pela manhã.\n"
    "Diagnóstico: Hipertensão Arterial Sistêmica. CID: I10"
)

LAUDO_SEM_CID = (
    "Laudo de Tomografia Computadorizada\n"
    "Paciente: Beltrana de Teste, 52 anos. Médico: Dra. Fulana Exemplo CRM: 145892-SP.\n"
    "Conclusão: Falha de enchimento compatível com Tromboembolismo Pulmonar Agudo (TEP)."
)


def _cliente_llm_fixo(resposta: str):
    def cliente(mensagens):
        return resposta

    return cliente


def _cliente_llm_com_erro(mensagens):
    raise RuntimeError("timeout simulado do provedor LLM")


def _resposta_receita(**sobrescritas) -> str:
    dados = {
        "paciente": {"nome": "Fulano de Teste", "idade": 35},
        "medico_solicitante": {"nome": "Dr. Ciclano Exemplo", "crm_uf": "87654-SP"},
        "exame_realizado": None,
        "diagnostico_principal": "Hipertensão Arterial Sistêmica",
        "cid_sugerido": "I10",
        "medicamentos": [{"medicamento": "Losartana Potássica", "dosagem": "50mg"}],
    }
    dados.update(sobrescritas)
    return json.dumps(dados)


def test_extrai_entidades_via_llm():
    node = criar_node_extracao(_cliente_llm_fixo(_resposta_receita()))

    resultado = node({"documento_texto": RECEITA})

    assert resultado["paciente"] == {"nome": "Fulano de Teste", "idade": 35}
    assert resultado["medico_solicitante"] == {"nome": "Dr. Ciclano Exemplo", "crm_uf": "87654-SP"}
    assert resultado["cid_sugerido"] == "I10"
    assert resultado["medicamentos"] == [{"medicamento": "Losartana Potássica", "dosagem": "50mg"}]
    assert resultado["dados_extraidos"]["metodo"] == "llm_generativa"
    assert resultado["status"] == "extraido"


def test_descarta_valores_da_llm_que_nao_estao_no_documento():
    resposta = _resposta_receita(
        paciente={"nome": "Paciente Identificado", "idade": 35},
        medico_solicitante={"nome": "Médico Identificado", "crm_uf": "999999-RJ"},
        cid_sugerido="Z00.0",
        medicamentos=[
            {"medicamento": "Losartana Potássica", "dosagem": "50mg"},
            {"medicamento": "Dipirona", "dosagem": "500mg"},
        ],
    )
    node = criar_node_extracao(_cliente_llm_fixo(resposta))

    resultado = node({"documento_texto": RECEITA})

    assert resultado["paciente"]["nome"] is None
    assert resultado["medico_solicitante"] == {"nome": None, "crm_uf": None}
    assert resultado["cid_sugerido"] is None
    assert resultado["medicamentos"] == [{"medicamento": "Losartana Potássica", "dosagem": "50mg"}]


@pytest.mark.parametrize(
    "resposta_invalida",
    [
        _resposta_receita(campo_extra="não previsto"),
        _resposta_receita(paciente={"nome": "Fulano de Teste", "idade": "trinta"}),
        "Não encontrei dados.",
        "{json quebrado",
    ],
)
def test_resposta_llm_fora_do_schema_aciona_fallback(resposta_invalida):
    node = criar_node_extracao(_cliente_llm_fixo(resposta_invalida))

    resultado = node({"documento_texto": RECEITA})

    assert resultado["dados_extraidos"]["metodo"] == "regex_heuristico"
    assert resultado["paciente"]["nome"] == "Fulano de Teste"


def test_falha_na_chamada_da_llm_aciona_fallback():
    node = criar_node_extracao(_cliente_llm_com_erro)

    resultado = node({"documento_texto": RECEITA})

    assert resultado["dados_extraidos"]["metodo"] == "regex_heuristico"


def test_fallback_extrai_campos_escritos_no_documento():
    node = criar_node_extracao(None)

    resultado = node({"documento_texto": RECEITA})

    assert resultado["paciente"] == {"nome": "Fulano de Teste", "idade": 35}
    assert resultado["medico_solicitante"] == {"nome": "Dr. Ciclano Exemplo", "crm_uf": "87654-SP"}
    assert resultado["diagnostico_principal"] == "Hipertensão Arterial Sistêmica"
    assert resultado["cid_sugerido"] == "I10"
    assert resultado["medicamentos"] == [{"medicamento": "Losartana Potássica", "dosagem": "50mg"}]


def test_fallback_nao_deduz_cid_a_partir_do_diagnostico():
    node = criar_node_extracao(None)

    resultado = node({"documento_texto": LAUDO_SEM_CID})

    assert "Tromboembolismo" in resultado["diagnostico_principal"]
    assert resultado["exame_realizado"] == "Tomografia Computadorizada"
    assert resultado["cid_sugerido"] is None


def test_crm_sem_uf_fica_nulo():
    node = criar_node_extracao(None)

    resultado = node({"documento_texto": "Paciente: Fulano de Teste. Dr. Ciclano Exemplo CRM 87654."})

    assert resultado["medico_solicitante"]["crm_uf"] is None


def test_documento_sem_dados_deixa_campos_nulos():
    node = criar_node_extracao(None)

    resultado = node({"documento_texto": "Texto ilegível sem paciente e sem CRM."})

    assert resultado["paciente"] == {"nome": None, "idade": None}
    assert resultado["medico_solicitante"] == {"nome": None, "crm_uf": None}
    assert resultado["exame_realizado"] is None
    assert resultado["diagnostico_principal"] is None
    assert resultado["cid_sugerido"] is None
    assert resultado["medicamentos"] == []


@pytest.mark.parametrize("texto", [RECEITA, LAUDO_SEM_CID, "Texto ilegível."])
def test_saida_do_no_respeita_schema_pydantic(texto):
    node = criar_node_extracao(None)

    resultado = node({"documento_texto": texto})

    dados = {chave: valor for chave, valor in resultado["dados_extraidos"].items() if chave not in ("metodo", "versao_prompt")}
    DadosExtraidos.model_validate(dados)
