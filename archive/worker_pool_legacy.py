"""
Worker Pool para Windows - Versão Simplificada
"""
import queue
import threading
import time
import random
import logging
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
    print("⚠️  Selenium não instalado. Instale com: pip install selenium undetected-chromedriver")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeleniumWorker:
    """Worker individual com instância Chrome"""
    
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
            options.add_argument(f'--user-agent={self._get_random_user_agent()}')
            
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            logger.info(f"Worker {self.worker_id}: Chrome inicializado")
            return True
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro ao inicializar: {e}")
            return False
    
    def _get_random_user_agent(self) -> str:
        """Retorna user-agent aleatório"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
        return random.choice(user_agents)
    
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
                    time.sleep(random.uniform(2, 4))
                else:
                    self.failed_searches += 1
                    self.is_busy = False
                    return {
                        'status': 'error',
                        'error': str(e),
                        'worker_id': self.worker_id
                    }
    
    def _perform_search(self, query: str, location: str) -> Dict[str, Any]:
        """Realiza a busca"""
        start_time = time.time()
        
        search_query = f"{query} {location}"
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        self.driver.get(url)
        logger.info(f"Worker {self.worker_id}: Aguardando carregamento da página...")
        time.sleep(random.uniform(6, 9))
        
        self._scroll_results()
        places = self._extract_places()
        
        elapsed_time = time.time() - start_time
        
        return {
            'status': 'success',
            'search_metadata': {
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                'total_time_taken': round(elapsed_time, 2),
                'method': 'Selenium WebDriver',
                'worker_id': self.worker_id,
                'from_cache': False
            },
            'search_parameters': {
                'engine': 'google_maps',
                'q': search_query,
                'location_requested': location
            },
            'local_results': {
                'places': places
            }
        }
    
    def _scroll_results(self):
        """Scroll na lista"""
        try:
            results_panel = self.driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
            for i in range(2):
                self.driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', results_panel)
                time.sleep(random.uniform(1, 2))
        except Exception as e:
            logger.warning(f"Worker {self.worker_id}: Erro ao fazer scroll: {e}")
    
    def _extract_places(self) -> list:
        """Extrai lugares"""
        places = []
        
        try:
            # Aguarda elementos aparecerem
            logger.info(f"Worker {self.worker_id}: Aguardando elementos...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="article"]'))
            )
            time.sleep(2)  # Aguarda mais um pouco para garantir
            
            articles = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            logger.info(f"Worker {self.worker_id}: Encontrados {len(articles)} elementos article")
            
            position = 1
            for idx, article in enumerate(articles[:30], 1):
                try:
                    # Nome - se não tiver nome válido, pula
                    try:
                        name_elem = article.find_element(By.CSS_SELECTOR, 'a[aria-label]')
                        title = name_elem.get_attribute('aria-label')
                        if not title or len(title) < 3:
                            logger.debug(f"Worker {self.worker_id}: Elemento {idx} sem título válido, pulando")
                            continue
                    except:
                        logger.debug(f"Worker {self.worker_id}: Elemento {idx} sem link com aria-label, pulando")
                        continue
                    
                    place_data = {
                        'position': position,
                        'title': title
                    }
                    
                    # Rating
                    try:
                        rating_text = article.find_element(By.CSS_SELECTOR, 'span[role="img"]').get_attribute('aria-label')
                        if 'estrelas' in rating_text or 'stars' in rating_text:
                            parts = rating_text.split()
                            place_data['rating'] = float(parts[0].replace(',', '.'))
                            review_elem = article.find_element(By.XPATH, './/span[contains(text(), "avaliações") or contains(text(), "reviews")]')
                            review_text = review_elem.text
                            place_data['reviews'] = int(''.join(filter(str.isdigit, review_text)))
                    except:
                        place_data['rating'] = None
                        place_data['reviews'] = None
                    
                    # Place ID e link
                    try:
                        link = article.find_element(By.CSS_SELECTOR, 'a[href*="maps"]')
                        href = link.get_attribute('href')
                        place_data['link'] = href
                        if '/place/' in href:
                            place_id = href.split('/place/')[1].split('/')[0]
                            place_data['place_id'] = place_id
                        else:
                            place_data['place_id'] = None
                    except:
                        place_data['link'] = None
                        place_data['place_id'] = None
                    
                    places.append(place_data)
                    logger.debug(f"Worker {self.worker_id}: Extraído lugar {position}: {title[:50]}")
                    position += 1
                    
                    # Limita a 20 resultados válidos
                    if position > 20:
                        break
                    
                except Exception as e:
                    logger.warning(f"Worker {self.worker_id}: Erro ao extrair elemento {idx}: {e}")
                    continue
            
        except TimeoutException:
            logger.error(f"Worker {self.worker_id}: Timeout ao aguardar resultados")
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro ao extrair: {e}")
        
        return places
    
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
                    self.config.get('delay_min', 2),
                    self.config.get('delay_max', 5)
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

