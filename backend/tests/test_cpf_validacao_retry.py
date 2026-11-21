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


def test_cpf_invalido_e_reextraido_com_sucesso(monkeypatch, tmp_path):
    imagem = _criar_imagem(tmp_path / "documento.jpg")

    class Cliente:
        chamadas = 0
        imagem_retry = None

        def invoke(self, mensagens, **_kwargs):
            self.chamadas += 1
            if self.chamadas == 1:
                return Resposta(_resposta_extracao(CPF_INVALIDO))
            self.imagem_retry = mensagens[0].content[1]["image_url"]["url"]
            if self.chamadas == 2:
                return Resposta(json.dumps({"paciente_cpf": CPF_INVALIDO}))
            return Resposta(json.dumps({"paciente_cpf": CPF_VALIDO}))

    cliente = Cliente()
    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: cliente)

    resultado = extrator.node_extracao(_estado(imagem))
    validado = node_validador(resultado)

    assert cliente.chamadas == 3
    assert validado["dados_extraidos"]["paciente"]["cpf"] == CPF_VALIDO
    assert validado["evidencias_campos"]["paciente.cpf"]["status"] == "releitura_visual"
    imagem_retry = base64.b64decode(cliente.imagem_retry.split(",", 1)[1])
    with Image.open(io.BytesIO(imagem_retry)) as imagem_preparada:
        # Sem coordenadas confiáveis, o retry usa a página inteira ampliada.
        assert imagem_preparada.size == (200, 100)


def test_cpf_invalido_apos_tentativas_e_encaminhado_para_revisao(monkeypatch, tmp_path):
    imagem = _criar_imagem(tmp_path / "documento.jpg")

    class Cliente:
        chamadas = 0

        def invoke(self, *_args, **_kwargs):
            self.chamadas += 1
            conteudo = _resposta_extracao(CPF_INVALIDO) if self.chamadas == 1 else json.dumps(
                {"paciente_cpf": CPF_INVALIDO}
            )
            return Resposta(conteudo)

    cliente = Cliente()
    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: cliente)
    extraido = extrator.node_extracao(_estado(imagem))
    validado = node_validador(extraido)

    assert cliente.chamadas == extrator.MAX_TENTATIVAS_RELEITURA_CPF + 1
    assert extraido["dados_extraidos"]["paciente"]["cpf"] is None
    assert validado["requer_auditoria_humana"] is True
    assert validado["etapa_revisao"] == "validacao"
    assert "CPF válido" in validado["motivo_revisao"]
    assert "10 tentativas" in validado["motivo_revisao"]


def test_cpf_ausente_nao_faz_retry(monkeypatch):
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
    assert resultado["cpf_validacao_falhou"] is True


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


@pytest.mark.parametrize("falha", ["imagem", "llm"])
def test_falha_no_retry_exige_revisao_sem_repetir(monkeypatch, tmp_path, falha):
    imagem = _criar_imagem(tmp_path / "documento.jpg")

    class Cliente:
        chamadas = 0

        def invoke(self, *_args, **_kwargs):
            self.chamadas += 1
            if self.chamadas == 1:
                return Resposta(_resposta_extracao(CPF_INVALIDO))
            raise RuntimeError("falha simulada")

    cliente = Cliente()
    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: cliente)
    if falha == "imagem":
        monkeypatch.setattr(
            extrator,
            "preparar_imagem_para_releitura",
            lambda _conteudo: (_ for _ in ()).throw(ValueError("imagem inválida")),
        )

    resultado = extrator.node_extracao(_estado(imagem))

    chamadas_esperadas = 1 if falha == "imagem" else extrator.MAX_TENTATIVAS_RELEITURA_CPF + 1
    assert cliente.chamadas == chamadas_esperadas
    assert resultado["dados_extraidos"]["paciente"]["cpf"] is None
    assert resultado["cpf_validacao_falhou"] is True


def test_candidato_invalido_sem_imagem_disponivel_exige_revisao(monkeypatch):
    class Cliente:
        chamadas = 0

        def invoke(self, *_args, **_kwargs):
            self.chamadas += 1
            return Resposta(_resposta_extracao(CPF_INVALIDO))

    cliente = Cliente()
    monkeypatch.setattr(extrator, "obter_cliente_llm", lambda: cliente)

    resultado = extrator.node_extracao(_estado(""))

    assert cliente.chamadas == 1
    assert resultado["dados_extraidos"]["paciente"]["cpf"] is None

