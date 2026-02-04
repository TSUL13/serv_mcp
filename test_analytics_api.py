#!/usr/bin/env python3
"""
Test directo de Analytics API
"""

import requests
import urllib3
import browser_cookie3

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

print(f"✅ Cookie encontrada: {session_cookie[:50]}...")

# Configurar sesión
session = requests.Session()
session.verify = False
session.cookies.set('session', session_cookie, domain='us02.analytics.sdwan.cisco.com', path='/analytics')

base_url = "https://us02.analytics.sdwan.cisco.com"

# Probar diferentes endpoints
endpoints = [
    "/analytics/api/applications",
    "/analytics/api/sites",
    "/analytics/api/flows",
    "/analytics/api/v1/applications",
    "/analytics/api/v2/applications",
    "/analytics/api/data/applications",
    "/api/dataservice/reporting/applications",
]

print("\n" + "=" * 70)
print("PROBANDO ENDPOINTS DE API")
print("=" * 70)

for endpoint in endpoints:
    url = f"{base_url}{endpoint}"
    print(f"\n📍 {endpoint}")
    
    try:
        response = session.get(url, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ JSON recibido")
                
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"   Keys: {keys}")
                    if 'data' in data and isinstance(data['data'], list):
                        print(f"   📊 {len(data['data'])} elementos en 'data'")
                elif isinstance(data, list):
                    print(f"   📊 {len(data)} elementos")
                    
                print(f"   Preview: {str(data)[:300]}...")
            except:
                print(f"   ⚠️  No JSON: {response.text[:200]}")
        else:
            print(f"   ❌ Error: {response.text[:150]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
