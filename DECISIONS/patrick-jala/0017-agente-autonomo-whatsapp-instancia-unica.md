# [0017] - Agente Autônomo do WhatsApp em Instância Única e Vínculo Institucional

- **Data:** 2026-11-19
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
O canal do WhatsApp no MediFlow precisa operar como um **agente autônomo institucional único** para todo o sistema, desacoplado das sessões individuais de médicos, enfermeiros e diretores clínicos. Anteriormente:
1. A aba de conexão do WhatsApp (`pages/4_WhatsApp_Evolution.py`) ficava exposta a qualquer perfil no frontend e o banco de dados não registrava a conta institucional responsável pela conexão (`mediflow@equipe.com.br` / `senha123456`) nem o estado persistido da instância única do agente.
2. Os documentos triados via WhatsApp não armazenavam os metadados do remetente (`whatsapp_numero`, `whatsapp_nome`, `whatsapp_message_id`) na tabela `documentos_triagem`.
3. Quando um documento enviado pelo WhatsApp caía em Revisão Humana (por legibilidade ou auditoria clínica), o worker enviava imediatamente diagnósticos/CIDs não validados no chat e não notificava o remetente quando o auditor concluía a revisão.
4. Mensagens de texto recebiam apenas uma resposta estática genérica, sem permitir consulta de status de protocolo (`DOC-WPP-...`) no banco de dados.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Garantir que exista **um único número/instância de WhatsApp** vinculado ao sistema como agente autônomo, cuja tela e endpoints de conexão sejam restritos exclusivamente à conta institucional (`mediflow@equipe.com.br`).
- Persistir no banco de dados o usuário institucional (`usuarios_sistema`), o estado e vínculo da instância única (`instancias_whatsapp`) e os metadados de origem do WhatsApp em cada triagem (`documentos_triagem`).
- Tornar o atendimento por texto no WhatsApp guiado e capaz de consultar em tempo real o status de protocolos (`DOC-WPP-...`) diretamente no banco de dados, exigindo PDF ou imagem para iniciar triagem clínica.
- Reter diagnósticos e CIDs não validados quando o documento entrar em revisão humana (`em_auditoria`), enviando apenas o aviso de encaminhamento para revisão e disparando automaticamente a devolutiva final ou solicitação de reenvio no WhatsApp assim que a decisão humana for registrada.

---

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Controlar o acesso à conexão do WhatsApp apenas em memória no Streamlit e manter o envio imediato de resultados preliminares no worker. Descartada por não persistir o vínculo institucional no banco, não proteger o backend e expor dados clínicos antes da validação humana.
- **Alternativa B (Escolhida):** Persistir a conta institucional e a instância única no banco de dados relacional, validar o vínculo institucional nos endpoints de gestão da instância, registrar o remetente do WhatsApp na triagem, suportar consulta de protocolo por texto e integrar o callback automático pós-auditoria.

### Detalhamento da Solução:
1. **Modelagem e Seed no Banco (`backend/app/models/triagem.py` e `backend/app/repositories/database.py`):**
   - Tabela `usuarios_sistema` (`UsuarioSistemaModel`) com seed automático da conta institucional `mediflow@equipe.com.br` (senha `senha123456` armazenada com hash `PBKDF2-HMAC-SHA256` da biblioteca padrão `hashlib` e flag `pode_gerenciar_whatsapp=True`).
   - Tabela `instancias_whatsapp` (`InstanciaWhatsAppModel`) representando a instância autônoma única do sistema vinculada a `mediflow@equipe.com.br`.
   - Colunas `whatsapp_numero`, `whatsapp_nome` e `whatsapp_message_id` em `DocumentoTriagemModel` (`documentos_triagem`).
2. **Autenticação Institucional e Gestão da Instância (`backend/app/controllers/evolution.py`):**
   - Endpoint `POST /webhook/evolution/autenticar-institucional` (e `/api/v1/webhook/evolution/autenticar-institucional`) que valida `email` e `senha` no banco de dados.
   - Validação do vínculo institucional (`X-Usuario-Email: mediflow@equipe.com.br`) nos endpoints de gestão da instância única (`/status-instancia`, `/conectar`, `/configurar-webhook`, `/desconectar`, `/enviar-teste`), sincronizando o estado no banco de dados.
3. **Agente Autônomo no WhatsApp (`evolution_service.py`, `evolution_webhook.py`, `evolution_triage_worker.py` e `triagem.py`):**
   - Atendimento guiado em mensagens de texto com detecção de protocolo (`DOC-WPP-...` / `DOC-...`) e consulta real ao banco de dados para informar o status atualizado.
   - Retenção de diagnóstico/CID quando `requer_auditoria_humana=True` (enviando aviso de revisão humana no WhatsApp).
   - Notificação ativa automática via WhatsApp ao concluir `TriagemService.registrar_decisao_medica` (devolutiva clínica validada, pedido de reenvio por ilegibilidade ou aviso de recusa).
4. **Visibilidade Condicional no Frontend (`frontend/app.py`, `frontend/utils/usuarios.py`, `frontend/services/cliente_whatsapp.py`):**
   - Função e hook de sessão (`eh_conta_institucional_whatsapp` / `EMAIL_INSTITUCIONAL_WHATSAPP = "mediflow@equipe.com.br"`) que oculta a página `Conectar` (`pages/4_WhatsApp_Evolution.py`) na navegação lateral para os perfis hospitalares comuns e só a exibe quando a conta institucional está ativa na sessão.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/models/`, `backend/app/repositories/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/controllers/`, `frontend/`, `frontend/utils/`, `frontend/services/`, `frontend/pages/`.
- **Arquivos Criados / Modificados:**
  - `backend/app/models/triagem.py`
  - `backend/app/repositories/database.py`
  - `backend/app/schemas/triagem.py`
  - `backend/app/services/evolution_service.py`
  - `backend/app/services/evolution_triage_worker.py`
  - `backend/app/services/triagem.py`
  - `backend/app/controllers/evolution.py`
  - `backend/app/controllers/evolution_webhook.py`
  - `frontend/app.py`
  - `frontend/utils/usuarios.py`
  - `frontend/services/cliente_whatsapp.py`
  - `frontend/pages/4_WhatsApp_Evolution.py`
  - `backend/tests/test_evolution_webhook.py`
  - `frontend/tests/test_app.py`, `frontend/tests/test_usuarios.py`, `frontend/tests/test_cliente_whatsapp.py`
- **Banco de Dados / Infra:** Novas tabelas `usuarios_sistema` e `instancias_whatsapp`, novas colunas de rastreamento WhatsApp em `documentos_triagem`, sem adição de bibliotecas externas.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** O WhatsApp passa a operar como agente autônomo único do sistema com governança no banco de dados, proteção contra exposição de diagnósticos não auditados e retorno ativo ao paciente/solicitante após o Human-in-the-Loop.
- **Riscos / Trade-offs:** Quando a tela de login definitiva do frontend for implementada, ela deverá popular o e-mail autenticado na sessão (`usuario_autenticado_email`) utilizando o endpoint institucional já estruturado no backend.
- **Validação / Testes:** Testes automatizados no backend (seed institucional, proteção dos endpoints de gestão, consulta de protocolo por texto, retenção em auditoria e callback pós-decisão) e no frontend (visibilidade condicional da aba Conectar e envio do cabeçalho institucional).
