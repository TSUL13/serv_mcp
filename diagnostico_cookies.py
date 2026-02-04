#!/usr/bin/env python3
"""
Script de diagnóstico detallado para el sistema de cookies
"""
import os
import sys
import browser_cookie3
from pathlib import Path

def verificar_navegador(nombre, func_browser, dominio):
    """Verifica un navegador específico"""
    print(f"\n{'='*60}")
    print(f"  🔍 Verificando {nombre}")
    print(f"{'='*60}")
    
    try:
        cookies = func_browser(domain_name=dominio)
        cookies_list = list(cookies)
        
        print(f"✅ {nombre} detectado")
        print(f"   Total de cookies para {dominio}: {len(cookies_list)}")
        
        if len(cookies_list) > 0:
            print(f"\n   📋 Cookies encontradas:")
            for cookie in cookies_list:
                print(f"      • {cookie.name} = {cookie.value[:30]}...")
                
            # Buscar las cookies específicas que necesitamos
            jsessionid = None
            xsrf_token = None
            
            for cookie in cookies_list:
                if cookie.name == "JSESSIONID":
                    jsessionid = cookie.value
                elif cookie.name == "XSRF-TOKEN":
                    xsrf_token = cookie.value
            
            if jsessionid and xsrf_token:
                print(f"\n   ✅ ¡ENCONTRADAS LAS COOKIES NECESARIAS!")
                print(f"      JSESSIONID: {jsessionid[:40]}...")
                print(f"      XSRF-TOKEN: {xsrf_token[:40]}...")
                return True
            elif jsessionid:
                print(f"\n   ⚠️  Solo encontré JSESSIONID, falta XSRF-TOKEN")
            elif xsrf_token:
                print(f"\n   ⚠️  Solo encontré XSRF-TOKEN, falta JSESSIONID")
            else:
                print(f"\n   ⚠️  No encontré JSESSIONID ni XSRF-TOKEN")
                print(f"      Necesitas iniciar sesión en vManage")
        else:
            print(f"   ⚠️  No hay cookies para {dominio}")
            print(f"      Necesitas abrir vManage en {nombre} e iniciar sesión")
            
    except Exception as e:
        print(f"❌ {nombre} no disponible o error: {str(e)}")
        
    return False


def verificar_archivos_navegador():
    """Verifica que existan los archivos de cookies de los navegadores"""
    print(f"\n{'='*60}")
    print(f"  📁 Verificando archivos de cookies")
    print(f"{'='*60}")
    
    home = str(Path.home())
    
    # Chrome
    chrome_paths = [
        f"{home}/.config/google-chrome/Default/Cookies",
        f"{home}/.config/google-chrome/Default/Network/Cookies",
        f"{home}/.config/chromium/Default/Cookies",
    ]
    
    print("\n🔵 Chrome/Chromium:")
    chrome_found = False
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"   ✅ {path}")
            chrome_found = True
        else:
            print(f"   ❌ {path} (no existe)")
    
    if not chrome_found:
        print("   ⚠️  Chrome no detectado")
    
    # Firefox
    firefox_dir = f"{home}/.mozilla/firefox"
    print("\n🟠 Firefox:")
    if os.path.exists(firefox_dir):
        profiles = [d for d in os.listdir(firefox_dir) if d.endswith('.default') or d.endswith('.default-release')]
        if profiles:
            for profile in profiles:
                cookies_path = f"{firefox_dir}/{profile}/cookies.sqlite"
                if os.path.exists(cookies_path):
                    print(f"   ✅ {cookies_path}")
                else:
                    print(f"   ❌ {cookies_path} (no existe)")
        else:
            print(f"   ⚠️  No se encontraron perfiles de Firefox")
    else:
        print(f"   ❌ Firefox no detectado")
    
    # Edge
    edge_paths = [
        f"{home}/.config/microsoft-edge/Default/Cookies",
        f"{home}/.config/microsoft-edge/Default/Network/Cookies",
    ]
    
    print("\n🔷 Microsoft Edge:")
    edge_found = False
    for path in edge_paths:
        if os.path.exists(path):
            print(f"   ✅ {path}")
            edge_found = True
        else:
            print(f"   ❌ {path} (no existe)")
    
    if not edge_found:
        print("   ⚠️  Edge no detectado")


def main():
    print("\n" + "="*60)
    print("  🔬 DIAGNÓSTICO COMPLETO DEL SISTEMA DE COOKIES")
    print("="*60)
    
    # Verificar archivos de navegador
    verificar_archivos_navegador()
    
    # Intentar extraer de cada navegador
    dominio = "vmanage.cjf.gob.mx"
    
    print(f"\n{'='*60}")
    print(f"  🌐 Intentando extraer cookies de {dominio}")
    print(f"{'='*60}")
    
    navegadores = [
        ("Chrome", browser_cookie3.chrome),
        ("Firefox", browser_cookie3.firefox),
        ("Edge", browser_cookie3.edge),
        ("Chromium", browser_cookie3.chromium),
    ]
    
    encontrado = False
    for nombre, func in navegadores:
        if verificar_navegador(nombre, func, dominio):
            encontrado = True
            break
    
    # Resumen final
    print(f"\n{'='*60}")
    if encontrado:
        print("  ✅ SISTEMA LISTO")
        print("="*60)
        print("\n💡 Puedes usar:")
        print("   • python cli.py")
        print("   • Claude Desktop\n")
    else:
        print("  ❌ NO SE ENCONTRARON COOKIES VÁLIDAS")
        print("="*60)
        print("\n📋 SOLUCIÓN:")
        print("   1. Abre Chrome, Firefox o Edge")
        print("   2. Ve a: https://vmanage.cjf.gob.mx")
        print("   3. Inicia sesión con tus credenciales")
        print("   4. Verifica que la sesión esté activa")
        print("   5. DEJA LA PESTAÑA ABIERTA")
        print("   6. Ejecuta este script nuevamente")
        print("\n💡 ALTERNATIVA: Puedo crear un sistema que copie/pegue cookies manualmente")
        print("   si el navegador no es compatible con browser-cookie3\n")


if __name__ == "__main__":
    main()
