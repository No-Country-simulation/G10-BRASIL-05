# [0003] - Atribuição Automática de Tarefas no Jira via MCP

- **Data:** 2026-10-14
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Durante a execução de tarefas do projeto, quando um agente de IA ou desenvolvedor assume um card do backlog no Jira, é fundamental que a equipe saiba quem está trabalhando naquela issue em tempo real, evitando duplicidade de esforço e falta de visibilidade no quadro Kanban/Scrum.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
Garantir que, no momento em que uma tarefa for selecionada para desenvolvimento, ela seja automaticamente atribuída ao desenvolvedor responsável no Jira Cloud antes ou durante a transição para "Em andamento", assegurando transparência e rastreabilidade total no backlog do time.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Atribuição manual pelo desenvolvedor na interface web do Jira. Descartado por depender de ação manual sujeita a esquecimento e atrito de troca de contexto.
- **Alternativa B (Escolhida):** Automação no ciclo de vida da tarefa utilizando as ferramentas `jira_get_myself` (para obter o `accountId` do desenvolvedor autenticado) ou `jira_find_users` (para outros membros) e `jira_assign_issue` para efetivar a atribuição via MCP.

### Detalhamento da Solução:
1. Ao iniciar o trabalho em uma issue (ex: `SCRUM-XX`), o agente consulta o `accountId` do usuário via `jira_get_myself` (ou busca via `jira_find_users`).
2. O agente executa `jira_assign_issue` passando a chave da issue e o `accountId`.
3. Em seguida, transiciona a issue para "Em andamento" (`transitionId: "21"`).
4. O processo fica documentado no ciclo de vida de tarefas em `AGENTS/AGENTS.md`.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `AGENTS/`, `DECISIONS/patrickgutem-create/`
- **Arquivos Criados / Modificados:** `AGENTS/AGENTS.md`, `DECISIONS/patrickgutem-create/0003-atribuicao-automatica-tarefas-jira.md`
- **Infraestrutura / MCP:** Uso da ferramenta `jira_assign_issue` do servidor MCP Jira.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Zero atrito para o desenvolvedor, quadro do Jira sempre atualizado com o responsável correto, maior clareza para a gestão do Hackathon.
- **Riscos / Trade-offs:** Requer que o usuário esteja devidamente cadastrado e com permissão de atribuição no projeto `SCRUM`.
- **Validação / Testes:** Testado com sucesso através da consulta de identidade com `jira_get_myself` retornando os dados do usuário autenticado.
