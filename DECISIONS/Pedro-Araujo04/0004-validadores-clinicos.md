# [0004] - Validadores Clínicos Determinísticos (SCRUM-53)

- **Data:** 2026-10-28
- **Autor(es):** @Pedro-Araujo04 (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

Os dados extraídos de documentos clínicos precisam de validações determinísticas para detectar CRM e CID-10 fora do formato esperado, idades implausíveis e dados obrigatórios ausentes para cada tipo documental. O modelo atual guarda paciente apenas como texto e, portanto, não consegue representar nem validar a idade apresentada no exemplo oficial.

## 2. Para quê? (Objetivo e Resultados Esperados)

Disponibilizar validadores unitariamente testáveis e uma validação agregada que reporte todas as inconsistências encontradas, sem inferir diagnóstico ou verificar registros em bases externas.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas

- **Alternativa A (Descartada):** Concentrar toda a lógica em validadores do Pydantic. Isso acoplaria as regras por tipo de documento a validações de parsing e dificultaria o retorno conjunto de inconsistências.
- **Alternativa B (Escolhida):** Manter funções puras em `backend/app/agent/nodes/validadores_clinicos.py`, usando os modelos Pydantic apenas como dados de entrada e retornando uma lista de mensagens na validação agregada. Esse caminho segue a estrutura oficial do núcleo do agente para validadores clínicos.

### Detalhamento da Solução

- Atualizar `DadosExtraidos.paciente` para um objeto opcional com `nome` e `idade` opcionais, conforme o exemplo oficial; idade deve ser inteiro estrito.
- Validar CRM nos formatos `CRM-UF número` e `número-UF`, aceitando apenas siglas de UFs brasileiras e sem consultar a existência do registro.
- Validar CID-10 pela sintaxe (`letra + dois dígitos`, com sufixo decimal de um ou dois dígitos opcional), sem catálogo externo.
- Aceitar idade inteira de 0 a 120, inclusive; ausência de idade é permitida.
- Validar campos obrigatórios conforme o tipo: `RECEITA` (paciente, médico com nome e CRM, ao menos um medicamento com nome e dosagem); `LAUDO` (paciente e exame); `GUIA_TISS` (paciente, médico com nome e CRM, exame); `RELATORIO_ALTA` (paciente e diagnóstico principal); `ATESTADO` (paciente, médico com nome e CRM).
- Os validadores individuais retornam booleano; a validação agregada coleta todos os erros em uma lista.
- Campos opcionais ausentes não geram erro, exceto quando exigidos pela matriz do tipo documental.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/schemas/`, `backend/app/agent/nodes/` e `backend/tests/`.
- **Arquivos Criados / Modificados:** `backend/app/agent/__init__.py`, `backend/app/agent/nodes/__init__.py`, `backend/app/agent/nodes/validadores_clinicos.py`, `backend/app/schemas/dados_extraidos.py`, `backend/tests/test_validadores_clinicos.py` e `backend/tests/test_dados_extraidos.py`.
- **Banco de Dados / Infra:** Nenhuma alteração ou dependência nova.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Regras explícitas, resultados reproduzíveis e vários problemas podem ser apresentados de uma só vez para revisão.
- **Riscos / Trade-offs:** Verificar apenas o formato não confirma que um CRM esteja ativo nem que um código CID exista no catálogo oficial. A faixa de idade é uma regra operacional de plausibilidade, não uma regra diagnóstica.
- **Validação / Testes:** Pytest cobrirá formatos aceitos e rejeitados, limites de idade, campos exigidos por cada tipo e acumulação de múltiplas inconsistências.
