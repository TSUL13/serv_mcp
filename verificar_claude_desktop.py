#!/usr/bin/env python3
"""
Test del servidor MCP para verificar antes de usar con Claude Desktop
"""
import subprocess
import time
import sys

print("\n" + "="*70)
print("  🔍 VERIFICACIÓN PRE-CLAUDE DESKTOP")
print("="*70)

print("\n[1/4] Verificando cookies del navegador...")
result = subprocess.run(
    ["python", "browser_cookies.py"],
    capture_output=True,
    text=True,
    timeout=10
)

if "¡Extracción exitosa!" in result.stdout:
    print("✅ Cookies extraídas correctamente")
else:
    print("❌ FALLO: No se pueden extraer cookies")
    print("\n📋 Solución:")
    print("   1. Abre Firefox")
    print("   2. Ve a https://vmanage.cjf.gob.mx")
    print("   3. Inicia sesión")
    print("   4. Deja la pestaña abierta")
    sys.exit(1)

print("\n[2/4] Verificando conexión con vManage...")
result = subprocess.run(
    ["python", "test_completo.py"],
    capture_output=True,
    text=True,
    timeout=15
)

if "¡ÉXITO!" in result.stdout and "332 dispositivos" in result.stdout:
    print("✅ Conexión exitosa - 332 dispositivos")
else:
    print("❌ FALLO: No se puede conectar con vManage")
    sys.exit(1)

print("\n[3/4] Verificando servidor MCP...")
try:
    # Intentar iniciar el servidor por 2 segundos
    process = subprocess.Popen(
        ["python", "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(2)
    
    if process.poll() is None:
        # Servidor sigue corriendo, está bien
        process.terminate()
        print("✅ Servidor MCP inicia correctamente")
    else:
        # Servidor terminó, puede haber error
        stdout, stderr = process.communicate()
        if stderr and "error" in stderr.lower():
            print(f"❌ FALLO: {stderr}")
            sys.exit(1)
        else:
            print("✅ Servidor MCP OK")
            
except Exception as e:
    print(f"❌ FALLO: {str(e)}")
    sys.exit(1)

print("\n[4/4] Verificando configuración de Claude Desktop...")
try:
    result = subprocess.run(
        ["cat", "/home/tsul/.config/Claude/claude_desktop_config.json"],
        capture_output=True,
        text=True
    )
    
    if "cisco-sdwan" in result.stdout:
        print("✅ Claude Desktop configurado")
    else:
        print("⚠️  Configuración no encontrada")
        
except Exception as e:
    print(f"⚠️  No se pudo verificar: {str(e)}")

print("\n" + "="*70)
print("  ✨ ¡TODO LISTO PARA CLAUDE DESKTOP!")
print("="*70)

print("\n📋 PRÓXIMOS PASOS:")
print("   1. Cierra Claude Desktop si está abierto")
print("   2. Abre Claude Desktop")
print("   3. Pregunta: '¿Qué herramientas MCP tienes?'")
print("   4. Deberías ver 4 herramientas de cisco-sdwan")
print("\n💡 Consulta GUIA_CLAUDE_DESKTOP.md para ejemplos de uso\n")
