#!/bin/bash
# Instalação Completa do Cluster
set -e

echo "=========================================="
echo "🚀 Instalação Completa - Cluster Scraper"
echo "=========================================="
echo ""

# Verificar se é root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Execute com sudo:"
    echo "   sudo bash install_all.sh"
    exit 1
fi

# Diretório de trabalho
WORK_DIR="/www/wwwroot/sistemas/search_API/scraper_windows"
cd "$WORK_DIR"

echo "📍 Diretório: $WORK_DIR"
echo ""

# 1. Instalar dependências do sistema
echo "📦 Instalando dependências do sistema..."
apt-get update > /dev/null 2>&1
apt-get install -y redis-server python3-pip > /dev/null 2>&1
echo "✅ Dependências do sistema instaladas"
echo ""

# 2. Instalar Chrome
echo "📦 Instalando Chrome..."
if ! command -v google-chrome &> /dev/null; then
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - > /dev/null 2>&1
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
    apt-get update > /dev/null 2>&1
    apt-get install -y google-chrome-stable > /dev/null 2>&1
    echo "✅ Chrome instalado"
else
    echo "✅ Chrome já instalado"
fi
echo ""

# 3. Instalar dependências Python
echo "📦 Instalando dependências Python..."
pip3 install --break-system-packages redis flask flask-cors selenium undetected-chromedriver requests > /dev/null 2>&1
echo "✅ Dependências Python instaladas"
echo ""

# 4. Configurar Redis
echo "⚙️  Configurando Redis..."
if ! grep -q "requirepass SenhaForte123" /etc/redis/redis.conf; then
    cat >> /etc/redis/redis.conf << 'EOF'

# Configurações customizadas
bind 127.0.0.1
requirepass SenhaForte123
maxmemory 8gb
maxmemory-policy allkeys-lru
EOF
    echo "✅ Redis configurado"
else
    echo "✅ Redis já configurado"
fi

systemctl restart redis-server
systemctl enable redis-server > /dev/null 2>&1
echo ""

# 5. Criar serviço Master
echo "🔧 Criando serviço Master..."
cat > /etc/systemd/system/cluster-master.service << 'EOF'
[Unit]
Description=Cluster Master
After=network.target redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/sistemas/search_API/scraper_windows
Environment="REDIS_HOST=127.0.0.1"
Environment="REDIS_PORT=6379"
Environment="REDIS_PASSWORD=SenhaForte123"
Environment="NODE_NAME=main-server"
Environment="WORKERS_PER_NODE=15"
Environment="WIT_API_KEYS=7LPNWKPEIGHO5EO3OYT7I222VXPYOZVZ,I4M45EQRQPPWWCSUIGWCNEABKOWOD6YO,BV5H5XSCLC7JZHN27FKUFEXFS5XOQLHH,QOFWBTM443P2FGWMSVQQWGGF3XFIUJQH,RJHVVYK4D2U3XQ25E73JBO4HNIOTNRSC,ZMFDKVZGDUQHW5CGNK5TS57V27PEAJF3,B26GRSCYU3IZV2TSBM6CHKRPLEHTTFIL,OMHM5MIQRVA5UZZNSW2L7NNZHXXXZTRF,ZJ3J6KTHXLMD6KXVJQKRAD4VLE5XCH3Y,ZJ3J6KTHXLMD6KXVJQKRAD4VLE5XCH3Y,HFM5IG66PGOIRORXQBR3KQ3AAXYVAJGB,KKMUC37GSFI4YQ4OPSDOVCCVOMHNCPMV,SABXNLRDEYA5DSDJKKF6PDXH3M7NTVC2,PILLPCBG2HI5I55RXCBTPJBOEOIKJFZA,IVHLXSJ2EBJAMS7PV7WFABPASFHTPA6V,QJWBFN2RQSEH3RXFY2HOMOMWRU74JGG4,SHMPRRVNKWJOFYBBI2H5AASSJZ5LNJXS,QXRFBVPFXYMHY7XGKST3WAE2JEXEQXZ3,TLVWLIZQHWVX4WCWPO3XO3KVZQFBP3QC,NRRIZLRIB2RHN5THI2BBLDVM6FQH73W3"
Environment="PORT=5000"
ExecStart=/usr/bin/python3 cluster_master.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
echo "✅ Serviço Master criado"
echo ""

