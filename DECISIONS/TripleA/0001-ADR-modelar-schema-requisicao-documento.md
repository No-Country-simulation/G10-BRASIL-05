# [0001] - Modelagem do Schema RequisicaoDocumento

- **Data:** 2026-10-21
- **Autor(es):** @TripleA (via Assistente IA)
- **Status:** Aceito

---

## 1. Por quê? (Contexto e Motivação)

A aplicação precisa definir um contrato de entrada para requisições relacionadas a documentos. Sem uma validação estruturada, dados ausentes ou inválidos podem chegar às próximas etapas do sistema, dificultando o tratamento de erros e a manutenção.

O briefing da tarefa estabelece quatro campos obrigatórios: `documento_id`, `tipo_arquivo`, `documento_texto` e `canal_origem`.

## 2. Para quê? (Objetivo e Resultados Esperados)

Criar o schema `RequisicaoDocumento` utilizando Pydantic para validar os dados recebidos conforme o briefing.

Resultados esperados:
- Validar a presença e o conteúdo dos campos obrigatórios.
- Aceitar somente `PDF`, `IMAGEM`, `TEXTO` e `JSON` em `tipo_arquivo`.
- Rejeitar strings vazias ou compostas apenas por espaços nos campos textuais.
- Rejeitar campos adicionais não definidos no contrato.
- Garantir a validação por meio de testes automatizados.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas

- **Alternativa A (Descartada):** Validar os dados manualmente com condicionais espalhadas pela aplicação. Essa abordagem pode duplicar regras e dificultar a manutenção.
- **Alternativa B (Escolhida):** Centralizar as regras em um modelo Pydantic, utilizando os recursos de validação da biblioteca e testes automatizados.

### Detalhamento da Solução

Criar o modelo `RequisicaoDocumento` com os seguintes campos:

- `documento_id`: string obrigatória, não vazia e sem restrição específica de formato.
- `tipo_arquivo`: valor restrito a `PDF`, `IMAGEM`, `TEXTO` ou `JSON`.
- `documento_texto`: string obrigatória e não vazia. Seu conteúdo será tratado como texto, sem interpretar ou validar a estrutura interna de JSON nesta tarefa.
- `canal_origem`: string obrigatória e não vazia, sem lista fixa de valores permitidos.

O modelo deverá rejeitar campos extras e seguir a versão e as convenções de Pydantic adotadas pelo projeto, após sua confirmação.

O escopo limita-se ao schema e aos testes, sem criação de endpoints, persistência em banco ou processamento de arquivos.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/schemas/` e `backend/tests/`.
- **Arquivos Criados / Modificados:**
  - `backend/app/schemas/requisicao_documento.py`
  - `backend/tests/test_requisicao_documento.py`
  - `DECISIONS/TripleA/0001-ADR-modelar-schema-requisicao-documento.md`
- **Banco de Dados / Infra:** Nenhuma alteração prevista.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Contrato de entrada centralizado, validações consistentes e maior facilidade para detectar dados inválidos.
- **Riscos / Trade-offs:** O contrato rejeitará campos extras e valores fora da enumeração definida. A validação de `JSON` limita-se ao valor permitido em `tipo_arquivo`; o conteúdo não será analisado como JSON.
- **Validação / Testes:** 27 testes automatizados aprovados. Os cenários cobrem payload válido, tipos de arquivo permitidos e inválidos, campos obrigatórios, strings vazias, campos extras, canal de origem sem lista predefinida, identificador sem formato fixo e conteúdo textual não interpretado como JSON.
