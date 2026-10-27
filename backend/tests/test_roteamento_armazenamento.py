import pytest
from pydantic import ValidationError
from app.schemas.roteamento import DecisaoRoteamento, NotificacaoAlerta
from app.schemas.armazenamento import ArmazenamentoOCI


def test_decisao_roteamento_com_notificacao():
    """Valida modelagem de DecisaoRoteamento contendo alerta de urgência."""
    alerta = NotificacaoAlerta(
        canal="Alerta_Plantao_Medico",
        mensagem="ALERTA URGENTE: Laudo critico de TEP detectado.",
    )
    roteamento = DecisaoRoteamento(
        destino_principal="Fila_Emergencia_Medica",
        requer_auditoria_humana=False,
        justificativa_roteamento="Achado de alta gravidade identificado com confianca 0.99.",
        notificacao_gerada=alerta,
    )

    assert roteamento.destino_principal == "Fila_Emergencia_Medica"
    assert roteamento.requer_auditoria_humana is False
    assert roteamento.notificacao_gerada is not None
    assert roteamento.notificacao_gerada.canal == "Alerta_Plantao_Medico"


def test_decisao_roteamento_sem_notificacao_padrao():
    """Valida modelagem de DecisaoRoteamento para fluxo padrão (sem alerta)."""
    roteamento = DecisaoRoteamento(
        destino_principal="Fluxo_Padrao",
        requer_auditoria_humana=False,
        justificativa_roteamento="Documento de rotina processado.",
    )

    assert roteamento.destino_principal == "Fluxo_Padrao"
    assert roteamento.notificacao_gerada is None


def test_decisao_roteamento_campos_obrigatorios():
    """Valida que campos obrigatórios ausentes disparam ValidationError do Pydantic."""
    with pytest.raises(ValidationError):
        DecisaoRoteamento(destino_principal="Fila_Emergencia_Medica")  # Faltam justificativa e requer_auditoria_humana


def test_armazenamento_oci_valido():
    """Valida modelagem de ArmazenamentoOCI com metadados do bucket."""
    storage = ArmazenamentoOCI(
        bucket="mediflow-documentos-clinicos",
        caminho_objeto="processados/urgentes/DOC-CLIN-2026-8942.json",
        status_backup="sucesso",
    )

    assert storage.bucket == "mediflow-documentos-clinicos"
    assert storage.caminho_objeto == "processados/urgentes/DOC-CLIN-2026-8942.json"
    assert storage.status_backup == "sucesso"


def test_armazenamento_oci_campos_obrigatorios():
    """Valida que a ausência de caminho_objeto ou bucket gera ValidationError."""
    with pytest.raises(ValidationError):
        ArmazenamentoOCI(bucket="mediflow-documentos-clinicos")
