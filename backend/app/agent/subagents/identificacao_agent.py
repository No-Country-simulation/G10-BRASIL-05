"""Subagente de Identificação e Cadastro do Paciente.

Responsável por identificar o paciente, extrair CPF com validação matemática,
identificar médico solicitante e resolver vínculos cadastrais no prontuário.
"""

from typing import Any, Callable, Dict
from app.agent.state import GraphState
from app.agent.nodes.identificacao import node_identificacao


def criar_agente_identificacao(
    resolver_cadastro: Callable[[GraphState], Dict[str, Any]] | None = None,
    on_etapa: Callable[[str], None] | None = None,
):
    """Factory para o subagente de identificação com suporte a injeção de callbacks."""
    def executar_identificacao(state: GraphState) -> GraphState:
        if on_etapa:
            on_etapa("identificacao")
            
        estado = node_identificacao(state)
        
        # Resolução cadastral do paciente se callback fornecido
        atualizacoes = resolver_cadastro(estado) if resolver_cadastro else {}
        if on_etapa:
            on_etapa("analise_clinica")
            
        trilha = list(estado.get("trilha_multiagente", []))
        trilha.append({
            "agente": "Agente_Identificacao",
            "paciente_encontrado": bool(estado.get("paciente") or atualizacoes.get("paciente")),
            "cpf_validado": not estado.get("cpf_validacao_falhou", False),
        })
        
        return {
            **estado,
            **atualizacoes,
            "etapa_atual": "analise_clinica",
            "trilha_multiagente": trilha,
            "agente_ativo": "Agente_Identificacao",
        }
        
    return executar_identificacao
