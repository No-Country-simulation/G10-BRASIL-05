"""Subagente de Triagem e Elegibilidade.

Responsável pela ingestão, análise de legibilidade/qualidade visual e
validação de escopo do documento (garantindo que se trata de documento médico/SUS).
"""

from typing import Any, Dict
from app.agent.state import GraphState
from app.agent.nodes.ingestao import node_ingestao
from app.agent.nodes.filtro_elegibilidade import node_filtro_elegibilidade
from app.agent.nodes.qualidade_documento import node_qualidade_documento


def executar_agente_pre_triagem(state: GraphState) -> GraphState:
    """Executa o pré-filtro de admissibilidade: ingestão e escopo médico."""
    estado = node_ingestao(state)
    estado = node_filtro_elegibilidade(estado)
    
    trilha = list(estado.get("trilha_multiagente", []))
    trilha.append({
        "agente": "Agente_Pre_Triagem",
        "elegibilidade": estado.get("elegibilidade"),
        "confianca": estado.get("confianca_elegibilidade"),
    })
    return {**estado, "trilha_multiagente": trilha, "agente_ativo": "Agente_Pre_Triagem"}


def executar_agente_qualidade(state: GraphState) -> GraphState:
    """Executa a inspeção visual de legibilidade e resolução."""
    estado = node_qualidade_documento(state)
    
    trilha = list(estado.get("trilha_multiagente", []))
    qualidade = estado.get("qualidade_documento") or {}
    trilha.append({
        "agente": "Agente_Qualidade_Visual",
        "qualidade_status": qualidade.get("status"),
        "resolucao": qualidade.get("resolucao"),
    })
    return {**estado, "trilha_multiagente": trilha, "agente_ativo": "Agente_Qualidade_Visual"}
