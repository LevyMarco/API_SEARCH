#!/bin/bash
# Deploy Rápido para 177.11.151.37
# Uso: ./deploy_agora.sh

set -e

SERVER_IP="177.11.151.37"

echo "=========================================="
echo "🚀 Deploy Rápido - Seu Servidor"
echo "=========================================="
echo "IP: $SERVER_IP"
echo "Specs: 24 CPU, 128GB RAM"
echo ""

# Verificar se arquivos existem
if [ ! -f "cluster_master.py" ]; then
    echo "❌ Arquivos não encontrados!"
    echo "   Execute este script dentro da pasta scraper_windows/"
    exit 1
fi

# Verificar conexão
echo "🔍 Verificando conexão..."
if ! ssh -o ConnectTimeout=5 root@$SERVER_IP "echo OK" > /dev/null 2>&1; then
    echo "❌ Não foi possível conectar ao servidor"
    echo ""
    echo "Tente:"
    echo "  ssh root@$SERVER_IP"
    echo ""
    echo "Se não tiver acesso root, edite o script e mude 'root' para seu usuário."
    exit 1
fi
echo "✅ Conexão OK"
echo ""

# Upload arquivos
echo "📤 Enviando arquivos..."
scp -q cluster_master.py root@$SERVER_IP:/root/
scp -q cluster_worker.py root@$SERVER_IP:/root/
scp -q captcha_solver_free.py root@$SERVER_IP:/root/
echo "✅ Arquivos enviados"
echo ""

# Instalar dependências
echo "📦 Instalando dependências (pode demorar 2-3 min)..."
ssh root@$SERVER_IP << 'EOF'
# Atualizar
apt-get update > /dev/null 2>&1

# Redis
if ! command -v redis-server &> /dev/null; then
    echo "  - Instalando Redis..."
    apt-get install -y redis-server > /dev/null 2>&1
else
    echo "  - Redis já instalado"
fi

# Chrome
if ! command -v google-chrome &> /dev/null; then
    echo "  - Instalando Chrome..."
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - > /dev/null 2>&1
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
    apt-get update > /dev/null 2>&1
    apt-get install -y google-chrome-stable > /dev/null 2>&1
else
    echo "  - Chrome já instalado"
fi

# Python deps
echo "  - Instalando dependências Python..."
pip3 install -q redis flask flask-cors selenium undetected-chromedriver requests 2>/dev/null || true
EOF
echo "✅ Dependências instaladas"
echo ""

# Configurar Redis
echo "⚙️  Configurando Redis..."
ssh root@$SERVER_IP << 'EOF'
# Backup
cp /etc/redis/redis.conf /etc/redis/redis.conf.bak 2>/dev/null || true

# Configurar
if ! grep -q "requirepass" /etc/redis/redis.conf; then
    cat >> /etc/redis/redis.conf << 'REDIS_CONF'

# Configurações customizadas
bind 127.0.0.1
requirepass MUDE_ESTA_SENHA_123
maxmemory 8gb
maxmemory-policy allkeys-lru
REDIS_CONF
fi

systemctl restart redis-server
systemctl enable redis-server > /dev/null 2>&1
EOF
echo "✅ Redis configurado"
echo ""

# Criar serviços
echo "🔧 Criando serviços systemd..."
ssh root@$SERVER_IP << 'EOF'
# Master
cat > /etc/systemd/system/cluster-master.service << 'SERVICE'
[Unit]
Description=Cluster Master
After=network.target redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/root
EnvironmentFile=/root/.env
ExecStart=/usr/bin/python3 /root/cluster_master.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Worker
cat > /etc/systemd/system/cluster-worker.service << 'SERVICE'
[Unit]
Description=Cluster Worker
After=network.target redis-server.service cluster-master.service

[Service]
Type=simple
User=root
WorkingDirectory=/root
EnvironmentFile=/root/.env
ExecStart=/usr/bin/python3 /root/cluster_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
EOF
echo "✅ Serviços criados"
echo ""

echo "=========================================="
echo "✅ Deploy concluído!"
echo "=========================================="
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo ""
echo "1. Criar 20 apps no Wit.ai:"
echo "   https://wit.ai"
echo ""
echo "2. Configurar no servidor:"
echo "   ssh root@$SERVER_IP"
echo "   nano /root/.env"
echo ""
echo "   Adicione:"
echo "   REDIS_HOST=127.0.0.1"
echo "   REDIS_PORT=6379"
echo "   REDIS_PASSWORD=MUDE_ESTA_SENHA_123"
echo "   NODE_NAME=main-server"
echo "   WORKERS_PER_NODE=15"
echo "   WIT_API_KEYS=key1,key2,key3,...,key20"
echo "   PORT=5000"
echo ""
echo "3. Iniciar serviços:"
echo "   systemctl start cluster-master"
echo "   systemctl start cluster-worker"
echo ""
echo "4. Verificar:"
echo "   curl http://localhost:5000/health"
echo "   curl http://localhost:5000/api/workers"
echo ""
echo "5. Testar busca:"
echo "   curl \"http://localhost:5000/api/search?query=restaurante&location=São Paulo\""
echo ""
echo "6. Monitorar (no seu PC):"
echo "   export MASTER_URL=http://$SERVER_IP:5000"
echo "   python cluster_monitor.py"
echo ""
echo "=========================================="
echo ""
echo "📖 Guia completo: DEPLOY_SEU_SERVIDOR.md"
echo ""

