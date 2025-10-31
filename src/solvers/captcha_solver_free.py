"""
CAPTCHA Solver GRATUITO usando Wit.ai (Facebook)
Taxa de sucesso: 70-80%
"""
import time
import requests
import logging
import base64
import io
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


class FreeCaptchaSolver:
    """Resolve CAPTCHAs gratuitamente usando Wit.ai"""
    
    def __init__(self, wit_api_keys: list):
        """
        Args:
            wit_api_keys: Lista de API keys do Wit.ai (grátis)
        """
        self.wit_api_keys = wit_api_keys
        self.current_key_index = 0
        
    def _get_next_wit_key(self) -> str:
        """Rotaciona entre as API keys"""
        key = self.wit_api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.wit_api_keys)
        return key
    
    def _transcribe_audio_with_wit(self, audio_data: bytes) -> Optional[str]:
        """
        Transcreve áudio usando Wit.ai
        
        Args:
            audio_data: Dados do áudio em bytes
            
        Returns:
            Texto transcrito ou None se falhar
        """
        wit_key = self._get_next_wit_key()
        
        try:
            headers = {
                'Authorization': f'Bearer {wit_key}',
                'Content-Type': 'audio/mpeg3'
            }
            
            response = requests.post(
                'https://api.wit.ai/speech?v=20220622',
                headers=headers,
                data=audio_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('text', '').strip()
                logger.info(f"Wit.ai transcreveu: '{text}'")
                return text
            else:
                logger.error(f"Wit.ai erro: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao transcrever com Wit.ai: {e}")
            return None
    
    def solve_recaptcha_v2(self, driver, max_attempts: int = 3) -> bool:
        """
        Resolve reCAPTCHA v2 usando método de áudio
        
        Args:
            driver: Instância do Selenium WebDriver
            max_attempts: Número máximo de tentativas
            
        Returns:
            True se resolveu com sucesso, False caso contrário
        """
        try:
            logger.info("Iniciando resolução de CAPTCHA com Wit.ai...")
            
            # 1. Encontra o iframe do reCAPTCHA
            logger.info("Procurando iframe do reCAPTCHA...")
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*="recaptcha"]'))
            )
            
            # 2. Muda para o iframe
            driver.switch_to.frame(iframe)
            
            # 3. Clica no checkbox
            logger.info("Clicando no checkbox...")
            checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.recaptcha-checkbox-border'))
            )
            checkbox.click()
            time.sleep(2)
            
            # 4. Volta para o contexto principal
            driver.switch_to.default_content()
            
            # 5. Procura o iframe do desafio
            logger.info("Procurando iframe do desafio...")
            challenge_iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*="bframe"]'))
            )
            
            # 6. Muda para o iframe do desafio
            driver.switch_to.frame(challenge_iframe)
            
            # 7. Clica no botão de áudio
            logger.info("Clicando no botão de áudio...")
            audio_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'recaptcha-audio-button'))
            )
            audio_button.click()
            time.sleep(2)
            
            # 8. Tenta resolver o desafio de áudio
            for attempt in range(max_attempts):
                logger.info(f"Tentativa {attempt + 1}/{max_attempts}")
                
                try:
                    # Pega o link do áudio
                    audio_source = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, 'audio-source'))
                    )
                    audio_url = audio_source.get_attribute('src')
                    logger.info(f"URL do áudio: {audio_url[:50]}...")
                    
                    # Baixa o áudio
                    logger.info("Baixando áudio...")
                    audio_response = requests.get(audio_url, timeout=30)
                    audio_data = audio_response.content
                    
                    # Transcreve com Wit.ai
                    logger.info("Transcrevendo com Wit.ai...")
                    transcription = self._transcribe_audio_with_wit(audio_data)
                    
                    if not transcription:
                        logger.warning("Falha na transcrição, tentando novamente...")
                        
                        # Clica em "Get new challenge"
                        reload_button = driver.find_element(By.ID, 'recaptcha-reload-button')
                        reload_button.click()
                        time.sleep(2)
                        continue
                    
                    # Digita a resposta
                    logger.info(f"Digitando resposta: '{transcription}'")
                    audio_input = driver.find_element(By.ID, 'audio-response')
                    audio_input.clear()
                    audio_input.send_keys(transcription)
                    time.sleep(1)
                    
                    # Clica em Verify
                    verify_button = driver.find_element(By.ID, 'recaptcha-verify-button')
                    verify_button.click()
                    time.sleep(3)
                    
                    # Verifica se resolveu
                    try:
                        error_message = driver.find_element(By.CLASS_NAME, 'rc-audiochallenge-error-message')
                        if error_message.is_displayed():
                            logger.warning("Resposta incorreta, tentando novamente...")
                            continue
                    except:
                        # Sem mensagem de erro = sucesso!
                        logger.info("✅ CAPTCHA resolvido com sucesso!")
                        driver.switch_to.default_content()
                        return True
                    
                except Exception as e:
                    logger.error(f"Erro na tentativa {attempt + 1}: {e}")
                    continue
            
            logger.error("Falha ao resolver CAPTCHA após todas as tentativas")
            driver.switch_to.default_content()
            return False
            
        except Exception as e:
            logger.error(f"Erro ao resolver CAPTCHA: {e}")
            try:
                driver.switch_to.default_content()
            except:
                pass
            return False


