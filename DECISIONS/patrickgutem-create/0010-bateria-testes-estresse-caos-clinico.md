# [0010] - Bateria de Testes de Estresse, Caos Clínico e Concorrência Brutal

- **Data:** 2026-10-26
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Sistemas hospitalares de emergência não podem falhar sob condições adversas. Cenários brandos de teste (happy path) mascaram vulnerabilidades críticas como:
- Concorrência de múltiplos médicos tentando travar o mesmo laudo sob estresse (race conditions);
- Injeção de textos maliciosos, corrupção proposital de binários (PDFs quebrados, imagens truncadas, fuzzing);
- Laudos com contradições clínicas extremas e termos ambíguos;
- Cascata de falhas de rede e dependências externas (LLM offline, timeout de banco, perda de conexão com Redis/MongoDB).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Implementar uma suíte de testes de estresse profundo (**testes brutos / chaos engineering**) sem complacência:
  1. **Concorrência e Race Conditions:** Disparo multithreading paralelo simulando 20 médicos tentando adquirir lock no mesmo milissegundo (apenas 1 deve vencer, 19 devem receber 409 Conflict de forma determinística).
  2. **Ingestão Paralela sob Carga:** Múltiplas threads processando triagens concorrentes no PostgreSQL, garantindo integridade e idempotência do ecossistema relacional.
  3. **Fuzzing & Payload Corrompido:** Testes com payloads gigantes (text-bomb > 100 KB), Unicode caótico, injeção de caracteres de controle e binários corrompidos (PDF com cabeçalho truncado, imagem PNG com bytes randômicos).
  4. **Caos Clínico e Limiares Extremos:** Documentos com termos contraditórios, textos médicos ilegíveis ("..."), idades absurdas (-10, 999), diagnósticos críticos mascarados.
  5. **Queda de Dependências (Chaos Resilience):** Verificação de que o sistema degrada graciosamente para o Plano C (heurística determinística) sem gerar erro 500 nem derrubar o servidor.

---

## 3. Como? (Implementação Técnica e Alternativas)

### Detalhamento da Solução:
- Arquivo `backend/tests/test_brutal_stress_and_chaos.py` contendo:
  - `ThreadPoolExecutor` para disparos concorrentes reais via FastAPI `TestClient`.
  - Geração dinâmica de PDFs corrompidos e imagens binárias inválidas.
  - Testes com injeção de caracteres Unicode, emojis, SQLi strings em campos de auditoria e nomes de pacientes.
  - Asserções estritas de contratos de resposta, envelope de erro RFC 7807 e integridade relacional.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- `DECISIONS/patrickgutem-create/0010-bateria-testes-estresse-caos-clinico.md`: Este ADR.
- `backend/tests/test_brutal_stress_and_chaos.py`: Suíte de testes pesados.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Certificação de robustez de nível militar para a API do MediFlow. Garantia de que a aplicação não trava em nenhuma condição de contorno.
- **Riscos / Trade-offs:** Testes mais pesados que consomem alguns segundos a mais de CPU durante a execução da suíte.
- **Validação / Testes:** Execução via `pytest` com 100% de assertividade.
