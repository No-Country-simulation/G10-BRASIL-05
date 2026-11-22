# Evolution API e WhatsApp

## Variáveis necessárias

Configure estas variáveis no `.env` da raiz do projeto, baseado em `.env.example`:

- `EVOLUTION_API_KEY`: chave usada pelo backend e pela Evolution API no header `apikey`.
- `EVOLUTION_WEBHOOK_SECRET`: segredo separado enviado no header `x-webhook-token`; precisa ter pelo menos 32 caracteres.
- `EVOLUTION_INSTANCE_NAME`: nome único da instância, por padrão `mediflow`.
- `EVOLUTION_WEBHOOK_URL`: endereço do backend que a Evolution consegue alcançar. No Compose, use `http://backend:8000/webhook/evolution`.
- `EVOLUTION_SERVER_URL`: endereço do serviço Evolution publicado no host, normalmente `http://localhost:8080` para desenvolvimento local.
- `EVOLUTION_DB_NAME`: banco PostgreSQL exclusivo da Evolution, por padrão `evolution`. Ele fica no mesmo servidor Postgres, separado de `DB_NAME` do MediFlow.

O Compose cria esse banco caso ainda não exista. A Evolution não usa o banco do MediFlow: isso mantém as migrations de cada aplicação isoladas. Não é necessário apagar ou limpar o banco do MediFlow.

Gere cada segredo separadamente e não os registre no Git:

```bash
openssl rand -hex 32
```

Use uma saída para `EVOLUTION_API_KEY` e outra para `EVOLUTION_WEBHOOK_SECRET`.

## Subir o serviço

O serviço `whatsapp` usa o profile `infra`. Com o `.env` configurado, o comando abaixo inicia os bancos, Redis, MongoDB, Evolution, backend e frontend:

```bash
docker compose --profile infra up -d --build postgres redis mongodb whatsapp backend frontend
```

Para acompanhar a inicialização da Evolution e do backend:

```bash
docker compose logs -f evolution-db-init whatsapp backend
```

## Conectar o aparelho

Entre no frontend com uma conta `ADMIN_GERAL`, abra **Conectar WhatsApp** e gere o QR Code. Após parear o aparelho, use **Salvar e ativar webhook**. Em ambiente Compose, a URL padrão é alcançável pelo DNS interno do serviço `backend`; informe uma URL manual somente quando estiver usando outro endereço acessível pela Evolution.

O valor do token de autenticação da Evolution (`EVOLUTION_API_KEY`) e o segredo do webhook (`EVOLUTION_WEBHOOK_SECRET`) têm funções diferentes e devem ser configurados no ambiente. Não os inclua na URL do webhook.
