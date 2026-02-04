#!/usr/bin/env python3
"""
Test con parámetros de Analytics
"""

import requests
import urllib3
import browser_cookie3
import json
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Extraer cookie
cj = browser_cookie3.chrome(domain_name='us02.analytics.sdwan.cisco.com')
session_cookie = None

for cookie in cj:
    if cookie.name == 'session':
        session_cookie = cookie.value
        break

if not session_cookie:
    print("❌ No se encontró cookie")
    exit(1)

print(f"✅ Cookie encontrada")

session = requests.Session()
session.verify = False
session.cookies.set('session', session_cookie, domain='us02.analytics.sdwan.cisco.com', path='/analytics')

base_url = "https://us02.analytics.sdwan.cisco.com/analytics/api/v4/dataservice/aggregate/applications"

# Calcular timestamps
end_time = int(datetime.now().timestamp() * 1000)
start_time = int((datetime.now() - timedelta(hours=12)).timestamp() * 1000)

print("\n" + "=" * 70)
print("PROBANDO CON DIFERENTES PARÁMETROS")
print("=" * 70)

# Probar diferentes combinaciones
params_combinations = [
    {},  # Sin parámetros
    {'startDate': start_time, 'endDate': end_time},
    {'timeRange': '12h'},
    {'timeRange': 'last_12_hours'},
    {'duration': '12h'},
]

for i, params in enumerate(params_combinations, 1):
    print(f"\n📍 Test {i}: {params}")
    
    try:
        response = session.get(base_url, params=params, timeout=20)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                count = len(data['data'])
                print(f"   ✅ {count} aplicaciones")
                if count > 0:
                    print(f"   Ejemplo: {data['data'][0].get('name', 'N/A')}")
                    print(f"   ✅✅ ENDPOINT FUNCIONAL ENCONTRADO!")
                    print(f"   Parámetros: {params}")
                    break
            elif isinstance(data, list):
                print(f"   ✅ {len(data)} aplicaciones")
                break
        else:
            print(f"   ❌ Error: {response.text[:100]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")

print("\n" + "=" * 70)
print("RECOMENDACIÓN:")
print("=" * 70)
print("""
En DevTools, busca la llamada y revisa:
- Query String Parameters (pestaña Headers)
- Request Payload (si es POST)
- Copia todos los parámetros que veas
""")
