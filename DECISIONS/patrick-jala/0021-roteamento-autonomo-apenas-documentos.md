# [0021] - Roteamento Autônomo Apenas para Documentos

- **Data:** 2026-11-19
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

Mensagens livres podem descrever sintomas com níveis de gravidade difíceis de inferir com segurança. A classificação de texto poderia encaminhar incorretamente um relato leve como emergência ou uma situação clínica relevante para uma fila administrativa.

## 2. Para quê? (Objetivo e Resultados Esperados)

- Restringir o roteamento autônomo à análise de documentos enviados em PDF ou imagem.
- Responder a mensagens sem documento com instruções para enviar um arquivo legível.
- Manter consultas textuais a protocolos de documentos existentes.
- Encaminhar documentos validados automaticamente para Emergência, Farmácia, Autorizações/TISS, Atestados, Exames ou atendimento padrão conforme tipo e prioridade.
- Preservar revisão humana para documentos ambíguos, incompletos ou abaixo do limiar de confiança.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:

- **Alternativa A (Descartada):** Classificar mensagens livres e criar solicitações em filas de atendimento. Descartada por exigir inferência de intenção e potencial gravidade clínica sem um documento verificável.
- **Alternativa B (Escolhida):** Não criar filas a partir de texto livre. O WhatsApp responde com instruções para envio de PDF/imagem, exceto quando a pessoa consulta um protocolo `DOC-*` já existente. O fluxo documental mantém o roteamento autônomo e seus gates de validação/revisão.

### Detalhamento da Solução:

O webhook usa texto apenas para orientação e consulta de protocolo. Anexos seguem o fluxo existente de ingestão, classificação, extração, validação e roteamento. O limite mínimo de confiança para automação é 0,80. Mensagens textuais não são classificadas como emergência nem persistidas como solicitações de atendimento.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/agent/`, `backend/app/controllers/`, `backend/app/services/`, `backend/migrations/` e `frontend/`.
- **Arquivos Criados / Modificados:** `backend/app/agent/nodes/roteador.py`, `backend/app/agent/config.py`, `backend/app/controllers/evolution_webhook.py`, `backend/app/services/evolution_service.py` e configuração do limiar de confiança.
- **Banco de Dados / Infra:** sem fila ou tabela nova para mensagens livres. Revisões de documentos continuam no esquema de triagem/auditoria existente.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Evita encaminhamento clínico baseado apenas em relatos de texto e mantém uma experiência simples para envio de documentos.
- **Riscos / Trade-offs:** Pedidos de atendimento que não venham acompanhados de documento não serão encaminhados automaticamente por este fluxo; a resposta orientará o envio do arquivo.
- **Validação / Testes:** Verificar orientação para texto sem protocolo, consulta de protocolo `DOC-*`, roteamento de cada tipo documental e revisão para baixa confiança.
