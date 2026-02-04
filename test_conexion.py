#!/usr/bin/env python3
"""Script de prueba de conexión a vManage"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from server import get_vmanage_session

print("\n" + "=" * 70)
print("  🔍 PRUEBA DE CONEXIÓN A VMANAGE")
print("=" * 70)

print("\n📋 Configuración:")
print(f"   Servidor: {os.getenv('VMANAGE_IP', 'NO CONFIGURADO')}")
print(f"   Usuario:  {os.getenv('VMANAGE_USERNAME', 'NO CONFIGURADO')}")
print(f"   Password: {'*' * len(os.getenv('VMANAGE_PASSWORD', '')) if os.getenv('VMANAGE_PASSWORD') else 'NO CONFIGURADO'}")

print("\n🔄 Intentando conectar...")

try:
    session = get_vmanage_session()
    print("✅ Sesión creada")
    
    print("\n🔄 Probando consulta de dispositivos...")
    result = session.get("/dataservice/device", timeout=10)
    
    if isinstance(result, dict) and 'data' in result:
        device_count = len(result['data'])
        print(f"✅ Conexión exitosa - Encontrados {device_count} dispositivos")
        
        if device_count > 0:
            print("\n📊 Primeros 3 dispositivos:")
            for i, device in enumerate(result['data'][:3], 1):
                print(f"   {i}. {device.get('host-name', 'N/A')} - {device.get('system-ip', 'N/A')}")
    else:
        print("❌ Respuesta inesperada del servidor")
        print(f"Tipo de respuesta: {type(result)}")
        if isinstance(result, str):
            print(f"Contenido (primeros 200 chars): {result[:200]}")
        
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print("\n💡 Posibles soluciones:")
    print("   1. Verifica usuario y contraseña en el archivo .env")
    print("   2. Prueba acceder manualmente a:")
    print("      https://Vmanage.cjf.gob.mx")
    print("   3. Verifica que tu cuenta no esté bloqueada")
    print("   4. Contacta al administrador")

print("\n" + "=" * 70 + "\n")
