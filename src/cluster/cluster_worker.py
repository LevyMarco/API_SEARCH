#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster Worker Node (Google Local)
- Consome tarefas do Redis (lista: scraper:tasks)
- Executa buscas locais do Google (tbm=lcl)
- Retorna resultados em chave: scraper:result:{task_id}
- Publica heartbeat periódico em: worker:{hostname}:worker-{id}:heartbeat
"""

import os
import sys
import json
import time
import socket
import signal
import logging
import argparse
import threading
from datetime import datetime, timezone
from urllib.parse import quote_plus

from dotenv import load_dotenv

import redis
import undetected_chromedriver as uc
from http.client import RemoteDisconnected
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    SessionNotCreatedException,
    InvalidSessionIdException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ======================================================================
# Carrega .env (caminho absoluto usado no projeto)
# ======================================================================
load_dotenv('/www/wwwroot/sistemas/search_API/scraper_windows/.env')

# ======================================================================
# Configurações principais (ambiente)
# ======================================================================
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

WORKER_ID = os.getenv('WORKER_ID', '0')
NODE_NAME = os.getenv('NODE_NAME', socket.gethostname() or 'node')

TASK_QUEUE_KEY = os.getenv('TASK_QUEUE_KEY', 'scraper:tasks')
RESULT_KEY_PREFIX = os.getenv('RESULT_KEY_PREFIX', 'scraper:result:')

HEARTBEAT_TTL = int(os.getenv('HEARTBEAT_TTL', '60'))
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '5'))

# Chrome init tunables
CHROME_STARTUP_TIMEOUT = int(os.getenv("CHROME_STARTUP_TIMEOUT", "90"))  # seconds
CHROME_RETRIES = int(os.getenv("CHROME_RETRIES", "3"))
CHROME_BACKOFF_BASE = int(os.getenv("CHROME_BACKOFF_BASE", "3"))        # seconds

# Scraping tunables
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "45"))
SCROLL_PAUSE = float(os.getenv("SCROLL_PAUSE", "0.4"))
MAX_SCROLLS = int(os.getenv("MAX_SCROLLS", "30"))  # segurança para não rolar infinito

# Depuração
DEBUG_DIR = os.getenv("DEBUG_DIR", "/tmp/scraper_debug")
os.makedirs(DEBUG_DIR, exist_ok=True)
SAVE_DEBUG_ON_EMPTY = os.getenv("SAVE_DEBUG_ON_EMPTY", "1") == "1"

# ======================================================================
# Logging
# ======================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

FULL_WORKER_ID = f"{NODE_NAME}:worker-{WORKER_ID}"

# ======================================================================
# Redis
# ======================================================================
def connect_redis() -> redis.Redis:
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=10,
        socket_connect_timeout=10,
    )
    r.ping()
    return r

# ======================================================================
# Utilidades
# ======================================================================
def now_iso() -> str:
    # UTC timezone-aware
    return datetime.now(timezone.utc).isoformat()

def _port_is_open(host: str, port: int, timeout=1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def _dump_debug(driver, label: str):
    """
    Salva screenshot e HTML atual para depuração.
    """
    try:
        ts = int(time.time())
        png_path = os.path.join(DEBUG_DIR, f"{FULL_WORKER_ID}-{label}-{ts}.png")
        html_path = os.path.join(DEBUG_DIR, f"{FULL_WORKER_ID}-{label}-{ts}.html")
        try:
            driver.save_screenshot(png_path)
        except Exception:
            pass
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        except Exception:
            pass
        logger.info(f"{FULL_WORKER_ID}: Debug salvo: {png_path} / {html_path}")
    except Exception as e:
        logger.warning(f"{FULL_WORKER_ID}: Falha ao salvar debug: {e}")

# ======================================================================
# Chrome / Selenium
# ======================================================================
def init_chrome():
    """
    Sobe o Chrome headless com UC com retries e backoff.
    Garante user-data-dir por WORKER_ID e checa a porta de depuração quando disponível.
    """
    user_home = os.path.expanduser("~")
    profile_dir = os.path.join(user_home, ".config", f"uc-worker-{WORKER_ID}")
    os.makedirs(profile_dir, exist_ok=True)

    last_exc = None
    for attempt in range(1, CHROME_RETRIES + 1):
        try:
            opts = uc.ChromeOptions()
            # Flags estáveis para headless
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--blink-settings=imagesEnabled=false")
            opts.add_argument("--lang=pt-BR")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--no-first-run")
            opts.add_argument("--test-type")
            opts.add_argument("--headless=new")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--start-maximized")
            opts.add_argument(f"--user-data-dir={profile_dir}")
            # Força devtools na loopback (UC já seta porta)
            opts.add_argument("--remote-debugging-host=127.0.0.1")

            # User-Agent coerente (UC define um; manter coerência ajuda a reduzir intersticiais)
            # opts.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            #                   "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

            driver = uc.Chrome(options=opts, headless=True)
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

            # tenta descobrir a porta de debug do devtools (quando disponível)
            debug_port = None
            try:
                caps = driver.capabilities or {}
                dbg = caps.get("goog:chromeOptions", {}).get("debuggerAddress")
                if dbg and ":" in dbg:
                    debug_port = int(dbg.split(":")[1])
            except Exception:
                pass

            # aguarda o Chrome ficar realmente acessível (se soubermos a porta)
            if debug_port:
                t0 = time.time()
                while time.time() - t0 < CHROME_STARTUP_TIMEOUT:
                    if _port_is_open("127.0.0.1", debug_port, timeout=0.3):
                        break
                    time.sleep(0.3)

            logger.info(f"{FULL_WORKER_ID}: Chrome inicializado")
            return driver

        except (SessionNotCreatedException, WebDriverException, TimeoutException) as e:
            last_exc = e
            wait_s = CHROME_BACKOFF_BASE * attempt
            logger.warning(
                f"{FULL_WORKER_ID}: init_chrome tentativa {attempt}/{CHROME_RETRIES} falhou: {e}. "
                f"Retry em {wait_s}s..."
            )
            time.sleep(wait_s)
        except Exception as e:
            last_exc = e
            logger.error(f"{FULL_WORKER_ID}: Erro inesperado no init_chrome: {e}", exc_info=True)
            break

    raise RuntimeError(f"Falha ao inicializar Chrome após {CHROME_RETRIES} tentativas: {last_exc}")

def _session_ok(driver) -> bool:
    try:
        _ = driver.title  # força hit no DevTools
        return True
    except Exception:
        return False

def safe_get(driver, url: str, tries: int = 3, backoff: float = 2.0):
    """
    Faz driver.get com retries e valida sessão.
    """
    last_err = None
    for i in range(1, tries + 1):
        try:
            if not _session_ok(driver):
                raise InvalidSessionIdException("Sessão inválida (driver morto).")
            driver.get(url)
            return
        except (RemoteDisconnected, WebDriverException, TimeoutException, InvalidSessionIdException) as e:
            last_err = e
            logger.warning(f"{FULL_WORKER_ID}: safe_get falhou (tentativa {i}/{tries}): {e}")
            time.sleep(backoff * i)
    raise last_err if last_err else RuntimeError("Falha desconhecida no safe_get")

# ======================================================================
# Captcha (placeholder para evoluir no futuro)
# ======================================================================
def solve_captcha_if_needed(driver):
    """
    Placeholder para resolver captchas caso apareçam.
    Hoje apenas detecta e retorna False (não resolveu).
    """
    try:
        if "sorry/index" in driver.current_url or "consent.google.com" in driver.current_url:
            return False
        # poderíamos procurar iframes de recaptcha, etc.
    except Exception:
        pass
    return True

# ======================================================================
# Scraping Google Local (tbm=lcl)
# ======================================================================
def build_local_search_url(query: str, location: str, per_page: int = 10) -> str:
    q = f"{query} {location}"
    # gl/hl alinhados ao Brasil/pt-BR
    return f"https://www.google.com/search?hl=pt-BR&gl=br&tbm=lcl&num={per_page}&q={quote_plus(q)}"

def _parse_rating_text(text: str):
    if not text:
        return None
    raw = text.replace(",", ".")
    num = ""
    for ch in raw:
        if ch.isdigit() or ch == '.':
            num += ch
        elif num:
            break
    try:
        return float(num) if num else None
    except Exception:
        return None

def _extract_places_from_dom(driver):
    """
    Extrai cards visíveis da lista de locais.
    Retorna lista de dicionários com 'title' e 'rating' (quando disponível).
    Cobre múltiplos layouts do Google Local.
    """
    items = []

    # 1) Layout comum: cards com role=article
    cards = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')

    # 2) Alternativas conhecidas: blocos dentro de feeds/lists
    if not cards:
        cards = driver.find_elements(By.CSS_SELECTOR,
            'div[class*="rlfl__tls"] div[jscontroller][data-attrid], '        # bloco clássico
            'div[jsname="Cpkphb"] div[jscontroller][data-attrid], '           # variante feed
            'div[jsname="UyI44e"] div[jscontroller][data-attrid]'             # outra variante
        )

    # 3) Fallback final: elementos que contenham título clicável
    if not cards:
        cards = driver.find_elements(By.CSS_SELECTOR,
            'div a[role="heading"], div div[role="heading"]'
        )

    for card in cards:
        try:
            title = None

            # Título: tentar por role=heading dentro do card
            try:
                title_el = card.find_element(By.CSS_SELECTOR, 'a[role="heading"], div[role="heading"]')
                title = title_el.text.strip()
                if not title:
                    title = title_el.get_attribute("aria-label") or ""
                    title = title.strip()
            except NoSuchElementException:
                pass

            # Alternativa: spans com classes de título
            if not title:
                try:
                    title_el = card.find_element(By.CSS_SELECTOR, 'span[role="link"][aria-level], div[aria-level]')
                    title = (title_el.text or "").strip()
                except Exception:
                    pass

            # Rating: várias possibilidades
            rating = None
            try:
                rating_el = card.find_element(By.CSS_SELECTOR, 'span[aria-label*="estrelas"], span[aria-label*="stars"]')
                rating = _parse_rating_text(rating_el.get_attribute("aria-label"))
            except NoSuchElementException:
                pass
            if rating is None:
                try:
                    raw = card.find_element(By.CSS_SELECTOR, 'span[class*="RfnDt"], span[class*="YDIN4c"]').text
                    rating = _parse_rating_text(raw)
                except Exception:
                    pass

            if title:
                items.append({"title": title, "rating": rating})
        except Exception:
            continue

    return items

def _do_scroll(driver):
    """
    Tenta rolar o container da lista; fallback para rolar a página.
    """
    try:
        scrollers = driver.find_elements(By.CSS_SELECTOR, 'div[jsname="I4bIT"], div[aria-label*="Resultados"], div[class*="rlfl__tls"]')
        if scrollers:
            driver.execute_script("arguments[0].scrollBy(0, 900);", scrollers[0])
        else:
            driver.execute_script("window.scrollBy(0, 900);")
    except Exception:
        try:
            driver.execute_script("window.scrollBy(0, 900);")
        except Exception:
            pass

def google_local_search(driver, query: str, location: str, limit: int = 10, allow_reinit_once: bool = True):
    """
    Abre a página de resultados locais, rola até coletar 'limit' itens (ou esgotar).
    Retorna estrutura compatível com a API.
    Se houver queda de sessão (RemoteDisconnected/etc), reinicializa o driver UMA vez.
    """
    tsearch0 = time.time()
    url = build_local_search_url(query, location, per_page=10)
    logger.info(f"{FULL_WORKER_ID}: Acessando {url}")

    # 1) Acessar com retries
    try:
        safe_get(driver, url, tries=3, backoff=2.0)
    except (RemoteDisconnected, WebDriverException, TimeoutException, InvalidSessionIdException) as e:
        if allow_reinit_once:
            logger.warning(f"{FULL_WORKER_ID}: safe_get falhou; reiniciando Chrome e tentando uma vez: {e}")
            try:
                driver.quit()
            except Exception:
                pass
            driver = init_chrome()
            return google_local_search(driver, query, location, limit, allow_reinit_once=False)
        raise

    # 2) Espera primeiro bloco de resultados carregar
    try:
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                'div[role="article"], div[class*="rlfl__tls"] div[jscontroller][data-attrid], '
                'div[jsname="Cpkphb"] div[jscontroller][data-attrid]'
            ))
        )
    except TimeoutException:
        if not solve_captcha_if_needed(driver):
            _dump_debug(driver, "captcha-or-consent")
            raise RuntimeError("Captcha ou consentimento bloqueando a página.")
        # Mesmo sem os seletores prontos, vamos seguir para tentar extrair algo
        pass

    collected = []
    seen_titles = set()
    scrolls = 0
    last_len = 0

    while len(collected) < limit and scrolls < MAX_SCROLLS:
        # Extrai o que já temos no DOM
        current = _extract_places_from_dom(driver)
        for it in current:
            t = (it.get("title") or "").strip()
            if not t:
                continue
            if t in seen_titles:
                continue
            seen_titles.add(t)
            collected.append(it)
            if len(collected) >= limit:
                break

        # Contabiliza e decide nova rolagem
        if len(collected) == last_len:
            scrolls += 1
        else:
            last_len = len(collected)
            scrolls += 1

        if len(collected) >= limit:
            break

        _do_scroll(driver)
        time.sleep(SCROLL_PAUSE)

    total_time = round(time.time() - tsearch0, 2)

    # Debug quando vazio
    if not collected and SAVE_DEBUG_ON_EMPTY:
        _dump_debug(driver, "no-results")

    # Monta payload padronizado
    places = []
    for idx, it in enumerate(collected[:limit], start=1):
        places.append({
            "position": idx,
            "title": it.get("title"),
            "rating": it.get("rating"),
        })

    return {
        "status": "success",
        "local_results": {
            "places": places
        },
        "search_parameters": {
            "engine": "google_local",
            "q": f"{query} {location}",
            "location_requested": location,
            "limit": limit
        },
        "search_metadata": {
            "created_at": now_iso(),
            "method": "Google Search (FREE CAPTCHA - Wit.ai)",
            "node": NODE_NAME,
            "worker_id": FULL_WORKER_ID,
            "from_cache": False,
            "cost": "$0.00",
            "captchas_solved": 0,  # placeholder
            "total_time_taken": total_time
        }
    }

# ======================================================================
# Heartbeat thread
# ======================================================================
def heartbeat_loop(r: redis.Redis, stop_event: threading.Event):
    key = f"worker:{FULL_WORKER_ID}:heartbeat"
    while not stop_event.is_set():
        try:
            now = now_iso()
            r.setex(key, HEARTBEAT_TTL, now)
        except Exception as e:
            logger.warning(f"{FULL_WORKER_ID}: heartbeat erro: {e}")
        stop_event.wait(HEARTBEAT_INTERVAL)

# ======================================================================
# Tarefas
# ======================================================================
def handle_task(driver, task: dict):
    """
    Executa a tarefa de busca local conforme 'task' recebida.
    Espera 'id', 'query', 'location', 'limit'.
    """
    t0 = time.time()
    task_id = task.get('id')
    query = task.get('query', '').strip()
    location = task.get('location', '').strip()
    limit = int(task.get('limit', 10))

    if not query or not location:
        raise ValueError("Parâmetros incompletos na tarefa (query/location).")

    try:
        result = google_local_search(driver, query, location, limit)
    except Exception as e:
        # Dump de depuração no erro
        try:
            _dump_debug(driver, "error")
        except Exception:
            pass
        raise

    # Atualiza total_time_taken (mais preciso)
    result['search_metadata']['total_time_taken'] = round(time.time() - t0, 2)
    result['task_id'] = task_id
    result['node'] = NODE_NAME
    result['worker_id'] = FULL_WORKER_ID

    return result

# ======================================================================
# Loop principal do worker
# ======================================================================
def main():
    parser = argparse.ArgumentParser(description="Scraper Cluster Worker")
    parser.add_argument("-c", "--concurrency", type=int, default=1,
                        help="(reservado) número de instâncias locais do worker")
    args = parser.parse_args()
    _ = args.concurrency  # hoje não usamos concorrência intra-processo

    print("=" * 69)
    print("🚀 Worker Node:", NODE_NAME, "/ ID", WORKER_ID)
    print("=" * 69)
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    print("=" * 69)

    # Conexão Redis
    try:
        r = connect_redis()
        logger.info("✅ Conectado ao Redis: %s:%s", REDIS_HOST, REDIS_PORT)
    except Exception as e:
        logger.error(f"{FULL_WORKER_ID}: Erro conectando ao Redis: {e}")
        sys.exit(1)

    # Inicializa Chrome
    driver = None
    try:
        driver = init_chrome()
        logger.info(f"{FULL_WORKER_ID}: Iniciado")
    except Exception as e:
        logger.error(f"{FULL_WORKER_ID}: ❌ Falha ao inicializar Chrome")
        print("=" * 69)
        print("🚀 Worker Node:", NODE_NAME, "/ ID", WORKER_ID)
        print("=" * 69)
        print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
        print("=" * 69)
        raise

    # Heartbeat
    stop_event = threading.Event()
    hb_thread = threading.Thread(target=heartbeat_loop, args=(r, stop_event), daemon=True)
    hb_thread.start()

    # Tratamento de sinais para encerramento limpo
    def _graceful_exit(signum, frame):
        try:
            stop_event.set()
        except Exception:
            pass
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _graceful_exit)
    signal.signal(signal.SIGINT, _graceful_exit)

    # Loop de consumo de tarefas
    while True:
        try:
            # Espera bloqueando por 2s para permitir encerrar via sinal
            item = r.brpop(TASK_QUEUE_KEY, timeout=2)
            if not item:
                continue

            _, raw = item
            try:
                task = json.loads(raw)
            except Exception:
                logger.warning(f"{FULL_WORKER_ID}: Tarefa inválida (JSON).")
                continue

            task_id = task.get('id', f"task:{int(time.time()*1000)}")

            try:
                res = handle_task(driver, task)
            except Exception as e:
                # Em caso de erro, retorna payload de erro
                res = {
                    "status": "error",
                    "error": str(e),
                    "task_id": task_id,
                    "node": NODE_NAME,
                    "worker_id": FULL_WORKER_ID,
                    "from_cache": False
                }

            # Publica resultado (master tem um loop de espera)
            result_key = f"{RESULT_KEY_PREFIX}{task_id}"
            r.setex(result_key, 180, json.dumps(res))

            logger.info(f"{FULL_WORKER_ID}: Tarefa {task_id} concluída")

        except Exception as e:
            # Erros transientes: loga e continua
            logger.error(f"{FULL_WORKER_ID}: Erro no loop principal: {e}")
            time.sleep(1)

# ======================================================================
if __name__ == "__main__":
    main()
