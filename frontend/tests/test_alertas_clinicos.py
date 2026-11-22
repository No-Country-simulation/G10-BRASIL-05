"""Testes unitários para o módulo de alertas clínicos."""
from unittest.mock import MagicMock, patch
import pytest

from utils.alertas_clinicos import (
    CHAVE_ALERTAS_CIENTES,
    ESTADO_EMERGENCIA,
    ESTADO_ESTAVEL,
    ESTADO_PERIGO,
    classificar_estado_clinico,
    obter_badge_estado_html,
    verificar_e_disparar_modal_alerta,
)


def test_classificacao_estado_emergencia():
    doc_iam = {
        "documento_id": "DOC-1",
        "nivel_prioridade": "EMERGENCIA",
        "motivo_revisao": "IAM com supra de ST",
    }
    chave, rotulo, css = classificar_estado_clinico(doc_iam)
    assert chave == ESTADO_EMERGENCIA
    assert rotulo == "EMERGÊNCIA"
    assert "emergencia" in css


def test_classificacao_estado_perigo():
    doc_perigo = {
        "documento_id": "DOC-2",
        "nivel_prioridade": "URGENTE",
        "motivo_revisao": "Conflito medicamentoso entre Varfarina e AAS",
    }
    chave, rotulo, css = classificar_estado_clinico(doc_perigo)
    assert chave == ESTADO_PERIGO
    assert rotulo == "PERIGO"
    assert "perigo" in css


def test_classificacao_estado_estavel():
    doc_estavel = {
        "documento_id": "DOC-3",
        "nivel_prioridade": "ROTINA",
        "motivo_revisao": None,
    }
    chave, rotulo, css = classificar_estado_clinico(doc_estavel)
    assert chave == ESTADO_ESTAVEL
    assert rotulo == "ESTÁVEL"
    assert "estavel" in css


def test_obter_badge_estado_html():
    doc = {"nivel_prioridade": "EMERGENCIA"}
    html = obter_badge_estado_html(doc)
    assert "badge-estado" in html
    assert "EMERGÊNCIA" in html
    assert "badge-estado-emergencia" in html


def test_verificar_e_disparar_modal_alerta():
    mock_session = {CHAVE_ALERTAS_CIENTES: set()}
    doc_emergencia = {
        "documento_id": "DOC-EMERG",
        "nivel_prioridade": "EMERGENCIA",
        "paciente_nome": "Paciente Critico",
    }

    with patch("streamlit.session_state", mock_session), \
         patch("utils.alertas_clinicos.modal_alerta_clinico_popup") as mock_modal:
        verificar_e_disparar_modal_alerta([doc_emergencia])
        assert mock_modal.called
        assert mock_modal.call_args[0][0]["documento_id"] == "DOC-EMERG"
        assert mock_modal.call_args[0][1] == ESTADO_EMERGENCIA

    # Se já está ciente, não deve disparar novamente
    mock_session[CHAVE_ALERTAS_CIENTES].add("DOC-EMERG")
    with patch("streamlit.session_state", mock_session), \
         patch("utils.alertas_clinicos.modal_alerta_clinico_popup") as mock_modal:
        verificar_e_disparar_modal_alerta([doc_emergencia])
        assert not mock_modal.called


def test_redirecionar_para_atendimento_auditoria():
    from utils.alertas_clinicos import redirecionar_para_atendimento_paciente
    mock_session = {CHAVE_ALERTAS_CIENTES: set()}
    doc_auditoria = {
        "documento_id": "DOC-AUD-1",
        "status": "esperando_auditar",
        "requer_auditoria_humana": True,
    }

    with patch("streamlit.session_state", mock_session), \
         patch("streamlit.switch_page") as mock_switch:
        redirecionar_para_atendimento_paciente(doc_auditoria)
        assert "DOC-AUD-1" in mock_session[CHAVE_ALERTAS_CIENTES]
        assert mock_session.get("auditoria_documento_selecionado") == "DOC-AUD-1"
        mock_switch.assert_called_once_with("pages/2_Auditoria_Humana.py")


def test_redirecionar_para_atendimento_analise():
    from utils.alertas_clinicos import redirecionar_para_atendimento_paciente
    mock_session = {CHAVE_ALERTAS_CIENTES: set()}
    doc_analise = {
        "documento_id": "DOC-ANALISE-1",
        "status": "concluido",
        "requer_auditoria_humana": False,
    }

    with patch("streamlit.session_state", mock_session), \
         patch("streamlit.switch_page") as mock_switch:
        redirecionar_para_atendimento_paciente(doc_analise)
        assert "DOC-ANALISE-1" in mock_session[CHAVE_ALERTAS_CIENTES]
        assert mock_session.get("documento_selecionado_analise") == "DOC-ANALISE-1"
        mock_switch.assert_called_once_with("pages/analise.py")


def test_verificar_e_disparar_suprime_quando_ha_botao_clicado():
    mock_session = {
        CHAVE_ALERTAS_CIENTES: set(),
        "btn_det_DOC-123_0": True,
    }
    doc_emergencia = {
        "documento_id": "DOC-EMERG",
        "nivel_prioridade": "EMERGENCIA",
    }
    with patch("streamlit.session_state", mock_session), \
         patch("utils.alertas_clinicos.modal_alerta_clinico_popup") as mock_modal:
        verificar_e_disparar_modal_alerta([doc_emergencia])
        assert not mock_modal.called
