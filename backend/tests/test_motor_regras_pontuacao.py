import pytest
from app.agent.nodes.avaliador import node_avaliacao
from app.agent.state import GraphState


def test_motor_regras_faixa_confiavel_direto():
    """Documento completo e legível com score >= 85 atinge CONFIAVEL_DIRETO."""
    estado: GraphState = {
        "documento_texto": (
            "Hospital Central - Laudo Tomografia Computadorizada\n"
            "Paciente: Juliana Prado Ferreira, 42 anos, CPF: 234.567.890-11\n"
            "Médico Solicitante: Dr. Fernando Albuquerque, CRM: 112233-SP\n"
            "Diagnóstico: Apendicite aguda fase supurativa.\n"
            "Conduta: Encaminhamento cirúrgico imediato."
        ),
        "qualidade_documento": {"status": "adequada"},
        "legibilidade_documento": "legivel",
        "paciente": {"nome": "Juliana Prado Ferreira", "idade": 42, "cpf": "23456789011"},
        "medico_solicitante": {"nome": "Dr. Fernando Albuquerque", "crm": "112233", "crm_uf": "SP"},
        "tipo_documento": "LAUDO",
        "diagnostico_principal": "Apendicite aguda",
        "exame_realizado": "Tomografia Computadorizada",
        "cid_sugerido": "K35.8",
        "cpf_validacao_falhou": False,
    }

    resultado = node_avaliacao(estado)

    detalhes = resultado["score_detalhes"]
    assert detalhes["etapa_1_qualidade"]["pontos"] == 15.0
    assert detalhes["etapa_1_qualidade"]["aprovado"] is True

    assert detalhes["etapa_2_cadastro"]["pontos"] == 20.0
    assert detalhes["etapa_2_cadastro"]["aprovado"] is True

    assert detalhes["etapa_3_regulatorio"]["pontos"] == 15.0
    assert detalhes["etapa_3_regulatorio"]["aprovado"] is True

    assert detalhes["etapa_4_clinico"]["pontos"] == 50.0
    assert detalhes["etapa_4_clinico"]["aprovado"] is True

    assert resultado["score_total"] == 100.0
    assert resultado["faixa_motor_regras"] == "CONFIAVEL_DIRETO"
    assert resultado["requer_auditoria_humana"] is False


def test_motor_regras_faixa_revisao_humana():
    """Documento com dados parciais (sem CRM e sem identificador regulatório) cai na faixa REVISAO_HUMANA."""
    estado: GraphState = {
        "documento_texto": (
            "Receituário Médico - Clínica Médica\n"
            "Paciente: Mariana Souza, 35 anos.\n"
            "Uso oral: Losartana 50mg pela manhã."
        ),
        "qualidade_documento": {"status": "adequada"},
        "legibilidade_documento": "legivel",
        "paciente": {"nome": "Mariana Souza", "idade": 35, "cpf": None},
        "medico_solicitante": {"nome": "Dr. Lucas Ramos", "crm": None, "crm_uf": None},
        "tipo_documento": "RECEITA",
        "medicamentos": [{"medicamento": "Losartana", "dosagem": "50mg"}],
    }

    resultado = node_avaliacao(estado)

    detalhes = resultado["score_detalhes"]
    assert detalhes["etapa_1_qualidade"]["pontos"] == 15.0
    assert detalhes["etapa_2_cadastro"]["pontos"] == 20.0
    # Sem CRM e sem CPF/CNS: ganha 5 pts, corte é 10 -> corte reprovado
    assert detalhes["etapa_3_regulatorio"]["pontos"] == 5.0
    assert detalhes["etapa_3_regulatorio"]["aprovado"] is False

    assert resultado["faixa_motor_regras"] == "REVISAO_HUMANA"
    assert resultado["requer_auditoria_humana"] is True


def test_motor_regras_faixa_pede_novo_documento():
    """Documento com pontuação global < 60 cai em PEDE_NOVO_DOCUMENTO."""
    estado: GraphState = {
        "documento_texto": "Texto curto sem identificação clara.",
        "qualidade_documento": {"status": "insuficiente"},
        "legibilidade_documento": "ilegivel",
        "paciente": {},
        "medico_solicitante": {},
    }

    resultado = node_avaliacao(estado)

    assert resultado["score_total"] < 60.0
    assert resultado["faixa_motor_regras"] == "PEDE_NOVO_DOCUMENTO"
    assert resultado["requer_auditoria_humana"] is True


def test_rotina_com_score_alto_nao_requer_auditoria():
    """Valida que nível ROTINA com pontuação >= 85 não exige revisão humana."""
    estado: GraphState = {
        "documento_texto": (
            "Receituário Médico de Rotina\n"
            "Paciente: José Ferreira, 50 anos, CPF: 111.222.333-44\n"
            "Médico: Dr. Carlos Santos, CRM: 12345-SP\n"
            "Prescrição: Dipirona 500mg uso oral se dor."
        ),
        "qualidade_documento": {"status": "adequada"},
        "legibilidade_documento": "legivel",
        "paciente": {"nome": "José Ferreira", "idade": 50, "cpf": "11122233344"},
        "medico_solicitante": {"nome": "Dr. Carlos Santos", "crm": "12345", "crm_uf": "SP"},
        "tipo_documento": "RECEITA",
        "nivel_prioridade": "ROTINA",
        "diagnostico_principal": "Hipertensão arterial",
        "cid_sugerido": "I10",
        "medicamentos": [{"medicamento": "Dipirona", "dosagem": "500mg"}],
    }

    resultado = node_avaliacao(estado)
    assert resultado["score_total"] >= 85.0
    assert resultado["requer_auditoria_humana"] is False
    assert resultado["motivo_revisao"] is None
    assert resultado["inconsistencias"] == []
    assert resultado["destino_principal"] == "Fluxo_Padrao"
