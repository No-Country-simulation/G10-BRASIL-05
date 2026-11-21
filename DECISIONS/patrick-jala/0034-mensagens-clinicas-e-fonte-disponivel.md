# [0034] - Mensagens clínicas e fonte disponível

- **Data:** 2026-11-21
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Validações podem expor nomes internos de campos e erros brutos do Pydantic nas mensagens de revisão. Além disso, o validador confunde arquivo original disponível com texto OCR já verificado e força a mesma mensagem para imagens e PDFs com fonte vinculada.

## 2. Para quê? (Objetivo e Resultados Esperados)
Manter mensagens de auditoria claras para médicos, ignorar campos extras da LLM sem falhar o schema e reconhecer quando o arquivo original está disponível para conferência, sem afirmar que seu OCR foi validado.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Aceitar a existência de imagem/PDF como prova de que o OCR foi conferido. A existência do arquivo não valida a transcrição.
- **Alternativa B (Escolhida):** Separar disponibilidade do original de verificação do texto; usar mensagens clínicas mapeadas e sanitizar erros de schema.

### Detalhamento da Solução:
Configurar os schemas de dados extraídos com `extra="ignore"`; mapear obrigatoriedades e inconsistências para texto clínico; aceitar prefixo CRM e formatos nacionais com validação de UF; registrar `fonte_original_disponivel` separadamente de `fonte_verificada`. Imagens e PDFs disponíveis continuam exigindo revisão visual, e a aprovação humana nessa etapa registra a conferência.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/schemas`, `backend/app/agent/nodes`.
- **Arquivos Criados / Modificados:** schemas extraídos, validadores clínicos, nó validador e testes relacionados.
- **Banco de Dados / Infra:** Sem alterações.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Menos mensagens técnicas e menos falhas por campos extras na saída da LLM.
- **Riscos / Trade-offs:** Disponibilidade do original não garante exatidão do OCR; a verificação visual continua explicitada como não realizada.
- **Validação / Testes:** 105 testes unitários relacionados a schema, formato CRM, CPF e mensagens do validador passaram; `git diff --check` sem erros.
