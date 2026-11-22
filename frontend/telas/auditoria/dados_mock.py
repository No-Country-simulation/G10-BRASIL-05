"""Dados mockados para demonstração e conferência da tela de Revisão / Auditoria."""

MOCKS_AUDITORIA_FILA = [
    {
        "documento_id": "REV-20261122-01",
        "versao": 1,
        "tipo_documento": "EXAME",
        "score_confianca": 0.98,
        "nivel_prioridade": "URGENTE",
        "destino_principal": "Auditoria_Humana",
        "motivo_revisao": "Monitoramento de anticoagulação: Tempo de Protrombina com INR em 0,92 (abaixo da faixa terapêutica alvo de 2,0 a 3,0). Necessita avaliação clínica para ajuste posológico.",
        "etapa_revisao": "AVALIACAO_LABORATORIAL",
        "justificativa_roteamento": "INR sub-terapêutico identificado em paciente com indicação de anticoagulação.",
        "created_at": "2026-11-22T10:15:00",
        "fonte_original_disponivel": True,
        "documento_texto": (
            "MENA DIAGNÓSTICO\n"
            "CNPJ: 31.876.181/0008-14\n"
            "O.S.: 140-064200 - RG: -\n"
            "Paciente: Maria Eni Gomes - CPF: 68227639615\n"
            "Idade: 61 anos - Feminino - Data de Nasc.: 11/07/1964\n"
            "Médico(a) Dr(a): 00108769 - Patricia Rosa Pinheiro\n"
            "Categoria: Sus_Leste - Udi Lote 3 / Municipal\n"
            "Data de cadastro: 11/04/2026 19:42:57 Saída: 16/04/2026\n"
            "Amostra colhida em: 11/04/2026\n\n"
            "TEMPO DE PROTROMBINA\n"
            "Material: Plasma (Citrato)\n"
            "Método: Coagulométrico\n\n"
            "Resultado:\n"
            "Tempo de Protrombina: 10,80 segundos (Valores de Referência: 10,0 a 14,0 segundos)\n"
            "Atividade: 100 % (Valores de Referência: 70 a 100 %)\n"
            "INR: 0,92 (Valores de Referência: 1,00 a 1,25)\n\n"
            "Valores para indicações terapêuticas (INR Alvo):\n"
            "a) Anticoagulação pré e per-operatória: Variação 2,0 - 3,0 / Alvo 2,5\n"
            "b) Cirurgias de costelas, outras cirurgias: Variação 1,5 - 2,5 / Alvo 2,0\n"
            "c) Prevenção de trombose venosa primária ou secundária: Variação 2,0 - 3,0 / Alvo 2,5\n"
            "d) Trombose venosa ativa, embolia pulmonar prevenção de trombose venosa recorrente: Variação 2,0 - 4,0 / Alvo 3,0\n"
            "e) Prevenção de trombo-embolia arterial e portadores de válvulas cardíacas: Variação 3,0 - 4,5 / Alvo 3,5\n"
            "f) Risco elevado de hemorragia: Variação 5,0 - 5,5 / Alvo 5,25\n\n"
            "Histórico prévio:\n"
            "Em 10/04/26: 11,10 s | Em 08/04/26: 10,50 s\n\n"
            "Assinado Eletronicamente por: Bianca Batista Freitas - CRBM 23012 em: 11/04/2026 22:59:14\n"
            "Assinatura Digital: 313A75CC4BD67461AF654B1EA95FEF7B\n"
            "Responsável Técnica: Dr. Joao Paulo Pimenta - CRBM 10327"
        ),
        "dados_extraidos": {
            "paciente": {
                "nome": "Maria Eni Gomes",
                "cpf": "682.276.396-15",
                "idade": 61,
                "sexo": "Feminino",
            },
            "medico_solicitante": {
                "nome": "Dra. Patricia Rosa Pinheiro",
                "crm": "00108769",
                "uf": "SP",
            },
            "diagnostico_principal": "Coagulograma - Tempo de Protrombina 10,80s e INR 0,92 (Sub-terapêutico)",
            "cid_sugerido": "Z51.81",
            "medicamentos": [
                {"nome": "Varfarina Sódica", "dosagem": "5 mg", "frequencia": "1 comprimido VO/dia (dose a reavaliar)"},
            ],
            "alergias": ["Sem registros de alergias no laudo"],
            "observacoes": (
                "Laudo do MENA Diagnóstico (OS: 140-064200). "
                "INR em 0,92 está abaixo do alvo terapêutico para anticoagulação (alvo usual: 2,0 a 3,0). "
                "Responsável técnica: Dr. Joao Paulo Pimenta (CRBM 10327)."
            ),
        },
        "classificacao": {
            "tipo_documento": "EXAME",
            "especialidade": "Hematologia / Clínica Geral",
            "nivel_prioridade": "URGENTE",
            "score_confianca_classificacao": 0.98,
        },
        "decisao_roteamento": {
            "destino_principal": "Auditoria_Humana",
            "requer_auditoria_humana": True,
            "justificativa_roteamento": "Paciente em controle de anticoagulação com INR abaixo da faixa terapêutica desejada.",
        },
    },
    {
        "documento_id": "REV-20261122-02",
        "versao": 1,
        "tipo_documento": "RECEITA",
        "score_confianca": 0.88,
        "nivel_prioridade": "URGENTE",
        "destino_principal": "Auditoria_Humana",
        "motivo_revisao": "Conflito clínico grave: alergia a Penicilinas relatada no histórico versus Amoxicilina prescrita. Risco de anafilaxia.",
        "etapa_revisao": "CONFLITO_ALERGIA",
        "justificativa_roteamento": "Possível risco de reação alérgica adversa grave (conflito farmacológico).",
        "created_at": "2026-11-22T09:40:00",
        "fonte_original_disponivel": True,
        "documento_texto": (
            "CLÍNICA INTEGRADA DE SAÚDE DA FAMÍLIA\n"
            "RECEITUÁRIO MÉDICO AMBULATORIAL\n"
            "Data: 22/11/2026 Hora: 09:35\n\n"
            "PACIENTE: Cláuria Carvalho Ribeiro\n"
            "CPF: 819.302.114-88 | IDADE: 42 anos\n"
            "MÉDICO: Dra. Mariana Vasconcelos Rios - CRM 32.140-RJ\n\n"
            "PRESCRIÇÃO:\n"
            "1. Amoxicilina + Clavulanato de Potássio 875/125 mg ---------- 14 comprimidos\n"
            "   Tomar 1 comprimido via oral de 12 em 12 horas por 7 dias.\n\n"
            "2. Ibuprofeno 600 mg ---------------------------------------- 10 comprimidos\n"
            "   Tomar 1 comprimido via oral de 8 em 8 horas se dor ou febre por até 3 dias.\n\n"
            "HISTÓRICO REGISTRADO NO PRONTUÁRIO:\n"
            "Alergia severa a Penicilina e derivados betalactâmicos (episódio prévio com edema de glote)."
        ),
        "dados_extraidos": {
            "paciente": {
                "nome": "Cláuria Carvalho Ribeiro",
                "cpf": "819.302.114-88",
                "idade": 42,
                "sexo": "Feminino",
            },
            "medico_solicitante": {
                "nome": "Dra. Mariana Vasconcelos Rios",
                "crm": "32140",
                "uf": "RJ",
            },
            "diagnostico_principal": "Amigdalite Bacteriana Aguda com hipersensibilidade a betalactâmicos",
            "cid_sugerido": "J03.0",
            "medicamentos": [
                {"nome": "Amoxicilina + Clavulanato de Potássio", "dosagem": "875/125 mg", "frequencia": "12/12h por 7 dias"},
                {"nome": "Ibuprofeno", "dosagem": "600 mg", "frequencia": "8/8h se dor"},
            ],
            "alergias": ["Penicilina", "Betalactâmicos"],
            "observacoes": "Necessário substituir antimicrobiano por Azitromicina devido a contraindicação de Penicilinas.",
        },
        "classificacao": {
            "tipo_documento": "RECEITA",
            "especialidade": "Clínica Geral",
            "nivel_prioridade": "URGENTE",
            "score_confianca_classificacao": 0.88,
        },
        "decisao_roteamento": {
            "destino_principal": "Auditoria_Humana",
            "requer_auditoria_humana": True,
            "justificativa_roteamento": "Conflito alérgico detectado na prescrição médica.",
        },
    },
    {
        "documento_id": "REV-20261122-03",
        "versao": 1,
        "tipo_documento": "RELATORIO_ALTA",
        "score_confianca": 0.58,
        "nivel_prioridade": "ROTINA",
        "destino_principal": "Auditoria_Humana",
        "motivo_revisao": "Baixa confiança de OCR (58%): falha de leitura no carimbo profissional do médico e posologia sem unidade.",
        "etapa_revisao": "BAIXA_CONFIANCA_OCR",
        "justificativa_roteamento": "Extração incerta de dados obrigatórios. Requer verificação humana.",
        "created_at": "2026-11-22T08:20:00",
        "fonte_original_disponivel": True,
        "documento_texto": (
            "HOSPITAL SANTA LÚCIA - RELATÓRIO DE ALTA HOSPITALAR\n"
            "Data de internação: 19/11/2026 | Data de alta: 22/11/2026\n\n"
            "PACIENTE: Beatriz Helena Martins Sousa\n"
            "CPF: 245.444.123-90 | IDADE: 32 anos\n\n"
            "PROCEDIMENTO REALIZADO: Colecistectomia videolaparoscópica eletiva.\n"
            "Evolução pós-operatória favorável, ferida operatória limpa.\n\n"
            "PRESCRIÇÃO DOMICILIAR:\n"
            "1. Dipirona 500 mg VO se dor até 6/6h.\n"
            "2. Cetoprofeno 100 mg VO de 12/12h por 3 dias.\n\n"
            "MÉDICO ASSISTENTE:\n"
            "Dr. Carlos Eduardo Nogueira - CRM 19.820-MG"
        ),
        "dados_extraidos": {
            "paciente": {
                "nome": "Beatriz Helena Martins Sousa",
                "cpf": "245.444.123-90",
                "idade": 32,
                "sexo": "Feminino",
            },
            "medico_solicitante": {
                "nome": "Dr. Carlos Eduardo Nogueira",
                "crm": "19820",
                "uf": "MG",
            },
            "diagnostico_principal": "Pós-operatório de colecistectomia videolaparoscópica",
            "cid_sugerido": "K80.2",
            "medicamentos": [
                {"nome": "Dipirona", "dosagem": "500 mg", "frequencia": "se dor até 6/6h"},
                {"nome": "Cetoprofeno", "dosagem": "100 mg", "frequencia": "12/12h por 3 dias"},
            ],
            "observacoes": "Carimbo médico com o último dígito parcialmente ilegível no scanner.",
        },
        "classificacao": {
            "tipo_documento": "RELATORIO_ALTA",
            "especialidade": "Cirurgia Geral",
            "nivel_prioridade": "ROTINA",
            "score_confianca_classificacao": 0.58,
        },
        "decisao_roteamento": {
            "destino_principal": "Auditoria_Humana",
            "requer_auditoria_humana": True,
            "justificativa_roteamento": "Score de OCR abaixo do limiar de segurança automatizada.",
        },
    },
]

