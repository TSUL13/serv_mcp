#!/usr/bin/env python3
"""
Extraer cookies de Analytics Cloud desde el navegador
"""

import browser_cookie3
import sys

print("=" * 70)
print("EXTRAYENDO COOKIES DE ANALYTICS CLOUD")
print("=" * 70)

domains = [
    'analytics.sdwan.cisco.com',
    'us02.analytics.sdwan.cisco.com',
    '.cisco.com',
    '.sdwan.cisco.com'
]

try:
    # Intentar Chrome primero
    cj = browser_cookie3.chrome(domain_name='cisco.com')
    
    print("\n🍪 Cookies encontradas en Chrome:\n")
    
    cookies_analytics = {}
    for cookie in cj:
        if 'analytics' in cookie.domain or 'cisco' in cookie.domain:
            print(f"   {cookie.name}: {cookie.value[:50]}...")
            print(f"      Domain: {cookie.domain}")
            print(f"      Path: {cookie.path}")
            cookies_analytics[cookie.name] = cookie.value
    
    if cookies_analytics:
        print("\n✅ Cookies de Analytics encontradas:")
        for name, value in cookies_analytics.items():
            print(f"   {name} = {value[:50]}...")
    else:
        print("\n⚠️  No se encontraron cookies específicas de Analytics")
        print("   Asegúrate de estar logueado en https://us02.analytics.sdwan.cisco.com")
        
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

print("\n" + "=" * 70)
print("INSTRUCCIONES:")
print("=" * 70)
print("""
1. Abre Chrome/Firefox
2. Ve a: https://us02.analytics.sdwan.cisco.com/analytics/v4/applications
3. Abre DevTools (F12) → Network tab
4. Recarga la página
5. Busca llamadas a API (XHR/Fetch)
6. Copia el endpoint exacto que usa
""")
