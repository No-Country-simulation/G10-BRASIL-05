# [0003] - Tratamento de falhas de armazenamento e modo local

- **Data:** 2026-10-29
- **Autor(es):** @adilson-manuel (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Sem credenciais OCI, o upload só simulava ("local_simulado") e nada era guardado; a leitura dava erro. Com a OCI configurada, uma falha de rede fazia o documento se perder, e erros passageiros não eram tentados de novo (SCRUM-74).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Permitir que qualquer integrante rode e teste upload, leitura e roteamento sem conta Oracle.
- Não perder documentos quando a OCI falhar e enviá-los para a nuvem quando ela voltar.
- Tentar de novo automaticamente em erros passageiros.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Manter o modo simulado. Não guarda nada e esconde falhas.
- **Alternativa B (Descartada):** Fila de reenvio para a OCI (tarefa em segundo plano). Complexa demais para o prazo do hackathon.
- **Alternativa C (Escolhida):** Pasta local `backend/storage_local/` com a mesma estrutura do bucket, usada sem credenciais ou quando a OCI falha, mais o retry nativo do SDK (`oci.retry.DEFAULT_RETRY_STRATEGY`).

### Detalhamento da Solução:
- `status_backup` possíveis:
  - `sucesso`: gravado na OCI.
  - `sucesso (local)`: sem OCI configurada, gravado em disco.
  - `falha_oci (salvo_local)`: a OCI falhou e o arquivo foi gravado em disco.
  - `falha: ...`: não foi possível gravar.
- A leitura tenta a OCI primeiro e usa a cópia local se o objeto não estiver na nuvem.
- O movimento por status (SCRUM-73) também funciona na pasta local.
- Caminhos que tentam sair da pasta local (`../`) são bloqueados.
- `print` foi trocado por `logging`.
- Arquivos salvos por falha da OCI entram numa lista de pendentes (`storage_local/_pendentes_oci.json`). Os arquivos do modo de desenvolvimento (sem credenciais) não entram, para não subirem dados de teste.
- `sincronizar_pendentes()` envia os pendentes para a OCI no mesmo caminho e apaga a cópia local. O `caminho_objeto` salvo no banco continua válido.
- Script manual: `python scripts/sincronizar_oci.py`, executado de dentro de `backend/`.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Arquivos Modificados:** `backend/app/repositories/arquivos_oci.py`, `backend/tests/test_arquivos_oci.py`, `.gitignore` (+ `storage_local/`)
- **Arquivos Criados:** este ADR, `backend/scripts/sincronizar_oci.py`
- **Banco de Dados / Infra:** Nenhuma mudança na OCI.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Desenvolvimento sem credenciais; nenhum documento perdido por falha de rede.
- **Riscos / Trade-offs:** A sincronização é manual (script). Rodar no startup da API exige alterar o `main.py` (outro integrante): combinar com o autor. A lista de pendentes não é segura para vários processos gravando ao mesmo tempo, o que basta para o hackathon (um único servidor).
- **Pendência:** O `salvar_triagem_json` do `storage.py` (P1) continua só simulando sem OCI e perde o JSON em caso de falha. Combinar com o autor se ele quer usar o mesmo modo local.
- **Mudança de comportamento:** o status `sucesso (local_simulado)` virou `sucesso (local)`, e a leitura sem OCI não gera mais `RuntimeError`.
- **Validação / Testes:** 26 testes em `test_arquivos_oci.py` (modo local, OCI fora do ar, retry, caminho bloqueado, pendentes e sincronização). Testado no bucket real: queda simulada → arquivo local → sincronização → arquivo no bucket.
