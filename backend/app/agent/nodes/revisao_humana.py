"""Fronteira de pausa do grafo para decisão humana."""

from langgraph.types import interrupt

from app.agent.state import GraphState


def node_revisao_humana(state: GraphState) -> GraphState:
    """Pausa com contexto/evidências e incorpora a decisão ao retomar o checkpoint."""
    decisao = interrupt(
        {
            "documento_id": state.get("documento_id"),
            "motivo": state.get("motivo_revisao") or state.get("justificativa_elegibilidade"),
            "elegibilidade": state.get("elegibilidade"),
            "avaliacao_escopo": state.get("avaliacao_escopo"),
            "qualidade_documento": state.get("qualidade_documento"),
            "dados_extraidos": state.get("dados_extraidos"),
            "evidencias_campos": state.get("evidencias_campos"),
            "campos_bloqueados": state.get("campos_bloqueados", []),
            "referencia_fonte": state.get("referencia_fonte"),
            "opcoes": ["aprovado", "corrigido", "rejeitado", "solicitar_reenvio"],
        }
    )
    decisao = decisao if isinstance(decisao, dict) else {"status_aprovacao": str(decisao)}
    atualizacao = {**state, "decisao_humana": decisao, "status": "revisao_respondida"}
    acao = decisao.get("status_aprovacao")

    if state.get("etapa_revisao") == "elegibilidade" and acao == "rejeitado":
        atualizacao["elegibilidade"] = "nao_medico"
        return atualizacao
    if acao in {"rejeitado", "solicitar_reenvio"}:
        return atualizacao
    if state.get("etapa_revisao") == "elegibilidade" and acao == "aprovado":
        atualizacao.update({"elegibilidade": "medico", "confianca_elegibilidade": 1.0})
    elif state.get("etapa_revisao") == "qualidade" and acao == "aprovado":
        qualidade = dict(state.get("qualidade_documento") or {})
        qualidade.update({"status": "adequada", "aprovada_por_revisor": True})
        atualizacao.update({"qualidade_documento": qualidade})
    elif state.get("etapa_revisao") == "validacao":
        corrigidos = decisao.get("dados_corrigidos")
        if corrigidos:
            atualizacao["dados_extraidos"] = corrigidos
            atualizacao["paciente"] = corrigidos.get("paciente")
            atualizacao["medico_solicitante"] = corrigidos.get("medico_solicitante")
            atualizacao["exame_realizado"] = corrigidos.get("exame_realizado")
            atualizacao["diagnostico_principal"] = corrigidos.get("diagnostico_principal")
            atualizacao["cid_sugerido"] = corrigidos.get("cid_sugerido")
        atualizacao["campos_bloqueados"] = []
        atualizacao["inconsistencias"] = []
        atualizacao["validacao_fonte"] = {
            **(state.get("validacao_fonte") or {}),
            "fonte_verificada": True,
            "fonte_verificada_visualmente": True,
            "aprovada_por_revisor": True,
        }
        atualizacao["fonte_verificada_visualmente"] = True
        atualizacao["validacao_schema"] = {"valido": True, "erros": [], "aprovado_por_revisor": True}
        atualizacao["revisao_concluida"] = True
    elif state.get("etapa_revisao") == "risco" and acao in {"aprovado", "corrigido"}:
        atualizacao["revisao_concluida"] = True
    if acao in {"aprovado", "corrigido"}:
        atualizacao["requer_auditoria_humana"] = False
    return atualizacao
