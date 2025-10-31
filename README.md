# Google Local Search API - Cluster com WitAI CAPTCHA Solver

API distribuída para busca local no Google com resolução automática de CAPTCHA usando **Wit.ai (gratuito)**.

## 🏗️ Arquitetura

Master Node (Redis)
    ↓
[Worker 1] [Worker 2] ... [Worker 20]
    ↓
Chrome + Wit.ai CAPTCHA Solver
    ↓
Google Search (local)
    ↓
Extração de dados

## 📂 Estrutura do Projeto

src/
├── workers/
│   └── worker_pool_v3.py         # Pool de workers com Wit.ai
├── solvers/
│   └── captcha_solver_free.py    # Resolver WitAI (70-80% sucesso)
├── cluster/
│   ├── cluster_master.py         # Coordenador central
│   ├── cluster_worker.py         # Worker node
│   └── cluster_monitor.py        # Dashboard de monitoramento

configs/
├── .env.example                   # Template de configuração
└── README.md                      # Instruções de setup

deploy/
├── deploy_agora.sh
├── deploy_single_server.sh
└── install_all.sh

## 🚀 Instalação

### 1. Clonar e instalar dependências

git clone https://github.com/LevyMarco/API_SEARCH.git
cd API_SEARCH
pip install -r requirements.txt

### 2. Configurar variáveis de ambiente

cp configs/.env.example .env

Editar .env com:
REDIS_HOST=localhost
REDIS_PORT=6379
WORKER_ID=1
NODE_NAME=worker-1
WIT_API_KEYS=sua_chave_aqui

### 3. Adicionar chaves Wit.ai

mkdir -p configs

**Como obter chaves grátis:**
1. Acesse https://wit.ai
2. Faça login com Facebook/GitHub
3. Crie um novo app
4. Copie o "Server Access Token"

## 🔄 Fluxo de Operação

### Master Node
python3 src/cluster/cluster_master.py
- Recebe requisições HTTP
- Distribui tarefas via Redis
- Coleta e retorna resultados

### Worker Node
python3 src/cluster/cluster_worker.py
- Consome tarefas da fila Redis
- Abre Chrome com Selenium
- Executa busca no Google
- Detecta e resolve CAPTCHA automaticamente com Wit.ai
- Extrai dados (título, rating)
- Publica resultado

### Monitor (Dashboard)
python3 src/cluster/cluster_monitor.py
- Exibe dashboard em tempo real
- Mostra status dos workers
- Monitora heartbeat

## 📊 Dados Extraídos

Cada resultado contém:
{
  "position": 1,
  "title": "Nome do Estabelecimento",
  "rating": 4.8
}

## ⚙️ Variáveis de Ambiente

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=

WORKER_ID=1
NODE_NAME=worker-1

UC_CHROME_BINARY=/usr/bin/google-chrome-stable
CHROME_STARTUP_TIMEOUT=90

WIT_API_KEYS=key1,key2,key3

PAGE_LOAD_TIMEOUT=45
SCROLL_PAUSE=0.4
MAX_SCROLLS=30

DEBUG_DIR=/tmp/scraper_debug
SAVE_DEBUG_ON_EMPTY=1

## 💰 Custos

- **Wit.ai**: GRÁTIS (70-80% sucesso)
- **Google**: GRÁTIS (sem limitação de requisições oficiais)
- **Custo total**: \

## 🔐 Segurança

⚠️ **IMPORTANTE**: Chaves Wit.ai estão em .gitignore. Nunca commitar arquivos com credenciais!

## 📝 Exemplo de Uso

### 1. Iniciar Master

python3 src/cluster/cluster_master.py

### 2. Iniciar Workers (em terminais diferentes)

python3 src/cluster/cluster_worker.py

### 3. Fazer requisição

curl "http://localhost:5000/api/search?query=pizzaria&location=São Paulo&limit=20"

## 🐛 Troubleshooting

**CAPTCHA não está sendo resolvido?**
- Verifique se WIT_API_KEYS está configurado corretamente
- Crie mais chaves no https://wit.ai

**Chrome não inicia?**
- Instale Chrome: sudo apt-get install google-chrome-stable
- Configure UC_CHROME_BINARY: /usr/bin/google-chrome-stable

**Redis não conecta?**
- Verifique se Redis está rodando: redis-cli ping
- Confirme REDIS_HOST e REDIS_PORT

## 📄 Licença

MIT

## 👨‍💻 Autor

LevyMarco
