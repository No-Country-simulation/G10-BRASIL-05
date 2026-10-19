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
- **No Frontend:**
  - `Page`: Responsável exclusivamente pela montagem e roteamento da tela.
  - `Component`: Responsável unicamente pela renderização visual e eventos de interface.
  - `Hook`: Responsável exclusivamente pelo gerenciamento de estado e regras de tela.
  - `API`: Responsável exclusivamente pela comunicação HTTP e parametrização de rede.


---

## 4. Rastreabilidade e Fiscalização
- **Commits:** Mensagens de commit claras e sem textos genéricos gerados automaticamente.
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

## 7. Estrutura de Pastas e Padrões de Arquitetura (Fullstack: Next.js + Python)

O projeto adota uma arquitetura fullstack desacoplada organizada em monorepo, com separação estrita entre o cliente web (**Next.js / TypeScript**) e o servidor de processamento e inteligência artificial (**Python / FastAPI + LangGraph**).

### 7.1 Layout Oficial do Repositório

```text
G10-BRASIL-05/
├── backend/                       # Servidor de API e Inteligência Artificial (Python)
│   ├── app/
│   │   ├── controllers/           # Controladores HTTP / Routers FastAPI (Entrada e saída de requisições)
│   │   ├── services/              # Camada de Serviços (Regras de negócio e orquestração do fluxo)
│   │   ├── models/                # Modelos ORM de Banco de Dados (PostgreSQL / SQLAlchemy)
│   │   ├── schemas/               # Contratos DTO Pydantic v2 (Validação de entrada e saída)
│   │   ├── repositories/          # Camada de Acesso a Dados e Storage (PostgreSQL e OCI)
│   │   ├── agent/                 # Núcleo de IA e Triagem Clínica (LangGraph)
│   │   │   ├── graph.py           # Definição e orquestração do StateGraph
│   │   │   ├── nodes/             # Nós isolados com SRP (classificador, extrator, validador)
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
│
├── frontend/                      # Interface do Usuário e Auditoria (Next.js / TypeScript)
│   ├── src/
│   │   ├── app/                   # Páginas separadas estritamente por pastas (App Router)
│   │   │   ├── layout.tsx         # Layout raiz global (Providers, fontes, navegação base)
│   │   │   ├── page.tsx           # Landing / Dashboard principal
│   │   │   ├── triagem/           # Pasta dedicada da página de triagem clínica
│   │   │   │   ├── page.tsx       # Tela de upload e acompanhamento do agente em tempo real
│   │   │   │   └── [id]/page.tsx  # Tela de detalhes do documento analisado
│   │   │   └── auditoria/         # Pasta dedicada da página de auditoria médica (Human-in-the-Loop)
│   │   │       ├── page.tsx       # Fila de itens aguardando revisão médica
│   │   │       └── [id]/page.tsx  # Tela de análise e decisão médica
│   │   ├── api/                   # Camada Central de Comunicação HTTP, Rotas e Axios/Fetch
│   │   │   ├── api.ts             # Instância base do Axios/Fetch (baseURL, timeout, interceptors e erros)
│   │   │   ├── endpoints.ts       # Mapeamento centralizado de todas as rotas e URLs da API
│   │   │   ├── triagem.api.ts     # Funções de requisição para triagem e execução do LangGraph
│   │   │   ├── auditoria.api.ts   # Funções de requisição para fila e aprovação médica
│   │   │   └── documentos.api.ts  # Funções de requisição para upload e consulta de laudos/arquivos
│   │   ├── components/            # Componentes React reutilizáveis e modulares
│   │   │   ├── ui/                # Componentes atômicos genéricos (Button, Input, Badge, Modal, Spinner)
│   │   │   ├── layout/            # Componentes estruturais (Navbar, Sidebar, PageHeader)
│   │   │   ├── forms/             # Formulários reutilizáveis
│   │   │   ├── triagem/           # Componentes específicos de triagem (DocViewer, EntityCards)
│   │   │   └── auditoria/         # Componentes específicos de auditoria (AuditTable, DecisionDialog)
│   │   ├── hooks/                 # Custom Hooks de regras de negócio e estado do front
│   │   │   ├── useTriagem.ts      # Orquestra envio, polling e estado do agente consumindo a pasta api/
│   │   │   └── useAuditoria.ts    # Gerencia a fila de revisão humana consumindo a pasta api/
│   │   ├── types/                 # Interfaces TypeScript alinhadas aos schemas Pydantic
│   │   │   ├── triagem.types.ts   # Contratos de triagem, classificação e entidades clínicas
│   │   │   ├── auditoria.types.ts # Contratos da fila e decisões de auditoria
│   │   │   └── api.types.ts       # Envelope padrão de resposta e erros da API
│   │   ├── contexts/              # Contextos globais (Notificações, tema, estado de sessão)
│   │   └── utils/                 # Formatadores (CRM, CID, datas), constantes e validadores
│   ├── public/                    # Assets estáticos (logos, ícones)
│   ├── package.json               # Dependências do ecossistema Node.js / React
│   ├── .env.example               # Template de variáveis do frontend (NEXT_PUBLIC_API_URL)
│   └── Dockerfile                 # Contêiner do serviço frontend
│
├── data/                          # Dados e Artefatos Compartilhados
│   └── samples/                   # Documentos clínicos sintéticos (PDFs, laudos, receitas de teste)
│
├── DECISIONS/                     # Registro de Decisões Arquiteturais (ADRs por desenvolvedor)
├── AGENTS/                        # Governança, diretrizes e regras para agentes de IA
├── .gitignore                     # Proteção unificada contra commit de segredos e dependências
└── README.md                      # Documentação central do projeto e papéis da equipe
```

