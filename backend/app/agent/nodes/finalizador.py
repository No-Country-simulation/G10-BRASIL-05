"""Consolida resultado terminal sem executar I/O ou persistência."""

from app.agent.state import GraphState


def node_finalizador(state: GraphState) -> GraphState:
    """Prepara mensagem/status terminal para a camada de serviço responder ao cliente."""
    if state.get("elegibilidade") == "nao_medico":
        return {
            **state,
            "status": "recusado",
            "mensagem_usuario": "O documento enviado não foi identificado como médico. O processamento foi recusado.",
        }
    decisao = state.get("decisao_humana") or {}
    status_revisao = decisao.get("status_aprovacao")
    if status_revisao == "rejeitado":
        return {**state, "status": "rejeitado", "mensagem_usuario": "A triagem foi rejeitada na revisão humana."}
    if status_revisao == "solicitar_reenvio":
        return {**state, "status": "aguardando_reenvio", "mensagem_usuario": "Envie uma nova imagem ou documento legível para continuar."}
    return {**state, "status": state.get("status") or "concluido"}
