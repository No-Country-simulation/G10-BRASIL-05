#!/usr/bin/env bash
# ==============================================================================
# MediFlow - Empacotador para Servidor (Produção Limpa)
# Gera um arquivo tar.gz contendo EXCLUSIVAMENTE backend, frontend e compose.
# ==============================================================================
set -euo pipefail

COR_VERDE="\033[0;32m"
COR_AZUL="\033[0;34m"
COR_RESET="\033[0m"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUTPUT_TAR="mediflow-producao.tar.gz"

echo -e "${COR_AZUL}[INFO]${COR_RESET} Limpando caches locais antes de empacotar..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo -e "${COR_AZUL}[INFO]${COR_RESET} Gerando arquivo de deploy $OUTPUT_TAR..."

# Cria o tar.gz excluindo testes, caches, docs pesados, dados de teste e ambientes virtuais
tar --exclude='backend/tests' \
    --exclude='frontend/tests' \
    --exclude='tests' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='*.log' \
    --exclude='*pytest.ini' \
    --exclude='Storage' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='.agents' \
    --exclude='.codex' \
    --exclude='AGENTS' \
    --exclude='DECISIONS' \
    --exclude='DOCUMENTOS' \
    --exclude='*.pdf' \
    --exclude='.env' \
    --exclude='.env.*' \
    -czvf "$OUTPUT_TAR" \
    backend \
    frontend \
    scripts \
    docker-compose.yml \
    deploy.sh \
    .env_server

echo ""
echo -e "${COR_VERDE}[SUCESSO]${COR_RESET} Pacote gerado com sucesso: $OUTPUT_TAR"
echo "Tamanho do pacote: $(du -h "$OUTPUT_TAR" | cut -f1)"
echo ""
echo "Para enviar e rodar no servidor via SSH:"
echo "  1. Enviar para a VM:"
echo "     scp $OUTPUT_TAR usuario@<IP_DA_VM>:~/"
echo ""
echo "  2. Na VM, descompactar e subir:"
echo "     tar -xzvf $OUTPUT_TAR"
echo "     ./deploy.sh"
echo "=========================================================="
