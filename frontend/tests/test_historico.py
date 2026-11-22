import pytest

from utils.historico import (
    FILTROS_DE_STATUS,
    FILTRO_TODOS,
    OPCOES_FILTRO_STATUS,
    STATUS_APROVADO,
    STATUS_DESCONHECIDO,
    STATUS_EM_AUDITORIA,
    STATUS_REJEITADO,
    STATUS_URGENCIA,
    filtrar_por_status,
    identificar_status,
    montar_estilos_da_tabela,
    montar_linhas_da_tabela,
    montar_tabela_estilizada,
)


def _documento_com_destino(destino: str, documento_id: str = "DOC-1") -> dict:
    return {"documento_id": documento_id, "destino_principal": destino}


@pytest.fixture
def documentos():
    return [
        _documento_com_destino("Fluxo_Padrao", "DOC-1"),
        _documento_com_destino("Fila_Emergencia_Medica", "DOC-2"),
        _documento_com_destino("Auditoria_Humana", "DOC-3"),
        _documento_com_destino("Farmacia_Hospitalar", "DOC-4"),
    ]


@pytest.mark.parametrize(
    "destino, status_esperado",
    [
        ("Fluxo_Padrao", STATUS_APROVADO),
        ("Farmacia_Hospitalar", STATUS_APROVADO),
        ("Fila_Emergencia_Medica", STATUS_URGENCIA),
        ("Auditoria_Humana", STATUS_EM_AUDITORIA),
        ("Nao_Elegivel", STATUS_REJEITADO),
        ("Descarte", STATUS_REJEITADO),
        ("Destino_Novo", STATUS_DESCONHECIDO),
    ],
)
def test_identifica_status_pelo_destino(destino, status_esperado):
    assert identificar_status(_documento_com_destino(destino)) == status_esperado


def test_documento_sem_destino_fica_sem_classificacao():
    assert identificar_status({}) == STATUS_DESCONHECIDO
    assert identificar_status({"destino_principal": None}) == STATUS_DESCONHECIDO


@pytest.mark.parametrize(
    "status_processamento, status_esperado",
    [
        ("auditoria_aprovado", STATUS_APROVADO),
        ("auditoria_corrigido", STATUS_APROVADO),
        ("auditoria_rejeitado", STATUS_REJEITADO),
        ("REJEITADO", STATUS_REJEITADO),
        ("rejeitado", STATUS_REJEITADO),
    ],
)
def test_documento_ja_auditado_usa_a_decisao_do_auditor(status_processamento, status_esperado):
    documento = {
        "destino_principal": "Auditoria_Humana",
        "status_processamento": status_processamento,
    }

    assert identificar_status(documento) == status_esperado


def test_documento_ainda_em_auditoria_continua_em_auditoria():
    documento = {"destino_principal": "Auditoria_Humana", "status_processamento": "em_auditoria"}

    assert identificar_status(documento) == STATUS_EM_AUDITORIA


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
    assert linha["Tipo"] == "-"
    assert linha["Prioridade"] == "-"
    assert linha["Confiança"] == "-"
    assert linha["Data"] == "-"


def test_linha_da_tabela_traduz_codigos_e_formata_confianca_e_data():
    documento = {
        "documento_id": "DOC-1",
        "tipo_documento": "RECEITA",
        "nivel_prioridade": "ROTINA",
        "score_confianca": 0.96,
        "destino_principal": "Fluxo_Padrao",
        "created_at": "2026-10-27T09:30:00",
    }

    assert montar_linhas_da_tabela([documento])[0] == {
        "Documento": "DOC-1",
        "Status": "Aprovado",
        "Tipo": "Receituário Médico",
        "Prioridade": "Rotina",
        "Confiança": "96%",
        "Data": "27/10/2026 06:30",
    }


def test_data_com_microssegundos_e_formatada():
    linha = montar_linhas_da_tabela([{"created_at": "2026-10-27T09:30:15.123456"}])[0]

    assert linha["Data"] == "27/10/2026 06:30"


def test_data_invalida_e_mostrada_como_veio():
    linha = montar_linhas_da_tabela([{"created_at": "ontem"}])[0]

    assert linha["Data"] == "ontem"

