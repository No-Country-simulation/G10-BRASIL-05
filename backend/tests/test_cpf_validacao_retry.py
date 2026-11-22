import json
import base64
import io

import pytest
from PIL import Image

from app.agent.nodes import extrator
from app.agent.nodes.validador import node_validador
from app.agent.normalizacao_texto import validar_cpf


CPF_VALIDO = "52998224725"
CPF_INVALIDO = "52998224724"


@pytest.fixture(autouse=True)
def autenticar_clientes_de_teste():
    """Estes testes isolados não precisam inicializar o banco da API global."""
    yield


@pytest.mark.parametrize(
    ("cpf", "esperado"),
    [
        (CPF_VALIDO, True),
        ("529.982.247-25", True),
        (CPF_INVALIDO, False),
        ("1234567890", False),
        ("11111111111", False),
        (None, False),
    ],
)
def test_validar_cpf(cpf, esperado):
    assert validar_cpf(cpf) is esperado


def _resposta_extracao(cpf):
    return json.dumps({
        "paciente_nome": "Maria Gomes",
        "paciente_cpf": cpf,
        "paciente_idade": None,
        "medico_nome": None,
        "medico_crm": None,
        "exame_realizado": "Hemograma",
        "diagnostico_principal": None,
        "cid_sugerido": None,
        "medicamentos": [],
    })


class Resposta:
    def __init__(self, content):
        self.content = content


def _estado(caminho_imagem):
    return {
        "documento_texto": "Paciente: Maria Gomes. CPF ilegível.",
        "tipo_arquivo": "imagem",
        "referencia_fonte": str(caminho_imagem),
        "identificacao_documento": {"paciente": {}, "medico_solicitante": {}},
    }


def _criar_imagem(caminho):
    Image.new("RGB", (100, 50), "white").save(caminho, format="JPEG")
    return caminho


def test_cpf_invalido_mantem_valor_e_nao_exige_revisao(monkeypatch, tmp_path):
    """CPF presente (mesmo sem passar no dígito verificador) é mantido e não força revisão."""
    imagem = _criar_imagem(tmp_path / "documento.jpg")

    class Cliente:
        chamadas = 0

        def invoke(self, *_args, **_kwargs):
            self.chamadas += 1
            return Resposta(_resposta_extracao(CPF_INVALIDO))

    cliente = Cliente()
    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: cliente)
    extraido = extrator.node_extracao(_estado(imagem))
    validado = node_validador(extraido)

    assert extraido["dados_extraidos"]["paciente"]["cpf"] == CPF_INVALIDO
    assert extraido["cpf_validacao_falhou"] is False
    assert "CPF" not in (validado.get("motivo_revisao") or "")


def test_cpf_ausente_nao_exige_revisao(monkeypatch):
    """CPF ausente não força falha de validação nem bloqueia triagem."""
    class Cliente:
        chamadas = 0

        def invoke(self, *_args, **_kwargs):
            self.chamadas += 1
            return Resposta(_resposta_extracao(None))

    cliente = Cliente()
    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: cliente)

    resultado = extrator.node_extracao({
        "documento_texto": "Laudo de exame.",
        "tipo_arquivo": "imagem",
        "identificacao_documento": {"paciente": {}, "medico_solicitante": {}},
    })

    assert cliente.chamadas == 1
    assert resultado["dados_extraidos"]["paciente"]["cpf"] is None
    assert resultado["cpf_validacao_falhou"] is False


def test_cpf_ausente_na_extracao_inicial_e_encontrado_no_retry(monkeypatch, tmp_path):
    imagem = _criar_imagem(tmp_path / "documento.jpg")

    class Cliente:
        chamadas = 0

        def invoke(self, *_args, **_kwargs):
            self.chamadas += 1
            cpf = None if self.chamadas == 1 else CPF_VALIDO
            conteudo = _resposta_extracao(cpf) if self.chamadas == 1 else json.dumps(
                {"paciente_cpf": cpf}
            )
            return Resposta(conteudo)

    cliente = Cliente()
    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: cliente)

    resultado = extrator.node_extracao(_estado(imagem))

    assert cliente.chamadas == 2
    assert resultado["dados_extraidos"]["paciente"]["cpf"] == CPF_VALIDO
    assert resultado["cpf_validacao_falhou"] is False

