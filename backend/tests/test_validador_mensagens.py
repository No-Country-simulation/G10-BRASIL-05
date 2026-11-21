import pytest

from app.agent.nodes.validador import node_validador


@pytest.fixture(autouse=True)
def autenticar_clientes_de_teste():
    """Os testes do nó de validação não precisam inicializar serviços da API."""
    yield


def _estado(tipo_arquivo="imagem", fonte_verificada_visualmente=False):
    return {
        "dados_extraidos": {
            "paciente": {"nome": "Ana Silva"},
            "exame_realizado": "Hemograma",
        },
        "documento_texto": "Paciente: Ana Silva. Exame realizado: Hemograma.",
        "tipo_documento": "LAUDO",
        "tipo_arquivo": tipo_arquivo,
        "referencia_fonte": "/storage/originais/documento",
        "fonte_verificada_visualmente": fonte_verificada_visualmente,
    }


def test_imagem_disponivel_nao_e_confundida_com_ocr_conferido():
    resultado = node_validador(_estado("imagem"))

    fonte = resultado["validacao_fonte"]
    assert fonte["fonte_original_disponivel"] is True
    assert fonte["fonte_verificada"] is False
    assert fonte["fonte_verificada_visualmente"] is False
    assert fonte["texto_ocr_eh_prova_da_imagem"] is False
    assert "Texto extraído do documento visual ainda precisa ser conferido no original." in resultado["motivo_revisao"]
    assert resultado["requer_auditoria_humana"] is True


def test_imagem_confirmada_visualmente_nao_recebe_motivo_de_fonte_pendente():
    resultado = node_validador(_estado("imagem", fonte_verificada_visualmente=True))

    fonte = resultado["validacao_fonte"]
    assert fonte["fonte_original_disponivel"] is True
    assert fonte["fonte_verificada"] is True
    assert fonte["fonte_verificada_visualmente"] is True
    assert resultado["motivo_revisao"] is None
    assert resultado["requer_auditoria_humana"] is False


def test_pdf_disponivel_exige_conferencia_visual_com_mensagem_clara():
    resultado = node_validador(_estado("pdf"))

    assert resultado["validacao_fonte"]["fonte_original_disponivel"] is True
    assert "Texto extraído do documento visual ainda precisa ser conferido no original." in resultado["motivo_revisao"]


def test_mensagens_de_schema_e_campos_ausentes_nao_expoem_termos_tecnicos():
    estado = _estado()
    estado["dados_extraidos"]["paciente"]["idade"] = "idade desconhecida"
    estado["dados_extraidos"].pop("exame_realizado")
    estado["documento_texto"] = ""

    resultado = node_validador(estado)
    motivo = resultado["motivo_revisao"]

    assert "Não foi possível validar os dados clínicos extraídos." in motivo
    assert "Nome do paciente não identificado no documento." in motivo
    assert "Exame realizado não identificado no documento." in motivo
    assert "Extra inputs are not permitted" not in motivo
    assert "paciente.nome" not in motivo
    assert "paciente.idade" not in motivo
