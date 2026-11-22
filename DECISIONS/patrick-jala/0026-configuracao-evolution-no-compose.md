# [0026] - Configuração da Evolution API no Compose

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
A integração já possui serviço, endpoints e tela para conectar o WhatsApp, mas o serviço Evolution fica em um perfil separado e a configuração automática do webhook usa um endereço IP de bridge fixo. Isso faz com que a API possa não ser iniciada junto da infraestrutura e que o webhook não consiga alcançar o backend em diferentes instalações Docker.

## 2. Para quê? (Objetivo e Resultados Esperados)
Deixar explícito como iniciar a Evolution junto da infraestrutura e permitir configurar o endereço do webhook sem depender de um IP de host fixo.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Manter o IP fixo como endereço padrão do webhook; ele varia conforme a rede Docker e pode não existir em outras máquinas.
- **Alternativa B (Escolhida):** Ler a URL do webhook da configuração de ambiente e usar o DNS do serviço `backend` no Compose; manter a Evolution em perfil explicitamente ativável.

### Detalhamento da Solução:
Adicionar `EVOLUTION_WEBHOOK_URL` às configurações do backend, usar esse valor quando a tela/API não receber uma URL específica, e fornecer o endereço interno `http://backend:8000/webhook/evolution` no Compose. O serviço `whatsapp` pertence ao profile `infra`. As credenciais da API e do webhook permanecem fornecidas pelo operador via env.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/config/`, `backend/app/services/`, `docker-compose.yml`, exemplos de env e documentação.
- **Arquivos Criados / Modificados:** Configuração do backend e exemplos de env; configuração Compose e guia local de WhatsApp.
- **Banco de Dados / Infra:** Sem alteração de banco; a Evolution requer Postgres, Redis, porta configurada e segredos definidos pelo operador.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Inicialização e destino do webhook ficam reprodutíveis sem IP de bridge fixo.
- **Riscos / Trade-offs:** A instalação deve habilitar o profile `infra` e configurar chaves válidas; em hospedagens externas, o endpoint do backend ainda precisa estar alcançável pela Evolution.
- **Validação / Testes:** Revisar a composição e validar sintaxe/configuração estaticamente; não iniciar ou reiniciar containers nesta solicitação.
