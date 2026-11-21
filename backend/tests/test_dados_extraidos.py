import pytest
from pydantic import ValidationError

from app.schemas.dados_extraidos import DadosExtraidos


def test_valida_dados_extraidos_completos():
    dados = DadosExtraidos.model_validate(
        {
            "paciente": {"nome": "Maria Silva", "idade": 52},
            "medico_solicitante": {"nome": "João Souza", "crm_uf": "12345-SP"},
            "exame_realizado": "Tomografia de tórax",
            "diagnostico_principal": "Tromboembolismo pulmonar",
            "cid_sugerido": "I26.9",
            "medicamentos": [
                {"medicamento": "Apixabana", "dosagem": "5 mg"},
                {"medicamento": "Dipirona", "dosagem": "500 mg"},
            ],
        }
    )

    assert dados.paciente is not None
    assert dados.paciente.nome == "Maria Silva"
    assert dados.paciente.idade == 52
    assert dados.medico_solicitante is not None
    assert dados.medico_solicitante.nome == "João Souza"
    assert dados.medico_solicitante.crm_uf == "12345-SP"
    assert dados.exame_realizado == "Tomografia de tórax"
    assert dados.diagnostico_principal == "Tromboembolismo pulmonar"
    assert dados.cid_sugerido == "I26.9"
    assert len(dados.medicamentos) == 2
    assert dados.medicamentos[0].medicamento == "Apixabana"
    assert dados.medicamentos[0].dosagem == "5 mg"


def test_aceita_todos_os_campos_ausentes():
    dados = DadosExtraidos.model_validate({})

    assert dados.paciente is None
    assert dados.medico_solicitante is None
    assert dados.exame_realizado is None
    assert dados.diagnostico_principal is None
    assert dados.cid_sugerido is None
    assert dados.medicamentos == []


def test_aceita_medico_e_medicamento_com_subcampos_ausentes():
    dados = DadosExtraidos.model_validate(
        {
            "medico_solicitante": {},
            "medicamentos": [{}, {"medicamento": "Dipirona"}],
        }
    )

    assert dados.medico_solicitante is not None
    assert dados.medico_solicitante.nome is None
    assert dados.medico_solicitante.crm_uf is None
    assert dados.medicamentos[0].medicamento is None
    assert dados.medicamentos[0].dosagem is None
    assert dados.medicamentos[1].medicamento == "Dipirona"
    assert dados.medicamentos[1].dosagem is None


def test_ignora_campos_extras_da_llm_no_schema_e_nos_modelos_filhos():
    dados = DadosExtraidos.model_validate(
        {
            "achados_criticos": ["campo adicional"],
            "metodo": "llm_generativa",
            "paciente": {"nome": "Maria Silva", "registro": "extra"},
            "medico_solicitante": {"nome": "João Souza", "uf": "SP"},
            "medicamentos": [{"medicamento": "AAS", "frequencia": "8/8h"}],
        }
    )

    assert dados.paciente.nome == "Maria Silva"
    assert dados.medico_solicitante.nome == "João Souza"
    assert dados.medicamentos[0].medicamento == "AAS"


@pytest.mark.parametrize(
    "payload",
    [
        {"paciente": 123},
        {"paciente": {"idade": 52.5}},
        {"paciente": {"idade": True}},
        {"medico_solicitante": "João Souza"},
        {"medicamentos": {"medicamento": "Dipirona"}},
        {"medicamentos": [{"dosagem": 500}]},
    ],
)
def test_rejeita_tipos_invalidos(payload):
    with pytest.raises(ValidationError):
        DadosExtraidos.model_validate(payload)
