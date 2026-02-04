#!/usr/bin/env python3
"""
Script para probar si tu vManage tiene Cisco Analytics habilitado
y qué endpoints están disponibles
"""

import sys
import json
import os
import requests
import urllib3
from dotenv import load_dotenv

# Deshabilitar warnings de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

class VManageSession:
    """Sesión simple para vManage"""
    def __init__(self):
        self.base_url = f"https://{os.getenv('VMANAGE_IP')}"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'Cookie': f"JSESSIONID={os.getenv('VMANAGE_JSESSIONID')}",
            'X-XSRF-TOKEN': os.getenv('VMANAGE_XSRF_TOKEN')
        })
    
    def get(self, endpoint, timeout=10):
        """Hace GET request"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, timeout=timeout)
        return response.json()

def probar_endpoint(session, endpoint, descripcion):
    """Prueba si un endpoint está disponible"""
    try:
        print(f"\n🔍 Probando: {descripcion}")
        print(f"   Endpoint: {endpoint}")
        
        result = session.get(endpoint, timeout=10)
        
        if 'data' in result and result['data']:
            print(f"   ✅ DISPONIBLE - {len(result['data'])} registros")
            return True
        elif 'error' in result:
            print(f"   ❌ ERROR: {result['error'].get('message', 'Unknown')}")
            return False
        else:
            print(f"   ⚠️  Sin datos (puede que no esté configurado)")
            return False
            
    except Exception as e:
        print(f"   ❌ FALLO: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("VERIFICACIÓN DE CISCO ANALYTICS EN VMANAGE")
    print("=" * 60)
    
    try:
        # Crear sesión
        session = VManageSession()
        print(f"\n✅ Conexión exitosa a vManage")
        
        # Endpoints de Analytics a probar
        endpoints = [
            ("/dataservice/statistics/app-aware/app-agg-stats", "Application QoE Statistics"),
            ("/dataservice/statistics/app-aware/flow-agg-stats", "Flow QoE Statistics"),
            ("/dataservice/statistics/dpi/aggregation", "DPI Aggregation (Flujos)"),
            ("/dataservice/statistics/interface/aggregation", "Interface Statistics"),
            ("/dataservice/statistics/tunnel/aggregation", "Tunnel Statistics"),
            ("/dataservice/statistics/approute/aggregation", "AppRoute Statistics"),
        ]
        
        disponibles = []
        no_disponibles = []
        
        for endpoint, descripcion in endpoints:
            if probar_endpoint(session, endpoint, descripcion):
                disponibles.append(descripcion)
            else:
                no_disponibles.append(descripcion)
        
        # Resumen
        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        print(f"\n✅ Endpoints disponibles: {len(disponibles)}")
        for desc in disponibles:
            print(f"   • {desc}")
        
        print(f"\n❌ Endpoints no disponibles: {len(no_disponibles)}")
        for desc in no_disponibles:
            print(f"   • {desc}")
        
        # Recomendaciones
        print("\n" + "=" * 60)
        print("RECOMENDACIONES")
        print("=" * 60)
        
        if len(disponibles) >= 4:
            print("\n🎉 Tu vManage tiene Cisco Analytics completamente habilitado!")
            print("   Puedes agregar todas las funciones de funciones_analytics.py")
        elif len(disponibles) >= 2:
            print("\n🟡 Tu vManage tiene Analytics parcialmente habilitado")
            print("   Puedes agregar las funciones correspondientes a los endpoints disponibles")
        else:
            print("\n⚠️  Cisco Analytics parece no estar habilitado o configurado")
            print("   Contacta con tu administrador de vManage para habilitarlo")
            print("\n   Pasos para habilitar Analytics:")
            print("   1. Administration > Settings > Analytics")
            print("   2. Enable Application Aware Routing")
            print("   3. Enable DPI (Deep Packet Inspection)")
        
    except Exception as e:
        print(f"\n❌ Error al conectar: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
