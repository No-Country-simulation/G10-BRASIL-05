# 🔌 Guia de Configuração do Jira MCP (para qualquer agente de IA)

> **Para agentes de IA:** este é o guia oficial para conectar ao Jira da equipe. Leia junto com a [seção 5 do AGENTS.md](./AGENTS.md#5-integração-com-jira--gestão-de-tarefas-mcp).
> **Para humanos:** siga o passo do **seu** cliente de IA. Leva cerca de 5 minutos.

---

## 1. Dados do Jira da Equipe

| Item | Valor |
| :--- | :--- |
| Instância Jira Cloud | `https://no-country.atlassian.net` |
| Projeto | `SCRUM` |
| Servidor MCP | pacote npm [`ff-mcp-jira`](https://www.npmjs.com/package/ff-mcp-jira) (rodado via `npx`, não precisa instalar) |
| Pré-requisito | Node.js 18+ (`node -v`) |

### Variáveis necessárias

| Variável | Valor | Onde conseguir |
| :--- | :--- | :--- |
| `JIRA_BASE_URL` | `https://no-country.atlassian.net` | Fixo (igual para todos) |
| `JIRA_EMAIL` | Seu e-mail da conta Atlassian | Sua conta |
| `JIRA_API_TOKEN` | Seu token pessoal | [Atlassian → Security → API tokens](https://id.atlassian.com/manage-profile/security/api-tokens) |

> ⚠️ **NUNCA** commite o token. Ele fica **só** no `.env` local (ignorado pelo Git) ou na configuração **global** do seu cliente de IA, fora do repositório.

---

## 2. Configuração por Cliente de IA

Em todos os exemplos, troque `<seu_email>` e `<seu_token>` pelos seus dados.

### 2.1 Antigravity / Gemini
Arquivo: `~/.gemini/config/mcp_config.json` (Gemini CLI: `~/.gemini/settings.json`)
```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "ff-mcp-jira"],
      "env": {
        "JIRA_BASE_URL": "https://no-country.atlassian.net",
        "JIRA_EMAIL": "<seu_email>",
        "JIRA_API_TOKEN": "<seu_token>"
      }
    }
  }
}
```

### 2.2 Cursor
Arquivo: `~/.cursor/mcp.json` (global, fora do repo). Use o **mesmo JSON** do item 2.1.

### 2.3 Claude Desktop
Arquivo: `claude_desktop_config.json` (Configurações → Developer → Edit Config). Use o **mesmo JSON** do item 2.1 e reinicie o app.

### 2.4 Claude Code (terminal)
```bash
claude mcp add jira --scope user \
  -e JIRA_BASE_URL=https://no-country.atlassian.net \
  -e JIRA_EMAIL=<seu_email> \
  -e JIRA_API_TOKEN=<seu_token> \
  -- npx -y ff-mcp-jira
```

### 2.5 VS Code (GitHub Copilot — modo Agent)
Arquivo: **configuração de usuário** (`Ctrl+Shift+P` → `MCP: Open User Configuration`). Não use `.vscode/mcp.json` com o token dentro, porque a pasta `.vscode/` fica no repositório.
```json
{
  "servers": {
    "jira": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "ff-mcp-jira"],
      "env": {
        "JIRA_BASE_URL": "https://no-country.atlassian.net",
        "JIRA_EMAIL": "<seu_email>",
        "JIRA_API_TOKEN": "<seu_token>"
      }
    }
  }
}
```

### 2.6 OpenAI Codex CLI
Arquivo: `~/.codex/config.toml`
```toml
[mcp_servers.jira]
command = "npx"
args = ["-y", "ff-mcp-jira"]
env = { JIRA_BASE_URL = "https://no-country.atlassian.net", JIRA_EMAIL = "<seu_email>", JIRA_API_TOKEN = "<seu_token>" }
```

### 2.7 Outro cliente
Qualquer cliente compatível com MCP via **stdio** funciona com: comando `npx`, argumentos `-y ff-mcp-jira` e as 3 variáveis acima.

---

## 3. Validar a Conexão

Depois de configurar, peça ao seu agente:
1. `jira_get_myself`: deve retornar seu nome e `accountId`.
2. `jira_search` com JQL `project = SCRUM ORDER BY created DESC` e `maxResults: 1`: deve retornar 1 card.

| Erro | Causa provável |
| :--- | :--- |
| `401 Unauthorized` | E-mail ou token errado, ou token expirado |
| `403 Forbidden` | Sua conta não tem acesso ao projeto `SCRUM`; peça acesso ao coordenador |
| Ferramentas `jira_*` não aparecem | Cliente não foi reiniciado ou Node.js não está instalado |

---

## 4. Instruções para Agentes de IA (fluxo obrigatório)

Ao iniciar **qualquer** tarefa neste repositório:

1. **Encontrar o card:** `jira_search` no projeto `SCRUM`. Se não houver card, **pare e pergunte** ao desenvolvedor.
2. **Atribuir:** `jira_get_myself` → `jira_assign_issue` com o `accountId`.
3. **Iniciar:** `jira_transition_issue` → **Em andamento**.
4. **Executar:** seguir os Critérios de Aceitação descritos no card.
5. **Finalizar:** após testes e validação humana → **Em análise** ou **Concluído**.

**IDs de transição do projeto SCRUM:**

| ID | Status |
| :-: | :--- |
| `11` | A fazer |
| `21` | Em andamento |
| `31` | Em análise |
| `41` | Concluído |

> Se um ID falhar, use `jira_list_transitions` no card para obter os IDs válidos.

**Regras:**
- Não execute ações no Jira (atribuir, transicionar, comentar, criar ou apagar) sem o desenvolvedor pedir ou sem estar dentro do fluxo acima.
- Nunca use `jira_delete_issue` sem confirmação explícita.
- Branch no padrão `feature/SCRUM-XX-descricao`.
