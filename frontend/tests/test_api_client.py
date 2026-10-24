import pytest

from services.api_client import enviar_documento, listar_documentos


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


def test_listar_documentos_devolve_documentos_identificados():
    documentos = listar_documentos()

    assert documentos
    assert all(documento["documento_id"] for documento in documentos)