# 6. Criar serviço Worker
echo "🔧 Criando serviço Worker..."
cat > /etc/systemd/system/cluster-worker.service << 'EOF'
[Unit]
Description=Cluster Worker
After=network.target redis-server.service cluster-master.service

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/sistemas/search_API/scraper_windows
Environment="REDIS_HOST=127.0.0.1"
Environment="REDIS_PORT=6379"
Environment="REDIS_PASSWORD=SenhaForte123"
Environment="NODE_NAME=main-server"
Environment="WORKERS_PER_NODE=15"
Environment="WIT_API_KEYS=7LPNWKPEIGHO5EO3OYT7I222VXPYOZVZ,I4M45EQRQPPWWCSUIGWCNEABKOWOD6YO,BV5H5XSCLC7JZHN27FKUFEXFS5XOQLHH,QOFWBTM443P2FGWMSVQQWGGF3XFIUJQH,RJHVVYK4D2U3XQ25E73JBO4HNIOTNRSC,ZMFDKVZGDUQHW5CGNK5TS57V27PEAJF3,B26GRSCYU3IZV2TSBM6CHKRPLEHTTFIL,OMHM5MIQRVA5UZZNSW2L7NNZHXXXZTRF,ZJ3J6KTHXLMD6KXVJQKRAD4VLE5XCH3Y,ZJ3J6KTHXLMD6KXVJQKRAD4VLE5XCH3Y,HFM5IG66PGOIRORXQBR3KQ3AAXYVAJGB,KKMUC37GSFI4YQ4OPSDOVCCVOMHNCPMV,SABXNLRDEYA5DSDJKKF6PDXH3M7NTVC2,PILLPCBG2HI5I55RXCBTPJBOEOIKJFZA,IVHLXSJ2EBJAMS7PV7WFABPASFHTPA6V,QJWBFN2RQSEH3RXFY2HOMOMWRU74JGG4,SHMPRRVNKWJOFYBBI2H5AASSJZ5LNJXS,QXRFBVPFXYMHY7XGKST3WAE2JEXEQXZ3,TLVWLIZQHWVX4WCWPO3XO3KVZQFBP3QC,NRRIZLRIB2RHN5THI2BBLDVM6FQH73W3"
Environment="PORT=5000"
ExecStart=/usr/bin/python3 cluster_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
echo "✅ Serviço Worker criado"
echo ""

# 7. Recarregar systemd
echo "🔄 Recarregando systemd..."
systemctl daemon-reload
echo "✅ Systemd recarregado"
echo ""

# 8. Habilitar e iniciar serviços
echo "🚀 Iniciando serviços..."
systemctl enable cluster-master cluster-worker > /dev/null 2>&1
systemctl restart cluster-master
sleep 3
systemctl restart cluster-worker
sleep 5
echo "✅ Serviços iniciados"
echo ""

# 9. Verificar status
echo "=========================================="
echo "✅ Instalação Concluída!"
echo "=========================================="
echo ""
echo "📊 Status dos Serviços:"
echo ""
systemctl status cluster-master --no-pager -l | head -5
echo ""
systemctl status cluster-worker --no-pager -l | head -5
echo ""
echo "=========================================="
echo "🧪 Testando API..."
echo ""
sleep 2
curl -s http://localhost:5000/health | python3 -m json.tool || echo "❌ API não respondeu"
echo ""
echo "=========================================="
echo "📋 Comandos Úteis:"
echo ""
echo "  Ver logs Master:  sudo journalctl -u cluster-master -f"
echo "  Ver logs Worker:  sudo journalctl -u cluster-worker -f"
echo "  Reiniciar:        sudo systemctl restart cluster-master cluster-worker"
echo "  Status:           sudo systemctl status cluster-master cluster-worker"
echo "  Testar API:       curl http://localhost:5000/health"
echo ""
echo "=========================================="
