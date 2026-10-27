"""Grafo de decisão do agente autônomo clínico com LangGraph (SCRUM-35).

Orquestra os nós de Ingestão, Classificação, Extração, Avaliação e Roteamento.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.agent.state import GraphState
from app.agent.nodes.ingestao import node_ingestao
from app.agent.nodes.classificador import node_classificacao
from app.agent.nodes.extrator import node_extracao
from app.agent.nodes.avaliador import node_avaliacao
from app.agent.nodes.roteador import node_roteamento

# Compilação singleton do grafo para reaproveitamento eficiente em memória
_grafo_compilado = None


def criar_grafo_triagem():
    """Constrói e compila o StateGraph autônomo do agente de triagem clínica."""
    global _grafo_compilado
    if _grafo_compilado is not None:
        return _grafo_compilado

    workflow = StateGraph(GraphState)

    # 1. Registro dos nós de decisão
    workflow.add_node("ingestao", node_ingestao)
    workflow.add_node("classificacao", node_classificacao)
    workflow.add_node("extracao", node_extracao)
    workflow.add_node("avaliacao", node_avaliacao)
    workflow.add_node("roteamento", node_roteamento)

    # 2. Definição do fluxo e arestas sequenciais
    workflow.add_edge(START, "ingestao")
    workflow.add_edge("ingestao", "classificacao")
    workflow.add_edge("classificacao", "extracao")
    workflow.add_edge("extracao", "avaliacao")
    workflow.add_edge("avaliacao", "roteamento")
    workflow.add_edge("roteamento", END)

    _grafo_compilado = workflow.compile()
    return _grafo_compilado


def executar_agente_triagem(estado_inicial: Dict[str, Any]) -> GraphState:
    """Executa o ciclo completo do agente autônomo LangGraph sobre o documento de entrada."""
    grafo = criar_grafo_triagem()
    return grafo.invoke(estado_inicial)
