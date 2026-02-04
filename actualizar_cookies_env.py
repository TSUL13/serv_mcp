#!/usr/bin/env python3
"""
Actualiza automáticamente las cookies en el archivo .env
Extrae cookies del navegador y las escribe en .env
"""
import os
import re
from browser_cookies import BrowserCookieExtractor
from dotenv import load_dotenv

def actualizar_cookies_en_env():
    """Extrae cookies del navegador y actualiza el archivo .env"""
    
    # Cargar configuración actual
    load_dotenv()
    vmanage_host = os.getenv('VMANAGE_IP', 'vmanage.cjf.gob.mx')
    
    print('🔍 Extrayendo cookies del navegador...')
    extractor = BrowserCookieExtractor(vmanage_host)
    
    # Forzar extracción del navegador (ignorar env vars)
    jsessionid, xsrf_token = extractor.extract_cookies()
    
    if not jsessionid or not xsrf_token:
        print('❌ No se pudieron extraer cookies del navegador')
        print('   Asegúrate de tener una sesión activa en vManage')
        return False
    
    print(f'✅ Cookies extraídas del navegador')
    print(f'   JSESSIONID: {jsessionid[:30]}...')
    print(f'   XSRF-TOKEN: {xsrf_token[:30]}...')
    
    # Leer archivo .env actual
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_path):
        print(f'❌ Archivo .env no encontrado: {env_path}')
        return False
    
    with open(env_path, 'r') as f:
        contenido = f.read()
    
    # Actualizar o agregar VMANAGE_JSESSIONID
    if 'VMANAGE_JSESSIONID=' in contenido:
        contenido = re.sub(
            r'VMANAGE_JSESSIONID=.*',
            f'VMANAGE_JSESSIONID={jsessionid}',
            contenido
        )
        print('✅ VMANAGE_JSESSIONID actualizado')
    else:
        # Agregar al final
        if not contenido.endswith('\n'):
            contenido += '\n'
        contenido += f'\n# Cookies del navegador (actualizadas automáticamente)\n'
        contenido += f'VMANAGE_JSESSIONID={jsessionid}\n'
        print('✅ VMANAGE_JSESSIONID agregado')
    
    # Actualizar o agregar VMANAGE_XSRF_TOKEN
    if 'VMANAGE_XSRF_TOKEN=' in contenido:
        contenido = re.sub(
            r'VMANAGE_XSRF_TOKEN=.*',
            f'VMANAGE_XSRF_TOKEN={xsrf_token}',
            contenido
        )
        print('✅ VMANAGE_XSRF_TOKEN actualizado')
    else:
        contenido += f'VMANAGE_XSRF_TOKEN={xsrf_token}\n'
        print('✅ VMANAGE_XSRF_TOKEN agregado')
    
    # Escribir archivo actualizado
    with open(env_path, 'w') as f:
        f.write(contenido)
    
    print(f'\n✅ Archivo .env actualizado exitosamente')
    print(f'   Ubicación: {env_path}')
    
    return True


if __name__ == '__main__':
    import sys
    
    print('=' * 70)
    print('🔄 Actualizador Automático de Cookies para vManage')
    print('=' * 70)
    print()
    
    exito = actualizar_cookies_en_env()
    
    if exito:
        print()
        print('💡 Las cookies se han actualizado en .env')
        print('   Reinicia Claude Desktop para que tome los cambios:')
        print('   $ pkill -9 -f claude-desktop')
        print()
        sys.exit(0)
    else:
        print()
        print('❌ Error al actualizar cookies')
        print('   1. Verifica que tengas una sesión activa en vManage')
        print('   2. Abre https://vmanage.cjf.gob.mx en tu navegador')
        print('   3. Inicia sesión y vuelve a ejecutar este script')
        print()
        sys.exit(1)
