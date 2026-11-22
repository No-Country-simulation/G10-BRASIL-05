# [0027] - Banco de dados isolado para Evolution API

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
A Evolution API está apontada para o mesmo banco PostgreSQL e schema público do MediFlow. Ao iniciar, Prisma tenta aplicar seu histórico de migrations sobre um schema já preenchido pelo MediFlow e encerra com P3005, deixando o container indisponível.

## 2. Para quê? (Objetivo e Resultados Esperados)
Permitir que a Evolution mantenha suas instâncias e dados operacionais sem interferir nas tabelas ou migrations do MediFlow, sem apagar o volume PostgreSQL existente nem criar um segundo servidor PostgreSQL.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Apagar o schema ou baselinear as migrations da Evolution no banco atual; pode danificar dados e misturar o ciclo de migrations de dois sistemas.
- **Alternativa B (Escolhida):** Criar um banco PostgreSQL separado para a Evolution no mesmo servidor, por meio de um serviço de inicialização idempotente; apontar Prisma para esse banco e aguardar sua criação antes de iniciar a API.
- **Alternativa C (Descartada):** Criar um segundo container PostgreSQL; adiciona outro servidor e volume, embora apenas um banco lógico separado seja necessário para este ambiente local.

### Detalhamento da Solução:
O Compose cria o banco `evolution` caso ainda não exista. A Evolution usa uma URL de conexão própria apontando para esse banco e depende da conclusão do serviço de inicialização. O banco `DB_NAME` do MediFlow permanece intacto.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `docker-compose.yml`, `.env.example`, `DOCUMENTOS/`, `DECISIONS/`.
- **Arquivos Criados / Modificados:** Serviço Compose de criação do banco, conexão da Evolution, guia de configuração e esta ADR.
- **Banco de Dados / Infra:** Novo banco lógico `evolution` no Postgres já existente; sem remoção ou migração das tabelas do MediFlow.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Ciclos de migrations isolados e os dados existentes do MediFlow preservados.
- **Riscos / Trade-offs:** MediFlow e Evolution continuam compartilhando a capacidade e o ciclo de vida do mesmo servidor PostgreSQL.
- **Validação / Testes:** Conferir sintaxe do Compose e dependências; não iniciar/reiniciar containers nem executar testes nesta solicitação.
