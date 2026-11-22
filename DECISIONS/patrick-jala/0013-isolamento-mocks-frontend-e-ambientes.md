# [0013] - Isolamento de mocks e seleção explícita de ambiente no frontend

- **Data:** 2026-11-17
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

O frontend contém respostas simuladas em módulos Python e seleciona entre API e mock por uma variável de demonstração. A seleção precisa permanecer explícita para que falhas de rede nunca sejam confundidas com dados simulados. Também é necessário selecionar a URL local ou de produção pelo ambiente.

## 2. Para quê? (Objetivo e Resultados Esperados)

Manter todos os dados de demonstração em JSON separado, impedir uso de mock em produção, não fazer fallback automático quando a API falha e fornecer timeout e URLs por ambiente.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Fallback automático para mock ao falhar a API (descartada):** pode apresentar conteúdo fictício como se fosse dado real.
- **Ativação explícita de mock somente no ambiente local (escolhida):** mantém demonstrações possíveis e falha de modo claro em produção.

### Detalhamento da Solução:

Os fixtures ficam em arquivos JSON na pasta de dados do frontend e são carregados pelo adaptador de demonstração. `APP_ENV` seleciona `API_URL_LOCAL` ou `API_URL_PRODUCTION`; `API_TIMEOUT` configura o tempo limite. `MODO_DEMONSTRACAO` só pode ser ativado em ambiente local. A URL de produção permanece vazia até que o endereço oficial seja definido e a inicialização em produção falha sem ela.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `frontend/services/`, `frontend/data/mocks/`, `frontend/tests/`.
- **Arquivos Criados / Modificados:** configuração de ambiente, fixtures JSON, carregador de mocks, adaptador de demonstração e testes.
- **Banco de Dados / Infra:** nenhum. Deploy deve definir `APP_ENV=production` e `API_URL_PRODUCTION`.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** elimina ambiguidade de ambiente e evita fallback silencioso para conteúdo fictício.
- **Riscos / Trade-offs:** produção não inicia chamadas ao backend até que a URL oficial esteja configurada.
- **Validação / Testes:** validar URLs por ambiente, bloqueio de mock em produção, carregamento de fixtures JSON e ausência de fallback automático em falhas de API.
