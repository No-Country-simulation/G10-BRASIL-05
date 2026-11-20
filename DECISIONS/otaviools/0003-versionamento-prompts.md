# [0003] - Versionamento e exemplos dos prompts do agente (SCRUM-64)

- **Data:** 2026-11-20
- **Autor(es):** @otaviools (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Os prompts de classificação e extração já ficam em arquivos separados (`backend/app/agent/prompts/`), mas não têm versão nem exemplos. Sem versão, não dá para saber qual texto de prompt gerou uma classificação gravada no banco, nem comparar resultados entre mudanças. Sem exemplos, a LLM tende a deduzir campos ausentes, principalmente o CID. O card SCRUM-64 pede "prompts versionados e revisados", com exemplos e instruções anti-alucinação, inclusive para CID.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Cada resposta gerada pela LLM registra a versão do prompt usado.
- Os exemplos few-shot mostram à LLM o formato exato da resposta e o caso "CID não escrito → `null`".
- Os testes impedem que um exemplo fora do schema ou uma versão sem registro no histórico entrem no código.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Prompts em arquivos `.txt`/`.yaml` carregados em tempo de execução. Motivo do descarte: adiciona leitura de arquivo e dependência (YAML) sem ganho real; os módulos Python já são versionados pelo git e permitem validar exemplos nos testes.
- **Alternativa B (Escolhida):** Constantes `VERSAO` e `EXEMPLOS` em cada módulo de prompt, com histórico em `prompts/CHANGELOG.md`.

### Detalhamento da Solução:
- `VERSAO` segue `MAIOR.MENOR.CORRECAO` (MAIOR muda o formato do JSON; MENOR muda regras ou exemplos; CORRECAO muda redação).
- `EXEMPLOS` é uma lista de pares (documento, resposta). `formatar_exemplos` anexa os pares ao prompt de sistema.
- Os nós gravam `versao_prompt` junto de `metodo` em `classificacao` e `dados_extraidos`. Quando o fallback é usado, `versao_prompt` é `None`.
- A revisão dos prompts acontece no PR, pela dupla, como qualquer código.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/agent/prompts/`, `backend/app/agent/nodes/`
- **Arquivos Criados / Modificados:** `prompts/__init__.py`, `prompts/classificacao.py`, `prompts/extracao.py`, `prompts/CHANGELOG.md` (novo), `nodes/classificador.py`, `nodes/extrator.py`, `tests/test_prompts.py` (novo).
- **Banco de Dados / Infra:** Nenhuma alteração.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** rastreabilidade de qual prompt gerou cada resultado; exemplos validados automaticamente.
- **Riscos / Trade-offs:** os exemplos aumentam o tamanho do prompt (mais tokens por chamada). A qualidade real dos prompts só pode ser medida com chave de LLM (SCRUM-47).
- **Validação / Testes:** `tests/test_prompts.py` verifica versão semântica, registro no CHANGELOG, exemplos contra os schemas, ausência de CID inventado nos exemplos e gravação de `versao_prompt` pelos nós.
