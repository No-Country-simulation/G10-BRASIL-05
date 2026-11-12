# [0004] - Monitorar uso dentro do Always Free

- **Data:** 2026-11-11
- **Autor(es):** @adilson-manuel (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
O projeto usa só recursos gratuitos da OCI. Sem acompanhamento, um erro (script em loop, arquivos de teste acumulados, recurso pago criado por engano) pode gerar custo ou bloquear o uso (SCRUM-75).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Ser avisado na hora se algo começar a custar dinheiro.
- Saber rapidamente quanto do limite gratuito do bucket (20 GB) está em uso.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Métricas e alarmes do OCI Monitoring. Mais completo, mas mais configuração do que o hackathon precisa.
- **Alternativa B (Escolhida):** Budget de custo na console, com alerta por email, mais o script `backend/scripts/uso_oci.py`, que mostra o tamanho e o número de objetos do bucket.

### Detalhamento da Solução:
- **Budget (console):** Billing & Cost Management → Budgets. Valor US$ 1, alerta por email a partir de 1%.
- **Script:** `get_bucket` com `approximateSize` e `approximateCount` (permitido pela regra `read buckets`). Avisa a partir de 80% do limite. Retorna o código 1 nesse caso, para poder ser usado em automação.
- Usa a autenticação do `StorageRepository`, sem alterá-lo.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Arquivos Modificados:** nenhum
- **Arquivos Criados:** `backend/scripts/uso_oci.py`, `backend/tests/test_uso_oci.py`, este ADR
- **Banco de Dados / Infra:** Budget na console OCI.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Custo zero garantido por alerta; verificação de uso em um comando.
- **Riscos / Trade-offs:** O tamanho do bucket é aproximado (atualizado pela Oracle de tempos em tempos). O limite de pedidos à API por mês não é medido pelo script: acompanhar pela console, se necessário.
- **Validação / Testes:** 4 testes em `test_uso_oci.py`; executado no bucket real.
