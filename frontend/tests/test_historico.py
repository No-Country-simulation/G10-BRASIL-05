import pytest

from utils.historico import (
    FILTRO_TODOS,
    STATUS_APROVADO,
    STATUS_DESCONHECIDO,
    STATUS_EM_AUDITORIA,
    STATUS_URGENCIA,
    filtrar_por_status,
    identificar_status,
    montar_linhas_da_tabela,
)


def _documento_com_destino(destino: str, documento_id: str = "DOC-1") -> dict:
    return {"documento_id": documento_id, "decisao_roteamento": {"destino_principal": destino}}


@pytest.fixture
def documentos():
    return [
        _documento_com_destino("Fluxo_Padrao", "DOC-1"),
        _documento_com_destino("Fila_Emergencia_Medica", "DOC-2"),
        _documento_com_destino("Auditoria_Humana", "DOC-3"),
        _documento_com_destino("Fluxo_Padrao", "DOC-4"),
    ]


@pytest.mark.parametrize(
    "destino, status_esperado",
    [
        ("Fluxo_Padrao", STATUS_APROVADO),
        ("Fila_Emergencia_Medica", STATUS_URGENCIA),
        ("Auditoria_Humana", STATUS_EM_AUDITORIA),
        ("Destino_Novo", STATUS_DESCONHECIDO),
    ],
)
def test_identifica_status_pelo_destino(destino, status_esperado):
    assert identificar_status(_documento_com_destino(destino)) == status_esperado


def test_documento_sem_roteamento_fica_sem_classificacao():
    assert identificar_status({}) == STATUS_DESCONHECIDO
    assert identificar_status({"decisao_roteamento": None}) == STATUS_DESCONHECIDO


def test_filtro_todos_mantem_todos_os_documentos(documentos):
    assert filtrar_por_status(documentos, FILTRO_TODOS) == documentos


@pytest.mark.parametrize(
    "filtro, ids_esperados",
    [
        (STATUS_APROVADO, ["DOC-1", "DOC-4"]),
        (STATUS_URGENCIA, ["DOC-2"]),
        (STATUS_EM_AUDITORIA, ["DOC-3"]),
    ],
)
def test_filtra_documentos_por_status(documentos, filtro, ids_esperados):
    ids = [documento["documento_id"] for documento in filtrar_por_status(documentos, filtro)]

    assert ids == ids_esperados


def test_linha_da_tabela_usa_traco_para_campos_ausentes():
    linha = montar_linhas_da_tabela([{}])[0]

    assert linha["Documento"] == "-"
    assert linha["Paciente"] == "-"
    assert linha["Confiança"] == "-"


def test_linha_da_tabela_formata_a_confianca_em_porcentagem():
    documento = {
        "documento_id": "DOC-1",
        "classificacao": {"score_confianca_classificacao": 0.96},
        "dados_extraidos": {"paciente": {"nome": "Maria"}},
        "decisao_roteamento": {"destino_principal": "Fluxo_Padrao"},
    }

    linha = montar_linhas_da_tabela([documento])[0]

    assert linha["Confiança"] == "96%"
    assert linha["Paciente"] == "Maria"
    assert linha["Status"] == "✅ Aprovado"