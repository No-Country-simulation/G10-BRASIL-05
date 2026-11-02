import pytest

from services.api_client import (
    buscar_documento,
    enviar_documento,
    listar_documentos,
    listar_fila_auditoria,
    registrar_decisao,
)

CAMPOS_DA_LISTA = {
    "documento_id",
    "tipo_documento",
    "nivel_prioridade",
    "score_confianca",
    "destino_principal",
    "status_processamento",
    "requer_auditoria_humana",
    "created_at",
}


def _requisicao_com_texto(texto: str) -> dict:
    return {"documento_texto": texto}


@pytest.mark.parametrize(
    "texto, destino_esperado, exige_auditoria",
    [
        ("suspeita de TEP", "Fila_Emergencia_Medica", False),
        ("receita com CRM ausente", "Auditoria_Humana", True),
        ("receita de rotina", "Fluxo_Padrao", False),
    ],
)
def test_enviar_documento_cobre_os_tres_cenarios(texto, destino_esperado, exige_auditoria):
    resposta = enviar_documento(_requisicao_com_texto(texto))

    decisao = resposta["decisao_roteamento"]
    assert decisao["destino_principal"] == destino_esperado
    assert decisao["requer_auditoria_humana"] is exige_auditoria


def test_urgencia_traz_notificacao_para_o_plantao():
    resposta = enviar_documento(_requisicao_com_texto("suspeita de TEP"))

    notificacao = resposta["decisao_roteamento"]["notificacao_gerada"]
    assert notificacao["canal"] == "Alerta_Plantao_Medico"


def test_enviar_documento_devolve_copia_da_resposta():
    primeira = enviar_documento(_requisicao_com_texto("receita de rotina"))
    primeira["decisao_roteamento"]["destino_principal"] = "Alterado"

    segunda = enviar_documento(_requisicao_com_texto("receita de rotina"))

    assert segunda["decisao_roteamento"]["destino_principal"] == "Fluxo_Padrao"


def test_listar_documentos_segue_o_formato_plano_do_backend():
    documentos = listar_documentos()

    assert documentos
    assert all(set(documento) == CAMPOS_DA_LISTA for documento in documentos)


def test_documento_em_auditoria_tem_o_status_de_auditoria():
    documentos = {documento["documento_id"]: documento for documento in listar_documentos()}

    assert documentos["DOC-CLIN-2026-0003"]["status_processamento"] == "em_auditoria"
    assert documentos["DOC-CLIN-2026-0001"]["status_processamento"] == "processado"


def test_buscar_documento_devolve_a_resposta_completa():
    documento = buscar_documento("DOC-CLIN-2026-8942")

    assert documento["decisao_roteamento"]["destino_principal"] == "Fila_Emergencia_Medica"


def test_buscar_documento_inexistente_devolve_none():
    assert buscar_documento("DOC-INEXISTENTE") is None


def test_listar_fila_auditoria_segue_o_formato_do_backend():
    fila = listar_fila_auditoria()

    assert fila
    assert all("dados_extraidos" in item and "score_confianca" in item for item in fila)


def test_registrar_decisao_devolve_o_novo_status():
    resposta = registrar_decisao("DOC-1", {"status_aprovacao": "aprovado"})

    assert resposta["documento_id"] == "DOC-1"
    assert resposta["novo_status"] == "auditoria_aprovado"