from datetime import datetime
from unittest.mock import MagicMock
from app.controllers.historico import listar_documentos, _extrair_info_paciente, _formatar_doc_historico


class MockDocumento:
    def __init__(
        self,
        documento_id="DOC-TEST-1",
        tipo_documento="Laudo",
        nivel_prioridade="Rotina",
        score_confianca=0.95,
        destino_principal="Arquivo",
        status_processamento="concluido",
        requer_auditoria_humana=False,
        dados_extraidos=None,
        created_at=None,
        paciente=None,
    ):
        self.documento_id = documento_id
        self.tipo_documento = tipo_documento
        self.nivel_prioridade = nivel_prioridade
        self.score_confianca = score_confianca
        self.destino_principal = destino_principal
        self.status_processamento = status_processamento
        self.requer_auditoria_humana = requer_auditoria_humana
        self.dados_extraidos = dados_extraidos
        self.created_at = created_at or datetime.utcnow()
        self.paciente = paciente


def test_extrair_info_paciente_casos_borda():
    # 1. dados_extraidos is None
    doc1 = MockDocumento(dados_extraidos=None)
    assert _extrair_info_paciente(doc1) == (None, None)

    # 2. paciente is None in dict
    doc2 = MockDocumento(dados_extraidos={"paciente": None})
    assert _extrair_info_paciente(doc2) == (None, None)

    # 3. paciente is a string
    doc3 = MockDocumento(dados_extraidos={"paciente": "Carlos Silva"})
    assert _extrair_info_paciente(doc3) == ("Carlos Silva", None)

    # 4. paciente is a dict with nome and cpf
    doc4 = MockDocumento(dados_extraidos={"paciente": {"nome": "Ana Maria", "cpf": "123.456.789-00"}})
    assert _extrair_info_paciente(doc4) == ("Ana Maria", "123.456.789-00")

    # 5. dados_extraidos is a JSON string
    doc5 = MockDocumento(dados_extraidos='{"paciente": {"nome": "Pedro Lima", "cpf": "999"}}')
    assert _extrair_info_paciente(doc5) == ("Pedro Lima", "999")

    # 6. Fallback to ORM paciente relationship
    mock_paciente_orm = MagicMock()
    mock_paciente_orm.nome = "Mariana"
    mock_paciente_orm.cpf = "888"
    doc6 = MockDocumento(dados_extraidos=None, paciente=mock_paciente_orm)
    assert _extrair_info_paciente(doc6) == ("Mariana", "888")


def test_listar_documentos_resiliente(monkeypatch):
    docs = [
        MockDocumento(documento_id="DOC-1", dados_extraidos={"paciente": None}),
        MockDocumento(documento_id="DOC-2", dados_extraidos={"paciente": "Carlos"}),
        MockDocumento(documento_id="DOC-3", dados_extraidos={"paciente": {"nome": "João", "cpf": "111"}}),
        MockDocumento(documento_id="DOC-4", dados_extraidos="invalid-json"),
    ]

    mock_repo = MagicMock()
    mock_repo.listar_todos.return_value = docs
    monkeypatch.setattr("app.controllers.historico.DatabaseRepository", lambda db: mock_repo)

    resultado = listar_documentos(skip=0, limit=50, db=MagicMock())
    assert len(resultado) == 4
    assert resultado[0]["paciente_nome"] is None
    assert resultado[1]["paciente_nome"] == "Carlos"
    assert resultado[2]["paciente_nome"] == "João"
    assert resultado[2]["paciente_cpf"] == "111"
    assert resultado[3]["paciente_nome"] is None
