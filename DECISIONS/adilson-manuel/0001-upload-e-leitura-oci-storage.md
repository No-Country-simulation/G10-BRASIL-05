# [0001] - Upload e leitura de arquivos no OCI Object Storage

- **Data:** 2026-10-27
- **Autor(es):** @adilson-manuel (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
O `StorageRepository` só salvava o JSON da triagem. O documento original enviado pelo usuário (PDF, imagem, texto) não era guardado, e não havia como ler de volta os objetos do bucket para exibir na interface ou na auditoria humana (SCRUM-72).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Guardar o arquivo original em `recebidos/`, mantendo rastreabilidade do documento recebido.
- Permitir que serviços leiam arquivos e JSONs do bucket (histórico, auditoria, UI).

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Criar um novo repositório `oci_storage.py`, como citado no plano. Duplicaria o `storage.py` já usado pelo `TriagemService`.
- **Alternativa B (Descartada):** Acrescentar os métodos dentro do `storage.py`. Alteraria código de outro integrante.
- **Alternativa C (Escolhida):** Novo arquivo `arquivos_oci.py` com a classe `ArquivosOCIRepository`, que herda do `StorageRepository` e reaproveita a autenticação sem modificá-lo.

### Detalhamento da Solução:
- `salvar_arquivo_original(documento_id, conteudo, nome_arquivo, content_type)` → grava em `recebidos/{documento_id}{extensao}`.
- `ler_arquivo(caminho_objeto)` → retorna os bytes do objeto; `FileNotFoundError` se não existir.
- `ler_triagem_json(caminho_objeto)` → retorna o JSON como dicionário.
- O `storage.py` não foi alterado.
- Sem credenciais OCI, o upload continua simulado e a leitura gera `RuntimeError` claro. A persistência local real fica para o SCRUM-74.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Arquivos Modificados:** nenhum
- **Arquivos Criados:** `backend/app/repositories/arquivos_oci.py`, `backend/tests/test_arquivos_oci.py`
- **Banco de Dados / Infra:** Nenhuma mudança. Usa as variáveis `OCI_*` já existentes no `.env`.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Documento original preservado; leitura disponível para outras camadas.
- **Riscos / Trade-offs:** Leitura indisponível sem OCI até o SCRUM-74.
- **Validação / Testes:** 6 testes em `test_arquivos_oci.py` com cliente OCI falso (sem acesso à nuvem).
