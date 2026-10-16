# [0001] - Integração com Jira Cloud via MCP Server

- **Data:** 2026-10-14
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Necessidade de conectar o ambiente do desenvolvedor e o assistente de IA ao Jira Cloud da equipe (projeto SCRUM - G10-5 da No-Country) para acompanhar o backlog do Hackathon, consultar especificações de tarefas e sincronizar o progresso sem atrito de contexto.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
Permitir consulta instantânea e manipulação de issues, sprints e requisitos do projeto SCRUM diretamente pelo agente e pela IDE, mantendo conformidade com as regras de desenvolvimento do time.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Scripts locais em Python com credenciais no repositório ou requisições manuais via curl. Descartado por expor segredos ou depender de operações manuais repetitivas.
- **Alternativa B (Escolhida):** Servidor MCP (*Model Context Protocol*) dedicado e compatível com a nova API `/rest/api/3/search/jql` do Jira Cloud, configurado globalmente em `~/.gemini/config/mcp_config.json`.

### Detalhamento da Solução:
- Servidor MCP em Node.js configurado em `~/.gemini/antigravity-cli/mcp/jira/`.
- Suporte ao endpoint moderno do Jira Cloud (`/rest/api/3/search/jql`) com paginação por token.
- Credenciais isoladas no diretório de configuração do usuário (`~/.gemini/config/mcp_config.json`), fora do controle de versão.
- Inclusão do `.gitignore` no repositório para blindar qualquer arquivo `.env`.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `DECISIONS/patrickgutem-create/`, `.gitignore`
- **Arquivos Criados / Modificados:** `DECISIONS/patrickgutem-create/0001-integracao-jira-mcp.md`, `.gitignore`
- **Infraestrutura / Configuração:** `~/.gemini/config/mcp_config.json` e `~/.gemini/antigravity-cli/mcp/jira/`

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Acesso direto a todas as 64 tarefas do projeto, zero risco de vazamento de segredos no Git.
- **Riscos / Trade-offs:** Requer Node.js no ambiente e validade ativa do token de acesso pessoal Atlassian.
- **Validação / Testes:** Testado com sucesso via JSON-RPC stdio e autenticação validada diretamente na API do Jira Cloud (`https://no-country.atlassian.net`).
