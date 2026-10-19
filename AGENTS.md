# AGENTS.md — Ponto de Entrada para Agentes de IA

> Este arquivo existe na raiz para ser descoberto automaticamente por qualquer agente de IA (Codex, Cursor, Copilot, Claude Code, Gemini, Antigravity, etc.).
> **As regras completas e obrigatórias estão em [AGENTS/AGENTS.md](AGENTS/AGENTS.md).**

## Antes de qualquer ação, leia nesta ordem

1. [AGENTS/AGENTS.md](AGENTS/AGENTS.md): regras, restrições, arquitetura e fluxo de trabalho (**obrigatório**).
2. [AGENTS/SKILLS/GRILL-ME.MD](AGENTS/SKILLS/GRILL-ME.MD): protocolo de entrevista antes de decisões (**obrigatório**).
3. [AGENTS/JIRA_MCP_SETUP.md](AGENTS/JIRA_MCP_SETUP.md): conexão com o Jira via MCP e fluxo de cards.
4. [DECISIONS/](DECISIONS/): decisões já tomadas (ADRs). Novas decisões seguem o [DECISIONS/TEMPLATE.md](DECISIONS/TEMPLATE.md).
5. [PLANO_DE_ACAO.md](PLANO_DE_ACAO.md): divisão da equipe, fases e checklist.
6. `mediflow (1).pdf`: enunciado oficial do desafio (fonte da verdade dos requisitos).

## Regras essenciais (resumo; o detalhe está em AGENTS/AGENTS.md)

- **Nunca** exponha ou commite segredos (`.env`, tokens, chaves).
- **Documente a decisão antes de codar** em `DECISIONS/<git config user.name>/`.
- **Todo código vem com testes.**
- **Todo trabalho é vinculado a um card do Jira** (projeto `SCRUM`).
- Em caso de dúvida sobre regra de negócio, **pare e pergunte** ao desenvolvedor.
