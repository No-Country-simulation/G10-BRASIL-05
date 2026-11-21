# [0035] - Reorganização PostgreSQL/MongoDB com reset local do MediFlow

- **Data:** 2026-11-21
- **Autor(es):** Patrick Jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

O esquema atual do PostgreSQL mistura dados operacionais, JSON clínico e metadados de arquivos. A trilha Mongo atual não tem idempotência, sequência por documento nem garantia de publicação: a triagem confirma o PostgreSQL antes de gravar no Mongo e pode ignorar a falha. A equipe decidiu reconstruir o modelo de desenvolvimento conforme a proposta v4 e as decisões complementares registradas nesta conversa.

## 2. Para quê? (Objetivo e Resultados Esperados)

- PostgreSQL como fonte da verdade relacional e operacional.
- MongoDB como trilha de eventos clínicos/auditoria, sem projeção separada nesta etapa.
- Publicação PostgreSQL → Mongo com outbox transacional, `evento_id` idempotente e sequência por documento.
- Reset reproduzível apenas dos bancos locais do MediFlow, preservando a base separada da Evolution.
- Seeds atuais mantidas, com novas seeds documentadas se as novas tabelas exigirem dados de domínio.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas

- **Alternativa A (Descartada):** guardar trilha e JSONs flexíveis apenas em JSONB no PostgreSQL; não atende à decisão do projeto de manter MongoDB para auditoria.
- **Alternativa B (Escolhida):** PostgreSQL relacional + MongoDB para eventos, ligados por outbox; evento e alteração operacional são gravados na mesma transação PostgreSQL.
- **Reset:** usar um script explicitamente destrutivo e restrito a desenvolvimento, em vez de uma revisão Alembic normal que apaga o banco. A Alembic fica com um baseline limpo do esquema v4.

### Detalhamento da Solução

- O outbox referencia o ID interno do documento e guarda cópia imutável de `documento_externo_id` para publicar sem junção.
- `versao` controla concorrência otimista; `ultima_sequencia` ordena eventos. A sequência é alocada na transação que insere o outbox.
- Mongo usa a coleção `auditoria_documentos`; novos eventos incluem `evento_id`, `documento_id` externo textual, `sequencia`, `tipo_evento`, `autor`, `justificativa`, `payload`, `payload_hash` e `created_at` BSON Date.
- O reset remove o schema do banco PostgreSQL dedicado ao MediFlow e a base Mongo de auditoria, sem remover volumes ou bancos usados pela Evolution.
- As seeds existentes permanecem idempotentes. A carga de domínios necessários para V4 será incluída apenas se a implementação comprovar essa necessidade.
- Dados legados serão descartados no reset local, conforme autorização explícita do usuário; este mecanismo não será executado contra instância compartilhada/produção.

## 4. Onde? (Impacto no Código e Arquitetura)

- `backend/app/models/`: entidades e associações do esquema v4, outbox e controle de concorrência.
- `backend/migrations/versions/`: baseline Alembic reconstruído para o esquema novo.
- `backend/app/services/` e `backend/app/repositories/`: persistência transacional, decisão condicional e worker do outbox.
- `scripts/`: reset local protegido para PostgreSQL/MongoDB.
- `DOCUMENTOS/`: diagramas e instruções do esquema atualizado.
- PostgreSQL e MongoDB locais serão recriados; Redis e o banco de Evolution ficam preservados.

## 5. Consequências e Débitos Técnicos

- **Pontos positivos:** elimina falha silenciosa de auditoria, define fonte da verdade e torna o reset de desenvolvimento reproduzível.
- **Riscos / Trade-offs:** reset local perde dados; uso indevido do script pode causar perda de dados, por isso exige ambiente local e confirmação explícita por variável.
- **Validação / Testes:** revisar migrations em banco vazio, executar seed idempotente, verificar índices/constraints e fazer um fluxo de outbox com duplicata e indisponibilidade temporária do Mongo.
