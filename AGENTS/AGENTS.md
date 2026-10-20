# Diretrizes de Uso de IA - Equipe G10-BRASIL-05

Este documento define as regras, restrições e padrões obrigatórios para qualquer agente de IA (Gemini, Claude, Cursor, Copilot, ChatGPT, etc.) ou desenvolvedor atuando no repositório **G10-BRASIL-05**.

---

## 1. Escopo e Papel da IA
- **SKILLS Obrigatórias:** Consultar e aplicar rigorosamente [Grill-Me Protocol](SKILLS/GRILL-ME.MD).
- **Modo de Operação:** Co-piloto e assistente técnico.
- **Autoridade Final:** Toda alteração de código deve ser validada e compreendida por um desenvolvedor humano da equipe antes de ser integrada à branch principal.
- **Registro de Decisões:** Toda decisão técnica/arquitetural tomada ao final da entrevista deve ser documentada antes de qualquer código ser escrito:
  - **Local:** `DECISIONS/<nome_do_usuario>/` (onde `<nome_do_usuario>` é obtido automaticamente via `git config user.name`).
  - **Nomenclatura:** Sequencial e descritiva (`0001-nome-da-decisao.md`).
  - **Estrutura:** Deve seguir estritamente o [DECISIONS/TEMPLATE.md](../DECISIONS/TEMPLATE.md), respondendo obrigatoriamente: **Por quê**, **Para quê**, **Como** e **Onde**.
  - **Regra de Ouro:** *Documente a decisão primeiro e depois faça o código, nunca o inverso.* 


---

## 2. Linhas Vermelhas e Restrições Críticas (O que a IA NUNCA deve fazer)
- **Segredos e Credenciais:** Jamais inserir, expor ou sugerir commit de chaves de API, senhas, tokens ou arquivos `.env`.
- **Invenção de Dependências:** Não adicionar bibliotecas ou pacotes externos sem validação prévia de necessidade e licença (evitar inchaço desnecessário).
- **Código sem Testes:** Qualquer função, endpoint ou lógica de negócio gerada por IA deve ser acompanhada dos respectivos testes automatizados.
- **Refatorações Destrutivas:** Não reescrever módulos inteiros ou alterar padrões de arquitetura estabelecidos sem solicitação explícita do desenvolvedor.
- **Alucinações de Contexto:** Não assumir regras de negócio inexistentes; em caso de dúvida, a IA deve parar e perguntar ao desenvolvedor.

---

## 3. Padrões de Código, Clean Code e Clean Architecture

Tanto no Backend quanto no Frontend, todo código produzido deve seguir rigorosamente as convenções de **Clean Code**, **Clean Architecture** e o **Princípio da Responsabilidade Única (SRP)**:

