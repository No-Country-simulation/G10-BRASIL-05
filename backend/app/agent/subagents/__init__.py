"""Módulo Multi-Agente do MediFlow.

Contém os agentes especialistas que se comunicam através do estado compartilhado (GraphState):
- Agente_Pre_Triagem & Agente_Qualidade_Visual
- Agente_Identificacao
- Agente_Clinico
- Agente_Auditor_Risco
- Supervisor_Roteamento
"""

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

__all__ = [
    "executar_agente_pre_triagem",
    "executar_agente_qualidade",
    "criar_agente_identificacao",
    "executar_agente_clinico",
    "executar_agente_auditor",
    "decisao_supervisor_preflight",
    "decisao_supervisor_qualidade",
    "decisao_supervisor_auditoria",
    "decisao_supervisor_pos_revisao",
]
