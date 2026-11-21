// MediFlow — proposta de esquema MongoDB para auditoria de documentos.
//
// MongoDB guarda eventos clínicos/auditoria flexíveis. PostgreSQL continua
// sendo a fonte da verdade para estado operacional, filas e relacionamentos.
// Um evento é inserido no Mongo a partir do auditoria_outbox do PostgreSQL.
//
// Convenção de IDs:
// - _id = evento_id do PostgreSQL, serializado como UUID em texto canônico.
// - stream_id = mongo_audit_stream_id do documento, também como UUID em texto.
// - documento_id = ID interno inteiro do documento no PostgreSQL.
// - sequencia = contador por documento, alocado na mesma transação do outbox.
//
// Não há coleção de projeção nesta versão. Para obter o histórico, consulte
// documento_eventos por stream_id e ordene por sequencia. Se a aplicação
// precisar do estado clínico corrente sem reproduzir os eventos, adicione uma
// projeção derivável/reconstruível em uma etapa posterior.

db.createCollection("documento_eventos", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Evento de auditoria do MediFlow",
      required: [
        "_id",
        "stream_id",
        "documento_id",
        "sequencia",
        "tipo",
        "ocorrido_em",
        "ator",
        "schema_versao",
        "payload"
      ],
      additionalProperties: false,
      properties: {
        _id: {
          bsonType: "string",
          description: "UUID do evento; igual ao evento_id no outbox PostgreSQL."
        },
        stream_id: {
          bsonType: "string",
          description: "UUID estável do stream deste documento."
        },
        documento_id: {
          bsonType: "int",
          description: "ID interno do documento no PostgreSQL."
        },
        sequencia: {
          bsonType: "long",
          minimum: 1,
          description: "Sequência crescente por documento, atribuída no PostgreSQL."
        },
        tipo: {
          bsonType: "string",
          minLength: 1,
          description: "Tipo do evento, definido pela aplicação."
        },
        ocorrido_em: {
          bsonType: "date",
          description: "Instante do evento em UTC."
        },
        ator: {
          bsonType: "object",
          required: ["tipo"],
          additionalProperties: false,
          properties: {
            tipo: {
              enum: ["SISTEMA", "USUARIO", "INTEGRACAO"]
            },
            id: {
              bsonType: ["string", "null"],
              description: "Identificador do ator; evitar nome ou dado pessoal desnecessário."
            }
          }
        },
        schema_versao: {
          bsonType: "int",
          minimum: 1,
          description: "Versão do formato de payload para evolução compatível."
        },
        payload: {
          bsonType: "object",
          description: "Dados do evento. Pode conter dados de saúde sensíveis (PHI)."
        },
        payload_hash: {
          bsonType: "string",
          pattern: "^[a-fA-F0-9]{64}$",
          description: "SHA-256 do conteúdo canônico, usado para conferir reenvio idempotente."
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// _id já possui índice único criado pelo MongoDB. Este índice também impede
// duas gravações diferentes para a mesma posição do stream.
db.documento_eventos.createIndex(
  { stream_id: 1, sequencia: 1 },
  { unique: true, name: "uq_eventos_stream_sequencia" }
);

// Consulta de histórico por documento interno, do mais recente ao mais antigo.
db.documento_eventos.createIndex(
  { documento_id: 1, ocorrido_em: -1 },
  { name: "ix_eventos_documento_data" }
);

// Regras de escrita e leitura:
// 1. Inserir eventos; não atualizar nem apagar eventos já publicados.
// 2. Mesmo _id e mesmo stream_id/sequencia/payload_hash = reenvio idempotente.
// 3. Mesmo _id com conteúdo diferente, ou mesma posição com outro _id = conflito
//    de integridade: bloquear o stream e alertar; não ignorar como duplicata.
// 4. Eventos fora de ordem podem ser armazenados, mas consumidores/projeções
//    devem aplicar sequencias em ordem e nunca avançar sobre uma lacuna.
// 5. Restringir acesso à coleção: payload pode conter dados clínicos sensíveis.
