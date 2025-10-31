"""
Script de debug para identificar seletores corretos
"""
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def debug_google_maps():
    """Debug dos seletores do Google Maps"""
    print("="*70)
    print("🔍 Debug de Seletores - Google Maps")
    print("="*70)
    
    # Inicializa Chrome
    print("\n1. Inicializando Chrome...")
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options, use_subprocess=True)
    print("✅ Chrome inicializado")
    
    # Acessa Google Maps
    query = "restaurante"
    location = "São Paulo"
    search_query = f"{query} {location}"
    url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
    
    print(f"\n2. Acessando: {url}")
    driver.get(url)
    print("✅ Página carregada")
    
    # Aguarda
    print("\n3. Aguardando 10 segundos...")
    time.sleep(10)
    
    # Testa diferentes seletores
    print("\n4. Testando seletores:")
    print("-" * 70)
    
    selectors = [
        ('div[role="article"]', 'Artigos com role'),
        ('div[role="feed"]', 'Feed principal'),
        ('a[href*="/maps/place/"]', 'Links de lugares'),
        ('div.Nv2PK', 'Classe Nv2PK'),
        ('div[jsaction]', 'Divs com jsaction'),
        ('div[data-result-index]', 'Divs com data-result-index'),
        ('a[aria-label]', 'Links com aria-label'),
        ('div.hfpxzc', 'Classe hfpxzc'),
        ('a.hfpxzc', 'Link classe hfpxzc'),
    ]
    
    for selector, description in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"✅ {description:30} -> {len(elements):3} elementos")
            
            # Mostra primeiros 3 elementos
            if len(elements) > 0:
                for i, elem in enumerate(elements[:3], 1):
                    try:
                        text = elem.text[:80] if elem.text else "(sem texto)"
                        aria = elem.get_attribute('aria-label')
                        if aria:
                            print(f"   [{i}] aria-label: {aria[:60]}")
                        else:
                            print(f"   [{i}] texto: {text}")
                    except:
                        print(f"   [{i}] (erro ao ler)")
                print()
        except Exception as e:
            print(f"❌ {description:30} -> Erro: {e}")
    
    print("-" * 70)
    
    # Salva HTML para análise
    print("\n5. Salvando HTML da página...")
    html = driver.page_source
    with open('/home/ubuntu/scraper_windows/debug_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML salvo em: /home/ubuntu/scraper_windows/debug_page.html")
    print(f"   Tamanho: {len(html)} bytes")
    
    # Screenshot
    print("\n6. Tirando screenshot...")
    driver.save_screenshot('/home/ubuntu/scraper_windows/debug_screenshot.png')
    print("✅ Screenshot salvo em: /home/ubuntu/scraper_windows/debug_screenshot.png")
    
    # Fecha
    driver.quit()
    print("\n✅ Debug concluído!")

if __name__ == '__main__':
    try:
        debug_google_maps()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

