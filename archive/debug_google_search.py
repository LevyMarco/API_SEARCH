"""
Debug para Google Search Normal (não Maps)
"""
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def debug_google_search():
    """Debug dos seletores do Google Search"""
    print("="*70)
    print("🔍 Debug de Seletores - Google Search Normal")
    print("="*70)
    
    # Inicializa Chrome
    print("\n1. Inicializando Chrome...")
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=pt-BR')
    
    driver = uc.Chrome(options=options, use_subprocess=True)
    print("✅ Chrome inicializado")
    
    # Acessa Google Search (não Maps)
    query = "restaurante"
    location = "São Paulo"
    search_query = f"{query} {location}"
    url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
    
    print(f"\n2. Acessando Google Search: {url}")
    driver.get(url)
    print("✅ Página carregada")
    
    # Aguarda
    print("\n3. Aguardando 8 segundos...")
    time.sleep(8)
    
    # Testa diferentes seletores para resultados locais
    print("\n4. Testando seletores para resultados locais:")
    print("-" * 70)
    
    selectors = [
        # Local Pack / Map Pack
        ('div[data-attrid="LocalResults"]', 'Local Results container'),
        ('div.rllt__details', 'Local result details'),
        ('div.VkpGBb', 'Local result card'),
        ('div[jsname="GZq3Ke"]', 'Local result item'),
        ('div[data-hveid]', 'Divs com data-hveid'),
        ('a[data-cid]', 'Links com data-cid (place ID)'),
        
        # Resultados orgânicos gerais
        ('div.g', 'Resultado orgânico'),
        ('div[data-sokoban-container]', 'Container Sokoban'),
        ('h3', 'Títulos H3'),
        ('a[jsname="UWckNb"]', 'Links principais'),
    ]
    
    for selector, description in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"{'✅' if len(elements) > 0 else '❌'} {description:35} -> {len(elements):3} elementos")
            
            # Mostra primeiros 5 elementos
            if len(elements) > 0:
                for i, elem in enumerate(elements[:5], 1):
                    try:
                        text = elem.text[:100].replace('\n', ' ') if elem.text else "(sem texto)"
                        aria = elem.get_attribute('aria-label')
                        href = elem.get_attribute('href')
                        data_cid = elem.get_attribute('data-cid')
                        
                        info = []
                        if aria:
                            info.append(f"aria: {aria[:50]}")
                        if data_cid:
                            info.append(f"cid: {data_cid}")
                        if href and '/maps/place/' in href:
                            info.append("href: (maps link)")
                        if text and len(text) > 5:
                            info.append(f"texto: {text[:60]}")
                        
                        if info:
                            print(f"   [{i}] {' | '.join(info)}")
                    except:
                        print(f"   [{i}] (erro ao ler)")
                print()
        except Exception as e:
            print(f"❌ {description:35} -> Erro: {e}")
    
    print("-" * 70)
    
    # Salva HTML
    print("\n5. Salvando HTML da página...")
    html = driver.page_source
    with open('/home/ubuntu/scraper_windows/debug_google_search.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML salvo: /home/ubuntu/scraper_windows/debug_google_search.html")
    print(f"   Tamanho: {len(html)} bytes")
    
    # Screenshot
    print("\n6. Tirando screenshot...")
    driver.save_screenshot('/home/ubuntu/scraper_windows/debug_google_search.png')
    print("✅ Screenshot: /home/ubuntu/scraper_windows/debug_google_search.png")
    
    # Fecha
    driver.quit()
    print("\n✅ Debug concluído!")

if __name__ == '__main__':
    try:
        debug_google_search()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

