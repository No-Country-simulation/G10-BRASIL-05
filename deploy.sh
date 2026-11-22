#!/usr/bin/env bash
# ==============================================================================
# MediFlow - Deploy Incremental (Estilo Git / CI/CD com rsync)
# Envia APENAS os arquivos que foram modificados, sem tocar nas configs do servidor (.env_server, chaves OCI, etc.)
# ==============================================================================
set -euo pipefail

COR_VERDE="\033[0;32m"
COR_AZUL="\033[0;34m"
COR_AMARELO="\033[1;33m"
COR_RESET="\033[0m"

log_info() { echo -e "${COR_AZUL}[INFO]${COR_RESET} $1"; }
log_sucesso() { echo -e "${COR_VERDE}[SUCESSO]${COR_RESET} $1"; }
log_alerta() { echo -e "${COR_AMARELO}[AVISO]${COR_RESET} $1"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

REMOTE_HOST="${1:-oci1}"
REMOTE_DIR="${2:-HACKATHON}"

echo "=========================================================="
echo "    MediFlow - Deploy Incremental                         "
echo "    Destino: $REMOTE_HOST:$REMOTE_DIR                     "
echo "=========================================================="

# 1. Limpeza local de caches antes da sincronização
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 2. Sincronização incremental de alta velocidade com rsync
log_info "Sincronizando apenas arquivos modificados com o servidor..."
rsync -avz \
    --exclude='backend/tests/' \
    --exclude='frontend/tests/' \
    --exclude='tests/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache/' \
    --exclude='*.log' \
    --exclude='*pytest.ini' \
    --exclude='Storage/' \
    --exclude='.venv/' \
    --exclude='venv/' \
    --exclude='.git/' \
    --exclude='.agents/' \
    --exclude='.codex/' \
    --exclude='AGENTS/' \
    --exclude='DECISIONS/' \
    --exclude='DOCUMENTOS/' \
    --exclude='*.pdf' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='.env_*' \
    --exclude='*.pem' \
    --exclude='mediflow-producao.tar.gz' \
    ./ "$REMOTE_HOST:$REMOTE_DIR/"

log_sucesso "Arquivos modificados sincronizados com sucesso."

# 3. Rebuild e atualização dos contêineres no servidor
log_info "Reconstruindo apenas os contêineres com código alterado na VM..."
ssh -t "$REMOTE_HOST" "
    cd $REMOTE_DIR
    docker compose --env-file .env_server --profile infra up -d --build --remove-orphans
"

echo ""
echo "=========================================================="
log_sucesso "Deploy concluído! Aplicação atualizada na OCI."
echo "URL: https://129.146.58.37.sslip.io"
echo "=========================================================="
