"""Dados semente para usuarios_sistema."""
from typing import Any
from app.services.autenticacao import gerar_hash_senha

SENHA_PADRAO = "123456789101112"


def obter_dados_usuarios() -> list[dict[str, Any]]:
    senha_hash = gerar_hash_senha(SENHA_PADRAO)

    # 1. Administradores Gerais (Contas com e-mails normais/pessoais da equipe)
    admins_gerais: list[dict[str, Any]] = [
        {
            "email": "patrickgutem@gmail.com",
            "nome": "Patrick Gutenberg Gomes Duarte",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "Backend API (FastAPI & Orquestração)",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
        {
            "email": "liannacr23@gmail.com",
            "nome": "Lianna Ribeiro",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "Frontend (Streamlit: Triagem, Auditoria & Histórico)",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
        {
            "email": "profmarciojmorais@gmail.com",
            "nome": "Marcio Jose de Morais",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "QA, Dados Clínicos Sintéticos & Testes Automatizado",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
        {
            "email": "jp.botelhoo@gmail.com",
            "nome": "Joao Pedro Alves Botelho",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "Banco de Dados & Persistência (PostgreSQL + Auditoria)",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
        {
            "email": "phmeuzebio@gmail.com",
            "nome": "Pedro Henrique Marinho Euzebio",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "IA: Grafo de Decisão, Score & Urgência (LangGraph)",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
        {
            "email": "otaviools13@gmail.com",
            "nome": "Otávio Oliveira Santos",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "IA: Ingestão, Classificação & Extração (LLM)",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
        {
            "email": "adilson.manuel1@hotmail.com",
            "nome": "Adilson Gaspar Morais Manuel",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "Infra & Nuvem (OCI Object Storage Always Free)",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
        {
            "email": "pa298571@gmail.com",
            "nome": "Pedro Araujo",
            "senha_hash": senha_hash,
            "papel": "ADMIN_GERAL",
            "registro": None,
            "especialidade": "Coordenação, Setup & Contratos (Schemas Pydantic)",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": True,
        },
    ]

    # 2. Acessos Individuais da Equipe por Cargo (Diretor, Médico e Enfermeiro)
    membros_equipe = [
        ("Pedro Araujo", "pedro", "101001", "202001"),
        ("Lianna Ribeiro", "lianna", "101002", "202002"),
        ("Marcio Jose de Morais", "marcio", "101003", "202003"),
        ("Joao Pedro Alves Botelho", "joao", "101004", "202004"),
        ("Pedro Henrique Marinho Euzebio", "pedrohenrique", "101005", "202005"),
        ("Otávio Oliveira Santos", "otavio", "101006", "202006"),
        ("Adilson Gaspar Morais Manuel", "adilson", "101007", "202007"),
        ("Patrick Gutenberg Gomes Duarte", "patrick", "101008", "202008"),
    ]

    usuarios_cargos: list[dict[str, Any]] = []
    for nome, prefixo, crm_num, coren_num in membros_equipe:
        usuarios_cargos.extend([
            {
                "email": f"{prefixo}.diretor@mediflow.com.br",
                "nome": nome,
                "senha_hash": senha_hash,
                "papel": "DIRETOR",
                "registro": f"CRM {crm_num}-SP",
                "especialidade": "Diretoria Clínica & Governança",
                "ativo": True,
                "trocar_senha_obrigatorio": True,
                "pode_gerenciar_whatsapp": False,
            },
            {
                "email": f"{prefixo}.medico@mediflow.com.br",
                "nome": nome,
                "senha_hash": senha_hash,
                "papel": "MEDICO",
                "registro": f"CRM {crm_num}-SP",
                "especialidade": "Clínica Médica & Auditoria",
                "ativo": True,
                "trocar_senha_obrigatorio": True,
                "pode_gerenciar_whatsapp": False,
            },
            {
                "email": f"{prefixo}.enfermeiro@mediflow.com.br",
                "nome": nome,
                "senha_hash": senha_hash,
                "papel": "ENFERMEIRO",
                "registro": f"COREN {coren_num}-SP",
                "especialidade": "Triagem e Emergência",
                "ativo": True,
                "trocar_senha_obrigatorio": True,
                "pode_gerenciar_whatsapp": False,
            },
        ])

    # 3. Contas Genéricas de Teste Rápido
    usuarios_genericos: list[dict[str, Any]] = [
        {
            "email": "diretor@mediflow.com.br",
            "nome": "Dr. Diretor Clínico",
            "senha_hash": senha_hash,
            "papel": "DIRETOR",
            "registro": "CRM 110022-SP",
            "especialidade": "Gestão Hospitalar & Governança",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": False,
        },
        {
            "email": "medico@mediflow.com.br",
            "nome": "Dr. Médico Plantonista",
            "senha_hash": senha_hash,
            "papel": "MEDICO",
            "registro": "CRM 123456-SP",
            "especialidade": "Clínica Médica & Auditoria",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": False,
        },
        {
            "email": "enfermeiro@mediflow.com.br",
            "nome": "Enfermeiro Triagem",
            "senha_hash": senha_hash,
            "papel": "ENFERMEIRO",
            "registro": "COREN 654321-SP",
            "especialidade": "Triagem e Emergência",
            "ativo": True,
            "trocar_senha_obrigatorio": True,
            "pode_gerenciar_whatsapp": False,
        },
    ]

    return admins_gerais + usuarios_cargos + usuarios_genericos
