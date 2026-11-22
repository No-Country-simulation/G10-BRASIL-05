# [0019] - Seeds pequenos e inicialização segura do banco

- **Data:** 2026-11-19
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

`database.py` mistura conexão, migrações, reparos defensivos, dados de demonstração e persistência do domínio. As rotinas de seed escondem falhas, e não há um bootstrap inicial confiável para o administrador. O serviço de autenticação também está incompleto e incompatível com o formato de hash da migração. Isso impede o login normal e torna o bootstrap pouco confiável.

## 2. Para quê? (Objetivo e Resultados Esperados)

Manter o módulo de banco focado em engine, sessão, dependência e inicialização; dividir seeds por domínio; criar o primeiro `ADMIN_GERAL` automaticamente com credenciais de ambiente sem redefini-las em reinícios; e completar o login por senha e JWT. A limpeza de storage deve se limitar a duplicação demonstrável, mantendo rollback e erros úteis.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Deixar o seed, a migração e o bootstrap de contas concentrados em `database.py`; isso mantém responsabilidades e tratamento silencioso de erro misturados.
- **Alternativa B (Escolhida):** Separar seeds em módulos pequenos por domínio, deixar `database.py` orquestrar migrações e seeds, e compartilhar um formato PBKDF2 com salt aleatório entre login e provisionamento. O primeiro administrador usa email e senha de configuração externa e só é criado se ainda não houver administrador.

### Detalhamento da Solução:

Migration é responsável pelo schema e seed idempotente pelos dados. Senha é derivada com PBKDF2-HMAC-SHA256, salt aleatório persistido e comparação constante. Login normaliza email, exige conta ativa e emite o JWT já adotado pelo backend. Não haverá autoinscrição nem credencial literal no código. O erro de storage permanece se necessário aos adaptadores e ao controller; apenas duplicação comprovada será extraída ou removida.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/repositories/`, `backend/app/seeders/`, `backend/app/services/`, `backend/app/controllers/`, `backend/app/commands/`, `backend/tests/`.
- **Arquivos Criados / Modificados:** Inicialização e repositório do banco, migração legada de colunas, módulos de seed, serviço de autenticação e testes relacionados. Não havia arquivo de comando manual de provisionamento no workspace.
- **Banco de Dados / Infra:** A migration Alembic versiona as colunas relacionais que antes eram reparadas por SQL dentro da inicialização. O container/ambiente fornece credenciais iniciais do admin.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Inicialização legível, bootstrap repetível e login funcional sem senha padrão embutida.
- **Riscos / Trade-offs:** Uma instalação nova exige credenciais de bootstrap; a sessão existente deve continuar sendo preservada quando um administrador já está cadastrado.
- **Validação / Testes:** Testes focados cobrem idempotência do seed, hash/login válido e inválido, cadastro e persistência de storage afetada.
