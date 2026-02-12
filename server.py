#!/usr/bin/env python3
"""
Servidor MCP para gestión de Cisco SD-WAN (vManage)
Desarrollado con FastMCP para Network Automation

AUTENTICACIÓN:
- vManage: API REST con usuario/contraseña
"""

import os
import sys
import requests
import urllib3
import base64
import threading
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastmcp import FastMCP

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cargar variables de entorno
load_dotenv()

# Inicializar servidor MCP
mcp = FastMCP("cisco-sdwan-manager")


class VManageSession:
    """Clase para gestionar la sesión con vManage usando API PURA
    
    Autenticación programática con usuario/contraseña (NO requiere cookies previas)
    Este es el método correcto para automatización y scripts.
    """
    
    def __init__(self, ip: str, username: str, password: str):
        self.base_url = f"https://{ip}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
        
    def login(self) -> bool:
        """
        Autenticación PROGRAMÁTICA con vManage (API Pura).
        
        NO requiere cookies del navegador.
        Hace POST a /j_security_check con usuario/contraseña.
        
        Returns:
            bool: True si login exitoso, False en caso contrario
        """
        try:
            from datetime import datetime
            print(f"\n🔐 [{datetime.now().strftime('%H:%M:%S')}] Autenticando con vManage (API Pura)...")
            
            # 1. POST con credenciales (API Pura - sin cookies previas)
            login_url = f"{self.base_url}/j_security_check"
            login_data = {
                'j_username': self.username,
                'j_password': self.password
            }
            
            login_response = self.session.post(
                login_url,
                data=login_data,
                verify=False,
                timeout=30
            )
            
            # Verificar que recibimos cookies de sesión
            if 'JSESSIONID' not in self.session.cookies:
                print(f"❌ Login falló - No se recibió JSESSIONID")
                print(f"   Status: {login_response.status_code}")
                return False
            
            jsessionid = self.session.cookies.get('JSESSIONID')
            print(f"✓ JSESSIONID obtenido: {jsessionid[:30]}...")
            
            # 2. Obtener token XSRF
            token_url = f"{self.base_url}/dataservice/client/token"
            token_response = self.session.get(
                token_url,
                verify=False,
                timeout=10
            )
            
            if token_response.status_code != 200:
                print(f"❌ No se pudo obtener XSRF token")
                return False
            
            self.token = token_response.text
            print(f"✓ XSRF-Token obtenido: {self.token[:30]}...")
            
            # 3. Configurar headers para futuras peticiones
            self.session.headers.update({
                "X-XSRF-TOKEN": self.token,
                "Content-Type": "application/json"
            })
            
            # 4. Verificar que la API funciona
            test_url = f"{self.base_url}/dataservice/device"
            test_response = self.session.get(test_url, timeout=10)
            
            if test_response.status_code == 200:
                print(f"✅ Autenticación exitosa (API Pura)")
                return True
            else:
                print(f"❌ API no responde correctamente: {test_response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout al conectar con vManage")
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Error de conexión - Verifica que vManage esté accesible")
            return False
        except Exception as e:
            print(f"❌ Error durante login: {str(e)}")
            return False
    
    def get(self, endpoint: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Realiza una petición GET al API de vManage
        
        Args:
            endpoint: Endpoint del API (sin base_url)
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Dict con la respuesta JSON del API
        """
        try:
            url = f"{self.base_url}{endpoint}"
            # Log de la consulta
            print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] GET {endpoint[:100]}", file=sys.stderr)
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            result = response.json()
            # Log del resultado
            if isinstance(result, dict) and 'data' in result:
                data_count = len(result['data']) if isinstance(result['data'], list) else 1
                print(f"   ✓ Respuesta: {data_count} registro(s)", file=sys.stderr)
            return result
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout", file=sys.stderr)
            raise TimeoutError(f"Timeout al consultar {endpoint}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error: {str(e)[:80]}", file=sys.stderr)
            raise ConnectionError(f"Error en petición GET a {endpoint}: {str(e)}")
    
    def post(self, endpoint: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Realiza una petición POST al API de vManage
        
        Args:
            endpoint: Endpoint del API (sin base_url)
            payload: Datos a enviar en el body
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Dict con la respuesta JSON del API
        """
        try:
            url = f"{self.base_url}{endpoint}"
            # Log de la consulta
            print(f"📤 [{datetime.now().strftime('%H:%M:%S')}] POST {endpoint[:100]}", file=sys.stderr)
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            result = response.json()
            # Log del resultado
            print(f"   ✓ Respuesta recibida", file=sys.stderr)
            return result
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout", file=sys.stderr)
            raise TimeoutError(f"Timeout al consultar {endpoint}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error: {str(e)[:80]}", file=sys.stderr)
            raise ConnectionError(f"Error en petición POST a {endpoint}: {str(e)}")


def get_vmanage_session() -> VManageSession:
    """
    Crea y autentica una sesión con vManage usando API PURA.
    
    Autenticación programática con usuario/contraseña del .env.
    NO requiere cookies del navegador ni variables JSESSIONID/XSRF_TOKEN en .env.
    
    Returns:
        VManageSession autenticada con API pura
        
    Raises:
        ValueError: Si faltan credenciales (IP, usuario, contraseña)
        ConnectionError: Si falla la autenticación
    """
    vmanage_ip = os.getenv('VMANAGE_IP')
    username = os.getenv('VMANAGE_USERNAME')
    password = os.getenv('VMANAGE_PASSWORD')
    
    if not all([vmanage_ip, username, password]):
        raise ValueError(
            "❌ Faltan credenciales de vManage en el archivo .env\n\n"
            "Se requieren:\n"
            "  VMANAGE_IP=tu_vmanage_ip\n"
            "  VMANAGE_USERNAME=tu_usuario\n"
            "  VMANAGE_PASSWORD=tu_contraseña\n\n"
            "NO necesitas VMANAGE_JSESSIONID ni VMANAGE_XSRF_TOKEN\n"
            "(Se generan automáticamente con API pura)"
        )
    
    # Crear sesión con API pura (genera sus propias cookies)
    session = VManageSession(vmanage_ip, username, password)
    
    if not session.login():
        raise ConnectionError(
            "❌ Error de autenticación con vManage\n\n"
            "Verifica:\n"
            "  • Credenciales correctas en .env\n"
            "  • vManage accesible en la red\n"
            "  • Usuario tiene permisos adecuados"
        )
    
    return session


class CatalystCenterSession:
    """Clase para gestionar la sesión con Cisco Catalyst Center con renovación automática de token"""
    
    def __init__(self, ip: str, username: str, password: str):
        self.base_url = f"https://{ip}"
        self.username = username
        self.password = password
        self.token = None
        self.token_expiry = None
        self.session = requests.Session()
        self.session.verify = False
        self._token_lock = threading.Lock()
        self._auto_refresh = False
        self._refresh_thread = None
        
    def obtener_token(self) -> str:
        """
        Obtiene un token de autenticación de Catalyst Center.
        El token tiene validez de 60 minutos.
        
        Returns:
            str: Token de autenticación
            
        Raises:
            ConnectionError: Si falla la autenticación
        """
        with self._token_lock:
            try:
                # Codificar credenciales en Base64
                credentials = f"{self.username}:{self.password}"
                encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                
                # Preparar headers para autenticación
                headers = {
                    'Authorization': f'Basic {encoded_credentials}',
                    'Content-Type': 'application/json'
                }
                
                # Realizar petición POST para obtener token
                auth_url = f"{self.base_url}/dna/system/api/v1/auth/token"
                response = self.session.post(
                    auth_url,
                    headers=headers,
                    verify=False,
                    timeout=30
                )
                
                response.raise_for_status()
                
                # Extraer token de la respuesta
                token_data = response.json()
                self.token = token_data.get('Token')
                
                if not self.token:
                    raise ConnectionError("No se recibió token en la respuesta")
                
                # Establecer tiempo de expiración (55 minutos para renovar antes)
                self.token_expiry = datetime.now() + timedelta(minutes=55)
                
                # Configurar headers de sesión con el token
                self.session.headers.update({
                    'X-Auth-Token': self.token,
                    'Content-Type': 'application/json'
                })
                
                print(f"✓ Token obtenido exitosamente. Válido hasta: {self.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
                
                return self.token
                
            except requests.exceptions.RequestException as e:
                raise ConnectionError(f"Error al obtener token de Catalyst Center: {str(e)}")
            except Exception as e:
                raise ConnectionError(f"Error inesperado al obtener token: {str(e)}")
    
    def _verificar_y_renovar_token(self) -> None:
        """
        Verifica si el token está por expirar y lo renueva si es necesario.
        Se llama automáticamente antes de cada petición.
        """
        if not self.token or not self.token_expiry:
            self.obtener_token()
        elif datetime.now() >= self.token_expiry:
            print("⚠️  Token expirado, renovando...")
            self.obtener_token()
    
    def _auto_refresh_loop(self) -> None:
        """
        Loop en segundo plano para renovar el token automáticamente cada 55 minutos.
        """
        while self._auto_refresh:
            time.sleep(3300)  # 55 minutos
            if self._auto_refresh:  # Verificar nuevamente antes de renovar
                try:
                    print("🔄 Renovación automática de token programada...")
                    self.obtener_token()
                except Exception as e:
                    print(f"❌ Error en renovación automática: {e}")
    
    def iniciar_renovacion_automatica(self) -> None:
        """
        Inicia un hilo en segundo plano que renovará el token automáticamente cada 55 minutos.
        Útil para scripts de larga duración.
        """
        if not self._auto_refresh:
            self._auto_refresh = True
            self._refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
            self._refresh_thread.start()
            print("✓ Renovación automática de token iniciada")
    
    def detener_renovacion_automatica(self) -> None:
        """
        Detiene la renovación automática del token.
        """
        if self._auto_refresh:
            self._auto_refresh = False
            print("✓ Renovación automática de token detenida")
    
    def get(self, endpoint: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Realiza una petición GET al API de Catalyst Center.
        Renueva el token automáticamente si es necesario.
        
        Args:
            endpoint: Endpoint del API (sin base_url)
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Dict con la respuesta JSON del API
        """
        self._verificar_y_renovar_token()
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=timeout)
            
            # Si recibimos 401, intentar renovar token y reintentar
            if response.status_code == 401:
                print("⚠️  Token inválido, renovando...")
                self.obtener_token()
                response = self.session.get(url, timeout=timeout)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout al consultar {endpoint}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error en petición GET a {endpoint}: {str(e)}")
    
    def post(self, endpoint: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Realiza una petición POST al API de Catalyst Center.
        Renueva el token automáticamente si es necesario.
        
        Args:
            endpoint: Endpoint del API (sin base_url)
            payload: Datos a enviar en el body
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Dict con la respuesta JSON del API
        """
        self._verificar_y_renovar_token()
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.post(url, json=payload, timeout=timeout)
            
            # Si recibimos 401, intentar renovar token y reintentar
            if response.status_code == 401:
                print("⚠️  Token inválido, renovando...")
                self.obtener_token()
                response = self.session.post(url, json=payload, timeout=timeout)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout al consultar {endpoint}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error en petición POST a {endpoint}: {str(e)}")


def get_catalyst_session(auto_refresh: bool = False) -> CatalystCenterSession:
    """
    Crea y autentica una sesión con Catalyst Center usando credenciales del .env.
    
    Args:
        auto_refresh: Si es True, inicia renovación automática del token cada 55 minutos
    
    Returns:
        CatalystCenterSession autenticada
        
    Raises:
        ValueError: Si faltan variables de entorno
        ConnectionError: Si falla la autenticación
    """
    catalyst_ip = os.getenv('CATALYST_IP')
    username = os.getenv('CATALYST_USERNAME')
    password = os.getenv('CATALYST_PASSWORD')
    
    if not all([catalyst_ip, username, password]):
        raise ValueError(
            "Faltan credenciales de Catalyst Center en el archivo .env. "
            "Se requieren: CATALYST_IP, CATALYST_USERNAME, CATALYST_PASSWORD"
        )
    
    session = CatalystCenterSession(catalyst_ip, username, password)
    session.obtener_token()
    
    if auto_refresh:
        session.iniciar_renovacion_automatica()
    
    return session


@mcp.tool()
def listar_dispositivos() -> str:
    """
    Lista todos los dispositivos en el inventario de SD-WAN (vEdges, vSmarts, vBonds, etc.)
    
    Returns:
        JSON string con el inventario completo de dispositivos
    """
    print(f"\n🔧 [{datetime.now().strftime('%H:%M:%S')}] HERRAMIENTA INVOCADA: listar_dispositivos", file=sys.stderr)
    try:
        session = get_vmanage_session()
        endpoint = "/dataservice/device"
        result = session.get(endpoint)
        
        if 'data' in result:
            devices = result['data']
            
            # Formatear respuesta con información relevante
            formatted_devices = []
            for device in devices:
                formatted_devices.append({
                    'hostname': device.get('host-name', 'N/A'),
                    'device_id': device.get('system-ip', 'N/A'),
                    'device_type': device.get('device-type', 'N/A'),
                    'device_model': device.get('device-model', 'N/A'),
                    'site_id': device.get('site-id', 'N/A'),
                    'version': device.get('version', 'N/A'),
                    'reachability': device.get('reachability', 'N/A'),
                    'status': device.get('state', 'N/A'),
                    'uuid': device.get('uuid', 'N/A')
                })
            
            return f"Total de dispositivos: {len(formatted_devices)}\n\nDispositivos:\n{formatted_devices}"
        
        return "No se encontraron dispositivos"
        
    except ValueError as e:
        return f"Error de configuración: {str(e)}"
    except (ConnectionError, TimeoutError) as e:
        return f"Error de conexión: {str(e)}"
    except Exception as e:
        return f"Error inesperado: {str(e)}"


@mcp.tool()
def ver_salud_equipo(device_id: str) -> str:
    """
    Consulta el estado de salud y alcanzabilidad de un dispositivo específico
    
    Args:
        device_id: System IP del dispositivo (device-id)
    
    Returns:
        JSON string con el estado de salud del dispositivo
    """
    try:
        session = get_vmanage_session()
        
        # Obtener información básica del dispositivo
        endpoint = f"/dataservice/device?system-ip={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result and len(result['data']) > 0:
            device = result['data'][0]
            
            health_info = {
                'hostname': device.get('host-name', 'N/A'),
                'device_id': device.get('system-ip', 'N/A'),
                'device_type': device.get('device-type', 'N/A'),
                'device_model': device.get('device-model', 'N/A'),
                'site_id': device.get('site-id', 'N/A'),
                'reachability': device.get('reachability', 'N/A'),
                'status': device.get('state', 'N/A'),
                'uptime': device.get('uptime-date', 'N/A'),
                'version': device.get('version', 'N/A'),
                'board_serial': device.get('board-serial', 'N/A'),
                'certificate_validity': device.get('validity', 'N/A')
            }
            
            # Intentar obtener métricas de salud adicionales
            try:
                health_endpoint = f"/dataservice/device/health?deviceId={device_id}"
                health_result = session.get(health_endpoint, timeout=10)
                if 'data' in health_result:
                    health_info['health_metrics'] = health_result['data']
            except Exception:
                health_info['health_metrics'] = 'No disponible'
            
            return f"Estado de salud del dispositivo {device_id}:\n\n{health_info}"
        
        return f"No se encontró el dispositivo con ID: {device_id}"
        
    except ValueError as e:
        return f"Error de configuración: {str(e)}"
    except (ConnectionError, TimeoutError) as e:
        return f"Error de conexión: {str(e)}"
    except Exception as e:
        return f"Error inesperado: {str(e)}"


@mcp.tool()
def ver_sesiones_bfd(device_id: str) -> str:
    """
    Consulta el estado de las sesiones BFD (túneles) para un dispositivo específico
    
    Args:
        device_id: System IP del dispositivo
    
    Returns:
        JSON string con el estado de las sesiones BFD
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/bfd/sessions?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            bfd_sessions = result['data']
            
            if not bfd_sessions:
                return f"No hay sesiones BFD activas para el dispositivo {device_id}"
            
            # Formatear información de sesiones BFD
            formatted_sessions = []
            for session_data in bfd_sessions:
                formatted_sessions.append({
                    'system_ip': session_data.get('system-ip', 'N/A'),
                    'site_id': session_data.get('site-id', 'N/A'),
                    'local_color': session_data.get('local-color', 'N/A'),
                    'remote_color': session_data.get('color', 'N/A'),
                    'state': session_data.get('state', 'N/A'),
                    'peer_system_ip': session_data.get('src-ip', 'N/A'),
                    'dst_ip': session_data.get('dst-ip', 'N/A'),
                    'uptime': session_data.get('uptime-date', 'N/A'),
                    'transitions': session_data.get('transitions', 'N/A')
                })
            
            # Contar estados
            state_counts = {}
            for sess in bfd_sessions:
                state = sess.get('state', 'unknown')
                state_counts[state] = state_counts.get(state, 0) + 1
            
            return (
                f"Sesiones BFD para dispositivo {device_id}:\n\n"
                f"Total de sesiones: {len(formatted_sessions)}\n"
                f"Estados: {state_counts}\n\n"
                f"Detalle de sesiones:\n{formatted_sessions}"
            )
        
        return f"No se pudo obtener información de sesiones BFD para {device_id}"
        
    except ValueError as e:
        return f"Error de configuración: {str(e)}"
    except (ConnectionError, TimeoutError) as e:
        return f"Error de conexión: {str(e)}"
    except Exception as e:
        return f"Error inesperado: {str(e)}"


@mcp.tool()
def ver_total_sesiones_bfd() -> str:
    """
    Cuenta el total de sesiones BFD en toda la red SD-WAN (optimizado)
    
    Returns:
        Total de sesiones BFD con estadísticas por estado
    """
    try:
        session = get_vmanage_session()
        
        # OPTIMIZACIÓN: Usar endpoint agregado en lugar de iterar dispositivos
        # Esto reduce de 331 consultas a solo 1
        bfd_result = session.get("/dataservice/device/bfd/sessions", timeout=30)
                    
        # OPTIMIZACIÓN: Usar endpoint agregado en lugar de iterar dispositivos
        # Esto reduce de 331 consultas a solo 1
        bfd_result = session.get("/dataservice/device/bfd/sessions", timeout=30)
        
        if 'data' not in bfd_result:
            return "No se pudieron obtener las sesiones BFD"
        
        bfd_sessions = bfd_result['data']
        total_sesiones = len(bfd_sessions)
        
        # Contar por estado
        sesiones_por_estado = {'up': 0, 'down': 0, 'init': 0, 'other': 0}
        dispositivos_con_bfd = set()
        
        for sess in bfd_sessions:
            state = sess.get('state', '').lower()
            system_ip = sess.get('system-ip', 'N/A')
            
            dispositivos_con_bfd.add(system_ip)
            
            if state == 'up':
                sesiones_por_estado['up'] += 1
            elif state == 'down':
                sesiones_por_estado['down'] += 1
            elif state == 'init':
                sesiones_por_estado['init'] += 1
            else:
                sesiones_por_estado['other'] += 1
        
        # Calcular porcentaje de sesiones UP
        porcentaje_up = (sesiones_por_estado['up'] / total_sesiones * 100) if total_sesiones > 0 else 0
        
        resultado = {
            'total_sesiones_bfd': total_sesiones,
            'sesiones_up': sesiones_por_estado['up'],
            'sesiones_down': sesiones_por_estado['down'],
            'sesiones_init': sesiones_por_estado['init'],
            'sesiones_other': sesiones_por_estado['other'],
            'porcentaje_up': f"{porcentaje_up:.2f}%",
            'dispositivos_con_bfd': len(dispositivos_con_bfd)
        }
        
        return (
            f"📊 TOTAL DE SESIONES BFD EN LA RED\n\n"
            f"Total de sesiones BFD: {total_sesiones}\n\n"
            f"Por estado:\n"
            f"  ✅ UP: {sesiones_por_estado['up']} ({porcentaje_up:.1f}%)\n"
            f"  ❌ DOWN: {sesiones_por_estado['down']}\n"
            f"  🔄 INIT: {sesiones_por_estado['init']}\n"
            f"  ⚠️  OTHER: {sesiones_por_estado['other']}\n\n"
            f"Dispositivos con BFD: {len(dispositivos_con_bfd)}\n\n"
            f"Detalle completo:\n{resultado}"
        )
        
    except Exception as e:
        return f"Error al obtener total de sesiones BFD: {str(e)}"


@mcp.tool()
def diagnosticar_dpi_dispositivo(identificador: str) -> str:
    """
    Diagnóstico completo de DPI para un dispositivo o sitio específico.
    Verifica configuración, estado del servicio, aplicaciones detectadas y flujos DPI.
    
    Args:
        identificador: Puede ser:
                      - Site ID (ej: "318", "51318")
                      - Hostname (ej: "SDWAN-CJF-318-RT01")
                      - System IP (ej: "10.95.11.3")
    
    Returns:
        Diagnóstico detallado de DPI incluyendo:
        - Estado de dispositivos
        - Configuración DPI
        - Aplicaciones detectadas
        - Flujos DPI activos
        - Recomendaciones para solucionar problemas
        
    Ejemplo:
        diagnosticar_dpi_dispositivo("318")
        diagnosticar_dpi_dispositivo("SDWAN-CJF-318-RT01")
    """
    print(f"\n🔧 [{datetime.now().strftime('%H:%M:%S')}] HERRAMIENTA INVOCADA: diagnosticar_dpi_dispositivo", file=sys.stderr)
    try:
        session = get_vmanage_session()
        
        resultado = f"🔍 DIAGNÓSTICO DPI\n"
        resultado += f"{'='*80}\n"
        resultado += f"Criterio de búsqueda: {identificador}\n\n"
        
        # Buscar dispositivos que coincidan
        devices_result = session.get("/dataservice/device")
        
        if 'data' not in devices_result:
            return "❌ No se pudieron obtener los dispositivos"
        
        # Filtrar dispositivos
        matched_devices = []
        for dev in devices_result['data']:
            site_id = str(dev.get('site-id', ''))
            hostname = dev.get('host-name', '')
            system_ip = dev.get('system-ip', '')
            
            if (identificador in site_id or
                identificador.upper() in hostname.upper() or
                identificador == system_ip):
                matched_devices.append(dev)
        
        if not matched_devices:
            return (
                f"{resultado}\n"
                f"❌ No se encontraron dispositivos con '{identificador}'\n\n"
                f"Verifica:\n"
                f"  • Site ID (ej: 318 o 51318)\n"
                f"  • Hostname (ej: SDWAN-CJF-318-RT01)\n"
                f"  • System IP (ej: 10.95.11.3)"
            )
        
        resultado += f"✅ {len(matched_devices)} dispositivo(s) encontrado(s)\n\n"
        resultado += f"{'='*80}\n\n"
        
        # Analizar cada dispositivo
        for i, device in enumerate(matched_devices, 1):
            hostname = device.get('host-name', 'N/A')
            system_ip = device.get('system-ip', 'N/A')
            device_id = device.get('deviceId', system_ip)
            model = device.get('device-model', 'N/A')
            site_id = device.get('site-id', 'N/A')
            reachability = device.get('reachability', 'unknown')
            state = device.get('state', 'N/A')
            
            status_icon = "🟢" if reachability == "reachable" else "🔴"
            
            resultado += f"{i}. {status_icon} {hostname}\n"
            resultado += f"{'─'*80}\n"
            resultado += f"   Site ID: {site_id}\n"
            resultado += f"   System IP: {system_ip}\n"
            resultado += f"   Modelo: {model}\n"
            resultado += f"   Estado: {state} / {reachability}\n\n"
            
            if reachability != "reachable":
                resultado += f"   ⚠️  Dispositivo no alcanzable - diagnóstico limitado\n\n"
                continue
            
            # Verificar servicio DPI
            resultado += f"   📊 SERVICIO DPI:\n"
            try:
                dpi_summary_endpoint = f"/dataservice/device/dpi/summary?deviceId={device_id}"
                dpi_summary = session.get(dpi_summary_endpoint, timeout=10)
                
                if 'data' in dpi_summary and dpi_summary['data']:
                    resultado += f"   ✅ Servicio DPI activo\n"
                else:
                    resultado += f"   ❌ Servicio DPI no devuelve datos\n"
            except Exception as e:
                resultado += f"   ❌ Servicio DPI no accesible\n"
            
            # Verificar aplicaciones detectadas
            resultado += f"\n   📱 APLICACIONES DETECTADAS:\n"
            try:
                apps_endpoint = f"/dataservice/device/dpi/applications?deviceId={device_id}"
                apps_result = session.get(apps_endpoint, timeout=10)
                
                if 'data' in apps_result:
                    apps = apps_result['data']
                    if apps:
                        resultado += f"   ✅ {len(apps)} aplicaciones detectadas\n\n"
                        
                        # Top 10 aplicaciones
                        apps_sorted = sorted(
                            apps,
                            key=lambda x: int(x.get('rx-bytes', 0)) + int(x.get('tx-bytes', 0)),
                            reverse=True
                        )[:10]
                        
                        resultado += f"   🔝 Top 10 aplicaciones por tráfico:\n"
                        for j, app in enumerate(apps_sorted, 1):
                            app_name = app.get('application', 'unknown')
                            familia = app.get('family', 'N/A')
                            rx_bytes = int(app.get('rx-bytes', 0))
                            tx_bytes = int(app.get('tx-bytes', 0))
                            total_bytes = rx_bytes + tx_bytes
                            
                            if total_bytes > 1024**3:  # GB
                                size_str = f"{total_bytes / (1024**3):.2f} GB"
                            elif total_bytes > 1024**2:  # MB
                                size_str = f"{total_bytes / (1024**2):.2f} MB"
                            else:
                                size_str = f"{total_bytes / 1024:.2f} KB"
                            
                            resultado += f"      {j:2}. {app_name:25} ({familia:20}) - {size_str}\n"
                    else:
                        resultado += f"   ⚠️  DPI activo pero sin aplicaciones detectadas\n"
                        resultado += f"\n   💡 Posibles causas:\n"
                        resultado += f"      • No hay tráfico activo en este momento\n"
                        resultado += f"      • El tráfico es todo encrypted/unknown\n"
                        resultado += f"      • Esperar 5-10 minutos para acumular estadísticas\n"
            except Exception as e:
                resultado += f"   ❌ No se pueden consultar aplicaciones\n"
            
            resultado += f"\n"
        
        # Verificar flujos DPI globales para estos dispositivos
        resultado += f"{'='*80}\n"
        resultado += f"🌐 FLUJOS DPI EN ESTADÍSTICAS GLOBALES:\n\n"
        
        try:
            # Limitar a 1000 flujos para performance
            dpi_stats = session.get("/dataservice/statistics/dpi", timeout=30)
            
            if 'data' in dpi_stats:
                all_flows = dpi_stats['data']
                
                # Filtrar flujos de los dispositivos encontrados
                device_hostnames = [d.get('host-name', '') for d in matched_devices]
                site_flows = [f for f in all_flows if f.get('host_name', '') in device_hostnames]
                
                if site_flows:
                    resultado += f"✅ {len(site_flows)} flujos DPI encontrados\n\n"
                    
                    # Analizar aplicaciones en flujos
                    apps_in_flows = {}
                    for flow in site_flows:
                        app = flow.get('application', 'unknown')
                        octets = int(flow.get('octets', 0))
                        if app not in apps_in_flows:
                            apps_in_flows[app] = 0
                        apps_in_flows[app] += octets
                    
                    resultado += f"📊 Top aplicaciones en flujos activos:\n"
                    for app, octets in sorted(apps_in_flows.items(), key=lambda x: x[1], reverse=True)[:15]:
                        if octets > 1024**2:
                            size_str = f"{octets / (1024**2):.2f} MB"
                        elif octets > 1024:
                            size_str = f"{octets / 1024:.2f} KB"
                        else:
                            size_str = f"{octets} B"
                        resultado += f"   • {app:30} - {size_str}\n"
                else:
                    resultado += f"⚠️  No hay flujos DPI activos en este momento\n\n"
                    resultado += f"Esto significa que:\n"
                    resultado += f"  1. No hay tráfico pasando por los dispositivos actualmente\n"
                    resultado += f"  2. O el tráfico no está siendo inspeccionado por DPI\n"
        except Exception as e:
            resultado += f"⚠️  No se pudieron consultar flujos DPI globales\n"
        
        # Recomendaciones
        resultado += f"\n{'='*80}\n"
        resultado += f"💡 RECOMENDACIONES:\n\n"
        
        # Determinar qué recomendar basado en los resultados
        tiene_servicio_dpi = False
        tiene_aplicaciones = False
        tiene_flujos = False
        
        try:
            for device in matched_devices:
                device_id = device.get('deviceId', device.get('system-ip', ''))
                
                # Check DPI service
                dpi_summary = session.get(f"/dataservice/device/dpi/summary?deviceId={device_id}", timeout=5)
                if 'data' in dpi_summary and dpi_summary['data']:
                    tiene_servicio_dpi = True
                
                # Check applications
                apps_result = session.get(f"/dataservice/device/dpi/applications?deviceId={device_id}", timeout=5)
                if 'data' in apps_result and apps_result['data']:
                    tiene_aplicaciones = True
        except:
            pass
        
        if not tiene_servicio_dpi:
            resultado += f"❌ DPI no está habilitado:\n"
            resultado += f"   1. Ve a vManage GUI → Configuration → Policies\n"
            resultado += f"   2. Crea o edita una Centralized Policy\n"
            resultado += f"   3. Habilita 'Application Aware Routing'\n"
            resultado += f"   4. En Security Policy, habilita DPI/Firewall\n"
            resultado += f"   5. Aplica la política al sitio\n\n"
        elif not tiene_aplicaciones:
            resultado += f"⚠️  DPI habilitado pero sin datos:\n"
            resultado += f"   1. Genera tráfico de prueba (navega web, YouTube, etc.)\n"
            resultado += f"   2. Espera 5-10 minutos para que se acumulen estadísticas\n"
            resultado += f"   3. Verifica que el tráfico pase por estos routers\n"
            resultado += f"   4. Usa 'ver_estadisticas_interfaces' para verificar tráfico\n\n"
        else:
            resultado += f"✅ DPI funcionando correctamente\n\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error en diagnóstico DPI: {str(e)}"


@mcp.tool()
def listar_alarmas_criticas() -> str:
    """
    Lista todas las alarmas de nivel crítico de las últimas 24 horas
    
    Returns:
        JSON string con las alarmas críticas activas
    """
    try:
        session = get_vmanage_session()
        
        # Calcular timestamp de hace 24 horas (en milisegundos)
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        from_time = int(yesterday.timestamp() * 1000)
        to_time = int(now.timestamp() * 1000)
        
        # Consultar alarmas críticas
        endpoint = "/dataservice/alarms"
        result = session.get(endpoint)
        
        if 'data' in result:
            all_alarms = result['data']
            
            # Filtrar alarmas críticas de las últimas 24 horas
            critical_alarms = []
            for alarm in all_alarms:
                # Verificar nivel crítico
                severity = alarm.get('severity', '').lower()
                entry_time = alarm.get('entry_time', 0)
                
                if severity == 'critical' and entry_time >= from_time:
                    critical_alarms.append({
                        'alarm_id': alarm.get('uuid', 'N/A'),
                        'severity': alarm.get('severity', 'N/A'),
                        'message': alarm.get('message', 'N/A'),
                        'device': alarm.get('system-ip', 'N/A'),
                        'hostname': alarm.get('host-name', 'N/A'),
                        'site_id': alarm.get('site-id', 'N/A'),
                        'entry_time': datetime.fromtimestamp(entry_time / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                        'acknowledged': alarm.get('acknowledged', False),
                        'active': alarm.get('active', 'N/A')
                    })
            
            if not critical_alarms:
                return "No hay alarmas críticas en las últimas 24 horas"
            
            return (
                f"Alarmas críticas (últimas 24 horas):\n\n"
                f"Total: {len(critical_alarms)}\n\n"
                f"Detalle:\n{critical_alarms}"
            )
        
        return "No se pudieron obtener las alarmas"
        
    except ValueError as e:
        return f"Error de configuración: {str(e)}"
    except (ConnectionError, TimeoutError) as e:
        return f"Error de conexión: {str(e)}"
    except Exception as e:
        return f"Error inesperado: {str(e)}"


# ============================================================================
# FASE 1: FUNCIONES ESENCIALES - MONITOREO Y CONECTIVIDAD
# ============================================================================

@mcp.tool()
def ver_uso_cpu_memoria(device_id: str) -> str:
    """
    Consulta el uso de CPU y memoria de un dispositivo en tiempo real
    
    Args:
        device_id: System IP del dispositivo (ejemplo: 10.80.10.207)
    
    Returns:
        Porcentaje de uso de CPU, memoria y procesos top
    """
    try:
        session = get_vmanage_session()
        
        # Obtener estado del sistema
        endpoint = f"/dataservice/device/system/status?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result and len(result['data']) > 0:
            system_status = result['data'][0]
            
            metrics = {
                'hostname': system_status.get('vdevice-host-name', 'N/A'),
                'device_id': device_id,
                'cpu_user': system_status.get('cpu-user', 'N/A'),
                'cpu_system': system_status.get('cpu-system', 'N/A'),
                'cpu_idle': system_status.get('cpu-idle', 'N/A'),
                'mem_total_mb': system_status.get('mem-total', 'N/A'),
                'mem_used_mb': system_status.get('mem-used', 'N/A'),
                'mem_free_mb': system_status.get('mem-free', 'N/A'),
                'mem_used_percent': system_status.get('mem-used-percent', 'N/A'),
                'disk_used_percent': system_status.get('disk-used', 'N/A'),
                'uptime': system_status.get('up-time', 'N/A')
            }
            
            # Calcular CPU total usado
            try:
                cpu_idle = float(metrics['cpu_idle'])
                cpu_usado = 100 - cpu_idle
                metrics['cpu_usado_percent'] = f"{cpu_usado:.2f}"
            except:
                metrics['cpu_usado_percent'] = 'N/A'
            
            return (
                f"Uso de recursos del dispositivo {device_id}:\n\n"
                f"Hostname: {metrics['hostname']}\n"
                f"CPU Usado: {metrics['cpu_usado_percent']}%\n"
                f"Memoria Usada: {metrics['mem_used_percent']}%\n"
                f"Disco Usado: {metrics['disk_used_percent']}%\n"
                f"Uptime: {metrics['uptime']}\n\n"
                f"Detalle completo:\n{metrics}"
            )
        
        return f"No se pudo obtener información del sistema para {device_id}"
        
    except Exception as e:
        return f"Error al obtener uso de CPU/memoria: {str(e)}"


@mcp.tool()
def ver_tuneles_omp(device_id: str) -> str:
    """
    Lista todos los túneles OMP (Overlay Management Protocol) de un dispositivo
    
    Args:
        device_id: System IP del dispositivo (ejemplo: 10.80.10.207)
    
    Returns:
        Estado de túneles OMP, peers y rutas anunciadas
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/omp/peers?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            peers = result['data']
            tunnel_info = []
            
            for peer in peers:
                tunnel_info.append({
                    'peer': peer.get('peer', 'N/A'),
                    'state': peer.get('state', 'N/A'),
                    'type': peer.get('type', 'N/A'),
                    'domain_id': peer.get('domain-id', 'N/A'),
                    'site_id': peer.get('site-id', 'N/A'),
                    'routes_received': peer.get('routes-received', 0),
                    'routes_sent': peer.get('routes-sent', 0),
                    'vsmart_controllers': peer.get('vsmart-controllers', 0),
                    'uptime': peer.get('up-time', 'N/A')
                })
            
            if not tunnel_info:
                return f"No se encontraron túneles OMP para el dispositivo {device_id}"
            
            return (
                f"Túneles OMP del dispositivo {device_id}:\n\n"
                f"Total de peers: {len(tunnel_info)}\n\n"
                f"Detalle:\n{tunnel_info}"
            )
        
        return f"No se pudo obtener información de túneles OMP para {device_id}"
        
    except Exception as e:
        return f"Error al obtener túneles OMP: {str(e)}"


@mcp.tool()
def ver_control_connections(device_id: str) -> str:
    """
    Consulta las conexiones al control plane (vSmart controllers)
    
    Args:
        device_id: System IP del dispositivo (ejemplo: 10.80.10.207)
    
    Returns:
        Estado de conexiones con vSmart controllers
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/control/connections?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            connections = result['data']
            control_info = []
            
            for conn in connections:
                control_info.append({
                    'peer': conn.get('peer-address', 'N/A'),
                    'peer_type': conn.get('peer-type', 'N/A'),
                    'state': conn.get('state', 'N/A'),
                    'protocol': conn.get('protocol', 'N/A'),
                    'local_color': conn.get('local-color', 'N/A'),
                    'remote_color': conn.get('remote-color', 'N/A'),
                    'uptime': conn.get('uptime', 'N/A'),
                    'domain_id': conn.get('domain-id', 'N/A'),
                    'site_id': conn.get('site-id', 'N/A')
                })
            
            if not control_info:
                return f"No se encontraron conexiones de control para {device_id}"
            
            # Contar estados
            up_count = sum(1 for c in control_info if c['state'] == 'up')
            
            return (
                f"Conexiones de control del dispositivo {device_id}:\n\n"
                f"Total: {len(control_info)} | Activas: {up_count}\n\n"
                f"Detalle:\n{control_info}"
            )
        
        return f"No se pudo obtener información de control connections para {device_id}"
        
    except Exception as e:
        return f"Error al obtener control connections: {str(e)}"


@mcp.tool()
def ver_resumen_red() -> str:
    """
    Muestra un dashboard general del estado de la red SD-WAN
    
    Returns:
        Resumen con total de dispositivos, estados, alarmas y salud general
    """
    try:
        session = get_vmanage_session()
        
        # Obtener dispositivos
        devices_result = session.get("/dataservice/device")
        total_devices = 0
        reachable = 0
        unreachable = 0
        device_types = {}
        
        if 'data' in devices_result:
            devices = devices_result['data']
            total_devices = len(devices)
            
            for device in devices:
                status = device.get('reachability', 'unknown')
                device_type = device.get('device-type', 'unknown')
                
                if status == 'reachable':
                    reachable += 1
                else:
                    unreachable += 1
                
                device_types[device_type] = device_types.get(device_type, 0) + 1
        
        # Obtener alarmas críticas
        alarms_result = session.get("/dataservice/alarms")
        critical_alarms = 0
        major_alarms = 0
        
        if 'data' in alarms_result:
            for alarm in alarms_result['data']:
                severity = alarm.get('severity', '').lower()
                if severity == 'critical':
                    critical_alarms += 1
                elif severity == 'major':
                    major_alarms += 1
        
        # Calcular salud general
        health_percentage = (reachable / total_devices * 100) if total_devices > 0 else 0
        
        resumen = {
            'dispositivos': {
                'total': total_devices,
                'alcanzables': reachable,
                'no_alcanzables': unreachable,
                'por_tipo': device_types
            },
            'salud_red': {
                'porcentaje': f"{health_percentage:.2f}%",
                'estado': 'Saludable' if health_percentage >= 95 else 'Con problemas' if health_percentage >= 80 else 'Crítico'
            },
            'alarmas': {
                'criticas': critical_alarms,
                'mayores': major_alarms,
                'total_importantes': critical_alarms + major_alarms
            }
        }
        
        return (
            f"📊 RESUMEN DE RED SD-WAN\n\n"
            f"Dispositivos:\n"
            f"  Total: {total_devices}\n"
            f"  ✅ Alcanzables: {reachable}\n"
            f"  ❌ No alcanzables: {unreachable}\n\n"
            f"Salud General: {resumen['salud_red']['estado']} ({resumen['salud_red']['porcentaje']})\n\n"
            f"Alarmas:\n"
            f"  🔴 Críticas: {critical_alarms}\n"
            f"  🟠 Mayores: {major_alarms}\n\n"
            f"Tipos de dispositivos:\n{device_types}\n\n"
            f"Detalle completo:\n{resumen}"
        )
        
    except Exception as e:
        return f"Error al obtener resumen de red: {str(e)}"


# ============================================================================
# FASE 2: FUNCIONES DE ANÁLISIS - BÚSQUEDA Y DIAGNÓSTICO
# ============================================================================

@mcp.tool()
def ver_aplicaciones_top(device_id: str, top: int = 10) -> str:
    """
    Muestra las aplicaciones que más consumen ancho de banda en un dispositivo
    
    Args:
        device_id: System IP del dispositivo (ejemplo: 10.80.10.207)
        top: Número de aplicaciones a mostrar (default: 10)
    
    Returns:
        Top aplicaciones por consumo de bytes/paquetes
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/dpi/applications?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            apps = result['data']
            
            # Ordenar por bytes totales (rx + tx)
            apps_sorted = sorted(
                apps,
                key=lambda x: int(x.get('rx-bytes', 0)) + int(x.get('tx-bytes', 0)),
                reverse=True
            )[:top]
            
            app_stats = []
            for app in apps_sorted:
                rx_bytes = int(app.get('rx-bytes', 0))
                tx_bytes = int(app.get('tx-bytes', 0))
                total_bytes = rx_bytes + tx_bytes
                
                app_stats.append({
                    'aplicacion': app.get('application', 'N/A'),
                    'familia': app.get('family', 'N/A'),
                    'total_mb': f"{total_bytes / (1024*1024):.2f}",
                    'rx_mb': f"{rx_bytes / (1024*1024):.2f}",
                    'tx_mb': f"{tx_bytes / (1024*1024):.2f}",
                    'paquetes': int(app.get('rx-packets', 0)) + int(app.get('tx-packets', 0))
                })
            
            if not app_stats:
                return f"No se encontraron estadísticas de aplicaciones para {device_id}"
            
            return (
                f"Top {top} aplicaciones del dispositivo {device_id}:\n\n"
                f"Detalle:\n{app_stats}"
            )
        
        return f"No se pudo obtener estadísticas de aplicaciones para {device_id}"
        
    except Exception as e:
        return f"Error al obtener aplicaciones top: {str(e)}"


@mcp.tool()
def ver_aplicaciones_top_red_global(
    top: int = 20,
    limite_flujos: int = 1000
) -> str:
    """
    Muestra las aplicaciones que más consumen ancho de banda en TODA LA RED SD-WAN.
    Similar al dashboard "Top Applications" de vManage.
    
    Usa el endpoint /dataservice/statistics/dpi que proporciona estadísticas DPI 
    agregadas de toda la red con información de IPs origen→destino.
    
    Args:
        top: Número de aplicaciones a mostrar en el ranking (default: 20)
        limite_flujos: Número máximo de flujos DPI a procesar (default: 1000)
    
    Returns:
        Top aplicaciones de toda la red con estadísticas agregadas de uso
        
    Ejemplo:
        ver_aplicaciones_top_red_global(top=15, limite_flujos=500)
    """
    print(f"\n🔧 [{datetime.now().strftime('%H:%M:%S')}] HERRAMIENTA INVOCADA: ver_aplicaciones_top_red_global", file=sys.stderr)
    print(f"\n🔧 [{datetime.now().strftime('%H:%M:%S')}] HERRAMIENTA INVOCADA: ver_aplicaciones_top_red_global", file=sys.stderr)
    try:
        session = get_vmanage_session()
        
        # Usar el endpoint de estadísticas DPI agregadas
        resultado_texto = f"📊 TOP {top} APPLICATIONS - TODA LA RED SD-WAN\n"
        resultado_texto += f"{'='*80}\n\n"
        resultado_texto += f"🔍 Consultando estadísticas DPI de toda la red...\n"
        
        # Endpoint de estadísticas DPI (proporciona datos agregados de todos los dispositivos)
        endpoint = "/dataservice/statistics/dpi"
        result = session.get(endpoint, timeout=60)
        
        if 'data' not in result:
            return (
                f"{resultado_texto}\n"
                f"❌ El endpoint no devolvió datos\n"
                f"Verifica que DPI esté habilitado en los dispositivos"
            )
        
        dpi_flows = result['data']
        
        if not dpi_flows:
            return (
                f"{resultado_texto}\n"
                f"ℹ️  No hay flujos DPI disponibles en este momento\n\n"
                f"Verifica:\n"
                f"  • DPI está habilitado en los routers cEdge\n"
                f"  • Hay tráfico activo en la red\n"
                f"  • Los dispositivos están reportando estadísticas a vManage"
            )
        
        # Limitar flujos si hay muchos (para performance)
        if len(dpi_flows) > limite_flujos:
            dpi_flows = dpi_flows[:limite_flujos]
            resultado_texto += f"⚠️  Procesando primeros {limite_flujos} flujos (de {len(result['data'])} totales)\n"
        
        resultado_texto += f"✅ {len(dpi_flows)} flujos DPI encontrados\n\n"
        
        # Agregar datos por aplicación
        apps_agregadas = {}
        dispositivos_unicos = set()
        vpns_detectadas = set()
        ips_origen = set()
        ips_destino = set()
        
        for flow in dpi_flows:
            app_name = flow.get('application', 'unknown')
            familia = flow.get('family', 'N/A')
            hostname = flow.get('host_name', 'Unknown')
            vpn_id = str(flow.get('vpn_id', 'N/A'))
            source_ip = flow.get('source_ip', '')
            dest_ip = flow.get('dest_ip', '')
            
            # Recolectar estadísticas globales
            dispositivos_unicos.add(hostname)
            if vpn_id != 'N/A':
                vpns_detectadas.add(vpn_id)
            if source_ip:
                ips_origen.add(source_ip)
            if dest_ip:
                ips_destino.add(dest_ip)
            
            # Agregar por aplicación
            if app_name not in apps_agregadas:
                apps_agregadas[app_name] = {
                    'aplicacion': app_name,
                    'familia': familia,
                    'total_bytes': 0,
                    'total_packets': 0,
                    'flujos': 0,
                    'dispositivos': set(),
                    'vpns': set(),
                    'ips_origen_top': {},
                    'ips_destino_top': {}
                }
            
            # Sumar estadísticas
            octets = int(flow.get('octets', 0))
            packets = int(flow.get('packets', 0))
            
            apps_agregadas[app_name]['total_bytes'] += octets
            apps_agregadas[app_name]['total_packets'] += packets
            apps_agregadas[app_name]['flujos'] += 1
            apps_agregadas[app_name]['dispositivos'].add(hostname)
            
            if vpn_id != 'N/A':
                apps_agregadas[app_name]['vpns'].add(vpn_id)
            
            # Trackear top IPs origen y destino por aplicación
            if source_ip:
                apps_agregadas[app_name]['ips_origen_top'][source_ip] = \
                    apps_agregadas[app_name]['ips_origen_top'].get(source_ip, 0) + octets
            if dest_ip:
                apps_agregadas[app_name]['ips_destino_top'][dest_ip] = \
                    apps_agregadas[app_name]['ips_destino_top'].get(dest_ip, 0) + octets
        
        # Ordenar aplicaciones por bytes
        apps_list = list(apps_agregadas.values())
        apps_list.sort(key=lambda x: x['total_bytes'], reverse=True)
        
        top_apps = apps_list[:top]
        total_bytes_red = sum(app['total_bytes'] for app in apps_list)
        
        # Formatear total de red
        if total_bytes_red > 1024**4:  # TB
            total_str = f"{total_bytes_red / (1024**4):.2f} TB"
        elif total_bytes_red > 1024**3:  # GB
            total_str = f"{total_bytes_red / (1024**3):.2f} GB"
        elif total_bytes_red > 1024**2:  # MB
            total_str = f"{total_bytes_red / (1024**2):.2f} MB"
        else:
            total_str = f"{total_bytes_red / 1024:.2f} KB"
        
        resultado_texto += f"📈 TRÁFICO TOTAL ANALIZADO: {total_str}\n"
        resultado_texto += f"🖥️  DISPOSITIVOS: {len(dispositivos_unicos)}\n"
        resultado_texto += f"🌐 VPNs: {', '.join(sorted(vpns_detectadas))}\n"
        resultado_texto += f"📍 IPs Origen únicas: {len(ips_origen)}\n"
        resultado_texto += f"📍 IPs Destino únicas: {len(ips_destino)}\n"
        resultado_texto += f"🔢 Aplicaciones únicas: {len(apps_list)}\n\n"
        resultado_texto += f"{'='*80}\n\n"
        
        # Tabla de aplicaciones
        resultado_texto += f"{'#':<4} {'APLICACIÓN':<25} {'TRÁFICO':<15} {'%':<8} {'FLUJOS':<8} {'DISPOS':<7} {'VPNs':<8}\n"
        resultado_texto += f"{'-'*4} {'-'*25} {'-'*15} {'-'*8} {'-'*8} {'-'*7} {'-'*8}\n"
        
        for i, app in enumerate(top_apps, 1):
            # Calcular porcentaje
            porcentaje = (app['total_bytes'] / total_bytes_red * 100) if total_bytes_red > 0 else 0
            
            # Formatear bytes
            bytes_val = app['total_bytes']
            if bytes_val > 1024**4:  # TB
                bytes_str = f"{bytes_val / (1024**4):.2f} TB"
            elif bytes_val > 1024**3:  # GB
                bytes_str = f"{bytes_val / (1024**3):.2f} GB"
            elif bytes_val > 1024**2:  # MB
                bytes_str = f"{bytes_val / (1024**2):.2f} MB"
            else:
                bytes_str = f"{bytes_val / 1024:.2f} KB"
            
            # Formatear flujos
            flujos_val = app['flujos']
            if flujos_val > 1000:
                flujos_str = f"{flujos_val / 1000:.1f}K"
            else:
                flujos_str = str(flujos_val)
            
            # Número de dispositivos y VPNs
            num_devices = len(app['dispositivos'])
            num_vpns = len(app['vpns'])
            vpns_str = ','.join(sorted(list(app['vpns']))[:3])
            
            # Nombre de aplicación (truncar si es muy largo)
            app_name = app['aplicacion'][:23]
            
            resultado_texto += f"{i:<4} {app_name:<25} {bytes_str:<15} {porcentaje:>6.2f}% {flujos_str:<8} {num_devices:<7} {vpns_str:<8}\n"
        
        resultado_texto += f"\n{'='*80}\n"
        
        # Mostrar top IPs destino para las primeras aplicaciones
        resultado_texto += f"\n📌 TOP IPs DESTINO POR APLICACIÓN:\n\n"
        for i, app in enumerate(top_apps[:top], 1):
            if not app['ips_destino_top']:
                continue
            resultado_texto += f"{i}. {app['aplicacion']}:\n"
            
            # Top 5 IPs destino
            top_dest_ips = sorted(app['ips_destino_top'].items(), key=lambda x: x[1], reverse=True)[:5]
            for ip, bytes_val in top_dest_ips:
                if bytes_val > 1024**3:
                    bytes_str = f"{bytes_val / (1024**3):.2f} GB"
                elif bytes_val > 1024**2:
                    bytes_str = f"{bytes_val / (1024**2):.1f} MB"
                else:
                    bytes_str = f"{bytes_val / 1024:.1f} KB"
                resultado_texto += f"   • {ip:15} - {bytes_str}\n"
            resultado_texto += "\n"
        
        # Resumen adicional
        if len(apps_list) > top:
            otras_apps = len(apps_list) - top
            otras_bytes = sum(app['total_bytes'] for app in apps_list[top:])
            otras_porcentaje = (otras_bytes / total_bytes_red * 100) if total_bytes_red > 0 else 0
            
            if otras_bytes > 1024**3:  # GB
                otras_str = f"{otras_bytes / (1024**3):.2f} GB"
            elif otras_bytes > 1024**2:  # MB
                otras_str = f"{otras_bytes / (1024**2):.2f} MB"
            else:
                otras_str = f"{otras_bytes / 1024:.2f} KB"
            
            resultado_texto += f"\n💡 Otras {otras_apps} aplicaciones: {otras_str} ({otras_porcentaje:.2f}%)\n"
        
        resultado_texto += f"\n🔧 HERRAMIENTAS RELACIONADAS:\n"
        resultado_texto += f"  • ver_aplicaciones_top(device_id, top=10) - Apps de un dispositivo específico\n"
        resultado_texto += f"  • obtener_ips_destino_aplicacion(aplicacion) - IPs destino detalladas de una app\n"
        resultado_texto += f"  • ver_aplicaciones_agregadas_avanzado(...) - Análisis con filtros avanzados\n"
        
        return resultado_texto
        
    except Exception as e:
        return f"❌ Error al obtener aplicaciones top de la red: {str(e)}"


@mcp.tool()
def ver_aplicaciones_agregadas_avanzado(
    horas: int = 1,
    dispositivos: str = "",
    familias: str = "",
    top_familias: int = 10,
    intervalo_minutos: int = 10
) -> str:
    """
    Análisis avanzado de aplicaciones DPI con agregación temporal y filtros personalizados.
    Usa el endpoint POST /dataservice/statistics/dpi/aggregation para consultas avanzadas.
    
    Permite filtrar por tiempo, dispositivos específicos y familias de aplicaciones,
    con histogramas temporales para ver evolución del tráfico.
    
    Args:
        horas: Número de horas hacia atrás para el análisis (default: 1, máximo recomendado: 24)
        dispositivos: Lista de System IPs o hostnames separados por coma (ej: "10.95.0.3,10.95.1.3")
                     Si está vacío, consulta todos los dispositivos
        familias: Lista de familias de aplicaciones separadas por coma 
                 (ej: "web,network-service,webmail,video,streaming,social-networking")
                 Si está vacío, consulta todas las familias
        top_familias: Número de familias top a mostrar (default: 10)
        intervalo_minutos: Intervalo en minutos para el histograma temporal (default: 10)
    
    Returns:
        Análisis agregado de tráfico por familia con evolución temporal
        
    Ejemplo:
        ver_aplicaciones_agregadas_avanzado(horas=6, familias="web,video,social-networking", top_familias=5)
        ver_aplicaciones_agregadas_avanzado(horas=1, dispositivos="10.95.0.3", intervalo_minutos=5)
    """
    print(f"\n🔧 [{datetime.now().strftime('%H:%M:%S')}] HERRAMIENTA INVOCADA: ver_aplicaciones_agregadas_avanzado", file=sys.stderr)
    try:
        session = get_vmanage_session()
        
        resultado_texto = f"📊 ANÁLISIS AVANZADO DE APLICACIONES DPI\n"
        resultado_texto += f"{'='*80}\n\n"
        
        # Construir query
        query_rules = [
            {
                "value": [str(horas)],
                "field": "entry_time",
                "type": "date",
                "operator": "last_n_hours"
            }
        ]
        
        # Agregar filtro de dispositivos si se especifica
        if dispositivos:
            device_list = [d.strip() for d in dispositivos.split(',')]
            
            # Resolver nombres de dispositivo a System IPs si es necesario
            devices_result = session.get("/dataservice/device")
            if 'data' in devices_result:
                resolved_devices = []
                for dev_input in device_list:
                    # Buscar por hostname o system-ip
                    for device in devices_result['data']:
                        if (dev_input in device.get('host-name', '') or 
                            dev_input == device.get('system-ip', '') or
                            dev_input == device.get('uuid', '')):
                            resolved_devices.append(device.get('system-ip', ''))
                            break
                
                if resolved_devices:
                    query_rules.append({
                        "value": resolved_devices,
                        "field": "vdevice_name",
                        "type": "string",
                        "operator": "in"
                    })
                    resultado_texto += f"🎯 Dispositivos filtrados: {', '.join(resolved_devices)}\n"
        
        # Agregar filtro de familias si se especifica
        if familias:
            family_list = [f.strip() for f in familias.split(',')]
            query_rules.append({
                "value": family_list,
                "field": "family",
                "type": "string",
                "operator": "in"
            })
            resultado_texto += f"📁 Familias filtradas: {', '.join(family_list)}\n"
        
        resultado_texto += f"⏰ Período: Últimas {horas} hora(s)\n"
        resultado_texto += f"📊 Intervalo: {intervalo_minutos} minutos\n\n"
        
        # Construir payload POST
        payload = {
            "query": {
                "condition": "AND",
                "rules": query_rules
            },
            "aggregation": {
                "field": [
                    {
                        "property": "family",
                        "sequence": 1,
                        "size": top_familias
                    }
                ],
                "metrics": [
                    {
                        "property": "octets",
                        "type": "sum"
                    }
                ],
                "histogram": {
                    "property": "entry_time",
                    "type": "minute",
                    "interval": intervalo_minutos,
                    "order": "asc"
                }
            }
        }
        
        # Realizar petición POST
        endpoint = "/dataservice/statistics/dpi/aggregation"
        result = session.post(endpoint, payload, timeout=60)
        
        if 'data' not in result or not result['data']:
            return (
                f"{resultado_texto}\n"
                f"ℹ️  No hay datos disponibles para los filtros especificados\n\n"
                f"Verifica:\n"
                f"  • Los dispositivos tienen DPI habilitado\n"
                f"  • Hay tráfico en el período seleccionado\n"
                f"  • Los nombres de familias son correctos"
            )
        
        data_points = result['data']
        entry_time_list = result.get('entryTimeList', [])
        
        resultado_texto += f"✅ {len(data_points)} puntos de datos recibidos\n"
        resultado_texto += f"🕐 {len(entry_time_list)} intervalos temporales\n\n"
        resultado_texto += f"{'='*80}\n\n"
        
        # Agregar por familia
        familias_agregadas = {}
        
        for point in data_points:
            familia = point.get('family', 'unknown')
            octets = int(point.get('octets', 0))
            count = int(point.get('count', 0))
            entry_time = point.get('entry_time', 0)
            
            if familia not in familias_agregadas:
                familias_agregadas[familia] = {
                    'familia': familia,
                    'total_bytes': 0,
                    'total_count': 0,
                    'timeline': {}
                }
            
            familias_agregadas[familia]['total_bytes'] += octets
            familias_agregadas[familia]['total_count'] += count
            familias_agregadas[familia]['timeline'][entry_time] = octets
        
        # Ordenar familias por bytes totales
        familias_sorted = sorted(familias_agregadas.values(), key=lambda x: x['total_bytes'], reverse=True)
        
        total_bytes = sum(f['total_bytes'] for f in familias_sorted)
        
        # Formatear total
        if total_bytes > 1024**4:  # TB
            total_str = f"{total_bytes / (1024**4):.2f} TB"
        elif total_bytes > 1024**3:  # GB
            total_str = f"{total_bytes / (1024**3):.2f} GB"
        elif total_bytes > 1024**2:  # MB
            total_str = f"{total_bytes / (1024**2):.2f} MB"
        else:
            total_str = f"{total_bytes / 1024:.2f} KB"
        
        resultado_texto += f"📈 TRÁFICO TOTAL: {total_str}\n\n"
        
        # Tabla de familias
        resultado_texto += f"{'#':<4} {'FAMILIA':<30} {'TRÁFICO':<15} {'%':<8} {'FLUJOS':<10}\n"
        resultado_texto += f"{'-'*4} {'-'*30} {'-'*15} {'-'*8} {'-'*10}\n"
        
        for i, fam in enumerate(familias_sorted[:top_familias], 1):
            # Calcular porcentaje
            porcentaje = (fam['total_bytes'] / total_bytes * 100) if total_bytes > 0 else 0
            
            # Formatear bytes
            bytes_val = fam['total_bytes']
            if bytes_val > 1024**4:  # TB
                bytes_str = f"{bytes_val / (1024**4):.2f} TB"
            elif bytes_val > 1024**3:  # GB
                bytes_str = f"{bytes_val / (1024**3):.2f} GB"
            elif bytes_val > 1024**2:  # MB
                bytes_str = f"{bytes_val / (1024**2):.2f} MB"
            else:
                bytes_str = f"{bytes_val / 1024:.2f} KB"
            
            # Formatear conteo
            count_val = fam['total_count']
            if count_val > 1000:
                count_str = f"{count_val / 1000:.1f}K"
            else:
                count_str = str(count_val)
            
            familia_name = fam['familia'][:28]
            
            resultado_texto += f"{i:<4} {familia_name:<30} {bytes_str:<15} {porcentaje:>6.2f}% {count_str:<10}\n"
        
        resultado_texto += f"\n{'='*80}\n"
        
        # Mostrar evolución temporal de top 3 familias
        if entry_time_list and len(familias_sorted) > 0:
            resultado_texto += f"\n📈 EVOLUCIÓN TEMPORAL (Top 3 Familias):\n\n"
            
            # Convertir timestamps a formato legible
            time_labels = []
            for ts in entry_time_list[:10]:  # Mostrar primeros 10 intervalos
                dt = datetime.fromtimestamp(ts / 1000)
                time_labels.append(dt.strftime('%H:%M'))
            
            resultado_texto += f"{'Familia':<25} | {' | '.join([f'{t:>8}' for t in time_labels])}\n"
            resultado_texto += f"{'-'*25}-+-{'-+-'.join(['-'*8 for _ in time_labels])}\n"
            
            for fam in familias_sorted[:3]:
                familia_name = fam['familia'][:23]
                timeline_values = []
                
                for ts in entry_time_list[:10]:
                    bytes_val = fam['timeline'].get(ts, 0)
                    if bytes_val > 1024**2:  # MB
                        val_str = f"{bytes_val / (1024**2):.1f}MB"
                    elif bytes_val > 1024:  # KB
                        val_str = f"{bytes_val / 1024:.1f}KB"
                    else:
                        val_str = f"{bytes_val}B" if bytes_val > 0 else "-"
                    timeline_values.append(f"{val_str:>8}")
                
                resultado_texto += f"{familia_name:<25} | {' | '.join(timeline_values)}\n"
            
            resultado_texto += f"\n"
        
        resultado_texto += f"💡 FAMILIAS COMUNES:\n"
        resultado_texto += f"  • web - Navegación HTTP/HTTPS\n"
        resultado_texto += f"  • network-service - DNS, DHCP, NTP\n"
        resultado_texto += f"  • video - YouTube, Netflix, streaming\n"
        resultado_texto += f"  • social-networking - Facebook, Twitter, Instagram\n"
        resultado_texto += f"  • file-sharing - Transferencias de archivos\n"
        resultado_texto += f"  • encrypted - Tráfico cifrado sin identificar\n"
        
        return resultado_texto
        
    except Exception as e:
        return f"❌ Error en análisis agregado: {str(e)}"


@mcp.tool()
def buscar_dispositivo(criterio: str) -> str:
    """
    Busca dispositivos por nombre, IP, modelo, site-id o cualquier criterio
    
    Args:
        criterio: Texto a buscar (nombre, IP, modelo, etc.)
    
    Returns:
        Lista de dispositivos que coinciden con el criterio
    """
    try:
        session = get_vmanage_session()
        result = session.get("/dataservice/device")
        
        if 'data' in result:
            devices = result['data']
            criterio_lower = criterio.lower()
            
            # Buscar en múltiples campos
            matches = []
            for device in devices:
                if (criterio_lower in device.get('host-name', '').lower() or
                    criterio_lower in device.get('system-ip', '') or
                    criterio_lower in device.get('device-model', '').lower() or
                    criterio_lower in str(device.get('site-id', '')) or
                    criterio_lower in device.get('device-type', '').lower()):
                    
                    matches.append({
                        'hostname': device.get('host-name', 'N/A'),
                        'system_ip': device.get('system-ip', 'N/A'),
                        'device_type': device.get('device-type', 'N/A'),
                        'device_model': device.get('device-model', 'N/A'),
                        'site_id': device.get('site-id', 'N/A'),
                        'status': device.get('reachability', 'N/A'),
                        'version': device.get('version', 'N/A')
                    })
            
            if not matches:
                return f"No se encontraron dispositivos que coincidan con '{criterio}'"
            
            return (
                f"Dispositivos encontrados con criterio '{criterio}':\n\n"
                f"Total: {len(matches)}\n\n"
                f"Resultados:\n{matches}"
            )
        
        return "No se pudieron obtener los dispositivos"
        
    except Exception as e:
        return f"Error al buscar dispositivo: {str(e)}"


@mcp.tool()
def ver_dispositivos_por_sitio(site_id: str) -> str:
    """
    Lista todos los dispositivos de un sitio específico
    
    Args:
        site_id: ID del sitio (ejemplo: 323, 367, etc.)
    
    Returns:
        Lista de dispositivos en el sitio especificado
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device?site-id={site_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            devices = result['data']
            
            site_devices = []
            reachable_count = 0
            
            for device in devices:
                status = device.get('reachability', 'N/A')
                if status == 'reachable':
                    reachable_count += 1
                
                site_devices.append({
                    'hostname': device.get('host-name', 'N/A'),
                    'system_ip': device.get('system-ip', 'N/A'),
                    'device_type': device.get('device-type', 'N/A'),
                    'device_model': device.get('device-model', 'N/A'),
                    'status': status,
                    'uptime': device.get('uptime-date', 'N/A'),
                    'version': device.get('version', 'N/A')
                })
            
            if not site_devices:
                return f"No se encontraron dispositivos en el sitio {site_id}"
            
            return (
                f"Dispositivos del sitio {site_id}:\n\n"
                f"Total: {len(site_devices)} | Alcanzables: {reachable_count}\n\n"
                f"Detalle:\n{site_devices}"
            )
        
        return f"No se pudieron obtener dispositivos del sitio {site_id}"
        
    except Exception as e:
        return f"Error al obtener dispositivos por sitio: {str(e)}"


@mcp.tool()
def ver_eventos_seguridad(horas: int = 24) -> str:
    """
    Lista eventos de seguridad recientes (IPS, firewall, intrusiones)
    
    Args:
        horas: Número de horas hacia atrás (default: 24)
    
    Returns:
        Eventos de seguridad del período especificado
    """
    try:
        session = get_vmanage_session()
        
        # Calcular timestamp
        from_time = int((datetime.now() - timedelta(hours=horas)).timestamp() * 1000)
        
        endpoint = f"/dataservice/event/security?from={from_time}"
        result = session.get(endpoint)
        
        if 'data' in result:
            events = result['data']
            
            security_events = []
            by_severity = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
            by_type = {}
            
            for event in events:
                severity = event.get('severity', 'unknown').lower()
                event_type = event.get('event-type', 'unknown')
                
                by_severity[severity] = by_severity.get(severity, 0) + 1
                by_type[event_type] = by_type.get(event_type, 0) + 1
                
                entry_time = event.get('entry-time', 0)
                security_events.append({
                    'time': datetime.fromtimestamp(entry_time / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'severity': event.get('severity', 'N/A'),
                    'type': event_type,
                    'message': event.get('message', 'N/A'),
                    'device': event.get('system-ip', 'N/A'),
                    'hostname': event.get('host-name', 'N/A')
                })
            
            if not security_events:
                return f"No hay eventos de seguridad en las últimas {horas} horas"
            
            return (
                f"Eventos de seguridad (últimas {horas} horas):\n\n"
                f"Total: {len(security_events)}\n\n"
                f"Por severidad: {by_severity}\n"
                f"Por tipo: {by_type}\n\n"
                f"Eventos recientes:\n{security_events[:20]}"
            )
        
        return f"No se pudieron obtener eventos de seguridad"
        
    except Exception as e:
        return f"Error al obtener eventos de seguridad: {str(e)}"


@mcp.tool()
def obtener_ips_destino_aplicacion(
    aplicacion: str,
    top_ips: int = 20
) -> str:
    """
    Obtiene las IPs destino más comunes para una aplicación específica.
    
    Busca en todos los flujos DPI de la red y filtra por la aplicación solicitada,
    mostrando las IPs destino con más tráfico, puertos utilizados, consumo total,
    los sitios/dispositivos involucrados y las IPs origen que generan ese tráfico.
    
    Args:
        aplicacion: Nombre de la aplicación (ej: "adobe-services", "microsoft-teams", "ssl", "torrent", "tor")
        top_ips: Número máximo de IPs destino a mostrar (default: 20)
    
    Returns:
        Lista de IPs destino con estadísticas detalladas de tráfico, puertos y consumo
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Buscando IPs destino de '{aplicacion}'...", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener flujos DPI de toda la red
        result = session.get("/dataservice/statistics/dpi", timeout=60)
        
        if 'data' not in result or not result['data']:
            return f"❌ No hay datos DPI disponibles en este momento"
        
        dpi_flows = result['data']
        total_flows = len(dpi_flows)
        
        # Filtrar por aplicación (búsqueda flexible)
        app_lower = aplicacion.lower()
        flujos_app = [f for f in dpi_flows if app_lower in f.get('application', '').lower()]
        
        if not flujos_app:
            # Buscar también en familia
            flujos_app = [f for f in dpi_flows if app_lower in f.get('family', '').lower()]
        
        if not flujos_app:
            # Mostrar aplicaciones similares
            todas_apps = set(f.get('application', '') for f in dpi_flows)
            similares = [a for a in todas_apps if any(p in a.lower() for p in app_lower.split('-'))]
            
            resultado = f"❌ No se encontraron flujos para '{aplicacion}'\n\n"
            if similares:
                resultado += f"📋 Aplicaciones similares encontradas:\n"
                for app in sorted(similares)[:15]:
                    resultado += f"   • {app}\n"
            else:
                resultado += f"📋 Aplicaciones disponibles (primeras 30):\n"
                for app in sorted(list(todas_apps))[:30]:
                    resultado += f"   • {app}\n"
            return resultado
        
        # Mapeo de protocolo IP
        proto_map = {'6': 'TCP', '17': 'UDP', '1': 'ICMP', '47': 'GRE', '50': 'ESP'}
        
        # Agregar datos
        ips_destino = {}
        ips_origen = {}
        puertos_destino = {}
        puertos_origen = {}
        dispositivos = set()
        sitios = set()
        total_bytes_app = 0
        total_packets_app = 0
        protocolos = {}
        app_real_name = flujos_app[0].get('application', aplicacion)
        familia = flujos_app[0].get('family', 'N/A')
        
        # Lista de conexiones detalladas (origen:puerto → destino:puerto)
        conexiones = []
        
        for flow in flujos_app:
            dest_ip = flow.get('dest_ip', '')
            source_ip = flow.get('source_ip', '')
            dest_port = str(flow.get('dest_port', ''))
            source_port = str(flow.get('source_port', ''))
            ip_proto = str(flow.get('ip_proto', ''))
            octets = int(flow.get('octets', 0))
            packets = int(flow.get('packets', 0))
            hostname = flow.get('host_name', 'Unknown')
            site_id = str(flow.get('site_id', 'N/A'))
            vpn_id = str(flow.get('vpn_id', 'N/A'))
            
            total_bytes_app += octets
            total_packets_app += packets
            dispositivos.add(hostname)
            sitios.add(site_id)
            
            # Contar protocolos
            proto_name = proto_map.get(ip_proto, ip_proto)
            protocolos[proto_name] = protocolos.get(proto_name, 0) + 1
            
            # Registrar conexión detallada
            conexiones.append({
                'src_ip': source_ip, 'src_port': source_port,
                'dst_ip': dest_ip, 'dst_port': dest_port,
                'proto': proto_name, 'bytes': octets, 'packets': packets,
                'hostname': hostname, 'site_id': site_id, 'vpn_id': vpn_id
            })
            
            # Agregar puertos destino
            if dest_port:
                if dest_port not in puertos_destino:
                    puertos_destino[dest_port] = {'bytes': 0, 'flujos': 0, 'proto': proto_name}
                puertos_destino[dest_port]['bytes'] += octets
                puertos_destino[dest_port]['flujos'] += 1
            
            # Agregar puertos origen
            if source_port:
                if source_port not in puertos_origen:
                    puertos_origen[source_port] = {'bytes': 0, 'flujos': 0, 'proto': proto_name}
                puertos_origen[source_port]['bytes'] += octets
                puertos_origen[source_port]['flujos'] += 1
            
            # Agregar IPs destino
            if dest_ip:
                if dest_ip not in ips_destino:
                    ips_destino[dest_ip] = {
                        'bytes': 0, 'packets': 0, 'flujos': 0,
                        'dispositivos': set(), 'sitios': set(),
                        'vpns': set(), 'ips_origen': set(),
                        'puertos': set()
                    }
                ips_destino[dest_ip]['bytes'] += octets
                ips_destino[dest_ip]['packets'] += packets
                ips_destino[dest_ip]['flujos'] += 1
                ips_destino[dest_ip]['dispositivos'].add(hostname)
                ips_destino[dest_ip]['sitios'].add(site_id)
                ips_destino[dest_ip]['vpns'].add(vpn_id)
                if dest_port:
                    ips_destino[dest_ip]['puertos'].add(dest_port)
                if source_ip:
                    ips_destino[dest_ip]['ips_origen'].add(source_ip)
            
            # Agregar IPs origen
            if source_ip:
                if source_ip not in ips_origen:
                    ips_origen[source_ip] = {'bytes': 0, 'flujos': 0, 'puertos': set()}
                ips_origen[source_ip]['bytes'] += octets
                ips_origen[source_ip]['flujos'] += 1
                if source_port:
                    ips_origen[source_ip]['puertos'].add(source_port)
        
        # Formatear bytes
        def fmt_bytes(b):
            if b > 1024**3: return f"{b / (1024**3):.2f} GB"
            if b > 1024**2: return f"{b / (1024**2):.2f} MB"
            if b > 1024: return f"{b / 1024:.1f} KB"
            return f"{b} B"
        
        # Construir resultado
        resultado = f"🎯 IPs DESTINO DE: {app_real_name}\n"
        resultado += f"{'='*100}\n\n"
        
        # === CONSUMO TOTAL ===
        resultado += f"📊 CONSUMO TOTAL:\n"
        resultado += f"   Aplicación:       {app_real_name}\n"
        resultado += f"   Familia:          {familia}\n"
        resultado += f"   Tráfico total:    {fmt_bytes(total_bytes_app)}\n"
        resultado += f"   Paquetes totales: {total_packets_app:,}\n"
        resultado += f"   Flujos activos:   {len(flujos_app)} (de {total_flows} totales en la red)\n"
        resultado += f"   Protocolos:       {', '.join(f'{k}({v})' for k, v in sorted(protocolos.items(), key=lambda x: x[1], reverse=True))}\n"
        resultado += f"   Sitios:           {len(sitios)} ({', '.join(sorted(sitios))})\n"
        resultado += f"   Dispositivos:     {len(dispositivos)} ({', '.join(sorted(dispositivos))})\n"
        resultado += f"   IPs destino:      {len(ips_destino)} únicas\n"
        resultado += f"   IPs origen:       {len(ips_origen)} únicas\n"
        resultado += f"   Puertos destino:  {len(puertos_destino)} únicos\n"
        resultado += f"   Puertos origen:   {len(puertos_origen)} únicos\n\n"
        
        # === PUERTOS DESTINO ===
        sorted_ports_dst = sorted(puertos_destino.items(), key=lambda x: x[1]['bytes'], reverse=True)
        resultado += f"{'='*100}\n"
        resultado += f"🔌 PUERTOS DESTINO UTILIZADOS ({len(sorted_ports_dst)}):\n\n"
        resultado += f"{'PUERTO':<10} {'PROTOCOLO':<10} {'TRÁFICO':<12} {'FLUJOS':<8} {'% TRÁFICO':<10}\n"
        resultado += f"{'-'*55}\n"
        
        for port, data in sorted_ports_dst[:15]:
            pct = (data['bytes'] / total_bytes_app * 100) if total_bytes_app > 0 else 0
            resultado += f"{port:<10} {data['proto']:<10} {fmt_bytes(data['bytes']):<12} {data['flujos']:<8} {pct:>6.1f}%\n"
        
        # === PUERTOS ORIGEN ===
        sorted_ports_src = sorted(puertos_origen.items(), key=lambda x: x[1]['bytes'], reverse=True)
        resultado += f"\n🔌 PUERTOS ORIGEN MÁS ACTIVOS (top 10 de {len(sorted_ports_src)}):\n\n"
        resultado += f"{'PUERTO':<10} {'PROTOCOLO':<10} {'TRÁFICO':<12} {'FLUJOS':<8}\n"
        resultado += f"{'-'*45}\n"
        
        for port, data in sorted_ports_src[:10]:
            resultado += f"{port:<10} {data['proto']:<10} {fmt_bytes(data['bytes']):<12} {data['flujos']:<8}\n"
        
        # === TOP IPs DESTINO ===
        sorted_dest = sorted(ips_destino.items(), key=lambda x: x[1]['bytes'], reverse=True)
        
        resultado += f"\n{'='*100}\n"
        resultado += f"📌 TOP {min(top_ips, len(sorted_dest))} IPs DESTINO:\n\n"
        resultado += f"{'#':<4} {'IP DESTINO':<18} {'TRÁFICO':<12} {'%':<7} {'PUERTOS':<20} {'FLUJOS':<8} {'ORÍGENES':<10}\n"
        resultado += f"{'-'*100}\n"
        
        for i, (ip, data) in enumerate(sorted_dest[:top_ips], 1):
            pct = (data['bytes'] / total_bytes_app * 100) if total_bytes_app > 0 else 0
            ports_str = ','.join(sorted(data['puertos'], key=lambda p: int(p) if p.isdigit() else 0)[:5])
            if len(data['puertos']) > 5:
                ports_str += f"(+{len(data['puertos'])-5})"
            num_orig = len(data['ips_origen'])
            
            resultado += f"{i:<4} {ip:<18} {fmt_bytes(data['bytes']):<12} {pct:>5.1f}% {ports_str:<20} {data['flujos']:<8} {num_orig:<10}\n"
        
        # === TOP IPs ORIGEN ===
        sorted_orig = sorted(ips_origen.items(), key=lambda x: x[1]['bytes'], reverse=True)
        
        resultado += f"\n{'='*100}\n"
        resultado += f"📍 TOP {min(10, len(sorted_orig))} IPs ORIGEN (quién consume {app_real_name}):\n\n"
        resultado += f"{'#':<4} {'IP ORIGEN':<18} {'TRÁFICO':<12} {'%':<7} {'PUERTOS':<20} {'FLUJOS':<8}\n"
        resultado += f"{'-'*75}\n"
        
        for i, (ip, data) in enumerate(sorted_orig[:10], 1):
            pct = (data['bytes'] / total_bytes_app * 100) if total_bytes_app > 0 else 0
            ports_str = ','.join(sorted(data['puertos'], key=lambda p: int(p) if p.isdigit() else 0)[:5])
            if len(data['puertos']) > 5:
                ports_str += f"(+{len(data['puertos'])-5})"
            resultado += f"{i:<4} {ip:<18} {fmt_bytes(data['bytes']):<12} {pct:>5.1f}% {ports_str:<20} {data['flujos']:<8}\n"
        
        # === DETALLE DE CONEXIONES ===
        conexiones.sort(key=lambda x: x['bytes'], reverse=True)
        resultado += f"\n{'='*100}\n"
        resultado += f"🔗 DETALLE DE CONEXIONES (top {min(15, len(conexiones))}):\n\n"
        resultado += f"{'#':<4} {'ORIGEN':<24} {'DESTINO':<24} {'PROTO':<6} {'TRÁFICO':<12} {'DISPOSITIVO':<25}\n"
        resultado += f"{'-'*100}\n"
        
        for i, conn in enumerate(conexiones[:15], 1):
            src = f"{conn['src_ip']}:{conn['src_port']}"
            dst = f"{conn['dst_ip']}:{conn['dst_port']}"
            resultado += f"{i:<4} {src:<24} {dst:<24} {conn['proto']:<6} {fmt_bytes(conn['bytes']):<12} {conn['hostname']:<25}\n"
        
        if len(conexiones) > 15:
            resultado += f"\n   ... y {len(conexiones) - 15} conexiones más\n"
        
        resultado += f"\n{'='*100}\n"
        resultado += f"💡 Para más detalle usa:\n"
        resultado += f"   • ver_aplicaciones_top_red_global() - Ranking de todas las apps\n"
        resultado += f"   • ver_aplicaciones_agregadas_avanzado() - Análisis temporal\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener IPs destino: {str(e)}"


# ============================================================================
# FUNCIONES DE CISCO CATALYST CENTER (DNA Center)
# ============================================================================

@mcp.tool()
def catalyst_listar_dispositivos_red() -> str:
    """
    Lista todos los dispositivos de red gestionados por Catalyst Center (switches, routers, APs, etc.)
    
    Returns:
        Lista completa de dispositivos con información de estado, familia y versión de software
    """
    try:
        session = get_catalyst_session()
        endpoint = "/dna/intent/api/v1/network-device"
        result = session.get(endpoint, timeout=30)
        
        if 'response' in result:
            devices = result['response']
            
            # Formatear respuesta
            formatted_devices = []
            for device in devices:
                formatted_devices.append({
                    'hostname': device.get('hostname', 'N/A'),
                    'management_ip': device.get('managementIpAddress', 'N/A'),
                    'family': device.get('family', 'N/A'),
                    'type': device.get('type', 'N/A'),
                    'role': device.get('role', 'N/A'),
                    'software_version': device.get('softwareVersion', 'N/A'),
                    'reachability': device.get('reachabilityStatus', 'N/A'),
                    'series': device.get('series', 'N/A'),
                    'location': device.get('location', 'N/A'),
                    'up_time': device.get('upTime', 'N/A')
                })
            
            return f"🌐 DISPOSITIVOS CATALYST CENTER\n\nTotal: {len(formatted_devices)}\n\nDispositivos:\n{formatted_devices}"
        
        return "No se encontraron dispositivos"
        
    except ValueError as e:
        return f"Error de configuración: {str(e)}\n\nAsegúrate de configurar CATALYST_IP, CATALYST_USERNAME y CATALYST_PASSWORD en el archivo .env"
    except (ConnectionError, TimeoutError) as e:
        return f"Error de conexión: {str(e)}"
    except Exception as e:
        return f"Error inesperado: {str(e)}"


@mcp.tool()
def catalyst_salud_dispositivo(device_id: str) -> str:
    """
    Obtiene el estado de salud de un dispositivo específico en Catalyst Center.
    
    Args:
        device_id: UUID o IP del dispositivo
    
    Returns:
        Estado de salud detallado incluyendo score general, memoria, CPU y conectividad
    """
    try:
        session = get_catalyst_session()
        
        # Obtener health score
        endpoint_health = f"/dna/intent/api/v1/device-health"
        result_health = session.get(endpoint_health, timeout=30)
        
        # Buscar el dispositivo específico
        device_health = None
        if 'response' in result_health:
            for dev in result_health['response']:
                if dev.get('id') == device_id or dev.get('managementIpAddress') == device_id:
                    device_health = dev
                    break
        
        if not device_health:
            return f"⚠️  No se encontró el dispositivo {device_id}"
        
        # Formatear resultado
        resultado = f"💚 SALUD DEL DISPOSITIVO\n"
        resultado += f"{'='*70}\n\n"
        resultado += f"Nombre: {device_health.get('name', 'N/A')}\n"
        resultado += f"IP: {device_health.get('managementIpAddress', 'N/A')}\n"
        resultado += f"Health Score: {device_health.get('overallHealth', 0)}/10\n\n"
        
        resultado += f"📊 Métricas:\n"
        resultado += f"  CPU: {device_health.get('cpuScore', 'N/A')}/10\n"
        resultado += f"  Memoria: {device_health.get('memoryScore', 'N/A')}/10\n"
        resultado += f"  Interfaces: {device_health.get('interfaceScore', 'N/A')}/10\n"
        resultado += f"  Issues: {device_health.get('issueCount', 0)}\n"
        
        return resultado
        
    except Exception as e:
        return f"Error al obtener salud del dispositivo: {str(e)}"


@mcp.tool()
def catalyst_topologia_red(topology_type: str = "physical") -> str:
    """
    Obtiene la topología de la red desde Catalyst Center.
    
    Args:
        topology_type: Tipo de topología - "physical" o "layer2" o "layer3" (default: "physical")
    
    Returns:
        Información de topología con nodos y enlaces
    """
    try:
        session = get_catalyst_session()
        endpoint = f"/dna/intent/api/v1/topology/{topology_type}-topology"
        result = session.get(endpoint, timeout=30)
        
        if 'response' in result:
            topology = result['response']
            nodes = topology.get('nodes', [])
            links = topology.get('links', [])
            
            resultado = f"🗺️  TOPOLOGÍA DE RED ({topology_type.upper()})\n"
            resultado += f"{'='*70}\n\n"
            resultado += f"Total de nodos: {len(nodes)}\n"
            resultado += f"Total de enlaces: {len(links)}\n\n"
            
            if nodes:
                resultado += f"📍 Nodos principales:\n"
                for i, node in enumerate(nodes[:10], 1):
                    resultado += f"  {i}. {node.get('label', 'N/A')} ({node.get('nodeType', 'N/A')})\n"
                
                if len(nodes) > 10:
                    resultado += f"  ... y {len(nodes) - 10} nodos más\n"
            
            return resultado
        
        return "No se pudo obtener la topología"
        
    except Exception as e:
        return f"Error al obtener topología: {str(e)}"


@mcp.tool()
def catalyst_inventario_sitios() -> str:
    """
    Lista todos los sitios configurados en Catalyst Center con su jerarquía.
    
    Returns:
        Estructura jerárquica de sitios (áreas, edificios, pisos)
    """
    try:
        session = get_catalyst_session()
        endpoint = "/dna/intent/api/v1/site"
        result = session.get(endpoint, timeout=30)
        
        if 'response' in result:
            sites = result['response']
            
            resultado = f"🏢 INVENTARIO DE SITIOS\n"
            resultado += f"{'='*70}\n\n"
            resultado += f"Total de sitios: {len(sites)}\n\n"
            
            for site in sites:
                site_info = site.get('additionalInfo', [])
                site_type = 'N/A'
                for info in site_info:
                    if info.get('nameSpace') == 'Location':
                        attrs = info.get('attributes', {})
                        site_type = attrs.get('type', 'N/A')
                        break
                
                resultado += f"📍 {site.get('name', 'N/A')}\n"
                resultado += f"   Tipo: {site_type}\n"
                resultado += f"   ID: {site.get('id', 'N/A')}\n\n"
            
            return resultado
        
        return "No se encontraron sitios"
        
    except Exception as e:
        return f"Error al obtener sitios: {str(e)}"


@mcp.tool()
def catalyst_clientes_conectados(limit: int = 100) -> str:
    """
    Lista los clientes conectados actualmente a la red.
    
    Args:
        limit: Número máximo de clientes a mostrar (default: 100)
    
    Returns:
        Lista de clientes con información de conectividad y salud
    """
    try:
        session = get_catalyst_session()
        endpoint = f"/dna/intent/api/v1/client-health?timestamp="
        result = session.get(endpoint, timeout=30)
        
        if 'response' in result:
            clients_summary = result['response']
            
            resultado = f"👥 CLIENTES CONECTADOS\n"
            resultado += f"{'='*70}\n\n"
            
            for score_category in clients_summary:
                score_type = score_category.get('scoreCategory', {}).get('scoreCategory', 'N/A')
                client_count = score_category.get('scoreCategory', {}).get('clientCount', 0)
                
                resultado += f"Score {score_type}: {client_count} clientes\n"
            
            # Obtener detalle de clientes individuales
            endpoint_detail = f"/dna/intent/api/v1/client-detail?limit={limit}"
            result_detail = session.get(endpoint_detail, timeout=30)
            
            if 'response' in result_detail and result_detail['response']:
                clients = result_detail['response']
                resultado += f"\n\n📋 Detalle de clientes (top {min(len(clients), limit)}):\n\n"
                
                for i, client in enumerate(clients[:limit], 1):
                    resultado += f"{i}. {client.get('hostName', 'N/A')}\n"
                    resultado += f"   MAC: {client.get('hostMac', 'N/A')}\n"
                    resultado += f"   IP: {client.get('hostIpV4', 'N/A')}\n"
                    resultado += f"   Conectado a: {client.get('connectedDevice', [{}])[0].get('deviceName', 'N/A')}\n"
                    resultado += f"   SSID: {client.get('ssid', 'N/A')}\n"
                    resultado += f"   Health Score: {client.get('healthScore', [{}])[0].get('score', 'N/A')}\n\n"
            
            return resultado
        
        return "No se pudo obtener información de clientes"
        
    except Exception as e:
        return f"Error al obtener clientes: {str(e)}"


@mcp.tool()
def catalyst_issues_red(severity: str = "HIGH") -> str:
    """
    Lista los problemas detectados en la red por Catalyst Center.
    
    Args:
        severity: Nivel de severidad - "HIGH", "MEDIUM", "LOW" (default: "HIGH")
    
    Returns:
        Lista de issues con descripción y dispositivos afectados
    """
    try:
        session = get_catalyst_session()
        endpoint = f"/dna/intent/api/v1/issues?severity={severity}"
        result = session.get(endpoint, timeout=30)
        
        if 'response' in result:
            issues = result['response']
            
            resultado = f"⚠️  PROBLEMAS DE RED (Severidad: {severity})\n"
            resultado += f"{'='*70}\n\n"
            resultado += f"Total de issues: {len(issues)}\n\n"
            
            for i, issue in enumerate(issues[:20], 1):
                resultado += f"{i}. {issue.get('name', 'N/A')}\n"
                resultado += f"   Categoría: {issue.get('category', 'N/A')}\n"
                resultado += f"   Severidad: {issue.get('severity', 'N/A')}\n"
                resultado += f"   Dispositivo: {issue.get('deviceName', 'N/A')}\n"
                resultado += f"   Última ocurrencia: {issue.get('lastOccurredTime', 'N/A')}\n\n"
            
            if len(issues) > 20:
                resultado += f"... y {len(issues) - 20} issues más\n"
            
            return resultado
        
        return f"No se encontraron issues con severidad {severity}"
        
    except Exception as e:
        return f"Error al obtener issues: {str(e)}"


@mcp.tool()
def catalyst_resumen_red() -> str:
    """
    Obtiene un dashboard general del estado de la red en Catalyst Center.
    
    Returns:
        Resumen con salud general, dispositivos, clientes e issues críticos
    """
    try:
        session = get_catalyst_session()
        
        # Obtener salud general
        endpoint_health = "/dna/intent/api/v1/network-health"
        health_data = session.get(endpoint_health, timeout=30)
        
        # Obtener conteo de dispositivos
        endpoint_devices = "/dna/intent/api/v1/network-device/count"
        devices_count = session.get(endpoint_devices, timeout=30)
        
        # Obtener issues críticos
        endpoint_issues = "/dna/intent/api/v1/issues?severity=HIGH"
        issues = session.get(endpoint_issues, timeout=30)
        
        resultado = f"📊 RESUMEN GENERAL - CATALYST CENTER\n"
        resultado += f"{'='*70}\n\n"
        
        # Salud general
        if 'response' in health_data:
            health_scores = health_data['response']
            resultado += f"💚 SALUD DE LA RED:\n"
            for health in health_scores[:5]:
                resultado += f"  {health.get('entity', 'N/A')}: {health.get('healthScore', 'N/A')}/10\n"
            resultado += f"\n"
        
        # Dispositivos
        if 'response' in devices_count:
            count = devices_count['response']
            resultado += f"🖥️  DISPOSITIVOS:\n"
            resultado += f"  Total: {count}\n\n"
        
        # Issues críticos
        if 'response' in issues:
            issues_list = issues['response']
            resultado += f"⚠️  ISSUES CRÍTICOS: {len(issues_list)}\n"
        
        resultado += f"\n{'='*70}\n"
        resultado += f"✅ Sistema operativo y monitoreando\n"
        
        return resultado
        
    except Exception as e:
        return f"Error al obtener resumen de red: {str(e)}"


@mcp.tool()
def top_sitios_saturados(
    top: int = 20,
    umbral_pct: float = 0.0
) -> str:
    """
    Identifica los sitios SD-WAN más saturados consultando las interfaces WAN de TODOS 
    los dispositivos en tiempo real usando consultas paralelas.
    
    Calcula el porcentaje de utilización de cada enlace WAN (VPN 0) comparando 
    el tráfico actual (kbps) contra la velocidad del enlace (speed-mbps).
    Analiza los ~325 dispositivos en ~30-40 segundos gracias a consultas concurrentes.
    
    Args:
        top: Número de sitios más saturados a mostrar (default: 20)
        umbral_pct: Solo mostrar interfaces con utilización mayor a este porcentaje (default: 0.0)
    
    Returns:
        Ranking de sitios por saturación con detalle de interfaces, tráfico y % de utilización.
        Incluye estadísticas globales de toda la red.
    
    Ejemplo:
        top_sitios_saturados() - Top 20 sitios más saturados (analiza TODOS los dispositivos)
        top_sitios_saturados(top=10, umbral_pct=10) - Solo sitios con más de 10% de utilización
    """
    try:
        import time as time_mod
        start_time = time_mod.time()
        
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Analizando saturación de TODOS los sitios (consultas paralelas)...", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener WAN edges alcanzables
        devices_result = session.get("/dataservice/device")
        all_devices = devices_result.get('data', [])
        
        vedges = [d for d in all_devices 
                  if d.get('device-type') == 'vedge' and d.get('reachability') == 'reachable']
        
        if not vedges:
            return "❌ No se encontraron dispositivos WAN Edge alcanzables"
        
        total_to_query = len(vedges)
        
        resultado = f"📊 ANÁLISIS DE SATURACIÓN DE SITIOS SD-WAN\n"
        resultado += f"{'='*110}\n\n"
        resultado += f"🔎 Modo: COMPLETO — Analizando TODOS los {total_to_query} dispositivos en paralelo\n"
        resultado += f"📡 WAN Edges alcanzables: {total_to_query}\n\n"
        
        # Función para consultar un dispositivo individual
        def consultar_dispositivo(dev):
            dev_id = dev.get('deviceId') or dev.get('system-ip', '')
            hostname = dev.get('host-name', '')
            site_id = str(dev.get('site-id', 'N/A'))
            interfaces_result = []
            
            try:
                resp = session.get(f"/dataservice/device/interface?deviceId={dev_id}", timeout=15)
                ifaces = resp.get('data', [])
                
                for iface in ifaces:
                    vpn = iface.get('vpn-id')
                    oper_status = iface.get('if-oper-status', '')
                    ifname = iface.get('ifname', '')
                    
                    if str(vpn) != '0' or 'ready' not in oper_status.lower():
                        continue
                    if ifname.lower().startswith(('loopback', 'system', 'sdwan_')):
                        continue
                    
                    rx_kbps = int(iface.get('rx-kbps', 0) or 0)
                    tx_kbps = int(iface.get('tx-kbps', 0) or 0)
                    speed_mbps = iface.get('speed-mbps', 0)
                    rx_octets = int(iface.get('rx-octets', 0) or 0)
                    tx_octets = int(iface.get('tx-octets', 0) or 0)
                    
                    utilization = 0.0
                    if speed_mbps and speed_mbps != 'N/A':
                        speed_kbps = int(speed_mbps) * 1000
                        if speed_kbps > 0:
                            utilization = ((rx_kbps + tx_kbps) / speed_kbps) * 100
                    
                    if rx_kbps + tx_kbps == 0:
                        continue
                    
                    interfaces_result.append({
                        'hostname': hostname,
                        'site_id': site_id,
                        'ifname': ifname,
                        'rx_kbps': rx_kbps,
                        'tx_kbps': tx_kbps,
                        'speed_mbps': speed_mbps,
                        'utilization': utilization,
                        'rx_gb': rx_octets / (1024**3),
                        'tx_gb': tx_octets / (1024**3),
                        'description': iface.get('description', '')
                    })
                
                return {'ok': True, 'interfaces': interfaces_result}
            except Exception as e:
                return {'ok': False, 'error': str(e)[:50], 'hostname': hostname}
        
        # Consultas paralelas con ThreadPoolExecutor
        resultados_devices = []
        errores = 0
        consultados = 0
        
        # Limitar concurrencia a 10 para no saturar vManage
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(consultar_dispositivo, dev): dev for dev in vedges}
            
            for future in as_completed(futures):
                result = future.result()
                if result['ok']:
                    resultados_devices.extend(result['interfaces'])
                    consultados += 1
                else:
                    errores += 1
                    print(f"   ⚠️ Error en {result.get('hostname', '?')}: {result.get('error', '?')}", file=sys.stderr)
                
                if (consultados + errores) % 50 == 0:
                    print(f"   ... {consultados + errores}/{total_to_query} dispositivos procesados", file=sys.stderr)
        
        elapsed = time_mod.time() - start_time
        
        if not resultados_devices:
            return f"❌ No se encontraron interfaces con datos de tráfico\n\nTiempo: {elapsed:.1f}s | Consultados: {consultados} | Errores: {errores}"
        
        # Agregar por sitio
        sitios = {}
        for iface in resultados_devices:
            site_id = iface['site_id']
            if site_id not in sitios:
                sitios[site_id] = {
                    'interfaces': [],
                    'hostnames': set(),
                    'max_util': 0.0,
                    'total_rx_kbps': 0,
                    'total_tx_kbps': 0,
                    'total_rx_gb': 0.0,
                    'total_tx_gb': 0.0
                }
            
            sitios[site_id]['hostnames'].add(iface['hostname'])
            sitios[site_id]['total_rx_kbps'] += iface['rx_kbps']
            sitios[site_id]['total_tx_kbps'] += iface['tx_kbps']
            sitios[site_id]['total_rx_gb'] += iface['rx_gb']
            sitios[site_id]['total_tx_gb'] += iface['tx_gb']
            
            if iface['utilization'] > sitios[site_id]['max_util']:
                sitios[site_id]['max_util'] = iface['utilization']
            
            sitios[site_id]['interfaces'].append(iface)
        
        def fmt_kbps(kbps):
            if kbps > 1000000:
                return f"{kbps / 1000000:.1f} Gbps"
            if kbps > 1000:
                return f"{kbps / 1000:.1f} Mbps"
            return f"{kbps} kbps"
        
        def fmt_gb(gb):
            if gb > 1024:
                return f"{gb / 1024:.1f} TB"
            return f"{gb:.1f} GB"
        
        sorted_sites = sorted(sitios.items(), key=lambda x: x[1]['max_util'], reverse=True)
        
        if umbral_pct > 0:
            sorted_sites = [(s, d) for s, d in sorted_sites if d['max_util'] >= umbral_pct]
        
        resultado += f"⏱️  Tiempo de análisis: {elapsed:.1f}s ({total_to_query} dispositivos en paralelo)\n"
        resultado += f"✅ Dispositivos consultados: {consultados} de {total_to_query}\n"
        if errores > 0:
            resultado += f"⚠️  Errores: {errores}\n"
        resultado += f"🏢 Sitios con tráfico: {len(sitios)}\n\n"
        
        # === RANKING DE SITIOS ===
        resultado += f"{'='*120}\n"
        resultado += f"🔝 TOP {min(top, len(sorted_sites))} SITIOS MÁS SATURADOS:\n\n"
        resultado += f"{'#':<4} {'SITIO':<10} {'MAX %':<8} {'TRÁFICO ACTUAL':<22} {'ACUMULADO':<22} {'DISPOSITIVOS':<30} {'IFACES':<8}\n"
        resultado += f"{'-'*120}\n"
        
        for i, (site_id, data) in enumerate(sorted_sites[:top], 1):
            total_actual = data['total_rx_kbps'] + data['total_tx_kbps']
            total_acum = data['total_rx_gb'] + data['total_tx_gb']
            max_util = data['max_util']
            hostnames = ', '.join(sorted(data['hostnames']))[:28]
            num_ifaces = len(data['interfaces'])
            
            if max_util >= 80:
                icon = "🔴"
            elif max_util >= 50:
                icon = "🟠"
            elif max_util >= 20:
                icon = "🟡"
            else:
                icon = "🟢"
            
            resultado += f"{i:<4} {site_id:<10} {icon}{max_util:>5.1f}% {fmt_kbps(total_actual):<22} {fmt_gb(total_acum):<22} {hostnames:<30} {num_ifaces:<8}\n"
            
            # Detalle de interfaces físicas del sitio (sin tunnels, ordenadas por utilización)
            ifaces_fisicas = [ifc for ifc in data['interfaces'] if not ifc['ifname'].lower().startswith('tunnel')]
            ifaces_sorted = sorted(ifaces_fisicas, key=lambda x: x['utilization'], reverse=True)
            resultado += f"{'':5} {'INTERFAZ':<22} {'RX':<14} {'TX':<14} {'SPEED':<12} {'% USO':<8} {'DESCRIPCIÓN'}\n"
            for ifc in ifaces_sorted:
                u = ifc['utilization']
                if u >= 80: ic = "🔴"
                elif u >= 50: ic = "🟠"
                elif u >= 20: ic = "🟡"
                else: ic = "🟢"
                spd = f"{ifc['speed_mbps']} Mbps" if ifc['speed_mbps'] != 'N/A' else 'N/A'
                desc = ifc.get('description', '') or ''
                resultado += f"{'':5} {ifc['ifname']:<22} {fmt_kbps(ifc['rx_kbps']):<14} {fmt_kbps(ifc['tx_kbps']):<14} {spd:<12} {ic}{u:>5.1f}% {desc}\n"
            resultado += f"\n"
        
        # === DETALLE DE INTERFACES MÁS SATURADAS ===
        all_interfaces = sorted(resultados_devices, key=lambda x: x['utilization'], reverse=True)
        top_ifaces = [i for i in all_interfaces if i['utilization'] >= max(umbral_pct, 1.0)][:25]
        
        if top_ifaces:
            resultado += f"\n{'='*110}\n"
            resultado += f"🔌 TOP {len(top_ifaces)} INTERFACES MÁS SATURADAS:\n\n"
            resultado += f"{'#':<4} {'SITIO':<10} {'DISPOSITIVO':<25} {'INTERFAZ':<22} {'RX':<12} {'TX':<12} {'SPEED':<10} {'% USO':<8}\n"
            resultado += f"{'-'*110}\n"
            
            for j, iface in enumerate(top_ifaces, 1):
                util = iface['utilization']
                if util >= 80:
                    icon = "🔴"
                elif util >= 50:
                    icon = "🟠"
                elif util >= 20:
                    icon = "🟡"
                else:
                    icon = "🟢"
                
                speed_str = f"{iface['speed_mbps']} Mbps" if iface['speed_mbps'] != 'N/A' else 'N/A'
                resultado += f"{j:<4} {iface['site_id']:<10} {iface['hostname']:<25} {iface['ifname']:<22} {fmt_kbps(iface['rx_kbps']):<12} {fmt_kbps(iface['tx_kbps']):<12} {speed_str:<10} {icon}{util:>5.1f}%\n"
                
                if iface.get('description'):
                    resultado += f"{'':4} {'':10} └─ {iface['description']}\n"
        
        # === ESTADÍSTICAS GLOBALES ===
        total_rx_global = sum(d['total_rx_kbps'] for d in sitios.values())
        total_tx_global = sum(d['total_tx_kbps'] for d in sitios.values())
        total_rx_gb_global = sum(d['total_rx_gb'] for d in sitios.values())
        total_tx_gb_global = sum(d['total_tx_gb'] for d in sitios.values())
        sitios_criticos = sum(1 for _, d in sorted_sites if d['max_util'] >= 80)
        sitios_altos = sum(1 for _, d in sorted_sites if 50 <= d['max_util'] < 80)
        sitios_medios = sum(1 for _, d in sorted_sites if 20 <= d['max_util'] < 50)
        sitios_bajos = sum(1 for _, d in sorted_sites if d['max_util'] < 20)
        
        resultado += f"\n{'='*110}\n"
        resultado += f"📈 ESTADÍSTICAS GLOBALES DE LA RED:\n\n"
        resultado += f"  📥 Tráfico Rx actual:    {fmt_kbps(total_rx_global)}\n"
        resultado += f"  📤 Tráfico Tx actual:    {fmt_kbps(total_tx_global)}\n"
        resultado += f"  📊 Tráfico total actual: {fmt_kbps(total_rx_global + total_tx_global)}\n"
        resultado += f"  💾 Acumulado Rx:         {fmt_gb(total_rx_gb_global)}\n"
        resultado += f"  💾 Acumulado Tx:         {fmt_gb(total_tx_gb_global)}\n\n"
        resultado += f"  🔴 Sitios críticos (≥80%):  {sitios_criticos}\n"
        resultado += f"  🟠 Sitios altos (50-80%):   {sitios_altos}\n"
        resultado += f"  🟡 Sitios medios (20-50%):  {sitios_medios}\n"
        resultado += f"  🟢 Sitios bajos (<20%):     {sitios_bajos}\n"
        
        resultado += f"\n💡 Leyenda: 🔴 ≥80% | 🟠 50-80% | 🟡 20-50% | 🟢 <20%\n"
        resultado += f"💡 % USO = (Rx + Tx kbps) / (Speed kbps) × 100 — interfaces VPN 0 (transporte)\n"
        resultado += f"💡 Análisis de {consultados} dispositivos completado en {elapsed:.1f}s\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al analizar saturación: {str(e)}"


@mcp.tool()
def ver_saturacion_sitio(sitio: str) -> str:
    """
    Muestra la saturación en tiempo real de un sitio SD-WAN específico.
    Consulta las interfaces WAN (VPN 0) de TODOS los dispositivos del sitio
    y calcula el porcentaje de utilización de cada enlace.
    
    Args:
        sitio: ID del sitio, nombre parcial o hostname de un dispositivo del sitio
               (ej: "51304", "304", "SDWAN-CJF-304-RT01")
    
    Returns:
        Detalle completo del sitio: dispositivos, interfaces WAN, tráfico Rx/Tx,
        velocidad del enlace, % de utilización y descripción.
    
    Ejemplo:
        ver_saturacion_sitio("51304") - Saturación del sitio 51304
        ver_saturacion_sitio("304") - Busca sitios que contengan "304"
        ver_saturacion_sitio("SDWAN-CJF-304-RT01") - Por hostname del dispositivo
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Analizando saturación del sitio: {sitio}", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener todos los dispositivos
        devices_result = session.get("/dataservice/device")
        all_devices = devices_result.get('data', [])
        
        # Buscar dispositivos del sitio por site-id, hostname o nombre parcial
        sitio_lower = sitio.strip().lower()
        site_devices = []
        
        for dev in all_devices:
            if dev.get('device-type') != 'vedge' or dev.get('reachability') != 'reachable':
                continue
            
            dev_site_id = str(dev.get('site-id', ''))
            dev_hostname = dev.get('host-name', '').lower()
            
            # Coincidencia exacta por site-id
            if sitio_lower == dev_site_id.lower():
                site_devices.append(dev)
            # Coincidencia parcial por site-id (ej: "304" matchea "51304")
            elif sitio_lower in dev_site_id:
                site_devices.append(dev)
            # Coincidencia por hostname
            elif sitio_lower in dev_hostname:
                site_devices.append(dev)
        
        if not site_devices:
            return (f"❌ No se encontraron dispositivos WAN Edge para el sitio '{sitio}'\n\n"
                    f"Intenta con:\n"
                    f"  • ID del sitio: ver_saturacion_sitio('51304')\n"
                    f"  • Parcial: ver_saturacion_sitio('304')\n"
                    f"  • Hostname: ver_saturacion_sitio('SDWAN-CJF-304-RT01')")
        
        # Verificar si hay dispositivos de múltiples sitios (búsqueda parcial ambigua)
        site_ids_encontrados = set(str(d.get('site-id', '')) for d in site_devices)
        
        resultado = f"📊 SATURACIÓN EN TIEMPO REAL — "
        if len(site_ids_encontrados) == 1:
            resultado += f"SITIO {list(site_ids_encontrados)[0]}\n"
        else:
            resultado += f"SITIOS: {', '.join(sorted(site_ids_encontrados))}\n"
        resultado += f"{'='*120}\n\n"
        resultado += f"🔎 Búsqueda: '{sitio}'\n"
        resultado += f"📡 Dispositivos encontrados: {len(site_devices)}\n\n"
        
        def fmt_kbps(kbps):
            if kbps > 1000000:
                return f"{kbps / 1000000:.1f} Gbps"
            if kbps > 1000:
                return f"{kbps / 1000:.1f} Mbps"
            return f"{kbps} kbps"
        
        def fmt_gb(gb):
            if gb > 1024:
                return f"{gb / 1024:.1f} TB"
            return f"{gb:.1f} GB"
        
        total_interfaces = 0
        max_util_global = 0.0
        total_rx_kbps = 0
        total_tx_kbps = 0
        
        for dev in site_devices:
            dev_id = dev.get('deviceId') or dev.get('system-ip', '')
            hostname = dev.get('host-name', '')
            system_ip = dev.get('system-ip', '')
            dev_site_id = str(dev.get('site-id', ''))
            dev_model = dev.get('device-model', '')
            
            resultado += f"{'─'*120}\n"
            resultado += f"🖥️  {hostname} | System IP: {system_ip} | Site: {dev_site_id} | Modelo: {dev_model}\n"
            resultado += f"{'─'*120}\n"
            
            try:
                resp = session.get(f"/dataservice/device/interface?deviceId={dev_id}", timeout=15)
                ifaces = resp.get('data', [])
                
                wan_ifaces = []
                for iface in ifaces:
                    vpn = iface.get('vpn-id')
                    oper_status = iface.get('if-oper-status', '')
                    ifname = iface.get('ifname', '')
                    
                    if str(vpn) != '0':
                        continue
                    if ifname.lower().startswith(('loopback', 'system', 'sdwan', 'tunnel', 'nvi', 'vmanage')):
                        continue
                    
                    rx_kbps = int(iface.get('rx-kbps', 0) or 0)
                    tx_kbps = int(iface.get('tx-kbps', 0) or 0)
                    speed_mbps = iface.get('speed-mbps', 0)
                    rx_octets = int(iface.get('rx-octets', 0) or 0)
                    tx_octets = int(iface.get('tx-octets', 0) or 0)
                    
                    is_up = 'ready' in oper_status.lower()
                    
                    # Omitir interfaces DOWN sin tráfico acumulado
                    if not is_up and rx_kbps + tx_kbps == 0 and rx_octets + tx_octets == 0:
                        continue
                    
                    utilization = 0.0
                    if speed_mbps and speed_mbps != 'N/A':
                        speed_kbps = int(speed_mbps) * 1000
                        if speed_kbps > 0:
                            utilization = ((rx_kbps + tx_kbps) / speed_kbps) * 100
                    
                    wan_ifaces.append({
                        'ifname': ifname,
                        'rx_kbps': rx_kbps,
                        'tx_kbps': tx_kbps,
                        'speed_mbps': speed_mbps,
                        'utilization': utilization,
                        'rx_gb': rx_octets / (1024**3),
                        'tx_gb': tx_octets / (1024**3),
                        'description': iface.get('description', '') or '',
                        'is_up': is_up,
                        'oper_status': oper_status,
                        'ip_address': iface.get('ip-address', 'N/A')
                    })
                
                wan_ifaces.sort(key=lambda x: x['utilization'], reverse=True)
                
                if not wan_ifaces:
                    resultado += f"  ⚠️  Sin interfaces WAN físicas en VPN 0\n\n"
                    continue
                
                resultado += f"  {'INTERFAZ':<25} {'ESTADO':<10} {'RX':<14} {'TX':<14} {'SPEED':<12} {'% USO':<10} {'ACUM RX':<12} {'ACUM TX':<12} {'DESCRIPCIÓN'}\n"
                resultado += f"  {'-'*115}\n"
                
                for ifc in wan_ifaces:
                    u = ifc['utilization']
                    if u >= 80: ic = "🔴"
                    elif u >= 50: ic = "🟠"
                    elif u >= 20: ic = "🟡"
                    else: ic = "🟢"
                    
                    status = "🟢 UP" if ifc['is_up'] else "🔴 DOWN"
                    spd = f"{ifc['speed_mbps']} Mbps" if ifc['speed_mbps'] != 'N/A' else 'N/A'
                    
                    resultado += f"  {ifc['ifname']:<25} {status:<10} {fmt_kbps(ifc['rx_kbps']):<14} {fmt_kbps(ifc['tx_kbps']):<14} {spd:<12} {ic}{u:>5.1f}%   {fmt_gb(ifc['rx_gb']):<12} {fmt_gb(ifc['tx_gb']):<12} {ifc['description']}\n"
                    
                    total_interfaces += 1
                    total_rx_kbps += ifc['rx_kbps']
                    total_tx_kbps += ifc['tx_kbps']
                    if u > max_util_global:
                        max_util_global = u
                
                resultado += f"\n"
                
            except Exception as e:
                resultado += f"  ❌ Error al consultar: {str(e)[:80]}\n\n"
        
        # Resumen del sitio
        if max_util_global >= 80: icon = "🔴 CRÍTICO"
        elif max_util_global >= 50: icon = "🟠 ALTO"
        elif max_util_global >= 20: icon = "🟡 MEDIO"
        else: icon = "🟢 BAJO"
        
        resultado += f"{'='*120}\n"
        resultado += f"📈 RESUMEN DEL SITIO:\n\n"
        resultado += f"  📡 Dispositivos:           {len(site_devices)}\n"
        resultado += f"  🔌 Interfaces WAN:         {total_interfaces}\n"
        resultado += f"  📥 Tráfico Rx total:       {fmt_kbps(total_rx_kbps)}\n"
        resultado += f"  📤 Tráfico Tx total:       {fmt_kbps(total_tx_kbps)}\n"
        resultado += f"  📊 Tráfico total:          {fmt_kbps(total_rx_kbps + total_tx_kbps)}\n"
        resultado += f"  🎯 Saturación máxima:      {max_util_global:.1f}% — {icon}\n\n"
        resultado += f"💡 % USO = (Rx + Tx kbps) / (Speed kbps) × 100 — interfaces VPN 0 (transporte)\n"
        resultado += f"💡 Leyenda: 🔴 ≥80% | 🟠 50-80% | 🟡 20-50% | 🟢 <20%\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al analizar saturación del sitio: {str(e)}"


@mcp.tool()
def ver_aplicaciones_sitio(
    sitio: str,
    top: int = 30,
    familia: str = ""
) -> str:
    """
    Muestra qué aplicaciones están corriendo por los enlaces de un sitio SD-WAN específico.
    Usa estadísticas DPI agregadas para mostrar el ranking de aplicaciones por consumo de ancho de banda,
    agrupadas también por familia de aplicación.
    
    Args:
        sitio: ID del sitio, parcial o hostname (ej: "51304", "304", "SDWAN-CJF-304-RT01")
        top: Número de aplicaciones a mostrar (default: 30)
        familia: (Opcional) Filtrar por familia de aplicación (ej: "web", "audio-video", "encrypted")
    
    Returns:
        Ranking de aplicaciones por tráfico con familias, paquetes y flujos.
        Incluye resumen por familia de aplicación.
    
    Ejemplo:
        ver_aplicaciones_sitio("51304") - Todas las apps del sitio 51304
        ver_aplicaciones_sitio("304", top=10) - Top 10 del sitio
        ver_aplicaciones_sitio("51304", familia="audio-video") - Solo apps de audio/video
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo aplicaciones DPI del sitio: {sitio}", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener dispositivos
        devices_result = session.get("/dataservice/device")
        all_devices = devices_result.get('data', [])
        
        # Buscar dispositivos del sitio
        sitio_lower = sitio.strip().lower()
        site_devices = []
        
        for dev in all_devices:
            if dev.get('device-type') != 'vedge' or dev.get('reachability') != 'reachable':
                continue
            dev_site_id = str(dev.get('site-id', ''))
            dev_hostname = dev.get('host-name', '').lower()
            
            if (sitio_lower == dev_site_id.lower() or
                sitio_lower in dev_site_id or
                sitio_lower in dev_hostname):
                site_devices.append(dev)
        
        if not site_devices:
            return (f"❌ No se encontraron dispositivos WAN Edge para '{sitio}'\n\n"
                    f"Intenta con:\n"
                    f"  • ver_aplicaciones_sitio('51304')\n"
                    f"  • ver_aplicaciones_sitio('304')\n"
                    f"  • ver_aplicaciones_sitio('SDWAN-CJF-304-RT01')")
        
        system_ips = [d.get('system-ip', '') for d in site_devices if d.get('system-ip')]
        hostnames = [d.get('host-name', '') for d in site_devices]
        site_ids = sorted(set(str(d.get('site-id', '')) for d in site_devices))
        
        def fmt_bytes(b):
            if b > 1024**4: return f"{b / (1024**4):.2f} TB"
            if b > 1024**3: return f"{b / (1024**3):.2f} GB"
            if b > 1024**2: return f"{b / (1024**2):.1f} MB"
            if b > 1024: return f"{b / 1024:.1f} KB"
            return f"{b} B"
        
        resultado = f"📱 APLICACIONES DPI — "
        if len(site_ids) == 1:
            resultado += f"SITIO {site_ids[0]}\n"
        else:
            resultado += f"SITIOS: {', '.join(site_ids)}\n"
        resultado += f"{'='*120}\n\n"
        resultado += f"🔎 Búsqueda: '{sitio}'\n"
        resultado += f"📡 Dispositivos: {', '.join(hostnames)}\n\n"
        
        # === CONSULTA 1: Aplicaciones por tráfico ===
        payload_apps = {
            "query": {
                "condition": "AND",
                "rules": [
                    {"field": "vdevice_name", "type": "string", "value": system_ips, "operator": "in"}
                ]
            },
            "aggregation": {
                "field": [
                    {"property": "application", "size": 200, "sequence": 1}
                ],
                "metrics": [
                    {"property": "octets", "type": "sum"},
                    {"property": "packets", "type": "sum"}
                ]
            }
        }
        
        resp_apps = session.post("/dataservice/statistics/dpi/aggregation", payload_apps, timeout=30)
        apps = resp_apps.get('data', [])
        
        if not apps:
            return (f"{resultado}❌ No hay datos DPI disponibles para este sitio.\n\n"
                    f"Verifica que DPI esté habilitado en los dispositivos del sitio.")
        
        # Si se filtra por familia, obtener el mapeo app->familia
        app_familia = {}
        if familia:
            payload_fam_app = {
                "query": {
                    "condition": "AND",
                    "rules": [
                        {"field": "vdevice_name", "type": "string", "value": system_ips, "operator": "in"}
                    ]
                },
                "aggregation": {
                    "field": [
                        {"property": "application", "size": 200, "sequence": 1},
                        {"property": "family", "size": 1, "sequence": 2}
                    ],
                    "metrics": [
                        {"property": "octets", "type": "sum"}
                    ]
                }
            }
            resp_fam_app = session.post("/dataservice/statistics/dpi/aggregation", payload_fam_app, timeout=30)
            for item in resp_fam_app.get('data', []):
                app_familia[item.get('application', '')] = item.get('family', '')
            
            familia_lower = familia.lower()
            apps = [a for a in apps if familia_lower in app_familia.get(a.get('application', ''), '').lower()]
            
            if not apps:
                return f"{resultado}ℹ️  No hay aplicaciones de la familia '{familia}' en este sitio."
        
        # Ordenar por octetos
        apps_sorted = sorted(apps, key=lambda x: int(x.get('octets', 0)), reverse=True)
        total_bytes = sum(int(a.get('octets', 0)) for a in apps_sorted)
        
        if familia:
            resultado += f"🔍 Filtro: familia = '{familia}'\n"
        resultado += f"📊 Aplicaciones únicas: {len(apps_sorted)} | Tráfico total: {fmt_bytes(total_bytes)}\n\n"
        
        resultado += f"{'#':<4} {'APLICACIÓN':<35} {'TRÁFICO':<14} {'%':<8} {'PAQUETES':<14} {'FLUJOS':<10}\n"
        resultado += f"{'-'*90}\n"
        
        for i, app in enumerate(apps_sorted[:top], 1):
            octets = int(app.get('octets', 0))
            packets = int(app.get('packets', 0))
            count = int(app.get('count', 0))
            pct = (octets / total_bytes * 100) if total_bytes > 0 else 0
            nombre = app.get('application', 'N/A')[:33]
            
            if pct >= 10: icon = "🔴"
            elif pct >= 5: icon = "🟠"
            elif pct >= 1: icon = "🟡"
            else: icon = "🟢"
            
            resultado += f"{i:<4} {icon} {nombre:<33} {fmt_bytes(octets):<14} {pct:>5.1f}%  {packets:<14,} {count:<10,}\n"
        
        if len(apps_sorted) > top:
            otros = len(apps_sorted) - top
            otros_bytes = sum(int(a.get('octets', 0)) for a in apps_sorted[top:])
            otros_pct = (otros_bytes / total_bytes * 100) if total_bytes > 0 else 0
            resultado += f"\n     ... y {otros} aplicaciones más ({fmt_bytes(otros_bytes)}, {otros_pct:.1f}%)\n"
        
        # === CONSULTA 2: Resumen por familias ===
        if not familia:
            payload_fam = {
                "query": {
                    "condition": "AND",
                    "rules": [
                        {"field": "vdevice_name", "type": "string", "value": system_ips, "operator": "in"}
                    ]
                },
                "aggregation": {
                    "field": [
                        {"property": "family", "size": 50, "sequence": 1}
                    ],
                    "metrics": [
                        {"property": "octets", "type": "sum"},
                        {"property": "packets", "type": "sum"}
                    ]
                }
            }
            
            resp_fam = session.post("/dataservice/statistics/dpi/aggregation", payload_fam, timeout=30)
            familias_data = resp_fam.get('data', [])
            
            if familias_data:
                fams_sorted = sorted(familias_data, key=lambda x: int(x.get('octets', 0)), reverse=True)
                total_fam = sum(int(f.get('octets', 0)) for f in fams_sorted)
                
                resultado += f"\n{'='*90}\n"
                resultado += f"📂 RESUMEN POR FAMILIA DE APLICACIÓN:\n\n"
                resultado += f"{'#':<4} {'FAMILIA':<35} {'TRÁFICO':<14} {'%':<8} {'PAQUETES':<14}\n"
                resultado += f"{'-'*78}\n"
                
                for i, fam in enumerate(fams_sorted, 1):
                    octets = int(fam.get('octets', 0))
                    packets = int(fam.get('packets', 0))
                    pct = (octets / total_fam * 100) if total_fam > 0 else 0
                    nombre = fam.get('family', 'N/A')[:33]
                    
                    if pct >= 10: icon = "🔴"
                    elif pct >= 5: icon = "🟠"
                    elif pct >= 1: icon = "🟡"
                    else: icon = "🟢"
                    
                    resultado += f"{i:<4} {icon} {nombre:<33} {fmt_bytes(octets):<14} {pct:>5.1f}%  {packets:<14,}\n"
        
        resultado += f"\n{'='*90}\n"
        resultado += f"💡 HERRAMIENTAS RELACIONADAS:\n"
        resultado += f"  • ver_aplicaciones_sitio('{site_ids[0]}', familia='audio-video') — Filtrar por familia\n"
        resultado += f"  • ver_saturacion_sitio('{site_ids[0]}') — Saturación de enlaces WAN del sitio\n"
        resultado += f"  • obtener_ips_destino_aplicacion('google-services') — IPs destino de una app\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener aplicaciones del sitio: {str(e)}"


@mcp.tool()
def obtener_flujos_dpi_sitio(sitio: str, aplicacion: str = "") -> str:
    """
    Obtiene información de flujos DPI de un sitio específico usando vManage API.
    Muestra dispositivos del sitio y sus aplicaciones detectadas por DPI.
    
    Args:
        sitio: Nombre del sitio, ID del sitio, o hostname del dispositivo (ej: "SITE_100", "100", "SDWAN-CJF-323-RT01")
        aplicacion: (Opcional) Filtrar por aplicación específica (ej: "adobe-services", "ssl")
    
    Returns:
        Dispositivos del sitio con aplicaciones DPI y estadísticas de uso
        
    Nota: Para IPs origen→destino específicas, usa vManage GUI:
          Monitor → Applications → DPI Flows → Filter por sitio → Export
    """
    try:
        session = get_vmanage_session()
        
        # Buscar dispositivos del sitio
        dispositivos = session.get("/dataservice/device")
        
        # Filtrar dispositivos por sitio
        devices_encontrados = []
        for dev in dispositivos.get('data', []):
            site_id = dev.get('site-id', '')
            hostname = dev.get('host-name', '')
            
            # Buscar por site_id, nombre de sitio en hostname, o hostname exacto
            if (str(site_id) == sitio or 
                sitio.upper() in hostname.upper() or
                sitio.lower() in hostname.lower()):
                devices_encontrados.append(dev)
        
        if not devices_encontrados:
            return f"❌ No se encontraron dispositivos para el sitio '{sitio}'.\n\nVerifica el nombre del sitio o ID."
        
        # Obtener TODOS los flujos DPI una sola vez
        all_dpi = session.get("/dataservice/statistics/dpi", timeout=60)
        all_flows = all_dpi.get('data', [])
        
        # Obtener estadísticas DPI de cada dispositivo
        resultado = f"🔍 FLUJOS DPI - {sitio.upper()}\n"
        resultado += f"{'='*80}\n\n"
        resultado += f"📊 Dispositivos encontrados: {len(devices_encontrados)}\n"
        resultado += f"📡 Flujos DPI totales en red: {len(all_flows)}\n\n"
        
        for i, dev in enumerate(devices_encontrados, 1):
            device_id = dev.get('deviceId', dev.get('system-ip', ''))
            hostname = dev.get('host-name', 'Unknown')
            site_id = dev.get('site-id', 'N/A')
            device_model = dev.get('device-model', 'N/A')
            reachability = dev.get('reachability', 'unknown')
            
            # Indicador de estado
            estado_icon = "🟢" if reachability == "reachable" else "🔴"
            
            resultado += f"{i}. {hostname} {estado_icon}\n"
            resultado += f"   Site ID: {site_id} | Modelo: {device_model}\n"
            resultado += f"   System IP: {device_id}\n"
            
            if reachability != "reachable":
                resultado += f"   ⚠️  Dispositivo no alcanzable\n\n"
                continue
            
            # Filtrar flujos DPI de este dispositivo
            try:
                device_flows = [f for f in all_flows 
                               if f.get('host_name', '') == hostname or 
                                  f.get('vdevice_name', '') == device_id]
                
                # Filtrar por aplicación si se especifica
                if aplicacion:
                    device_flows = [f for f in device_flows 
                                   if aplicacion.lower() in f.get('application', '').lower()]
                
                if device_flows:
                    # Agregar por aplicación
                    apps_agg = {}
                    for flow in device_flows:
                        app_name = flow.get('application', 'unknown')
                        octets = int(flow.get('octets', 0))
                        if app_name not in apps_agg:
                            apps_agg[app_name] = {'bytes': 0, 'flujos': 0}
                        apps_agg[app_name]['bytes'] += octets
                        apps_agg[app_name]['flujos'] += 1
                    
                    # Ordenar por bytes
                    sorted_apps = sorted(apps_agg.items(), key=lambda x: x[1]['bytes'], reverse=True)
                    
                    total_bytes = sum(a[1]['bytes'] for a in sorted_apps)
                    
                    def fmt_bytes(b):
                        if b > 1024**3: return f"{b / (1024**3):.2f} GB"
                        if b > 1024**2: return f"{b / (1024**2):.2f} MB"
                        if b > 1024: return f"{b / 1024:.1f} KB"
                        return f"{b} B"
                    
                    resultado += f"\n   📱 Top aplicaciones DPI ({len(sorted_apps)} apps, {len(device_flows)} flujos, {fmt_bytes(total_bytes)} total):\n"
                    resultado += f"   {'#':<5} {'APLICACIÓN':<30} {'TRÁFICO':<12} {'%':<7} {'FLUJOS':<8}\n"
                    resultado += f"   {'-'*65}\n"
                    
                    for j, (app_name, data) in enumerate(sorted_apps[:15], 1):
                        pct = (data['bytes'] / total_bytes * 100) if total_bytes > 0 else 0
                        resultado += f"   {j:<5} {app_name:<30} {fmt_bytes(data['bytes']):<12} {pct:>5.1f}% {data['flujos']:<8}\n"
                    
                    if len(sorted_apps) > 15:
                        resultado += f"   ... y {len(sorted_apps) - 15} aplicaciones más\n"
                else:
                    if aplicacion:
                        resultado += f"   ℹ️  No hay tráfico de '{aplicacion}' en este dispositivo\n"
                    else:
                        resultado += f"   ℹ️  Sin flujos DPI activos para este dispositivo\n"
                    
            except Exception as e:
                resultado += f"   ⚠️  Error al obtener DPI: {str(e)}\n"
            
            resultado += "\n"
        
        resultado += f"{'='*80}\n"
        resultado += f"💡 NOTAS:\n"
        resultado += f"   • Esta información viene de vManage API en tiempo real\n"
        resultado += f"   • Para ver IPs origen→destino específicas:\n"
        resultado += f"     1. Abre vManage GUI\n"
        resultado += f"     2. Monitor → Applications → DPI Flows\n"
        resultado += f"     3. Filtra por Site ID: {devices_encontrados[0].get('site-id', 'N/A')}\n"
        resultado += f"     4. Export → verás IPs origen, destino, puertos, etc.\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener flujos DPI: {str(e)}\n\nVerifica:\n1. Conexión con vManage\n2. Nombre del sitio correcto\n3. DPI habilitado en el sitio"


@mcp.tool()
def ver_metricas_dispositivos_sdwan() -> str:
    """
    Obtiene métricas de todos los dispositivos SD-WAN desde vManage.
    Muestra información de conectividad, control, y estabilidad de cada dispositivo.
    
    Útil para:
    - Ver estado de conexiones vSmart de todos los dispositivos
    - Identificar dispositivos con reinicios o crashes
    - Verificar conectividad de control plane
    - Auditoría de estabilidad de la red SD-WAN
    
    Returns:
        Tabla con métricas de dispositivos: System IP, conexiones vSmart, 
        conexiones esperadas, número de reinicios y crashes
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo métricas de dispositivos SD-WAN...", file=sys.stderr)
        
        vmanage = VManageSession(
            os.getenv("VMANAGE_IP"),
            os.getenv("VMANAGE_USERNAME"),
            os.getenv("VMANAGE_PASSWORD")
        )
        
        if not vmanage.login():
            return "❌ Error de autenticación con vManage"
        
        # Obtener lista de dispositivos (endpoint principal)
        response = vmanage.get("/dataservice/device")
        
        if not response or 'data' not in response:
            return "❌ No se pudieron obtener métricas de dispositivos"
        
        devices_data = response['data']
        
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Métricas obtenidas: {len(devices_data)} dispositivos", file=sys.stderr)
        
        resultado = f"📊 MÉTRICAS DE DISPOSITIVOS SD-WAN\n"
        resultado += f"{'='*100}\n\n"
        resultado += f"Total de dispositivos: {len(devices_data)}\n"
        resultado += f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Tabla de métricas
        resultado += f"{'Hostname':<30} {'System IP':<16} {'Site ID':<10} {'Estado':<15} {'Reachability':<15} {'Modelo':<20}\n"
        resultado += f"{'-'*120}\n"
        
        # Contadores para estadísticas
        devices_reachable = 0
        devices_unreachable = 0
        devices_up = 0
        devices_down = 0
        sites_dict = {}
        
        for device in sorted(devices_data, key=lambda x: x.get('host-name', '')):
            hostname = device.get('host-name', 'Unknown')
            system_ip = device.get('system-ip', 'N/A')
            site_id = device.get('site-id', 'N/A')
            reachability = device.get('reachability', 'unknown')
            status = device.get('status', 'unknown')
            model = device.get('device-model', 'N/A')
            
            # Estadísticas
            if reachability == 'reachable':
                devices_reachable += 1
            else:
                devices_unreachable += 1
            
            if status == 'normal':
                devices_up += 1
            else:
                devices_down += 1
            
            # Contar sitios únicos
            if site_id != 'N/A':
                sites_dict[site_id] = sites_dict.get(site_id, 0) + 1
            
            # Indicador de estado
            if reachability == 'reachable' and status == 'normal':
                status_icon = "✅"
            elif reachability == 'reachable':
                status_icon = "⚠️ "
            else:
                status_icon = "🔴"
            
            # Formatear valores
            reach_display = "🟢 Reachable" if reachability == 'reachable' else "🔴 Unreachable"
            status_display = "🟢 Normal" if status == 'normal' else f"⚠️  {status}"
            
            resultado += f"{status_icon} {hostname:<28} {system_ip:<16} {site_id:<10} {status_display:<15} {reach_display:<15} {model:<20}\n"
        
        # Resumen estadístico
        resultado += f"\n{'='*120}\n"
        resultado += f"📈 RESUMEN ESTADÍSTICO:\n\n"
        resultado += f"  🌐 Total de dispositivos:             {len(devices_data)}\n"
        resultado += f"  🏢 Total de sitios:                   {len(sites_dict)}\n"
        resultado += f"  ✅ Dispositivos alcanzables:          {devices_reachable}\n"
        resultado += f"  🔴 Dispositivos NO alcanzables:       {devices_unreachable}\n"
        resultado += f"  🟢 Dispositivos con estado normal:    {devices_up}\n"
        resultado += f"  ⚠️  Dispositivos con problemas:        {devices_down}\n"
        
        resultado += f"\n{'='*120}\n"
        resultado += f"💡 INTERPRETACIÓN:\n"
        resultado += f"  • Reachability: Indica si vManage puede contactar el dispositivo\n"
        resultado += f"  • Estado: Estado operativo del dispositivo (normal, warning, down, etc.)\n"
        resultado += f"  • Site ID: Identificador del sitio al que pertenece el dispositivo\n"
        resultado += f"\n  ✅ = Dispositivo operativo y alcanzable\n"
        resultado += f"  ⚠️  = Dispositivo alcanzable pero con advertencias\n"
        resultado += f"  🔴 = Dispositivo NO alcanzable o fuera de servicio\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener métricas de dispositivos: {str(e)}"


@mcp.tool()
def ver_estadisticas_interfaces(identificador: str, top_interfaces: int = 20) -> str:
    """
    Obtiene estadísticas detalladas de todas las interfaces de un dispositivo.
    Muestra tráfico, errores, estado administrativo/operativo, y métricas de rendimiento.
    
    Args:
        identificador: Hostname, System IP, o ID del dispositivo (ej: "SDWAN-CJF-318-RT01", "10.95.11.3")
        top_interfaces: Número de interfaces con más tráfico a destacar (default: 20)
    
    Returns:
        Estadísticas detalladas de interfaces:
        - Estado administrativo y operativo
        - Velocidad, MTU, direcciones IP/MAC
        - Tráfico Rx/Tx (kbps, packets, octets)
        - Errores y descartes
        - Top interfaces por tráfico
    
    Útil para:
    - Diagnosticar problemas de conectividad
    - Identificar interfaces con errores
    - Analizar patrones de tráfico
    - Verificar configuración de interfaces
    - Troubleshooting de rendimiento
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo estadísticas de interfaces para: {identificador}", file=sys.stderr)
        
        vmanage = VManageSession(
            os.getenv("VMANAGE_IP"),
            os.getenv("VMANAGE_USERNAME"),
            os.getenv("VMANAGE_PASSWORD")
        )
        
        if not vmanage.login():
            return "❌ Error de autenticación con vManage"
        
        # Buscar dispositivo
        devices_response = vmanage.get("/dataservice/device")
        if not devices_response or 'data' not in devices_response:
            return "❌ No se pudo obtener lista de dispositivos"
        
        devices = devices_response['data']
        
        # Buscar por hostname, system-ip o device-id
        device_found = None
        for dev in devices:
            if (identificador.lower() in dev.get('host-name', '').lower() or
                identificador == dev.get('system-ip', '') or
                identificador == dev.get('uuid', '')):
                device_found = dev
                break
        
        if not device_found:
            return (f"❌ Dispositivo '{identificador}' no encontrado\n\n"
                   f"Verifica el identificador. Puede ser:\n"
                   f"  • Hostname (ej: SDWAN-CJF-318-RT01)\n"
                   f"  • System IP (ej: 10.95.11.3)\n"
                   f"  • Device UUID")
        
        device_id = device_found.get('deviceId') or device_found.get('uuid')
        hostname = device_found.get('host-name', 'Unknown')
        system_ip = device_found.get('system-ip', 'N/A')
        site_id = device_found.get('site-id', 'N/A')
        
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Dispositivo encontrado: {hostname} ({system_ip})", file=sys.stderr)
        
        # Obtener estadísticas de interfaces
        response = vmanage.get(f"/dataservice/device/counters?deviceId={device_id}")
        
        if not response or 'data' not in response:
            return f"❌ No se pudieron obtener estadísticas de interfaces para {hostname}"
        
        interfaces = response['data']
        
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Estadísticas obtenidas: {len(interfaces)} interfaces", file=sys.stderr)
        
        resultado = f"🌐 ESTADÍSTICAS DE INTERFACES - {hostname}\n"
        resultado += f"{'='*120}\n\n"
        resultado += f"Dispositivo:  {hostname}\n"
        resultado += f"System IP:    {system_ip}\n"
        resultado += f"Site ID:      {site_id}\n"
        resultado += f"Device ID:    {device_id}\n"
        resultado += f"Interfaces:   {len(interfaces)}\n"
        resultado += f"Actualizado:  {datetime.fromtimestamp(response.get('header', {}).get('generatedOn', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Clasificar interfaces
        interfaces_up = []
        interfaces_down = []
        interfaces_with_traffic = []
        interfaces_with_errors = []
        
        for iface in interfaces:
            if_oper_status = iface.get('if-oper-status', '')
            rx_octets = iface.get('rx-octets', 0)
            tx_octets = iface.get('tx-octets', 0)
            rx_errors = iface.get('rx-errors', 0) + iface.get('rx-drops', 0)
            tx_errors = iface.get('tx-errors', 0) + iface.get('tx-drops', 0)
            
            total_traffic = rx_octets + tx_octets
            total_errors = rx_errors + tx_errors
            
            if 'ready' in if_oper_status.lower():
                interfaces_up.append(iface)
            else:
                interfaces_down.append(iface)
            
            if total_traffic > 0:
                iface['_total_traffic'] = total_traffic
                interfaces_with_traffic.append(iface)
            
            if total_errors > 0:
                iface['_total_errors'] = total_errors
                interfaces_with_errors.append(iface)
        
        # Resumen
        resultado += f"{'='*120}\n"
        resultado += f"📊 RESUMEN DE ESTADO:\n\n"
        resultado += f"  🟢 Interfaces UP (operativas):     {len(interfaces_up)}\n"
        resultado += f"  🔴 Interfaces DOWN:                {len(interfaces_down)}\n"
        resultado += f"  📈 Interfaces con tráfico:         {len(interfaces_with_traffic)}\n"
        resultado += f"  ⚠️  Interfaces con errores/drops:  {len(interfaces_with_errors)}\n\n"
        
        # Top interfaces por tráfico
        if interfaces_with_traffic:
            interfaces_with_traffic.sort(key=lambda x: x.get('_total_traffic', 0), reverse=True)
            
            resultado += f"{'='*120}\n"
            resultado += f"🔝 TOP {min(top_interfaces, len(interfaces_with_traffic))} INTERFACES POR TRÁFICO:\n\n"
            resultado += f"{'Interface':<20} {'VPN':<5} {'Admin':<8} {'Oper':<8} {'Rx (GB)':<12} {'Tx (GB)':<12} {'Errores':<10} {'IP Address':<18}\n"
            resultado += f"{'-'*120}\n"
            
            for iface in interfaces_with_traffic[:top_interfaces]:
                ifname = iface.get('ifname', 'N/A')
                vpn = iface.get('vpn-id', 'N/A')
                admin_status = '🟢 UP' if 'up' in iface.get('if-admin-status', '').lower() else '🔴 DOWN'
                oper_status = '🟢 UP' if 'ready' in iface.get('if-oper-status', '').lower() else '🔴 DOWN'
                rx_gb = iface.get('rx-octets', 0) / (1024**3)
                tx_gb = iface.get('tx-octets', 0) / (1024**3)
                errors = iface.get('_total_errors', 0)
                ip_addr = iface.get('ip-address', 'N/A')
                
                error_icon = '⚠️ ' if errors > 0 else '  '
                
                resultado += f"{error_icon}{ifname:<18} {vpn:<5} {admin_status:<8} {oper_status:<8} {rx_gb:>10.2f}  {tx_gb:>10.2f}  {errors:<10} {ip_addr:<18}\n"
        
        # Interfaces con errores
        if interfaces_with_errors:
            interfaces_with_errors.sort(key=lambda x: x.get('_total_errors', 0), reverse=True)
            
            resultado += f"\n{'='*120}\n"
            resultado += f"⚠️  INTERFACES CON ERRORES/DESCARTES:\n\n"
            resultado += f"{'Interface':<20} {'VPN':<5} {'Rx Errors':<12} {'Rx Drops':<12} {'Tx Errors':<12} {'Tx Drops':<12} {'Total':<10}\n"
            resultado += f"{'-'*120}\n"
            
            for iface in interfaces_with_errors[:20]:  # Máximo 20 interfaces con errores
                ifname = iface.get('ifname', 'N/A')
                vpn = iface.get('vpn-id', 'N/A')
                rx_errors = iface.get('rx-errors', 0)
                rx_drops = iface.get('rx-drops', 0)
                tx_errors = iface.get('tx-errors', 0)
                tx_drops = iface.get('tx-drops', 0)
                total_errors = iface.get('_total_errors', 0)
                
                resultado += f"{'⚠️ '}{ifname:<18} {vpn:<5} {rx_errors:<12} {rx_drops:<12} {tx_errors:<12} {tx_drops:<12} {total_errors:<10}\n"
        
        # Interfaces Down
        if interfaces_down:
            resultado += f"\n{'='*120}\n"
            resultado += f"🔴 INTERFACES DOWN (No operativas):\n\n"
            resultado += f"{'Interface':<20} {'VPN':<5} {'Admin Status':<15} {'Oper Status':<20} {'IP Address':<18}\n"
            resultado += f"{'-'*120}\n"
            
            for iface in interfaces_down[:30]:  # Máximo 30 interfaces down
                ifname = iface.get('ifname', 'N/A')
                vpn = iface.get('vpn-id', 'N/A')
                admin_status = iface.get('if-admin-status', 'N/A')
                oper_status = iface.get('if-oper-status', 'N/A')
                ip_addr = iface.get('ip-address', 'N/A')
                
                resultado += f"  {ifname:<18} {vpn:<5} {admin_status:<15} {oper_status:<20} {ip_addr:<18}\n"
        
        # Estadísticas totales
        total_rx_gb = sum(iface.get('rx-octets', 0) for iface in interfaces) / (1024**3)
        total_tx_gb = sum(iface.get('tx-octets', 0) for iface in interfaces) / (1024**3)
        total_rx_errors = sum(iface.get('rx-errors', 0) + iface.get('rx-drops', 0) for iface in interfaces)
        total_tx_errors = sum(iface.get('tx-errors', 0) + iface.get('tx-drops', 0) for iface in interfaces)
        
        resultado += f"\n{'='*120}\n"
        resultado += f"📈 ESTADÍSTICAS TOTALES DEL DISPOSITIVO:\n\n"
        resultado += f"  📥 Total recibido (Rx):       {total_rx_gb:>10.2f} GB\n"
        resultado += f"  📤 Total transmitido (Tx):    {total_tx_gb:>10.2f} GB\n"
        resultado += f"  📊 Total tráfico:             {(total_rx_gb + total_tx_gb):>10.2f} GB\n"
        resultado += f"  ⚠️  Total errores Rx:          {total_rx_errors:>10,}\n"
        resultado += f"  ⚠️  Total errores Tx:          {total_tx_errors:>10,}\n"
        
        resultado += f"\n{'='*120}\n"
        resultado += f"💡 NOTAS:\n"
        resultado += f"  • Admin Status: Estado configurado (UP/DOWN)\n"
        resultado += f"  • Oper Status: Estado operativo real\n"
        resultado += f"  • Errores incluyen: rx-errors + rx-drops + tx-errors + tx-drops\n"
        resultado += f"  • Para ver detalles específicos de una interfaz en vManage:\n"
        resultado += f"    Monitor → Network → {hostname} → Interface\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener estadísticas de interfaces: {str(e)}"


if __name__ == "__main__":
    """
    Punto de entrada principal del servidor MCP.
    Primero actualiza las cookies y luego inicia el servidor.
    """
    print(f"\n🚀 INICIANDO SERVIDOR MCP - CISCO SD-WAN MANAGER", file=sys.stderr)
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", file=sys.stderr)
    
    # Iniciar el servidor MCP
    print(f"🎯 Iniciando servidor MCP...\n", file=sys.stderr)
    try:
        mcp.run()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Servidor detenido por el usuario", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error al ejecutar el servidor: {str(e)}", file=sys.stderr)
        sys.exit(1)
