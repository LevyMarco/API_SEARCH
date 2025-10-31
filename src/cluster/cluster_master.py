#!/usr/bin/env python3
"""
Cluster Master Node - Coordenador Central
Distribui tarefas via Redis e coleta resultados
"""

import os
import sys
import json
import time
import redis
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# Carregar variáveis de ambiente com caminho absoluto
load_dotenv('/www/wwwroot/sistemas/search_API/scraper_windows/.env')

# Configuração
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
PORT = int(os.getenv('PORT', 5000))

# Conectar ao Redis
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# Flask App
app = Flask(__name__)
CORS(app)

# Estatísticas
stats = {
    'total_requests': 0,
    'successful': 0,
    'failed': 0,
    'cache_hits': 0,
    'captchas_solved': 0
}

# ---------------------- Helpers de cache/params ---------------------- #
def _normalize_limit(limit_raw) -> int:
    try:
        n = int(limit_raw)
    except Exception:
        n = 10
    return max(1, min(50, n))  # 1..50

def generate_cache_key(query: str, location: str, limit: int) -> str:
    """Chave de cache inclui limit para não misturar respostas."""
    key_string = f"{query}:{location}:{limit}"
    return f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"

def get_cached_result(query: str, location: str, limit: int):
    """Buscar resultado em cache"""
    cache_key = generate_cache_key(query, location, limit)
    cached = redis_client.get(cache_key)
    if cached:
        stats['cache_hits'] += 1
        return json.loads(cached)
    return None

def set_cached_result(query: str, location: str, limit: int, result: dict, ttl: int = 86400):
    """Salvar resultado em cache (padrão: 24h)"""
    cache_key = generate_cache_key(query, location, limit)
    redis_client.setex(cache_key, ttl, json.dumps(result))


# ---------------------- Endpoints ---------------------- #
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        redis_client.ping()
        return jsonify({
            'status': 'healthy',
            'service': 'master-node',
            'redis': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/api/workers', methods=['GET'])
def get_workers():
    """
    Lista workers ativos usando o TTL da chave de heartbeat:
      - padrão de chave: worker:{node}:{worker-N}:heartbeat
      - ativo se TTL > 0
    """
    try:
        workers = []
        for key in redis_client.scan_iter("worker:*:heartbeat"):
            parts = key.split(':')
            # id legível (node:worker-N)
            worker_id = ':'.join(parts[1:-1]) if len(parts) >= 3 else key
            last_heartbeat = redis_client.get(key)
            ttl = redis_client.ttl(key)  # segundos (-2=nao existe, -1=sem ttl)
            is_active = True if ttl and ttl > 0 else False
            workers.append({
                'id': worker_id,
                'last_seen': last_heartbeat,
                'ttl_seconds': ttl,
                'active': is_active
            })

        active_workers = [w for w in workers if w['active']]
        return jsonify({'total_workers': len(active_workers), 'workers': active_workers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['GET'])
def search():
    """Endpoint principal de busca"""
    try:
        query = request.args.get('query')
        location = request.args.get('location')
        limit = _normalize_limit(request.args.get('limit', 10))
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'

        if not query or not location:
            return jsonify({'error': 'Missing required parameters: query and location'}), 400

        stats['total_requests'] += 1

        # Cache
        if use_cache:
            cached_result = get_cached_result(query, location, limit)
            if cached_result:
                cached_result['from_cache'] = True
                return jsonify(cached_result)

        # Criar tarefa e enfileirar
        task_id = f"task:{int(time.time() * 1000)}"
        redis_client.lpush('scraper:tasks', json.dumps({
            'id': task_id,
            'query': query,
            'location': location,
            'limit': limit
        }))

        # Aguardar resultado (timeout: 120s)
        timeout = 120
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = redis_client.get(f"scraper:result:{task_id}")
            if result:
                result_data = json.loads(result)
                # Limpar resultado do Redis
                redis_client.delete(f"scraper:result:{task_id}")

                # Atualizar stats e cache
                if result_data.get('status') == 'success':
                    stats['successful'] += 1
                    if result_data.get('search_metadata', {}).get('captchas_solved', 0) > 0:
                        stats['captchas_solved'] += result_data['search_metadata']['captchas_solved']
                    set_cached_result(query, location, limit, result_data)
                else:
                    stats['failed'] += 1

                result_data['from_cache'] = False
                return jsonify(result_data)

            time.sleep(1)

        # Timeout
        stats['failed'] += 1
        return jsonify({'status': 'error', 'error': 'Request timeout - no worker available'}), 504

    except Exception as e:
        stats['failed'] += 1
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Estatísticas do cluster (workers ativos via TTL)"""
    try:
        active_workers = 0
        for key in redis_client.scan_iter("worker:*:heartbeat"):
            ttl = redis_client.ttl(key)
            if ttl and ttl > 0:
                active_workers += 1

        queue_size = redis_client.llen('scraper:tasks')
        return jsonify({'active_workers': active_workers, 'queue_size': queue_size, 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Limpar cache"""
    try:
        deleted = 0
        for key in redis_client.scan_iter("cache:*"):
            redis_client.delete(key)
            deleted += 1
        return jsonify({'status': 'success', 'deleted_keys': deleted})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 80)
    print("🚀 CLUSTER MASTER NODE")
    print("=" * 80)
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"Port: {PORT}")
    print("=" * 80)

    try:
        redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        sys.exit(1)

    print("\n🎯 Starting Flask server...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
