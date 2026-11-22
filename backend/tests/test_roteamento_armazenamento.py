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


def test_node_roteamento_alerta_emergencia():
    """Valida mensagem de emergência personalizada com diagnóstico e nome do paciente."""
    from app.agent.nodes.roteador import node_roteamento
    estado = {
        "is_urgente": True,
        "motivo_urgencia": "Achado crítico",
        "documento_id": "DOC-99",
        "paciente": {"nome": "Maria Santos"},
        "diagnostico_principal": "Infarto Agudo do Miocárdio",
    }
    resultado = node_roteamento(estado)
    assert resultado["destino_principal"] == "Fila_Emergencia_Medica"
    alerta = resultado["notificacao_gerada"]
    assert alerta is not None
    assert alerta["canal"] == "Alerta_Plantao_Medico"
    assert alerta["mensagem"] == "ALERTA URGENTE: Laudo critico de Infarto Agudo do Miocárdio para paciente Maria Santos no Pronto-Socorro."


def test_storage_salvar_triagem_json_chaves_canonicas(tmp_path):
    """Garante que o JSON salvo no storage e OCI tem a raiz canônica com as 6 chaves."""
    import json
    from app.repositories.storage import StorageRepository
    repo = StorageRepository(local_storage_dir=str(tmp_path))
    dados = {
        "classificacao": {"tipo_documento": "RECEITA", "especialidade": "Clínica Geral", "nivel_prioridade": "ROTINA", "score_confianca_classificacao": 0.95},
        "dados_extraidos": {"paciente": {"nome": "João", "idade": 50}},
    }
    resultado = repo.salvar_triagem_json(documento_id="DOC-TESTE-CANONICO", dados_resultado=dados, is_urgente=False)
    assert resultado["status_backup"] == "sucesso"
    caminho = resultado["caminho_local"]
    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = json.load(f)
    chaves_esperadas = {"status", "documento_id", "classificacao", "dados_extraidos", "decisao_roteamento", "armazenamento_oci"}
    assert chaves_esperadas.issubset(set(conteudo.keys()))
    assert conteudo["status"] == "processado"
    assert conteudo["armazenamento_oci"]["status_backup"] == "sucesso"
