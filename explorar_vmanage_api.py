#!/usr/bin/env python3
"""
Explorar API de vManage para encontrar endpoints de flujos
"""

import os
import sys
import requests
import urllib3
from dotenv import load_dotenv
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

vmanage_host = os.getenv('VMANAGE_HOST')
username = os.getenv('VMANAGE_USERNAME')
password = os.getenv('VMANAGE_PASSWORD')

# Autenticar
session = requests.Session()
session.verify = False

auth_url = f"https://{vmanage_host}/j_security_check"
auth_response = session.post(auth_url, data={'j_username': username, 'j_password': password})

token_url = f"https://{vmanage_host}/dataservice/client/token"
token_response = session.get(token_url)
if token_response.status_code == 200:
    session.headers['X-XSRF-TOKEN'] = token_response.text

print("="*70)
print("🔍 EXPLORANDO ENDPOINTS DE APLICACIONES Y FLUJOS")
print("="*70)

# Lista de endpoints a probar con diferentes métodos
test_cases = [
    # Statistics - Monitoring
    ("GET", "/dataservice/statistics/settings"),
    ("GET", "/dataservice/statistics/settings/status"),
    
    # DPI con parámetros de query
    ("GET", "/dataservice/data/dpi/applications/aggregation"),
    ("GET", "/dataservice/data/dpi/summary"),
    
    # Monitor - Real-time
    ("GET", "/dataservice/monitor/dpi/applications"),
    
    # Device specific DPI
    ("POST", "/dataservice/device/dpi/applications", {
        "deviceId": "10.95.3.3"  # IP de un dispositivo conocido
    }),
    
    # Flows
    ("GET", "/dataservice/statistics/flows"),
    ("GET", "/dataservice/data/flows"),
]

for method, endpoint, *payload in test_cases:
    url = f"https://{vmanage_host}{endpoint}"
    print(f"\n🔍 {method} {endpoint}")
    
    try:
        if method == "GET":
            response = session.get(url, timeout=10)
        else:
            response = session.post(url, json=payload[0] if payload else {}, timeout=10)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Success!")
                
                if isinstance(data, dict):
                    if 'data' in data:
                        print(f"      Records: {len(data['data'])}")
                        if len(data['data']) > 0:
                            keys = list(data['data'][0].keys())
                            print(f"      Keys: {keys[:10]}")
                    else:
                        print(f"      Keys: {list(data.keys())[:10]}")
                        
            except:
                print(f"   Content (first 150 chars): {response.text[:150]}")
                
        elif response.status_code == 400:
            print(f"   ⚠️  Bad Request")
            try:
                error = response.json()
                print(f"      Error: {error}")
            except:
                print(f"      Text: {response.text[:100]}")
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:60]}")

# Intentar obtener la documentación de API
print(f"\n" + "="*70)
print(f"📚 Intentando obtener documentación de API")
print("="*70)

doc_endpoints = [
    "/dataservice/swagger",
    "/apidocs",
    "/api-docs",
    "/dataservice/docs",
]

for endpoint in doc_endpoints:
    url = f"https://{vmanage_host}{endpoint}"
    print(f"\n🔍 {endpoint}")
    try:
        response = session.get(url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Disponible! Abre en navegador:")
            print(f"      https://{vmanage_host}{endpoint}")
    except:
        print(f"   ❌ No disponible")

print(f"\n" + "="*70)
print(f"💡 ACCESO VÍA GUI")
print("="*70)
print(f"""
Para ver flujos con IPs origen/destino:

1. Abre en navegador: https://{vmanage_host}
2. Login: {username}
3. Navega a: Monitor → Applications
4. Selecciona un dispositivo
5. Busca la aplicación específica (ej: W3-Relaciones-familiare)
6. Verás tabla con flujos incluyendo:
   - Source IP (Usuario)
   - Destination IP (Servidor)
   - Bytes
   - Packets
   - QoE metrics

Mientras exploramos la API, puedes exportar esos datos manualmente
desde la GUI para análisis inmediato.
""")

print(f"\n🔧 ALTERNATIVA: Browser DevTools")
print(f"="*70)
print(f"""
1. Abre vManage en Chrome con DevTools (F12)
2. Ve a Monitor → Applications
3. En Network tab, filtra por 'XHR'
4. Navega a las aplicaciones que te interesan
5. Copia las URLs de las peticiones exitosas
6. Las URLs reales que usa la GUI nos darán los endpoints correctos

Las peticiones suelen ir a:
- /dataservice/statistics/...
- /dataservice/data/...
- Con parámetros query como: ?deviceId=X&hours=24
""")