### 3.1 Clean Code
- **Nomenclatura Significativa:** Nomes de variáveis, funções, classes e arquivos devem revelar sua intenção com clareza, evitando abreviações crípticas.
- **Funções Pequenas e Focadas:** Funções e métodos devem realizar apenas uma ação e possuir tamanho reduzido.
- **Tratamento Explícito de Erros:** É proibido silenciar exceções (`except Exception: pass`); erros devem ser tratados e logados com clareza.
- **DRY (Don't Repeat Yourself):** Evitar duplicação de lógica, centralizando operações comuns em utilitários ou serviços.

### 3.2 Clean Architecture & Desacoplamento
- **Regra de Dependência:** O núcleo de negócio (entidades, serviços e nós do agente) não deve depender de detalhes externos (frameworks de apresentação, drivers de banco, bibliotecas de terceiros). Os detalhes dependem das abstrações.
- **Isolamento de Infraestrutura:** Consultas a banco de dados e armazenamento em nuvem (OCI) ficam estritamente contidos em repositórios/adaptadores de I/O.

### 3.3 Princípio da Responsabilidade Única (SRP)
- **No Backend:**
  - `Controller`: Apenas valida a entrada HTTP e devolve a resposta formatada.
  - `Service`: Centraliza a orquestração e as regras de negócio.
  - `Repository`: Responsável unicamente pela persistência e I/O de dados (PostgreSQL e OCI).
  - `Agent Node`: Cada nó do LangGraph executa apenas uma etapa pura de análise clínica.
- **No Frontend (Streamlit):**
  - `Page` (`pages/`): Responsável exclusivamente pela montagem visual da aba/página e fluxo de interação do usuário.
  - `Component` (`components/`): Funções visuais reutilizáveis do Streamlit (cartões de entidades, alertas de urgência, visualizador de documentos).
  - `API Client` (`services/api_client.py`): Responsável exclusivamente pela comunicação HTTP (`httpx`/`requests`) com a API FastAPI.


---

## 4. Rastreabilidade, Branches e Fiscalização
- **Commits:** Mensagens de commit claras, curtas e diretas (sem textos longos ou genéricos gerados automaticamente).
- **Política Estrita de Branches e Push:**
  - **Sempre em Branch Nova:** Cada entrega/push deve ser feita obrigatoriamente em uma **branch nova** criada a partir da `develop` atualizada (padrão: `feature/SCRUM-XX-descricao-curta` ou `fix/SCRUM-XX-descricao`). É proibido fazer push direto na `main` ou na `develop`.
  - **Exclusão Pós-Merge:** Assim que o Pull Request for revisado, aprovado e o merge for concluído na `develop`, **a branch deve ser excluída imediatamente** (tanto no GitHub via botão *Delete branch* / `git push origin --delete <branch>` quanto localmente via `git branch -d <branch>`).
- **Revisão Humana:** O autor do Pull Request é 100% responsável pelo código gerado por IA que submeter.

## 5. Integração com Jira & Gestão de Tarefas (MCP)

O agente de IA deve operar orientado a tarefas, utilizando obrigatoriamente a integração com o Jira via **MCP (Model Context Protocol)** para manter rastreabilidade, contexto e alinhamento com o backlog do time.

> 📘 **Configuração para qualquer cliente de IA** (Antigravity, Gemini, Cursor, Claude Desktop/Code, VS Code Copilot, Codex): ver [JIRA_MCP_SETUP.md](./JIRA_MCP_SETUP.md).

### 5.1 Regra de Ouro do Fluxo de Trabalho
- **Trabalho Orientado a Cards:** Nenhuma linha de código ou refatoração deve ser iniciada sem estar vinculada a um card do Jira.
- **Ciclo de Vida da Tarefa:**
  1. **Puxar o Card:** Ao iniciar qualquer atividade, o agente deve identificar o card correspondente no projeto `SCRUM`.
  2. **Atribuir o Card ao Desenvolvedor:** Chamar a ferramenta `jira_assign_issue` com o `accountId` do desenvolvedor (obtido via `jira_get_myself` para o usuário atual ou `jira_find_users`).
  3. **Transicionar para "Em andamento":** Mover o status da issue no Jira (ID `21`) antes de iniciar o desenvolvimento.
  4. **Seguir os Critérios de Aceitação (CA):** Ler a descrição completa e garantir que todos os CAs descritos no card sejam rigorosamente atendidos.
  5. **Concluir a Tarefa:** Após a implementação dos testes e validação com o desenvolvedor, transicionar para o status seguinte (*Em análise* ou *Concluído*).

### 5.2 Credenciais e Variáveis de Ambiente
O desenvolvedor deve configurar previamente as seguintes variáveis de ambiente no seu ambiente local (fora do versionamento Git):
- `JIRA_BASE_URL`: URL base da instância Jira Cloud (ex: `https://no-country.atlassian.net`).
- `JIRA_EMAIL`: E-mail da conta Atlassian do desenvolvedor.
- `JIRA_API_TOKEN`: Token de API pessoal gerado em [Atlassian Security Tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

> ⚠️ **Atenção:** Jamais exponha ou versione essas variáveis no repositório. Use o `.env` local (ignorado pelo `.gitignore`) ou armazene diretamente nas configurações globais do cliente MCP.

### 5.3 Inicialização do MCP pelo Agente
Assim que o usuário informar que as credenciais foram definidas no ambiente, o agente deve seguir o seguinte protocolo de inicialização:

1. **Garantir a Configuração do Servidor MCP:**
   Verificar ou registrar o servidor no arquivo de configuração do cliente MCP (ex: `~/.gemini/config/mcp_config.json` ou no arquivo de configuração MCP do seu ambiente):
   ```json
   {
     "mcpServers": {
       "jira": {
         "command": "npx",
         "args": ["-y", "ff-mcp-jira"],
         "env": {
           "JIRA_BASE_URL": "https://no-country.atlassian.net",
           "JIRA_EMAIL": "<seu_email_atlassian>",
           "JIRA_API_TOKEN": "<seu_api_token_atlassian>"
         }
       }
     }
   }
   ```
   *(Nota: Caso opte por clonar ou executar o servidor MCP localmente via Node, utilize `"command": "node"` com `"args": ["<caminho_para_o_servidor>/server.js"]`).*
2. **Validar a Conectividade:**
   Executar uma chamada de teste (ex: `jira_search` com JQL `project = SCRUM AND maxResults = 1`) para confirmar que a autenticação está ativa e sem erros de permissão ou API.
3. **Mapeamento de Status do Projeto:**
   - `11` → **A fazer** (Backlog / Pendente)
   - `21` → **Em andamento** (Desenvolvimento ativo)
   - `31` → **Em análise** (Code review / Testes)
   - `41` → **Concluído** (Entrega finalizada)
4. **Listar Próximas Tarefas:**
   Apresentar ao desenvolvedor os cards prioritários do backlog para definir o próximo item a ser trabalhado.

---

## 6. Verificação de Ambiente: Banco de Dados (PostgreSQL)

Antes de iniciar tarefas que envolvam persistência de dados, migrações (Alembic/Prisma) ou execução de testes de integração, o agente deve obrigatoriamente verificar a disponibilidade de uma instância PostgreSQL.

### 6.1 Protocolo de Verificação pelo Agente
O agente deve executar os seguintes passos para auditar o ambiente:
1. **Verificar se o cliente ou serviço existe localmente:**
   ```bash
   which psql || pg_isready 2>/dev/null
   ```
2. **Verificar se há contêiner PostgreSQL em execução (Docker):**
   ```bash
   docker ps --filter "ancestor=postgres" --format "{{.ID}}: {{.Names}} ({{.Status}})"
   ```
3. **Verificar a conectividade na porta padrão (5432):**
   ```bash
   nc -zv localhost 5432 2>&1 || true
   ```

### 6.2 O que fazer se o PostgreSQL NÃO estiver disponível?
Se o agente constatar que não há instância acessível, ele **NÃO** deve falhar silenciosamente nem prosseguir com comandos que dependam do banco. Em vez disso, deve informar o desenvolvedor e sugerir os seguintes caminhos viáveis:

#### Opção A: Docker (Recomendado — Rápido e Isolado)
Sugerir subir um contêiner oficial do PostgreSQL em segundo plano:
```bash
docker run --name postgres-g10 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=g10_brasil_db \
  -p 5432:5432 \
  -d postgres:16-alpine
```
*(Ou disponibilizar um `docker-compose.yml` no projeto para orquestração simples).*

#### Opção B: Instalação Nativa no Sistema Operacional
Se o desenvolvedor preferir rodar nativamente na máquina:
- **Ubuntu/Debian (Linux):**
  ```bash
  sudo apt update && sudo apt install -y postgresql postgresql-contrib
  sudo systemctl start postgresql
  ```
- **macOS:**
  ```bash
  brew install postgresql@16 && brew services start postgresql@16
  ```
- **Windows:**
  - Instalar via [EnterpriseDB Installer](https://www.postgresql.org/download/windows/) ou gerenciador de pacotes (`winget install PostgreSQL.PostgreSQL` / `choco install postgresql`).

#### Opção C: Banco Gerenciado Gratuito na Nuvem (Free Tier)
Se o desenvolvedor não puder ou não quiser rodar serviços locais:
- **[Neon.tech](https://neon.tech):** PostgreSQL Serverless gratuito, provisionado em segundos, ideal para desenvolvimento e hackathons.
- **[Supabase](https://supabase.com):** Instância gerenciada com free tier generoso.
- **Procedimento:** Obter a connection string fornecida pelo provedor e atualizar a variável `DATABASE_URL` no `.env`.

---

## 7. Estrutura de Pastas e Padrões de Arquitetura (100% Python: Streamlit + FastAPI)

O projeto adota uma arquitetura desacoplada em monorepo **100% Python** (conforme [ADR 0004](../DECISIONS/patrickgutem-create/0004-adocao-streamlit-e-postgresql.md)), com separação estrita entre a interface visual (**Streamlit**) e o servidor de processamento, banco de dados e inteligência artificial (**FastAPI + LangGraph + PostgreSQL + OCI Object Storage**).

### 7.1 Layout Oficial do Repositório

```text
G10-BRASIL-05/
├── backend/                       # Servidor de API e Inteligência Artificial (FastAPI + LangGraph)
│   ├── app/
│   │   ├── controllers/           # Controladores HTTP / Routers FastAPI (Entrada e saída de requisições)
│   │   ├── services/              # Camada de Serviços (Regras de negócio e orquestração do fluxo)
│   │   ├── models/                # Modelos ORM de Banco de Dados (PostgreSQL / SQLAlchemy)
│   │   ├── schemas/               # Contratos DTO Pydantic v2 (Validação de entrada e saída)
│   │   ├── repositories/          # Camada de Acesso a Dados e Storage (PostgreSQL e OCI Object Storage)
│   │   ├── agent/                 # Núcleo de IA e Triagem Clínica (LangGraph)
│   │   │   ├── graph.py           # Definição e orquestração do StateGraph
│   │   │   ├── nodes/             # Nós isolados com SRP (ingestão, classificador, extrator, validador, urgência)
│   │   │   ├── prompts/           # Engenharia e versionamento de templates de prompts
│   │   │   ├── state.py           # Estado tipado do agente (GraphState)
│   │   │   └── config.py          # Configurações do agente (modelos LLM, temperatura, fallbacks)
│   │   ├── config/                # Configurações centrais da aplicação (Settings, DB pool, Envs)
│   │   └── main.py                # Entrypoint da aplicação FastAPI
│   ├── tests/                     # Testes automatizados do backend (Pytest)
│   ├── requirements.txt           # Dependências Python do backend
│   ├── .env.example               # Template de variáveis do backend (DB, OCI, LLMs)
│   └── Dockerfile                 # Contêiner do serviço backend
│
├── frontend/                      # Interface Visual de Triagem e Auditoria (Streamlit)
│   ├── app.py                     # Entrypoint principal do Streamlit (Home / Navegação)
│   ├── pages/                     # Páginas multipage do Streamlit
│   │   ├── 1_Triagem_Clinica.py   # Upload de PDF/imagem/texto e diagnóstico em tempo real
│   │   ├── 2_Auditoria_Humana.py  # Fila Human-in-the-Loop para aprovar/corrigir/rejeitar
│   │   └── 3_Historico.py         # Consulta de documentos processados e métricas
│   ├── components/                # Componentes visuais reutilizáveis (cards, badges de urgência, tabelas)
│   ├── services/                  # Cliente HTTP centralizado
│   │   └── api_client.py          # Funções de requisição HTTP (httpx/requests) para a API FastAPI
│   ├── utils/                     # Formatadores (CRM, CID, datas) e helpers de estado (st.session_state)
│   ├── requirements.txt           # Dependências do frontend (streamlit, httpx, pydantic)
│   └── Dockerfile                 # Contêiner do serviço frontend
│
├── data/                          # Dados e Artefatos Compartilhados
│   └── samples/                   # Documentos clínicos sintéticos (Rotina, Urgência e Ambíguo)
│
├── DECISIONS/                     # Registro de Decisões Arquiteturais (ADRs por desenvolvedor)
├── AGENTS/                        # Governança, diretrizes e regras para agentes de IA
├── PLANO_DE_ACAO.md               # Divisão das 8 pessoas, fluxos Mermaid e cards do Jira
├── .gitignore                     # Proteção unificada contra commit de segredos e dependências
└── README.md                      # Documentação central do projeto e instruções de execução
```

### 7.2 Regras de Fronteira e Comunicação

1. **Isolamento Estrito de Acesso a Dados:**
   - O **Frontend (Streamlit)** **NUNCA** acessa o banco de dados PostgreSQL nem o OCI Object Storage diretamente.
   - Qualquer persistência, consulta, upload de arquivo ou inferência via LangGraph deve passar obrigatoriamente pelos endpoints da API do Backend (`frontend/services/api_client.py` → `backend`).

2. **Fonte da Verdade dos Contratos (API First):**
   - Os schemas em `backend/app/schemas/` (Pydantic v2) são a fonte primária da verdade para validação de entrada e saída.

3. **Responsabilidade dos Nós do Grafo (`backend/app/agent/nodes/`):**
   - Cada nó deve ter responsabilidade única (função pura que consome e atualiza o `GraphState`).
   - Não acoplar queries SQL ou chamadas do OCI diretamente nos nós; a persistência fica na camada `backend/app/repositories/` orquestrada por `backend/app/services/`.

4. **Gerenciamento de Ambientes e `.env`:**
   - As variáveis de ambiente (PostgreSQL, OCI, LLM Keys, `API_BASE_URL`) ficam definidas no `.env` local (baseado no `.env.example`) e nunca são versionadas.

5. **Human-in-the-Loop Integrado:**
   - O painel de auditoria médica (`pages/2_Auditoria_Humana.py`) consome a fila de auditoria exposta pela API do backend e envia a decisão médica via `POST /auditoria/{id}/decisao`.

### 7.3 Regras Mandatórias de Estruturação do Frontend (Streamlit)

1. **Páginas Organizadas em `frontend/pages/`:**
   - As páginas do Streamlit atuam apenas na renderização visual e captura de inputs do usuário.
2. **Centralização Total de Requisições em `frontend/services/api_client.py`:**
   - É proibido espalhar chamadas `requests.get/post` com URLs fixas dentro das páginas; toda chamada à FastAPI passa pelo `api_client.py`.
3. **Componentização em `frontend/components/`:**
   - Elementos visuais repetidos (cartão de dados extraídos, alerta vermelho de urgência médica, badge de score de confiança) ficam isolados em funções dentro de `components/`.

### 7.4 Regras Mandatórias de Estruturação do Backend (MVC + Services + Agent Core)

Com ênfase em **simplicidade, clareza e manutenção organizada** (sem complexidade acidental):

1. **Controllers Finos (`app/controllers/`):**
   - Responsáveis estritamente pela camada de transporte HTTP (FastAPI Routers).
   - Devem apenas validar o payload recebido via `schemas/` Pydantic, delegar o trabalho para a camada de `services/` e devolver o status HTTP apropriado.
   - É terminantemente proibido colocar lógicas de negócio complexas, queries SQL diretas ou chamadas manuais de LLM dentro dos controllers.

2. **Camada de Serviços (`app/services/`):**
   - Centraliza todas as regras de negócio da aplicação (ex: `triagem_service.py`, `auditoria_service.py`, `documento_service.py`).
   - Orquestra os passos de processamento, invoca o grafo do agente LangGraph e aciona os repositórios (PostgreSQL e OCI) para persistir dados.

3. **Núcleo do Agente de IA (`app/agent/`):**
   - Centraliza exclusivamente a inteligência artificial e orquestração do LangGraph:
     - `graph.py`: Monta a máquina de estados e o fluxo de decisão clínica (`StateGraph`).
     - `nodes/`: Funções puras e isoladas, cada uma com uma responsabilidade única (ingerir, classificar, extrair entidades, validar CRM/CID, avaliar urgência).
     - `prompts/`: Engenharia e versionamento de templates de prompts.
     - `state.py`: Modelo tipado do `GraphState` via Pydantic v2.
     - `config.py`: Parâmetros do agente (seleção de modelo, temperatura, limites de retentativa e chaves).

4. **Separação Estrita: Models vs Schemas:**
   - `app/models/`: Entidades persistidas no banco de dados (tabelas PostgreSQL / SQLAlchemy).
   - `app/schemas/`: Contratos DTO de entrada e saída da API (Pydantic v2).

5. **Camada de Repositórios (`app/repositories/`):**
   - Isola o I/O de dados: persistência relacional em PostgreSQL e uploads/downloads/movimentação de arquivos no OCI Object Storage.





