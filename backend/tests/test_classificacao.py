import pytest
from pydantic import ValidationError
from app.schemas.classificacao import (
    ClassificacaoDocumento,
    TipoDocumento,
    NivelPrioridade
)

def test_classificacao_valida():
    dados = {
        "tipo_documento": "LAUDO",
        "nivel_prioridade": "EMERGENCIA",
        "especialidade": "Cardiologia",
        "score_confianca_classificacao": 0.95
    }
    classificacao = ClassificacaoDocumento(**dados)
    assert classificacao.tipo_documento == TipoDocumento.LAUDO
    assert classificacao.nivel_prioridade == NivelPrioridade.EMERGENCIA
    assert classificacao.especialidade == "Cardiologia"
    assert classificacao.score_confianca_classificacao == 0.95

def test_classificacao_tipo_documento_invalido():
    dados = {
        "tipo_documento": "EXAME_SANGUE",
        "nivel_prioridade": "ROTINA",
        "especialidade": "Clínica Geral",
        "score_confianca_classificacao": 0.8
    }
    with pytest.raises(ValidationError):
        ClassificacaoDocumento(**dados)

def test_classificacao_score_invalido_maior_que_um():
    dados = {
        "tipo_documento": "RECEITA",
        "nivel_prioridade": "ROTINA",
        "especialidade": "Dermatologia",
        "score_confianca_classificacao": 1.5
    }
    with pytest.raises(ValidationError):
        ClassificacaoDocumento(**dados)

def test_classificacao_score_invalido_menor_que_zero():
    dados = {
        "tipo_documento": "RECEITA",
        "nivel_prioridade": "ROTINA",
        "especialidade": "Dermatologia",
        "score_confianca_classificacao": -0.1
    }
    with pytest.raises(ValidationError):
        ClassificacaoDocumento(**dados)

def test_classificacao_especialidade_muito_longa():
    dados = {
        "tipo_documento": "GUIA_TISS",
        "nivel_prioridade": "URGENTE",
        "especialidade": "A" * 101,
        "score_confianca_classificacao": 0.9
    }
    with pytest.raises(ValidationError):
        ClassificacaoDocumento(**dados)