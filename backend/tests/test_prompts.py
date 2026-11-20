import re

import pytest

from app.agent.nodes.classificador import criar_node_classificacao
from app.agent.nodes.extrator import criar_node_extracao
from app.agent.prompts import classificacao, extracao, transcricao
from app.schemas.classificacao import ClassificacaoDocumento
from app.schemas.dados_extraidos import DadosExtraidos

PADRAO_VERSAO_SEMANTICA = re.compile(r"^\d+\.\d+\.\d+$")


@pytest.mark.parametrize("modulo", [classificacao, extracao, transcricao])
def test_prompt_declara_versao_semantica(modulo):
    assert PADRAO_VERSAO_SEMANTICA.fullmatch(modulo.VERSAO)


@pytest.mark.parametrize("modulo", [classificacao, extracao, transcricao])
def test_versao_do_prompt_registrada_no_changelog(modulo):
    from pathlib import Path

    changelog = (Path(modulo.__file__).parent / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"### {modulo.VERSAO} " in changelog


@pytest.mark.parametrize("documento, resposta", classificacao.EXEMPLOS)
def test_exemplos_de_classificacao_respeitam_schema(documento, resposta):
    ClassificacaoDocumento.model_validate(resposta)
    assert documento in classificacao.PROMPT_CLASSIFICACAO_SYSTEM


@pytest.mark.parametrize("documento, resposta", extracao.EXEMPLOS)
def test_exemplos_de_extracao_respeitam_schema(documento, resposta):
    DadosExtraidos.model_validate(resposta)
    assert documento in extracao.PROMPT_EXTRACAO_SYSTEM


@pytest.mark.parametrize("documento, resposta", extracao.EXEMPLOS)
def test_exemplos_de_extracao_nao_inventam_cid(documento, resposta):
    cid = resposta["cid_sugerido"]
    assert cid is None or cid in documento


def test_prompt_de_extracao_proibe_deduzir_cid():
    assert "não deduza o código" in extracao.PROMPT_EXTRACAO_SYSTEM


def test_prompts_de_usuario_aceitam_documento_com_chaves():
    texto = 'Documento com {"chaves"} no conteúdo'

    assert texto in classificacao.PROMPT_CLASSIFICACAO_USER.format(documento_texto=texto)
    assert texto in extracao.PROMPT_EXTRACAO_USER.format(documento_texto=texto)


def test_classificacao_registra_versao_do_prompt():
    resposta = '{"tipo_documento": "RECEITA", "nivel_prioridade": "ROTINA", "especialidade": "X", "score_confianca_classificacao": 0.9}'
    node = criar_node_classificacao(lambda mensagens: resposta)

    resultado = node({"documento_texto": "Receita: uso oral"})

    assert resultado["classificacao"]["versao_prompt"] == classificacao.VERSAO


def test_extracao_registra_versao_do_prompt():
    resposta = '{"paciente": null, "medico_solicitante": null, "exame_realizado": null, "diagnostico_principal": null, "cid_sugerido": null, "medicamentos": []}'
    node = criar_node_extracao(lambda mensagens: resposta)

    resultado = node({"documento_texto": "Texto qualquer"})

    assert resultado["dados_extraidos"]["versao_prompt"] == extracao.VERSAO


def test_fallback_nao_registra_versao_de_prompt():
    resultado = criar_node_classificacao(None)({"documento_texto": "Receita: uso oral"})

    assert resultado["classificacao"]["versao_prompt"] is None
