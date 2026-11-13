# MediFlow

Aplicação para triagem e roteamento de documentos clínicos. O repositório contém uma API FastAPI em `backend/`, uma interface Streamlit em `frontend/` e testes automatizados para ambos.

## Pré-requisitos

- Python 3.11 (versão usada pela imagem do backend).
- Docker Desktop com Docker Compose, para iniciar PostgreSQL, Redis e MongoDB localmente.
- Git para obter o repositório.

O uso de OCI Object Storage, de um provedor de LLM e da Evolution API/WhatsApp depende de configuração externa. Eles não são necessários para instalar os pacotes ou executar os testes unitários.

## Instalação

Na raiz do repositório, crie e ative um ambiente virtual:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependências de cada aplicação no mesmo ambiente virtual:

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m pip install -r frontend/requirements.txt
```

## Serviços locais

O Compose da raiz inicia os serviços de infraestrutura. PostgreSQL, Redis e MongoDB são usados pela aplicação; a Evolution API pode ser iniciada quando for necessário desenvolver ou validar a integração com WhatsApp.

```powershell
docker compose up -d postgres redis mongodb
# Opcional, para a integração WhatsApp:
docker compose up -d evolution-api
```

O PostgreSQL é publicado na porta `5434` por padrão no host. O backend, por sua vez, lê a configuração `DATABASE_URL`, cujo padrão aponta para a porta `5432`. Para conectar à instância do Compose, defina no ambiente antes de iniciar a API:

```powershell
$env:DATABASE_URL = "postgresql://postgres:root@localhost:5434/mediflow_db"
```

Os valores `postgres/root` são padrões locais definidos no Compose, destinados ao desenvolvimento. Ajuste-os para o ambiente usado. Se alterar usuário, senha, nome do banco ou porta no Compose, mantenha a URL consistente.

Redis e MongoDB usam, por padrão, `redis://localhost:6379/0` e `mongodb://localhost:27017`, respectivamente. O backend carrega configurações de variáveis de ambiente e de arquivos `.env` na raiz do projeto ou em `backend/.env`. Arquivos `.env` não devem ser versionados.

Para inferência com LLM, configure a chave do provedor selecionado em `LLM_PROVIDER` (por exemplo, `OPENROUTER_API_KEY`, `GOOGLE_API_KEY` ou `OPENAI_API_KEY`). O uso de armazenamento OCI requer suas credenciais e dados de bucket. Configure `EVOLUTION_API_URL` e `EVOLUTION_API_KEY` para a Evolution API; não compartilhe nem versione credenciais reais.

## Executar a aplicação

Inicie a API a partir da raiz:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

A documentação interativa da API estará em [http://localhost:8000/docs](http://localhost:8000/docs) e a verificação básica de saúde em [http://localhost:8000/health](http://localhost:8000/health).

Em outro terminal, ative o mesmo ambiente virtual e execute a interface a partir da pasta `frontend`:

```powershell
Set-Location frontend
$env:BACKEND_URL = "http://localhost:8000"
python -m streamlit run app.py
```

A interface abre em [http://localhost:8501](http://localhost:8501). Para executar os comandos em Bash, ative o ambiente com `source .venv/bin/activate`, use `export DATABASE_URL=...` e `export BACKEND_URL=http://localhost:8000`, e substitua os caminhos PowerShell pelos caminhos equivalentes do sistema.

## Testes

Com o ambiente virtual ativo, configure a URL do PostgreSQL na porta publicada pelo Compose e execute a suíte do backend a partir da raiz:

```powershell
$env:DATABASE_URL = "postgresql://postgres:root@localhost:5434/mediflow_db"
python -m pytest backend/tests
```

O backend usa PostgreSQL durante parte da coleta e execução dos testes. Inicie o serviço com `docker compose up -d postgres` antes de executar os testes e use a mesma `DATABASE_URL` configurada na seção anterior. Execute os testes do frontend separadamente, a partir da pasta `frontend`, para que o diretório de serviços seja encontrado:

```powershell
Set-Location frontend
python -m pytest tests
```

Os testes existentes incluem stubs e fixtures para validar fluxos sem depender de todos os provedores externos. Uma execução das suítes não comprova a integração ponta a ponta com Redis, MongoDB, OCI, provedores LLM ou WhatsApp; valide esses serviços separadamente quando fizer parte do desenvolvimento.

## Estrutura do repositório

```text
backend/
  app/                 # API FastAPI, configurações, agentes e acesso a dados
  tests/               # Testes do backend
  requirements.txt
frontend/
  app.py               # Entrada Streamlit
  pages/               # Páginas da interface
  services/             # Cliente da API e respostas de demonstração
  tests/               # Testes do frontend
  requirements.txt
DECISIONS/              # Registros de decisões técnicas
AGENTS/                 # Diretrizes de colaboração do repositório
docker-compose.yml      # PostgreSQL, Redis, MongoDB e Evolution API
```

## Encerrar os serviços

```powershell
docker compose down
```

Esse comando mantém os volumes locais. Para ver os logs de um serviço, use `docker compose logs -f postgres` (substitua `postgres` por `redis`, `mongodb` ou `evolution-api`).
