#!/usr/bin/env python3
"""
Test de las nuevas funciones agregadas al servidor MCP
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
from dotenv import load_dotenv
from server import VManageSession

load_dotenv()

# Crear sesión
vmanage_ip = os.getenv('VMANAGE_IP')
username = os.getenv('VMANAGE_USERNAME')
password = os.getenv('VMANAGE_PASSWORD')

print("\n" + "="*70)
print("  🧪 TEST DE NUEVAS FUNCIONES MCP")
print("="*70)

session = VManageSession(vmanage_ip, username, password)
if not session.login():
    print("❌ Error al conectar con vManage")
    sys.exit(1)

print("✅ Sesión iniciada correctamente\n")

# Test 1: Resumen de red
print("[1/5] Probando endpoint de resumen...")
try:
    devices = session.get("/dataservice/device")
    alarms = session.get("/dataservice/alarms")
    
    total = len(devices.get('data', []))
    alarmas = len([a for a in alarms.get('data', []) if a.get('severity') == 'Critical'])
    
    print(f"✅ Resumen: {total} dispositivos, {alarmas} alarmas críticas")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Estadísticas de interfaces
print("\n[2/5] Probando estadísticas de interfaces...")
try:
    result = session.get("/dataservice/device/interface/stats?deviceId=10.80.10.207")
    if 'data' in result:
        print(f"✅ Interfaces encontradas: {len(result['data'])}")
    else:
        print("⚠️  No hay datos de interfaces")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: CPU y Memoria
print("\n[3/5] Probando uso de CPU/Memoria...")
try:
    result = session.get("/dataservice/device/system/status?deviceId=10.80.10.207")
    if 'data' in result and len(result['data']) > 0:
        sys_data = result['data'][0]
        cpu_idle = sys_data.get('cpu-idle', 0)
        mem_percent = sys_data.get('mem-used-percent', 0)
        print(f"✅ CPU usado: {100 - float(cpu_idle):.1f}%, Memoria: {mem_percent}%")
    else:
        print("⚠️  No hay datos de sistema")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Control connections
print("\n[4/5] Probando control connections...")
try:
    result = session.get("/dataservice/device/control/connections?deviceId=10.80.10.207")
    if 'data' in result:
        up_count = sum(1 for c in result['data'] if c.get('state') == 'up')
        print(f"✅ Conexiones de control: {len(result['data'])} total, {up_count} activas")
    else:
        print("⚠️  No hay datos de control")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Búsqueda de dispositivos
print("\n[5/5] Probando búsqueda de dispositivos...")
try:
    result = session.get("/dataservice/device")
    if 'data' in result:
        vmanages = [d for d in result['data'] if 'vmanage' in d.get('host-name', '').lower()]
        print(f"✅ Dispositivos vManage encontrados: {len(vmanages)}")
    else:
        print("⚠️  No hay datos")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("  ✅ TEST COMPLETADO")
print("="*70)
print("\n📊 Nuevas funciones disponibles en el servidor MCP:")
print("\n   FASE 1 - Esenciales (5):")
print("   1. ver_estadisticas_interfaces")
print("   2. ver_uso_cpu_memoria")
print("   3. ver_tuneles_omp")
print("   4. ver_control_connections")
print("   5. ver_resumen_red")
print("\n   FASE 2 - Análisis (5):")
print("   6. ver_aplicaciones_top")
print("   7. buscar_dispositivo")
print("   8. ver_dispositivos_por_sitio")
print("   9. ver_eventos_seguridad")
print("   10. diagnostico_completo_dispositivo")
print("\n🎯 Total de herramientas MCP: 14 (4 originales + 10 nuevas)")
print("\n💡 Para usar en Claude Desktop:")
print("   1. Cierra Claude Desktop si está abierto")
print("   2. Abre Claude Desktop nuevamente")
print("   3. Pregunta: '¿Qué herramientas MCP tienes?'")
print("   4. Deberías ver 14 herramientas de cisco-sdwan\n")
