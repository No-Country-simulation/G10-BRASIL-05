"""Orquestração Multi-Agente da triagem clínica e dos pontos de revisão humana.

Integra uma rede de subagentes especializados com comunicação orientada a estados:
1. Agente_Pre_Triagem: Ingestão e escopo médico/SUS.
2. Agente_Qualidade_Visual: Legibilidade, resolução e pré-processamento OCR.
3. Agente_Identificacao: Reconhecimento de paciente, validação matemática de CPF e busca cadastral.
4. Agente_Clinico: Classificação de tipo documental e extração de medicamentos, exames e CID.
5. Agente_Auditor_Risco: Validação de regras CFM/SUS, detecção de emergências e score de confiança.
6. Supervisor_Roteamento: Orquestração, pontos de pausa HITL (revisão humana) e roteamento final.
"""

from typing import Any, Callable, Dict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agent.state import GraphState
from app.agent.nodes.finalizador import node_finalizador
from app.agent.nodes.revisao_humana import node_revisao_humana
from app.agent.nodes.roteador import node_roteamento
from app.agent.nodes.classificador import node_classificacao
from app.agent.nodes.extrator import node_extracao
from app.agent.nodes.validador import node_validador
from app.agent.nodes.avaliador import node_avaliacao

from app.agent.subagents.triagem_agent import (
    executar_agente_pre_triagem,
    executar_agente_qualidade,
)
from app.agent.subagents.identificacao_agent import criar_agente_identificacao
from app.agent.subagents.clinico_agent import executar_agente_clinico
from app.agent.subagents.auditor_agent import executar_agente_auditor
from app.agent.subagents.supervisor import (
    decisao_supervisor_preflight,
    decisao_supervisor_qualidade,
    decisao_supervisor_auditoria,
    decisao_supervisor_pos_revisao,
)


_grafo_compilado = None
_checkpointer = None
_checkpointer_fallback = InMemorySaver()


def configurar_checkpointer(checkpointer: Any) -> None:
    """Injeta saver durável durante o lifespan da API e invalida o grafo em cache."""
    global _checkpointer, _grafo_compilado
    _checkpointer = checkpointer
    _grafo_compilado = None


def _apos_preflight(state: GraphState) -> str:
    return decisao_supervisor_preflight(state).replace("agente_qualidade", "qualidade")


def _apos_qualidade(state: GraphState) -> str:
    return decisao_supervisor_qualidade(state).replace("agente_identificacao", "identificacao")


def _apos_validacao(state: GraphState) -> str:
    return "avaliacao"


def _apos_avaliacao(state: GraphState) -> str:
    return decisao_supervisor_auditoria(state).replace("agente_roteamento", "roteamento")


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
    """Constrói o StateGraph multi-agente; callbacks por trabalho não são compartilhados."""
    global _grafo_compilado
    if resolver_cadastro is None and on_etapa is None and _grafo_compilado is not None:
        return _grafo_compilado

    cp = _checkpointer if _checkpointer is not None else _checkpointer_fallback

    workflow = StateGraph(GraphState)
    workflow.add_node("continuacao", lambda state: state)
    workflow.add_node("qualidade", executar_agente_qualidade)

    agente_identificacao_fn = criar_agente_identificacao(resolver_cadastro, on_etapa)
    workflow.add_node("identificacao", agente_identificacao_fn)
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
    workflow.add_edge("identificacao", "classificacao")
    workflow.add_edge("classificacao", "extracao")
    workflow.add_edge("extracao", "validacao")
    workflow.add_conditional_edges("validacao", _apos_validacao)
    workflow.add_conditional_edges("avaliacao", _apos_avaliacao)
    workflow.add_conditional_edges("revisao_humana", _apos_revisao)
    workflow.add_edge("roteamento", "finalizador")
    workflow.add_edge("finalizador", END)

    grafo = workflow.compile(checkpointer=cp)
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
    """Executa a rede multi-agente até a saída final ou pausa para revisão médica."""
    # Fase 1: Pré-Triagem com Agente de Admissibilidade
    estado = executar_agente_pre_triagem(estado_inicial)

    if estado.get("elegibilidade") == "nao_medico":
        return node_finalizador(estado)

    # Fase 2: Orquestração dos Agentes Especialistas no Grafo
    return criar_grafo_triagem(resolver_cadastro, on_etapa).invoke(
        estado, config=_thread_config(estado)
    )


def obter_estado_triagem(documento_id: str) -> Dict[str, Any] | None:
    """Lê o último estado persistido do checkpoint multi-agente."""
    cp = _checkpointer if _checkpointer is not None else _checkpointer_fallback
    if cp is None:
        return None
    snapshot = criar_grafo_triagem().get_state(
        {"configurable": {"thread_id": str(documento_id)}}
    )
    return dict(snapshot.values) if snapshot and snapshot.values else None


def retomar_agente_triagem(documento_id: str, decisao: Dict[str, Any]) -> GraphState:
    """Retoma o checkpoint do documento após receber uma decisão humana validada."""
    grafo = criar_grafo_triagem()
    config = {"configurable": {"thread_id": str(documento_id)}}
    snapshot = grafo.get_state(config)
    if not snapshot.next or "revisao_humana" not in snapshot.next:
        raise ValueError("Não há checkpoint de revisão humana ativo para este documento.")
    return grafo.invoke(Command(resume=decisao), config=config)


def excluir_checkpoint_triagem(documento_id: str) -> None:
    """Remove o checkpoint persistente do grafo."""
    cp = _checkpointer if _checkpointer is not None else _checkpointer_fallback
    if cp is not None and hasattr(cp, "delete_thread"):
        cp.delete_thread(str(documento_id))
