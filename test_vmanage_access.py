#!/usr/bin/env python3
"""
Script para probar acceso a vManage y endpoints de flujos DPI
"""

import os
import sys
import requests
import urllib3
from dotenv import load_dotenv
import getpass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

print("="*70)
print("🔍 TEST DE ACCESO A VMANAGE")
print("="*70)

# Verificar credenciales
vmanage_host = os.getenv('VMANAGE_HOST')
username = os.getenv('VMANAGE_USERNAME')
password = os.getenv('VMANAGE_PASSWORD')

print(f"\n📋 Credenciales actuales:")
print(f"   Host: {vmanage_host if vmanage_host else '❌ NO CONFIGURADO'}")
print(f"   Usuario: {username if username else '❌ NO CONFIGURADO'}")
print(f"   Password: {'✅ Configurado' if password else '❌ NO CONFIGURADO'}")

# Solicitar host si no está configurado
if not vmanage_host:
    print(f"\n⚙️  Configuración necesaria")
    vmanage_host = input("Ingresa la IP o hostname de vManage: ").strip()
    
    if not vmanage_host:
        print("❌ Host requerido. Saliendo...")
        sys.exit(1)
    
    # Preguntar si guardar en .env
    guardar = input(f"\n¿Guardar '{vmanage_host}' en .env? (s/n): ").strip().lower()
    if guardar == 's':
        with open('.env', 'a') as f:
            f.write(f"\nVMANAGE_HOST={vmanage_host}\n")
        print("✅ Host guardado en .env")

if not username:
    username = input("Usuario de vManage: ").strip()

if not password:
    password = getpass.getpass("Password de vManage: ")

print(f"\n🔄 Intentando conectar a vManage...")
print(f"   URL: https://{vmanage_host}")

# Crear sesión
session = requests.Session()
session.verify = False

# 1. Test de conectividad básica
print(f"\n1️⃣  Test de conectividad...")
try:
    response = session.get(f"https://{vmanage_host}", timeout=5)
    print(f"   ✅ Servidor responde (Status: {response.status_code})")
except Exception as e:
    print(f"   ❌ No se puede conectar: {str(e)[:60]}")
    print(f"\n💡 Verifica:")
    print(f"   - La IP/hostname es correcta")
    print(f"   - vManage está accesible desde esta red")
    print(f"   - No hay firewall bloqueando")
    sys.exit(1)

# 2. Autenticación
print(f"\n2️⃣  Test de autenticación...")
auth_url = f"https://{vmanage_host}/j_security_check"
auth_data = {
    'j_username': username,
    'j_password': password
}

try:
    auth_response = session.post(auth_url, data=auth_data, timeout=10)
    
    if auth_response.status_code == 200 and '<html>' not in auth_response.text:
        print(f"   ✅ Autenticación exitosa")
    else:
        print(f"   ❌ Autenticación falló")
        print(f"   Verifica usuario y contraseña")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Error en autenticación: {str(e)[:60]}")
    sys.exit(1)

# 3. Obtener token CSRF
print(f"\n3️⃣  Obteniendo token CSRF...")
try:
    token_url = f"https://{vmanage_host}/dataservice/client/token"
    token_response = session.get(token_url, timeout=10)
    
    if token_response.status_code == 200:
        token = token_response.text
        session.headers['X-XSRF-TOKEN'] = token
        print(f"   ✅ Token obtenido: {token[:20]}...")
    else:
        print(f"   ⚠️  No se pudo obtener token: {token_response.status_code}")
        
except Exception as e:
    print(f"   ⚠️  Error obteniendo token: {str(e)[:60]}")

# 4. Test de endpoints básicos
print(f"\n4️⃣  Probando endpoints básicos...")

endpoints_basicos = [
    ("/dataservice/device", "Lista de dispositivos"),
    ("/dataservice/admin/user", "Usuarios"),
]

for endpoint, descripcion in endpoints_basicos:
    try:
        url = f"https://{vmanage_host}{endpoint}"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('data', []))
            print(f"   ✅ {descripcion}: {count} registros")
        else:
            print(f"   ⚠️  {descripcion}: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ {descripcion}: {str(e)[:40]}")

# 5. Test de endpoints DPI/Application
print(f"\n5️⃣  Probando endpoints de DPI y aplicaciones...")

