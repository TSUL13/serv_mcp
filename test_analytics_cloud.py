#!/usr/bin/env python3
"""
Test de conexión a Cisco Analytics Cloud
"""

import sys
import os
sys.path.insert(0, '/home/tsul/Documentos/serv_mcp')

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

# Probar con las mismas cookies de vManage
session = requests.Session()
session.verify = False
session.headers.update({
    'Cookie': f"JSESSIONID={os.getenv('VMANAGE_JSESSIONID')}",
    'X-XSRF-TOKEN': os.getenv('VMANAGE_XSRF_TOKEN'),
    'Content-Type': 'application/json'
})

analytics_base = "https://us02.analytics.sdwan.cisco.com"

print("=" * 70)
print("TEST DE CISCO ANALYTICS CLOUD")
print("=" * 70)

endpoints_test = [
    "/analytics/v4/applications",
    "/analytics/v4/applications/summary",
    "/analytics/v4/sites",
    "/api/analytics/v4/applications",
]

for endpoint in endpoints_test:
    print(f"\n📍 Probando: {endpoint}")
    url = f"{analytics_base}{endpoint}"
    
    try:
        response = session.get(url, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and 'data' in data:
                    count = len(data['data']) if isinstance(data['data'], list) else 1
                    print(f"   ✅ {count} elementos")
                    print(f"   Preview: {str(data)[:200]}")
                elif isinstance(data, list):
                    print(f"   ✅ {len(data)} elementos")
                    print(f"   Preview: {str(data[0] if data else 'empty')[:200]}")
                else:
                    print(f"   ✅ Datos recibidos")
                    print(f"   Preview: {str(data)[:200]}")
            except Exception as e:
                print(f"   ⚠️  Response: {response.text[:300]}")
        elif response.status_code == 401:
            print(f"   ❌ No autorizado - necesita autenticación diferente")
        elif response.status_code == 404:
            print(f"   ❌ Endpoint no encontrado")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Excepción: {str(e)}")

print("\n" + "=" * 70)
print("CONCLUSIÓN:")
print("=" * 70)
print("""
Si funciona, actualizaré las funciones para usar Analytics Cloud.
Si no funciona, necesitamos obtener el token/cookies específicos de Analytics.
""")
