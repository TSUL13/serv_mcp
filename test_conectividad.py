#!/usr/bin/env python3
"""Verificar conectividad a vManage SIN autenticarse"""

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

vmanage = "Vmanage.cjf.gob.mx"
url = f"https://{vmanage}"

print("\n" + "=" * 60)
print("  🔍 VERIFICACIÓN DE CONECTIVIDAD (Sin login)")
print("=" * 60)

print(f"\n🌐 Probando conexión a: {url}")

try:
    response = requests.get(url, verify=False, timeout=10)
    
    if response.status_code == 200:
        print("✅ Servidor alcanzable")
        print(f"   Status: {response.status_code}")
        
        if "login" in response.text.lower():
            print("✅ Página de login detectada")
            print("\n💡 El servidor está funcionando correctamente")
            print("   Puedes intentar autenticarte cuando la cuenta se desbloquee")
    else:
        print(f"⚠️  Status code: {response.status_code}")
        
except requests.exceptions.SSLError as e:
    print(f"❌ Error SSL: {e}")
    print("💡 El servidor requiere HTTPS (ya configurado en el código)")
    
except requests.exceptions.ConnectionError as e:
    print(f"❌ Error de conexión: {e}")
    print("💡 Verifica:")
    print("   1. Conexión a internet")
    print("   2. Acceso a la red del CJF")
    print("   3. VPN si es requerida")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("\n⏰ TIEMPO DE ESPERA RECOMENDADO:")
print("   • Espera 15-30 minutos antes de reintentar")
print("   • Contacta al administrador si persiste bloqueado")
print("\n📝 PASOS SIGUIENTES:")
print("   1. Espera el tiempo recomendado")
print("   2. Verifica usuario/password manualmente en el navegador:")
print(f"      {url}")
print("   3. Si funciona en navegador, actualiza el .env")
print("   4. Ejecuta de nuevo: python test_conexion.py")
print("\n" + "=" * 60 + "\n")