### 7.2 Regras de Fronteira e Comunicação

1. **Isolamento Estrito de Acesso a Dados:**
   - O **Frontend (Next.js)** **NUNCA** acessa o banco de dados PostgreSQL nem o OCI Object Storage diretamente.
   - Qualquer persistência, consulta, upload de arquivo ou inferência via LangGraph deve passar obrigatoriamente pelos endpoints da API do Backend.

2. **Fonte da Verdade dos Contratos (API First):**
   - Os schemas em `backend/app/schemas/` (Pydantic v2) são a fonte primária da verdade.
   - As interfaces e tipos em `frontend/src/types/` devem espelhar fielmente esses contratos.

3. **Responsabilidade dos Nós do Grafo (`backend/app/nodes/`):**
   - Cada nó deve ter responsabilidade única (função pura que consome e atualiza o `GraphState`).
   - Não acoplar chamadas de rede ou queries SQL diretamente nos nós; delegar para classes adaptadoras em `app/storage/`.

4. **Gerenciamento de Ambientes e `.env`:**
   - O `backend/` possui seu próprio arquivo `.env` com chaves sensíveis (PostgreSQL, OCI, LLM Keys).
   - O `frontend/` possui seu próprio `.env.local` apenas com variáveis públicas de cliente (ex: `NEXT_PUBLIC_API_URL=http://localhost:8000`).

5. **Human-in-the-Loop Integrado:**
   - O painel de auditoria médica e revisão de inconformidades clínicas deve ser desenvolvido como telas do próprio **Next.js**, consumindo a fila de auditoria exposta pela API do backend.

### 7.3 Regras Mandatórias de Estruturação do Frontend (Next.js)

Para garantir escalabilidade, manutenibilidade e separação estrita de responsabilidades no cliente:

1. **Páginas Organizadas por Pastas Dedicadas (`src/app/<pagina>/`):**
   - Toda página deve possuir sua pasta exclusiva (ex: `src/app/triagem/`, `src/app/auditoria/`).
   - As páginas atuam puramente como montadoras de layout e roteamento.
   - Lógicas de negócio e formulários devem residir em `hooks/`, e elementos visuais em `components/`.

2. **Centralização Total de Requisições na Pasta `src/api/`:**
   - É **estritamente proibido** instanciar `axios`, chamar `fetch` ou definir URLs diretamente em componentes ou páginas.
   - Toda e qualquer configuração de cliente HTTP (instância base, interceptors de autenticação, timeout e tratamento global de erros) reside em `src/api/client.ts`.
   - Todas as URLs e rotas da API devem ser mapeadas em `src/api/endpoints.ts`.
   - Funções de requisição ficam organizadas por contexto em arquivos dedicados (ex: `src/api/triagem.api.ts`, `src/api/auditoria.api.ts`).

