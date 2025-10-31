"""
Módulo de resolução de CAPTCHA usando 2Captcha
"""
import time
import requests
import logging

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Resolve CAPTCHAs usando 2Captcha API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://2captcha.com"
        
    def solve_recaptcha_v2(self, site_key: str, page_url: str, timeout: int = 120) -> str:
        """
        Resolve reCAPTCHA v2
        
        Args:
            site_key: Site key do reCAPTCHA (data-sitekey)
            page_url: URL da página com CAPTCHA
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            Token de resposta do CAPTCHA
        """
        logger.info(f"Enviando CAPTCHA para resolução...")
        
        # 1. Envia o CAPTCHA
        submit_url = f"{self.base_url}/in.php"
        params = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': page_url,
            'json': 1
        }
        
        try:
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()
            
            if result.get('status') != 1:
                error = result.get('request', 'Unknown error')
                logger.error(f"Erro ao enviar CAPTCHA: {error}")
                raise Exception(f"2Captcha error: {error}")
            
            captcha_id = result.get('request')
            logger.info(f"CAPTCHA enviado, ID: {captcha_id}")
            
        except Exception as e:
            logger.error(f"Erro ao enviar CAPTCHA: {e}")
            raise
        
        # 2. Aguarda resolução (polling)
        result_url = f"{self.base_url}/res.php"
        start_time = time.time()
        
        logger.info("Aguardando resolução do CAPTCHA...")
        
        while time.time() - start_time < timeout:
            time.sleep(5)  # Aguarda 5 segundos entre tentativas
            
            try:
                response = requests.get(result_url, params={
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }, timeout=30)
                
                result = response.json()
                
                if result.get('status') == 1:
                    token = result.get('request')
                    logger.info(f"✅ CAPTCHA resolvido! Token: {token[:50]}...")
                    return token
                
                elif result.get('request') == 'CAPCHA_NOT_READY':
                    elapsed = int(time.time() - start_time)
                    logger.debug(f"CAPTCHA ainda não resolvido... ({elapsed}s)")
                    continue
                
                else:
                    error = result.get('request', 'Unknown error')
                    logger.error(f"Erro ao buscar resultado: {error}")
                    raise Exception(f"2Captcha error: {error}")
                    
            except Exception as e:
                logger.warning(f"Erro ao verificar status: {e}")
                continue
        
        # Timeout
        logger.error(f"Timeout ao resolver CAPTCHA ({timeout}s)")
        raise TimeoutError(f"CAPTCHA não foi resolvido em {timeout}s")
    
    def get_balance(self) -> float:
        """Retorna saldo da conta 2Captcha"""
        try:
            response = requests.get(f"{self.base_url}/res.php", params={
                'key': self.api_key,
                'action': 'getbalance',
                'json': 1
            }, timeout=10)
            
            result = response.json()
            
            if result.get('status') == 1:
                balance = float(result.get('request', 0))
                return balance
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Erro ao buscar saldo: {e}")
            return 0.0


def test_captcha_solver():
    """Testa o solver de CAPTCHA"""
    import os
    
    api_key = os.getenv('CAPTCHA_API_KEY', '')
    
    if not api_key:
        print("❌ Configure a variável CAPTCHA_API_KEY")
        print("   Exemplo: export CAPTCHA_API_KEY='sua_chave_aqui'")
        return False
    
    solver = CaptchaSolver(api_key)
    
    # Verifica saldo
    print("Verificando saldo...")
    balance = solver.get_balance()
    print(f"Saldo: ${balance:.4f}")
    
    if balance < 0.001:
        print("⚠️  Saldo insuficiente. Adicione créditos em https://2captcha.com")
        return False
    
    print("\n✅ API Key válida e com saldo!")
    print(f"   Você pode resolver ~{int(balance / 0.001)} CAPTCHAs")
    
    return True


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_captcha_solver()

