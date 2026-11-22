# [0031] - Ajustes de extração e validação clínica

- **Data:** 2026-11-21
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
Documentos laboratoriais podem trazer CPF do paciente com pontuação variável no OCR, CRM numérico sem UF, resultados comparados a referências e nenhum diagnóstico/CID explícito. O fluxo precisa padronizar CPF como 11 dígitos entre LLM, evidência, schema e persistência para não descartá-lo por pontuação. A validação também não deve reprovar CRM legível apenas por não conter UF nem tratar diagnóstico ausente como inconsistência geral.

## 2. Para quê? (Objetivo e Resultados Esperados)
Persistir e exibir CPF como 11 dígitos, tolerar diferenças de pontuação entre CPF e OCR, reduzir falsos alertas e apresentar achados laboratoriais objetivos sem inventar doenças ou CID.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Exigir diagnóstico e CRM com UF para todo documento. Isso mantém falsos positivos em laudos.
- **Alternativa B (Escolhida):** Aceitar CRM numérico sem UF como registro extraído, exigir diagnóstico somente onde o tipo documental exige, orientar extração a descrever resultados fora da referência sem inferir doença, e manter CID apenas quando escrito no documento.

### Detalhamento da Solução:
Ajustar validador CRM e avaliação por tipo documental; normalizar CPF na identificação e extração, localizar sua evidência por sequência de dígitos e salvar apenas dígitos; instruir prompt de extração a comparar resultado com a referência do próprio documento; manter CID apenas quando escrito no documento.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/agent`, `backend/app/schemas`, `backend/app/repositories`, `backend/app/models`.
- **Arquivos Criados / Modificados:** identificador, extrator, normalização de texto, validador, schema de dados extraídos e repositório de pacientes.
- **Banco de Dados / Infra:** Sem alterações.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** CPF permanece consistente mesmo com variação de pontuação no OCR; menos auditorias por formato de CRM e diagnóstico ausente em laudos.
- **Riscos / Trade-offs:** CRM sem UF tem validação apenas sintática, não confirma existência ou estado de registro; achados dependem das referências transcritas no laudo.
- **Validação / Testes:** Testes unitários do pipeline de CPF, validação clínica e auditoria.
