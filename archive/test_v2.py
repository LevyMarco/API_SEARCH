"""
Teste da versão 2 - Google Search Normal
"""
import sys
import json
from worker_pool_v2 import SeleniumWorker

def test_google_search():
    """Testa busca no Google Search normal"""
    print("="*70)
    print("🧪 Teste V2 - Google Search Normal com Simulação Humana")
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
    print("   (Isso pode levar 15-30 segundos com simulação humana...)")
    result = worker.search(query="restaurante", location="São Paulo")
    
    # Fecha worker
    worker.close()
    
    # Analisa resultado
    print("\n3. Resultado da busca:")
    print("-" * 70)
    print(f"Status: {result.get('status')}")
    print(f"Tempo: {result.get('search_metadata', {}).get('total_time_taken')}s")
    print(f"Método: {result.get('search_metadata', {}).get('method')}")
    
    if result.get('status') != 'success':
        print(f"❌ Erro: {result.get('error')}")
        return False
    
    places = result.get('local_results', {}).get('places', [])
    print(f"Total de lugares: {len(places)}")
    print("-" * 70)
    
    if len(places) == 0:
        print("❌ Nenhum lugar encontrado")
        return False
    
    # Mostra resultados
    print("\n4. Lugares encontrados:")
    print("=" * 70)
    
    for place in places[:10]:
        pos = place.get('position', '?')
        title = place.get('title', 'N/A')
        rating = place.get('rating', 'N/A')
        reviews = place.get('reviews', 'N/A')
        address = place.get('address', 'N/A')
        phone = place.get('phone', 'N/A')
        place_type = place.get('type', 'N/A')
        
        print(f"\n#{pos} - {title}")
        print(f"   ⭐ Rating: {rating} ({reviews} avaliações)")
        print(f"   📍 Endereço: {address}")
        print(f"   📞 Telefone: {phone}")
        print(f"   🏷️  Tipo: {place_type}")
    
    print("=" * 70)
    
    # Salva resultado completo
    print("\n5. Salvando resultado completo...")
    with open('/home/ubuntu/scraper_windows/test_v2_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("✅ Salvo em: /home/ubuntu/scraper_windows/test_v2_result.json")
    
    # Validação
    print("\n6. Validação:")
    positions_ok = all(place.get('position') == i for i, place in enumerate(places, 1))
    
    if positions_ok:
        print(f"✅ Posições corretas (1 a {len(places)})")
    else:
        print("❌ Posições incorretas")
    
    if len(places) >= 3:
        print(f"✅ Quantidade adequada ({len(places)} lugares)")
        return True
    else:
        print(f"⚠️  Poucos resultados ({len(places)} lugares)")
        return False

if __name__ == '__main__':
    try:
        success = test_google_search()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

