# [0024] - Falhas explícitas, dados de demonstração e provisionamento por seed

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
O sistema possui alternativas em memória para serviços externos, respostas heurísticas quando a LLM falha e dados de demonstração no frontend. Esses comportamentos podem mascarar indisponibilidade e apresentar dados que não vieram do banco. O provisionamento atual também não oferece uma troca obrigatória da senha inicial nem uma forma simples de cadastrar várias contas via seed.

## 2. Para quê? (Objetivo e Resultados Esperados)
- Propagar erros claros quando Redis, MongoDB, LLM, banco ou checkpoint requerido estiver indisponível, sem usar estado alternativo em memória.
- Remover mocks e registros de demonstração do frontend, mantendo rótulos e mensagens necessárias à interface.
- Provisionar uma lista editável de contas pelo seed, usando uma senha temporária obrigatória da env e armazenamento apenas do hash.
- Criar as contas provisionadas com perfil inicial de enfermeiro e exigir a troca da senha no primeiro acesso. O Administrador Geral pode alterar o perfil de acesso posteriormente; dados profissionais não são inventados nem preenchidos pela mudança de perfil.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Manter respostas substitutas ou dados mock quando um serviço falha; isso oculta erros e pode misturar demonstração com dados reais.
- **Alternativa B (Escolhida):** Falhar com mensagens explícitas e provisionar contas idempotentemente a partir de uma lista de emails/nome no módulo de seed, com senha temporária em configuração de ambiente.

### Detalhamento da Solução:
O seed não contém segredos versionados. A senha inicial é lida da env, validada e transformada em hash antes de persistir cada conta. Um campo persistente indica a troca obrigatória de senha. O primeiro login conduz à tela de troca; até completar a troca, a sessão não libera as páginas usuais. As contas seedadas começam como `ENFERMEIRO`; a interface de administração permite ao Administrador Geral alterar o perfil sem criar CRM, registro ou especialidade automaticamente. Os usuários e documentos fictícios e o cliente mock do frontend são removidos; textos de interface e mensagens de ausência permanecem.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/`, `backend/migrations/`, `frontend/`, `DECISIONS/`.
- **Arquivos Criados / Modificados:** Seeds e autenticação, modelos, migrations, serviços Redis/Mongo/LLM/checkpointer, cliente e configuração de demonstração do frontend, telas de login e usuários.
- **Banco de Dados / Infra:** Nova coluna persistente para exigir troca de senha; nova variável de ambiente para senha temporária das contas seedadas; Redis, MongoDB e LLM passam a ser dependências explícitas dos fluxos que os utilizam.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Indisponibilidade fica visível, o frontend não exibe registros fictícios e o bootstrap de contas não armazena senha em texto puro.
- **Riscos / Trade-offs:** Contas provisionadas compartilham a senha inicial até cada titular alterá-la; a implantação precisa configurar a env e informar esse valor aos usuários por canal apropriado. Serviços externos indisponíveis interrompem os fluxos que dependem deles.
- **Validação / Testes:** Revisar o fluxo de migrations, login e troca obrigatória, idempotência do seed, erro de dependências indisponíveis e remoção dos caminhos de demonstração. Não executar testes nesta solicitação.
