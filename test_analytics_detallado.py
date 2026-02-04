#!/usr/bin/env python3
"""
Test detallado de Analytics - Verifica endpoints alternativos
"""

import os
import requests
import urllib3
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            try:
                return response.json()
            except:
                print(f"   Response: {response.text[:200]}")
                return None
        else:
            print(f"   Error: {response.text[:200]}")
            return None

def main():
    print("=" * 70)
    print("TEST AVANZADO - CISCO ANALYTICS")
    print("=" * 70)
    
    session = VManageSession()
    
    # 1. Primero obtener un device_id válido
    print("\n📱 Obteniendo dispositivos...")
    devices = session.get("/dataservice/device")
    
    if not devices or 'data' not in devices:
        print("❌ No se pudieron obtener dispositivos")
        return
    
    # Tomar el primer dispositivo edge
    device_id = None
    for dev in devices['data']:
        if dev.get('device-type') == 'vedge':
            device_id = dev.get('deviceId') or dev.get('uuid')
            device_name = dev.get('host-name')
            print(f"   ✅ Usando dispositivo: {device_name} ({device_id})")
            break
    
    if not device_id:
        print("❌ No se encontró ningún dispositivo edge")
        return
    
    # 2. Test endpoints específicos con parámetros
    print("\n" + "=" * 70)
    print("ENDPOINTS DE ANALYTICS")
    print("=" * 70)
    
    endpoints_test = [
        # DPI - Deep Packet Inspection
        {
            'url': f"/dataservice/device/dpi/applications?deviceId={device_id}",
            'nombre': "DPI Applications (por dispositivo)",
            'categoria': "Analytics Básico"
        },
        {
            'url': f"/dataservice/statistics/dpi/application/summary?deviceId={device_id}",
            'nombre': "DPI Application Summary",
            'categoria': "Analytics Avanzado"
        },
        
        # Application Aware Routing
        {
            'url': f"/dataservice/data/device/app-route/statistics?deviceId={device_id}",
            'nombre': "App-Route Statistics",
            'categoria': "AppQoE"
        },
        
        # Interface Statistics
        {
            'url': f"/dataservice/data/device/statistics/interfacestatistics?deviceId={device_id}",
            'nombre': "Interface Statistics (Real-time)",
            'categoria': "Performance"
        },
        
        # Tunnel Statistics
        {
            'url': f"/dataservice/data/device/statistics/ipsectunnelstatistics?deviceId={device_id}",
            'nombre': "IPsec Tunnel Statistics",
            'categoria': "Performance"
        },
        
        # Flow Analytics
        {
            'url': f"/dataservice/statistics/dpi/flow-count?deviceId={device_id}",
            'nombre': "DPI Flow Count",
            'categoria': "Analytics Avanzado"
        },
        
        # Application QoE
        {
            'url': "/dataservice/statistics/app-aware/available-apps",
            'nombre': "Available Applications (App-Aware)",
            'categoria': "AppQoE"
        },
        
        # System Statistics
        {
            'url': f"/dataservice/device/system/status?deviceId={device_id}",
            'nombre': "System Status",
            'categoria': "Básico"
        }
    ]
    
    resultados = {
        'disponible': [],
        'no_disponible': [],
        'error': []
    }
    
    for endpoint in endpoints_test:
        print(f"\n🔍 {endpoint['nombre']}")
        print(f"   Categoría: {endpoint['categoria']}")
        print(f"   URL: {endpoint['url']}")
        
        result = session.get(endpoint['url'])
        
        if result and 'data' in result:
            count = len(result['data']) if isinstance(result['data'], list) else 1
            print(f"   ✅ DISPONIBLE - {count} registros")
            resultados['disponible'].append(endpoint)
        elif result and 'error' not in result:
            print(f"   ⚠️  Sin datos")
            resultados['no_disponible'].append(endpoint)
        else:
            resultados['error'].append(endpoint)
    
    # Resumen por categoría
    print("\n" + "=" * 70)
    print("RESUMEN POR CATEGORÍA")
    print("=" * 70)
    
    categorias = {}
    for endpoint in resultados['disponible']:
        cat = endpoint['categoria']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(endpoint['nombre'])
    
    if categorias:
        print("\n✅ DISPONIBLES:")
        for cat, nombres in categorias.items():
            print(f"\n   {cat}:")
            for nombre in nombres:
                print(f"      • {nombre}")
    else:
        print("\n❌ No hay endpoints de Analytics disponibles")
    
    # Recomendaciones finales
    print("\n" + "=" * 70)
    print("FUNCIONES QUE PUEDES AGREGAR AL MCP")
    print("=" * 70)
    
    if any('DPI' in e['nombre'] for e in resultados['disponible']):
        print("\n✅ DPI está disponible - Puedes agregar:")
        print("   • ver_aplicaciones_top() ← Ya lo tienes")
        print("   • ver_flujos_anormales() ← Nueva función")
    
    if any('App-Route' in e['nombre'] or 'AppQoE' in e['categoria'] for e in resultados['disponible']):
        print("\n✅ App-Aware Routing disponible - Puedes agregar:")
        print("   • analizar_experiencia_aplicaciones() ← Nueva función")
    
    if any('Interface' in e['nombre'] for e in resultados['disponible']):
        print("\n✅ Interface Stats disponible - Puedes agregar:")
        print("   • predecir_capacidad_enlaces() ← Nueva función")
    
    if any('Tunnel' in e['nombre'] or 'ipsec' in e['url'].lower() for e in resultados['disponible']):
        print("\n✅ Tunnel Stats disponible - Puedes agregar:")
        print("   • analizar_rendimiento_tuneles() ← Nueva función")
    
    if len(resultados['disponible']) == 0:
        print("\n⚠️  Analytics no está disponible en tu vManage")
        print("   Tus opciones:")
        print("   1. Usar solo las funciones básicas que ya tienes (ver_dispositivos, ver_aplicaciones_top, etc.)")
        print("   2. Solicitar a tu admin que habilite Analytics en vManage")
        print("   3. Actualizar vManage a una versión con Analytics (20.9+)")

if __name__ == "__main__":
    main()
