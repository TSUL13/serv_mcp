#!/usr/bin/env python3
"""
Test alternativo - Verificar datos de DPI en tiempo real vs históricos
"""

import sys
import os
sys.path.insert(0, '/home/tsul/Documentos/serv_mcp')

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

class VManageSession:
    def __init__(self):
        self.base_url = f"https://{os.getenv('VMANAGE_IP')}"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'Cookie': f"JSESSIONID={os.getenv('VMANAGE_JSESSIONID')}",
            'X-XSRF-TOKEN': os.getenv('VMANAGE_XSRF_TOKEN'),
            'Content-Type': 'application/json'
        })
    
    def get(self, endpoint, timeout=15):
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, timeout=timeout)
        return response.status_code, response.text[:500], response

session = VManageSession()

# Obtener un dispositivo de prueba
devices = session.get("/dataservice/device")[2].json()
test_device = None
for d in devices['data']:
    if d.get('device-type') == 'vedge' and d.get('reachability') == 'reachable':
        test_device = d
        break

if not test_device:
    print("No se encontró dispositivo reachable")
    sys.exit(1)

device_id = test_device.get('deviceId') or test_device.get('uuid')
device_name = test_device.get('host-name')

print("=" * 70)
print(f"DISPOSITIVO DE PRUEBA: {device_name} ({device_id})")
print("=" * 70)

endpoints_test = [
    # Endpoints que probamos antes
    (f"/dataservice/device/dpi/applications?deviceId={device_id}", "DPI Applications (histórico)"),
    (f"/dataservice/device/dpi/summary?deviceId={device_id}", "DPI Summary"),
    
    # Endpoints alternativos en tiempo real
    (f"/dataservice/data/device/dpi/applications?deviceId={device_id}", "DPI Applications (real-time)"),
    (f"/dataservice/device/app-route/statistics?deviceId={device_id}", "App Route Statistics"),
    
    # Verificar si DPI está configurado
    (f"/dataservice/device/feature?deviceId={device_id}", "Device Features"),
    (f"/dataservice/template/policy/vedge/definition", "DPI Policies"),
]

print("\n🔍 PROBANDO ENDPOINTS:\n")

for endpoint, nombre in endpoints_test:
    print(f"📍 {nombre}")
    print(f"   Endpoint: {endpoint}")
    
    status, preview, resp = session.get(endpoint)
    print(f"   Status: {status}")
    
    if status == 200:
        try:
            data = resp.json()
            if 'data' in data:
                if isinstance(data['data'], list):
                    count = len(data['data'])
                    print(f"   ✅ Respuesta con {count} elementos")
                    if count > 0:
                        print(f"   Ejemplo: {str(data['data'][0])[:200]}")
                else:
                    print(f"   ✅ Respuesta con datos")
                    print(f"   Ejemplo: {str(data['data'])[:200]}")
            elif 'error' in data:
                print(f"   ❌ Error: {data['error'].get('message', 'Unknown')}")
            else:
                print(f"   ⚠️  Respuesta: {preview}")
        except:
            print(f"   ⚠️  No JSON: {preview}")
    else:
        print(f"   ❌ Error {status}")
    
    print()

print("\n" + "=" * 70)
print("CONCLUSIÓN:")
print("=" * 70)
print("""
Si todos los endpoints regresan sin datos, significa que:

1. ✅ DPI está instalado pero NO está habilitado en las políticas
2. ✅ Los dispositivos NO tienen configurado Application-Aware Routing
3. ✅ No hay flujos clasificados porque DPI no está activo

SOLUCIÓN:
- En vManage: Configuration → Policies → Centralized Policy
- Agregar/Editar política con "Application Aware Routing" o "Traffic Data"
- Activar DPI en los device templates
- Aplicar a los dispositivos
""")
