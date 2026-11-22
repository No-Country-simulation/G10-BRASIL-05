// MediFlow — índices da coleção auditoria_documentos (V4 implementada).
// Executar uma vez após criar/resetar somente o banco de auditoria do MediFlow.
// O script é idempotente e não apaga nem altera documentos existentes.

db.auditoria_documentos.createIndex(
  { evento_id: 1 },
  {
    unique: true,
    partialFilterExpression: { evento_id: { $type: "string" } },
    name: "uq_auditoria_evento_id"
  }
);

db.auditoria_documentos.createIndex(
  { documento_id: 1, sequencia: 1 },
  {
    unique: true,
    partialFilterExpression: { sequencia: { $type: "number" } },
    name: "uq_auditoria_documento_sequencia"
  }
);

db.auditoria_documentos.createIndex(
  { documento_id: 1, sequencia: 1, created_at: 1, _id: 1 },
  { name: "ix_auditoria_timeline" }
);

// Eventos publicados pelo outbox:
// {
//   _id: ObjectId,
//   evento_id: "uuid",
//   documento_id: "ID externo textual",
//   sequencia: NumberInt(1),
//   tipo_evento: "TRIAGEM_INICIAL" | "REVISAO_INICIADA" | "DECISAO_MEDICA_*",
//   autor: String,
//   justificativa: String | null,
//   payload: Object,
//   payload_hash: "sha256",
//   created_at: ISODate(...)
// }
