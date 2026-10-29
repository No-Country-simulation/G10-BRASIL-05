import streamlit as st

NAO_INFORMADO = "Não informado"

ALERTAS_POR_DESTINO = {
    "Fila_Emergencia_Medica": (st.error, "🚨", "URGENTE: encaminhado para a fila de emergência médica"),
    "Auditoria_Humana": (st.warning, "👨‍⚕️", "Revisão humana necessária"),
    "Fluxo_Padrao": (st.success, "✅", "Rotina: aprovado automaticamente"),
}
ALERTA_DESTINO_DESCONHECIDO = (st.info, "ℹ️", "Destino não reconhecido")


def exibir_alerta_de_roteamento(decisao: dict) -> None:
    exibir_alerta, icone, titulo = ALERTAS_POR_DESTINO.get(
        decisao.get("destino_principal"), ALERTA_DESTINO_DESCONHECIDO
    )
    partes = [f"**{titulo}**", decisao.get("justificativa_roteamento")]
    notificacao = decisao.get("notificacao_gerada")
    if notificacao:
        partes.append(notificacao.get("mensagem"))
    exibir_alerta("\n\n".join(parte for parte in partes if parte), icon=icone)


def exibir_classificacao(classificacao: dict) -> None:
    campos = (
        ("Tipo de documento", classificacao.get("tipo_documento")),
        ("Especialidade", classificacao.get("especialidade")),
        ("Prioridade", classificacao.get("nivel_prioridade")),
        ("Confiança", _formatar_score(classificacao.get("score_confianca_classificacao"))),
    )
    for coluna, (rotulo, valor) in zip(st.columns(len(campos)), campos):
        with coluna:
            _exibir_campo(rotulo, valor)


def exibir_dados_extraidos(dados: dict) -> None:
    coluna_pessoas, coluna_clinica = st.columns(2)
    with coluna_pessoas:
        _exibir_campo("Paciente", _formatar_paciente(dados.get("paciente") or {}))
        _exibir_campo("Médico solicitante", _formatar_medico(dados.get("medico_solicitante") or {}))
    with coluna_clinica:
        _exibir_campo("Diagnóstico principal", dados.get("diagnostico_principal"))
        _exibir_campo("CID-10 sugerido", dados.get("cid_sugerido"))
    _exibir_itens_clinicos(dados)


def exibir_resultado_da_triagem(resposta: dict) -> None:
    exibir_alerta_de_roteamento(resposta.get("decisao_roteamento") or {})
    st.subheader("Classificação")
    exibir_classificacao(resposta.get("classificacao") or {})
    st.subheader("Dados extraídos")
    exibir_dados_extraidos(resposta.get("dados_extraidos") or {})
    with st.expander("Ver resposta completa (JSON)"):
        st.json(resposta)


def exibir_item_de_auditoria(item: dict) -> None:
    motivo = item.get("justificativa_roteamento") or NAO_INFORMADO
    st.warning(f"**Revisão humana necessária**\n\n{motivo}", icon="👨‍⚕️")
    campos = (
        ("Tipo de documento", item.get("tipo_documento")),
        ("Confiança", _formatar_score(item.get("score_confianca"))),
    )
    for coluna, (rotulo, valor) in zip(st.columns(len(campos)), campos):
        with coluna:
            _exibir_campo(rotulo, valor)
    st.subheader("Dados extraídos")
    exibir_dados_extraidos(item.get("dados_extraidos") or {})


def _exibir_campo(rotulo: str, valor) -> None:
    st.caption(rotulo)
    st.markdown(f"**{valor or NAO_INFORMADO}**")


def _exibir_itens_clinicos(dados: dict) -> None:
    exame = dados.get("exame_realizado")
    if exame:
        _exibir_campo("Exame realizado", exame)
    medicamentos = dados.get("medicamentos") or []
    if medicamentos:
        st.caption("Medicamentos")
        for medicamento in medicamentos:
            st.markdown(f"- {_formatar_medicamento(medicamento)}")


def _formatar_score(score) -> str | None:
    if score is None:
        return None
    return f"{score:.0%}"


def _formatar_paciente(paciente: dict) -> str | None:
    nome = paciente.get("nome")
    idade = paciente.get("idade")
    if nome and idade:
        return f"{nome}, {idade} anos"
    return nome


def _formatar_medico(medico: dict) -> str | None:
    nome = medico.get("nome")
    crm = medico.get("crm")
    if not nome:
        return None
    return f"{nome} (CRM {crm})" if crm else f"{nome} (CRM não informado)"


def _formatar_medicamento(medicamento: dict) -> str:
    partes = (medicamento.get(campo) for campo in ("nome", "dosagem", "posologia"))
    return " · ".join(parte for parte in partes if parte)