MOCKS_AUDITORIA_GERAL = [
    {
        "documento_id": "REV-20261122-04",
        "arquivo": "REV-20261122-04.pdf",
        "paciente_nome": "Marcelo Fonseca Dias",
        "paciente_cpf": "118.994.205-33",
        "tipo_documento": "EXAME",
        "nivel_prioridade": "ROTINA",
        "score_confianca": 0.94,
        "status_processamento": "auditoria_aprovado",
        "destino_principal": "Fluxo_Padrao",
        "motivo_revisao": "Laudo radiológico conferido e aprovado pelo revisor clínico.",
        "justificativa_roteamento": "Aprovado sem ressalvas após revisão médica.",
        "created_at": "2026-11-21T18:30:00",
        "dados_extraidos": {
            "paciente": {"nome": "Marcelo Fonseca Dias", "cpf": "118.994.205-33"},
            "medico_solicitante": {"nome": "Dra. Renata Meireles", "crm": "55401", "uf": "SP"},
            "diagnostico_principal": "Radiografia de tórax PA e perfil dentro dos padrões de normalidade",
            "cid_sugerido": "R91",
        },
        "classificacao": {
            "tipo_documento": "EXAME",
            "especialidade": "Radiologia",
            "nivel_prioridade": "ROTINA",
            "score_confianca_classificacao": 0.94,
        },
        "decisao_roteamento": {
            "destino_principal": "Fluxo_Padrao",
            "requer_auditoria_humana": False,
            "justificativa_roteamento": "Aprovado sem ressalvas pelo auditor clínico.",
        },
    },
    {
        "documento_id": "REV-20261122-05",
        "arquivo": "REV-20261122-05.pdf",
        "paciente_nome": "Gabriel Santos Nogueira",
        "paciente_cpf": "319.442.887-55",
        "tipo_documento": "ATESTADO",
        "nivel_prioridade": "ROTINA",
        "score_confianca": 0.74,
        "status_processamento": "auditoria_corrigido",
        "destino_principal": "Auditoria_Humana",
        "motivo_revisao": "Atestado com correção de CID e dias de repouso validados pelo auditor.",
        "justificativa_roteamento": "Corrigido pelo médico auditor e integrado ao prontuário.",
        "created_at": "2026-11-21T16:15:00",
        "dados_extraidos": {
            "paciente": {"nome": "Gabriel Santos Nogueira", "cpf": "319.442.887-55"},
            "medico_solicitante": {"nome": "Dr. Paulo Henrique Lima", "crm": "61229", "uf": "BA"},
            "diagnostico_principal": "Gastroenterite e colite infecciosas",
            "cid_sugerido": "A09",
        },
        "classificacao": {
            "tipo_documento": "ATESTADO",
            "especialidade": "Clínica Médica",
            "nivel_prioridade": "ROTINA",
            "score_confianca_classificacao": 0.74,
        },
        "decisao_roteamento": {
            "destino_principal": "Auditoria_Humana",
            "requer_auditoria_humana": True,
            "justificativa_roteamento": "Atestado validado com correção de CID.",
        },
    },
]


