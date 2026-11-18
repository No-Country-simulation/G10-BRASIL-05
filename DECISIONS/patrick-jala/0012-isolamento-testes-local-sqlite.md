# [0012] - Isolamento dos testes locais com SQLite em memória

- **Data:** 2026-11-16
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

A suíte de testes do backend tentava inicializar o PostgreSQL configurado para desenvolvimento local e ficava dependente de um serviço externo ou container. Isso impede executar os testes unitários em uma máquina sem banco ativo e mistura configuração de teste com dados de desenvolvimento.

## 2. Para quê? (Objetivo e Resultados Esperados)

Executar os testes do backend sem depender de containers ou de uma instância PostgreSQL, mantendo explícita a distinção entre execução local e produção.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **PostgreSQL em container durante os testes (descartada):** adiciona dependência operacional que não é necessária para testes unitários.
- **SQLite em memória para a suíte de testes (escolhida):** isola os testes do banco local e da infraestrutura externa.

### Detalhamento da Solução:

O `conftest.py` define `APP_ENV=local` e `DATABASE_URL=sqlite://` antes de importar a aplicação. A configuração local do desenvolvedor é marcada com `APP_ENV=local`, sem alterar sua URL de PostgreSQL. Ambientes de produção definem `APP_ENV=production` e injetam a URL PostgreSQL apropriada por variável de ambiente.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/config/`, `backend/tests/`, `backend/`.
- **Arquivos Criados / Modificados:** `backend/tests/conftest.py`, `backend/tests/test_decisao_auditoria_endpoint.py`, `backend/app/config/logger.py`, `backend/app/main.py`, `backend/.env`, `backend/.env.example`.
- **Banco de Dados / Infra:** testes usam SQLite em memória; execução normal local e produção seguem a URL PostgreSQL configurada em seus ambientes.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** testes unitários não exigem Docker/PostgreSQL e não acessam o banco local do desenvolvedor.
- **Riscos / Trade-offs:** testes SQLite não substituem testes de integração PostgreSQL; o checkpoint LangGraph usa memória no ambiente local sem PostgresSaver.
- **Validação / Testes:** testes do grafo e da auditoria executados sem container, com SQLite em memória e prazo de 3 segundos nos POSTs de validação.
