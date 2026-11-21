# [0032] - Stream SSE autenticado por cookie para eventos da triagem

- **Data:** 2026-11-21
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
O acompanhamento da triagem precisa receber atualizações emitidas pelo backend sem depender de consultas repetidas. O `EventSource` nativo do navegador não permite configurar o header `Authorization`, enquanto a aplicação já mantém o JWT em cookie para restaurar a sessão.

## 2. Para quê? (Objetivo e Resultados Esperados)
Disponibilizar um stream SSE autenticado para os eventos de triagem, aproveitando o cookie existente e preservando a autenticação Bearer usada pelas demais rotas.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Migrar todas as rotas para autenticação por cookie. Isso ampliaria o escopo e exigiria ajustes de proteção CSRF nas operações mutáveis.
- **Alternativa B (Escolhida):** Manter Bearer como padrão e aceitar o cookie de sessão somente como alternativa de autenticação para o endpoint SSE. O stream fica limitado ao usuário autenticado; eventos são publicados no Redis por usuário e a reconexão consulta o estado atual dos trabalhos.

### Detalhamento da Solução:
Após o login, um componente do navegador troca o Bearer recebido pelo Streamlit por um cookie `HttpOnly`, `SameSite=Lax` e `Secure` em produção. O endpoint SSE valida esse cookie pelo mesmo validador das credenciais Bearer; as demais rotas continuam aceitando Bearer. O logout remove o cookie no backend. Trabalhadores publicam mudanças de estado no canal Redis do usuário; o SSE envia eventos com IDs, heartbeat e snapshot inicial, sem transmitir documento clínico completo.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/services`, `backend/app/controllers`, `backend/app/api`, `frontend/components`, `frontend/telas/analise`.
- **Arquivos Criados / Modificados:** serviço de eventos SSE, autenticação, login, rotas, fila/worker, componente SSE e tela de análise.
- **Banco de Dados / Infra:** Reutiliza Redis existente; não exige migração de banco nem nova dependência.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Atualizações ao vivo, reutilização do Redis e autenticação sem token na URL.
- **Riscos / Trade-offs:** Redis Pub/Sub não retém eventos; snapshot de estado na conexão/reconexão mitiga lacunas, mas não fornece histórico integral de cada evento. O token ainda transita pelo componente de autenticação no navegador para que a API emita o cookie; ele deixa de ser persistido como cookie legível por JavaScript.
- **Validação / Testes:** Testes de autenticação Bearer/cookie, autorização do stream, publicação e formatação dos eventos, mais validação manual de conexão, reconexão e término.