dpi_endpoints = [
    ("/dataservice/statistics/dpi/applications", "GET", None, "Aplicaciones DPI"),
    ("/dataservice/statistics/approute/applications", "GET", None, "App-Route Applications"),
    ("/dataservice/statistics/dpi/aggregation", "POST", {
        "aggregation": {
            "metrics": [
                {"property": "application", "type": "groupBy"},
                {"property": "total_bytes", "type": "sum"}
            ]
        }
    }, "DPI Aggregation"),
]

for endpoint, method, payload, descripcion in dpi_endpoints:
    try:
        url = f"https://{vmanage_host}{endpoint}"
        
        if method == "GET":
            response = session.get(url, timeout=10)
        else:
            response = session.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                count = len(data['data'])
                print(f"   ✅ {descripcion}: {count} registros")
                
                # Mostrar campos del primer registro
                if count > 0:
                    first_keys = list(data['data'][0].keys())[:8]
                    print(f"      Campos: {', '.join(first_keys)}")
                    
                    # Verificar si tiene IPs
                    first_record = data['data'][0]
                    if 'src_ip' in first_record or 'dst_ip' in first_record:
                        print(f"      🎯 TIENE IPs ORIGEN/DESTINO!")
                        print(f"         src_ip: {first_record.get('src_ip', 'N/A')}")
                        print(f"         dst_ip: {first_record.get('dst_ip', 'N/A')}")
            else:
                print(f"   ⚠️  {descripcion}: Respuesta sin 'data'")
                print(f"      Keys: {list(data.keys())}")
        else:
            print(f"   ⚠️  {descripcion}: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ {descripcion}: {str(e)[:50]}")

# 6. Test específico de flujos
print(f"\n6️⃣  Probando endpoints de FLUJOS (con IPs origen/destino)...")

flow_endpoints = [
    ("/dataservice/statistics/dpi/flows", "GET", None, "DPI Flows"),
    ("/dataservice/statistics/approute/fec/flows", "GET", None, "App-Route FEC Flows"),
]

for endpoint, method, payload, descripcion in flow_endpoints:
    try:
        url = f"https://{vmanage_host}{endpoint}"
        
        if method == "GET":
            response = session.get(url, timeout=10)
        else:
            response = session.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                count = len(data['data'])
                print(f"   ✅ {descripcion}: {count} flujos")
                
                if count > 0:
                    first_flow = data['data'][0]
                    all_keys = list(first_flow.keys())
                    
                    print(f"      Total campos: {len(all_keys)}")
                    print(f"      Campos: {', '.join(all_keys[:15])}")
                    
                    # Buscar campos de IPs
                    ip_fields = [k for k in all_keys if 'ip' in k.lower() or 'src' in k.lower() or 'dst' in k.lower()]
                    if ip_fields:
                        print(f"      🎯 Campos de IP encontrados: {', '.join(ip_fields)}")
                        
                        print(f"\n      📝 Ejemplo de flujo:")
                        for field in ip_fields[:6]:
                            print(f"         {field}: {first_flow.get(field)}")
            else:
                print(f"   ⚠️  {descripcion}: Sin datos")
        else:
            print(f"   ⚠️  {descripcion}: {response.status_code}")
            if response.status_code == 400:
                print(f"      Respuesta: {response.text[:100]}")
            
    except Exception as e:
        print(f"   ❌ {descripcion}: {str(e)[:50]}")

# Resumen final
print(f"\n" + "="*70)
print(f"✅ TEST COMPLETADO")
print(f"="*70)
print(f"\n💡 Próximos pasos:")
print(f"   1. Si viste endpoints con IPs origen/destino, puedes implementar")
print(f"      función para obtener esos datos")
print(f"   2. Accede a vManage GUI en: https://{vmanage_host}")
print(f"   3. Navega a: Monitor → Applications → Application-Aware Routing")
print(f"   4. Verifica datos de flujos disponibles visualmente")
print(f"\n📁 Guarda esta configuración en .env si no lo hiciste:")
print(f"   VMANAGE_HOST={vmanage_host}")
print(f"   VMANAGE_USERNAME={username}")
print(f"   VMANAGE_PASSWORD=<tu_password>")
