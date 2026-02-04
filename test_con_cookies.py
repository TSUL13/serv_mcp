#!/usr/bin/env python3
"""
SOLUCIÓN ALTERNATIVA: Usar cookies del navegador

INSTRUCCIONES:
1. Abre tu navegador y accede a vManage
2. Abre las herramientas de desarrollador (F12)
3. Ve a la pestaña "Network" o "Red"
4. Haz una petición a /dataservice/device
5. Copia el valor de las cookies JSESSIONID y X-XSRF-TOKEN
6. Pégalas aquí abajo
"""

import requests
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# CONFIGURA ESTAS COOKIES DESDE TU NAVEGADOR
# ============================================================

VMANAGE_URL = "https://vmanage.cjf.gob.mx"

# Copia aquí el valor de JSESSIONID de tu navegador
JSESSIONID = "ZFHV6-1TmMAx5lc8GVRDySoy3Q1oDxgd6W-M1IkB.ac76ee48-5334-48a0-81ab-a46976f774d7"

# Copia aquí el valor de X-XSRF-TOKEN de tu navegador
XSRF_TOKEN = "45603F94D7D3C81AD837E9FE6DB6BB4CE94CDFD088DCB0F1ACF4F8BCF2E8D66124A70AB8D2BEB9E8FA9E98ADC2E80B0CD053"

# ============================================================

print("\n" + "=" * 70)
print("  🔍 TEST CON COOKIES DEL NAVEGADOR")
print("=" * 70)

if JSESSIONID == "PEGA_AQUI_EL_JSESSIONID":
    print("\n❌ ERROR: Debes configurar las cookies primero")
    print("\n📋 PASOS:")
    print("   1. Abre Firefox/Chrome y accede a vManage")
    print("   2. Presiona F12 (Developer Tools)")
    print("   3. Ve a Network/Red")
    print("   4. Recarga la página")
    print("   5. Busca cualquier petición")
    print("   6. En Headers > Request Headers busca:")
    print("      - Cookie: JSESSIONID=XXXXX")
    print("      - X-XSRF-TOKEN: XXXXX")
    print("   7. Copia esos valores y pégalos en este script")
    print("\n" + "=" * 70 + "\n")
    exit(1)

print(f"\nServidor: {VMANAGE_URL}")
print(f"JSESSIONID: {JSESSIONID[:20]}...")
print(f"XSRF-TOKEN: {XSRF_TOKEN[:20] if len(XSRF_TOKEN) > 20 else XSRF_TOKEN}")

session = requests.Session()
session.verify = False

# Configurar cookies y headers
session.cookies.set('JSESSIONID', JSESSIONID)
session.headers.update({
    'X-XSRF-TOKEN': XSRF_TOKEN,
    'Content-Type': 'application/json'
})

print("\n🔄 Probando consulta de dispositivos...")

try:
    response = session.get(f"{VMANAGE_URL}/dataservice/device", timeout=30)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            devices = data['data']
            print(f"\n🎉 ¡FUNCIONA! Dispositivos: {len(devices)}")
            
            print("\n📊 Primeros 3 dispositivos:")
            for i, dev in enumerate(devices[:3], 1):
                print(f"   {i}. {dev.get('host-name', 'N/A')} - {dev.get('system-ip', 'N/A')}")
                
            print("\n💡 SOLUCIÓN: Las cookies del navegador funcionan")
            print("   El problema es la autenticación programática.")
            print("   Necesitas credenciales de API o cuenta sin restricciones.")
        else:
            print(f"\n⚠️  Respuesta sin 'data': {data}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"   Respuesta: {response.text[:500]}")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 70 + "\n")
