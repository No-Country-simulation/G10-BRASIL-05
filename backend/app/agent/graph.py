"""Orquestração da triagem clínica e dos pontos de revisão humana."""

from typing import Any, Dict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agent.state import GraphState
from app.agent.nodes.avaliador import node_avaliacao
from app.agent.nodes.classificador import node_classificacao
from app.agent.nodes.extrator import node_extracao
from app.agent.nodes.filtro_elegibilidade import node_filtro_elegibilidade
from app.agent.nodes.finalizador import node_finalizador
from app.agent.nodes.ingestao import node_ingestao
from app.agent.nodes.qualidade_documento import node_qualidade_documento
from app.agent.nodes.revisao_humana import node_revisao_humana
from app.agent.nodes.roteador import node_roteamento
from app.agent.nodes.validador import node_validador


_grafo_compilado = None
_checkpointer = InMemorySaver()


def configurar_checkpointer(checkpointer: Any) -> None:
    """Injeta saver durável durante o lifespan da API e invalida o grafo em cache."""
    global _checkpointer, _grafo_compilado
    _checkpointer = checkpointer
    _grafo_compilado = None


def _apos_preflight(state: GraphState) -> str:
    return "revisao_humana" if state.get("elegibilidade") == "incerto" else "qualidade"


def _apos_qualidade(state: GraphState) -> str:
    qualidade = state.get("qualidade_documento") or {}
    return "classificacao" if qualidade.get("status") == "adequada" else "revisao_humana"


def _apos_validacao(state: GraphState) -> str:
    return "avaliacao" if state.get("status") == "validado" else "revisao_humana"


def _apos_avaliacao(state: GraphState) -> str:
    return "revisao_humana" if state.get("requer_auditoria_humana") else "roteamento"


def _apos_revisao(state: GraphState) -> str:
    decisao = state.get("decisao_humana") or {}
    acao = decisao.get("status_aprovacao")
    if acao in {"rejeitado", "solicitar_reenvio"}:
        return "finalizador"
    etapa = state.get("etapa_revisao")
    if etapa == "elegibilidade":
        return "qualidade" if state.get("elegibilidade") == "medico" else "finalizador"
    if etapa == "qualidade":
        return "classificacao" if (state.get("qualidade_documento") or {}).get("status") == "adequada" else "finalizador"
    if etapa == "validacao":
        return "avaliacao"
    if etapa == "risco":
        return "roteamento"
    return "finalizador"


def criar_grafo_triagem():
    """Constrói o StateGraph com ramificações e pausa retomável por thread_id."""
    global _grafo_compilado
    if _grafo_compilado is not None:
        return _grafo_compilado

    workflow = StateGraph(GraphState)
    workflow.add_node("continuacao", lambda state: state)
    workflow.add_node("qualidade", node_qualidade_documento)
    workflow.add_node("classificacao", node_classificacao)
    workflow.add_node("extracao", node_extracao)
    workflow.add_node("validacao", node_validador)
    workflow.add_node("avaliacao", node_avaliacao)
    workflow.add_node("revisao_humana", node_revisao_humana)
    workflow.add_node("roteamento", node_roteamento)
    workflow.add_node("finalizador", node_finalizador)

    workflow.add_edge(START, "continuacao")
    workflow.add_conditional_edges("continuacao", _apos_preflight)
    workflow.add_conditional_edges("qualidade", _apos_qualidade)
    workflow.add_edge("classificacao", "extracao")
    workflow.add_edge("extracao", "validacao")
    workflow.add_conditional_edges("validacao", _apos_validacao)
    workflow.add_conditional_edges("avaliacao", _apos_avaliacao)
    workflow.add_conditional_edges("revisao_humana", _apos_revisao)
    workflow.add_edge("roteamento", "finalizador")
    workflow.add_edge("finalizador", END)

    _grafo_compilado = workflow.compile(checkpointer=_checkpointer)
    return _grafo_compilado


def _thread_config(estado: GraphState) -> dict[str, Any]:
    thread_id = estado.get("documento_id") or str(uuid4())
    return {"configurable": {"thread_id": str(thread_id)}}


def executar_agente_triagem(estado_inicial: Dict[str, Any]) -> GraphState:
    """Executa até a saída final ou até uma pausa explícita para revisão humana."""
    # O filtro prévio roda sem checkpoint: conteúdo não médico não deve ser persistido.
    admissibilidade = StateGraph(GraphState)
    admissibilidade.add_node("ingestao", node_ingestao)
    admissibilidade.add_node("elegibilidade", node_filtro_elegibilidade)
    admissibilidade.add_edge(START, "ingestao")
    admissibilidade.add_edge("ingestao", "elegibilidade")
    admissibilidade.add_edge("elegibilidade", END)
    estado = admissibilidade.compile().invoke(estado_inicial)

    if estado.get("elegibilidade") == "nao_medico":
        return node_finalizador(estado)

    return criar_grafo_triagem().invoke(estado, config=_thread_config(estado))


def retomar_agente_triagem(documento_id: str, decisao: Dict[str, Any]) -> GraphState:
    """Retoma o checkpoint do documento após receber uma decisão humana validada."""
    grafo = criar_grafo_triagem()
    config = {"configurable": {"thread_id": str(documento_id)}}
    snapshot = grafo.get_state(config)
    if not snapshot.next or "revisao_humana" not in snapshot.next:
        raise ValueError("Não há checkpoint de revisão humana ativo para este documento.")
    return grafo.invoke(Command(resume=decisao), config=config)


def excluir_checkpoint_triagem(documento_id: str) -> None:
    """Remove o estado transitório quando a revisão conclui que o arquivo está fora do escopo."""
    _checkpointer.delete_thread(str(documento_id))
