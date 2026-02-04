#!/usr/bin/env python3
"""
Test rápido del sistema completo
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from server import VManageSession
import os
from dotenv import load_dotenv

# Cargar variables
load_dotenv()

print("\n" + "="*70)
print("  🧪 TEST COMPLETO DEL SISTEMA")
print("="*70)

# Obtener configuración
vmanage_ip = os.getenv('VMANAGE_IP')
username = os.getenv('VMANAGE_USERNAME')
password = os.getenv('VMANAGE_PASSWORD')

print(f"\n📋 Configuración:")
print(f"   Servidor: {vmanage_ip}")
print(f"   Usuario: {username}")

# Crear sesión
print(f"\n🔐 Iniciando sesión con cookies del navegador...")
session = VManageSession(vmanage_ip, username, password)

if session.login():
    print("\n✅ Sesión iniciada exitosamente!")
    
    # Probar consulta
    print("\n🔄 Consultando dispositivos...")
    try:
        result = session.get("/dataservice/device")
        if 'data' in result:
            devices = result['data']
            print(f"\n✅ ¡ÉXITO! Encontrados {len(devices)} dispositivos")
            
            print(f"\n📊 Primeros 5 dispositivos:")
            for i, device in enumerate(devices[:5], 1):
                nombre = device.get('host-name', 'N/A')
                ip = device.get('system-ip', 'N/A')
                tipo = device.get('device-type', 'N/A')
                estado = device.get('reachability', 'N/A')
                print(f"   {i}. {nombre}")
                print(f"      IP: {ip} | Tipo: {tipo} | Estado: {estado}")
        else:
            print("⚠️  Respuesta sin datos")
            
    except Exception as e:
        print(f"❌ Error al consultar: {str(e)}")
else:
    print("\n❌ No se pudo iniciar sesión")

print("\n" + "="*70)
