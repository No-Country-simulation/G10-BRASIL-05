"""Dados semente para a tabela destinos_roteamento (filas de atendimento)."""

DADOS_DESTINOS_ROTEAMENTO = [
    {"codigo": "Fila_Atestados", "tipo": "FILA", "descricao": "Fila para triagem e validação de atestados"},
    {"codigo": "Fila_Atendimento_Geral", "tipo": "FILA", "descricao": "Fila para atendimento clínico geral"},
    {"codigo": "Fila_Auditoria_Humana", "tipo": "FILA", "descricao": "Fila de contingência para auditoria humana médica"},
    {"codigo": "Fila_Autorizacoes", "tipo": "FILA", "descricao": "Fila para autorização de guias e procedimentos TISS"},
    {"codigo": "Fila_Emergencia_Medica", "tipo": "FILA", "descricao": "Fila de urgência/emergência prioritária"},
    {"codigo": "Fila_Exames", "tipo": "FILA", "descricao": "Fila para agendamento e liberação de exames diagnósticos"},
    {"codigo": "Fila_Farmacia", "tipo": "FILA", "descricao": "Fila para dispensação e auditoria de receitas/fármacos"},
    {"codigo": "Fila_Fluxo_Padrao", "tipo": "FILA", "descricao": "Fila padrão de triagem de rotina"},
]
