"""Subagente Clínico Especialista.

Responsável por classificar o tipo do documento (Laudo, Receita, Exame, etc.)
e extrair com precisão entidades clínicas (medicamentos, dosagens, diagnósticos, CIDs).
"""

from app.agent.state import GraphState
from app.agent.nodes.classificador import node_classificacao
from app.agent.nodes.extrator import node_extracao


def executar_agente_clinico(state: GraphState) -> GraphState:
    """Executa classificação e extração clínica estruturada."""
    # 1. Classificação de tipo e especialidade
    estado = node_classificacao(state)
    
    # 2. Extração detalhada de dados clínicos
    estado = node_extracao(estado)
    
    trilha = list(estado.get("trilha_multiagente", []))
    trilha.append({
        "agente": "Agente_Clinico",
        "tipo_documento": estado.get("tipo_documento"),
        "especialidade": estado.get("especialidade"),
        "total_medicamentos": len(estado.get("medicamentos", [])),
        "diagnostico": estado.get("diagnostico_principal"),
        "cid": estado.get("cid_sugerido"),
    })
    
    return {
        **estado,
        "trilha_multiagente": trilha,
        "agente_ativo": "Agente_Clinico",
    }
