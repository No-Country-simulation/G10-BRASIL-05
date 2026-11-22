# [0020] - Roteamento Autônomo de Pacientes para Filas Internas

- **Data:** 2026-11-19
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Substituído por [0021](0021-roteamento-autonomo-apenas-documentos.md)

---

## 1. Por quê? (Contexto e Motivação)

O atendimento por WhatsApp precisa encaminhar documentos e mensagens livres para filas adequadas sem exigir que um atendente decida cada caso. Hoje os documentos são classificados e recebem um destino textual, enquanto mensagens livres recebem apenas orientação genérica ou consulta de protocolo. O roteador também não cobre destinos próprios para TISS, atestados, exames e atendimento geral, e não há uma fila interna persistida para solicitações textuais.

## 2. Para quê? (Objetivo e Resultados Esperados)

- Encaminhar automaticamente casos claros para Emergência, Farmácia, Autorizações/TISS, Atestados, Exames ou Atendimento geral.
- Usar confiança mínima de 0,80 como critério auxiliar, junto com intenção clara, campos necessários e ausência de conflito.
- Enviar casos ambíguos, incompletos ou conflitantes para revisão humana, sem exigir revisão para todas as decisões.
- Registrar as solicitações textuais em filas internas do MediFlow para consulta por profissionais autenticados.
- Manter consulta de protocolo e processamento de documentos existentes.
- Limitar a LLM à classificação de intenção/rota; não gerar diagnóstico nem substituir avaliação clínica.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:

- **Alternativa A (Descartada):** Continuar respondendo mensagens livres com orientação estática e apenas gravar o destino dos documentos. Não encaminha pedidos textuais para filas internas.
- **Alternativa B (Escolhida):** Classificar intenção em schema fechado, validar a resposta e aplicar regras determinísticas de destino e revisão. Persistir solicitações de WhatsApp em uma tabela interna consultável por profissionais autenticados.

### Detalhamento da Solução:

1. O agente classifica a intenção da mensagem em categorias fechadas: emergência, farmácia, autorizações/TISS, atestado, exame, atendimento geral, revisão humana ou indeterminada.
2. O agente não produz diagnóstico, prescrição ou aconselhamento clínico. Relatos de sintomas que não sejam um pedido administrativo claro são encaminhados ao atendimento geral ou revisão humana, conforme confiança e conflito.
3. A confiança mínima de 0,80 é aplicada como requisito auxiliar; classe fora do schema, baixa confiança, dados obrigatórios ausentes ou intenções conflitantes levam a revisão humana.
4. Solicitações em texto são persistidas com protocolo, remetente, texto recebido, categoria, confiança, destino, justificativa e status. A API de fila exige perfil profissional autorizado.
5. Documentos seguem o grafo existente e o roteador usa regras explícitas por tipo documental. Sinais de urgência permanecem limitados ao avaliador existente.
6. O canal responde ao paciente com confirmação do protocolo e destino geral, sem expor conteúdo clínico sensível.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/agent/`, `backend/app/controllers/`, `backend/app/models/`, `backend/app/repositories/`, `backend/app/schemas/`, `backend/app/services/`, `backend/migrations/` e `frontend/`.
- **Arquivos Criados / Modificados:** agente e prompt de intenção, política de roteamento, modelo/repositório/API de solicitações, integração com webhook WhatsApp e visualização autenticada das filas.
- **Banco de Dados / Infra:** nova tabela relacional para solicitações textuais; sem nova dependência externa prevista.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Casos administrativos claros avançam sem decisão humana individual, com rastreabilidade e uma fila operacional consultável.
- **Riscos / Trade-offs:** A classificação semântica pode errar. Regras conservadoras e revisão de exceções reduzem o risco, mas não o eliminam. As filas são internas; integração com sistemas externos fica fora desta decisão.
- **Validação / Testes:** A classificação, os limites de confiança, a persistência, autorização da fila e a compatibilidade com protocolo e documentos requerem cobertura automatizada antes de integração.
