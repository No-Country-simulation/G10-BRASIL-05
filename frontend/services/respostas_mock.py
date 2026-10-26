from copy import deepcopy

RESPOSTA_ROTINA = {
    "status": "processado",
    "documento_id": "DOC-CLIN-2026-0001",
    "classificacao": {
        "tipo_documento": "Receituário Médico",
        "especialidade": "Clínica Geral",
        "nivel_prioridade": "Rotina",
        "score_confianca_classificacao": 0.96,
    },
    "dados_extraidos": {
        "paciente": {"nome": "Maria Aparecida Souza", "idade": 34},
        "medico_solicitante": {"nome": "Dr. Paulo Andrade", "crm": "123456-SP"},
        "medicamentos": [
            {
                "nome": "Amoxicilina",
                "dosagem": "500 mg",
                "posologia": "1 cápsula a cada 8 horas por 7 dias",
            }
        ],
        "diagnostico_principal": "Faringite aguda",
        "cid_sugerido": "J02.9",
    },
    "decisao_roteamento": {
        "destino_principal": "Fluxo_Padrao",
        "requer_auditoria_humana": False,
        "justificativa_roteamento": "Documento completo, CRM válido e alta confiança na extração.",
        "notificacao_gerada": None,
    },
    "armazenamento_oci": {
        "bucket": "mediflow-documentos-clinicos",
        "caminho_objeto": "processados/rotina/DOC-CLIN-2026-0001.json",
        "status_backup": "sucesso",
    },
}

RESPOSTA_URGENCIA = {
    "status": "processado",
    "documento_id": "DOC-CLIN-2026-8942",
    "classificacao": {
        "tipo_documento": "Laudo de Exame de Imagem",
        "especialidade": "Radiologia / Pneumologia",
        "nivel_prioridade": "Urgente",
        "score_confianca_classificacao": 0.99,
    },
    "dados_extraidos": {
        "paciente": {"nome": "Carlos Eduardo Mendes", "idade": 52},
        "medico_solicitante": {"nome": "Dra. Renata Silveira", "crm": "145892-SP"},
        "exame_realizado": "Tomografia de Torax com contraste",
        "diagnostico_principal": "Tromboembolismo Pulmonar Agudo (TEP)",
        "cid_sugerido": "I26.9",
    },
    "decisao_roteamento": {
        "destino_principal": "Fila_Emergencia_Medica",
        "requer_auditoria_humana": False,
        "justificativa_roteamento": "Achado critico de alta gravidade (TEP agudo) detectado em paciente sintomatico.",
        "notificacao_gerada": {
            "canal": "Alerta_Plantao_Medico",
            "mensagem": "ALERTA URGENTE: Laudo critico de TEP Agudo para paciente Carlos Eduardo Mendes no Pronto-Socorro.",
        },
    },
    "armazenamento_oci": {
        "bucket": "mediflow-documentos-clinicos",
        "caminho_objeto": "processados/urgentes/DOC-CLIN-2026-8942.json",
        "status_backup": "sucesso",
    },
}

RESPOSTA_AMBIGUA = {
    "status": "processado",
    "documento_id": "DOC-CLIN-2026-0003",
    "classificacao": {
        "tipo_documento": "Receituário Médico",
        "especialidade": "Não identificada",
        "nivel_prioridade": "Indefinido",
        "score_confianca_classificacao": 0.58,
    },
    "dados_extraidos": {
        "paciente": {"nome": "João P. Lima", "idade": None},
        "medico_solicitante": {"nome": "Não legível", "crm": None},
        "medicamentos": [
            {
                "nome": "Losartana (trecho ilegível)",
                "dosagem": None,
                "posologia": None,
            }
        ],
        "diagnostico_principal": None,
        "cid_sugerido": None,
    },
    "decisao_roteamento": {
        "destino_principal": "Auditoria_Humana",
        "requer_auditoria_humana": True,
        "justificativa_roteamento": "CRM ausente e trechos ilegíveis reduziram a confiança da extração.",
        "notificacao_gerada": None,
    },
    "armazenamento_oci": {
        "bucket": "mediflow-documentos-clinicos",
        "caminho_objeto": "auditoria_humana/DOC-CLIN-2026-0003.json",
        "status_backup": "sucesso",
    },
}

def _variar_resposta(base: dict, documento_id: str, nome_paciente: str) -> dict:
    resposta = deepcopy(base)
    resposta["documento_id"] = documento_id
    resposta["dados_extraidos"]["paciente"]["nome"] = nome_paciente
    return resposta


HISTORICO_MOCK = [
    RESPOSTA_URGENCIA,
    RESPOSTA_ROTINA,
    RESPOSTA_AMBIGUA,
    _variar_resposta(RESPOSTA_ROTINA, "DOC-CLIN-2026-0004", "Ana Beatriz Lima"),
    _variar_resposta(RESPOSTA_ROTINA, "DOC-CLIN-2026-0005", "Roberto Alves Pinto"),
    _variar_resposta(RESPOSTA_AMBIGUA, "DOC-CLIN-2026-0006", "M. Souza"),
]

def _montar_item_de_auditoria(
    documento_id: str,
    nome_paciente: str,
    nivel_prioridade: str,
    score: float,
) -> dict:
    item = _variar_resposta(RESPOSTA_AMBIGUA, documento_id, nome_paciente)
    item["documento_texto"] = (
        f"RECEITUARIO MEDICO. Paciente: {nome_paciente}. "
        "Medico: nome ilegivel, CRM ausente. Prescricao: Losartana (trecho ilegivel)."
    )
    item["classificacao"]["nivel_prioridade"] = nivel_prioridade
    item["classificacao"]["score_confianca_classificacao"] = score
    return item


FILA_AUDITORIA_MOCK = [
    _montar_item_de_auditoria("DOC-CLIN-2026-0003", "João P. Lima", "Indefinido", 0.58),
    _montar_item_de_auditoria("DOC-CLIN-2026-0006", "M. Souza", "Rotina", 0.66),
    _montar_item_de_auditoria("DOC-CLIN-2026-0007", "Paulo R. Nunes", "Urgente", 0.62),
]