"""
Sistema de extracción automática de cookies del navegador para vManage
Soporta: 
  1. Variables de entorno (para servidores remotos)
  2. Extracción de navegador local (Firefox, Chrome, Edge)
"""
import browser_cookie3
import time
import os
from datetime import datetime
from typing import Optional, Tuple

class BrowserCookieExtractor:
    """Extractor de cookies del navegador para vManage"""
    
    def __init__(self, vmanage_host: str):
        self.vmanage_host = vmanage_host
        self.last_extraction = None
        self.from_env = False
        
        # PRIORIDAD 1: Intentar primero variables de entorno (para servidor remoto)
        env_jsessionid = os.getenv('VMANAGE_JSESSIONID')
        env_xsrf = os.getenv('VMANAGE_XSRF_TOKEN')
        
        if env_jsessionid and env_xsrf:
            print(f"✅ Usando cookies de variables de entorno")
            print(f"   JSESSIONID: {env_jsessionid[:20]}...")
            print(f"   XSRF-TOKEN: {env_xsrf[:20]}...")
            self.jsessionid = env_jsessionid
            self.xsrf_token = env_xsrf
            self.last_extraction = datetime.now()
            self.from_env = True
        else:
            # PRIORIDAD 2: Extraer del navegador local
            self.jsessionid = None
            self.xsrf_token = None
            self.from_env = False
        
    def extract_cookies(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrae JSESSIONID y X-XSRF-TOKEN del navegador
        
        Si solo encuentra JSESSIONID, obtiene el token haciendo una petición al API.
        
        Returns:
            Tuple con (JSESSIONID, XSRF_TOKEN) o (None, None) si falla
        """
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        browsers = [
            ("Chrome", browser_cookie3.chrome),
            ("Firefox", browser_cookie3.firefox),
            ("Edge", browser_cookie3.edge),
            ("Chromium", browser_cookie3.chromium),
        ]
        
        for browser_name, browser_func in browsers:
            try:
                cookies = browser_func(domain_name=self.vmanage_host)
                jsessionid = None
                xsrf_token = None
                
                for cookie in cookies:
                    if cookie.name == "JSESSIONID":
                        jsessionid = cookie.value
                    elif cookie.name == "XSRF-TOKEN":
                        xsrf_token = cookie.value
                
                # Si tenemos ambas cookies, perfecto
                if jsessionid and xsrf_token:
                    self.jsessionid = jsessionid
                    self.xsrf_token = xsrf_token
                    self.last_extraction = datetime.now()
                    print(f"✅ Cookies completas extraídas de {browser_name}")
                    print(f"   JSESSIONID: {jsessionid[:20]}...")
                    print(f"   XSRF-TOKEN: {xsrf_token[:20]}...")
                    return jsessionid, xsrf_token
                
                # Si solo tenemos JSESSIONID, obtener token del API
                elif jsessionid:
                    print(f"🔄 JSESSIONID encontrado en {browser_name}, obteniendo token...")
                    
                    try:
                        session = requests.Session()
                        session.verify = False
                        session.cookies.set("JSESSIONID", jsessionid)
                        
                        token_response = session.get(
                            f"https://{self.vmanage_host}/dataservice/client/token",
                            timeout=10
                        )
                        
                        if token_response.status_code == 200:
                            xsrf_token = token_response.text
                            self.jsessionid = jsessionid
                            self.xsrf_token = xsrf_token
                            self.last_extraction = datetime.now()
                            print(f"✅ Token obtenido exitosamente")
                            print(f"   JSESSIONID: {jsessionid[:20]}...")
                            print(f"   XSRF-TOKEN: {xsrf_token[:20]}...")
                            return jsessionid, xsrf_token
                        else:
                            print(f"⚠️  No se pudo obtener token (HTTP {token_response.status_code})")
                            
                    except Exception as e:
                        print(f"⚠️  Error al obtener token: {str(e)}")
                    
            except Exception as e:
                # Silenciar errores de navegadores no instalados
                continue
        
        # Si no se encontraron en ningún navegador
        print("⚠️  No se encontraron cookies en ningún navegador")
        print("   Asegúrate de:")
        print("   1. Haber iniciado sesión en vManage en tu navegador")
        print("   2. Tener la sesión activa")
        print("   3. Usar Chrome, Firefox o Edge")
        return None, None
    
    def get_cookies(self, force_refresh: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """
        Obtiene las cookies, extrayéndolas si es necesario
        
        Prioridad:
          1. Variables de entorno (VMANAGE_JSESSIONID, VMANAGE_XSRF_TOKEN)
          2. Extracción del navegador local
        
        Args:
            force_refresh: Si es True, extrae nuevas cookies aunque tenga cached
            
        Returns:
            Tuple con (JSESSIONID, XSRF_TOKEN)
        """
        # Si tenemos cookies de variables de entorno y no se fuerza refresh, usar esas
        if self.from_env and not force_refresh:
            return self.jsessionid, self.xsrf_token
        
        # Si no hay cookies o se fuerza refresh, extraer del navegador
        if force_refresh or not self.jsessionid or not self.xsrf_token:
            return self.extract_cookies()
        
        # Retornar cookies existentes
        return self.jsessionid, self.xsrf_token
    
    def get_cookies_dict(self, force_refresh: bool = False) -> dict:
        """
        Obtiene las cookies como diccionario
        
        Args:
            force_refresh: Si es True, extrae nuevas cookies aunque tenga cached
            
        Returns:
            Dict con {'JSESSIONID': '...', 'XSRF-TOKEN': '...'}
        """
        jsessionid, xsrf_token = self.get_cookies(force_refresh)
        return {
            'JSESSIONID': jsessionid,
            'XSRF-TOKEN': xsrf_token
        }
    
    def should_refresh(self, max_age_seconds: int = 300) -> bool:
        """
        Determina si las cookies deberían refrescarse
        
        Args:
            max_age_seconds: Edad máxima en segundos (default: 5 minutos)
            
        Returns:
            True si las cookies deberían refrescarse
        """
        if not self.last_extraction:
            return True
        
        age = (datetime.now() - self.last_extraction).total_seconds()
        return age > max_age_seconds


def test_extraction():
    """Función de prueba para verificar la extracción de cookies"""
    print("=" * 70)
    print("  🍪 TEST DE EXTRACCIÓN DE COOKIES DEL NAVEGADOR")
    print("=" * 70)
    print()
    
    # Intentar extraer cookies
    extractor = BrowserCookieExtractor("vmanage.cjf.gob.mx")
    jsessionid, xsrf_token = extractor.extract_cookies()
    
    if jsessionid and xsrf_token:
        print("\n✅ ¡Extracción exitosa!")
        print(f"   JSESSIONID: {jsessionid}")
        print(f"   XSRF-TOKEN: {xsrf_token}")
        print("\n💡 Ahora el servidor MCP puede usar estas cookies automáticamente")
    else:
        print("\n❌ No se pudieron extraer las cookies")
        print("\n📋 Pasos para solucionar:")
        print("   1. Abre Chrome, Firefox o Edge")
        print("   2. Ve a https://vmanage.cjf.gob.mx")
        print("   3. Inicia sesión con tus credenciales")
        print("   4. Deja la pestaña abierta")
        print("   5. Ejecuta este script nuevamente")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_extraction()
