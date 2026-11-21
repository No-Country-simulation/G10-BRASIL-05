# MongoDB atual — MediFlow

> Retrato do que o código atual declara e grava. Não é a proposta futura de eventos com `stream_id`/`sequencia` e não foi conferido contra uma instância MongoDB em execução.

## Banco e coleção

- **Database:** valor de `MONGODB_DATABASE` (Compose usa `MONGO_DB`).
- **Collection:** `auditoria_documentos`.
- **Repositório:** `backend/app/repositories/nosql_auditoria.py` (`MongoAuditoriaRepository`).
- A collection é criada implicitamente pelo MongoDB no primeiro insert. O código não configura validator JSON Schema nem regras de imutabilidade.

## Documento gravado

```javascript
{
  _id: ObjectId,                  // gerado pelo MongoDB
  documento_id: String,           // ID externo do documento, ex. "DOC-..."
  tipo_evento: String,
  autor: String,
  justificativa: String | null,   // campo omitido? O repositório grava null
  payload: Object,
  created_at: String              // ISO-8601 em UTC, não BSON Date
}
```

`documento_id` corresponde ao identificador textual `documentos_triagem.documento_id` do PostgreSQL atual, não ao PK inteiro `documentos_triagem.id`. A relação é lógica; o Mongo não declara uma FK.

## Eventos encontrados no código

| `tipo_evento` | `autor` | Conteúdo de `payload` |
|---|---|---|
| `TRIAGEM_INICIAL` | `Sistema_IA` | `classificacao`, `dados_extraidos`, `decisao_roteamento` |
| `BLOQUEIO_EXCLUSIVO` | Nome do usuário | `ttl_segundos` |
| `DESBLOQUEIO_AUDITORIA` | Nome do usuário | Objeto vazio `{}` |
| `DECISAO_MEDICA_<STATUS>` | Nome do auditor | Dados corrigidos ou `{}` |

O evento `TRIAGEM_INICIAL` também passa a justificativa separadamente em `justificativa`. O formato interno dos objetos de `payload` vem dos modelos/valores da aplicação e não é validado pelo Mongo.

## Índices atuais

```javascript
db.auditoria_documentos.createIndex({ documento_id: 1 });
db.auditoria_documentos.createIndex({ created_at: -1 });
```

Ambos são não únicos. A consulta por documento filtra por `documento_id` e ordena `created_at` em ordem decrescente. A listagem geral ordena por `created_at` decrescente.

## Comportamento atual observado no código

- Cada chamada a `gravar_evento` faz `insert_one`; não há `evento_id`, sequência por documento ou deduplicação no Mongo.
- “Append-only” é convenção de uso: não há regra de banco impedindo update/delete.
- O Mongo recebe eventos de triagem e auditoria; dados completos do documento também são persistidos no PostgreSQL.
- A gravação da triagem no PostgreSQL é confirmada antes do insert Mongo. A falha do registro Mongo é capturada e ignorada nesse trecho, então os dois bancos podem divergir.
- A API converte `_id` para texto ao devolver os eventos.

## Fora desta estrutura

Redis é usado pelo projeto para fila/estado operacional, locks, sessões/idempotência e Pub/Sub; não é uma coleção Mongo. O checkpointer do LangGraph usa PostgreSQL.
