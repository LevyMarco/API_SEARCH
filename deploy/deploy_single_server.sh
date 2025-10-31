#!/bin/bash
# Deploy Automatizado - Servidor Único para 80K buscas/semana
# Uso: ./deploy_single_server.sh <SERVER_IP>

set -e

SERVER_IP=$1

if [ -z "$SERVER_IP" ]; then
    echo "Uso: ./deploy_single_server.sh <SERVER_IP>"
    echo ""
    echo "Exemplo:"
    echo "  ./deploy_single_server.sh 192.168.1.100"
    exit 1
fi

echo "=========================================="
echo "🚀 Deploy Servidor Único - 80K/semana"
echo "=========================================="
echo "IP: $SERVER_IP"
echo ""

# Verificar conexão
echo "🔍 Verificando conexão..."
if ! ssh -o ConnectTimeout=5 root@$SERVER_IP "echo OK" > /dev/null 2>&1; then
    echo "❌ Não foi possível conectar ao servidor"
    echo "   Verifique o IP e suas credenciais SSH"
    exit 1
fi
echo "✅ Conexão OK"
echo ""

# Upload arquivos
echo "📤 Uploading arquivos..."
scp cluster_master.py root@$SERVER_IP:/root/
scp cluster_worker.py root@$SERVER_IP:/root/
scp captcha_solver_free.py root@$SERVER_IP:/root/
echo "✅ Arquivos enviados"
echo ""

# Instalar dependências
echo "📦 Instalando dependências..."
ssh root@$SERVER_IP << 'EOF'
# Atualizar sistema
echo "  - Atualizando sistema..."
apt-get update > /dev/null 2>&1
apt-get upgrade -y > /dev/null 2>&1

# Instalar Redis
echo "  - Instalando Redis..."
apt-get install -y redis-server > /dev/null 2>&1

# Instalar Python
echo "  - Instalando Python..."
apt-get install -y python3.11 python3-pip > /dev/null 2>&1

# Instalar Chrome
echo "  - Instalando Chrome..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - > /dev/null 2>&1
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
apt-get update > /dev/null 2>&1
apt-get install -y google-chrome-stable > /dev/null 2>&1

# Instalar dependências Python
echo "  - Instalando dependências Python..."
pip3 install -q redis flask flask-cors selenium undetected-chromedriver requests

echo "✅ Dependências instaladas"
EOF
echo ""

# Configurar Redis
echo "⚙️  Configurando Redis..."
ssh root@$SERVER_IP << 'EOF'
# Backup config original
cp /etc/redis/redis.conf /etc/redis/redis.conf.bak

# Configurar Redis
cat >> /etc/redis/redis.conf << 'REDIS_CONF'

# Configurações customizadas
bind 127.0.0.1
requirepass CHANGE_THIS_PASSWORD
maxmemory 4gb
maxmemory-policy allkeys-lru
REDIS_CONF

# Reiniciar Redis
systemctl restart redis-server
systemctl enable redis-server
EOF
echo "✅ Redis configurado"
echo ""

# Criar serviços systemd
echo "🔧 Criando serviços systemd..."
ssh root@$SERVER_IP << 'EOF'
# Master service
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

# Worker service
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
echo "⚠️  PRÓXIMOS PASSOS:"
echo ""
echo "1. Configure Wit.ai:"
echo "   - Crie 20 apps em https://wit.ai"
echo "   - Copie as Server Access Tokens"
echo ""
echo "2. Configure o servidor:"
echo "   ssh root@$SERVER_IP"
echo "   nano /root/.env"
echo ""
echo "   Adicione:"
echo "   REDIS_HOST=127.0.0.1"
echo "   REDIS_PORT=6379"
echo "   REDIS_PASSWORD=CHANGE_THIS_PASSWORD"
echo "   NODE_NAME=main-server"
echo "   WORKERS_PER_NODE=15"
echo "   WIT_API_KEYS=key1,key2,key3,...,key20"
echo "   PORT=5000"
echo ""
echo "3. Inicie os serviços:"
echo "   systemctl start cluster-master"
echo "   systemctl start cluster-worker"
echo ""
echo "4. Verifique status:"
echo "   systemctl status cluster-master"
echo "   systemctl status cluster-worker"
echo ""
echo "5. Teste:"
echo "   curl http://$SERVER_IP:5000/health"
echo "   curl http://$SERVER_IP:5000/api/workers"
echo ""
echo "6. Monitore:"
echo "   export MASTER_URL=http://$SERVER_IP:5000"
echo "   python cluster_monitor.py"
echo ""
echo "=========================================="

