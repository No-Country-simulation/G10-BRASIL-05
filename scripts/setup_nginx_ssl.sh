#!/usr/bin/env bash
# ==============================================================================
# MediFlow - Configuração Automática de HTTPS Autoassinado no Nginx (Host da VM)
# ==============================================================================
set -euo pipefail

COR_VERDE="\033[0;32m"
COR_AZUL="\033[0;34m"
COR_RESET="\033[0m"

echo -e "${COR_AZUL}[INFO]${COR_RESET} Verificando permissões de root/sudo..."
if [ "$EUID" -ne 0 ]; then
    echo "Por favor, execute este script com sudo: sudo ./setup_nginx_ssl.sh"
    exit 1
fi

echo -e "${COR_AZUL}[INFO]${COR_RESET} Verificando instalação do Nginx..."
if ! command -v nginx &> /dev/null; then
    echo -e "${COR_AZUL}[INFO]${COR_RESET} Nginx não encontrado. Instalando Nginx via apt-get..."
    apt-get update && apt-get install -y nginx
fi
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

echo -e "${COR_AZUL}[INFO]${COR_RESET} Gerando certificado SSL autoassinado (OpenSSL)..."
mkdir -p /etc/ssl/private /etc/ssl/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/mediflow-selfsigned.key \
  -out /etc/ssl/certs/mediflow-selfsigned.crt \
  -subj "/C=BR/ST=SP/L=SaoPaulo/O=MediFlow/OU=Saude/CN=mediflow.local"

chmod 600 /etc/ssl/private/mediflow-selfsigned.key

echo -e "${COR_AZUL}[INFO]${COR_RESET} Escrevendo configuração do Nginx (/etc/nginx/sites-available/mediflow)..."
cat << 'EOF' > /etc/nginx/sites-available/mediflow
# Redireciona HTTP (porta 80) para HTTPS (porta 443)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://$host$request_uri;
}

# Servidor Seguro HTTPS (porta 443)
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;

    ssl_certificate /etc/ssl/certs/mediflow-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/mediflow-selfsigned.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Suporte a upload de arquivos clínicos pesados (exame, pdf, imagem)
    client_max_body_size 50M;

    # Frontend Streamlit (com WebSockets ativados)
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 86400;
    }

    # Backend FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Documentação Swagger
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }
}
EOF

echo -e "${COR_AZUL}[INFO]${COR_RESET} Ativando configuração no Nginx..."
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
ln -sf /etc/nginx/sites-available/mediflow /etc/nginx/sites-enabled/mediflow

echo -e "${COR_AZUL}[INFO]${COR_RESET} Testando sintaxe do Nginx..."
nginx -t

echo -e "${COR_AZUL}[INFO]${COR_RESET} Recarregando Nginx..."
systemctl reload nginx || systemctl restart nginx

echo -e "${COR_AZUL}[INFO]${COR_RESET} Ajustando firewall iptables local para portas 80 e 443..."
iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
if command -v netfilter-persistent &> /dev/null; then
    netfilter-persistent save 2>/dev/null || true
fi

echo ""
echo -e "${COR_VERDE}[SUCESSO]${COR_RESET} Nginx configurado com HTTPS (porta 443) e redirecionamento de HTTP!"
echo "Acesse agora: https://<IP_DA_SUA_VM>"
echo "(Lembre-se de clicar em 'Avançado' -> 'Continuar para o site' no navegador por ser certificado autoassinado)."
echo "=========================================================="
