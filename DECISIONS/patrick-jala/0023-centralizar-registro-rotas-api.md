# [0023] - Centralizar o Registro de Rotas da API

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
As rotas HTTP estão declaradas em vários arquivos de controller, enquanto `app/api/router.py` apenas agrega os routers. Isso dificulta obter uma visão única dos caminhos e métodos expostos.

## 2. Para quê? (Objetivo e Resultados Esperados)
Manter o registro de todos os caminhos, métodos, tags e metadados HTTP da API em `app/api/router.py`, preservando as funções handler nos controllers.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Mover também a lógica dos handlers ao arquivo agregador, misturando registro de rotas e implementação dos controllers.
- **Alternativa B (Escolhida):** Manter handlers em seus controllers e registrá-los explicitamente com `add_api_route` no router central.

### Detalhamento da Solução:
Remover os decoradores de rota dos controllers e declarar no router central os endpoints, seus métodos, paths, tags, modelos de resposta, status e dependências de router. Registrar também as cópias versionadas e legadas conforme `API_V1_PREFIX`.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/api/`, `backend/app/controllers/`
- **Arquivos Criados / Modificados:** `backend/app/api/router.py`, controllers existentes e este registro de decisão.
- **Banco de Dados / Infra:** Sem alterações.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Visão centralizada das rotas sem deslocar lógica HTTP ou de negócio dos handlers.
- **Riscos / Trade-offs:** A lista central precisa ser atualizada quando um handler ou contrato de rota mudar.
- **Validação / Testes:** Conferir estaticamente os registros e preservar os testes existentes; não executar testes sem solicitação explícita.
