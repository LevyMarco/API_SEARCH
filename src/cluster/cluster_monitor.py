"""
Monitor do Cluster - Dashboard em Tempo Real
Exibe estatísticas e saúde do cluster
"""
import os
import time
import requests
from datetime import datetime
from typing import Dict, Any

MASTER_URL = os.getenv('MASTER_URL', 'http://localhost:5000')
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', 5))


def clear_screen():
    """Limpa a tela"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_timestamp(iso_string: str) -> str:
    """Formata timestamp"""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except:
        return iso_string


def draw_progress_bar(percentage: float, width: int = 30) -> str:
    """Desenha barra de progresso"""
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percentage:.1f}%"


def get_cluster_stats() -> Dict[str, Any]:
    """Pega estatísticas do master"""
    try:
        response = requests.get(f"{MASTER_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        return None


def display_dashboard(stats: Dict[str, Any]):
    """Exibe dashboard"""
    clear_screen()
    
    print("="*80)
    print("🚀 CLUSTER MONITOR - Google Local Scraper".center(80))
    print("="*80)
    print()
    
    if not stats:
        print("❌ Não foi possível conectar ao Master Node")
        print(f"   URL: {MASTER_URL}")
        print()
        print("Verifique se o Master Node está rodando:")
        print(f"   python cluster_master.py")
        return
    
    # Cluster Status
    cluster = stats.get('cluster', {})
    print("📊 CLUSTER STATUS")
    print("-" * 80)
    print(f"  Nodes:           {cluster.get('active_nodes', 0)}/{cluster.get('total_nodes', 0)} online")
    print(f"  Workers:         {cluster.get('total_workers', 0)} total")
    print(f"                   {cluster.get('busy_workers', 0)} busy | {cluster.get('idle_workers', 0)} idle")
    print()
    
    # Nodes detalhados
    nodes = cluster.get('nodes', {})
    if nodes:
        print("🖥️  NODES")
        print("-" * 80)
        for node_name, node_data in nodes.items():
            workers = node_data.get('workers', 0)
            busy = node_data.get('busy_workers', 0)
            searches = node_data.get('total_searches', 0)
            
            utilization = (busy / workers * 100) if workers > 0 else 0
            bar = draw_progress_bar(utilization, width=20)
            
            print(f"  {node_name:20} {bar} {busy}/{workers} workers | {searches} searches")
        print()
    
    # Queue
    queue = stats.get('queue', {})
    pending = queue.get('pending_tasks', 0)
    print("📋 QUEUE")
    print("-" * 80)
    print(f"  Pending tasks:   {pending}")
    print()
    
    # Performance
    perf = stats.get('performance', {})
    total_req = perf.get('total_requests', 0)
    success = perf.get('successful_searches', 0)
    failed = perf.get('failed_searches', 0)
    success_rate = perf.get('success_rate', 0)
    
    cache_hits = perf.get('cache_hits', 0)
    cache_misses = perf.get('cache_misses', 0)
    cache_rate = perf.get('cache_hit_rate', 0)
    
    print("⚡ PERFORMANCE")
    print("-" * 80)
    print(f"  Total requests:  {total_req}")
    print(f"  Successful:      {success}")
    print(f"  Failed:          {failed}")
    print(f"  Success rate:    {draw_progress_bar(success_rate, width=20)}")
    print()
    print(f"  Cache hits:      {cache_hits}")
    print(f"  Cache misses:    {cache_misses}")
    print(f"  Cache hit rate:  {draw_progress_bar(cache_rate, width=20)}")
    print()
    
    # CAPTCHAs
    captchas = stats.get('captchas', {})
    solved = captchas.get('total_solved', 0)
    cost = captchas.get('cost', '$0.00')
    
    print("🔓 CAPTCHAS")
    print("-" * 80)
    print(f"  Total solved:    {solved}")
    print(f"  Cost:            {cost} (FREE!)")
    print()
    
    # Timestamp
    timestamp = stats.get('timestamp', '')
    if timestamp:
        print(f"🕐 Last update: {format_timestamp(timestamp)}")
    
    print("="*80)
    print(f"Refreshing every {REFRESH_INTERVAL}s... Press Ctrl+C to exit")


def main():
    """Loop principal"""
    print("Conectando ao Master Node...")
    print(f"URL: {MASTER_URL}")
    print()
    
    try:
        while True:
            stats = get_cluster_stats()
            display_dashboard(stats)
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n👋 Bye!")


if __name__ == '__main__':
    main()

