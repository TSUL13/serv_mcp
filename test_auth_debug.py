#!/usr/bin/env python3
"""Test de autenticación detallado con debug"""

import os
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

vmanage_ip = os.getenv('VMANAGE_IP')
username = os.getenv('VMANAGE_USERNAME')
password = os.getenv('VMANAGE_PASSWORD')

print("\n" + "=" * 70)
print("  🔍 TEST DE AUTENTICACIÓN DETALLADO")
print("=" * 70)
print(f"\nServidor: {vmanage_ip}")
print(f"Usuario: {username}")
print(f"Password: {'*' * len(password)}")

base_url = f"https://{vmanage_ip}"
session = requests.Session()
session.verify = False

print("\n🔄 PASO 1: Intentando login...")
login_url = f"{base_url}/j_security_check"

payload = {
    'j_username': username,
    'j_password': password
}

print(f"   URL: {login_url}")
print(f"   Payload: j_username={username}, j_password={'*' * len(password)}")

try:
    response = session.post(login_url, data=payload, timeout=30)
    
    print(f"\n✅ Respuesta recibida:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"   Cookies: {dict(session.cookies)}")
    print(f"   URL Final: {response.url}")
    
    # Verificar si hay JSESSIONID
    if 'JSESSIONID' in session.cookies:
        print("\n✅ JSESSIONID encontrado!")
        
        print("\n🔄 PASO 2: Obteniendo token XSRF...")
        token_url = f"{base_url}/dataservice/client/token"
        token_response = session.get(token_url, timeout=30)
        
        print(f"   Status Code: {token_response.status_code}")
        
        if token_response.status_code == 200:
            token = token_response.text
            print(f"   Token: {token[:20]}..." if len(token) > 20 else f"   Token: {token}")
            
            session.headers.update({
                'X-XSRF-TOKEN': token,
                'Content-Type': 'application/json'
            })
            
            print("\n🔄 PASO 3: Probando consulta de dispositivos...")
            device_url = f"{base_url}/dataservice/device"
            device_response = session.get(device_url, timeout=30)
            
            print(f"   Status Code: {device_response.status_code}")
            
            if device_response.status_code == 200:
                try:
                    data = device_response.json()
                    if 'data' in data:
                        print(f"\n🎉 ¡ÉXITO! Encontrados {len(data['data'])} dispositivos")
                        for i, dev in enumerate(data['data'][:3], 1):
                            print(f"   {i}. {dev.get('host-name', 'N/A')} - {dev.get('system-ip', 'N/A')}")
                    else:
                        print(f"\n❌ Respuesta sin 'data': {data}")
                except Exception as e:
                    print(f"\n❌ Error parseando JSON: {e}")
                    print(f"   Respuesta: {device_response.text[:200]}")
            else:
                print(f"\n❌ Error en consulta de dispositivos")
                print(f"   Respuesta: {device_response.text[:500]}")
        else:
            print(f"\n❌ Error obteniendo token")
            print(f"   Respuesta: {token_response.text[:500]}")
    else:
        print("\n❌ No se encontró JSESSIONID - Login falló")
        print(f"   Contenido de respuesta (primeros 500 chars):")
        print(f"   {response.text[:500]}")
        
        # Verificar si hay error en la respuesta
        if "error" in response.text.lower() or "invalid" in response.text.lower():
            print("\n💡 Parece que las credenciales son incorrectas o la cuenta está bloqueada")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 70 + "\n")
