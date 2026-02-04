#!/usr/bin/env python3
"""
Test del endpoint correcto de Analytics
"""

import requests
import urllib3
import browser_cookie3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Extraer cookie de session
cj = browser_cookie3.chrome(domain_name='us02.analytics.sdwan.cisco.com')
session_cookie = None

for cookie in cj:
    if cookie.name == 'session':
        session_cookie = cookie.value
        break

if not session_cookie:
    print("❌ No se encontró cookie de session")
    exit(1)

print(f"✅ Cookie encontrada")

# Configurar sesión
session = requests.Session()
session.verify = False
session.cookies.set('session', session_cookie, domain='us02.analytics.sdwan.cisco.com', path='/analytics')

# Endpoint correcto
url = "https://us02.analytics.sdwan.cisco.com/analytics/api/v4/dataservice/aggregate/applications"

print("\n" + "=" * 70)
print("TEST DEL ENDPOINT CORRECTO")
print("=" * 70)
print(f"URL: {url}\n")

try:
    response = session.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ JSON recibido")
        print(f"Type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            
            if 'data' in data:
                apps = data['data']
                print(f"\n📊 Total de aplicaciones: {len(apps)}")
                
                if apps:
                    print(f"\n🔍 Ejemplo de aplicación:\n")
                    print(json.dumps(apps[0], indent=2))
                    
                    print(f"\n🏆 TOP 10 APLICACIONES:\n")
                    
                    # Ordenar por usage
                    if 'usage' in apps[0]:
                        sorted_apps = sorted(apps, key=lambda x: x.get('usage', 0), reverse=True)
                    else:
                        sorted_apps = apps
                    
                    for i, app in enumerate(sorted_apps[:10], 1):
                        name = app.get('name', 'Unknown')
                        usage = app.get('usage', 0)
                        family = app.get('family', 'N/A')
                        print(f"{i}. {name}")
                        print(f"   Familia: {family}")
                        print(f"   Uso: {usage / (1024**3):.2f} GB")
                        print()
        elif isinstance(data, list):
            print(f"\n📊 Total de aplicaciones: {len(data)}")
            if data:
                print(f"\n🔍 Ejemplo:\n")
                print(json.dumps(data[0], indent=2))
    else:
        print(f"❌ Error {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"❌ Exception: {str(e)}")