3. **Regras de Negócio e Estado em Hooks (`src/hooks/`):**
   - Os Custom Hooks são a ponte entre as páginas e a pasta `src/api/`.
   - Polling de processamento do agente LangGraph, controle de estados de loading e mutações devem ser implementados em hooks reutilizáveis (ex: `useTriagem`, `useAuditoria`).

4. **Tipagem Estrita (Zero `any`):**
   - Todos os payloads de requisição e resposta na pasta `src/api/` devem possuir tipagem estrita definida em `src/types/`. O uso de `any` ou tipos implícitos é proibido.

5. **Componentização Modular:**
   - Componentes genéricos de UI (botões, modais, badges) ficam em `components/ui/`.
   - Componentes vinculados ao domínio da saúde/triagem (visualizador de receitas, cartões de entidades clínicas) ficam isolados em pastas temáticas dentro de `components/`.

6. **Padrão de Rotas Dinâmicas (`[id]/page.tsx`):**
   - O uso de colchetes `[id]` no Next.js representa uma rota dinâmica parametrizada via URL:
     - `src/app/triagem/[id]/page.tsx`: Tela de Raio-X e histórico de um documento específico já processado. Exibe o documento original (PDF/imagem do OCI), entidades clínicas extraídas (CRM, CID, medicamentos), score de confiança da IA e alertas de urgência médica.
     - `src/app/auditoria/[id]/page.tsx`: Tela de decisão individual do médico/auditor (Human-in-the-Loop) para aprovar, corrigir ou rejeitar uma triagem com inconformidade.
   - **Benefício:** Garante que cada documento e item de auditoria possua uma URL direta, única e compartilhável entre a equipe médica (ex: `/triagem/uuid-do-documento`).

### 7.4 Regras Mandatórias de Estruturação do Backend (MVC + Services + Agent Core)

Com ênfase em **simplicidade, clareza e manutenção organizada** (sem complexidade acidental):

1. **Controllers Finos (`app/controllers/`):**
   - Responsáveis estritamente pela camada de transporte HTTP (FastAPI Routers).
   - Devem apenas validar o payload recebido via `schemas/` Pydantic, delegar o trabalho para a camada de `services/` e devolver o status HTTP apropriado.
   - É terminantemente proibido colocar lógicas de negócio complexas, queries SQL diretas ou chamadas manuais de LLM dentro dos controllers.

2. **Camada de Serviços (`app/services/`):**
   - Centraliza todas as regras de negócio da aplicação (ex: `triagem_service.py`, `auditoria_service.py`, `documento_service.py`).
   - Orquestra os passos de processamento, invoca os nós do agente LangGraph e aciona os repositórios para persistir dados.

3. **Núcleo do Agente de IA (`app/agent/`):**
   - Centraliza exclusivamente a inteligência artificial e orquestração do LangGraph:
     - `graph.py`: Monta a máquina de estados e o fluxo de decisão clínica (`StateGraph`).
     - `nodes/`: Funções puras e isoladas, cada uma com uma responsabilidade única (classificar, extrair entidades, validar CRM/CID, avaliar urgência).
     - `prompts/`: Engenharia e versionamento de templates de prompts.
     - `state.py`: Modelo tipado do `GraphState` via Pydantic v2.
     - `config.py`: Parâmetros do agente (seleção de modelo, temperatura, limites de retentativa e chaves).

4. **Separação Estrita: Models vs Schemas:**
   - `app/models/`: Entidades persistidas no banco de dados (tabelas PostgreSQL / SQLAlchemy).
   - `app/schemas/`: Contratos DTO de entrada e saída da API (Pydantic v2).

5. **Camada de Repositórios (`app/repositories/`):**
   - Isola o I/O de dados: persistência em PostgreSQL e uploads/downloads no OCI Object Storage.





