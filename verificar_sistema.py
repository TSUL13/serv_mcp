#!/usr/bin/env python3
"""
Script rápido para verificar el sistema de cookies antes de usar CLI o MCP
"""
import sys
from browser_cookies import BrowserCookieExtractor
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def verificar_sistema():
    """Verifica que todo está listo para usar"""
    print("\n" + "=" * 70)
    print("  🔍 VERIFICACIÓN DEL SISTEMA DE COOKIES")
    print("=" * 70)
    
    # Paso 1: Verificar extracción de cookies
    print("\n[1/3] Extrayendo cookies del navegador...")
    extractor = BrowserCookieExtractor("vmanage.cjf.gob.mx")
    jsessionid, xsrf_token = extractor.extract_cookies()
    
    if not jsessionid or not xsrf_token:
        print("❌ FALLO: No se encontraron cookies\n")
        print("📋 Pasos para solucionar:")
        print("   1. Abre Chrome, Firefox o Edge")
        print("   2. Ve a https://vmanage.cjf.gob.mx")
        print("   3. Inicia sesión con tus credenciales")
        print("   4. Deja la pestaña abierta")
        print("   5. Ejecuta este script nuevamente\n")
        return False
    
    print(f"✅ Cookies extraídas correctamente")
    print(f"   JSESSIONID: {jsessionid[:30]}...")
    print(f"   XSRF-TOKEN: {xsrf_token[:30]}...")
    
    # Paso 2: Verificar que las cookies funcionan
    print("\n[2/3] Verificando validez de las cookies...")
    session = requests.Session()
    session.verify = False
    session.cookies.set("JSESSIONID", jsessionid)
    session.headers.update({
        "X-XSRF-TOKEN": xsrf_token,
        "Content-Type": "application/json"
    })
    
    try:
        response = session.get(
            "https://vmanage.cjf.gob.mx/dataservice/device",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            device_count = len(data.get('data', []))
            print(f"✅ Cookies válidas - {device_count} dispositivos encontrados")
        else:
            print(f"❌ FALLO: Cookies no válidas (HTTP {response.status_code})")
            print("   Tu sesión en el navegador puede haber expirado")
            print("   Refresca la página en el navegador e inicia sesión nuevamente")
            return False
            
    except Exception as e:
        print(f"❌ FALLO: Error al consultar API - {str(e)}")
        return False
    
    # Paso 3: Verificar entorno Python
    print("\n[3/3] Verificando entorno Python...")
    try:
        import fastmcp
        import browser_cookie3
        print("✅ Todas las dependencias instaladas")
    except ImportError as e:
        print(f"⚠️  ADVERTENCIA: Falta dependencia - {str(e)}")
        print("   Ejecuta: pip install fastmcp browser-cookie3")
        return False
    
    # Todo OK
    print("\n" + "=" * 70)
    print("  ✨ ¡SISTEMA LISTO!")
    print("=" * 70)
    print("\n📌 Puedes usar:")
    print("   • python cli.py           - CLI independiente")
    print("   • Claude Desktop          - Servidor MCP con IA")
    print("\n💡 Mantén vManage abierto en tu navegador mientras trabajas\n")
    return True


if __name__ == "__main__":
    resultado = verificar_sistema()
    sys.exit(0 if resultado else 1)
