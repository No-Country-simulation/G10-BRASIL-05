# [0006] - Script de teste da chave da LLM (SCRUM-47)

- **Data:** 2026-11-20
- **Autor(es):** @otaviools (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Os nós de classificação, extração e transcrição só usam a LLM quando há chave configurada; sem ela, tudo cai no fallback heurístico. Não existe hoje uma forma rápida de confirmar que a chave funciona e que o modelo escolhido aceita imagem e PDF escaneado. O card SCRUM-47 pede gerar a chave e testar chamadas de texto e de PDF/imagem, com um script que retorne a resposta do modelo.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Qualquer pessoa do time confirma, com um comando, se a chave e o modelo estão funcionando.
- O teste usa o mesmo adaptador (`app/agent/llm.py`) que o grafo, então valida o caminho real de produção.
- O modelo pode ser trocado sem mudar código, caso o modelo padrão seja descontinuado.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Script chamando a API do Gemini direto (`google-generativeai`). Motivo do descarte: adicionaria outra dependência e testaria um caminho diferente do usado pelo grafo.
- **Alternativa B (Escolhida):** Script que usa `obter_cliente_llm()` e `obter_cliente_visao()`.

### Detalhamento da Solução:
- `backend/scripts/testar_llm.py` faz três chamadas: texto ("responda OK"), visão na `receita_escaneada.png` e visão no `laudo_escaneado.pdf` (amostras do SCRUM-96). Imprime cada resposta, um resumo e sai com código 0 só se as três responderem.
- Sem chave, orienta a configurar o `.env` e sai com código 1. O script mostra o provedor e o modelo, nunca a chave.
- Nova variável opcional `LLM_MODEL` em `settings` e no `.env.example`; vazia, usa o padrão do provedor (`gemini-1.5-flash` ou `gpt-4o-mini`).
- A geração da chave é feita por um integrante do time no console do provedor (Google AI Studio) e fica só no `.env` local.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/scripts/`, `backend/app/agent/`, `backend/app/config/`
- **Arquivos Criados / Modificados:** `scripts/testar_llm.py` (novo), `agent/llm.py`, `config/settings.py`, `backend/.env.example`, `tests/test_script_testar_llm.py` (novo).
- **Banco de Dados / Infra:** nova variável de ambiente opcional `LLM_MODEL`.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** diagnóstico rápido da integração com a LLM; troca de modelo por variável de ambiente.
- **Riscos / Trade-offs:** cada execução consome cota do provedor (3 chamadas). O modelo padrão `gemini-1.5-flash` pode estar descontinuado; nesse caso, definir `LLM_MODEL` com um modelo atual.
- **Validação / Testes:** `tests/test_script_testar_llm.py` cobre ausência de chave, sucesso das três chamadas, falha em uma chamada e resposta vazia, com clientes simulados. O CA "script retorna resposta do modelo" só é confirmado rodando o script com uma chave real.
