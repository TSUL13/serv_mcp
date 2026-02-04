#!/usr/bin/env python3
"""
Test de autenticación mejorado simulando navegador
"""

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
print("  🔍 TEST DE AUTENTICACIÓN - SIMULANDO NAVEGADOR")
print("=" * 70)
print(f"\nServidor: https://{vmanage_ip}")
print(f"Usuario: {username}")
print(f"Password: {'*' * len(password)}")

base_url = f"https://{vmanage_ip}"
session = requests.Session()
session.verify = False

# Headers de navegador real
browser_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

session.headers.update(browser_headers)

print("\n🔄 PASO 1: Accediendo a página principal...")
try:
    # Acceder primero a la página principal para obtener cookies iniciales
    main_response = session.get(base_url, timeout=30)
    print(f"   Status: {main_response.status_code}")
    print(f"   Cookies iniciales: {dict(session.cookies)}")
    
    print("\n🔄 PASO 2: Realizando POST a /j_security_check...")
    auth_url = f"{base_url}/j_security_check"
    
    # Payload exacto como lo envía el navegador
    payload = {
        'j_username': username,
        'j_password': password
    }
    
    # Headers específicos para el POST
    post_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': base_url,
        'Referer': base_url + '/'
    }
    
    login_response = session.post(
        auth_url,
        data=payload,
        headers=post_headers,
        timeout=30,
        allow_redirects=False  # No seguir redirects
    )
    
    print(f"   Status: {login_response.status_code}")
    print(f"   Cookies después del login: {dict(session.cookies)}")
    print(f"   Headers de respuesta: {dict(login_response.headers)}")
    
    if 'JSESSIONID' in session.cookies:
        print("\n✅ JSESSIONID obtenido correctamente")
        
        print("\n🔄 PASO 3: Obteniendo token X-XSRF...")
        token_url = f"{base_url}/dataservice/client/token"
        
        token_response = session.get(token_url, timeout=30)
        print(f"   Status: {token_response.status_code}")
        print(f"   Content-Type: {token_response.headers.get('content-type', 'N/A')}")
        
        token_text = token_response.text.strip()
        
        if token_text.startswith('<'):
            print(f"\n❌ ERROR: Recibió HTML en lugar de token")
            print(f"   Primeros 200 caracteres: {token_text[:200]}")
            print("\n💡 Esto significa que la autenticación falló.")
            print("   Verifica:")
            print("   1. Usuario y contraseña correctos")
            print("   2. Cuenta no bloqueada")
            print("   3. No requiere 2FA/MFA")
        else:
            print(f"\n✅ Token obtenido: {token_text}")
            
            # Configurar headers para peticiones API
            session.headers.update({
                'X-XSRF-TOKEN': token_text,
                'Content-Type': 'application/json'
            })
            
            print("\n🔄 PASO 4: Probando consulta de dispositivos...")
            devices_url = f"{base_url}/dataservice/device"
            devices_response = session.get(devices_url, timeout=30)
            
            print(f"   Status: {devices_response.status_code}")
            
            if devices_response.status_code == 200:
                try:
                    data = devices_response.json()
                    if 'data' in data:
                        device_count = len(data['data'])
                        print(f"\n🎉 ¡AUTENTICACIÓN EXITOSA!")
                        print(f"   Dispositivos encontrados: {device_count}")
                        
                        if device_count > 0:
                            print("\n📊 Primeros 3 dispositivos:")
                            for i, dev in enumerate(data['data'][:3], 1):
                                print(f"   {i}. {dev.get('host-name', 'N/A')} ({dev.get('device-type', 'N/A')}) - {dev.get('system-ip', 'N/A')}")
                    else:
                        print(f"\n⚠️  Respuesta sin 'data': {data}")
                except Exception as e:
                    print(f"\n❌ Error parseando JSON: {e}")
            else:
                print(f"\n❌ Error en consulta: {devices_response.text[:500]}")
    else:
        print("\n❌ No se obtuvo JSESSIONID")
        print("   El login falló completamente")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    print(traceback.format_exc())

print("\n" + "=" * 70 + "\n")
