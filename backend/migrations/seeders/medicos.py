"""Dados semente para medicos e medico_especialidades."""

DADOS_MEDICOS = [
    {"id": 1, "crm": "145892", "uf": "SP", "nome": "Dra. Renata Silveira"},
    {"id": 2, "crm": "87654", "uf": "SP", "nome": "Dr. Lucas Ramos"},
    {"id": 3, "crm": "112233", "uf": "SP", "nome": "Dr. Roberto Silva"},
]

DADOS_MEDICO_ESPECIALIDADES = [
    {"medico_id": 1, "especialidade_id": 1},
    {"medico_id": 1, "especialidade_id": 2},
    {"medico_id": 2, "especialidade_id": 3},
    {"medico_id": 3, "especialidade_id": 4},
]
