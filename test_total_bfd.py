#!/usr/bin/env python3
"""
Test de la función ver_total_sesiones_bfd
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
from dotenv import load_dotenv
from server import VManageSession

load_dotenv()

print("\n" + "="*70)
print("  🧪 TEST: TOTAL DE SESIONES BFD EN LA RED")
print("="*70)

# Crear sesión
vmanage_ip = os.getenv('VMANAGE_IP')
username = os.getenv('VMANAGE_USERNAME')
password = os.getenv('VMANAGE_PASSWORD')

session = VManageSession(vmanage_ip, username, password)

print("\n🔐 Conectando con vManage...")
if not session.login():
    print("❌ Error al conectar")
    sys.exit(1)

print("✅ Sesión iniciada\n")

# Obtener dispositivos
print("🔄 Obteniendo lista de dispositivos...")
devices_result = session.get("/dataservice/device")

if 'data' in devices_result:
    devices = devices_result['data']
    reachable_devices = [d for d in devices if d.get('reachability') == 'reachable' 
                        and d.get('device-type') not in ['vmanage']]
    
    print(f"✅ Dispositivos reachables (excluyendo vManage): {len(reachable_devices)}")
    print(f"   Consultando sesiones BFD...\n")
    
    total_sesiones = 0
    up_count = 0
    down_count = 0
    devices_with_bfd = 0
    
    # Muestrear primeros 10 dispositivos para no tardar mucho
    sample_devices = reachable_devices[:10]
    
    for i, device in enumerate(sample_devices, 1):
        device_id = device.get('system-ip')
        hostname = device.get('host-name', 'N/A')
        
        print(f"   [{i}/{len(sample_devices)}] {hostname} ({device_id})...", end=" ")
        
        try:
            bfd_result = session.get(f"/dataservice/device/bfd/sessions?deviceId={device_id}", timeout=5)
            
            if 'data' in bfd_result:
                sessions = bfd_result['data']
                num_sessions = len(sessions)
                
                if num_sessions > 0:
                    devices_with_bfd += 1
                    total_sesiones += num_sessions
                    
                    up = sum(1 for s in sessions if s.get('state', '').lower() == 'up')
                    down = sum(1 for s in sessions if s.get('state', '').lower() == 'down')
                    
                    up_count += up
                    down_count += down
                    
                    print(f"{num_sessions} sesiones (UP: {up}, DOWN: {down})")
                else:
                    print("Sin sesiones BFD")
            else:
                print("No disponible")
                
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "="*70)
    print("  📊 RESUMEN (MUESTRA DE 10 DISPOSITIVOS)")
    print("="*70)
    print(f"\nTotal sesiones BFD: {total_sesiones}")
    print(f"  ✅ UP: {up_count}")
    print(f"  ❌ DOWN: {down_count}")
    print(f"\nDispositivos con BFD: {devices_with_bfd}/{len(sample_devices)}")
    
    if total_sesiones > 0:
        porcentaje = (up_count / total_sesiones * 100)
        print(f"\nSalud BFD: {porcentaje:.1f}% sesiones UP")
        
        if porcentaje >= 95:
            print("Estado: ✅ EXCELENTE")
        elif porcentaje >= 80:
            print("Estado: ⚠️  ACEPTABLE")
        else:
            print("Estado: ❌ CRÍTICO")
    
    print("\n💡 Para ver el total completo de toda la red, usa en Claude Desktop:")
    print("   'Muéstrame el total de sesiones BFD en la red'\n")
    
else:
    print("❌ No se pudieron obtener dispositivos")

print("="*70 + "\n")
