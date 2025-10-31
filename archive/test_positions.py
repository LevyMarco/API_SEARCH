"""
Script de teste para validar posições corretas
"""
import sys
import time
from worker_pool import SeleniumWorker

def test_positions():
    """Testa se as posições estão corretas"""
    print("="*70)
    print("🧪 Teste de Posições - Google Maps Scraper")
    print("="*70)
    
    # Cria worker
    print("\n1. Inicializando worker...")
    worker = SeleniumWorker(worker_id=1, config={})
    
    if not worker.initialize():
        print("❌ Erro ao inicializar worker")
        return False
    
    print("✅ Worker inicializado")
    
    # Executa busca
    print("\n2. Executando busca: 'restaurante' em 'São Paulo'")
    result = worker.search(query="restaurante", location="São Paulo")
    
    # Fecha worker
    worker.close()
    
    # Analisa resultado
    print("\n3. Analisando resultado...")
    print(f"Status: {result.get('status')}")
    
    if result.get('status') != 'success':
        print(f"❌ Erro: {result.get('error')}")
        return False
    
    places = result.get('local_results', {}).get('places', [])
    print(f"Total de lugares encontrados: {len(places)}")
    
    if len(places) == 0:
        print("❌ Nenhum lugar encontrado")
        return False
    
    # Verifica posições
    print("\n4. Verificando posições:")
    print("-" * 70)
    
    positions_ok = True
    for i, place in enumerate(places[:10], 1):
        position = place.get('position')
        title = place.get('title', 'N/A')[:50]
        rating = place.get('rating', 'N/A')
        reviews = place.get('reviews', 'N/A')
        
        status = "✅" if position == i else "❌"
        print(f"{status} Posição esperada: {i}, Posição retornada: {position}")
        print(f"   Nome: {title}")
        print(f"   Rating: {rating} ({reviews} avaliações)")
        
        if position != i:
            positions_ok = False
    
    print("-" * 70)
    
    # Resultado final
    print("\n5. Resultado:")
    if positions_ok and len(places) >= 10:
        print("✅ TESTE PASSOU! Posições 1-10 estão corretas")
        return True
    elif positions_ok and len(places) < 10:
        print(f"⚠️  Posições corretas, mas apenas {len(places)} resultados encontrados (esperado: 10+)")
        return True
    else:
        print("❌ TESTE FALHOU! Posições incorretas")
        return False

if __name__ == '__main__':
    try:
        success = test_positions()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

