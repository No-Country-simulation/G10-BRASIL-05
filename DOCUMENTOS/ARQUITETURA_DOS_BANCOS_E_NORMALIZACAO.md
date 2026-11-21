# Bancos de dados e normalização do MediFlow

## Escopo e fonte desta documentação

Este documento descreve o que está configurado no código, nas migrations e no Docker Compose do projeto. A instância PostgreSQL não respondeu durante a inspeção e o acesso ao Docker estava indisponível; portanto, este inventário não foi comparado com bancos em execução.

## Visão geral

| Tecnologia | Uso no MediFlow | Dados principais | Modelo |
|---|---|---|---|
| PostgreSQL | Fonte relacional principal e checkpointer do LangGraph | Cadastros clínicos, documentos, usuários, decisões e estado durável do grafo | Relacional, com colunas JSON para conteúdo variável |
| MongoDB | Eventos de auditoria | Eventos de triagem, bloqueios e decisões com payload variável | Documentos BSON sem esquema rígido declarado no código |
| Redis | Fila, coordenação e dados temporários | Trabalhos RQ, locks, sessões, idempotência, Pub/Sub e snapshots SSE | Chaves e estruturas de dados; não relacional |
| PostgreSQL da Evolution | Persistência própria da Evolution API | Instâncias e dados operacionais da integração WhatsApp | Banco lógico separado no mesmo servidor PostgreSQL |
| OCI / armazenamento local | Arquivos originais e artefatos | Imagens, PDFs e arquivos de triagem | Armazenamento de objetos/arquivos, não banco de dados |

O frontend Streamlit deve acessar esses recursos somente pela API FastAPI. A configuração do frontend aponta para `backend:8000` dentro do Compose; o backend acessa bancos e armazenamento.

A estrutura do pipeline de inteligência artificial está descrita à parte em [Arquitetura da IA de triagem](ARQUITETURA_IA_TRIAGEM.md).

## PostgreSQL

### Tabelas e relações

Os modelos SQLAlchemy atuais declaram:

- `hospitais`
- `medicos`
- `pacientes`
- `documentos_triagem`
- `trilha_auditoria`
- `usuarios_sistema`
- `instancias_whatsapp`

`documentos_triagem` referencia paciente, médico e hospital por chaves estrangeiras. CPF do paciente e CRM do médico são campos únicos nos modelos. A tabela de documentos mantém classificação, status, roteamento e revisão, além de campos JSON (`dados_extraidos`, evidências e metadados) para resultados que variam conforme o documento.

As migrations também criam estruturas do ecossistema institucional: `enfermeiros`, `estabelecimentos_saude`, `categorias_hospital`, tabelas de associação entre estabelecimentos/profissionais e hospitais/diretores, `atendimentos`, `destinos_roteamento` e `encaminhamentos`. Algumas dessas tabelas não têm modelo SQLAlchemy correspondente em `backend/app/models/triagem.py`; vale manter um inventário explícito da cobertura entre migrations, modelos e rotas.

O banco `evolution` é criado separadamente para as migrations da Evolution API. Compartilha o servidor PostgreSQL do Compose, mas não o banco lógico do MediFlow.

### Formas normais

As formas normais são critérios do modelo relacional. Em termos simples, 3FN é a mais normalizada dentre 1FN, 2FN e 3FN; “filtragem” é outro conceito.

- **1FN:** as colunas escalares do núcleo relacional são atômicas. Os campos JSON de documentos podem conter objetos e listas aninhados; isso não segue a interpretação estrita de atomicidade da 1FN, embora seja uma escolha útil para dados clínicos variáveis.
- **2FN:** as tabelas principais usam chaves primárias simples. As tabelas associativas usam chaves compostas formadas pelos identificadores relacionados; não há atributos descritivos aparentes que dependam de apenas parte dessas chaves.
- **3FN:** o núcleo de pacientes, médicos, hospitais e documentos separa entidades e liga os documentos por FKs, o que é consistente com 3FN em alto nível. Não é uma certificação formal de todo o esquema; seria preciso validar cada dependência funcional e o banco implantado.

Há um ponto de integridade a considerar: `trilha_auditoria.documento_id` é indexado, mas não é uma FK para `documentos_triagem`; a relação não é garantida pelo banco.

## MongoDB

- Database vem de `MONGODB_DATABASE`; no Compose, o nome é configurado por `MONGO_DB`.
- Collection usada: `auditoria_documentos`.
- Documento gravado pelo repositório: `documento_id`, `tipo_evento`, `autor`, `justificativa` opcional, `payload` e `created_at`.
- Índices atuais: não únicos em `documento_id` e `created_at`. A consulta por documento ordena eventos do mais recente para o mais antigo.
- O formato de `payload` é flexível; o código não declara validador de schema Mongo nem mecanismo que torne a collection imutável. “Append-only” é a convenção de uso, não uma garantia configurada pelo banco.

**Normalização:** 1FN/2FN/3FN não se aplicam diretamente a coleções documentais da mesma forma que a tabelas relacionais. A decisão principal é quais campos manter no envelope do evento e quais podem variar dentro de `payload`.

