"""Grafo de decisão do agente autônomo clínico com LangGraph (SCRUM-35).

Orquestra os nós de Ingestão, Transcrição (OCR), Classificação, Extração, Avaliação e Roteamento.
"""

from typing import Any, Callable, Dict
from langgraph.graph import StateGraph, START, END
from app.agent.state import GraphState
from app.agent.nodes.ingestao import node_ingestao
from app.agent.nodes.transcricao import node_transcricao
from app.agent.nodes.classificador import node_classificacao
from app.agent.nodes.extrator import node_extracao
from app.agent.nodes.avaliador import node_avaliacao
from app.agent.nodes.roteador import node_roteamento

# Compilação singleton do grafo para reaproveitamento eficiente em memória
_grafo_compilado = None


def _proximo_apos_ingestao(state: GraphState) -> str:
    """Documentos sem texto legível passam pelo OCR multimodal antes da classificação (SCRUM-96)."""
    return "transcricao" if state.get("requer_ocr") else "classificacao"


def construir_grafo_triagem(transcricao: Callable[[GraphState], GraphState] = node_transcricao):
    """Constrói e compila o StateGraph; o nó de transcrição pode ser substituído nos testes."""
    workflow = StateGraph(GraphState)

    # 1. Registro dos nós de decisão
    workflow.add_node("ingestao", node_ingestao)
    workflow.add_node("transcricao", transcricao)
    workflow.add_node("classificacao", node_classificacao)
    workflow.add_node("extracao", node_extracao)
    workflow.add_node("avaliacao", node_avaliacao)
    workflow.add_node("roteamento", node_roteamento)

    # 2. Definição do fluxo e arestas sequenciais
    workflow.add_edge(START, "ingestao")
    workflow.add_conditional_edges("ingestao", _proximo_apos_ingestao, ["transcricao", "classificacao"])
    workflow.add_edge("transcricao", "classificacao")
    workflow.add_edge("classificacao", "extracao")
    workflow.add_edge("extracao", "avaliacao")
    workflow.add_edge("avaliacao", "roteamento")
    workflow.add_edge("roteamento", END)

    return workflow.compile()


def criar_grafo_triagem():
    """Retorna o grafo de triagem compilado, reaproveitando a mesma instância em memória."""
    global _grafo_compilado
    if _grafo_compilado is None:
        _grafo_compilado = construir_grafo_triagem()
    return _grafo_compilado


def executar_agente_triagem(estado_inicial: Dict[str, Any]) -> GraphState:
    """Executa o ciclo completo do agente autônomo LangGraph sobre o documento de entrada."""
    grafo = criar_grafo_triagem()
    return grafo.invoke(estado_inicial)
