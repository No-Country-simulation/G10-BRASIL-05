"""Subagente Validador e Auditor de Risco Clínico.

Responsável por validar a integridade das evidências, verificar regras do CFM/COFEN
(ex: CRM/UF válidos, dosagens coerentes), detectar emergências críticas e calcular o score de confiança.
"""

from app.agent.state import GraphState
from app.agent.nodes.validador import node_validador
from app.agent.nodes.avaliador import node_avaliacao


def executar_agente_auditor(state: GraphState) -> GraphState:
    """Executa a auditoria de regras clínicas e cálculo de score de confiança."""
    # 1. Validação de regras e evidências
    estado = node_validador(state)
    
    # 2. Avaliação de urgência e score final
    estado = node_avaliacao(estado)
    
    trilha = list(estado.get("trilha_multiagente", []))
    trilha.append({
        "agente": "Agente_Auditor_Risco",
        "status_validacao": estado.get("status"),
        "is_urgente": estado.get("is_urgente", False),
        "score_total": estado.get("score_total"),
        "faixa_motor_regras": estado.get("faixa_motor_regras"),
        "score_confianca": estado.get("score_confianca_classificacao"),
        "requer_auditoria_humana": estado.get("requer_auditoria_humana", False),
    })
    
    return {
        **estado,
        "trilha_multiagente": trilha,
        "agente_ativo": "Agente_Auditor_Risco",
    }
