# [0007] - Agente Autônomo de Triagem Clínica com LangGraph Híbrido Resiliente

- **Data:** 2026-10-26
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
A triagem autônoma de documentos clínicos é o núcleo funcional do MediFlow (Hackathon ONE). Documentos hospitalares (laudos radiológicos, receituários, atestados) demandam análise semântica multimodal para extrair entidades, verificar achados críticos com risco de vida (ex.: *Tromboembolismo Pulmonar Agudo - TEP*) e calcular scores de confiança antes do roteamento.
Além disso, depender exclusivamente de chamadas externas a APIs de LLM sem mecanismo de contingência tornaria o sistema frágil a indisponibilidades de rede, esgotamento de cotas de tokens ou ausência de chaves de API locais na máquina dos avaliadores.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Implementar o fluxo completo de decisão em grafo autônomo usando **LangGraph (`StateGraph`)**.
- Garantir uma estratégia **Híbrida e Resiliente** (Plano B e Plano C):
  - **Plano B (Online):** Quando chaves de LLM (`GOOGLE_API_KEY` ou `OPENAI_API_KEY`) estiverem disponíveis, o agente utiliza modelos generativos com saídas estruturadas via Pydantic para inferência semântica refinada.
  - **Plano C (Offline / Contingência):** Caso não haja chave configurada, a API falhe ou ocorra timeout, os nós acionam imediatamente analisadores heurísticos determinísticos baseados em expressões regulares médicas e termos sentinela, sem derrubar a aplicação.
- Cobrir 100% dos requisitos dos cards técnicos:
  - `SCRUM-54`: Grafo de decisão documentado;
  - `SCRUM-55`: Estado compartilhado tipado (`GraphState`);
  - `SCRUM-56`: Ingestão e normalização de texto/PDF/imagem;
  - `SCRUM-57`: Nó de classificação documental;
  - `SCRUM-58`: Nó de extração de entidades clínicas;
  - `SCRUM-59`: Avaliação de consistência e score de confiança;
  - `SCRUM-60`: Detecção de urgência médica sentinela;
  - `SCRUM-61`: Arestas condicionais e nó de roteamento;
  - `SCRUM-62`: Regras de contingência e fallback;
  - `SCRUM-63`: Geração de notificação de alerta;
  - `SCRUM-64`: Engenharia de prompts com regras anti-alucinação.

---

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Grafo dependente exclusivamente de LLM remota.
  - *Motivo do descarte:* Se a cota expirar ou a chave faltar na máquina de quem avalia o projeto, o sistema trava.
- **Alternativa B (Escolhida):** Arquitetura em nós puros no LangGraph com execução híbrida (LLM com fallback defensivo determinístico interno por nó).
  - *Motivo da escolha:* Combina o melhor dos dois mundos: alta inteligência semântica quando conectado à nuvem e 100% de confiabilidade e previsibilidade em qualquer ambiente de teste local.

### Topologia do Grafo:
1. `node_ingestao`: Normaliza espaços, remove ruídos e padroniza entrada.
2. `node_classificacao`: Identifica `tipo_documento`, `especialidade` e `nivel_prioridade`.
3. `node_extracao`: Extrai `paciente`, `medico_solicitante`, `diagnostico_principal`, `cid_sugerido` e `exame_realizado`.
4. `node_avaliacao`: Avalia consistência, calcula `score_confianca` (0 a 1) e detecta `is_urgente`.
5. `aresta_condicional_roteamento`:
   - Se `is_urgente == True` ➔ `node_urgencia` (direciona para `Fila_Emergencia_Medica` e emite alerta);
   - Se `score_confianca < 0.75` ➔ `node_auditoria` (direciona para `Auditoria_Humana` sem alerta);
   - Se `tipo == Receituario` ➔ `node_farmacia` (direciona para `Farmacia_Hospitalar`);
   - Caso contrário ➔ `node_padrao` (direciona para `Fluxo_Padrao`).

---

## 4. Onde? (Impacto no Código e Arquitetura)
- `backend/app/agent/prompts/`: Templates de classificação e extração com diretrizes anti-alucinação.
- `backend/app/agent/nodes/`: Implementação de cada nó do LangGraph.
- `backend/app/agent/graph.py`: Montagem e compilação do `StateGraph`.
- `backend/app/services/triagem.py`: Invocação do agente LangGraph compilado no endpoint de triagem.
- `backend/tests/test_agent_graph.py`: Bateria de testes dos cenários de rotina, emergência e auditoria.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Garante robustez extrema para a apresentação final do projeto; o time pode rodar com LLM real ou demonstrar em modo resiliente sem risco de surpresas.
- **Riscos / Trade-offs:** Em fallback puramente determinístico, a capacidade de inferir documentos manuscritos muito atípicos depende de termos-chave conhecidos.
- **Validação / Testes:** Testes automatizados executados com e sem chaves configuradas cobrindo os 3 cenários do briefing.
