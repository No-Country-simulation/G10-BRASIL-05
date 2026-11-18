# [0014] - Executar frontend e backend em containers separados

- **Data:** 2026-11-17
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

O Compose existente inicializa PostgreSQL, Redis, MongoDB e Evolution API, mas deixa o frontend Streamlit e o backend FastAPI fora da orquestração. Isso exige inicialização manual e torna confusa a URL usada entre os processos.

## 2. Para quê? (Objetivo e Resultados Esperados)

Subir a aplicação completa por um único Compose, mantendo frontend, backend e dependências em containers separados e comunicando serviços pela rede interna do Compose.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Executar frontend e backend no host (descartada):** exige iniciar cada processo manualmente e manter URLs distintas.
- **Um container por serviço coordenado por Compose (escolhida):** preserva isolamento e permite usar nomes de serviço para comunicação interna.

### Detalhamento da Solução:

Adicionar Dockerfiles para Streamlit e FastAPI e serviços `frontend` e `backend` ao `docker-compose.yml`. Os containers recebem os `.env` locais por `env_file`, mas esses arquivos ficam fora da imagem via `.dockerignore`. No Compose, o frontend chama `http://backend:8000`; no host, mantém `http://localhost:8000`.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** raiz do Compose, `backend/` e `frontend/`.
- **Arquivos Criados / Modificados:** `docker-compose.yml`, `backend/.dockerignore`, `frontend/Dockerfile`, `frontend/.dockerignore`.
- **Banco de Dados / Infra:** backend espera PostgreSQL, Redis e Mongo saudáveis; frontend espera healthcheck do backend. Nenhum container é aninhado.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** uma inicialização coordena toda a aplicação e mantém separação de processos.
- **Riscos / Trade-offs:** os arquivos `backend/.env` e `frontend/.env` precisam ser criados localmente a partir dos exemplos; o Compose deve estar instalado.
- **Validação / Testes:** validar o YAML do Compose e os comandos/configurações dos containers; executar builds quando o daemon e o Compose estiverem disponíveis.
