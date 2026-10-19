# [0004] - Adoção de Streamlit no Frontend + Persistência Híbrida (PostgreSQL + OCI) e Divisão para 8 Integrantes

- **Data:** 2026-10-19
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado (Substitui parcialmente a ADR 0002 no tocante ao Next.js)

---

## 1. Por quê? (Contexto e Motivação)
Ao auditar o backlog oficial do projeto no Jira (`SCRUM-33` a `SCRUM-96`) em confronto com o enunciado oficial (`mediflow (1).pdf`), constatou-se que:
1. O backlog e o desafio oficial preveem o uso de **Streamlit** (`SCRUM-78`) para o painel de triagem e auditoria médica (Human-in-the-Loop).
2. Manter toda a stack em **100% Python** (Streamlit + FastAPI + LangGraph + SQLAlchemy) elimina o atrito de múltiplos runtimes (Node.js/TypeScript vs Python) e acelera a entrega para uma equipe de **8 pessoas**.
3. O uso combinado de **PostgreSQL** (para consultas estruturadas de histórico, fila de auditoria e trilha de decisões) com **OCI Object Storage** (para armazenamento segregado dos arquivos e JSONs de backup nos buckets Always Free) garante robustez e velocidade nas telas.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Unificar a linguagem do repositório em **Python**, permitindo que qualquer membro ajude em qualquer camada.
- Manter o desacoplamento arquitetural: o `frontend/` (Streamlit) consome exclusivamente a API REST do `backend/` (FastAPI), sem acessar o PostgreSQL ou o OCI diretamente.
- Distribuir o trabalho técnico em **8 frentes claras (P1 a P8)** onde todos programam e todos participam da documentação e apresentação final.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Substituída):** Frontend em Next.js/TypeScript (ADR 0002). Substituída para alinhar 100% com o card `SCRUM-78` do Jira, com o PDF do desafio e maximizar a velocidade da equipe em Python.
- **Alternativa B (Escolhida):** Monorepo 100% Python desacoplado:
  - `frontend/`: Aplicação **Streamlit** modularizada (páginas de Upload/Triagem, Painel de Auditoria Humana e Histórico), comunicando-se via cliente HTTP (`requests`/`httpx`) com a FastAPI.
  - `backend/`: **FastAPI + LangGraph + SQLAlchemy (PostgreSQL) + SDK OCI Object Storage**.

### Novos Cards Criados no Jira para Completar o Escopo:
- `SCRUM-97`: Configurar PostgreSQL, SQLAlchemy e modelos de dados (Models)
- `SCRUM-98`: Repositório PostgreSQL para persistência de triagens e auditoria
- `SCRUM-99`: Endpoint `POST /auditoria/{id}/decisao` para aprovar, corrigir ou rejeitar triagem
- `SCRUM-100`: Tela Streamlit de Upload, Triagem Clínica e Histórico

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `frontend/`, `backend/`, `AGENTS/AGENTS.md`, `PLANO_DE_ACAO.md`, `DECISIONS/patrickgutem-create/`
- **Arquivos Criados / Modificados:** `DECISIONS/patrickgutem-create/0004-adocao-streamlit-e-postgresql.md`, `DECISIONS/patrickgutem-create/0002-arquitetura-monorepo-desacoplado.md`, `AGENTS/AGENTS.md`, `PLANO_DE_ACAO.md`

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Stack 100% Python, curva de aprendizado mínima, contratos Pydantic compartilháveis, alinhamento total com o backlog do Jira (`SCRUM-33` a `SCRUM-100`).
- **Riscos / Trade-offs:** Menor flexibilidade de estilização CSS avançada no Streamlit em comparação ao React, compensada pela produtividade imediata em dashboards clínicos.
- **Validação / Testes:** Testes automatizados com Pytest no backend e validação dos 3 cenários obrigatórios (Rotina, Urgência e Ambíguo) na interface Streamlit.
