import json

import pytest

from app.agent.nodes.classificador import (
    SCORE_DOCUMENTO_NAO_IDENTIFICADO,
    SCORE_MAXIMO_FALLBACK,
    criar_node_classificacao,
)
from app.schemas.classificacao import ClassificacaoDocumento

DOCUMENTOS_POR_TIPO = {
    "RECEITA": (
        "Receituário Médico - Clínica Médica\n"
        "Uso oral: Losartana Potássica 50mg - Tomar 1 comprimido pela manhã."
    ),
    "LAUDO": (
        "Laudo de Tomografia Computadorizada de Tórax\n"
        "Conclusão: Falha de enchimento em artéria pulmonar, compatível com Tromboembolismo Pulmonar Agudo."
    ),
    "GUIA_TISS": (
        "Guia TISS - Solicitação de Autorização de Procedimento\n"
        "Procedimento: Colecistectomia videolaparoscópica. Código TUSS 31005497."
    ),
    "RELATORIO_ALTA": (
        "Relatório de Alta Hospitalar\n"
        "Internado por pneumonia comunitária, tratado com antibioticoterapia. Alta em bom estado geral."
    ),
    "ATESTADO": (
        "Atestado Médico\n"
        "Atesto para os devidos fins que o paciente necessita de 3 dias de afastamento para repouso."
    ),
}


def _cliente_llm_fixo(resposta: str):
    mensagens_recebidas = []

    def cliente(mensagens):
        mensagens_recebidas.append(mensagens)
        return resposta

    cliente.mensagens_recebidas = mensagens_recebidas
    return cliente


def _cliente_llm_com_erro(mensagens):
    raise RuntimeError("timeout simulado do provedor LLM")


def _resposta_llm(tipo: str, prioridade: str = "ROTINA", score: float = 0.92) -> str:
    return json.dumps(
        {
            "tipo_documento": tipo,
            "nivel_prioridade": prioridade,
            "especialidade": "Clinica Medica",
            "score_confianca_classificacao": score,
        }
    )


@pytest.mark.parametrize("tipo", DOCUMENTOS_POR_TIPO.keys())
def test_classifica_os_5_tipos_via_llm(tipo):
    cliente = _cliente_llm_fixo(_resposta_llm(tipo))
    node = criar_node_classificacao(cliente)

    resultado = node({"documento_texto": DOCUMENTOS_POR_TIPO[tipo]})

    assert resultado["tipo_documento"] == tipo
    assert resultado["nivel_prioridade"] == "ROTINA"
    assert resultado["score_confianca_classificacao"] == 0.92
    assert resultado["classificacao"]["metodo"] == "llm_generativa"
    assert resultado["status"] == "classificado"
    assert DOCUMENTOS_POR_TIPO[tipo] in cliente.mensagens_recebidas[0][1][1]


@pytest.mark.parametrize("tipo", DOCUMENTOS_POR_TIPO.keys())
def test_classifica_os_5_tipos_via_fallback_heuristico(tipo):
    node = criar_node_classificacao(None)

    resultado = node({"documento_texto": DOCUMENTOS_POR_TIPO[tipo]})

    assert resultado["tipo_documento"] == tipo
    assert resultado["classificacao"]["metodo"] == "fallback_heuristico"
    assert resultado["score_confianca_classificacao"] <= SCORE_MAXIMO_FALLBACK


@pytest.mark.parametrize("tipo", DOCUMENTOS_POR_TIPO.keys())
def test_saida_do_no_respeita_schema_pydantic(tipo):
    node = criar_node_classificacao(None)

    resultado = node({"documento_texto": DOCUMENTOS_POR_TIPO[tipo]})

    dados = {chave: valor for chave, valor in resultado["classificacao"].items() if chave != "metodo"}
    ClassificacaoDocumento.model_validate(dados)


def test_aceita_resposta_llm_em_bloco_markdown():
    resposta = f"```json\n{_resposta_llm('LAUDO', 'EMERGENCIA', 0.97)}\n```"
    node = criar_node_classificacao(_cliente_llm_fixo(resposta))

    resultado = node({"documento_texto": DOCUMENTOS_POR_TIPO["LAUDO"]})

    assert resultado["tipo_documento"] == "LAUDO"
    assert resultado["nivel_prioridade"] == "EMERGENCIA"
    assert resultado["classificacao"]["metodo"] == "llm_generativa"


@pytest.mark.parametrize(
    "resposta_invalida",
    [
        _resposta_llm("EXAME_SANGUE"),
        _resposta_llm("RECEITA", prioridade="Urgente"),
        _resposta_llm("RECEITA", score=1.5),
        "Não consegui classificar este documento.",
        "{json quebrado",
    ],
)
def test_resposta_llm_fora_do_schema_aciona_fallback(resposta_invalida):
    node = criar_node_classificacao(_cliente_llm_fixo(resposta_invalida))

    resultado = node({"documento_texto": DOCUMENTOS_POR_TIPO["RECEITA"]})

    assert resultado["tipo_documento"] == "RECEITA"
    assert resultado["classificacao"]["metodo"] == "fallback_heuristico"


def test_falha_na_chamada_da_llm_aciona_fallback():
    node = criar_node_classificacao(_cliente_llm_com_erro)

    resultado = node({"documento_texto": DOCUMENTOS_POR_TIPO["ATESTADO"]})

    assert resultado["tipo_documento"] == "ATESTADO"
    assert resultado["classificacao"]["metodo"] == "fallback_heuristico"


def test_fallback_marca_emergencia_para_termo_critico():
    node = criar_node_classificacao(None)

    resultado = node({"documento_texto": DOCUMENTOS_POR_TIPO["LAUDO"]})

    assert resultado["nivel_prioridade"] == "EMERGENCIA"


def test_fallback_nao_confunde_termo_critico_dentro_de_palavra():
    node = criar_node_classificacao(None)

    resultado = node({"documento_texto": "Receita: uso oral de vitamina D. Paciente reside em Diamantina."})

    assert resultado["nivel_prioridade"] == "ROTINA"


def test_documento_nao_identificado_nao_inventa_tipo():
    node = criar_node_classificacao(None)

    resultado = node({"documento_texto": "Texto ilegível sem paciente e sem CRM.", "erros": []})

    assert resultado["classificacao"] is None
    assert resultado["tipo_documento"] is None
    assert resultado["score_confianca_classificacao"] == SCORE_DOCUMENTO_NAO_IDENTIFICADO
    assert "Tipo de documento não identificado na classificação." in resultado["erros"]
