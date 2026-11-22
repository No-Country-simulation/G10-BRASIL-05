# [0005] - Suporte a Upload de Arquivos Clínicos (PDF e Imagens) no FastAPI

- **Data:** 2026-10-26
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Até o momento, a API de triagem clínica (`POST /triagem`) recebia apenas payloads em formato texto/JSON bruto. No entanto, no ecossistema de saúde e nos requisitos do Hackathon MediFlow, os documentos clínicos reais (laudos, receitas e atestados) chegam predominantemente em formato PDF (documentos digitais/vetoriais) ou em imagens escaneadas (PNG/JPEG) enviadas pelo pronto-socorro ou upload de pacientes. Sem um endpoint multipart com validação de tipo de arquivo e extração automática de texto, o sistema não suporta a entrada de documentos reais provenientes do Frontend Streamlit e de canais hospitalares.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Fornecer o endpoint `POST /triagem/upload` aceitando upload multipart (`file: UploadFile`).
- Validar extensões e tipos MIME permitidos (`application/pdf`, `image/png`, `image/jpeg`).
- Limitar o tamanho do arquivo a um máximo seguro (10 MB) para prevenir sobrecarga de memória e ataques de negação de serviço.
- Extrair o texto do PDF usando biblioteca leve (`pypdf`) e processar imagens através de pipeline de OCR/fallback seguro.
- Encaminhar transparentemente o texto extraído para o pipeline de triagem existente (`TriagemService.processar_triagem`), mantendo o contrato de resposta unificado (`RespostaTriagem`).
- Cumprir integralmente os critérios de aceitação do card **`SCRUM-67`**.

---

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Tesseract OCR via subprocess ou wrappers pesados no sistema operacional.
  - *Motivo do descarte:* Exige binários pesados de sistema operacional (`tesseract-ocr`, pacotes de idioma), que aumentam o tamanho da imagem Docker e podem falhar em ambientes conteinerizados sem as dependências instaladas.
- **Alternativa B (Escolhida):** Usar `pypdf` para leitura de PDFs baseados em texto e serviço de extração desacoplado com fallback defensivo para imagens/OCR.
  - *Motivo da escolha:* `pypdf` é 100% Python, leve, performático e não requer dependências de sistema externas, garantindo alta portabilidade e compatibilidade com OCI e Docker.

### Detalhamento da Solução:
1. **Novo Módulo de Extração:** Criar serviço utilitário em `backend/app/services/document_parser.py` responsável pela leitura de bytes, identificação de tipo MIME e extração de texto de PDFs e imagens.
2. **Novo Endpoint em `backend/app/controllers/triagem.py`:**
   - Rota: `POST /triagem/upload`
   - Parâmetros: `file: UploadFile = File(...)`, `canal_origem: Optional[str] = Form("Pronto_Socorro")`, `documento_id: Optional[str] = Form(None)`.
   - Validações: Tipo MIME (`application/pdf`, `image/jpeg`, `image/png`) e limite de 10 MB.
   - Orquestração: Extrai o texto clínico e chama `TriagemService(db).processar_triagem(...)`.
3. **Atualização de Dependências:** Adicionar `pypdf>=4.0.0` e `python-multipart>=0.0.9` ao `backend/requirements.txt`.
4. **Testes Automatizados:** Adicionar suíte de testes unitários para a rota de upload e o parser de documentos.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/services/`, `backend/app/controllers/`, `backend/requirements.txt`, `backend/tests/`
- **Arquivos Criados / Modificados:**
  - `backend/app/services/document_parser.py` (criado)
  - `backend/app/controllers/triagem.py` (modificado)
  - `backend/requirements.txt` (modificado)
  - `backend/tests/test_upload.py` (criado)
- **Banco de Dados / Infra:** Nenhuma migração necessária; os documentos continuarão sendo persistidos na tabela `documentos_triagem` com o `tipo_arquivo` correto (`pdf`, `imagem` ou `texto`).

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Suporte direto à ingestão de arquivos reais enviados pelo Frontend Streamlit e canais de parceiros.
- **Riscos / Trade-offs:** PDFs puramente digitalizados (fotos dentro de PDF) exigirão o nó de OCR multimodal (escopo do diferencial `SCRUM-96`). Para mitigar isso, o parser identifica a ausência de texto nativo e sinaliza adequadamente para auditoria humana ou processamento de imagem.
- **Validação / Testes:** Testes automatizados cobrindo upload de PDF com texto, rejeição de formatos não suportados, rejeição de arquivos vazios e fluxo de triagem ponta a ponta.
