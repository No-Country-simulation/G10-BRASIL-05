# Pendências e propostas para os bancos e processamento assíncrono

> Documento de acompanhamento para priorizar com a equipe. Registra achados do código e caminhos de correção; **não implementa** mudanças no backend ou no Compose.

## 1. Fila Redis pode confirmar um trabalho que não foi enfileirado

**Comportamento atual:** `reservar_trabalho()` retorna sucesso quando Redis lança exceção. `enfileirar_documento()` e `enfileirar_texto()` capturam falhas de enqueue e retornam `None`. Os endpoints não conferem esse resultado e podem devolver `status="na_fila"` mesmo sem job no RQ. O lote também pode cair num dicionário em memória, que não é compartilhado entre processos.

**Impacto:** a interface mostra processamento pendente que nunca começará; reinício da API também perde o lote guardado apenas em memória.

**Proposta de tratamento:**

1. Falhar de forma explícita quando Redis não reservar ou confirmar o job. Não retornar `na_fila` sem o job aceito pelo RQ.
2. Fazer o repositório de fila propagar uma exceção tipada ou retornar um resultado explícito com `aceito/job_id`; não engolir exceções.
3. No endpoint, em falha, liberar reserva/lock, desfazer armazenamento parcial quando seguro e responder `503` com mensagem de serviço temporariamente indisponível. Se for importante rastrear o envio, persistir um estado `falhou` no PostgreSQL com código de erro e permitir reenvio explícito.
4. Só publicar evento SSE e registrar o lote como `na_fila` depois que o RQ confirmar o job. Use `documento_id` como chave idempotente e trate reenvios sem duplicar trabalhos.
5. Remover o fallback em memória como se fosse fila durável; se mantido para desenvolvimento, expor claramente que não há garantia de persistência e não responder sucesso de produção.
6. Cobrir com testes a indisponibilidade em cada etapa: reserva, enqueue, registro de lote, publicação do evento e rollback do arquivo.

## 2. Ordem recomendada de inicialização no Docker Compose

PostgreSQL, Redis e MongoDB são dependências independentes e podem subir em paralelo. O backend precisa esperar as três dependências ficarem saudáveis antes de aceitar triagens; hoje ele aplica migrations e abre o checkpointer PostgreSQL no startup, mas também instancia os repositórios Mongo/Redis ao processar triagem.

```text
PostgreSQL saudável ──┬──> init do banco Evolution concluído ──> Evolution API
                      └──> Backend (aguarda PostgreSQL + Redis + Mongo saudáveis)
Redis saudável ────────┘                     │
Mongo saudável ─────────────────────────────┤
                                            ├──> Frontend
                                            └──> Worker RQ
```

- Configure `backend.depends_on` com `condition: service_healthy` para `postgres`, `redis` e `mongodb`.
- Mantenha `evolution-db-init` dependente do PostgreSQL saudável e a Evolution dependente da conclusão do init e do Redis saudável.
- Frontend e worker devem aguardar backend saudável; o worker também usa Redis.
- O backend não precisa aguardar a Evolution para inicializar sua API. Se um endpoint de WhatsApp exigir Evolution indisponível, esse endpoint deve retornar erro claro sem derrubar o serviço inteiro.
- Verifique a prontidão real no endpoint de health: hoje `/health` responde valores estáticos e não mede conexões aos bancos. Separe liveness (processo vivo) de readiness (dependências requeridas disponíveis).
- `COMPOSE_PROFILES=infra` precisa estar ativo para subir os serviços de infraestrutura e worker declarados nesse perfil.

Dependências Compose ordenam início e podem aguardar healthcheck, mas não substituem reconexão e tratamento de perda de dependência depois do startup.

## 3. Auditoria: papel oficial do MongoDB e referência PostgreSQL

**Entendimento do objetivo:** MongoDB deve ser o registro oficial dos eventos e versões JSON da auditoria — o que a IA produziu e o que o profissional aprovou, corrigiu ou rejeitou. PostgreSQL continua sendo o banco principal para o estado operacional atual, cadastro, filtros e relações. A linha de `documentos_triagem` proposta fica menor e guarda uma referência lógica (`mongo_audit_stream_id`), em vez de duplicar o texto OCR, o resultado clínico JSON e suas evidências.

**Hoje há sobreposição:** `AuditoriaDatabaseRepository.registrar_decisao()` grava decisão, justificativa, `dados_anteriores` e `dados_finais` na tabela `trilha_auditoria`; também atualiza o estado atual em `documentos_triagem`. O fluxo de serviço grava alguns eventos e payloads no Mongo, mas a cobertura não é uniforme. Isso permite diferença entre o JSON do PostgreSQL e os eventos Mongo.

**Modelo alvo proposto:**

