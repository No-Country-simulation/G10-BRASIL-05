"""Dados semente para estabelecimentos_saude, hospitais e clinicas."""

DADOS_ESTABELECIMENTOS_SAUDE = [
    {
        "id": 1,
        "tipo": "HOSPITAL",
        "nome": "Hospital Central MediFlow",
        "cnpj": "12.345.678/0001-90",
        "cidade_id": 1,
        "ativo": True,
    },
    {
        "id": 2,
        "tipo": "HOSPITAL",
        "nome": "UPA Pronto Atendimento 24h",
        "cnpj": "98.765.432/0001-10",
        "cidade_id": 1,
        "ativo": True,
    },
    {
        "id": 3,
        "tipo": "CLINICA",
        "nome": "Ambulatório Geral de Especialidades",
        "cnpj": "55.443.221/0001-33",
        "cidade_id": 2,
        "ativo": True,
    },
]

DADOS_HOSPITAIS = [
    {"estabelecimento_id": 1, "categoria_id": 1},
    {"estabelecimento_id": 2, "categoria_id": 1},
]

DADOS_CLINICAS = [
    {"estabelecimento_id": 3},
]
