#!/usr/bin/env python3
"""
Test con el payload correcto de Analytics Cloud
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
csrf_token = None
overlay_id = None

for cookie in cj:
    if cookie.name == 'session':
        session_cookie = cookie.value
    elif cookie.name == 'okta-oauth-state':
        csrf_token = cookie.value
    elif cookie.name == 'cl-overlay-id':
        overlay_id = cookie.value

if not session_cookie:
    print("❌ No se encontró cookie de session")
    exit(1)

if not csrf_token:
    print("⚠️  No se encontró CSRF token")
    
if not overlay_id:
    print("⚠️  No se encontró overlay-id")

print(f"✅ Session cookie encontrada")
print(f"✅ CSRF token: {csrf_token[:50] if csrf_token else 'N/A'}...")
print(f"✅ Overlay ID: {overlay_id}")

session = requests.Session()
session.verify = False

# Agregar todas las cookies de Analytics
for cookie in cj:
    if 'analytics.sdwan.cisco.com' in cookie.domain or 'cisco.com' in cookie.domain:
        session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)

# Headers necesarios (exactamente como en el navegador)
session.headers.update({
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'x-csrftoken': csrf_token if csrf_token else '',
    'sdwan-overlay': overlay_id if overlay_id else '',
    'Origin': 'https://us02.analytics.sdwan.cisco.com',
    'Referer': 'https://us02.analytics.sdwan.cisco.com/analytics/v4/overview',
})

url = "https://us02.analytics.sdwan.cisco.com/analytics/api/v4/dataservice/aggregate/applications"

# Calcular timestamps - Analytics usa intervalos de 5 minutos redondeados
now = datetime.now()
# Redondear a intervalos de 5 minutos
minute = (now.minute // 5) * 5
end_time = now.replace(minute=minute, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

start = now - timedelta(hours=12)
start_minute = (start.minute // 5) * 5
start_time = start.replace(minute=start_minute, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

# Payload exacto como en el navegador (SIN sort)
payload = {
    "time_frame": "12h",
    "entry_ts": {
        "start": start_time,
        "end": end_time
    }
}

print("\n" + "=" * 70)
print("TEST CON PAYLOAD CORRECTO")
print("=" * 70)
print(f"URL: {url}")
print(f"Payload:\n{json.dumps(payload, indent=2)}\n")

try:
    response = session.post(url, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ SUCCESS! Datos recibidos")
        print(f"Type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            
            if 'data' in data:
                apps = data['data']
            else:
                apps = [data]
        elif isinstance(data, list):
            apps = data
        else:
            apps = []
        
        print(f"\n📊 Total de aplicaciones: {len(apps)}")
        
        if apps:
            print(f"\n🔍 EJEMPLO DE APLICACIÓN:\n")
            print(json.dumps(apps[0], indent=2))
            
            print(f"\n🏆 TOP 10 APLICACIONES MÁS USADAS:\n")
            
            for i, app in enumerate(apps[:10], 1):
                name = app.get('name', app.get('application', 'Unknown'))
                usage = app.get('usage', app.get('total_bytes', 0))
                family = app.get('family', app.get('app_family', 'N/A'))
                site_count = app.get('site_count', app.get('sites', 'N/A'))
                
                print(f"{i}. {name}")
                print(f"   Familia: {family}")
                print(f"   Uso: {usage / (1024**3):.2f} GB")
                print(f"   Sitios: {site_count}")
                print()
                
            print("\n✅✅✅ ENDPOINT FUNCIONAL!")
            
    else:
        print(f"❌ Error {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Exception: {str(e)}")
    import traceback
    traceback.print_exc()
