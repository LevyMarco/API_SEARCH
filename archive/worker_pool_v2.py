"""
Worker Pool V2 - Google Search Normal com Simulação Humana
"""
import queue
import threading
import time
import random
import logging
import re
from typing import Dict, Any, Optional

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium não instalado. Instale com: pip install selenium undetected-chromedriver")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeleniumWorker:
    """Worker individual com instância Chrome - Google Search Normal"""
    
    def __init__(self, worker_id: int, config: Dict[str, Any]):
        self.worker_id = worker_id
        self.config = config
        self.driver = None
        self.is_busy = False
        self.total_searches = 0
        self.successful_searches = 0
        self.failed_searches = 0
        
    def initialize(self):
        """Inicializa o Chrome"""
        if not SELENIUM_AVAILABLE:
            logger.error(f"Worker {self.worker_id}: Selenium não disponível")
            return False
            
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument(f'--user-agent={self._get_random_user_agent()}')
            options.add_argument('--lang=pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7')
            options.add_argument('--window-size=1920,1080')
            
            # Preferências para parecer mais humano
            prefs = {
                'profile.default_content_setting_values': {
                    'notifications': 2,
                    'geolocation': 1
                }
            }
            options.add_experimental_option('prefs', prefs)
            
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            
            # Remove propriedades de webdriver
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })
            
            logger.info(f"Worker {self.worker_id}: Chrome inicializado")
            return True
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro ao inicializar: {e}")
            return False
    
    def _get_random_user_agent(self) -> str:
        """Retorna user-agent aleatório"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        return random.choice(user_agents)
    
    def _simulate_human_behavior(self):
        """Simula comportamento humano"""
        try:
            # Movimento aleatório do mouse
            actions = ActionChains(self.driver)
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                actions.move_by_offset(x, y)
            actions.perform()
            
            time.sleep(random.uniform(0.5, 1.5))
        except:
            pass
    
    def _human_scroll(self):
        """Scroll natural como humano"""
        try:
            # Scroll em etapas pequenas
            current_position = 0
            target_position = random.randint(400, 800)
            
            while current_position < target_position:
                scroll_step = random.randint(50, 150)
                current_position += scroll_step
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(random.uniform(0.1, 0.3))
            
            time.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            logger.warning(f"Worker {self.worker_id}: Erro ao fazer scroll: {e}")
    
    def search(self, query: str, location: str, max_retries: int = 2) -> Dict[str, Any]:
        """Executa busca"""
        self.is_busy = True
        self.total_searches += 1
        
        for attempt in range(max_retries):
            try:
                result = self._perform_search(query, location)
                self.successful_searches += 1
                self.is_busy = False
                return result
            except Exception as e:
                logger.warning(f"Worker {self.worker_id}: Tentativa {attempt + 1} falhou: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 6))
                else:
                    self.failed_searches += 1
                    self.is_busy = False
                    return {
                        'status': 'error',
                        'error': str(e),
                        'worker_id': self.worker_id
                    }
    
    def _perform_search(self, query: str, location: str) -> Dict[str, Any]:
        """Realiza a busca no Google Search Normal"""
        start_time = time.time()
        
        # Monta query de busca
        search_query = f"{query} {location}"
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        
        logger.info(f"Worker {self.worker_id}: Acessando {url}")
        self.driver.get(url)
        
        # Aguarda carregamento inicial
        time.sleep(random.uniform(3, 5))
        
        # Simula comportamento humano
        self._simulate_human_behavior()
        
        # Scroll suave
        self._human_scroll()
        
        # Aguarda um pouco mais
        time.sleep(random.uniform(1, 2))
        
        # Extrai resultados
        places = self._extract_local_results()
        
        elapsed_time = time.time() - start_time
        
        return {
            'status': 'success',
            'search_metadata': {
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                'total_time_taken': round(elapsed_time, 2),
                'method': 'Google Search (Human Simulation)',
                'worker_id': self.worker_id,
                'from_cache': False
            },
            'search_parameters': {
                'engine': 'google_local',
                'q': search_query,
                'location_requested': location
            },
            'local_results': {
                'places': places
            }
        }
    
    def _extract_local_results(self) -> list:
        """Extrai resultados locais do Google Search"""
        places = []
        
        try:
            # Estratégia 1: Local Pack (caixa de resultados locais)
            logger.info(f"Worker {self.worker_id}: Procurando Local Pack...")
            
            # Tenta diferentes seletores para o Local Pack
            selectors = [
                'div.rllt__details',  # Detalhes de resultado local
                'div[jsname="GZq3Ke"]',  # Container de resultado local
                'div.VkpGBb',  # Card de resultado local
                'div[data-attrid="LocalResults"] div.rllt__details',  # Específico do Local Results
            ]
            
            local_elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) > 0:
                        logger.info(f"Worker {self.worker_id}: Encontrados {len(elements)} elementos com '{selector}'")
                        local_elements = elements
                        break
                except:
                    continue
            
            # Se não encontrou Local Pack, tenta resultados orgânicos com informações locais
            if len(local_elements) == 0:
                logger.info(f"Worker {self.worker_id}: Local Pack não encontrado, tentando resultados orgânicos...")
                local_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.g')
            
            logger.info(f"Worker {self.worker_id}: Total de elementos para processar: {len(local_elements)}")
            
            position = 1
            for idx, element in enumerate(local_elements[:30], 1):
                try:
                    place_data = self._extract_place_data(element, position)
                    
                    if place_data and place_data.get('title'):
                        places.append(place_data)
                        logger.debug(f"Worker {self.worker_id}: Extraído #{position}: {place_data['title'][:50]}")
                        position += 1
                        
                        if position > 20:
                            break
                            
                except Exception as e:
                    logger.debug(f"Worker {self.worker_id}: Erro ao extrair elemento {idx}: {e}")
                    continue
            
            logger.info(f"Worker {self.worker_id}: Total extraído: {len(places)} lugares")
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro geral na extração: {e}")
        
        return places
    
    def _extract_place_data(self, element, position: int) -> Optional[Dict[str, Any]]:
        """Extrai dados de um elemento de lugar"""
        place_data = {'position': position}
        
        try:
            # Tenta pegar o texto completo do elemento
            full_text = element.text
            
            if not full_text or len(full_text) < 5:
                return None
            
            # Nome/Título
            try:
                # Tenta link com aria-label primeiro
                link = element.find_element(By.CSS_SELECTOR, 'a[aria-label]')
                title = link.get_attribute('aria-label')
                place_data['title'] = title
                
                # Pega o link
                href = link.get_attribute('href')
                place_data['link'] = href
                
                # Extrai place_id se for link do Maps
                if href and '/maps/place/' in href:
                    try:
                        place_id = href.split('/maps/place/')[1].split('/')[0]
                        place_data['place_id'] = place_id
                    except:
                        place_data['place_id'] = None
                        
            except:
                # Tenta H3 ou span com o nome
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, 'h3, span[role="heading"]')
                    place_data['title'] = title_elem.text
                except:
                    # Usa primeira linha do texto
                    lines = full_text.split('\n')
                    place_data['title'] = lines[0] if lines else None
            
            if not place_data.get('title'):
                return None
            
            # Rating e Reviews usando regex no texto completo
            try:
                # Padrão: 4.5(1,234) ou 4.5 (1234) ou 4,5(1.234)
                rating_pattern = r'(\d+[.,]\d+)\s*\(?([\d.,]+)\)?'
                match = re.search(rating_pattern, full_text)
                if match:
                    rating_str = match.group(1).replace(',', '.')
                    place_data['rating'] = float(rating_str)
                    
                    reviews_str = match.group(2).replace('.', '').replace(',', '')
                    place_data['reviews'] = int(reviews_str)
                else:
                    place_data['rating'] = None
                    place_data['reviews'] = None
            except:
                place_data['rating'] = None
                place_data['reviews'] = None
            
            # Endereço (geralmente tem vírgula ou número)
            try:
                address_pattern = r'(?:Rua|Av\.|Avenida|R\.|Alameda)[^·\n]+'
                match = re.search(address_pattern, full_text, re.IGNORECASE)
                if match:
                    place_data['address'] = match.group(0).strip()
                else:
                    place_data['address'] = None
            except:
                place_data['address'] = None
            
            # Telefone
            try:
                phone_pattern = r'\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}'
                match = re.search(phone_pattern, full_text)
                if match:
                    place_data['phone'] = match.group(0)
                else:
                    place_data['phone'] = None
            except:
                place_data['phone'] = None
            
            # Tipo/Categoria (palavras antes do endereço)
            try:
                lines = full_text.split('\n')
                for line in lines[1:4]:  # Pula o título
                    if len(line) > 3 and len(line) < 50 and not re.search(r'\d', line):
                        place_data['type'] = line.strip()
                        break
                else:
                    place_data['type'] = None
            except:
                place_data['type'] = None
            
            return place_data
            
        except Exception as e:
            logger.debug(f"Worker {self.worker_id}: Erro ao extrair dados: {e}")
            return None
    
    def close(self):
        """Fecha o Chrome"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"Worker {self.worker_id}: Chrome fechado")
            except:
                pass


