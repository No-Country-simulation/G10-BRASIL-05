# [0001] - Nó de Classificação do Documento validado por Pydantic (SCRUM-57)

- **Data:** 2026-10-29
- **Autor(es):** @otaviools (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
O nó de classificação entregue no PR do grafo (SCRUM-35) devolve rótulos livres (`"Receituario Medico"`, `"Urgente"`, `"Documento Nao Identificado"`) que não existem no contrato `ClassificacaoDocumento` (`app/schemas/classificacao.py`, ADR 0002 de @Pedro-Araujo04). A resposta da LLM também não passa por nenhuma validação: um JSON fora do formato segue adiante e pode quebrar o roteamento. O tipo `RELATORIO_ALTA` não é reconhecido. O card SCRUM-57 exige "saída validada por Pydantic; testado nos 5 tipos de documento".

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Toda classificação que sai do nó obedece ao schema `ClassificacaoDocumento` (tipo, prioridade, especialidade e score).
- Os 5 tipos do schema (`RECEITA`, `LAUDO`, `GUIA_TISS`, `RELATORIO_ALTA`, `ATESTADO`) são reconhecidos e testados.
- O nó pode ser testado sem chave de LLM e sem rede, enquanto o SCRUM-47 (chave da LLM) não é concluído.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Criar o nó do zero sobre a `develop`. Motivo do descarte: a `develop` ainda não tem o grafo, as settings nem as dependências do LangGraph, e o arquivo conflitaria com o PR do SCRUM-35.
- **Alternativa B (Escolhida):** Partir da branch do SCRUM-35 e ajustar o nó existente para validar a saída com `ClassificacaoDocumento`. Contra: o PR do SCRUM-57 só pode entrar depois do PR do SCRUM-35.

### Detalhamento da Solução:
- **Cliente LLM injetável:** `app/agent/llm.py` define `ClienteLLM` (função que recebe as mensagens e devolve o texto da resposta) e `obter_cliente_llm()`, que monta o cliente Gemini/OpenAI a partir das settings ou devolve `None` sem chave. O nó é criado por `criar_node_classificacao(cliente_llm)`; o grafo usa `node_classificacao`, criado com o cliente padrão. Os testes injetam um cliente falso.
- **Validação:** o JSON da LLM é extraído do texto (aceita blocos ```json) e validado com `ClassificacaoDocumento.model_validate`. Falha de chamada, JSON inválido ou `ValidationError` acionam o fallback.
- **Fallback heurístico:** palavras-chave (texto sem acentos) mapeadas para os enums do schema. Termos de risco iminente (`TERMOS_URGENCIA_CRITICA`) definem `EMERGENCIA`. O score do fallback é limitado a `0.70`, abaixo do `CONFIDENCE_THRESHOLD` (0.75), para que a classificação heurística sempre seja revisada.
- **Documento não identificado:** o schema não tem tipo "indefinido". Nesse caso o nó não inventa um tipo: grava `classificacao = None`, `score_confianca_classificacao = 0.10` e um erro em `erros`.
- **Prompt:** `prompts/classificacao.py` passa a pedir os valores exatos dos enums e a chave `score_confianca_classificacao`.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/agent/`
- **Arquivos Criados / Modificados:** `agent/llm.py` (novo), `agent/nodes/classificador.py`, `agent/prompts/classificacao.py`, `agent/nodes/roteador.py` (compara `RECEITA` em vez de `"Receituario Medico"`), `tests/test_no_classificacao.py` (novo), `tests/test_agent_graph.py`.
- **Banco de Dados / Infra:** Nenhuma alteração. A coluna `nivel_prioridade` passa a receber `ROTINA`/`URGENTE`/`EMERGENCIA`.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** contrato único entre classificação, roteamento e frontend; nó testável sem rede.
- **Riscos / Trade-offs:** os valores gravados mudam de `"Urgente"`/`"Rotina"` para os enums; o frontend e `schemas/triagem.py` precisam aceitar os novos valores. O fallback por palavras-chave é limitado e serve só como rede de segurança.
- **Validação / Testes:** `tests/test_no_classificacao.py` cobre os 5 tipos via LLM falsa e via fallback, resposta inválida da LLM, resposta com bloco markdown e documento não identificado.
