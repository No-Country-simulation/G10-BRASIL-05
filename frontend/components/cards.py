import streamlit as st

from utils.aparencia import (
    montar_alerta_de_emergencia,
    montar_selo_de_prioridade,
    texto_colorido_da_confianca,
)
from utils.formatadores import (
    crm_do_medico,
    nome_do_paciente,
    rotular_prioridade,
    rotular_tipo_documento,
)

NAO_INFORMADO = "Não informado"
DESTINO_EMERGENCIA = "Fila_Emergencia_Medica"
TITULO_DA_EMERGENCIA = "URGENTE: encaminhado para a fila de emergência médica"

ALERTAS_POR_DESTINO = {
    "Auditoria_Humana": (st.warning, "👨‍⚕️", "Revisão humana necessária"),
    "Fluxo_Padrao": (st.success, "✅", "Rotina: aprovado automaticamente"),
    "Farmacia_Hospitalar": (st.success, "💊", "Rotina: encaminhado para a farmácia hospitalar"),
}
ALERTA_DESTINO_DESCONHECIDO = (st.info, "ℹ️", "Destino não reconhecido")

EXTENSOES_DE_IMAGEM = ("png", "jpg", "jpeg", "webp")
BYTES_POR_KB = 1024


def exibir_previa_do_arquivo(arquivo) -> None:
    extensao = arquivo.name.rsplit(".", 1)[-1].lower()
    if extensao in EXTENSOES_DE_IMAGEM:
        st.image(arquivo, caption=f"Pré-visualização: {arquivo.name}", width="stretch")
    elif extensao == "pdf":
        st.info(f"📄 PDF carregado: **{arquivo.name}** ({arquivo.size / BYTES_POR_KB:.1f} KB)")


def exibir_alerta_de_roteamento(decisao: dict) -> None:
    destino = decisao.get("destino_principal")
    justificativa = decisao.get("justificativa_roteamento")
    mensagem_do_plantao = (decisao.get("notificacao_gerada") or {}).get("mensagem")
    if destino == DESTINO_EMERGENCIA:
        alerta = montar_alerta_de_emergencia(TITULO_DA_EMERGENCIA, justificativa, mensagem_do_plantao)
        st.markdown(alerta, unsafe_allow_html=True)
        return
    exibir_alerta, icone, titulo = ALERTAS_POR_DESTINO.get(destino, ALERTA_DESTINO_DESCONHECIDO)
    partes = [f"**{titulo}**", justificativa, mensagem_do_plantao]
    exibir_alerta("\n\n".join(parte for parte in partes if parte), icon=icone)


def exibir_classificacao(classificacao: dict) -> None:
    _exibir_selo_de_prioridade(classificacao.get("nivel_prioridade"))
    campos = (
        ("Tipo de documento", rotular_tipo_documento(classificacao.get("tipo_documento"))),
        ("Especialidade", classificacao.get("especialidade")),
        ("Prioridade", rotular_prioridade(classificacao.get("nivel_prioridade"))),
    )
    colunas = st.columns(len(campos) + 1)
    for coluna, (rotulo, valor) in zip(colunas, campos):
        with coluna:
            _exibir_campo(rotulo, valor)
    with colunas[-1]:
        _exibir_confianca(classificacao.get("score_confianca_classificacao"))


def exibir_dados_extraidos(dados: dict) -> None:
    coluna_pessoas, coluna_clinica = st.columns(2)
    with coluna_pessoas:
        _exibir_campo("Paciente", _formatar_paciente(dados.get("paciente")))
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
    _exibir_selo_de_prioridade(item.get("nivel_prioridade"))
    motivo = item.get("justificativa_roteamento") or NAO_INFORMADO
    st.warning(f"**Revisão humana necessária**\n\n{motivo}", icon="👨‍⚕️")
    coluna_tipo, coluna_confianca = st.columns(2)
    with coluna_tipo:
        _exibir_campo("Tipo de documento", rotular_tipo_documento(item.get("tipo_documento")))
    with coluna_confianca:
        _exibir_confianca(item.get("score_confianca"))
    st.subheader("Dados extraídos")
    exibir_dados_extraidos(item.get("dados_extraidos") or {})


def _exibir_selo_de_prioridade(prioridade: str | None) -> None:
    selo = montar_selo_de_prioridade(prioridade)
    if selo:
        st.markdown(selo, unsafe_allow_html=True)


def _exibir_campo(rotulo: str, valor) -> None:
    st.caption(rotulo)
    st.markdown(f"**{valor or NAO_INFORMADO}**")


def _exibir_confianca(score: float | None) -> None:
    st.caption("Confiança")
    st.markdown(texto_colorido_da_confianca(score) or f"**{NAO_INFORMADO}**")


def _exibir_itens_clinicos(dados: dict) -> None:
    exame = dados.get("exame_realizado")
    if exame:
        _exibir_campo("Exame realizado", exame)
    medicamentos = dados.get("medicamentos") or []
    if medicamentos:
        st.caption("Medicamentos")
        for medicamento in medicamentos:
            descricao = _formatar_medicamento(medicamento)
            if descricao:
                st.markdown(f"- {descricao}")


def _formatar_paciente(paciente) -> str | None:
    nome = nome_do_paciente(paciente)
    idade = paciente.get("idade") if isinstance(paciente, dict) else None
    return f"{nome}, {idade} anos" if nome and idade else nome


def _formatar_medico(medico: dict) -> str | None:
    nome = medico.get("nome")
    crm = crm_do_medico(medico)
    if not nome:
        return None
    return f"{nome} (CRM {crm})" if crm else f"{nome} (CRM não informado)"


def _formatar_medicamento(medicamento: dict) -> str:
    partes = (medicamento.get(campo) for campo in ("medicamento", "dosagem"))
    return " · ".join(parte for parte in partes if parte)
