# [0002] - Modelagem do Schema de Classificação de Documentos (SCRUM-50)

- **Data:** 2026-10-21
- **Autor(es):** @Pedro-Araujo4 (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
O pipeline de triagem clínica utilizando LangGraph (P3) e FastAPI (P4) exige uma estrutura de dados previsível e rígida para os retornos gerados pelo nó de classificação (P2). Como modelos de linguagem (LLMs) são suscetíveis a variações e alucinações, a ausência de um contrato de dados validado na entrada do backend pode quebrar a lógica de roteamento subsequente (ex: direcionar erroneamente um TEP agudo para a fila de rotina por falha de tipagem).

---

## 2. Para quê? (Objetivo e Resultados Esperados)
Garantir que a saída da classificação do documento clínico seja estruturalmente perfeita, validando automaticamente os tipos permitidos, os níveis de severidade clínica (prioridade) e os limites matemáticos do nível de confiança. O benefício direto é a prevenção de exceções não tratadas no servidor e a garantia de que o painel Streamlit receba dados limpos.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Dicionários Python padrão):** Prós: Simplicidade inicial sem dependências adicionais. Contras / Motivo do descarte: Nenhuma validação em tempo de execução, falta de auto-complete integrado para a dupla técnica, e impossibilidade de expor schemas OpenAPI de forma nativa.
- **Alternativa B (Pydantic v2):** Prós: Validação de dados robusta, coerção de tipos, fácil integração com FastAPI e geração automática de JSON Schema. Contras / Motivo da escolha: É o padrão do projeto definido na arquitetura base e garante segurança de tipo rigorosa.

### Detalhamento da Solução:
A solução utilizará `pydantic.BaseModel` e o módulo `enum` padrão do Python:
- **`tipo_documento`**: `Enum` estrito (`RECEITA`, `LAUDO`, `GUIA_TISS`, `RELATORIO_ALTA`, `ATESTADO`).
- **`nivel_prioridade`**: `Enum` estrito (`ROTINA`, `URGENTE`, `EMERGENCIA`).
- **`especialidade`**: `str` livre limitada via `Field(max_length=100)` para absorver erros menores de extração pela IA sem quebrar o parse.
- **`score_confianca_classificacao`**: `float` validado entre `0.0` e `1.0` usando `Field(ge=0.0, le=1.0)`.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/schemas/`
- **Arquivos Criados / Modificados:** `classificacao.py`
- **Banco de Dados / Infra:** Nenhuma alteração direta no banco de dados; esses dados servirão para popular os ORMs na fase de persistência.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Contrato blindado; erros de classificação pela LLM são detectados imediatamente na conversão do modelo.
- **Riscos / Trade-offs:** Uma resposta mal formatada da LLM que viole o `Enum` lançará um `ValidationError`. Isso exige que o nó LangGraph (P3) implemente um mecanismo de fallback ou retentativa automática.
- **Validação / Testes:** Serão criados testes automatizados usando `pytest` para verificar se dados inválidos (ex: prioridade "BAIXA" ou score "1.5") são corretamente bloqueados.