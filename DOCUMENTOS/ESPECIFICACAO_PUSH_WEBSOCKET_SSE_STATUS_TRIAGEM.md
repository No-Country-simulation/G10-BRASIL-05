# Especificação Técnica: Push em Tempo Real (SSE / WebSocket) para Status de Triagem Clínica

**Status**: Proposta de Arquitetura  
**Autor**: Frontend UI/UX  
**Destinatário**: Equipe de Backend / Core  
**Data**: 2026-11-20  

---

## 1. Contexto e Motivação

Atualmente, o processamento de documentos clínicos pela IA e agentes LangGraph ocorre de forma assíncrona através de filas Redis (`rq` / `triagem_queue`). 

Na interface do usuário, a tela de **Análise** acompanha a esteira de processamento dos arquivos enviados. Para evitar tráfego desnecessário de rede por consultas periódicas (*polling* contínuo de `GET /triagem/trabalhos/{documento_id}`) e garantir que o operador veja instantaneamente quando um documento:
1. Entra na fila;
2. Inicia o processamento;
3. Tem a identificação cadastral do paciente concluída (Nome e CPF extraídos);
4. Conclui com sucesso ou falha;

É necessária uma via de comunicação unidirecional (ou bidirecional) direta do servidor para o cliente web.

---

## 2. Recomendação de Protocolo: Server-Sent Events (SSE)

Para o caso de uso do MediFlow (onde o cliente apenas recebe notificações e eventos de progresso emitidos pelo backend), o protocolo **Server-Sent Events (SSE)** sobre HTTP/2 ou HTTP/1.1 é a solução mais leve, padronizada e robusta:

- **Vantagens em relação a WebSockets**:
  - Funciona nativamente sobre HTTP/HTTPS padrão (sem necessidade de *handshake upgrade* de protocolo).
  - Reconexão automática embutida na API do navegador (`EventSource`).
  - Suporte nativo a IDs de evento e controle de continuidade (`Last-Event-ID`).
  - Menor complexidade de infraestrutura em proxies reversos (Nginx, Traefik, AWS ALB).

*(Nota: Caso o backend opte por WebSockets devido a padrões já existentes na infraestrutura, a estrutura dos eventos abaixo permanece idêntica).*

---

## 3. Endpoints Propostos

### 3.1. Stream de Eventos por Usuário ou Lote

```http
GET /api/v1/triagem/eventos/stream?lote_id={lote_id}
```
ou
```http
GET /api/v1/triagem/eventos/stream
```

- **Headers**:
  - `Authorization: Bearer <token_jwt>`
  - `Accept: text/event-stream`
- **Response**:
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`

---

## 4. Estrutura dos Eventos (JSON Payload)

Cada evento disparado pelo backend para o canal do cliente deve seguir o formato SSE padrão com um payload JSON estruturado:

### 4.1. Evento: Atualização de Etapa / Início de Processamento (`status_update`)
```text
event: status_update
data: {
  "documento_id": "doc-a1b2c3d4",
  "lote_id": "lote-987654",
  "status": "processando",
  "etapa_atual": "analise_clinica",
  "arquivo": "laudo_exame.pdf",
  "atualizado_em": "2026-11-20T21:10:00Z"
}
```

### 4.2. Evento: Identificação do Paciente Concluída (`paciente_identificado`)
*Disparado assim que o nó do agente extrai o nome e CPF do paciente, antes do fim de todo o pipeline.*
```text
event: paciente_identificado
data: {
  "documento_id": "doc-a1b2c3d4",
  "lote_id": "lote-987654",
  "status": "processando",
  "paciente_nome": "Maria Silva Santos",
  "paciente_cpf": "123.456.789-00",
  "atualizado_em": "2026-11-20T21:10:12Z"
}
```

### 4.3. Evento: Processamento Concluído com Sucesso (`concluido`)
```text
event: concluido
data: {
  "documento_id": "doc-a1b2c3d4",
  "lote_id": "lote-987654",
  "status": "concluido",
  "paciente_nome": "Maria Silva Santos",
  "paciente_cpf": "123.456.789-00",
  "classificacao_risco": "AMARELO",
  "tipo_documento": "Receituário / Laudo",
  "destino_sugerido": "Ambulatório",
  "alertas": [],
  "atualizado_em": "2026-11-20T21:10:25Z"
}
```

### 4.4. Evento: Falha no Processamento (`falha`)
```text
event: falha
data: {
  "documento_id": "doc-a1b2c3d4",
  "lote_id": "lote-987654",
  "status": "falhou",
  "erro_codigo": "TIMEOUT_EXTRACAO",
  "erro_mensagem": "Tempo limite de análise de imagem excedido.",
  "atualizado_em": "2026-11-20T21:10:30Z"
}
```

---

## 5. Arquitetura de Publicação no Backend (Redis Pub/Sub)

Para conectar os trabalhadores assíncronos (`rq worker` / `triagem_worker.py`) ao endpoint FastAPI que serve o cliente:

1. **Worker publica no Redis**:
   Ao mudar de status no `triagem_worker.py`:
   ```python
   redis.publish(
       f"triagem:usuario:{usuario_id}:eventos",
       json.dumps({"event": "status_update", "data": {...}})
   )
   ```
2. **FastAPI consome via PubSub assíncrono**:
   O endpoint SSE escuta `pubsub.listen()` no canal do usuário e faz o `yield` de cada mensagem diretamente para o cliente conectado.

---

## 6. Integração no Frontend

Assim que este endpoint estiver disponível, o frontend registrará um ouvinte SSE via componente dedicado, eliminando qualquer necessidade de recarregamento manual ou polling por tempo.
