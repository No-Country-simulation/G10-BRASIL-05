"""Configuração isolada para testes locais sem dependência de containers."""

import os


# Definir antes dos imports da aplicação força o engine de teste a usar SQLite
# em memória, sem tocar no PostgreSQL configurado no .env do desenvolvedor.
os.environ["APP_ENV"] = "local"
os.environ["DATABASE_URL"] = "sqlite://"
# Testes usam storage local e nunca devem enviar fixtures para um bucket real.
os.environ["OCI_AUTH_MODE"] = "local_only"
