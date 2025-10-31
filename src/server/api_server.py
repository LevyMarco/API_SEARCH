#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Server para Linux/Windows - Sem Redis, Cache em Memória
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import uuid
import logging
import os
from src.workers.worker_pool_v3 import WorkerPool

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configurações
NUM_WORKERS = int(os.getenv('SELENIUM_WORKERS', 1))
MAX_RESPONSE_TIME = int(os.getenv('MAX_RESPONSE_TIME', 120))

# Cache em memória
cache_memory = {}

# Worker pool
worker_pool = None


def init_worker_pool():
    """Inicializa o pool de workers"""
    global worker_pool

    config = {
        'delay_min': float(os.getenv('RANDOM_DELAY_MIN', 2)),
        'delay_max': float(os.getenv('RANDOM_DELAY_MAX', 5)),

        # repasse caminho do Chrome/Chromium
        'chromium_binary': os.getenv('UC_CHROME_BINARY'),

        # arquivo com várias chaves (uma por linha)
        'captcha_token_file': os.getenv('CAPTCHA_TOKEN_FILE'),

        # fallback de uma chave única (opcional)
        'captcha_api_key': os.getenv('CAPTCHA_API_KEY') or os.getenv('WIT_AI_TOKEN'),

        # outros tunáveis
        'max_retries': int(os.getenv('MAX_RETRIES', 2)),
        'default_limit': int(os.getenv('DEFAULT_LIMIT', 20)),
        'headless': True,
        'enrich_place_ids': True,
    }

    worker_pool = WorkerPool(num_workers=NUM_WORKERS, config=config)
    worker_pool.start()
    logger.info(f"✅ Worker pool iniciado com {worker_pool.get_stats().get('total_workers', 0)} workers")


def get_cache_key(query: str, location: str) -> str:
    """Gera chave única para cache"""
    return f"{query}|{location}".lower().strip()


@app.route('/')
def index():
    """Página inicial"""
    return jsonify({
        'service': 'Google Local Scraper API',
        'version': '3.0',
        'status': 'online',
        'endpoints': {
            'search': '/api/search?query=<query>&location=<location>',
            'stats': '/stats',
            'health': '/health'
        }
    })


@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'cache': 'memory',
        'workers': worker_pool.get_stats() if worker_pool else None
    })


@app.route('/stats')
def stats():
    """Estatísticas do sistema"""
    if not worker_pool:
        return jsonify({'error': 'Worker pool não inicializado'}), 500

    pool_stats = worker_pool.get_stats()

    cache_stats = {
        'total_keys': len(cache_memory),
        'type': 'memory',
        'note': 'Cache em memória (não persiste após reiniciar)'
    }

    return jsonify({
        'worker_pool': pool_stats,
        'cache': cache_stats,
        'config': {
            'num_workers': NUM_WORKERS,
            'max_response_time': MAX_RESPONSE_TIME
        }
    })


@app.route('/api/search')
def search():
    """Endpoint principal de busca"""
    query = request.args.get('query', '').strip()
    location = request.args.get('location', '').strip()
    limit = int(request.args.get('limit', os.getenv('DEFAULT_LIMIT', 20)))

    if not query or not location:
        return jsonify({
            'status': 'error',
            'error': 'Parâmetros "query" e "location" são obrigatórios'
        }), 400

    logger.info(f"🔍 Nova busca: query='{query}', location='{location}', limit={limit}")

    cache_key = get_cache_key(query, location)
    if cache_key in cache_memory:
        logger.info(f"✅ Cache HIT: {query} em {location}")
        result = cache_memory[cache_key].copy()
        result['search_metadata']['from_cache'] = True
        return jsonify(result)

    logger.info(f"❌ Cache MISS: {query} em {location}")

    if not worker_pool:
        return jsonify({
            'status': 'error',
            'error': 'Sistema não inicializado'
        }), 503

    stats_data = worker_pool.get_stats()
    if stats_data['available_workers'] == 0 and stats_data['total_workers'] == 0:
        return jsonify({
            'status': 'error',
            'error': 'Nenhum worker ativo no momento'
        }), 503

    task_id = str(uuid.uuid4())
    worker_pool.submit_task(query, location, task_id, limit=limit)

    logger.info(f"📤 Tarefa submetida: {task_id}")

    start_time = time.time()
    result = worker_pool.get_result(task_id=task_id, timeout=MAX_RESPONSE_TIME)

    if result is None:
        elapsed = time.time() - start_time
        logger.error(f"⏱️  Timeout após {elapsed:.1f}s")
        return jsonify({
            'status': 'timeout',
            'error': f'Busca excedeu tempo limite de {MAX_RESPONSE_TIME}s',
            'elapsed_time': round(elapsed, 2)
        }), 504

    if result.get('status') == 'error':
        logger.error(f"❌ Erro na busca: {result.get('error')}")
        return jsonify(result), 500

    cache_memory[cache_key] = result.copy()
    result['search_metadata']['from_cache'] = False

    logger.info(f"✅ Busca concluída em {result['search_metadata']['total_time_taken']}s")

    return jsonify(result)


def shutdown_handler():
    """Handler para shutdown gracioso"""
    if worker_pool:
        logger.info("Encerrando worker pool...")
        worker_pool.stop()


if __name__ == '__main__':
    import atexit
    import signal

    atexit.register(shutdown_handler)

    try:
        signal.signal(signal.SIGTERM, lambda s, f: shutdown_handler())
        signal.signal(signal.SIGINT, lambda s, f: shutdown_handler())
    except Exception:
        pass

    logger.info("="*70)
    logger.info("🚀 Google Local Scraper API")
    logger.info("="*70)

    init_worker_pool()

    port = int(os.getenv('PORT', 5000))
    logger.info(f"🌐 Servidor iniciando na porta {port}...")
    logger.info(f"📡 Acesse: http://0.0.0.0:{port}")
    logger.info("="*70)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