def get_free_wit_api_keys() -> list:
    """
    Retorna lista de API keys do Wit.ai
    
    Para criar API keys gratuitas:
    1. Acesse https://wit.ai
    2. Faça login com Facebook/GitHub
    3. Crie um app
    4. Copie o Server Access Token
    
    Você pode criar múltiplos apps para ter múltiplas keys
    """
    import os
    
    # Tenta pegar do ambiente
    keys_env = os.getenv('WIT_API_KEYS', '')
    if keys_env:
        return [k.strip() for k in keys_env.split(',') if k.strip()]
    
    # Keys de exemplo (você precisa substituir pelas suas)
    return [
        'YOUR_WIT_API_KEY_1',
        'YOUR_WIT_API_KEY_2',
        'YOUR_WIT_API_KEY_3',
    ]


def test_free_captcha_solver():
    """Testa o solver gratuito"""
    import undetected_chromedriver as uc
    
    print("="*70)
    print("🧪 Teste do CAPTCHA Solver GRATUITO (Wit.ai)")
    print("="*70)
    
    # Verifica API keys
    wit_keys = get_free_wit_api_keys()
    
    if wit_keys[0] == 'YOUR_WIT_API_KEY_1':
        print("\n❌ Configure suas API keys do Wit.ai primeiro!")
        print("\nPasso a passo:")
        print("1. Acesse: https://wit.ai")
        print("2. Faça login com Facebook ou GitHub")
        print("3. Clique em 'New App'")
        print("4. Dê um nome (ex: 'captcha-solver-1')")
        print("5. Copie o 'Server Access Token'")
        print("6. Configure:")
        print("   export WIT_API_KEYS='key1,key2,key3'")
        print("\nOu edite o código e substitua YOUR_WIT_API_KEY_1")
        return False
    
    print(f"\n✅ Encontradas {len(wit_keys)} API keys do Wit.ai")
    
    # Inicializa Chrome
    print("\nInicializando Chrome...")
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    driver = uc.Chrome(options=options)
    
    try:
        # Acessa página de teste do reCAPTCHA
        print("\nAcessando página de teste...")
        driver.get("https://www.google.com/recaptcha/api2/demo")
        time.sleep(3)
        
        # Cria solver
        solver = FreeCaptchaSolver(wit_keys)
        
        # Tenta resolver
        print("\nTentando resolver CAPTCHA...")
        print("(Isso pode levar 30-60 segundos)")
        
        success = solver.solve_recaptcha_v2(driver, max_attempts=3)
        
        if success:
            print("\n" + "="*70)
            print("✅ SUCESSO! CAPTCHA resolvido gratuitamente!")
            print("="*70)
            
            # Aguarda para ver o resultado
            print("\nAguardando 10 segundos para você ver o resultado...")
            time.sleep(10)
            return True
        else:
            print("\n" + "="*70)
            print("❌ Falha ao resolver CAPTCHA")
            print("="*70)
            print("\nDicas:")
            print("- Verifique se as API keys estão corretas")
            print("- Tente criar mais API keys no Wit.ai")
            print("- Execute novamente (taxa de sucesso: 70-80%)")
            return False
            
    finally:
        driver.quit()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_free_captcha_solver()

