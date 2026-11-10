# [0005] - Validar Decisões e Correções da Auditoria (SCRUM-108)

- **Data:** 2026-11-05
- **Autor(es):** @Pedro_Araujo04 (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

O contrato de decisão de auditoria aceita qualquer texto em `status_aprovacao` e qualquer dicionário em `dados_corrigidos`. Isso permite encerrar uma auditoria com status inválido e gravar correções que não seguem o schema dos dados clínicos. A execução dos testes também emitia avisos de depreciação por metadados `example` e pelo status HTTP 422.

## 2. Para quê? (Objetivo e Resultados Esperados)

Rejeitar decisões inválidas antes da persistência e manter as correções da auditoria no mesmo contrato clínico utilizado pelo restante do backend.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas

- **Alternativa A (Descartada):** Criar um segundo schema para correções de auditoria. Isso duplicaria o contrato clínico e poderia divergir ao longo do tempo.
- **Alternativa B (Escolhida):** Reutilizar `app.schemas.dados_extraidos.DadosExtraidos` no payload da decisão e validar as regras cruzadas no próprio schema da requisição.

### Detalhamento da Solução

- Restringir `status_aprovacao` aos valores `aprovado`, `corrigido` e `rejeitado`.
- Exigir `dados_corrigidos` com ao menos um valor clínico efetivamente preenchido quando o status for `corrigido`.
- Rejeitar `dados_corrigidos` para os status `aprovado` e `rejeitado`.
- Aceitar correções parciais que obedeçam ao schema clínico existente.
- Normalizar o campo legado `medico_solicitante.crm` para `crm_uf` no payload montado pela interface de auditoria.
- Deixar a validação Pydantic ocorrer antes da chamada ao serviço/repositório, para payload inválido resultar em HTTP 422 sem mutação persistida.
- Serializar o modelo clínico validado como dicionário antes de enviá-lo aos repositórios JSON do PostgreSQL e da trilha NoSQL.
- Usar `json_schema_extra` para os exemplos Pydantic e o código 422 sem acessar a constante depreciada do Starlette.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/schemas/`, `backend/app/controllers/`, `backend/app/config/`, `backend/app/services/`, `backend/tests/`, `frontend/utils/` e `frontend/tests/`.
- **Arquivos Criados / Modificados:** `backend/app/schemas/triagem.py`, `backend/app/controllers/evolution.py`, `backend/app/config/error_handlers.py`, `backend/app/services/triagem.py`, `backend/tests/test_decisao_auditoria_schema.py`, `backend/tests/test_decisao_auditoria_endpoint.py`, `backend/tests/test_decisao_auditoria_service.py`, `frontend/utils/auditoria.py` e `frontend/tests/test_auditoria.py`.
- **Banco de Dados / Infra:** Sem alteração de banco ou infraestrutura.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Status explícitos, dados corrigidos tipados e falhas rejeitadas no limite da API antes de alterar persistência; os testes não emitem os avisos de depreciação observados.
- **Riscos / Trade-offs:** Correções parciais são válidas pelo contrato existente; este schema garante estrutura/tipos, sem validar regras clínicas adicionais não incluídas no contrato de extração.
- **Validação / Testes:** Testes unitários do schema, serviço e interface; regressões do endpoint para status, correções ausentes/vazias/inválidas, correção parcial válida e não invocação da camada de serviço em requests inválidas.
