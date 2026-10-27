# [0009] - Auditoria Avançada de Documentos Clínicos com Redis e MongoDB (NoSQL)

- **Data:** 2026-10-26
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Em sistemas hospitalares e de triagem clínica autônoma, a auditoria é um requisito crítico de conformidade regulatória (LGPD, CFM e ANVISA):
1. **Concorrência Médica (Race Conditions no Human-in-the-Loop):** Quando múltiplos médicos ou auditores clínicos acessam a fila de auditoria simultaneamente, há o risco de dois profissionais começarem a auditar e sobrescrever o mesmo documento clínico ao mesmo tempo.
2. **Volumetria e Imutabilidade de Documentos Clínicos:** Documentos clínicos brutos (textos de laudos, logs de execução do grafo LangGraph, payloads JSON de diferentes especialidades e diffs de correção médica) possuem formatos variáveis e exigem histórico append-only imutável de auditoria sem sobrecarregar a modelagem relacional estrita do PostgreSQL.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- **Redis (Lock Distribuído & Streaming de Eventos):**
  - Implementar Lock Distribuído com TTL automático (`lock:auditoria:{documento_id}`) para garantir que um documento em revisão fique reservado com exclusividade para o médico responsável.
  - Publicação de eventos de auditoria em canal de telemetria em tempo real (`mediflow:auditoria:eventos`).
- **MongoDB (Repositório NoSQL Append-Only de Auditoria):**
  - Armazenar histórico completo e imutável de eventos clínicos: versão original do documento, sugestões da IA, revisões humanas, justificativas e carimbos de tempo.
  - Consulta rápida de trilha de auditoria longitudinal por documento (`GET /triagem/auditoria/{id}/historico-nosql`).
- **Resiliência e Fallback Transparente:**
  - Prover cliente híbrido com fallback gracioso em memória caso os daemons de Redis ou MongoDB não estejam presentes no host, mantendo 100% de estabilidade nos testes automatizados e em deploys isolados.
- **Docker Compose:**
  - Incluir serviços oficiais `redis:7-alpine` e `mongo:7` no `docker-compose.yml`.

---

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Persistir todos os logs brutos e locks exclusivamente no PostgreSQL.
  - *Motivo do descarte:* Bloqueios pessimistas (`SELECT FOR UPDATE`) no Postgres degradam a performance de triagem em alta concorrência; schemas relacionais rígidos sofrem com a flexibilidade de dados semiestruturados de auditoria médica.
- **Alternativa B (Escolhida):** Arquitetura Poliglota com Redis (Locks e Streams) + MongoDB (NoSQL Document Store de Auditoria) com Fallback Gracioso.
  - *Motivo da escolha:* Combina alta velocidade em memória para controle de concorrência com a flexibilidade NoSQL para conformidade e rastreabilidade total.

### Detalhamento da Solução:
1. **Infraestrutura (`docker-compose.yml`):**
   - Serviço `redis` na porta 6379 com healthcheck `redis-cli ping`.
   - Serviço `mongo` na porta 27017 com volume persistente `mongodata`.
2. **Dependências (`backend/requirements.txt`):**
   - `redis>=5.0.0`
   - `pymongo>=4.6.0`
3. **Módulo Redis (`backend/app/services/redis_service.py`):**
   - Gerenciador com suporte a `adquirir_lock(documento_id, auditor_nome, ttl_segundos)`, `liberar_lock(documento_id, auditor_nome)` e `publicar_evento(canal, payload)`.
4. **Módulo NoSQL Auditoria (`backend/app/repositories/nosql_auditoria.py`):**
   - Repositório com suporte a `gravar_evento_auditoria(documento_id, tipo_evento, payload, autor)` e `listar_historico_documento(documento_id)`.
5. **Endpoints de Auditoria (`backend/app/controllers/triagem.py`):**
   - `POST /triagem/auditoria/{id}/bloquear` (adquirir lock exclusivo de revisão)
   - `POST /triagem/auditoria/{id}/desbloquear` (liberar lock)
   - `GET /triagem/auditoria/{id}/trilha-nosql` (consultar histórico imutável no MongoDB)

---

## 4. Onde? (Impacto no Código e Arquitetura)
- `docker-compose.yml`: Adicionados serviços Redis e MongoDB.
- `backend/requirements.txt`: Dependências `redis` e `pymongo`.
- `backend/app/config/settings.py`: Novas variáveis `REDIS_URL` e `MONGODB_URL`.
- `backend/app/services/redis_service.py`: Gerenciamento de lock distribuído e pubsub.
- `backend/app/repositories/nosql_auditoria.py`: Persistência de documentos de auditoria NoSQL.
- `backend/app/controllers/triagem.py`: Endpoints de lock e consulta de trilha NoSQL.
- `backend/tests/test_auditoria_redis_mongodb.py`: Testes automatizados.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Elimina conflitos de concorrência na auditoria médica e garante rastreabilidade regulatória completa (LGPD) com consultas rápidas e imutáveis.
- **Riscos / Trade-offs:** Introdução de dois novos serviços de banco de dados; mitigado por fallback gracioso em memória caso algum serviço esteja temporariamente inacessível.
- **Validação / Testes:** Testes cobrindo aquisição/liberação de lock, conflito de lock com outro médico, gravação e recuperação de eventos no MongoDB e resiliência em caso de desconexão.
