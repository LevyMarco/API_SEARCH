#!/bin/bash
# Script de Deploy Automatizado do Cluster
# Uso: ./deploy.sh [master|worker|redis] <IP>

set -e

COMPONENT=$1
IP=$2

if [ -z "$COMPONENT" ] || [ -z "$IP" ]; then
    echo "Uso: ./deploy.sh [master|worker|redis] <IP>"
    echo ""
    echo "Exemplos:"
    echo "  ./deploy.sh redis 192.168.1.10"
    echo "  ./deploy.sh master 192.168.1.11"
    echo "  ./deploy.sh worker 192.168.1.12"
    exit 1
fi

echo "=========================================="
echo "🚀 Deploy do Cluster - $COMPONENT"
echo "=========================================="
echo "IP: $IP"
echo ""

case $COMPONENT in
    redis)
        echo "📦 Instalando Redis Server..."
        ssh root@$IP << 'EOF'
apt-get update && apt-get upgrade -y
apt-get install -y redis-server
systemctl enable redis-server
echo "✅ Redis instalado!"
EOF
        echo ""
        echo "⚠️  Configure manualmente:"
        echo "  1. Edite /etc/redis/redis.conf"
        echo "  2. Mude 'bind' para 0.0.0.0"
        echo "  3. Adicione 'requirepass YOUR_PASSWORD'"
        echo "  4. Reinicie: systemctl restart redis-server"
        ;;
    
    master)
        echo "📦 Instalando Master Node..."
        
        # Upload arquivos
        echo "📤 Uploading arquivos..."
        scp cluster_master.py root@$IP:/root/
        scp cluster_monitor.py root@$IP:/root/
        
        # Instalar dependências
        ssh root@$IP << 'EOF'
apt-get update && apt-get upgrade -y
apt-get install -y python3.11 python3-pip
pip3 install redis flask flask-cors
EOF
        
        echo ""
        echo "✅ Master Node instalado!"
        echo ""
        echo "⚠️  Configure manualmente:"
        echo "  1. Crie /root/.env com:"
        echo "     REDIS_HOST=<REDIS_IP>"
        echo "     REDIS_PORT=6379"
        echo "     REDIS_PASSWORD=<PASSWORD>"
        echo "  2. Crie serviço systemd (veja CLUSTER_DEPLOY.md)"
        echo "  3. Inicie: systemctl start cluster-master"
        ;;
    
    worker)
        echo "📦 Instalando Worker Node..."
        
        # Upload arquivos
        echo "📤 Uploading arquivos..."
        scp cluster_worker.py root@$IP:/root/
        scp captcha_solver_free.py root@$IP:/root/
        
        # Instalar dependências
        ssh root@$IP << 'EOF'
apt-get update && apt-get upgrade -y
apt-get install -y python3.11 python3-pip wget gnupg

# Instalar Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

# Instalar dependências Python
pip3 install redis selenium undetected-chromedriver requests
EOF
        
        echo ""
        echo "✅ Worker Node instalado!"
        echo ""
        echo "⚠️  Configure manualmente:"
        echo "  1. Crie /root/.env com:"
        echo "     REDIS_HOST=<REDIS_IP>"
        echo "     REDIS_PORT=6379"
        echo "     REDIS_PASSWORD=<PASSWORD>"
        echo "     NODE_NAME=worker-node-X"
        echo "     WORKERS_PER_NODE=10"
        echo "     WIT_API_KEYS=key1,key2,..."
        echo "  2. Crie serviço systemd (veja CLUSTER_DEPLOY.md)"
        echo "  3. Inicie: systemctl start cluster-worker"
        ;;
    
    *)
        echo "❌ Componente inválido: $COMPONENT"
        echo "Use: redis, master ou worker"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ Deploy concluído!"
echo "=========================================="