class WorkerPool:
    """Pool de workers"""
    
    def __init__(self, num_workers: int = 5, config: Optional[Dict[str, Any]] = None):
        self.num_workers = num_workers
        self.config = config or {}
        self.workers = []
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = False
        self.lock = threading.Lock()
        
        logger.info(f"Inicializando pool com {num_workers} workers...")
        
    def start(self):
        """Inicia o pool"""
        self.is_running = True
        
        for i in range(self.num_workers):
            worker = SeleniumWorker(i + 1, self.config)
            if worker.initialize():
                self.workers.append(worker)
                thread = threading.Thread(target=self._worker_loop, args=(worker,), daemon=True)
                thread.start()
            else:
                logger.error(f"Falha ao inicializar worker {i + 1}")
        
        logger.info(f"Pool iniciado com {len(self.workers)} workers ativos")
    
    def _worker_loop(self, worker: SeleniumWorker):
        """Loop do worker"""
        while self.is_running:
            try:
                task = self.task_queue.get(timeout=1)
                
                if task is None:
                    break
                
                query = task['query']
                location = task['location']
                task_id = task['id']
                
                result = worker.search(query, location)
                result['task_id'] = task_id
                
                self.result_queue.put(result)
                self.task_queue.task_done()
                
                delay = random.uniform(
                    self.config.get('delay_min', 3),
                    self.config.get('delay_max', 7)
                )
                time.sleep(delay)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker.worker_id}: Erro no loop: {e}")
    
    def submit_task(self, query: str, location: str, task_id: str) -> None:
        """Adiciona tarefa"""
        task = {
            'id': task_id,
            'query': query,
            'location': location
        }
        self.task_queue.put(task)
    
    def get_result(self, timeout: float = 120) -> Optional[Dict[str, Any]]:
        """Pega resultado"""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas"""
        with self.lock:
            total_searches = sum(w.total_searches for w in self.workers)
            successful = sum(w.successful_searches for w in self.workers)
            failed = sum(w.failed_searches for w in self.workers)
            busy_workers = sum(1 for w in self.workers if w.is_busy)
            
            return {
                'total_workers': len(self.workers),
                'busy_workers': busy_workers,
                'available_workers': len(self.workers) - busy_workers,
                'total_searches': total_searches,
                'successful_searches': successful,
                'failed_searches': failed,
                'success_rate': round(successful / total_searches * 100, 2) if total_searches > 0 else 0,
                'queue_size': self.task_queue.qsize()
            }
    
    def stop(self):
        """Para o pool"""
        logger.info("Parando pool...")
        self.is_running = False
        
        for _ in self.workers:
            self.task_queue.put(None)
        
        for worker in self.workers:
            worker.close()
        
        logger.info("Pool parado")

