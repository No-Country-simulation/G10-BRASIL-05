import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agent.graph import executar_agente_triagem
from app.repositories.database import init_db

init_db()
client = TestClient(app, raise_server_exceptions=False)


def test_grafo_cenario_urgencia_tep():
    """Valida o Cenário 2 do briefing: detecção de emergência crítica (TEP agudo)."""
    estado_entrada = {
        "documento_id": "TEST-URG-001",
        "tipo_arquivo": "pdf",
        "canal_origem": "Pronto_Socorro",
        "documento_texto": (
            "Hospital Geral - Laudo de Tomografia Computadorizada\n"
            "Paciente: Carlos Eduardo Mendes, 52 anos. Médico: Dra. Renata Silveira CRM: 145892-SP.\n"
            "Indicação: Dispneia súbita e dor torácica pleurítica.\n"
            "Conclusão: Falha de enchimento em artéria pulmonar principal direita, "
            "compatível com Tromboembolismo Pulmonar Agudo (TEP)."
        ),
    }

    resultado = executar_agente_triagem(estado_entrada)

    assert resultado["status"] == "roteado"
    assert resultado["is_urgente"] is True
    assert resultado["destino_principal"] == "Fila_Emergencia_Medica"
    assert resultado["notificacao_gerada"] is not None
    assert resultado["notificacao_gerada"]["canal"] == "Alerta_Plantao_Medico"
    assert "TEP" in resultado["diagnostico_principal"] or "Tromboembolismo" in resultado["diagnostico_principal"]
    assert resultado["cid_sugerido"] == "I26.9"


def test_grafo_cenario_rotina_receita():
    """Valida o fluxo padrão aprovado de receituário médico para farmácia."""
    estado_entrada = {
        "documento_id": "TEST-ROT-002",
        "tipo_arquivo": "texto",
        "canal_origem": "Ambulatorio",
        "documento_texto": (
            "Receituário Médico - Clínica Médica\n"
            "Paciente: Mariana Souza, 35 anos. Médico: Dr. Lucas Ramos CRM: 87654-SP.\n"
            "Uso oral: Losartana Potássica 50mg - Tomar 1 comprimido pela manhã.\n"
            "Diagnóstico: Hipertensão Arterial Sistêmica."
        ),
    }

    resultado = executar_agente_triagem(estado_entrada)

    assert resultado["status"] == "roteado"
    assert resultado["is_urgente"] is False
    assert resultado["tipo_documento"] == "RECEITA"
    # Sem chave de LLM a classificação vem do fallback heurístico, que sempre exige revisão humana (SCRUM-57)
    assert resultado["destino_principal"] == "Auditoria_Humana"
    assert resultado["requer_auditoria_humana"] is True
    assert resultado["score_confianca_classificacao"] < 0.75


def test_grafo_cenario_ambiguo_auditoria():
    """Valida o Cenário 3 do briefing: documento incompleto direcionado para Human-in-the-Loop."""
    estado_entrada = {
        "documento_id": "TEST-AMB-003",
        "tipo_arquivo": "texto",
        "canal_origem": "Telemedicina",
        "documento_texto": "Texto ilegível sem paciente e sem CRM.",
    }

    resultado = executar_agente_triagem(estado_entrada)

    assert resultado["status"] == "roteado"
    assert resultado["is_urgente"] is False
    assert resultado["requer_auditoria_humana"] is True
    assert resultado["destino_principal"] == "Auditoria_Humana"
    assert len(resultado["inconsistencias"]) > 0


def test_endpoint_triagem_com_grafo_integrado():
    """Valida o endpoint POST /triagem consumindo o grafo compilado ponta a ponta."""
    payload = {
        "documento_id": "DOC-GRAFO-TEST-004",
        "tipo_arquivo": "texto",
        "canal_origem": "Pronto_Socorro",
        "documento_texto": (
            "Paciente: Carlos Eduardo Mendes, 52 anos. Dr. Renato CRM: 145892-SP. "
            "Laudo de Tomografia de Tórax: Tromboembolismo Pulmonar Agudo detectado."
        ),
    }

    response = client.post("/triagem", json=payload)
    assert response.status_code == 200
    dados = response.json()

    assert dados["documento_id"] == "DOC-GRAFO-TEST-004"
    assert dados["decisao_roteamento"]["destino_principal"] == "Fila_Emergencia_Medica"
    assert dados["decisao_roteamento"]["notificacao_gerada"] is not None
    assert dados["classificacao"]["nivel_prioridade"] == "EMERGENCIA"
    assert "armazenamento_oci" in dados
