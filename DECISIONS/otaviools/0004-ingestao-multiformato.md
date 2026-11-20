# [0004] - Ingestão padronizada de texto, PDF e imagem (SCRUM-56)

- **Data:** 2026-11-20
- **Autor(es):** @otaviools (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Hoje o upload converte imagens e PDFs escaneados em um texto de marcação (`"[Documento Clínico Imagem ... Aguardando OCR]"`), e esse texto falso segue para a classificação e a extração. A imagem em si é descartada, então nenhum nó consegue lê-la. O card SCRUM-56 pede que texto, PDF e imagem cheguem ao nó seguinte "em formato padronizado", prontos para a LLM (texto direto ou arquivo multimodal).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Um único contrato (`DocumentoIngerido`) para os três formatos.
- Imagens e PDFs escaneados chegam ao grafo como imagem, prontos para um modelo de visão (SCRUM-96).
- Nenhum texto de marcação é tratado como conteúdo clínico.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Ler PDF e imagem dentro do nó de ingestão. Motivo do descarte: o AGENTS.md proíbe nós dependerem de detalhes externos; a leitura de arquivo (pypdf, Pillow) já vive em `services/document_parser.py`.
- **Alternativa B (Escolhida):** O serviço converte o arquivo no contrato `DocumentoIngerido`; o nó de ingestão valida e normaliza esse contrato dentro do estado do grafo.

### Detalhamento da Solução:
- `app/schemas/ingestao.py`: `FormatoDocumento` (`TEXTO`, `JSON`, `PDF`, `IMAGEM`), `ImagemDocumento` (`mime_type`, `dados_base64`) e `DocumentoIngerido` (`formato`, `texto`, `imagens`, `requer_ocr`).
- `DocumentParserService.preparar_documento` substitui `extrair_texto`:
  - PDF com camada de texto → `texto` com as páginas.
  - PDF escaneado → `imagens` com as imagens embutidas nas páginas (via `page.images` do pypdf).
  - Imagem → `imagens` com o próprio arquivo.
- `node_ingestao` grava no estado `tipo_arquivo`, `documento_texto`, `imagens_documento` e `requer_ocr`. Formato desconhecido vira `TEXTO`; imagem fora do contrato é descartada com erro registrado.
- `TriagemService.processar_triagem` recebe `imagens` opcionais e grava no banco o texto normalizado pelo grafo.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/schemas/`, `backend/app/services/`, `backend/app/controllers/`, `backend/app/agent/`
- **Arquivos Criados / Modificados:** `schemas/ingestao.py` (novo), `services/document_parser.py`, `services/triagem.py`, `controllers/triagem.py`, `agent/nodes/ingestao.py`, `agent/state.py`, `tests/test_no_ingestao.py` (novo).
- **Banco de Dados / Infra:** `tipo_arquivo` passa a ser gravado em maiúsculas (`PDF`, `IMAGEM`). Para imagens sem OCR, `documento_texto` fica vazio em vez do texto de marcação.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** o conteúdo visual chega intacto ao grafo; o contrato é validado por Pydantic.
- **Riscos / Trade-offs:** enquanto o OCR (SCRUM-96) não estiver ativo, imagens chegam à classificação sem texto e vão para auditoria humana. PDFs escaneados com imagens em formatos raros (JBIG2, CCITT) podem não ser extraídos pelo pypdf. As imagens trafegam em base64 no estado do grafo (até 10 MB por arquivo).
- **Validação / Testes:** `tests/test_no_ingestao.py` cobre texto, PDF com texto, PDF escaneado, PNG, JPEG, formato desconhecido, documento vazio e imagem inválida.