**Consistência a revisar:** a decisão arquitetural 0009 descreve fallback em memória quando Mongo estiver indisponível, mas o repositório atual falha no `ping` e lança erro. A inicialização de `TriagemService` também instancia o repositório, então Mongo é uma dependência operacional do serviço. Hoje a trilha é persistida parcialmente no PostgreSQL e parcialmente no Mongo; a direção proposta é Mongo como registro oficial dos eventos e snapshots de auditoria, com o PostgreSQL mantendo o estado atual consultável e referências aos eventos Mongo. Essa mudança ainda não foi implementada.

## Redis

Redis 7 usa o banco lógico **0** no backend e **1** na Evolution API (com prefixo `evolution` para os dados da integração). No projeto, atende fila e estado operacional; não é o registro clínico permanente.

| Chave/estrutura | Uso | Expiração observada |
|---|---|---|
| RQ queue `triagem` | Trabalhos de processamento assíncrono | Job concluído: resultado não retido (`result_ttl=0`); falha: até 24h |
| `triagem:usuario:{id}:trabalhos` (Set) | Trabalhos ativos por usuário; limite de 10 | 24h |
| `triagem:documento:{id}:proprietario` (String) | Reserva/identificação do proprietário do trabalho | 24h |
| `triagem:lote:{id}` (String JSON) | Estado do lote para consulta e SSE | 24h |
| `lock:auditoria:{documento_id}` | Exclusividade temporária da revisão | 300s por padrão |
| `lock:upload_lote:{usuario_id}` | Cooldown de envio | 30s |
| `idempotencia:{chave}` | Evitar repetição de eventos/mensagens | 24h por padrão |
| `whatsapp:sessao:{numero}` | Contexto de atendimento | 24h |
| `triagem:usuario:{id}:evento:{documento_id}` e Set de documentos | Snapshots recentes para reconectar SSE | 24h |
| Canal `triagem:usuario:{id}:eventos` | Pub/Sub de progresso de triagem | Transitório; snapshots permitem recuperação limitada |
| `mediflow:auditoria:recentes` (List) | Últimos eventos de telemetria | Limitada a 100 itens; sem TTL explícito |

**Persistência:** o Compose monta volume para Redis, mas não configura explicitamente política RDB/AOF. O volume sozinho não define a garantia de durabilidade dos dados; confirmar a política efetiva do container implantado.

**Normalização:** formas normais relacionais não se aplicam ao Redis. A documentação relevante é o catálogo de chaves, estrutura, TTL, dono do dado, política de recuperação e comportamento na indisponibilidade.

## Riscos e itens de acompanhamento

1. O código da fila trata indisponibilidade do Redis como reserva aceita, e as funções de enqueue retornam `None` em caso de erro. Os endpoints podem continuar respondendo `na_fila` sem que exista um job real. A API precisa validar o resultado do enqueue e reportar falha de dependência.
2. Backend não declara dependências saudáveis de PostgreSQL, Redis e Mongo no Compose; início fora de ordem pode falhar durante a inicialização.
3. O healthcheck HTTP do backend responde status estático e não informa saúde individual de Postgres, Redis ou Mongo.
4. A trilha de auditoria hoje está dividida entre PostgreSQL e Mongo. A proposta registrada é centralizar eventos/snapshots de auditoria no Mongo e manter no PostgreSQL o estado atual e a referência; essa migração ainda precisa ser planejada e aprovada.
5. Alinhar o fallback de Mongo descrito na decisão 0009 com a implementação atual e com os testes.
6. Conferir as tabelas criadas pelas migrations que não têm modelos SQLAlchemy correspondentes e marcar quais continuam em uso.

## Diagrama do PostgreSQL

O site provavelmente lembrado é [dbdiagram.io](https://dbdiagram.io/), uma ferramenta para criar diagramas de banco e importar/exportar SQL. A documentação oficial também descreve a geração de DBML a partir de bancos existentes via CLI: [atualização programática de ERD](https://docs.dbdiagram.io/best-practices/programmatic-erd-update/).

O DBML pronto para colar está em [diagrama_postgresql.dbml](diagrama_postgresql.dbml). O dbdiagram é voltado principalmente a diagramas relacionais. MongoDB não tem tabelas SQL e Redis usa chaves/estruturas como Sets, Strings, Lists, Pub/Sub e filas; para esses dois, esta documentação funciona como dicionário de dados, e um desenho de arquitetura separado é mais fiel do que inventar tabelas.

Para este projeto, exporte apenas **estrutura e constraints** (DDL), sem dados clínicos, CPFs, tokens, credenciais ou URLs de conexão, antes de usar ferramenta externa. O diagrama do PostgreSQL pode ser rascunhado a partir das migrations/DDL; validar contra uma instância real exige acesso autorizado ao banco. Os problemas atuais e as propostas para tratá-los estão em [Pendências e propostas de arquitetura de dados](ARQUITETURA_DADOS_PENDENCIAS_E_PROPOSTAS.md).