- Mongo: um documento por evento em `auditoria_documentos`, sem array infinito de eventos dentro de um único documento. Campos propostos: `event_id` (UUID idempotente), `mongo_audit_stream_id`, `documento_id`, `tipo_evento`, `autor`, `justificativa`, `created_at` e `payload` versionado. O `payload` pode conter o snapshot JSON da classificação, dados extraídos, texto OCR, evidências, metadados, decisão de roteamento e/ou correções humanas pertinentes àquele evento.
- PostgreSQL: manter estado operacional e campos consultados/relacionados de `documentos_triagem`; acrescentar `mongo_audit_stream_id` como referência lógica estável para buscar a trilha do documento. Manter no PostgreSQL chaves estrangeiras de paciente/médico/hospital, classificação/status/prioridade/destino, campos curtos necessários à fila e as referências ao arquivo no OCI. Não guardar URL de conexão ou credencial como referência.
- Remover da linha corrente do PostgreSQL, após migração validada, `documento_texto`, `dados_extraidos`, `evidencias_campos`, `metadados_documento`, `campos_rotulados` e `evidencias_escopo`, que passam ao snapshot de auditoria Mongo. A tabela `trilha_auditoria` deixa de guardar `dados_anteriores`/`dados_finais` duplicados; a trilha oficial passa a ser consultada no Mongo. A tabela só deve ser removida/encolhida depois da migração e backup.
- Criar índice único de idempotência no identificador do evento em Mongo, além dos índices de consulta por documento/data. Uma referência para evento deve permitir consultar a trilha inteira pelo `documento_id`.
- Definir política de retenção, acesso, exportação e exclusão conforme regras de auditoria e LGPD. “Append-only” precisa de controles operacionais/autorizativos; não é garantido só pelo fato de usar Mongo.

**Consistência entre dois bancos:** PostgreSQL e Mongo não compartilham uma transação ACID local. Para evitar que uma gravação relacional confirme e a gravação Mongo desapareça (ou vice-versa), recomenda-se o padrão **outbox**: gravar a alteração relacional e um evento de auditoria pendente na mesma transação PostgreSQL; um worker publica no Mongo com `event_id` idempotente; após confirmação, marca o outbox como entregue e guarda o ID Mongo. O payload na outbox é staging transitório para reentrega, não uma cópia de consulta permanente; remover seu conteúdo publicado conforme a política definida. Falhas ficam retentáveis e observáveis. A fonte oficial de auditoria é Mongo.

**DBML da proposta:** [diagrama_proposta_postgresql.dbml](diagrama_proposta_postgresql.dbml) mostra o recorte relacional proposto, com uma linha operacional menor em `documentos_triagem` e a tabela transitória `auditoria_outbox`. Ele é separado do [diagrama do PostgreSQL atual](diagrama_postgresql.dbml). O DBML modela somente as tabelas relacionais; a coleção Mongo é documentada como JSON e não deve ser apresentada como tabela SQL.

**Revisão da proposta incorporada:** o DBML agora identifica médicos por `(crm, uf)` e enfermeiros por `(coren, uf)`; remove defaults de cidade/UF que poderiam inventar localização; deixa a confiança sem valor presumido e inicia prioridade como `Indefinida`, com revisão humana ligada por padrão; mantém hospital como subtipo de `estabelecimentos_saude`, usando `estabelecimento_id` como PK/FK; liga documento a atendimento e destino por FK; e registra documento de origem no encaminhamento. Inclui estado consultável da revisão humana (revisor, data e decisão), índices para a fila e FKs usadas na triagem, hash SHA-256 do original, e usuário responsável pela instância WhatsApp como FK. Vínculos profissionais usam chave substituta e início do vínculo para preservar períodos históricos. Datas estão como `timestamptz`, e a outbox usa `jsonb`.

Algumas decisões precisam ser confirmadas ao implementar: os domínios exatos de status, escopo, legibilidade e papel precisam virar `CHECK`/enum; o DBML anota os domínios candidatos, mas notas não criam constraints no banco. A migration deve criar índice único parcial do webhook (`whatsapp_message_id IS NOT NULL`) e índice parcial de pendências da outbox; o worker deve reivindicar eventos com `FOR UPDATE SKIP LOCKED`. A gravação operacional e o evento outbox precisam compartilhar a mesma transação PostgreSQL. A proposta mantém `data_nascimento` no cadastro e a idade tal como extraída no snapshot Mongo. Diagnóstico/CID ficam em Mongo enquanto não houver requisito de filtro relacional; se a equipe precisar filtrar por eles no PostgreSQL, adicionar campos de busca com origem/proveniência explícita. Para produção, definir proteção de CPF/nome (criptografia, controle de acesso, retenção e estratégia de busca) conforme LGPD.

