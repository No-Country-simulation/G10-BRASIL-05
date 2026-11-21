import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent.nodes import extrator
from app.agent.nodes.identificacao import _parsear_identificacao
from app.agent.nodes.validador import node_validador
from app.agent.normalizacao_texto import normalizar_cpf
from app.models.triagem import Base, PacienteModel
from app.repositories.pacientes import PacientesRepository
from app.schemas.dados_extraidos import DadosExtraidos


@pytest.fixture(autouse=True)
def autenticar_clientes_de_teste():
    """Este módulo testa CPF isoladamente e não precisa inicializar a API global."""
    yield


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("682.276.396-15", "68227639615"),
        ("68227639615", "68227639615"),
        ("123.456.789-00", "12345678900"),
        (None, None),
        ("12.345", None),
        ("CPF ilegível", None),
        (12345678901, None),
    ],
)
def test_normaliza_cpf_para_digitos_com_11_posicoes(entrada, esperado):
    assert normalizar_cpf(entrada) == esperado


def test_identificacao_normaliza_cpf_formatado_da_llm():
    identificacao = _parsear_identificacao(
        json.dumps(
            {
                "paciente_nome": "Maria Gomes",
                "paciente_cpf": "682.276.396-15",
                "paciente_idade": 61,
                "medico_nome": None,
                "medico_crm": None,
            }
        )
    )

    assert identificacao["paciente"]["cpf"] == "68227639615"


def test_identificacao_descarta_cpf_invalido_da_llm():
    identificacao = _parsear_identificacao(
        json.dumps(
            {
                "paciente_nome": "Maria Gomes",
                "paciente_cpf": "123.45",
                "paciente_idade": None,
                "medico_nome": None,
                "medico_crm": None,
            }
        )
    )

    assert identificacao["paciente"]["cpf"] is None


@pytest.mark.parametrize(
    ("cpf_texto", "cpf_llm"),
    [
        ("CPF: 682.276.396-15", "68227639615"),
        ("CPF: 68227639615", "682.276.396-15"),
    ],
)
def test_extracao_e_validador_preservam_cpf_com_pontuacao_diferente(
    monkeypatch, cpf_texto, cpf_llm
):
    documento = f"Paciente: Maria Gomes - {cpf_texto}\nLaudo do exame: Hemograma completo."
    resposta_llm = {
        "paciente_nome": "Maria Gomes",
        "paciente_cpf": cpf_llm,
        "paciente_idade": None,
        "medico_nome": None,
        "medico_crm": None,
        "exame_realizado": "Hemograma completo",
        "diagnostico_principal": None,
        "cid_sugerido": None,
        "medicamentos": [],
    }

    class Resposta:
        content = json.dumps(resposta_llm)

    class Cliente:
        def invoke(self, *_args, **_kwargs):
            return Resposta()

    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: Cliente())
    extraido = extrator.node_extracao(
        {
            "documento_texto": documento,
            "identificacao_documento": {
                "paciente": {"nome": "Maria Gomes", "cpf": None, "idade": None},
                "medico_solicitante": {},
            },
        }
    )

    assert extraido["dados_extraidos"]["paciente"]["cpf"] == "68227639615"
    validado = node_validador(
        {
            **extraido,
            "documento_texto": documento,
            "tipo_documento": "LAUDO",
            "tipo_arquivo": "imagem",
        }
    )

    assert validado["dados_extraidos"]["paciente"]["cpf"] == "68227639615"
    assert validado["evidencias_campos"]["paciente.cpf"]["status"] == "trecho_encontrado"
    assert "paciente.cpf" not in validado["campos_bloqueados"]
    DadosExtraidos.model_validate(validado["dados_extraidos"])


def test_schema_exige_cpf_em_11_digitos_puros():
    dados = DadosExtraidos.model_validate({"paciente": {"cpf": "68227639615"}})

    assert dados.paciente.cpf == "68227639615"


def test_repositorio_persiste_cpf_sem_pontuacao():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        paciente = PacientesRepository(sessao).obter_ou_criar_paciente(
            nome="Maria Gomes",
            cpf="682.276.396-15",
        )
        sessao.flush()
        salvo = sessao.query(PacienteModel).filter_by(id=paciente.id).one()

        assert salvo.cpf == "68227639615"
