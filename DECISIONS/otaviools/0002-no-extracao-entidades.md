# [0002] - Nó de Extração de Entidades Clínicas sem dados inventados (SCRUM-58)

- **Data:** 2026-11-20
- **Autor(es):** @otaviools (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
O nó de extração do PR do grafo (SCRUM-35) preenche campos ausentes com valores fictícios: `"Paciente Identificado"`, idade `45`, CRM `"145892-SP"`. O fallback por regex deduz o CID a partir de palavras do texto (ex.: "losartana" vira `I10`), e o `TriagemService` repete os mesmos valores fictícios (`"Z00.0"`, `"Avaliação Clínica"`). O card SCRUM-58 exige: "extração sem inventar dados; campos ausentes ficam nulos". A saída também não usa o schema `DadosExtraidos` da `develop` (ADR 0003 de @Pedro-Araujo04), que tem `crm_uf` e `medicamentos`.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Toda extração sai validada por `DadosExtraidos`.
- Campo que não está escrito no documento fica `null` (ou lista vazia, para medicamentos), tanto na LLM quanto no fallback e no serviço.
- O validador clínico (SCRUM-53) e a auditoria humana passam a ver as lacunas reais do documento.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Confiar só no prompt para a LLM não inventar dados. Motivo do descarte: LLMs ainda alucinam nomes e códigos; o CA exige garantia.
- **Alternativa B (Escolhida):** Prompt anti-alucinação + validação Pydantic + verificação de evidência no texto.

### Detalhamento da Solução:
- Mesmo padrão do nó de classificação (ADR 0001): `criar_node_extracao(cliente_llm)` com cliente injetável e fallback por regex.
- **Verificação de evidência:** depois de validar a resposta da LLM, nome do paciente, nome do médico, CID e nomes de medicamentos só são mantidos se aparecerem no texto (comparação sem acentos e sem diferenciar maiúsculas). O número do CRM precisa aparecer no texto. Valores sem evidência viram `null`. Exame e diagnóstico não passam por essa verificação, porque a LLM pode resumi-los.
- **Fallback por regex:** extrai só campos rotulados (`Paciente:`, `Dr./Dra.`, `CRM`, `CID:`, `Diagnóstico:`/`Conclusão:`, `Exame:`/`Laudo de`) e pares medicamento + dosagem (`Losartana 50mg`). O CID só é preenchido quando está escrito; CRM sem UF fica `null`.
- `app/agent/texto.py` concentra `normalizar` e `extrair_json`, usados pelos dois nós.
- O estado do grafo passa a usar `crm_uf` (antes `crm`) e ganha `medicamentos`.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/agent/`, `backend/app/services/`
- **Arquivos Criados / Modificados:** `agent/texto.py` (novo), `agent/nodes/extrator.py`, `agent/nodes/classificador.py`, `agent/nodes/avaliador.py`, `agent/prompts/extracao.py`, `agent/state.py`, `services/triagem.py`, `tests/test_no_extracao.py` (novo), `tests/test_agent_graph.py`.
- **Banco de Dados / Infra:** Nenhuma alteração. Campos de extração podem ser gravados como `NULL`.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** nenhum dado clínico fictício chega ao banco, ao OCI ou ao painel.
- **Riscos / Trade-offs:** documentos incompletos passam a mostrar campos vazios no frontend, que precisa tratar `null`. Mais documentos irão para auditoria humana. A verificação de evidência pode descartar um nome correto se a LLM corrigir a grafia do documento.
- **Validação / Testes:** `tests/test_no_extracao.py` cobre extração via LLM falsa, descarte de valores inventados, resposta fora do schema, falha na chamada, fallback por regex, CID não deduzido, CRM sem UF e documento sem dados.
