#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worker Pool V3 - Google Local (Google Search) com resolução de CAPTCHA.
Retorno padronizado:
{
  "status": "success",
  "search_metadata": {...},
  "local_results": {
    "places": [
      {
        position, title, rating, reviews, reviews_original, price, type, address,
        hours, thumbnail, maps_url,
        place_id,          # Google Place ID oficial (ChIJ...)
        place_id_cid       # CID numérico ("ludocid/cid") - compatível com SerpAPI
      }
    ]
  }
}
"""

import os
import re
import time
import random
import queue
import threading
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs, unquote

# ----------------------------------------------------------------------
# Selenium / UC stack
# ----------------------------------------------------------------------
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Solver PAGO (opcional / fallback)
try:
    from src.solvers.captcha_solver import CaptchaSolver  # 2Captcha
except Exception:
    CaptchaSolver = None

# Solver GRÁTIS (Wit.ai) — tente vários nomes de arquivo
FreeCaptchaSolver = None
try:
    from src.solvers.captcha_solver_free import FreeCaptchaSolver
except Exception:
    pass

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


# ======================================================================
# SeleniumWorker
# ======================================================================
class SeleniumWorker:
    def __init__(self, worker_id: int, config: Dict[str, Any]):
        self.worker_id = worker_id
        self.config = config or {}
        self.driver = None
        self.is_busy = False
        self.total_searches = 0
        self.successful_searches = 0
        self.failed_searches = 0
        self.captchas_solved = 0

        # 2Captcha (pago) — opcional
        captcha_api_key = self.config.get("captcha_api_key") or os.getenv("CAPTCHA_API_KEY")
        self.captcha_solver = CaptchaSolver(captcha_api_key) if (CaptchaSolver and captcha_api_key) else None

        # Wit.ai (grátis) — preferencial
        wit_keys_env = os.getenv("WIT_API_KEYS", "")
        self.free_captcha_solver = None
        if FreeCaptchaSolver and wit_keys_env:
            wit_keys = [k.strip() for k in wit_keys_env.split(",") if k.strip()]
            if wit_keys:
                try:
                    self.free_captcha_solver = FreeCaptchaSolver(wit_keys)
                    logger.info(f"Worker {self.worker_id}: Free CAPTCHA solver (Wit.ai) habilitado com {len(wit_keys)} keys")
                except Exception as e:
                    logger.warning(f"Worker {self.worker_id}: falha ao instanciar FreeCaptchaSolver: {e}")
            else:
                logger.warning(f"Worker {self.worker_id}: WIT_API_KEYS está vazio (nenhuma key válida)")
        else:
            if not FreeCaptchaSolver:
                logger.info(f"Worker {self.worker_id}: FreeCaptchaSolver não disponível")
            elif not wit_keys_env:
                logger.info(f"Worker {self.worker_id}: WIT_API_KEYS não definido")

        if self.captcha_solver:
            logger.info(f"Worker {self.worker_id}: CAPTCHA solver pago (2Captcha) habilitado")
        else:
            logger.info(f"Worker {self.worker_id}: CAPTCHA solver pago (2Captcha) desabilitado")

    # ------------------------------------------------------------------
    def initialize(self) -> bool:
        """Inicializa o Chrome (undetected_chromedriver) de forma robusta em servidor."""
        if not SELENIUM_AVAILABLE:
            logger.error(f"Worker {self.worker_id}: Selenium não disponível")
            return False

        try:
            options = uc.ChromeOptions()
            for arg in [
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--lang=pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "--window-size=1920,1080",
            ]:
                options.add_argument(arg)
            options.add_argument(f'--user-agent={self._get_random_user_agent()}')

            # perfis/dados isolados por worker (evita conflito)
            user_conf = os.path.join("/home/dev/.config", f"google-chrome-uc-{self.worker_id}")
            user_cache = os.path.join("/home/dev/.cache", f"google-chrome-uc-{self.worker_id}")
            os.makedirs(user_conf, exist_ok=True)
            os.makedirs(user_cache, exist_ok=True)
            options.add_argument(f'--user-data-dir={user_conf}')
            options.add_argument(f'--data-path={user_cache}')

            # runtime
            runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or "/tmp/runtime-dev"
            os.makedirs(runtime_dir, exist_ok=True)

            prefs = {"profile.default_content_setting_values": {"notifications": 2, "geolocation": 1}}
            options.add_experimental_option("prefs", prefs)

            # binário do Chrome
            chromium_bin = self.config.get("chromium_binary") or os.getenv("UC_CHROME_BINARY") or "/usr/bin/google-chrome-stable"
            options.binary_location = chromium_bin

            # Detectar versão principal do Chrome para repassar ao UC (evita "chrome not reachable")
            import subprocess
            version_main = None
            try:
                out = subprocess.check_output([chromium_bin, "--version"], text=True).strip()
                m = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
                if m:
                    version_main = int(m.group(1))
            except Exception as e:
                logger.warning(f"Worker {self.worker_id}: não foi possível detectar versão do Chrome ({e})")

            logger.info(f"Worker {self.worker_id}: usando Chrome em {chromium_bin} (version_main={version_main})")

            if version_main:
                self.driver = uc.Chrome(options=options, use_subprocess=True, version_main=version_main)
            else:
                self.driver = uc.Chrome(options=options, use_subprocess=True)

            # Remove webdriver flag
            try:
                self.driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'}
                )
            except Exception:
                pass

            logger.info(f"Worker {self.worker_id}: Chrome inicializado")
            return True

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro ao inicializar: {e}")
            return False

    # ------------------------------------------------------------------
    def _get_random_user_agent(self) -> str:
        uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ]
        return random.choice(uas)

    # ------------------------------------------------------------------
    def _check_and_solve_captcha(self) -> bool:
        """
        Detecta CAPTCHA e tenta resolver:
          1) Primeiro: solver GRÁTIS (Wit.ai) via áudio
          2) Fallback opcional: solver pago (2Captcha), se configurado
        """
        try:
            html = (self.driver.page_source or "")
            low = html.lower()
            if ("captcha" not in low) and ("unusual traffic" not in low) and ("/sorry/" not in self.driver.current_url):
                return True

            logger.warning(f"Worker {self.worker_id}: CAPTCHA detectado em {self.driver.current_url}")

            # 1) Tentar solver GRÁTIS (Wit.ai)
            if self.free_captcha_solver:
                try:
                    ok = self.free_captcha_solver.solve_recaptcha_v2(self.driver, max_attempts=3)
                except Exception as e:
                    logger.warning(f"Worker {self.worker_id}: erro no solver grátis (Wit.ai): {e}")
                    ok = False

                if ok:
                    self.captchas_solved += 1
                    logger.info(f"Worker {self.worker_id}: ✅ CAPTCHA resolvido (Wit.ai)")
                    # revalidar página
                    time.sleep(2)
                    low2 = (self.driver.page_source or "").lower()
                    if ("captcha" in low2) or ("unusual traffic" in low2) or ("/sorry/" in self.driver.current_url):
                        logger.warning(f"Worker {self.worker_id}: Página ainda indica CAPTCHA após solver grátis")
                    else:
                        return True
                else:
                    logger.warning(f"Worker {self.worker_id}: solver grátis falhou, vendo fallback (2Captcha)")

            # 2) Fallback 2Captcha (se houver)
            if not self.captcha_solver:
                logger.error(f"Worker {self.worker_id}: Nenhum solver pago configurado; CAPTCHA persiste.")
                return False

            m = re.search(r'data-sitekey="([^"]+)"', html)
            if not m:
                logger.error(f"Worker {self.worker_id}: Site key não encontrado p/ 2Captcha")
                return False

            site_key = m.group(1)
            token = self.captcha_solver.solve_recaptcha_v2(site_key, self.driver.current_url, timeout=180)

            script = """
                (function(){
                    var textarea = document.getElementById("g-recaptcha-response");
                    if (!textarea) {
                        textarea = document.createElement("textarea");
                        textarea.id = "g-recaptcha-response";
                        textarea.name = "g-recaptcha-response";
                        textarea.style = "display:none;";
                        document.body.appendChild(textarea);
                    }
                    textarea.value = "%s";
                    var form = document.getElementById("captcha-form") || document.forms[0];
                    if (form) { form.submit(); }
                })();
            """ % (token.replace('"', '\\"'))

            self.driver.execute_script(script)
            time.sleep(random.uniform(4, 7))

            low2 = (self.driver.page_source or "").lower()
            if ("captcha" in low2) or ("unusual traffic" in low2) or ("/sorry/" in self.driver.current_url):
                logger.error(f"Worker {self.worker_id}: CAPTCHA persistente após 2Captcha.")
                return False

            self.captchas_solved += 1
            logger.info(f"Worker {self.worker_id}: ✅ CAPTCHA resolvido (2Captcha)")
            return True

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro solver: {e}")
            return False

    # ------------------------------------------------------------------
    def search(self, query: str, location: str, *, limit: int = 20,
               headless: bool = True, enrich_place_ids: bool = True,
               max_retries: int = 2) -> Dict[str, Any]:
        self.is_busy = True
        self.total_searches += 1
        last_err = None

        for attempt in range(max_retries):
            try:
                result = self._perform_search(query, location, limit=limit)
                self.successful_searches += 1
                self.is_busy = False
                return result
            except Exception as e:
                last_err = e
                logger.warning(f"Worker {self.worker_id}: Tentativa {attempt + 1} falhou: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 6))

        self.failed_searches += 1
        self.is_busy = False
        return {"status": "error", "error": str(last_err or "erro desconhecido"), "worker_id": self.worker_id}

    # ------------------------------------------------------------------
    def _perform_search(self, query: str, location: str, *, limit: int = 20) -> Dict[str, Any]:
        start_time = time.time()

        search_query = f"{query} {location}".strip()
        lcl_url = (
            "https://www.google.com/search?"
            f"q={search_query.replace(' ', '+')}"
            "&hl=pt-BR&gl=br&pws=0&tbm=lcl"
            f"&num={max(10, min(20, limit*2))}"
        )

        try:
            # 1) preparar sessão/cookies
            logger.info(f"Worker {self.worker_id}: Abrindo Google Home p/ cookie/session")
            self.driver.get("https://www.google.com/")
            time.sleep(random.uniform(1.0, 2.0))
            try:
                accept_btn = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((
                        By.XPATH, "//button//div[contains(text(),'Aceitar') or contains(text(),'I agree') or contains(text(),'Accept all') or contains(text(),'Aceitar tudo')]"
                    ))
                )
                accept_btn.click()
                time.sleep(random.uniform(0.6, 1.2))
            except Exception:
                pass

            # 2) geolocalização (ex.: Recife)
            try:
                lat, lon, acc = -8.047562, -34.876964, 100
                self.driver.execute_cdp_cmd("Browser.grantPermissions", {
                    "origin": "https://www.google.com", "permissions": ["geolocation"]
                })
                self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
                    "latitude": lat, "longitude": lon, "accuracy": acc
                })
            except Exception:
                pass

            # 3) vertical local
            logger.info(f"Worker {self.worker_id}: Acessando tbm=lcl: {lcl_url}")
            self.driver.get(lcl_url)
            time.sleep(random.uniform(2.0, 3.0))
            if not self._check_and_solve_captcha():
                raise Exception("Falha ao resolver CAPTCHA")

            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1200);")
                time.sleep(random.uniform(0.8, 1.3))

            places = self._extract_local_results_lcl(limit=limit)

            # 4) fallback SERP
            if not places:
                serp_url = (
                    "https://www.google.com/search?"
                    f"q={search_query.replace(' ', '+')}"
                    "&hl=pt-BR&gl=br&pws=0"
                    f"&num={max(10, min(20, limit*2))}"
                )
                logger.info(f"Worker {self.worker_id}: Fallback SERP comum…")
                self.driver.get(serp_url)
                time.sleep(random.uniform(2.0, 3.0))
                if not self._check_and_solve_captcha():
                    raise Exception("Falha ao resolver CAPTCHA (fallback SERP)")
                for _ in range(2):
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(random.uniform(0.7, 1.1))
                places = self._extract_local_results_serp(limit=limit)

            # 5) fallback Maps
            if not places:
                maps_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}+{location.replace(' ', '+')}"
                logger.info(f"Worker {self.worker_id}: Fallback Maps: {maps_url}")
                self.driver.get(maps_url)
                time.sleep(random.uniform(3.0, 4.0))
                if not self._check_and_solve_captcha():
                    raise Exception("Falha ao resolver CAPTCHA (maps fallback)")

                anchors = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "a[aria-label][data-ludocid], a.hfpxzc[aria-label], a[aria-label][href*='ludocid='], a[aria-label][href*='cid=']"
                )
                logger.info(f"Worker {self.worker_id}: Anchors no Maps: {len(anchors)}")
                pos = 1
                for a in anchors:
                    if pos > limit:
                        break
                    item = self._extract_place_data_from_any_anchor(a, pos)
                    if item:
                        places.append(item)
                        pos += 1

            elapsed_time = time.time() - start_time
            return {
                "status": "success",
                "search_metadata": {
                    "query": query,
                    "location": location,
                    "engine": "google_local",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                    "total_time_taken": round(elapsed_time, 2),
                    "worker_id": self.worker_id,
                    "captchas_solved": self.captchas_solved,
                    "from_cache": False,
                },
                "local_results": {"places": places[:limit]},
            }

        except Exception:
            raise

    # ------------------------------------------------------------------
    def _extract_local_results_lcl(self, *, limit: int = 20) -> list:
        results: List[Dict[str, Any]] = []
        try:
            logger.info(f"Worker {self.worker_id}: Extraindo (tbm=lcl) - procurando anchors…")
            anchors = self.driver.find_elements(
                By.CSS_SELECTOR,
                "a[aria-label][data-ludocid], a.hfpxzc[aria-label], a[aria-label][href*='ludocid='], a[aria-label][href*='cid=']"
            )

            if not anchors:
                containers = self.driver.find_elements(By.CSS_SELECTOR, "div#search, div[jsname='GZq3Ke'], div.VkpGBb")
                for c in containers:
                    if len(anchors) >= limit:
                        break
                    try:
                        anchors += c.find_elements(
                            By.CSS_SELECTOR,
                            "a[aria-label][data-ludocid], a.hfpxzc[aria-label], a[aria-label][href*='ludocid='], a[aria-label][href*='cid=']"
                        )
                    except Exception:
                        continue

            if not anchors:
                for _ in range(3):
                    self.driver.execute_script("window.scrollBy(0, 1200);")
                    time.sleep(random.uniform(0.8, 1.2))
                anchors = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "a[aria-label][data-ludocid], a.hfpxzc[aria-label], a[aria-label][href*='ludocid='], a[aria-label][href*='cid=']"
                )
                logger.info(f"Worker {self.worker_id}: Anchors após scroll (lcl): {len(anchors)}")

            pos = 1
            for a in anchors:
                if pos > limit:
                    break
                try:
                    item = self._extract_place_data_from_any_anchor(a, pos)
                    if item:
                        results.append(item)
                        pos += 1
                except Exception as e:
                    logger.debug(f"Worker {self.worker_id}: erro anchor lcl: {e}")
                    continue

            logger.info(f"Worker {self.worker_id}: Extraídos {len(results)} lugares (tbm=lcl).")
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro tbm=lcl: {e}")
        return results

    # ------------------------------------------------------------------
    def _extract_local_results_serp(self, *, limit: int = 20) -> list:
        results: List[Dict[str, Any]] = []
        try:
            logger.info(f"Worker {self.worker_id}: Extraindo (SERP)…")
            anchors = self.driver.find_elements(
                By.CSS_SELECTOR,
                "a[aria-label][data-ludocid], a.hfpxzc[aria-label], a[aria-label][href*='ludocid='], a[aria-label][href*='cid=']"
            )

            if not anchors:
                candidates = self.driver.find_elements(By.CSS_SELECTOR, "div[jsname='GZq3Ke'], div.VkpGBb, div#search")
                for c in candidates:
                    if len(anchors) >= limit:
                        break
                    try:
                        anchors += c.find_elements(
                            By.CSS_SELECTOR,
                            "a[aria-label][data-ludocid], a.hfpxzc[aria-label], a[aria-label][href*='ludocid='], a[aria-label][href*='cid=']"
                        )
                    except Exception:
                        continue

            if not anchors:
                for _ in range(2):
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(random.uniform(0.7, 1.1))
                anchors = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "a[aria-label][data-ludocid], a.hfpxzc[aria-label], a[aria-label][href*='ludocid='], a[aria-label][href*='cid=']"
                )

            logger.info(f"Worker {self.worker_id}: Anchors (SERP): {len(anchors)}")

            pos = 1
            for a in anchors:
                if pos > limit:
                    break
                item = self._extract_place_data_from_any_anchor(a, pos)
                if item:
                    results.append(item)
                    pos += 1

            logger.info(f"Worker {self.worker_id}: Extraídos {len(results)} lugares (SERP).")
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Erro SERP: {e}")

        return results

    # ------------------------------------------------------------------
    def _extract_place_ids_from_href(self, href: str) -> Dict[str, Optional[str]]:
        """
        Retorna {'place_id': PlaceID ChIJ..., 'place_id_cid': CID numérico} quando possível.
        """
        place_id = None
        place_id_cid = None

        # 1) Querystring: cid= ou ludocid=
        try:
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            if "cid" in qs and qs["cid"]:
                place_id_cid = qs["cid"][0]
            if "ludocid" in qs and qs["ludocid"]:
                place_id_cid = qs["ludocid"][0]
        except Exception:
            pass

        # 2) Marcadores no path: ...!1sChIJ... ou ...!19sChIJ...
        if not place_id:
            try:
                href_dec = unquote(href)
                m = re.search(r"!(?:1|19)s(ChIJ[0-9A-Za-z_-]+)", href_dec)
                if m:
                    place_id = m.group(1)
            except Exception:
                pass

        return {"place_id": place_id, "place_id_cid": place_id_cid}

    # ------------------------------------------------------------------
    def _maybe_place_ids_from_jslog(self, a_el) -> Dict[str, Optional[str]]:
        """
        Tenta extrair CID/PlaceID de atributos alternativos (ex.: jslog com 'ludocid').
        """
        pid = None
        cid = None
        try:
            jslog = a_el.get_attribute("jslog") or ""
            m = re.search(r"ludocid:(\d+)", jslog)
            if m:
                cid = m.group(1)
        except Exception:
            pass
        return {"place_id": pid, "place_id_cid": cid}

    # ------------------------------------------------------------------
    def _extract_place_data_from_any_anchor(self, a_el, position: int) -> Optional[Dict[str, Any]]:
        try:
            title = (a_el.get_attribute("aria-label") or "").strip()
            if not title:
                return None

            href = a_el.get_attribute("href") or ""
            ludocid_attr = a_el.get_attribute("data-ludocid") or None

            # IDs via href
            ids = self._extract_place_ids_from_href(href)
            place_id = ids.get("place_id")
            place_id_cid = ids.get("place_id_cid") or ludocid_attr

            # IDs via jslog (fallback)
            if not place_id_cid:
                alt = self._maybe_place_ids_from_jslog(a_el)
                if alt.get("place_id_cid"):
                    place_id_cid = alt["place_id_cid"]

            # container pai para contexto de texto/imagem
            parent = None
            try:
                parent = a_el.find_element(By.XPATH, "./ancestor::div[1]")
            except Exception:
                parent = None

            whole_text = (parent.text or "").strip() if parent else ""

            # rating / reviews
            rating, reviews, reviews_original = None, None, None
            m = re.search(r"(\d+[.,]\d+)\s*\(?\s*([\d\.\,]+\s*(?:mil)?)\s*\)?", whole_text, flags=re.I)
            if m:
                rating = float(m.group(1).replace(",", "."))
                reviews_original = m.group(2).strip()
                if re.search(r"\bmil\b", reviews_original, re.I):
                    try:
                        num = float(re.sub(r"[^\d,\.]", "", reviews_original.replace("mil", "")).replace(",", "."))
                    except Exception:
                        num = float(re.sub(r"[^\d\.]", "", reviews_original))
                    reviews = int(round(num * 1000))
                else:
                    reviews = int(reviews_original.replace(".", "").replace(",", ""))

            # price
            price = None
            m = re.search(r"(R\$\s*[\d\s\-–]+|\${1,4}|€{1,4})", whole_text)
            if m:
                price = m.group(0).strip()

            # address
            address = None
            m = re.search(r"(Rua|Av\.|Avenida|R\.|Alameda|Rod\.|Travessa|Tv\.)[^·\n]+", whole_text, re.I)
            if m:
                address = m.group(0).strip()

            # hours
            hours = None
            m = re.search(r"(Fechado|Fecha|Aberto|Abre\s+[^·\n]+|Fecha\s+[^·\n]+)", whole_text, re.I)
            if m:
                hours = m.group(0).strip()

            # type/categoria (segunda linha limpa, quando não é tel/endereço)
            typ = None
            if whole_text:
                lines = [ln.strip() for ln in whole_text.split("\n") if ln.strip()]
                if len(lines) >= 2:
                    candidate = lines[1]
                    if not re.search(r"\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}", candidate) and not re.search(r"(Rua|Av\.|Avenida|R\.|Alameda|Rod\.)", candidate, re.I):
                        typ = candidate[:100]

            # thumbnail
            thumb = None
            if parent:
                try:
                    img = parent.find_element(By.CSS_SELECTOR, "img")
                    thumb = img.get_attribute("src") or None
                except Exception:
                    pass

            item = {
                "position": position,
                "title": title,
                "maps_url": href or None,
            }

            # IDs
            if place_id:
                item["place_id"] = place_id               # ChIJ...
            if place_id_cid:
                item["place_id_cid"] = str(place_id_cid)  # numérico (cid/ludocid)

            if rating is not None: item["rating"] = rating
            if reviews is not None: item["reviews"] = reviews
            if reviews_original:    item["reviews_original"] = reviews_original
            if price:               item["price"] = price
            if typ:                 item["type"] = typ
            if address:             item["address"] = address
            if hours:               item["hours"] = hours
            if thumb:               item["thumbnail"] = thumb

            return item
        except Exception:
            return None

    # ------------------------------------------------------------------
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"Worker {self.worker_id}: Chrome fechado (CAPTCHAs resolvidos: {self.captchas_solved})")
            except Exception:
                pass


# ======================================================================
# WorkerPool
# ======================================================================
class WorkerPool:
    def __init__(self, num_workers: int = 5, config: Optional[Dict[str, Any]] = None):
        self.num_workers = num_workers
        self.config = config or {}
        self.workers: List[SeleniumWorker] = []
        self.task_queue: "queue.Queue[dict]" = queue.Queue()
        self.result_queue: "queue.Queue[dict]" = queue.Queue()
        self.is_running = False
        self.lock = threading.Lock()
        self._threads: List[threading.Thread] = []

        self.default_limit = int(self.config.get("default_limit", 20))
        self.default_headless = bool(self.config.get("headless", True))
        self.default_enrich = bool(self.config.get("enrich_place_ids", True))

        logger.info(f"Inicializando pool com {num_workers} workers...")

    def start(self):
        self.is_running = True

        # 2Captcha: pode ter várias chaves em arquivo (rota round-robin) — OPCIONAL
        token_file = self.config.get('captcha_token_file') or os.getenv('CAPTCHA_TOKEN_FILE')
        captcha_keys: List[str] = []
        if token_file:
            try:
                with open(token_file, 'r') as f:
                    captcha_keys = [line.strip() for line in f if line.strip()]
                logger.info(f"WorkerPool: carregadas {len(captcha_keys)} chaves de CAPTCHA de {token_file}")
            except Exception as e:
                logger.warning(f"WorkerPool: não foi possível ler token file {token_file}: {e}")

        single_key = self.config.get('captcha_api_key') or os.getenv('CAPTCHA_API_KEY')
        if not captcha_keys and single_key:
            captcha_keys = [single_key]

        chromium_binary = self.config.get("chromium_binary") or os.getenv("UC_CHROME_BINARY")

        for i in range(self.num_workers):
            key_for_worker = captcha_keys[i % len(captcha_keys)] if captcha_keys else None
            worker_cfg = dict(self.config or {})
            if key_for_worker:
                worker_cfg['captcha_api_key'] = key_for_worker
            if chromium_binary:
                worker_cfg['chromium_binary'] = chromium_binary

            worker = SeleniumWorker(i + 1, worker_cfg)
            if worker.initialize():
                self.workers.append(worker)
                thread = threading.Thread(target=self._worker_loop, args=(worker,), daemon=True)
                thread.start()
                self._threads.append(thread)
            else:
                logger.error(f"Falha ao inicializar worker {i + 1}")

        logger.info(f"Pool iniciado com {len(self.workers)} workers ativos")

    def _worker_loop(self, worker: SeleniumWorker):
        while self.is_running:
            try:
                task = self.task_queue.get(timeout=1)
            except queue.Empty:
                continue

            if task is None:
                break

            try:
                result = worker.search(
                    task["query"],
                    task["location"],
                    limit=task.get("limit", self.default_limit),
                    headless=task.get("headless", self.default_headless),
                    enrich_place_ids=task.get("enrich_place_ids", self.default_enrich),
                    max_retries=int(self.config.get("max_retries", 2)),
                )
                result["task_id"] = task["id"]
                self.result_queue.put(result)
            except Exception as e:
                self.result_queue.put({"status": "error", "error": str(e), "task_id": task["id"]})
            finally:
                self.task_queue.task_done()

            delay = random.uniform(float(self.config.get("delay_min", 2)), float(self.config.get("delay_max", 5)))
            time.sleep(delay)

    def submit_task(self, query: str, location: str, task_id: str, **kwargs) -> None:
        payload = {"id": task_id, "query": query, "location": location}
        payload.update(kwargs or {})
        self.task_queue.put(payload)

    def get_result(self, task_id: Optional[str] = None, timeout: float = 180) -> Optional[Dict[str, Any]]:
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                item = self.result_queue.get(timeout=0.5)
                if (not task_id) or (item.get("task_id") == task_id):
                    return item
                else:
                    self.result_queue.put(item)
            except queue.Empty:
                continue
        return None

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total_captchas = sum(w.captchas_solved for w in self.workers)
            total_searches = sum(w.total_searches for w in self.workers)
            successful = sum(w.successful_searches for w in self.workers)
            failed = sum(w.failed_searches for w in self.workers)
            busy_workers = sum(1 for w in self.workers if w.is_busy)

            return {
                "total_workers": len(self.workers),
                "busy_workers": busy_workers,
                "available_workers": len(self.workers) - busy_workers,
                "total_searches": total_searches,
                "successful_searches": successful,
                "failed_searches": failed,
                "captchas_solved": total_captchas,
                "success_rate": round(successful / total_searches * 100, 2) if total_searches > 0 else 0,
                "queue_size": self.task_queue.qsize(),
            }

    def stop(self):
        logger.info("Parando pool...")
        self.is_running = False
        for _ in self.workers:
            self.task_queue.put(None)
        for w in self.workers:
            try:
                w.close()
            except Exception:
                pass
        for t in self._threads:
            try:
                t.join(timeout=3.0)
            except Exception:
                pass
        logger.info("Pool parado")
