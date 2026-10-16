# [0002] - Arquitetura Fullstack Desacoplada (Next.js + Python FastAPI)

- **Data:** 2026-10-14
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
O projeto necessita de uma interface web interativa, moderna e responsiva para os profissionais de saúde e auditores (Human-in-the-Loop), combinada com um backend robusto em Python especializado em orquestração de IA generativa (LangGraph), processamento de arquivos e integração com serviços de nuvem (OCI e PostgreSQL).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
Garantir independência entre as camadas de apresentação e processamento:
- Permitir que a equipe de Frontend evolua a UI no ecossistema React/Next.js sem atrito com o runtime Python.
- Permitir que a equipe de Backend e IA evolua o grafo clínico, prompts e integrações no Python sem acoplamento a templates HTML monolíticos.
- Padronizar a comunicação exclusivamente via API REST com contratos tipados.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Aplicação monolítica apenas em Python com Streamlit para toda a experiência do usuário. Descartado por limitações de customização visual, performance de renderização em escala e experiência do usuário no fluxo de triagem.
- **Alternativa B (Escolhida):** Arquitetura desacoplada em monorepo com `frontend/` (Next.js / App Router / TypeScript) e `backend/` (FastAPI / LangGraph / Python).

### Detalhamento da Solução:
- **Frontend (`frontend/`):** Next.js com TypeScript, páginas modulares separadas por pastas (`src/app/<pagina>/`), rotas dinâmicas (`[id]/page.tsx`) para detalhes de laudos e auditoria com URLs compartilháveis, camada centralizada de requisições e rotas (`src/api/` com Axios/Fetch e interceptores) e espelhamento estrito dos contratos de dados.
- **Backend (`backend/`):** Arquitetura organizada em MVC + Services + Repositories + Agent Core (LangGraph isolado com SRP), Pydantic v2 para contratos DTO, SQLAlchemy para Models do PostgreSQL e Clean Architecture/Clean Code em todas as camadas.
- **Isolamento de Segurança:** O Frontend jamais acessa o PostgreSQL ou OCI diretamente.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `frontend/`, `backend/`, `AGENTS/AGENTS.md`
- **Arquivos Criados / Modificados:** `AGENTS/AGENTS.md`, `DECISIONS/patrickgutem-create/0002-arquitetura-monorepo-desacoplado.md`
- **Infraestrutura / Variáveis:** Separação entre variáveis de backend (`backend/.env`) e cliente (`frontend/.env.local`).

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Separação limpa de papéis no time, tipagem forte de ponta a ponta, interface profissional e backend desacoplado.
- **Riscos / Trade-offs:** Necessidade de manter dois runtimes locais (Node.js e Python) e garantir sincronia dos tipos entre Pydantic e TypeScript.
- **Validação / Testes:** Testes unitários com Pytest no backend e Jest/Vitest no frontend; testes de integração via contratos da OpenAPI.