Exemplo conceitual de evento Mongo (nomes/campos ainda sujeitos à aprovação do contrato):

```json
{
  "event_id": "uuid-imutavel-por-evento",
  "mongo_audit_stream_id": "uuid-estavel-por-documento",
  "documento_id": "DOC-...",
  "tipo_evento": "TRIAGEM_INICIAL",
  "autor": "Sistema_IA",
  "justificativa": "...",
  "created_at": "2026-11-21T00:00:00Z",
  "payload": {
    "schema_version": 1,
    "texto_ocr": "...",
    "classificacao": {},
    "dados_extraidos": {},
    "evidencias_campos": {},
    "metadados_documento": {},
    "evidencias_escopo": {},
    "decisao_roteamento": {}
  }
}
```

**Migração sugerida, quando aprovada:** mapear todos os eventos atuais; definir contrato e identificadores; começar a gravar eventos Mongo de forma idempotente; validar o novo estado relacional e fluxo de revisão; comparar contagens e payloads; migrar referências; então parar de duplicar snapshots em `trilha_auditoria` e planejar migration de remoção/arquivamento somente depois de backup e validação. Esta revisão do DBML é uma proposta arquitetural, não uma migration aplicada nem confirmação do esquema efetivamente implantado.

## 4. Mongo indisponível e divergência entre decisão e código

O repositório Mongo atual faz `ping` na construção e lança erro se não conectar. `TriagemService` instancia esse repositório junto com Redis; portanto, as operações que instanciam o serviço dependem de Mongo. Uma ADR antiga descreve fallback em memória, mas isso não corresponde ao comportamento atual.

**Proposta:** escolher explicitamente o requisito de disponibilidade. Para auditoria clínica, não descartar eventos silenciosamente: preferir outbox durável e retry. Se a política for impedir triagem sem registro de auditoria, falhar com erro operacional claro; se a política permitir triagem degradada, persistir outbox no PostgreSQL e alertar até entrega no Mongo. Atualizar a ADR e os testes para refletir a opção escolhida.

## 5. Escalabilidade

- **Worker:** já há `TRIAGEM_WORKER_CONCURRENCY`, que cria vários processos consumidores dentro de um container. Comece aumentando isso com limites de CPU/memória monitorados. Para escala horizontal, use vários containers de worker consumindo a mesma fila e assegure idempotência dos jobs.
- **Compose atual:** `container_name: g10-worker` (e nomes fixos nos outros serviços) impede o `docker compose --scale` para esse serviço. Remover nomes fixos dos serviços que serão replicados e deixar o Compose gerar nomes por réplica.
- **API/frontend:** o Compose local representa instâncias únicas. Escala horizontal futura requer proxy/load balancer e atenção a sessões Streamlit, limites de conexões PostgreSQL, pools e callbacks/webhooks.
- **Bancos:** PostgreSQL, Mongo e Redis estão configurados como instâncias únicas no Compose; são pontos únicos de falha. Para ambiente de produção com alta disponibilidade, avaliar serviços gerenciados/replicação, backups testados, monitoramento e recuperação antes de aumentar réplicas de aplicação.
- **Redis:** o Compose usa volume, mas não configura explicitamente política RDB/AOF. Definir se fila e estado operacional podem ser reconstruídos ou exigem persistência e escolher AOF/RDB conforme RPO/RTO.
- **Observabilidade:** medir profundidade e idade da fila, falhas/retries, disponibilidade dos bancos, jobs presos, outbox pendente, tempo de triagem e uso de conexões. Alertar antes de escalar apenas por concorrência.

## 6. Prioridade sugerida

1. **P0 — confiabilidade:** corrigir resposta `na_fila` falsa e fallback de reserva Redis.
2. **P1 — inicialização e prontidão:** dependências saudáveis no Compose e health/readiness real.
3. **P1 — integridade da auditoria:** aprovar contrato Mongo + referência PG + outbox/idempotência.
4. **P2 — reconciliação:** alinhar ADR, testes, modelos e migrations; documentar tabelas relacionais ainda sem modelos.
5. **P2 — escala/recuperação:** remover `container_name` conforme necessidade, definir persistência Redis e plano de backup/restore.

## Referências no código

- Fila e tratamento de falhas: `backend/app/services/triagem_queue.py`, `backend/app/controllers/triagem_jobs.py`.
- Modelos relacionais e snapshots: `backend/app/models/triagem.py`, `backend/app/repositories/auditoria_database.py`.
- Eventos Mongo: `backend/app/repositories/nosql_auditoria.py`, `backend/app/services/triagem.py`.
- Dependências e healthchecks: `docker-compose.yml`, `backend/app/main.py`, `backend/app/api/router.py`.