def test_documento_rejeitado_pode_ser_filtrado():
    documentos = [
        {"documento_id": "DOC-1", "destino_principal": "Auditoria_Humana", "status_processamento": "auditoria_rejeitado"},
        {"documento_id": "DOC-2", "destino_principal": "Fluxo_Padrao"},
    ]

    assert STATUS_REJEITADO in FILTROS_DE_STATUS
    assert [d["documento_id"] for d in filtrar_por_status(documentos, STATUS_REJEITADO)] == ["DOC-1"]


def test_linha_da_tabela_aceita_prioridade_no_formato_do_backend():
    linha = montar_linhas_da_tabela([{"nivel_prioridade": "Urgente"}])[0]

    assert linha["Prioridade"] == "Urgente"


def test_estilos_destacam_fundo_prioridade_e_confianca():
    documento = {
        "destino_principal": "Fila_Emergencia_Medica",
        "nivel_prioridade": "Urgente",
        "score_confianca": 0.5,
    }

    estilos = montar_estilos_da_tabela([documento], ["Documento", "Prioridade", "Confiança"])[0]

    assert estilos[0] == "background-color: #FDECEA;"
    assert "color: #C2410C" in estilos[1]
    assert "color: #C62828" in estilos[2]


def test_estilos_sem_dados_ficam_vazios():
    assert montar_estilos_da_tabela([{}], ["Documento", "Prioridade"]) == [["", ""]]


def test_tabela_estilizada_tem_uma_linha_por_documento():
    documentos = [_documento_com_destino("Fluxo_Padrao", "DOC-1"), _documento_com_destino("Auditoria_Humana", "DOC-2")]

    tabela = montar_tabela_estilizada(documentos)

    assert list(tabela.data["Documento"]) == ["DOC-1", "DOC-2"]


def test_corresponde_busca_por_nome_e_cpf():
    from utils.historico import corresponde_busca

    doc = {
        "documento_id": "DOC-CLIN-001",
        "paciente_nome": "Maria de Souza Silva",
        "paciente_cpf": "123.456.789-00",
        "tipo_documento": "RECEITA",
    }

    assert corresponde_busca(doc, "maria")
    assert corresponde_busca(doc, "SOUZA")
    assert corresponde_busca(doc, "123.456")
    assert corresponde_busca(doc, "doc-clin")
    assert corresponde_busca(doc, "receituario")
    assert not corresponde_busca(doc, "Carlos")


def test_filtrar_historico_completo_com_multiplos_criterios():
    from utils.historico import filtrar_historico_completo

    docs = [
        {
            "documento_id": "DOC-1",
            "paciente_nome": "Carlos Drummond",
            "tipo_documento": "LAUDO",
            "nivel_prioridade": "EMERGENCIA",
            "destino_principal": "Fila_Emergencia_Medica",
            "score_confianca": 0.99,
            "created_at": "2026-11-20T10:00:00",
        },
        {
            "documento_id": "DOC-2",
            "paciente_nome": "Clarice Lispector",
            "tipo_documento": "RECEITA",
            "nivel_prioridade": "ROTINA",
            "destino_principal": "Fluxo_Padrao",
            "score_confianca": 0.85,
            "created_at": "2026-11-21T10:00:00",
        },
    ]

    # Busca por nome
    res_busca = filtrar_historico_completo(docs, termo_busca="clarice")
    assert len(res_busca) == 1
    assert res_busca[0]["documento_id"] == "DOC-2"

    # Filtro por prioridade
    res_pri = filtrar_historico_completo(docs, filtro_prioridade="Emergência")
    assert len(res_pri) == 1
    assert res_pri[0]["documento_id"] == "DOC-1"

    # Ordenação mais recente
    res_ord = filtrar_historico_completo(docs, ordenacao="Mais recentes primeiro")
    assert res_ord[0]["documento_id"] == "DOC-2"


def test_calcular_metricas_historico():
    from utils.historico import calcular_metricas_historico

    docs = [
        {"destino_principal": "Fluxo_Padrao"},
        {"destino_principal": "Fila_Emergencia_Medica"},
        {"destino_principal": "Auditoria_Humana"},
        {"status_processamento": "auditoria_rejeitado"},
    ]

    metricas = calcular_metricas_historico(docs)
    assert metricas["total"] == 4
    assert metricas["aprovados"] == 1
    assert metricas["urgencias"] == 1
    assert metricas["em_auditoria"] == 1
    assert metricas["rejeitados"] == 1

