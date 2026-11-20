# [0016] - Harness de Segurança para Triagem de Documentos

- **Data:** 2026-11-19
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)

O fluxo MediFlow precisa separar escopo médico, legibilidade e análise clínica. Hoje, sinais insuficientes de elegibilidade podem abrir revisão humana como se fosse auditoria médica, e a LLM pode receber texto sem uma política unificada que limite suas ações. Isso pode persistir conteúdo fora do escopo, encaminhar material desconhecido para a fila errada ou levar a classificação clínica sem evidência legível.

## 2. Para quê? (Objetivo e Resultados Esperados)

- Definir um Harness como camada de software que organiza regras, ferramentas, contexto e execução da LLM.
- Recusar conteúdo claramente não médico antes de qualquer persistência.
- Permitir triagem normal para documentos médicos legíveis.
- Encaminhar documentos que aparentam ser médicos, mas não podem ser lidos ou não têm texto extraível, para revisão humana de legibilidade.
- Impedir classificação, diagnóstico e CID inventados; se o revisor confirmar ilegibilidade, solicitar reenvio.
- Evitar que conteúdo desconhecido seja enviado automaticamente para auditoria médica.
- Disponibilizar uma inspeção sem persistência que mostre o texto efetivamente extraído e a decisão de escopo, inclusive em documentos recusados, para depuração.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Manter uma lista crescente de palavras-chave e nomes de documentos fora do escopo. Não generaliza para tipos documentais novos.
- **Alternativa B (Escolhida):** Usar um classificador semântico de escopo multimodal, com resposta estruturada e evidências validadas, antes dos nós clínicos; manter regras determinísticas apenas como proteções auxiliares.

### Detalhamento da Solução:

O Harness controla a sequência: validação do arquivo, extração textual/visual, decisão estruturada de escopo, avaliação de legibilidade, triagem clínica e revisão humana. A decisão de escopo ocorre antes da persistência. O classificador retorna `medico`, `nao_medico` ou `incerto`, legibilidade, justificativa e evidências tipadas. Evidências textuais precisam corresponder a trechos encontrados na extração. Evidências visuais descrevem sinais observáveis do formulário, sem completar texto ilegível. O classificador de escopo não produz tipo documental clínico, diagnóstico nem CID. Somente documentos médicos legíveis avançam à triagem; documentos médicos ilegíveis vão à revisão de legibilidade; fora de escopo é recusado; escopo indeterminado pede outro arquivo. Uma rota de inspeção sem persistência usa o mesmo classificador e mostra a decisão e as evidências.

Conteúdo cuja natureza médica permaneça indeterminada não será automaticamente classificado como médico nem encaminhado para auditoria médica. O sistema pedirá uma nova imagem ou documento que permita comprovar o contexto médico, sem persistir o arquivo indeterminado.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/agent/`, `backend/app/services/`, `backend/app/controllers/` e páginas/serviços do frontend.
- **Arquivos Criados / Modificados:** Harness/política do agente, schema e prompt de escopo, filtros de elegibilidade e qualidade, parser, fluxos de upload/texto/WhatsApp, inspeção sem persistência e interface; casos automatizados do fluxo.
- **Banco de Dados / Infra:** Sem alteração de schema ou dependências prevista; confirmar ao implementar.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Limites de responsabilidade explícitos, menor risco de alucinação clínica e roteamento mais seguro para revisão.
- **Riscos / Trade-offs:** A decisão semântica ainda pode errar e deve falhar para `incerto` quando não houver evidência validável. PDF digitalizado sem texto não é inspecionado visualmente nesta entrega e pedirá outro arquivo. A inspeção exibirá dados sensíveis no navegador do usuário que enviou o arquivo e não deve ser persistida como registro clínico.
- **Validação / Testes:** Exercitar recusa pré-persistência, triagem legível, revisão de legibilidade sem classificação/CID, solicitação de reenvio após confirmação humana e conteúdo indeterminado sem auditoria médica automática.
