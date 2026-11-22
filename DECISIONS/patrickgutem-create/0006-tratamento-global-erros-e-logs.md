# [0006] - Tratamento Global de Erros e Logging Estruturado (LGPD)

- **Data:** 2026-10-26
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Em aplicações hospitalares e de triagem clínica, o tratamento de erros e a emissão de logs são pontos críticos de segurança, conformidade e governança. Sem handlers globais padronizados, erros internos (500) ou falhas de validação (422) podem vazar rastros de pilha (*stack traces*), segredos de infraestrutura ou consultas SQL sensíveis diretamente para os clientes HTTP. Além disso, logs não estruturados em texto livre dificultam a indexação no OCI Logging/CloudWatch e aumentam o risco de violação da LGPD (Lei Geral de Proteção de Dados) ao registrar inadvertidamente dados sensíveis de pacientes (CPF, prontuário, diagnósticos).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Padronizar 100% das respostas de erro da API sob um contrato JSON previsível e consistente:
  `{"erro": {"codigo": "...", "mensagem": "...", "detalhes": [...], "timestamp": "...", "path": "..."}}`.
- Interceptar as 4 categorias de erros fundamentais:
  1. `RequestValidationError` (422) da biblioteca Pydantic, com detalhamento amigável dos campos faltantes ou inválidos.
  2. `HTTPException` (4xx customizados), preservando status codes corretos.
  3. `SQLAlchemyError` (503 Service Unavailable), mascarando queries de banco e retornando aviso seguro de indisponibilidade.
  4. `Exception` genérica (500 Internal Server Error), protegendo o cliente contra vazamento de stack trace enquanto o erro completo é logado internamente.
- Implementar logging estruturado em formato JSON (stdout/console) usando exclusivamente a biblioteca padrão do Python (`logging`), compatível com contêineres Docker e OCI Logging.
- Garantir a conformidade com a LGPD: permitir inspeção completa de payloads em ambiente de desenvolvimento (`APP_ENV=development`) e mascarar dados sensíveis de pacientes em produção (`APP_ENV=production`).
- Atender com excelência a todos os critérios de aceitação do card **`SCRUM-69`**.

---

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Dependência externa pesada (`loguru`, `structlog`).
  - *Motivo do descarte:* Introduz dependências externas desnecessárias, contrariando o princípio de manter o projeto com dependências enxutas e de fácil manutenção em imagens Docker Always Free.
- **Alternativa B (Escolhida):** Usar o módulo padrão `logging` com formatador JSON nativo (`logging.Formatter`) e interceptação de erros via decoradores de exceção do FastAPI (`@app.exception_handler`).
  - *Motivo da escolha:* Alto desempenho, sem dependências externas, compatível com o ecossistema Uvicorn/Docker e plenamente auditável.

### Detalhamento da Solução:
1. **Módulo de Logging (`backend/app/config/logger.py`):**
   - Criação da classe `JSONLogFormatter` que serializa registros de log em JSON com campos: `timestamp`, `level`, `logger`, `message`, `module`, `function`, e metadados adicionais.
   - Função utilitária de sanitização LGPD que ofusca padrões de CPF (`\d{3}\.\d{3}\.\d{3}-\d{2}` ou 11 dígitos) e nomes de pacientes quando `APP_ENV != "development"`.
2. **Módulo de Handlers Globais (`backend/app/config/error_handlers.py`):**
   - Função `register_error_handlers(app: FastAPI)` que adiciona os 4 interceptadores:
     - `validation_exception_handler` (422)
     - `http_exception_handler` (4xx)
     - `database_exception_handler` (503)
     - `global_exception_handler` (500)
3. **Integração no `backend/app/main.py`:**
   - Chamada a `setup_logging()` e `register_error_handlers(app)`.
4. **Testes Automatizados:**
   - Criação de `backend/tests/test_errors_and_logs.py` validando os códigos de erro, formato JSON do envelope e emissão correta de logs.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/config/`, `backend/app/main.py`, `backend/tests/`
- **Arquivos Criados / Modificados:**
  - `backend/app/config/logger.py` (criado)
  - `backend/app/config/error_handlers.py` (criado)
  - `backend/app/main.py` (modificado)
  - `backend/tests/test_errors_and_logs.py` (criado)

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Segurança total contra vazamento de dados de infraestrutura, padronização para o Frontend Streamlit consumir erros com clareza e conformidade com a LGPD.
- **Riscos / Trade-offs:** Em produção, logs de stack trace ficam restritos aos logs do servidor e nunca chegam à resposta HTTP, exigindo acesso aos logs de contêiner para debugar exceções 500.
- **Validação / Testes:** Testes automatizados simulando erros de schema (422), 404, falhas de banco e exceções inesperadas (500).
