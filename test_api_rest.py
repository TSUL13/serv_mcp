#!/usr/bin/env python3
"""
Script de prueba rápida para la API REST
Verifica que todos los endpoints funcionen
"""

import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_endpoint(method, endpoint, description):
    print(f"\n🔍 Probando: {description}")
    print(f"   {method} {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ OK - Status: {response.status_code}")
            
            # Mostrar preview de datos
            if isinstance(data, dict):
                if "total" in data:
                    print(f"   📊 Total: {data['total']}")
                if "total_devices" in data:
                    print(f"   📊 Total: {data['total_devices']}")
                if "total_critical" in data:
                    print(f"   ⚠️  Críticas: {data['total_critical']}")
                if "total_bfd_sessions" in data:
                    print(f"   📡 Sesiones BFD: {data['total_bfd_sessions']}")
            
            return True
        else:
            print(f"   ❌ Error: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Error: No se puede conectar al servidor")
        print("   💡 ¿Está corriendo? Ejecuta: python api_rest.py")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "="*70)
    print("  🧪 PRUEBA DE API REST - vManage")
    print("  Compatible con GPT, Gemini y cualquier cliente HTTP")
    print("="*70)
    
    # Verificar que el servidor está corriendo
    print("\n🔌 Verificando conexión al servidor...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ Servidor respondiendo en {BASE_URL}")
    except:
        print(f"❌ Error: No se puede conectar a {BASE_URL}")
        print("\n💡 Para iniciar el servidor, ejecuta:")
        print("   python api_rest.py")
        return
    
    # Tests de endpoints
    print_section("ENDPOINTS BÁSICOS")
    
    tests = [
        ("GET", "/", "Información de la API"),
        ("GET", "/devices", "Lista de dispositivos"),
        ("GET", "/alarms/critical", "Alarmas críticas"),
        ("GET", "/network-summary", "Resumen de red"),
        ("GET", "/bfd/total?sample_size=5", "Total sesiones BFD (muestra 5)"),
    ]
    
    successful = 0
    for method, endpoint, desc in tests:
        if test_endpoint(method, endpoint, desc):
            successful += 1
        sleep(0.5)  # Pausa entre requests
    
    # Obtener un device_id para pruebas específicas
    print_section("ENDPOINTS ESPECÍFICOS DE DISPOSITIVO")
    
    try:
        response = requests.get(f"{BASE_URL}/devices", timeout=10)
        devices = response.json().get("devices", [])
        
        if devices:
            # Tomar primer dispositivo alcanzable
            device = None
            for d in devices:
                if d.get("reachability") == "reachable":
                    device = d
                    break
            
            if device:
                device_id = device.get("system-ip")
                device_name = device.get("host-name")
                
                print(f"\n📍 Usando dispositivo de prueba:")
                print(f"   ID: {device_id}")
                print(f"   Nombre: {device_name}")
                
                device_tests = [
                    ("GET", f"/devices/{device_id}/health", "Salud del dispositivo"),
                    ("GET", f"/devices/{device_id}/bfd", "Sesiones BFD"),
                    ("GET", f"/devices/{device_id}/cpu-memory", "CPU y Memoria"),
                    ("GET", f"/devices/{device_id}/interfaces", "Interfaces"),
                ]
                
                for method, endpoint, desc in device_tests:
                    if test_endpoint(method, endpoint, desc):
                        successful += 1
                    sleep(0.5)
        else:
            print("⚠️  No se encontraron dispositivos para pruebas específicas")
    
    except Exception as e:
        print(f"❌ Error obteniendo dispositivos: {e}")
    
    # Resumen
    total_tests = len(tests) + 4  # 4 tests específicos de dispositivo
    print_section("RESUMEN")
    print(f"\n✅ Tests exitosos: {successful}/{total_tests}")
    print(f"❌ Tests fallidos: {total_tests - successful}/{total_tests}")
    
    if successful == total_tests:
        print("\n🎉 ¡Todos los tests pasaron!")
        print("\n💡 Próximos pasos:")
        print("   1. Abre http://localhost:8000/docs para ver la documentación")
        print("   2. Lee CONECTAR_GPT_GEMINI.md para configurar GPT/Gemini")
        print("   3. Crea un Custom GPT con estos endpoints")
    else:
        print("\n⚠️  Algunos tests fallaron. Revisa los errores arriba.")
    
    print("\n" + "="*70)
    print("  📚 Documentación disponible:")
    print("     - Swagger UI: http://localhost:8000/docs")
    print("     - Redoc: http://localhost:8000/redoc")
    print("     - OpenAPI JSON: http://localhost:8000/openapi.json")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
