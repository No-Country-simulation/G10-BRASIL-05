# [0005] - OCR de documentos escaneados com modelo multimodal (SCRUM-96)

- **Data:** 2026-11-20
- **Autor(es):** @otaviools (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Receitas manuscritas, laudos escaneados e fotos de documentos não têm texto que o pypdf consiga ler. Depois do SCRUM-56, esses arquivos chegam ao grafo como imagem (`requer_ocr = True`), mas nenhum nó lê o conteúdo: a classificação recebe texto vazio e o documento vai direto para a auditoria humana. O card SCRUM-96 pede usar o modelo multimodal diretamente na imagem, com pelo menos 2 documentos escaneados processados.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Documentos escaneados ganham texto e seguem o mesmo fluxo de classificação e extração dos documentos digitais.
- A transcrição não inventa conteúdo: trechos ilegíveis ficam marcados.
- Sem modelo configurado ou com falha, o documento continua indo para a auditoria humana, com o motivo registrado.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** OCR local com Tesseract (`pytesseract`). Motivo do descarte: exige instalar o binário do Tesseract no contêiner e lê mal letra manuscrita. O card pede modelo multimodal.
- **Alternativa B (Descartada):** Mandar a imagem para a classificação e a extração em cada chamada. Motivo do descarte: duplica o custo de envio da imagem e obriga os dois nós a lidar com imagem.
- **Alternativa C (Escolhida):** Um nó de transcrição que roda só quando `requer_ocr` é verdadeiro e devolve texto para os nós seguintes.

### Detalhamento da Solução:
- `agent/llm.py`: `ClienteVisao` e `obter_cliente_visao()`, que enviam a instrução e as imagens (data URI base64) ao Gemini ou à OpenAI via LangChain. A criação do modelo foi unificada em `_criar_modelo_chat()`.
- `agent/prompts/transcricao.py` (versão 1.0.0): transcrição literal, `[ilegível]` para trechos incertos e `SEM_TEXTO_LEGIVEL` quando nada é legível.
- `agent/nodes/transcricao.py`: `criar_node_transcricao(cliente_visao)`. Em caso de sucesso, grava `documento_texto`, `requer_ocr = False` e `transcricao = {metodo, versao_prompt}`. Sem cliente, com falha ou sem texto legível, registra o erro em `erros` e mantém o documento sem texto.
- `agent/graph.py`: aresta condicional `ingestao → transcricao → classificacao` quando `requer_ocr`; caso contrário `ingestao → classificacao`. `construir_grafo_triagem(transcricao=...)` permite injetar o nó nos testes.
- `data/samples/escaneados/`: duas amostras sintéticas (receita em PNG e laudo em PDF só com imagem), geradas por `gerar_amostras.py` com dados fictícios.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/agent/`, `data/samples/escaneados/`
- **Arquivos Criados / Modificados:** `agent/llm.py`, `agent/graph.py`, `agent/state.py`, `agent/nodes/transcricao.py` (novo), `agent/prompts/transcricao.py` (novo), `agent/prompts/CHANGELOG.md`, `tests/test_no_transcricao.py` (novo), `tests/test_prompts.py`, `data/samples/escaneados/*` (novo).
- **Banco de Dados / Infra:** Nenhuma alteração. Usa a mesma chave de LLM do SCRUM-47.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** documentos escaneados passam pelo fluxo automático; a transcrição registra o método e a versão do prompt.
- **Riscos / Trade-offs:** cada documento escaneado gera uma chamada a mais à LLM. As amostras são impressas e não manuscritas; a qualidade com letra de médico real só pode ser medida com a chave da LLM e documentos reais anonimizados.
- **Validação / Testes:** `tests/test_no_transcricao.py` cobre o desvio para OCR, transcrição, falhas e as 2 amostras escaneadas passando pelo grafo inteiro com um modelo multimodal simulado. A leitura real das amostras pelo modelo depende da chave da LLM (SCRUM-47).
