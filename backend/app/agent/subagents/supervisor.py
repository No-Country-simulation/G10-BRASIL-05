"""Supervisor Multi-Agente e Roteador Final.

Orquestra a comunicação entre os agentes especialistas, avalia as decisões
condicionais e direciona para revisão médica (HITL) ou roteamento para os destinos finais.
"""

from app.agent.state import GraphState
from app.agent.nodes.roteador import node_roteamento
from app.agent.nodes.revisao_humana import node_revisao_humana
from app.agent.nodes.finalizador import node_finalizador


def decisao_supervisor_preflight(state: GraphState) -> str:
    """Decide se avança para inspeção visual ou finaliza por não ser documento médico."""
    if state.get("elegibilidade") == "nao_medico":
        return "finalizador"
    if state.get("elegibilidade") == "incerto":
        return "revisao_humana"
    return "agente_qualidade"


def decisao_supervisor_qualidade(state: GraphState) -> str:
    """Decide se avança para identificação ou para revisão humana por qualidade inadequada."""
    qualidade = state.get("qualidade_documento") or {}
    if qualidade.get("status") == "adequada":
        return "agente_identificacao"
    return "revisao_humana"


def decisao_supervisor_auditoria(state: GraphState) -> str:
    """Decide se avança para roteamento ou pausa para revisão médica humana."""
    if state.get("requer_auditoria_humana"):
        return "revisao_humana"
    return "agente_roteamento"


def decisao_supervisor_pos_revisao(state: GraphState) -> str:
    """Avalia o retorno da decisão humana inserida pelo médico/diretor."""
    decisao = state.get("decisao_humana") or {}
    acao = decisao.get("status_aprovacao")
    if acao in {"rejeitado", "solicitar_reenvio"}:
        return "finalizador"
        
    etapa = state.get("etapa_revisao")
    if etapa == "elegibilidade":
        return "agente_qualidade" if state.get("elegibilidade") == "medico" else "finalizador"
    if etapa == "qualidade":
        return "agente_clinico" if (state.get("qualidade_documento") or {}).get("status") == "adequada" else "finalizador"
    if etapa in {"validacao", "risco"}:
        return "agente_roteamento"
    return "finalizador"