def obter_mocks_auditoria_fila() -> list[dict]:
    """Retorna itens de exemplo pendentes de revisão humana na esteira clínica."""
    return list(MOCKS_AUDITORIA_FILA)


def obter_mocks_auditoria_geral() -> list[dict]:
    """Retorna itens de exemplo já revisados para histórico e conferência da tabela."""
    return list(MOCKS_AUDITORIA_GERAL)


def obter_mock_documento_por_id(documento_id: str) -> dict | None:
    """Busca um item mockado pelo identificador do documento."""
    for item in MOCKS_AUDITORIA_FILA:
        if item.get("documento_id") == documento_id:
            return item
    for item in MOCKS_AUDITORIA_GERAL:
        if item.get("documento_id") == documento_id:
            return item
    return None


def registrar_decisao_mock(documento_id: str, decisao: dict) -> dict:
    """Atualiza o estado de um documento mockado na esteira após a decisão humana."""
    idx_remover = None
    for i, item in enumerate(MOCKS_AUDITORIA_FILA):
        if item.get("documento_id") == documento_id:
            idx_remover = i
            break

    status_aprov = str(decisao.get("status_aprovacao") or "aprovado").lower()
    fila_enc = str(decisao.get("fila_encaminhamento") or "Rotina")

    if idx_remover is not None:
        item = MOCKS_AUDITORIA_FILA.pop(idx_remover)
        item["status_processamento"] = f"auditoria_{status_aprov}"
        item["motivo_revisao"] = f"Revisão concluída: {status_aprov.upper()}. Encaminhado para a fila {fila_enc.upper()}."
        item["nivel_prioridade"] = "URGENTE" if fila_enc == "Urgente" else "ROTINA"
        item["destino_principal"] = "Fila_Emergencia_Medica" if fila_enc == "Urgente" else "Fluxo_Padrao"
        MOCKS_AUDITORIA_GERAL.insert(0, item)

    return {
        "mensagem": "Decisão de revisão registrada com sucesso.",
        "documento_id": documento_id,
        "fila_encaminhamento": fila_enc,
    }
