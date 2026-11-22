# MongoDB de auditoria MediFlow — V4 implementada

O Mongo armazena uma coleção de eventos por documento. O PostgreSQL mantém as relações e o estado operacional; a publicação é feita pelo outbox transacional. O detalhe clínico da triagem é reconstituído dos eventos no Mongo.

## Banco e coleção

- Banco configurado por `MONGODB_DATABASE` (local: `mediflow_auditoria`).
- Coleção: `auditoria_documentos`.
- Chave do stream: `documento_id`, o identificador externo textual `documento_externo_id` do PostgreSQL.
- O ID interno inteiro do PostgreSQL fica somente no outbox, junto com a cópia do ID externo.

## Evento publicado

```javascript
{
  _id: ObjectId,
  evento_id: "uuid",
  documento_id: "DOC-...",
  sequencia: 1,
  tipo_evento: "TRIAGEM_INICIAL",
  autor: "Sistema_IA",
  justificativa: "..." | null,
  payload: { /* conteúdo do evento */ },
  payload_hash: "sha256",
  created_at: ISODate("...")
}
```

`evento_id` é a chave idempotente compartilhada com o outbox. `sequencia` é alocada por documento na mesma transação PostgreSQL que grava a alteração operacional e o outbox. `created_at` é BSON Date com o horário de ocorrência do evento.

## Índices criados no reset local

- Índice único parcial em `evento_id` para eventos novos.
- Índice único parcial em `(documento_id, sequencia)` para eventos numerados.
- Índice de leitura da linha do tempo `(documento_id, sequencia, created_at, _id)`.

O script idempotente está em `DOCUMENTOS/diagrama_mongodb.js`; o reset local também cria esses índices. A aplicação não precisa de permissão `createIndex` em runtime.

## Publicação e ordenação

- `TRIAGEM_INICIAL`, `REVISAO_INICIADA` e `DECISAO_MEDICA_*` são gravados primeiro no outbox, dentro da transação PostgreSQL.
- O worker publica com retry e lease. Uma duplicata de `evento_id` só é sucesso se stream, sequência, tipo e hash coincidirem; divergência é erro de integridade.
- Eventos antigos do modelo anterior são removidos pelo reset local autorizado. A sequência começa em 1 para eventos novos; não há corte de histórico neste ambiente reconstruído.
- `DESBLOQUEIO_AUDITORIA` não é evento oficial, pois o lock vive no Redis. Ausência de decisão depois do evento de início prova somente que nenhuma decisão foi registrada na trilha.

## Nota de proteção de dados

O payload contém dados clínicos e deve ser tratado como PHI. A trilha não tem TTL configurado; retenção, anonimização e políticas de leitura precisam ser definidas antes de produção.
