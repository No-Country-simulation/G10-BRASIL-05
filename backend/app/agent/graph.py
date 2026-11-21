"""Orquestração da triagem clínica e dos pontos de revisão humana."""

from typing import Any, Callable, Dict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agent.state import GraphState
from app.agent.nodes.avaliador import node_avaliacao
from app.agent.nodes.classificador import node_classificacao
from app.agent.nodes.extrator import node_extracao
from app.agent.nodes.filtro_elegibilidade import node_filtro_elegibilidade
from app.agent.nodes.finalizador import node_finalizador
from app.agent.nodes.ingestao import node_ingestao
from app.agent.nodes.identificacao import node_identificacao
from app.agent.nodes.qualidade_documento import node_qualidade_documento
from app.agent.nodes.revisao_humana import node_revisao_humana
from app.agent.nodes.roteador import node_roteamento
from app.agent.nodes.validador import node_validador


_grafo_compilado = None
_checkpointer = None


def configurar_checkpointer(checkpointer: Any) -> None:
    """Injeta saver durável durante o lifespan da API e invalida o grafo em cache."""
    global _checkpointer, _grafo_compilado
    _checkpointer = checkpointer
    _grafo_compilado = None


def _apos_preflight(state: GraphState) -> str:
    return "finalizador" if state.get("elegibilidade") in {"nao_medico", "incerto"} else "qualidade"


def _apos_qualidade(state: GraphState) -> str:
    qualidade = state.get("qualidade_documento") or {}
    return "identificacao" if qualidade.get("status") == "adequada" else "revisao_humana"


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


def criar_grafo_triagem(
    resolver_cadastro: Callable[[GraphState], Dict[str, Any]] | None = None,
    on_etapa: Callable[[str], None] | None = None,
):
    """Constrói o StateGraph; callbacks por trabalho não são compartilhados entre documentos."""
    global _grafo_compilado
    if resolver_cadastro is None and on_etapa is None and _grafo_compilado is not None:
        return _grafo_compilado
    if _checkpointer is None:
        raise RuntimeError("O checkpointer PostgreSQL não foi inicializado.")

    workflow = StateGraph(GraphState)
    workflow.add_node("continuacao", lambda state: state)
    workflow.add_node("qualidade", node_qualidade_documento)

    def executar_identificacao(state: GraphState) -> GraphState:
        if on_etapa:
            on_etapa("identificacao")
        return node_identificacao(state)

    def buscar_cadastro(state: GraphState) -> GraphState:
        atualizacoes = resolver_cadastro(state) if resolver_cadastro else {}
        if on_etapa:
            on_etapa("analise_clinica")
        return {**state, **atualizacoes, "etapa_atual": "analise_clinica"}

    workflow.add_node("identificacao", executar_identificacao)
    workflow.add_node("buscar_cadastro", buscar_cadastro)
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
    workflow.add_edge("identificacao", "buscar_cadastro")
    workflow.add_edge("buscar_cadastro", "classificacao")
    workflow.add_edge("classificacao", "extracao")
    workflow.add_edge("extracao", "validacao")
    workflow.add_conditional_edges("validacao", _apos_validacao)
    workflow.add_conditional_edges("avaliacao", _apos_avaliacao)
    workflow.add_conditional_edges("revisao_humana", _apos_revisao)
    workflow.add_edge("roteamento", "finalizador")
    workflow.add_edge("finalizador", END)

    grafo = workflow.compile(checkpointer=_checkpointer)
    if resolver_cadastro is None and on_etapa is None:
        _grafo_compilado = grafo
    return grafo


def _thread_config(estado: GraphState) -> dict[str, Any]:
    thread_id = estado.get("documento_id") or str(uuid4())
    return {"configurable": {"thread_id": str(thread_id)}}


def executar_agente_triagem(
    estado_inicial: Dict[str, Any],
    resolver_cadastro: Callable[[GraphState], Dict[str, Any]] | None = None,
    on_etapa: Callable[[str], None] | None = None,
) -> GraphState:
    """Executa até a saída final ou até uma pausa explícita para revisão humana."""
    # O filtro prévio roda sem checkpoint: conteúdo não médico não deve ser persistido.
    admissibilidade = StateGraph(GraphState)
    admissibilidade.add_node("ingestao", node_ingestao)
    admissibilidade.add_node("elegibilidade", node_filtro_elegibilidade)
    admissibilidade.add_edge(START, "ingestao")
    admissibilidade.add_edge("ingestao", "elegibilidade")
    admissibilidade.add_edge("elegibilidade", END)
    estado = admissibilidade.compile().invoke(estado_inicial)

    if estado.get("elegibilidade") in {"nao_medico", "incerto"}:
        return node_finalizador(estado)

    return criar_grafo_triagem(resolver_cadastro, on_etapa).invoke(
        estado, config=_thread_config(estado)
    )


def obter_estado_triagem(documento_id: str) -> Dict[str, Any] | None:
    """Lê o último estado persistido para apresentar progresso sem duplicar dados no Redis."""
    if _checkpointer is None:
        return None
    snapshot = criar_grafo_triagem().get_state(
        {"configurable": {"thread_id": str(documento_id)}}
    )
    return dict(snapshot.values) if snapshot and snapshot.values else None


def retomar_agente_triagem(documento_id: str, decisao: Dict[str, Any]) -> GraphState:
    """Retoma o checkpoint do documento após receber uma decisão humana validada."""
    if _checkpointer is None:
        raise RuntimeError("O checkpointer PostgreSQL não foi inicializado.")
    grafo = criar_grafo_triagem()
    config = {"configurable": {"thread_id": str(documento_id)}}
    snapshot = grafo.get_state(config)
    if not snapshot.next or "revisao_humana" not in snapshot.next:
        raise ValueError("Não há checkpoint de revisão humana ativo para este documento.")
    return grafo.invoke(Command(resume=decisao), config=config)


def excluir_checkpoint_triagem(documento_id: str) -> None:
    """Remove o estado transitório quando a revisão conclui que o arquivo está fora do escopo."""
    if _checkpointer is None:
        raise RuntimeError("O checkpointer PostgreSQL não foi inicializado.")
    _checkpointer.delete_thread(str(documento_id))
