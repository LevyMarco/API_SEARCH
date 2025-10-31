"""
Debug V2 - Verifica o que o Google está retornando
"""
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def debug_v2():
    """Debug completo"""
    print("="*70)
    print("🔍 Debug V2 - Verificando resposta do Google")
    print("="*70)
    
    # Inicializa Chrome
    print("\n1. Inicializando Chrome...")
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--lang=pt-BR,pt;q=0.9')
    options.add_argument('--window-size=1920,1080')
    
    prefs = {
        'profile.default_content_setting_values': {
            'notifications': 2,
            'geolocation': 1
        }
    }
    options.add_experimental_option('prefs', prefs)
    
    driver = uc.Chrome(options=options, use_subprocess=True)
    
    # Remove webdriver
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
    })
    
    print("✅ Chrome inicializado")
    
    # Acessa Google
    url = "https://www.google.com/search?q=restaurante+São+Paulo"
    print(f"\n2. Acessando: {url}")
    driver.get(url)
    time.sleep(8)
    
    # Pega título
    print(f"\n3. Título da página: {driver.title}")
    
    # Scroll
    print("\n4. Fazendo scroll...")
    for i in range(5):
        driver.execute_script(f"window.scrollTo(0, {(i+1)*200});")
        time.sleep(0.3)
    
    time.sleep(2)
    
    # Testa seletores
    print("\n5. Testando seletores:")
    print("-" * 70)
    
    selectors = [
        'div.g',
        'div.rllt__details',
        'div[jsname="GZq3Ke"]',
        'div.VkpGBb',
        'div[data-attrid="LocalResults"]',
        'a[href*="maps"]',
        'h3',
        'div#search',
        'div#rso',
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            status = "✅" if len(elements) > 0 else "❌"
            print(f"{status} {selector:40} -> {len(elements):3} elementos")
            
            if len(elements) > 0 and len(elements) <= 3:
                for i, elem in enumerate(elements[:3], 1):
                    text = elem.text[:80].replace('\n', ' ') if elem.text else "(vazio)"
                    print(f"   [{i}] {text}")
        except Exception as e:
            print(f"❌ {selector:40} -> Erro: {e}")
    
    print("-" * 70)
    
    # Salva HTML
    print("\n6. Salvando HTML...")
    html = driver.page_source
    with open('/home/ubuntu/scraper_windows/debug_v2.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML salvo ({len(html)} bytes)")
    
    # Verifica se tem CAPTCHA
    if 'captcha' in html.lower() or 'unusual traffic' in html.lower():
        print("⚠️  DETECTADO: Google está pedindo CAPTCHA!")
    
    # Screenshot
    print("\n7. Tirando screenshot...")
    driver.save_screenshot('/home/ubuntu/scraper_windows/debug_v2.png')
    print("✅ Screenshot salvo")
    
    # Fecha
    driver.quit()
    print("\n✅ Debug concluído!")
    print("\nArquivos gerados:")
    print("  - /home/ubuntu/scraper_windows/debug_v2.html")
    print("  - /home/ubuntu/scraper_windows/debug_v2.png")

if __name__ == '__main__':
    try:
        debug_v2()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

