# [0002] - Roteamento do arquivo original por status

- **Data:** 2026-10-29
- **Autor(es):** @adilson-manuel (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Depois da triagem, o JSON do resultado vai para `processados/urgentes/`, `processados/rotina/` ou `auditoria_humana/`, mas o arquivo original continua em `recebidos/`. Assim, original e resultado ficam separados, e `recebidos/` acumula arquivos já processados (SCRUM-73).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Mover o original para a mesma pasta do JSON, de acordo com o status da triagem.
- Deixar em `recebidos/` só o que ainda não foi processado.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Baixar, enviar de novo e apagar (`get` + `put` + `delete`). São três chamadas, e uma falha no meio pode deixar uma cópia duplicada.
- **Alternativa B (Descartada):** Acrescentar a lógica no `storage.py`. Alteraria código de outro integrante.
- **Alternativa C (Escolhida):** Novo método `mover_por_status` no `ArquivosOCIRepository`, usando `rename_object` da OCI, que move o objeto numa única chamada dentro do mesmo bucket.

### Detalhamento da Solução:
- `mover_por_status(caminho_atual, is_urgente, requer_auditoria)`: a prioridade é a mesma do `salvar_triagem_json` (auditoria > urgente > rotina).
- Exemplo: `recebidos/DOC-001.pdf` → `processados/urgentes/DOC-001.pdf`.
- Retorna `{"bucket", "caminho_objeto", "status_backup"}`, no mesmo formato dos outros métodos. Em caso de falha, o `caminho_objeto` continua sendo o caminho original.
- Sem credenciais OCI, o movimento é simulado.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Arquivos Modificados:** `backend/app/repositories/arquivos_oci.py` (+1 método), `backend/tests/test_arquivos_oci.py` (+6 testes)
- **Arquivos Criados:** este ADR
- **Banco de Dados / Infra:** Nenhuma mudança. A política IAM `manage objects` já permite renomear.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Original e JSON ficam na mesma pasta; `recebidos/` funciona como fila de entrada.
- **Riscos / Trade-offs:** O método ainda não é chamado pela aplicação. A ligação no `TriagemService` (upload no início, mover no fim) precisa ser combinada com o dono do arquivo (P1/P4).
- **Pendência:** Definir com o P6 se, depois da decisão médica, o arquivo sai de `auditoria_humana/` para `processados/`.
- **Validação / Testes:** 12 testes em `test_arquivos_oci.py`, com cliente OCI falso.
