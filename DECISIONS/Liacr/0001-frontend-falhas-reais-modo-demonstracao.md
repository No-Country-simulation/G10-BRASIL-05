# [0001] - Frontend: falhas reais da API e modo demonstração explícito

- **Data:** 2026-11-05
- **Autor(es):** @Liacr (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
A revisão técnica de 04/11/2026 (SCRUM-103) mostrou que o frontend exibia sucesso sem persistência: `registrar_decisao` devolvia mensagem de sucesso após erro HTTP ou exceção, e triagem, histórico e fila recorriam a mocks em silêncio. O usuário podia acreditar que uma decisão clínica foi salva ou que um documento foi processado sem que a API tivesse feito a operação.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Timeout, indisponibilidade e respostas 4xx/5xx nunca geram sucesso na interface.
- Decisões não confirmadas pela API continuam pendentes na tela.
- Dados fictícios só existem em modo demonstração pedido de forma explícita e sinalizado na tela.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** manter o modo demonstração ativo quando `API_BASE_URL` está vazio. Esquecer a variável no uso real serviria dados fictícios sem aviso.
- **Alternativa B (Escolhida):** `MODO_DEMONSTRACAO=true` liga o mock. Sem a variável, o front usa a API real (`API_BASE_URL`, padrão `http://localhost:8000`) e qualquer falha vira erro na tela.

### Detalhamento da Solução:
1. `cliente_http` e `cliente_whatsapp` levantam `ErroDeApi` para timeout, falha de conexão, resposta inválida, 4xx/5xx e `{"sucesso": false}` com HTTP 200 (formato usado pelas rotas do WhatsApp).
2. Ações que gravam ou enviam (decisão de auditoria e WhatsApp) nunca usam mock. Em modo demonstração levantam `ErroDeApi`.
3. As páginas tratam `ErroDeApi` com `chamar_api_ou_parar`. Em falha de decisão, o documento segue na fila e a mensagem informa isso.
4. O modo demonstração é identificado no topo de todas as páginas e na barra lateral.
5. O `documento_id` ganha sufixo aleatório, pois o backend sobrescreve o registro quando o ID repete.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `frontend/` (nenhuma alteração no backend).
- **Arquivos Criados / Modificados:** `services/configuracao.py`, `services/api_client.py`, `services/cliente_http.py`, `services/cliente_whatsapp.py`, `components/erros.py`, `components/modo_de_execucao.py`, `pages/`, `utils/whatsapp.py`, `utils/requisicao.py`, `app.py`, `tests/`.
- **Infra:** nova variável `MODO_DEMONSTRACAO` no `.env` do frontend. `API_BASE_URL` vazio passa a significar `http://localhost:8000`.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** a interface só confirma o que a API confirmou. O modo demonstração é intencional e visível.
- **Riscos / Trade-offs:** em modo demonstração não é possível concluir uma decisão de auditoria nem usar o WhatsApp. Depois de timeout não há como saber se a API gravou a decisão, então a tela manda conferir a fila.
- **Validação / Testes:** testes com API simulada (`httpx.MockTransport`) cobrem timeout, indisponibilidade, 4xx/5xx, resposta inválida e sucesso, sem backend ativo. Validado também contra o backend da branch `homologacao`.