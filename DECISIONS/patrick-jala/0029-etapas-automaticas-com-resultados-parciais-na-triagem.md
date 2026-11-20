# [0029] - Etapas automáticas com resultados parciais na triagem

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)

Hoje a tela recebe o resultado da triagem somente quando todo o processamento termina. A equipe quer ver primeiro os dados de paciente e médico identificados no documento, enquanto a análise clínica continua automaticamente.

## 2. Para quê? (Objetivo e Resultados Esperados)

Exibir uma devolutiva intermediária da identificação cadastral e, sem pausar o fluxo nem aguardar decisão humana, continuar para classificação e análise clínica, validação, avaliação de risco e roteamento.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:

- **Processar tudo e responder apenas no final:** descartada porque não permite acompanhar o resultado da primeira etapa.
- **Interromper o grafo e retomá-lo depois:** descartada porque a sequência é automática e não depende de confirmação humana.
- **Etapas sequenciais com atualização do trabalho na fila:** escolhida. O primeiro passo extrai dados de paciente e médico, procura correspondências de forma somente leitura e publica a etapa atual. O resultado identificador permanece no estado do LangGraph, e a análise clínica continua com esse contexto. A API autenticada recupera o resultado parcial do checkpoint; Redis guarda somente o status da etapa.

### Detalhamento da Solução:

Executar a validação de escopo, extrair paciente e médico, buscar correspondências exatas e únicas no cadastro sem criar nem alterar registros, e disponibilizar um resumo intermediário vinculado ao `documento_id`. A análise clínica recebe o texto original e o contexto identificado. A consulta de status retorna etapa atual e resumo parcial quando disponível, respeitando a autorização do usuário proprietário. A resposta final e os fluxos de auditoria existentes permanecem preservados.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/agent/`, `backend/app/services/`, `backend/app/repositories/`, `backend/app/controllers/`, `frontend/`.
- **Arquivos Criados / Modificados:** estado e grafo LangGraph, nó de identificação, prompt de extração, repositórios de pacientes e médicos, serviço e worker de triagem, consulta de trabalho, cliente HTTP e tela de triagem.
- **Banco de Dados / Infra:** sem migração ou nova dependência; o checkpoint PostgreSQL mantém os dados intermediários, Redis mantém apenas progresso operacional.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** feedback visível antes da resposta final, contexto preservado entre etapas e nenhuma pausa de retomada.
- **Riscos / Trade-offs:** correspondências ambíguas ou sem identificador confiável não são tratadas como confirmadas; são mostradas como tal e o fluxo continua para validação existente.
- **Validação / Testes:** validar correspondência única, ausente e ambígua, atualização da etapa no endpoint autenticado, continuidade até a resposta final e preservação do comportamento de auditoria.
