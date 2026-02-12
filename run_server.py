#!/usr/bin/env python3
"""
Wrapper para iniciar el servidor MCP
1. Actualiza las cookies en .env silenciosamente
2. Inicia el servidor MCP
"""

import sys
import os

# Asegurarse de que estamos en el directorio correcto
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def actualizar_cookies_silencioso():
    """Actualiza cookies de Analytics Cloud de forma silenciosa"""
    try:
        import browser_cookie3
        
        todas_las_cookies = {}
        
        # Cargar variables de entorno
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except:
            pass
        
        # Extraer cookies de Analytics Cloud (OAuth - requiere navegador)
        browsers = [
            browser_cookie3.chrome,
            browser_cookie3.chromium,
            browser_cookie3.firefox,
            browser_cookie3.edge,
        ]
        
        for browser_func in browsers:
            try:
                cj = browser_func(domain_name='us02.analytics.sdwan.cisco.com')
                session_cookie = None
                csrf_token = None
                overlay_id = None
                
                for cookie in cj:
                    if 'analytics.sdwan.cisco.com' in cookie.domain:
                        if cookie.name == 'session':
                            session_cookie = cookie.value
                        elif cookie.name == 'okta-oauth-state':
                            csrf_token = cookie.value
                        elif cookie.name == 'cl-overlay-id':
                            overlay_id = cookie.value
                
                if session_cookie and csrf_token and overlay_id:
                    todas_las_cookies['ANALYTICS_SESSION_COOKIE'] = session_cookie
                    todas_las_cookies['ANALYTICS_CSRF_TOKEN'] = csrf_token
                    todas_las_cookies['ANALYTICS_OVERLAY_ID'] = overlay_id
                    break  # Salir si se obtuvieron las cookies
            except:
                continue
        
        # Actualizar .env solo con cookies de Analytics (vManage usa API pura)
        if todas_las_cookies:
            try:
                env_path = '.env'
                
                with open(env_path, 'r', encoding='utf-8') as f:
                    lineas = f.readlines()
                
                lineas_actualizadas = []
                cookies_actualizadas = set()
                
                for linea in lineas:
                    linea_modificada = False
                    for key, value in todas_las_cookies.items():
                        if linea.startswith(f"{key}="):
                            lineas_actualizadas.append(f"{key}={value}\n")
                            cookies_actualizadas.add(key)
                            linea_modificada = True
                            break
                    
                    if not linea_modificada:
                        lineas_actualizadas.append(linea)
                
                for key, value in todas_las_cookies.items():
                    if key not in cookies_actualizadas:
                        lineas_actualizadas.append(f"{key}={value}\n")
                
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(lineas_actualizadas)
                
                # Recargar variables de entorno
                try:
                    from dotenv import load_dotenv
                    load_dotenv(override=True)
                except:
                    pass
                    
            except:
                pass
    except:
        pass


if __name__ == "__main__":
    # Redirigir stdout temporalmente para suprimir mensajes de actualización de cookies
    # que interfieren con el protocolo MCP
    import io
    _original_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        # Intentar actualizar cookies (no bloquear si falla)
        actualizar_cookies_silencioso()
    except:
        pass
    finally:
        # Restaurar stdout inmediatamente
        sys.stdout = _original_stdout
    
    # Importar y ejecutar el servidor
    try:
        import server
        server.mcp.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
