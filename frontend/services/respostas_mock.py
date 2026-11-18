"""Carregamento dos fixtures fictícios mantidos em arquivos JSON separados."""

import json
from pathlib import Path
from typing import Any

PASTA_DOS_MOCKS = Path(__file__).resolve().parents[1] / "data" / "mocks"


def _carregar_json(nome: str) -> Any:
    caminho = PASTA_DOS_MOCKS / nome
    with caminho.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


RESPOSTA_ROTINA = _carregar_json("triagem_rotina.json")
RESPOSTA_URGENCIA = _carregar_json("triagem_urgencia.json")
RESPOSTA_AMBIGUA = _carregar_json("triagem_ambigua.json")
HISTORICO_MOCK = _carregar_json("historico.json")
FILA_AUDITORIA_MOCK = _carregar_json("fila_auditoria.json")
