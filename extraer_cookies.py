#!/usr/bin/env python3
"""
Extrae cookies del navegador local para uso en servidor remoto
"""
import sys
import os

# Agregar path actual para importar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_cookies import BrowserCookieExtractor

def main():
    vmanage_host = "vmanage.cjf.gob.mx"
    
    print("🔍 Buscando cookies en navegadores locales...", file=sys.stderr)
    
    try:
        extractor = BrowserCookieExtractor(vmanage_host)
        jsessionid, xsrf_token = extractor.get_cookies()
        
        if jsessionid and xsrf_token:
            print("✅ Cookies encontradas", file=sys.stderr)
            print(f"VMANAGE_JSESSIONID={jsessionid}")
            print(f"VMANAGE_XSRF_TOKEN={xsrf_token}")
            return 0
        else:
            print("❌ Error: No se encontraron cookies", file=sys.stderr)
            print("", file=sys.stderr)
            print("Asegúrate de:", file=sys.stderr)
            print("  1. Tener sesión activa en vManage en Firefox/Chrome", file=sys.stderr)
            print("  2. El navegador esté cerrado (o espera unos segundos)", file=sys.stderr)
            print(f"  3. El dominio sea exactamente: {vmanage_host}", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
