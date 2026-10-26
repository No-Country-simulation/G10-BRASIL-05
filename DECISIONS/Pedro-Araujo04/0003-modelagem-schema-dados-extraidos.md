# [0003] - Modelagem do Schema de Dados Extraídos (SCRUM-51)

- **Data:** 2026-10-26
- **Autor(es):** @Pedro-Araujo04 (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

O fluxo de extração clínica precisa de um contrato estruturado e validado para representar os dados obtidos de documentos. Como cada documento pode omitir informações diferentes, exigir todos os campos impediria a validação de extrações parcialmente completas.

## 2. Para quê? (Objetivo e Resultados Esperados)

Criar o schema `DadosExtraidos` para representar paciente, médico solicitante, exame, diagnóstico, CID sugerido e medicamentos com dosagens, aceitando campos ausentes quando o documento não trouxer a informação.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas

- **Alternativa A (Descartada):** Um único modelo plano com campos textuais para todas as informações. Isso não representa com clareza os subcampos do médico nem permite estruturar vários medicamentos.
- **Alternativa B (Escolhida):** Modelos Pydantic v2 compostos, com médico e medicamento/dosagem como modelos próprios e lista para medicamentos. Campos simples e subcampos serão opcionais; a lista de medicamentos usará lista vazia quando ausente.

### Detalhamento da Solução

- `DadosExtraidos`: `paciente`, `exame_realizado`, `diagnostico_principal` e `cid_sugerido` como texto opcional.
- `medico_solicitante`: objeto opcional com `nome` e `crm_uf` opcionais.
- `medicamentos`: lista vazia por padrão de itens com `medicamento` e `dosagem` opcionais.
- Os modelos rejeitarão campos extras, alinhados ao contrato de entrada existente.
- O schema não fará validação clínica ou validação de formato do CRM/CID; isso permanece fora do escopo deste card.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/schemas/` e `backend/tests/`.
- **Arquivos Criados / Modificados:** `backend/app/schemas/dados_extraidos.py`, `backend/tests/test_dados_extraidos.py`.
- **Banco de Dados / Infra:** Nenhuma alteração.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Contrato de extração explícito, composto e capaz de representar informações ausentes sem valores fictícios.
- **Riscos / Trade-offs:** Consumidores devem tratar campos opcionais e lista vazia; validações de formato clínico continuam dependentes de trabalho posterior.
- **Validação / Testes:** Testes Pytest cobrirão payload completo, dados ausentes, lista com vários itens, rejeição de campos extras e tipos inválidos.
