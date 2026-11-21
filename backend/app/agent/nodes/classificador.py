import json
from typing import Any

from app.agent.harness import texto_clinico_sem_metadados
from app.agent.llm import ClienteLLM, obter_cliente_llm
from app.agent.prompts.classificacao import (
    PROMPT_CLASSIFICACAO_SYSTEM,
    PROMPT_CLASSIFICACAO_USER,
)
from app.agent.state import GraphState
from app.schemas.classificacao import ClassificacaoDocumento


LIMITE_CARACTERES_PROMPT = 4000


def _extrair_json(resposta: str) -> dict[str, Any]:
    """Extrai e valida o objeto JSON retornado pela LLM."""
    inicio, fim = resposta.find("{"), resposta.rfind("}")
    if inicio == -1 or fim < inicio:
        raise ValueError("Resposta da LLM não contém um objeto JSON.")
    dados = json.loads(resposta[inicio : fim + 1])
    return ClassificacaoDocumento.model_validate(dados).model_dump(mode="json")


def criar_node_classificacao(cliente_llm: ClienteLLM):
    """Cria o nó de classificação, interrompendo o fluxo se a LLM falhar."""

    def node_classificacao(state: GraphState) -> GraphState:
        texto = texto_clinico_sem_metadados(state["documento_texto"])
        mensagens = [
            ("system", PROMPT_CLASSIFICACAO_SYSTEM),
            (
                "human",
                PROMPT_CLASSIFICACAO_USER.format(
                    documento_texto=texto[:LIMITE_CARACTERES_PROMPT]
                ),
            ),
        ]
        classificacao = ClassificacaoDocumento.model_validate(
            _extrair_json(cliente_llm(mensagens))
        ).model_dump(mode="json")
        return {
            **state,
            "classificacao": {**classificacao, "metodo": "llm_generativa"},
            "tipo_documento": classificacao["tipo_documento"],
            "especialidade": classificacao["especialidade"],
            "nivel_prioridade": classificacao["nivel_prioridade"],
            "score_confianca_classificacao": classificacao[
                "score_confianca_classificacao"
            ],
            "status": "classificado",
        }

    return node_classificacao


def node_classificacao(state: GraphState) -> GraphState:
    """Nó padrão instanciado com o cliente LLM configurado."""
    return criar_node_classificacao(obter_cliente_llm())(state)
