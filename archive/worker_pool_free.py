"""
Worker Pool com CAPTCHA Solver GRATUITO (Wit.ai)
Taxa de sucesso: 70-80%
Custo: $0
"""
import queue
import threading
import time
import random
import logging
import re
import os
from typing import Dict, Any, Optional

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from captcha_solver_free import FreeCaptchaSolver, get_free_wit_api_keys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeleniumWorker:
    """Worker com CAPTCHA solver GRATUITO"""
    
    def __init__(self, worker_id: int, config: Dict[str, Any]):
        self.worker_id = worker_id
        self.config = config
        self.driver = None
        self.is_busy = False
        self.total_searches = 0
        self.successful_searches = 0
        self.failed_searches = 0
        self.captchas_solved = 0
        self.captchas_failed = 0
        
        # Inicializa CAPTCHA solver gratuito
        try:
            wit_keys = get_free_wit_api_keys()
            if wit_keys and wit_keys[0] != 'YOUR_WIT_API_KEY_1':
                self.captcha_solver = FreeCaptchaSolver(wit_keys)
                logger.info(f"Worker {self.worker_id}: CAPTCHA solver GRATUITO habilitado ({len(wit_keys)} keys)")
            else:
                self.captcha_solver = None
                logger.warning(f"Worker {self.worker_id}: Configure WIT_API_KEYS para resolver CAPTCHAs")
        except Exception as e:
            self.captcha_solver = None
            logger.error(f"Worker {self.worker_id}: Erro ao inicializar CAPTCHA solver: {e}")
        
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
            options.add_argument('--lang=pt-BR,pt;q=0.9')
            options.add_argument('--window-size=1920,1080')
            
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
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
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
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        return random.choice(user_agents)
    
    def _check_and_solve_captcha(self) -> bool:
        """Verifica se há CAPTCHA e resolve GRATUITAMENTE"""
        try:
            page_source = self.driver.page_source.lower()
            
            # Verifica se há CAPTCHA
            if 'captcha' not in page_source and 'unusual traffic' not in page_source:
                return True  # Sem CAPTCHA
            
            logger.warning(f"Worker {self.worker_id}: CAPTCHA detectado!")
            
            if not self.captcha_solver:
                logger.error(f"Worker {self.worker_id}: CAPTCHA solver não configurado")
                logger.error("Configure WIT_API_KEYS para resolver CAPTCHAs gratuitamente")
                self.captchas_failed += 1
                return False
            
            logger.info(f"Worker {self.worker_id}: Resolvendo CAPTCHA com Wit.ai (GRÁTIS)...")
            
            # Resolve CAPTCHA gratuitamente
            success = self.captcha_solver.solve_recaptcha_v2(self.driver, max_attempts=3)
            
            if success:
                logger.info(f"Worker {self.worker_id}: ✅ CAPTCHA resolvido gratuitamente!")
                self.captchas_solved += 1
                return True
            else:
                logger.error(f"Worker {self.worker_id}: ❌ Falha ao resolver CAPTCHA")
                self.captchas_failed += 1
                return False
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro ao resolver CAPTCHA: {e}")
            self.captchas_failed += 1
            return False
    
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
        """Realiza a busca no Google Search"""
        start_time = time.time()
        
        search_query = f"{query} {location}"
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        
        logger.info(f"Worker {self.worker_id}: Acessando {url}")
        self.driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        # Verifica e resolve CAPTCHA gratuitamente
        if not self._check_and_solve_captcha():
            raise Exception("Falha ao resolver CAPTCHA")
        
        # Aguarda um pouco mais
        time.sleep(random.uniform(2, 4))
        
        # Extrai resultados
        places = self._extract_local_results()
        
        elapsed_time = time.time() - start_time
        
        return {
            'status': 'success',
            'search_metadata': {
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                'total_time_taken': round(elapsed_time, 2),
                'method': 'Google Search (FREE CAPTCHA solver - Wit.ai)',
                'worker_id': self.worker_id,
                'captchas_solved': self.captchas_solved,
                'captchas_failed': self.captchas_failed,
                'cost': '$0.00',
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
            logger.info(f"Worker {self.worker_id}: Extraindo resultados...")
            
            # Tenta diferentes seletores
            selectors = [
                'div.rllt__details',
                'div[jsname="GZq3Ke"]',
                'div.VkpGBb',
                'div.g',
            ]
            
            local_elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) > 0:
                        logger.info(f"Worker {self.worker_id}: Encontrados {len(elements)} com '{selector}'")
                        local_elements = elements
                        break
                except:
                    continue
            
            logger.info(f"Worker {self.worker_id}: Processando {len(local_elements)} elementos")
            
            position = 1
            for idx, element in enumerate(local_elements[:30], 1):
                try:
                    place_data = self._extract_place_data(element, position)
                    
                    if place_data and place_data.get('title'):
                        places.append(place_data)
                        logger.debug(f"Worker {self.worker_id}: #{position}: {place_data['title'][:50]}")
                        position += 1
                        
                        if position > 20:
                            break
                            
                except Exception as e:
                    logger.debug(f"Worker {self.worker_id}: Erro elemento {idx}: {e}")
                    continue
            
            logger.info(f"Worker {self.worker_id}: Extraídos {len(places)} lugares")
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro na extração: {e}")
        
        return places
    
    def _extract_place_data(self, element, position: int) -> Optional[Dict[str, Any]]:
        """Extrai dados de um elemento"""
        place_data = {'position': position}
        
        try:
            full_text = element.text
            if not full_text or len(full_text) < 5:
                return None
            
            # Nome/Título
            try:
                link = element.find_element(By.CSS_SELECTOR, 'a[aria-label]')
                title = link.get_attribute('aria-label')
                place_data['title'] = title
                place_data['link'] = link.get_attribute('href')
                
                href = place_data['link']
                if href and '/maps/place/' in href:
                    try:
                        place_id = href.split('/maps/place/')[1].split('/')[0]
                        place_data['place_id'] = place_id
                    except:
                        place_data['place_id'] = None
            except:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, 'h3')
                    place_data['title'] = title_elem.text
                except:
                    lines = full_text.split('\n')
                    place_data['title'] = lines[0] if lines else None
            
            if not place_data.get('title'):
                return None
            
            # Rating e Reviews
            try:
                rating_pattern = r'(\d+[.,]\d+)\s*\(?([\d.,]+)\)?'
                match = re.search(rating_pattern, full_text)
                if match:
                    place_data['rating'] = float(match.group(1).replace(',', '.'))
                    place_data['reviews'] = int(match.group(2).replace('.', '').replace(',', ''))
                else:
                    place_data['rating'] = None
                    place_data['reviews'] = None
            except:
                place_data['rating'] = None
                place_data['reviews'] = None
            
            # Endereço
            try:
                address_pattern = r'(?:Rua|Av\.|Avenida|R\.|Alameda)[^·\n]+'
                match = re.search(address_pattern, full_text, re.IGNORECASE)
                place_data['address'] = match.group(0).strip() if match else None
            except:
                place_data['address'] = None
            
            # Telefone
            try:
                phone_pattern = r'\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}'
                match = re.search(phone_pattern, full_text)
                place_data['phone'] = match.group(0) if match else None
            except:
                place_data['phone'] = None
            
            return place_data
            
        except Exception as e:
            return None
    
    def close(self):
        """Fecha o Chrome"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"Worker {self.worker_id}: Chrome fechado")
                logger.info(f"  CAPTCHAs resolvidos: {self.captchas_solved}")
                logger.info(f"  CAPTCHAs falhados: {self.captchas_failed}")
                logger.info(f"  Custo total: $0.00 (GRÁTIS!)")
            except:
                pass


class WorkerPool:
    """Pool de workers com CAPTCHA solver gratuito"""
    
    def __init__(self, num_workers: int = 5, config: Optional[Dict[str, Any]] = None):
        self.num_workers = num_workers
        self.config = config or {}
        self.workers = []
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = False
        self.lock = threading.Lock()
        
        logger.info(f"Inicializando pool com {num_workers} workers...")
        logger.info("🆓 Usando CAPTCHA solver GRATUITO (Wit.ai)")
        
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
                
                result = worker.search(task['query'], task['location'])
                result['task_id'] = task['id']
                
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
        self.task_queue.put({'id': task_id, 'query': query, 'location': location})
    
    def get_result(self, timeout: float = 180) -> Optional[Dict[str, Any]]:
        """Pega resultado"""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas"""
        with self.lock:
            total_captchas_solved = sum(w.captchas_solved for w in self.workers)
            total_captchas_failed = sum(w.captchas_failed for w in self.workers)
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
                'captchas_solved': total_captchas_solved,
                'captchas_failed': total_captchas_failed,
                'captcha_success_rate': round(total_captchas_solved / (total_captchas_solved + total_captchas_failed) * 100, 2) if (total_captchas_solved + total_captchas_failed) > 0 else 0,
                'success_rate': round(successful / total_searches * 100, 2) if total_searches > 0 else 0,
                'total_cost': '$0.00 (FREE!)',
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
        logger.info("💰 Custo total: $0.00 (100% GRATUITO!)")

