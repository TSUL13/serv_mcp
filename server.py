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

# (ver_aplicaciones_top_red_global ELIMINADA — reemplazada por ver_dpi_red_completa)


# (ver_aplicaciones_agregadas_avanzado ELIMINADA — reemplazada por ver_dpi_red_completa)


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
            # La agregación no tiene datos para este sitio, pero puede haber flujos
            # Intentar obtener flujos detallados via POST
            try:
                payload_flows = {
                    "query": {"condition": "AND", "rules": [
                        {"field": "vdevice_name", "type": "string", "value": system_ips, "operator": "in"}
                    ]},
                    "size": 50
                }
                resp_flows = session.post("/dataservice/statistics/dpi", payload_flows, timeout=30)
                flows = resp_flows.get('data', [])
            except:
                flows = []
            
            if flows:
                # Hay flujos — construir ranking desde los datos crudos
                from collections import defaultdict
                app_agg = defaultdict(lambda: {'bytes': 0, 'packets': 0, 'flows': 0})
                for flow in flows:
                    app_name = flow.get('application', 'unknown')
                    app_agg[app_name]['bytes'] += int(flow.get('octets', 0))
                    app_agg[app_name]['packets'] += int(flow.get('packets', 0))
                    app_agg[app_name]['flows'] += 1
                
                apps_sorted = sorted(app_agg.items(), key=lambda x: x[1]['bytes'], reverse=True)
                total_bytes = sum(a[1]['bytes'] for a in apps_sorted)
                
                resultado += f"📊 Datos de flujos DPI en tiempo real ({len(flows)} flujos)\n"
                resultado += f"📊 Aplicaciones únicas: {len(apps_sorted)} | Tráfico: {fmt_bytes(total_bytes)}\n\n"
                
                resultado += f"{'#':<4} {'APLICACIÓN':<35} {'TRÁFICO':<14} {'%':<8} {'FLUJOS':<10}\n"
                resultado += f"{'-'*75}\n"
                
                for i, (app_name, data) in enumerate(apps_sorted[:top], 1):
                    pct = (data['bytes'] / total_bytes * 100) if total_bytes > 0 else 0
                    if pct >= 10: icon = "🔴"
                    elif pct >= 5: icon = "🟠"
                    elif pct >= 1: icon = "🟡"
                    else: icon = "🟢"
                    resultado += f"{i:<4} {icon} {app_name:<33} {fmt_bytes(data['bytes']):<14} {pct:>5.1f}%  {data['flows']:<10}\n"
                
                resultado += f"\nℹ️  Nota: Datos basados en flujos en tiempo real (no agregación histórica)\n"
                resultado += f"💡 Usa ver_flujos_dpi_detalle(sitio='{site_ids[0]}') para ver IPs y puertos\n"
                return resultado
            
            resultado += f"ℹ️  No se encontraron datos DPI para este sitio en este momento.\n\n"
            resultado += f"Esto puede ocurrir si:\n"
            resultado += f"  • El sitio no tiene Data Policy con clasificación DPI activa\n"
            resultado += f"  • Los datos aún no se han propagado al historial de vManage\n\n"
            resultado += f"💡 HERRAMIENTAS ALTERNATIVAS:\n"
            resultado += f"  • ver_dpi_red_completa() — Ver qué sitios SÍ tienen datos DPI\n"
            resultado += f"  • ver_saturacion_sitio('{site_ids[0]}') — Tráfico real por interfaz WAN\n"
            resultado += f"  • ver_estadisticas_interfaces('{hostnames[0]}') — Estadísticas de interfaces\n"
            return resultado
        
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
        resultado += f"  • ver_flujos_dpi_detalle(sitio='{site_ids[0]}') — Flujos con IPs y puertos\n"
        resultado += f"  • ver_top_consumidores_dpi(aplicacion='youtube') — Quién consume más una app\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener aplicaciones del sitio: {str(e)}"


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


# =====================================================
# HERRAMIENTA 31: VER CALIDAD SAAS POR SITIO (CloudX)
# =====================================================
@mcp.tool()
def ver_calidad_saas_sitios(
    top: int = 30,
    sitio: str = "",
    aplicacion: str = ""
) -> str:
    """
    Muestra la calidad de aplicaciones SaaS (Office 365, Webex, etc.) por sitio,
    usando datos Cloud Express (CloudX) de vManage — la misma información que se ve en Analytics.
    Incluye Score VQE (Video Quality Experience), latencia, pérdida y mejor camino.
    
    Args:
        top: Número de sitios a mostrar en el ranking (default: 30)
        sitio: (Opcional) Filtrar por sitio específico (ej: "51660", "660")
        aplicacion: (Opcional) Filtrar por aplicación (ej: "office365", "webex")
    
    Returns:
        Ranking de sitios por calidad SaaS con scores VQE, latencia y pérdida.
        Incluye resumen por aplicación y detección de sitios con problemas.
    
    Ejemplo:
        ver_calidad_saas_sitios() - Todos los sitios, ranking por peor calidad
        ver_calidad_saas_sitios(sitio="660") - Calidad SaaS de un sitio específico
        ver_calidad_saas_sitios(aplicacion="office365") - Solo Office 365
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo calidad SaaS (CloudX)...", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener datos CloudX (hasta 10000 registros)
        cloudx_result = session.get("/dataservice/statistics/cloudx?count=10000", timeout=60)
        cloudx_data = cloudx_result.get('data', [])
        
        if not cloudx_data:
            return ("❌ No hay datos de Cloud Express (CloudX) disponibles.\n\n"
                    "Esto puede ocurrir si:\n"
                    "  1. Cloud OnRamp/Cloud Express no está habilitado\n"
                    "  2. No hay aplicaciones SaaS siendo monitoreadas\n"
                    "  3. Las políticas de Cloud Express no están desplegadas")
        
        # Filtrar por sitio si se especificó
        if sitio:
            sitio_lower = sitio.strip().lower()
            cloudx_data = [item for item in cloudx_data
                           if sitio_lower in str(item.get('site_id', '')).lower()
                           or sitio_lower in item.get('host_name', '').lower()]
            if not cloudx_data:
                return f"❌ No se encontraron datos CloudX para el sitio '{sitio}'."
        
        # Filtrar por aplicación si se especificó
        if aplicacion:
            app_lower = aplicacion.strip().lower()
            cloudx_data = [item for item in cloudx_data
                           if app_lower in item.get('application', '').lower()
                           or app_lower in item.get('nbar_app_group_name', '').lower()]
            if not cloudx_data:
                return f"❌ No se encontraron datos CloudX para la aplicación '{aplicacion}'."
        
        def fmt_score(score):
            """Formatea el score VQE con icono de calidad."""
            try:
                s = float(score)
            except (ValueError, TypeError):
                return "  -  "
            if s >= 8: return f"🟢 {s:.1f}"
            if s >= 5: return f"🟡 {s:.1f}"
            if s >= 3: return f"🟠 {s:.1f}"
            return f"🔴 {s:.1f}"
        
        # ===== ANÁLISIS POR SITIO =====
        from collections import defaultdict
        site_stats = defaultdict(lambda: {
            'total_score': 0.0, 'total_latency': 0.0, 'total_loss': 0.0,
            'count': 0, 'best_paths': 0, 'hostname': '', 'apps': set()
        })
        
        for item in cloudx_data:
            sid = str(item.get('site_id', '?'))
            try:
                site_stats[sid]['total_score'] += float(item.get('vqe_score', 0))
                site_stats[sid]['total_latency'] += float(item.get('latency', 0))
                site_stats[sid]['total_loss'] += float(item.get('loss', 0))
            except (ValueError, TypeError):
                pass
            site_stats[sid]['count'] += 1
            if item.get('best_path') == 'TRUE':
                site_stats[sid]['best_paths'] += 1
            site_stats[sid]['hostname'] = item.get('host_name', '')
            site_stats[sid]['apps'].add(item.get('application', ''))
        
        # Ordenar por peor score (ascendente)
        sites_ranked = sorted(site_stats.items(),
                              key=lambda x: x[1]['total_score'] / max(x[1]['count'], 1))
        
        total_sites = len(sites_ranked)
        
        # ===== ANÁLISIS POR APLICACIÓN =====
        app_stats = defaultdict(lambda: {
            'total_score': 0.0, 'total_latency': 0.0, 'total_loss': 0.0,
            'count': 0, 'best_paths': 0, 'group': ''
        })
        
        for item in cloudx_data:
            app = item.get('application', '?')
            try:
                app_stats[app]['total_score'] += float(item.get('vqe_score', 0))
                app_stats[app]['total_latency'] += float(item.get('latency', 0))
                app_stats[app]['total_loss'] += float(item.get('loss', 0))
            except (ValueError, TypeError):
                pass
            app_stats[app]['count'] += 1
            if item.get('best_path') == 'TRUE':
                app_stats[app]['best_paths'] += 1
            app_stats[app]['group'] = item.get('nbar_app_group_name', '')
        
        # ===== CONSTRUIR RESULTADO =====
        resultado = f"🌐 CALIDAD DE APLICACIONES SaaS (Cloud Express)\n"
        resultado += f"{'='*130}\n\n"
        resultado += f"📊 Registros analizados: {len(cloudx_data):,}\n"
        resultado += f"📡 Sitios con datos: {total_sites}\n"
        resultado += f"📱 Aplicaciones monitoreadas: {len(app_stats)}\n"
        if sitio:
            resultado += f"🔎 Filtro sitio: '{sitio}'\n"
        if aplicacion:
            resultado += f"🔎 Filtro aplicación: '{aplicacion}'\n"
        
        # Detectar sitios con problemas
        problem_sites = [s for s, stats in sites_ranked
                         if stats['total_score'] / max(stats['count'], 1) < 5.0]
        if problem_sites:
            resultado += f"\n⚠️  SITIOS CON CALIDAD DEFICIENTE (VQE < 5.0): {len(problem_sites)}\n"
        
        # Tabla de sitios
        resultado += f"\n{'='*130}\n"
        resultado += f"📋 RANKING DE SITIOS (ordenado por peor calidad):\n\n"
        resultado += f"{'#':<4} {'SITIO':<10} {'DISPOSITIVO':<35} {'VQE SCORE':<12} {'LATENCIA':<14} {'PÉRDIDA':<10} {'APPS':<6} {'MUESTRAS':<10}\n"
        resultado += f"{'-'*105}\n"
        
        for i, (sid, stats) in enumerate(sites_ranked[:top], 1):
            n = max(stats['count'], 1)
            avg_score = stats['total_score'] / n
            avg_lat = stats['total_latency'] / n
            avg_loss = stats['total_loss'] / n
            
            resultado += (f"{i:<4} {sid:<10} {stats['hostname']:<35} "
                         f"{fmt_score(avg_score):<12} {avg_lat:>8.1f} ms   "
                         f"{avg_loss:>5.1f}%    {len(stats['apps']):<6} {stats['count']:<10}\n")
        
        if len(sites_ranked) > top:
            resultado += f"\n     ... y {len(sites_ranked) - top} sitios más\n"
        
        # Tabla de aplicaciones
        apps_ranked = sorted(app_stats.items(),
                             key=lambda x: x[1]['total_score'] / max(x[1]['count'], 1))
        
        resultado += f"\n{'='*130}\n"
        resultado += f"📱 CALIDAD POR APLICACIÓN:\n\n"
        resultado += f"{'#':<4} {'APLICACIÓN':<45} {'GRUPO':<20} {'VQE SCORE':<12} {'LATENCIA':<14} {'PÉRDIDA':<10} {'BEST PATH':<10}\n"
        resultado += f"{'-'*120}\n"
        
        for i, (app, stats) in enumerate(apps_ranked, 1):
            n = max(stats['count'], 1)
            avg_score = stats['total_score'] / n
            avg_lat = stats['total_latency'] / n
            avg_loss = stats['total_loss'] / n
            bp_pct = (stats['best_paths'] / n * 100) if n > 0 else 0
            
            resultado += (f"{i:<4} {app:<45} {stats['group']:<20} "
                         f"{fmt_score(avg_score):<12} {avg_lat:>8.1f} ms   "
                         f"{avg_loss:>5.1f}%    {bp_pct:>5.1f}%\n")
        
        # Detalle de sitio específico
        if sitio and len(sites_ranked) <= 5:
            resultado += f"\n{'='*130}\n"
            resultado += f"📋 DETALLE POR APLICACIÓN EN EL SITIO:\n\n"
            
            site_app_detail = defaultdict(lambda: {
                'total_score': 0.0, 'total_latency': 0.0, 'total_loss': 0.0,
                'count': 0, 'best_path_iface': '', 'exit_type': ''
            })
            
            for item in cloudx_data:
                app = item.get('application', '?')
                try:
                    site_app_detail[app]['total_score'] += float(item.get('vqe_score', 0))
                    site_app_detail[app]['total_latency'] += float(item.get('latency', 0))
                    site_app_detail[app]['total_loss'] += float(item.get('loss', 0))
                except (ValueError, TypeError):
                    pass
                site_app_detail[app]['count'] += 1
                if item.get('best_path') == 'TRUE':
                    site_app_detail[app]['best_path_iface'] = item.get('interface', '')
                    site_app_detail[app]['exit_type'] = item.get('exit_type', '')
            
            resultado += f"{'APLICACIÓN':<45} {'VQE':<10} {'LATENCIA':<14} {'PÉRDIDA':<10} {'BEST PATH':<20} {'SALIDA':<10}\n"
            resultado += f"{'-'*110}\n"
            
            for app, stats in sorted(site_app_detail.items(),
                                      key=lambda x: x[1]['total_score'] / max(x[1]['count'], 1)):
                n = max(stats['count'], 1)
                avg_score = stats['total_score'] / n
                avg_lat = stats['total_latency'] / n
                avg_loss = stats['total_loss'] / n
                resultado += (f"{app:<45} {fmt_score(avg_score):<10} {avg_lat:>8.1f} ms   "
                             f"{avg_loss:>5.1f}%    {stats['best_path_iface']:<20} {stats['exit_type']:<10}\n")
        
        resultado += f"\n{'='*130}\n"
        resultado += f"💡 NOTAS:\n"
        resultado += f"  • VQE Score: 0-10 (10=excelente, <5=problemas)\n"
        resultado += f"  • 🟢 ≥8 (bueno) | 🟡 5-7 (aceptable) | 🟠 3-4 (degradado) | 🔴 <3 (crítico)\n"
        resultado += f"  • Datos de Cloud Express — mismas métricas que Analytics\n"
        resultado += f"  • Best Path: interfaz con mejor calidad seleccionada por SD-WAN\n\n"
        resultado += f"💡 HERRAMIENTAS RELACIONADAS:\n"
        resultado += f"  • ver_calidad_saas_sitios(sitio='51660') — Detalle de un sitio\n"
        resultado += f"  • ver_calidad_saas_sitios(aplicacion='office365') — Solo Office 365\n"
        resultado += f"  • ver_saturacion_sitio('660') — Saturación de enlaces del sitio\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener calidad SaaS: {str(e)}"


# =====================================================
# HERRAMIENTA 32: VER DROPS QoS POR SITIO
# =====================================================
@mcp.tool()
def ver_drops_qos(
    top: int = 30,
    sitio: str = "",
    queue: str = ""
) -> str:
    """
    Muestra los drops de QoS (Quality of Service) por dispositivo y cola de prioridad.
    Detecta sitios con congestión real donde se están descartando paquetes.
    Usa las mismas estadísticas que Analytics para detectar degradación de servicio.
    
    Args:
        top: Número de dispositivos a mostrar en el ranking (default: 30)
        sitio: (Opcional) Filtrar por sitio o hostname (ej: "944", "SDWAN-CJF-407-RT01")
        queue: (Opcional) Filtrar por cola específica (ej: "Queue0", "Queue2")
    
    Returns:
        Ranking de dispositivos con más drops QoS, detalle por cola, y detección de congestión.
    
    Ejemplo:
        ver_drops_qos() - Todos los dispositivos, ranking por más drops
        ver_drops_qos(sitio="944") - Drops QoS de un sitio específico
        ver_drops_qos(queue="Queue0") - Solo cola de prioridad (voz/video)
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo estadísticas QoS...", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener datos QoS (hasta 10000 registros)
        qos_result = session.get("/dataservice/statistics/qos?count=10000", timeout=60)
        qos_data = qos_result.get('data', [])
        
        if not qos_data:
            return ("❌ No hay datos de QoS disponibles.\n\n"
                    "Esto puede ocurrir si:\n"
                    "  1. No hay políticas QoS aplicadas\n"
                    "  2. Los dispositivos no reportan estadísticas QoS\n"
                    "  3. Problema de conexión con vManage")
        
        # Filtrar por sitio si se especificó
        if sitio:
            sitio_lower = sitio.strip().lower()
            qos_data = [item for item in qos_data
                        if sitio_lower in item.get('host_name', '').lower()
                        or sitio_lower in str(item.get('vdevice_name', '')).lower()]
            if not qos_data:
                return f"❌ No se encontraron datos QoS para el sitio '{sitio}'."
        
        # Filtrar por queue si se especificó
        if queue:
            queue_lower = queue.strip().lower()
            qos_data = [item for item in qos_data
                        if queue_lower in item.get('queue_name', '').lower()]
            if not qos_data:
                return f"❌ No se encontraron datos QoS para la cola '{queue}'."
        
        def fmt_bytes(b):
            if b > 1024**4: return f"{b / (1024**4):.1f} TB"
            if b > 1024**3: return f"{b / (1024**3):.1f} GB"
            if b > 1024**2: return f"{b / (1024**2):.1f} MB"
            if b > 1024: return f"{b / 1024:.1f} KB"
            return f"{b} B"
        
        from collections import defaultdict
        
        # ===== ANÁLISIS POR QUEUE (global) =====
        queue_totals = defaultdict(lambda: {'tx_bytes': 0, 'drop_bytes': 0, 'drop_pkts': 0, 'count': 0})
        
        for item in qos_data:
            q = item.get('queue_name', '?')
            if q == 'Aggregate':
                continue  # Saltar el agregado
            queue_totals[q]['tx_bytes'] += int(item.get('tx_bytes', 0))
            queue_totals[q]['drop_bytes'] += int(item.get('drop_in_bytes', 0))
            queue_totals[q]['drop_pkts'] += int(item.get('drop_in_pkts', 0))
            queue_totals[q]['count'] += 1
        
        # ===== ANÁLISIS POR DISPOSITIVO =====
        dev_stats = defaultdict(lambda: {
            'tx_bytes': 0, 'drop_bytes': 0, 'drop_pkts': 0,
            'hostname': '', 'interface': '', 'queues': defaultdict(lambda: {'tx': 0, 'drop': 0, 'drop_pkts': 0})
        })
        
        for item in qos_data:
            q = item.get('queue_name', '?')
            if q == 'Aggregate':
                continue
            dev_ip = item.get('vdevice_name', '?')
            dev_stats[dev_ip]['tx_bytes'] += int(item.get('tx_bytes', 0))
            dev_stats[dev_ip]['drop_bytes'] += int(item.get('drop_in_bytes', 0))
            dev_stats[dev_ip]['drop_pkts'] += int(item.get('drop_in_pkts', 0))
            dev_stats[dev_ip]['hostname'] = item.get('host_name', '')
            dev_stats[dev_ip]['interface'] = item.get('interface', '')
            dev_stats[dev_ip]['queues'][q]['tx'] += int(item.get('tx_bytes', 0))
            dev_stats[dev_ip]['queues'][q]['drop'] += int(item.get('drop_in_bytes', 0))
            dev_stats[dev_ip]['queues'][q]['drop_pkts'] += int(item.get('drop_in_pkts', 0))
        
        # Ordenar por más drops
        devs_ranked = sorted(dev_stats.items(),
                             key=lambda x: x[1]['drop_bytes'], reverse=True)
        
        total_devs = len(devs_ranked)
        total_drops = sum(s['drop_bytes'] for _, s in devs_ranked)
        total_tx = sum(s['tx_bytes'] for _, s in devs_ranked)
        
        # ===== CONSTRUIR RESULTADO =====
        resultado = f"📊 DROPS DE QoS POR DISPOSITIVO\n"
        resultado += f"{'='*130}\n\n"
        resultado += f"📦 Registros analizados: {len(qos_data):,}\n"
        resultado += f"📡 Dispositivos: {total_devs}\n"
        resultado += f"📈 Tráfico total: {fmt_bytes(total_tx)} | Drops totales: {fmt_bytes(total_drops)}"
        if total_tx > 0:
            resultado += f" ({total_drops/total_tx*100:.3f}%)"
        resultado += "\n"
        if sitio:
            resultado += f"🔎 Filtro sitio: '{sitio}'\n"
        if queue:
            resultado += f"🔎 Filtro cola: '{queue}'\n"
        
        # Detectar congestión severa
        congested = [(dev, s) for dev, s in devs_ranked
                     if s['tx_bytes'] > 0 and s['drop_bytes'] / s['tx_bytes'] > 0.01]
        if congested:
            resultado += f"\n🚨 DISPOSITIVOS CON CONGESTIÓN (>1% drops): {len(congested)}\n"
            for dev, s in congested:
                pct = s['drop_bytes'] / s['tx_bytes'] * 100
                resultado += f"   ⚠️  {s['hostname']}: {pct:.2f}% drops ({fmt_bytes(s['drop_bytes'])})\n"
        
        # Tabla resumen por queue
        resultado += f"\n{'='*130}\n"
        resultado += f"📋 RESUMEN POR COLA DE PRIORIDAD:\n\n"
        resultado += f"{'COLA':<15} {'TX TOTAL':<15} {'DROPS':<15} {'DROP PKTS':<15} {'%DROP':<10} {'PRIORIDAD':<30}\n"
        resultado += f"{'-'*100}\n"
        
        queue_names_info = {
            'Queue0': 'Realtime (Voz/Video)',
            'Queue1': 'Interactive (Señalización)',
            'Queue2': 'Default (Datos)',
            'Queue3': 'Bulk (Transferencia)',
            'Queue4': 'Best Effort',
            'Queue5': 'Control/Management',
            'Queue6': 'Scavenger',
            'Queue7': 'Network Control'
        }
        
        for q, stats in sorted(queue_totals.items()):
            pct = (stats['drop_bytes'] / stats['tx_bytes'] * 100) if stats['tx_bytes'] > 0 else 0
            icon = "🔴" if pct > 0.5 else "🟠" if pct > 0.1 else "🟡" if pct > 0 else "🟢"
            info = queue_names_info.get(q, '')
            resultado += (f"{icon} {q:<13} {fmt_bytes(stats['tx_bytes']):<15} "
                         f"{fmt_bytes(stats['drop_bytes']):<15} {stats['drop_pkts']:>12,}   "
                         f"{pct:>6.3f}%   {info}\n")
        
        # Ranking de dispositivos
        resultado += f"\n{'='*130}\n"
        resultado += f"📋 RANKING DE DISPOSITIVOS (por más drops):\n\n"
        resultado += f"{'#':<4} {'DISPOSITIVO':<35} {'INTERFAZ':<25} {'TX':<15} {'DROPS':<15} {'DROP PKTS':<12} {'%DROP':<8}\n"
        resultado += f"{'-'*120}\n"
        
        for i, (dev_ip, stats) in enumerate(devs_ranked[:top], 1):
            pct = (stats['drop_bytes'] / stats['tx_bytes'] * 100) if stats['tx_bytes'] > 0 else 0
            icon = "🔴" if pct > 1 else "🟠" if pct > 0.1 else "🟡" if pct > 0 else "🟢"
            
            resultado += (f"{i:<4} {icon} {stats['hostname']:<33} {stats['interface']:<25} "
                         f"{fmt_bytes(stats['tx_bytes']):<15} {fmt_bytes(stats['drop_bytes']):<15} "
                         f"{stats['drop_pkts']:>10,}   {pct:>5.2f}%\n")
            
            # Si se filtra por sitio, mostrar detalle por queue
            if sitio and stats['drop_bytes'] > 0:
                for q, qs in sorted(stats['queues'].items()):
                    if qs['drop'] > 0:
                        q_pct = (qs['drop'] / qs['tx'] * 100) if qs['tx'] > 0 else 0
                        q_info = queue_names_info.get(q, '')
                        resultado += (f"     └─ {q} ({q_info}): "
                                     f"TX={fmt_bytes(qs['tx'])}, "
                                     f"Drops={fmt_bytes(qs['drop'])} ({q_pct:.2f}%), "
                                     f"{qs['drop_pkts']:,} pkts\n")
        
        if len(devs_ranked) > top:
            resultado += f"\n     ... y {len(devs_ranked) - top} dispositivos más\n"
        
        resultado += f"\n{'='*130}\n"
        resultado += f"💡 NOTAS:\n"
        resultado += f"  • Queue0 = tráfico de voz/video (prioritario) — drops aquí = problemas de calidad\n"
        resultado += f"  • Queue2 = tráfico de datos (default) — drops normales bajo congestión\n"
        resultado += f"  • >1% drops = congestión severa | >0.1% = congestión moderada\n"
        resultado += f"  • Datos de estadísticas QoS de vManage — misma fuente que Analytics\n\n"
        resultado += f"💡 HERRAMIENTAS RELACIONADAS:\n"
        resultado += f"  • ver_drops_qos(sitio='944') — Detalle de drops de un sitio\n"
        resultado += f"  • ver_drops_qos(queue='Queue0') — Solo cola de voz/video\n"
        resultado += f"  • ver_saturacion_sitio('944') — Saturación de enlaces del sitio\n"
        resultado += f"  • ver_calidad_saas_sitios() — Calidad de aplicaciones SaaS\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener drops QoS: {str(e)}"


# =====================================================
# HERRAMIENTA 33: VER SLA DE TÚNELES (Approute)
# =====================================================
@mcp.tool()
def ver_sla_tuneles(
    top: int = 30,
    sitio: str = "",
    color: str = ""
) -> str:
    """
    Muestra el SLA (Service Level Agreement) de los túneles SD-WAN: latencia, jitter y pérdida de paquetes.
    Usa estadísticas Approute de vManage para mostrar la calidad de cada enlace por color
    (MPLS/private1, Internet/gold, silver, etc.) — mismos datos que Analytics.
    
    Args:
        top: Número de túneles o dispositivos a mostrar (default: 30)
        sitio: (Opcional) Filtrar por sitio o hostname (ej: "720", "SDWAN-CJF-720-RT01")
        color: (Opcional) Filtrar por color de enlace (ej: "gold", "private1", "silver")
    
    Returns:
        Ranking de túneles por peor SLA con latencia, jitter, pérdida y score VQoE.
        Incluye resumen por tipo de enlace (color) y detección de túneles degradados.
    
    Ejemplo:
        ver_sla_tuneles() - Todos los túneles, ranking por peor SLA
        ver_sla_tuneles(sitio="720") - SLA de túneles de un sitio
        ver_sla_tuneles(color="gold") - Solo túneles por Internet
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo SLA de túneles (Approute)...", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener datos Approute (hasta 10000 registros)
        approute_result = session.get("/dataservice/statistics/approute?count=10000", timeout=60)
        approute_data = approute_result.get('data', [])
        
        if not approute_data:
            return ("❌ No hay datos de Approute disponibles.\n\n"
                    "Esto puede ocurrir si:\n"
                    "  1. Los túneles SD-WAN no están activos\n"
                    "  2. BFD/Approute no está habilitado\n"
                    "  3. Problema de conexión con vManage")
        
        # Filtrar por sitio si se especificó
        if sitio:
            sitio_lower = sitio.strip().lower()
            approute_data = [item for item in approute_data
                            if sitio_lower in item.get('host_name', '').lower()
                            or sitio_lower in str(item.get('siteid', '')).lower()
                            or sitio_lower in str(item.get('vdevice_name', '')).lower()]
            if not approute_data:
                return f"❌ No se encontraron datos Approute para el sitio '{sitio}'."
        
        # Filtrar por color si se especificó
        if color:
            color_lower = color.strip().lower()
            approute_data = [item for item in approute_data
                            if color_lower in item.get('local_color', '').lower()
                            or color_lower in item.get('remote_color', '').lower()
                            or color_lower in item.get('tunnel_color', '').lower()]
            if not approute_data:
                return f"❌ No se encontraron datos Approute para el color '{color}'."
        
        from collections import defaultdict
        
        # ===== ANÁLISIS POR COLOR DE ENLACE =====
        color_stats = defaultdict(lambda: {
            'total_lat': 0.0, 'total_jit': 0.0, 'total_loss': 0.0,
            'total_score': 0.0, 'count': 0
        })
        
        for item in approute_data:
            tc = item.get('tunnel_color', '?')
            try:
                color_stats[tc]['total_lat'] += float(item.get('latency', 0))
                color_stats[tc]['total_jit'] += float(item.get('jitter', 0))
                color_stats[tc]['total_loss'] += float(item.get('loss_percentage', 0))
                color_stats[tc]['total_score'] += float(item.get('vqoe_score', 0))
            except (ValueError, TypeError):
                pass
            color_stats[tc]['count'] += 1
        
        # ===== ANÁLISIS POR DISPOSITIVO =====
        dev_stats = defaultdict(lambda: {
            'total_lat': 0.0, 'total_jit': 0.0, 'total_loss': 0.0,
            'total_score': 0.0, 'count': 0, 'hostname': '', 'site_id': '',
            'tunnels': defaultdict(lambda: {
                'total_lat': 0.0, 'total_jit': 0.0, 'total_loss': 0.0,
                'total_score': 0.0, 'count': 0, 'state': '', 'sla_names': ''
            })
        })
        
        for item in approute_data:
            dev_ip = item.get('vdevice_name', '?')
            tc = item.get('tunnel_color', '?')
            try:
                lat = float(item.get('latency', 0))
                jit = float(item.get('jitter', 0))
                loss = float(item.get('loss_percentage', 0))
                score = float(item.get('vqoe_score', 0))
            except (ValueError, TypeError):
                continue
            
            dev_stats[dev_ip]['total_lat'] += lat
            dev_stats[dev_ip]['total_jit'] += jit
            dev_stats[dev_ip]['total_loss'] += loss
            dev_stats[dev_ip]['total_score'] += score
            dev_stats[dev_ip]['count'] += 1
            dev_stats[dev_ip]['hostname'] = item.get('host_name', '')
            dev_stats[dev_ip]['site_id'] = str(item.get('siteid', ''))
            
            dev_stats[dev_ip]['tunnels'][tc]['total_lat'] += lat
            dev_stats[dev_ip]['tunnels'][tc]['total_jit'] += jit
            dev_stats[dev_ip]['tunnels'][tc]['total_loss'] += loss
            dev_stats[dev_ip]['tunnels'][tc]['total_score'] += score
            dev_stats[dev_ip]['tunnels'][tc]['count'] += 1
            dev_stats[dev_ip]['tunnels'][tc]['state'] = item.get('state', '')
            dev_stats[dev_ip]['tunnels'][tc]['sla_names'] = item.get('sla_class_names', '')
        
        # Ordenar dispositivos por peor latencia promedio
        devs_ranked = sorted(dev_stats.items(),
                             key=lambda x: x[1]['total_lat'] / max(x[1]['count'], 1),
                             reverse=True)
        
        total_devs = len(devs_ranked)
        total_tunnels = sum(len(s['tunnels']) for _, s in devs_ranked)
        
        def fmt_score(score):
            if score >= 8: return f"🟢 {score:.1f}"
            if score >= 5: return f"🟡 {score:.1f}"
            if score >= 3: return f"🟠 {score:.1f}"
            return f"🔴 {score:.1f}"
        
        # ===== CONSTRUIR RESULTADO =====
        resultado = f"🔗 SLA DE TÚNELES SD-WAN (Approute)\n"
        resultado += f"{'='*140}\n\n"
        resultado += f"📦 Registros analizados: {len(approute_data):,}\n"
        resultado += f"📡 Dispositivos: {total_devs} | Túneles: {total_tunnels}\n"
        if sitio:
            resultado += f"🔎 Filtro sitio: '{sitio}'\n"
        if color:
            resultado += f"🔎 Filtro color: '{color}'\n"
        
        # Detectar túneles degradados
        degraded = []
        for dev_ip, stats in devs_ranked:
            n = max(stats['count'], 1)
            avg_loss = stats['total_loss'] / n
            avg_lat = stats['total_lat'] / n
            if avg_loss > 1.0 or avg_lat > 100:
                degraded.append((stats['hostname'], avg_lat, avg_loss))
        
        if degraded:
            resultado += f"\n⚠️  DISPOSITIVOS CON SLA DEGRADADO: {len(degraded)}\n"
            for hostname, lat, loss in degraded[:10]:
                resultado += f"   🔴 {hostname}: {lat:.0f}ms latencia, {loss:.2f}% pérdida\n"
        
        # Tabla resumen por color
        resultado += f"\n{'='*140}\n"
        resultado += f"📋 SLA PROMEDIO POR TIPO DE ENLACE:\n\n"
        resultado += f"{'COLOR TÚNEL':<30} {'LATENCIA':<14} {'JITTER':<12} {'PÉRDIDA':<10} {'VQoE':<10} {'MUESTRAS':<10}\n"
        resultado += f"{'-'*90}\n"
        
        color_names = {
            'private1:private1': 'MPLS → MPLS',
            'gold:gold': 'Internet → Internet',
            'gold:silver': 'Internet → Internet(B)',
            'silver:silver': 'Internet(B) → Internet(B)',
            'silver:gold': 'Internet(B) → Internet',
            'private1:gold': 'MPLS → Internet',
            'gold:private1': 'Internet → MPLS',
        }
        
        for tc, stats in sorted(color_stats.items(),
                                key=lambda x: x[1]['total_lat'] / max(x[1]['count'], 1),
                                reverse=True):
            n = max(stats['count'], 1)
            avg_lat = stats['total_lat'] / n
            avg_jit = stats['total_jit'] / n
            avg_loss = stats['total_loss'] / n
            avg_score = stats['total_score'] / n
            
            icon = "🔴" if avg_loss > 1 else "🟠" if avg_loss > 0.5 else "🟡" if avg_lat > 50 else "🟢"
            label = color_names.get(tc, tc)
            resultado += (f"{icon} {label:<28} {avg_lat:>8.1f} ms   {avg_jit:>7.1f} ms  "
                         f"{avg_loss:>6.3f}%   {fmt_score(avg_score):<10} {stats['count']:>6}\n")
        
        # Ranking de dispositivos
        resultado += f"\n{'='*140}\n"
        resultado += f"📋 RANKING DE DISPOSITIVOS (ordenado por peor latencia):\n\n"
        resultado += f"{'#':<4} {'DISPOSITIVO':<35} {'SITIO':<10} {'LATENCIA':<14} {'JITTER':<12} {'PÉRDIDA':<10} {'VQoE':<10} {'TÚNELES':<8}\n"
        resultado += f"{'-'*105}\n"
        
        for i, (dev_ip, stats) in enumerate(devs_ranked[:top], 1):
            n = max(stats['count'], 1)
            avg_lat = stats['total_lat'] / n
            avg_jit = stats['total_jit'] / n
            avg_loss = stats['total_loss'] / n
            avg_score = stats['total_score'] / n
            
            icon = "🔴" if avg_loss > 1 else "🟠" if avg_loss > 0.5 else "🟡" if avg_lat > 50 else "🟢"
            
            resultado += (f"{i:<4} {icon} {stats['hostname']:<33} {stats['site_id']:<10} "
                         f"{avg_lat:>8.1f} ms   {avg_jit:>7.1f} ms  "
                         f"{avg_loss:>6.3f}%   {fmt_score(avg_score):<10} {len(stats['tunnels']):>4}\n")
            
            # Si se filtra por sitio, mostrar detalle por túnel
            if sitio:
                for tc, ts in sorted(stats['tunnels'].items(),
                                      key=lambda x: x[1]['total_lat'] / max(x[1]['count'], 1),
                                      reverse=True):
                    tn = max(ts['count'], 1)
                    t_lat = ts['total_lat'] / tn
                    t_jit = ts['total_jit'] / tn
                    t_loss = ts['total_loss'] / tn
                    t_score = ts['total_score'] / tn
                    t_state = ts['state']
                    
                    label = color_names.get(tc, tc)
                    state_icon = "✅" if t_state == 'Up' else "❌"
                    resultado += (f"     └─ {label:<25} {state_icon} "
                                 f"lat={t_lat:.1f}ms  jit={t_jit:.1f}ms  "
                                 f"loss={t_loss:.3f}%  score={fmt_score(t_score)}\n")
        
        if len(devs_ranked) > top:
            resultado += f"\n     ... y {len(devs_ranked) - top} dispositivos más\n"
        
        # SLA classes disponibles
        sla_names = set()
        for item in approute_data:
            names = item.get('sla_class_names', '')
            if names:
                for name in names.split(','):
                    name = name.strip()
                    if name and name != '__all_tunnels__':
                        sla_names.add(name)
        
        resultado += f"\n{'='*140}\n"
        resultado += f"💡 NOTAS:\n"
        resultado += f"  • Latencia: <50ms bueno | 50-100ms aceptable | >100ms degradado\n"
        resultado += f"  • Pérdida: <0.1% bueno | 0.1-1% aceptable | >1% problema\n"
        resultado += f"  • VQoE: 0-10 (10=excelente, <5=problemas)\n"
        resultado += f"  • Datos Approute de vManage — misma fuente que Analytics\n"
        if sla_names:
            resultado += f"  • SLA Classes configuradas: {', '.join(sorted(sla_names))}\n"
        resultado += f"\n💡 HERRAMIENTAS RELACIONADAS:\n"
        resultado += f"  • ver_sla_tuneles(sitio='720') — Detalle SLA de un sitio\n"
        resultado += f"  • ver_sla_tuneles(color='gold') — Solo túneles por Internet\n"
        resultado += f"  • ver_drops_qos() — Drops de QoS por dispositivo\n"
        resultado += f"  • ver_calidad_saas_sitios() — Calidad de Office 365 / Webex\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener SLA de túneles: {str(e)}"


# =====================================================
# HERRAMIENTA 34: DPI RED COMPLETA — Top apps/familias
# =====================================================
@mcp.tool()
def ver_dpi_red_completa(
    top: int = 40,
    familia: str = "",
    horas: int = 24
) -> str:
    """
    Análisis DPI de TODA la red SD-WAN — muestra las aplicaciones que más ancho de banda consumen
    en todos los sitios, con ranking por tráfico, familias, y distribución por sitio.
    Usa la API de agregación que es la misma fuente de datos que Analytics/vAnalytics.

    Args:
        top: Número de aplicaciones a mostrar en el ranking (default: 40)
        familia: (Opcional) Filtrar por familia de aplicación (ej: "web", "audio-video", "encrypted", "tunneling")
        horas: Ventana de tiempo en horas (default: 24, máx 720 = 30 días)

    Returns:
        Ranking global de aplicaciones por consumo, resumen por familia, y top sitios por tráfico.
        Incluye detección de aplicaciones no deseadas (torrent, tor, etc.)

    Ejemplo:
        ver_dpi_red_completa() — Top 40 apps de toda la red (últimas 24h)
        ver_dpi_red_completa(top=20, familia="audio-video") — Solo audio/video
        ver_dpi_red_completa(horas=168) — Última semana
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Analizando DPI de toda la red ({horas}h)...", file=sys.stderr)
        from collections import defaultdict

        session = get_vmanage_session()

        def fmt_bytes(b):
            try: b = int(b)
            except: return str(b)
            if b > 1024**4: return f"{b / (1024**4):.2f} TB"
            if b > 1024**3: return f"{b / (1024**3):.2f} GB"
            if b > 1024**2: return f"{b / (1024**2):.1f} MB"
            if b > 1024: return f"{b / 1024:.1f} KB"
            return f"{b} B"

        # Limitar horas
        horas = max(1, min(horas, 720))

        # ── 1. Aplicaciones globales ──
        payload_apps = {
            "query": {"condition": "AND", "rules": []},
            "aggregation": {
                "field": [{"property": "application", "size": 500, "sequence": 1}],
                "metrics": [
                    {"property": "octets", "type": "sum"},
                    {"property": "packets", "type": "sum"}
                ]
            }
        }
        if horas != 24:
            payload_apps["query"]["rules"].append(
                {"field": "entry_time", "type": "date", "value": [str(horas)], "operator": "last_n_hours"}
            )

        resp_apps = session.post("/dataservice/statistics/dpi/aggregation", payload_apps, timeout=60)
        apps_data = resp_apps.get('data', [])

        if not apps_data:
            return ("❌ No hay datos DPI de agregación disponibles para la red.\n\n"
                    "Posibles causas:\n"
                    "  1. DPI/NBAR no está habilitado en los dispositivos\n"
                    "  2. No hay Data Policy aplicada para clasificación\n"
                    "  3. Los dispositivos no envían estadísticas a vManage")

        # ── 2. Familias globales ──
        payload_fam = {
            "query": {"condition": "AND", "rules": []},
            "aggregation": {
                "field": [{"property": "family", "size": 100, "sequence": 1}],
                "metrics": [
                    {"property": "octets", "type": "sum"},
                    {"property": "packets", "type": "sum"}
                ]
            }
        }
        if horas != 24:
            payload_fam["query"]["rules"].append(
                {"field": "entry_time", "type": "date", "value": [str(horas)], "operator": "last_n_hours"}
            )

        resp_fam = session.post("/dataservice/statistics/dpi/aggregation", payload_fam, timeout=60)
        fam_data = resp_fam.get('data', [])

        # ── 3. Top sitios (por vdevice_name agrupado) ──
        payload_sites = {
            "query": {"condition": "AND", "rules": []},
            "aggregation": {
                "field": [{"property": "vdevice_name", "size": 400, "sequence": 1}],
                "metrics": [
                    {"property": "octets", "type": "sum"},
                    {"property": "packets", "type": "sum"}
                ]
            }
        }
        if horas != 24:
            payload_sites["query"]["rules"].append(
                {"field": "entry_time", "type": "date", "value": [str(horas)], "operator": "last_n_hours"}
            )

        resp_sites = session.post("/dataservice/statistics/dpi/aggregation", payload_sites, timeout=60)
        sites_data = resp_sites.get('data', [])

        # Mapear system_ip → hostname + site_id
        devices_result = session.get("/dataservice/device")
        dev_map = {}
        for dev in devices_result.get('data', []):
            sip = dev.get('system-ip', '')
            dev_map[sip] = {
                'hostname': dev.get('host-name', sip),
                'site_id': str(dev.get('site-id', 'N/A'))
            }

        # ── Filtrar por familia si se especificó ──
        if familia:
            fam_lower = familia.strip().lower()
            # Necesitamos mapeo app→family
            payload_app_fam = {
                "query": {"condition": "AND", "rules": []},
                "aggregation": {
                    "field": [
                        {"property": "application", "size": 500, "sequence": 1},
                        {"property": "family", "size": 1, "sequence": 2}
                    ],
                    "metrics": [{"property": "octets", "type": "sum"}]
                }
            }
            if horas != 24:
                payload_app_fam["query"]["rules"].append(
                    {"field": "entry_time", "type": "date", "value": [str(horas)], "operator": "last_n_hours"}
                )
            resp_af = session.post("/dataservice/statistics/dpi/aggregation", payload_app_fam, timeout=60)
            app_fam_map = {}
            for item in resp_af.get('data', []):
                app_fam_map[item.get('application', '')] = item.get('family', '')

            apps_data = [a for a in apps_data if fam_lower in app_fam_map.get(a.get('application', ''), '').lower()]
            if not apps_data:
                return f"❌ No hay aplicaciones de la familia '{familia}' en los datos DPI."

        # ── Construir resultado ──
        apps_sorted = sorted(apps_data, key=lambda x: int(x.get('octets', 0)), reverse=True)
        total_bytes = sum(int(a.get('octets', 0)) for a in apps_sorted)

        resultado = f"🌐 DPI RED COMPLETA — ANÁLISIS GLOBAL DE APLICACIONES\n"
        resultado += f"{'='*120}\n\n"
        resultado += f"⏰ Ventana de análisis: últimas {horas} hora(s)\n"
        resultado += f"📊 Aplicaciones únicas: {len(apps_sorted)} | Tráfico total clasificado: {fmt_bytes(total_bytes)}\n"
        if familia:
            resultado += f"🔍 Filtro: familia = '{familia}'\n"
        resultado += f"\n"

        # ── RANKING DE APLICACIONES ──
        resultado += f"{'#':<5} {'APLICACIÓN':<35} {'TRÁFICO':<14} {'%':<8} {'PAQUETES':<16}\n"
        resultado += f"{'-'*82}\n"

        # Apps no deseadas / sospechosas
        apps_sospechosas = {'torrent', 'bittorrent', 'tor', 'ultrasurf', 'psiphon', 'tunnelbear',
                            'openvpn', 'wireguard', 'shadowsocks', 'v2ray', 'crypto-mining'}

        alertas = []
        for i, app in enumerate(apps_sorted[:top], 1):
            octets = int(app.get('octets', 0))
            packets = int(app.get('packets', 0))
            nombre = app.get('application', 'N/A')
            pct = (octets / total_bytes * 100) if total_bytes > 0 else 0

            if pct >= 10: icon = "🔴"
            elif pct >= 5: icon = "🟠"
            elif pct >= 1: icon = "🟡"
            else: icon = "🟢"

            alerta = ""
            if nombre.lower() in apps_sospechosas or any(s in nombre.lower() for s in apps_sospechosas):
                alerta = " ⚠️ SOSPECHOSA"
                alertas.append(nombre)

            resultado += f"{i:<5} {icon} {nombre:<33} {fmt_bytes(octets):<14} {pct:>5.1f}%  {packets:<16,}{alerta}\n"

        if len(apps_sorted) > top:
            otros = len(apps_sorted) - top
            otros_bytes = sum(int(a.get('octets', 0)) for a in apps_sorted[top:])
            resultado += f"\n      ... y {otros} aplicaciones más ({fmt_bytes(otros_bytes)}, {(otros_bytes/total_bytes*100):.1f}%)\n"

        # ── RESUMEN POR FAMILIA ──
        if fam_data and not familia:
            fams_sorted = sorted(fam_data, key=lambda x: int(x.get('octets', 0)), reverse=True)
            total_fam = sum(int(f.get('octets', 0)) for f in fams_sorted)

            resultado += f"\n{'='*120}\n"
            resultado += f"📂 DISTRIBUCIÓN POR FAMILIA DE APLICACIÓN:\n\n"
            resultado += f"{'#':<5} {'FAMILIA':<35} {'TRÁFICO':<14} {'%':<8} {'PAQUETES':<16}\n"
            resultado += f"{'-'*82}\n"

            for i, fam in enumerate(fams_sorted, 1):
                octets = int(fam.get('octets', 0))
                packets = int(fam.get('packets', 0))
                pct = (octets / total_fam * 100) if total_fam > 0 else 0
                nombre = fam.get('family', 'N/A')

                if pct >= 10: icon = "🔴"
                elif pct >= 5: icon = "🟠"
                elif pct >= 1: icon = "🟡"
                else: icon = "🟢"

                resultado += f"{i:<5} {icon} {nombre:<33} {fmt_bytes(octets):<14} {pct:>5.1f}%  {packets:<16,}\n"

        # ── TOP SITIOS POR TRÁFICO DPI ──
        if sites_data:
            # Agrupar por site_id
            site_agg = defaultdict(lambda: {'bytes': 0, 'packets': 0, 'devices': []})
            for sd in sites_data:
                sip = sd.get('vdevice_name', '')
                info = dev_map.get(sip, {'hostname': sip, 'site_id': 'N/A'})
                sid = info['site_id']
                site_agg[sid]['bytes'] += int(sd.get('octets', 0))
                site_agg[sid]['packets'] += int(sd.get('packets', 0))
                site_agg[sid]['devices'].append(info['hostname'])

            sites_ranked = sorted(site_agg.items(), key=lambda x: x[1]['bytes'], reverse=True)

            resultado += f"\n{'='*120}\n"
            resultado += f"🏢 TOP 30 SITIOS POR TRÁFICO DPI:\n\n"
            resultado += f"{'#':<5} {'SITE ID':<12} {'TRÁFICO':<14} {'%':<8} {'DISPOSITIVOS':<60}\n"
            resultado += f"{'-'*100}\n"

            for i, (sid, data) in enumerate(sites_ranked[:30], 1):
                pct = (data['bytes'] / total_bytes * 100) if total_bytes > 0 else 0
                devs = ', '.join(sorted(set(data['devices'])))[:58]

                if pct >= 5: icon = "🔴"
                elif pct >= 2: icon = "🟠"
                elif pct >= 0.5: icon = "🟡"
                else: icon = "🟢"

                resultado += f"{i:<5} {icon} {sid:<10} {fmt_bytes(data['bytes']):<14} {pct:>5.1f}%  {devs}\n"

            resultado += f"\n      Total sitios con tráfico DPI: {len(sites_ranked)}\n"

        # ── ALERTAS ──
        if alertas:
            resultado += f"\n{'='*120}\n"
            resultado += f"🚨 ALERTAS — APLICACIONES SOSPECHOSAS DETECTADAS:\n\n"
            for app_name in alertas:
                resultado += f"  ⚠️  {app_name} — Puede ser tráfico no autorizado (P2P, proxy, evasión)\n"
            resultado += f"\n  💡 Usa ver_aplicaciones_sitio(sitio) para identificar qué sitios generan este tráfico\n"
            resultado += f"  💡 Usa ver_flujos_dpi_detalle(aplicacion='{alertas[0]}') para ver IPs origen/destino\n"

        resultado += f"\n{'='*120}\n"
        resultado += f"💡 HERRAMIENTAS RELACIONADAS:\n"
        resultado += f"  • ver_aplicaciones_sitio('51318') — DPI detallado de un sitio específico\n"
        resultado += f"  • ver_flujos_dpi_detalle(sitio='318') — Flujos con IPs origen/destino\n"
        resultado += f"  • ver_top_consumidores_dpi(aplicacion='youtube') — Quién consume más una app\n"
        resultado += f"  • ver_dpi_red_completa(familia='audio-video') — Solo una familia\n"

        return resultado

    except Exception as e:
        return f"❌ Error al analizar DPI de la red: {str(e)}"


# =====================================================
# HERRAMIENTA 35: FLUJOS DPI DETALLADOS (IPs y puertos)
# =====================================================
@mcp.tool()
def ver_flujos_dpi_detalle(
    sitio: str = "",
    aplicacion: str = "",
    top: int = 50
) -> str:
    """
    Muestra flujos DPI detallados con IPs origen/destino, puertos, protocolos e interfaces.
    Usa POST a la API de estadísticas DPI para obtener datos de CUALQUIER sitio (no solo CJF-304).

    Args:
        sitio: (Opcional) ID del sitio, parcial o hostname (ej: "318", "51318", "SDWAN-CJF-318-RT01")
        aplicacion: (Opcional) Filtrar por aplicación (ej: "youtube", "ms-teams", "torrent")
        top: Número de flujos a mostrar (default: 50)

    Returns:
        Tabla de flujos con IP origen, IP destino, puertos, protocolo, bytes, interfaz y aplicación.
        Incluye resumen de top IPs destino, top IPs origen, y top puertos.

    Ejemplo:
        ver_flujos_dpi_detalle(sitio="318") — Todos los flujos del sitio 318
        ver_flujos_dpi_detalle(sitio="318", aplicacion="youtube") — Solo YouTube del 318
        ver_flujos_dpi_detalle(aplicacion="torrent") — Buscar torrent en TODA la red
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo flujos DPI detallados...", file=sys.stderr)
        from collections import defaultdict

        session = get_vmanage_session()

        def fmt_bytes(b):
            try: b = int(b)
            except: return str(b)
            if b > 1024**3: return f"{b / (1024**3):.2f} GB"
            if b > 1024**2: return f"{b / (1024**2):.1f} MB"
            if b > 1024: return f"{b / 1024:.1f} KB"
            return f"{b} B"

        # Resolver system_ips si se especifica sitio
        system_ips = []
        hostnames_map = {}
        site_label = "TODA LA RED"

        if sitio:
            devices_result = session.get("/dataservice/device")
            sitio_lower = sitio.strip().lower()

            for dev in devices_result.get('data', []):
                if dev.get('device-type') != 'vedge' or dev.get('reachability') != 'reachable':
                    continue
                dev_site_id = str(dev.get('site-id', ''))
                dev_hostname = dev.get('host-name', '').lower()
                sip = dev.get('system-ip', '')

                if (sitio_lower == dev_site_id.lower() or
                    sitio_lower in dev_site_id or
                    sitio_lower in dev_hostname):
                    system_ips.append(sip)
                    hostnames_map[sip] = dev.get('host-name', sip)

            if not system_ips:
                return (f"❌ No se encontraron dispositivos para el sitio '{sitio}'\n\n"
                        f"Usa: ver_flujos_dpi_detalle(sitio='51318') o ver_flujos_dpi_detalle(sitio='318')")

            site_ids = sorted(set(str(dev.get('site-id', ''))
                                  for dev in devices_result.get('data', [])
                                  if dev.get('system-ip', '') in system_ips))
            site_label = f"SITIO {', '.join(site_ids)}"

        # Construir query
        rules = []
        if system_ips:
            rules.append({"field": "vdevice_name", "type": "string", "value": system_ips, "operator": "in"})
        if aplicacion:
            rules.append({"field": "application", "type": "string", "value": [aplicacion.strip()], "operator": "in"})

        payload = {
            "query": {"condition": "AND", "rules": rules} if rules else {},
            "size": min(top * 3, 500)  # Pedimos más para tener margen después del filtrado
        }

        resp = session.post("/dataservice/statistics/dpi", payload, timeout=60)
        flows = resp.get('data', [])

        if not flows:
            msg = f"❌ No se encontraron flujos DPI"
            if sitio:
                msg += f" para el sitio '{sitio}'"
            if aplicacion:
                msg += f" con aplicación '{aplicacion}'"
            msg += "\n\nSugerencias:\n"
            msg += "  • Usa ver_dpi_red_completa() para ver qué sitios tienen datos DPI\n"
            msg += "  • Usa ver_aplicaciones_sitio('318') para ver qué apps están clasificadas\n"
            return msg

        # Filtro adicional por aplicación (case-insensitive)
        if aplicacion:
            app_lower = aplicacion.strip().lower()
            flows_filtered = [f for f in flows if app_lower in f.get('application', '').lower()]
            if flows_filtered:
                flows = flows_filtered

        proto_map = {'6': 'TCP', '17': 'UDP', '1': 'ICMP', '47': 'GRE', '50': 'ESP', '132': 'SCTP'}

        # ── Construir resultado ──
        resultado = f"🔬 FLUJOS DPI DETALLADOS — {site_label}\n"
        resultado += f"{'='*140}\n\n"
        if sitio:
            resultado += f"📡 Dispositivos: {', '.join(hostnames_map.values()) if hostnames_map else 'N/A'}\n"
        if aplicacion:
            resultado += f"🔍 Filtro aplicación: '{aplicacion}'\n"
        resultado += f"📊 Flujos obtenidos: {len(flows)}\n\n"

        # ── TABLA DE FLUJOS ──
        resultado += f"{'#':<4} {'APLICACIÓN':<25} {'IP ORIGEN':<18} {'PTO':<7} {'IP DESTINO':<18} {'PTO':<7} {'PROTO':<6} {'BYTES':<12} {'INTERFAZ':<25}\n"
        resultado += f"{'-'*125}\n"

        # Acumuladores para el resumen
        dst_ips = defaultdict(lambda: {'bytes': 0, 'flows': 0, 'apps': set()})
        src_ips = defaultdict(lambda: {'bytes': 0, 'flows': 0})
        dst_ports = defaultdict(lambda: {'bytes': 0, 'flows': 0, 'proto': ''})
        apps_count = defaultdict(lambda: {'bytes': 0, 'flows': 0})
        total_bytes = 0

        for i, f in enumerate(flows[:top], 1):
            app = f.get('application', '?')
            src_ip = f.get('source_ip', '?')
            dst_ip = f.get('dest_ip', '?')
            src_port = str(f.get('source_port', '?'))
            dst_port = str(f.get('dest_port', '?'))
            proto = proto_map.get(str(f.get('ip_proto', '')), str(f.get('ip_proto', '?')))
            octets = int(f.get('octets', 0))
            iface = f.get('ingress_intf', f.get('egress_intf', '?'))

            resultado += f"{i:<4} {app:<25} {src_ip:<18} {src_port:<7} {dst_ip:<18} {dst_port:<7} {proto:<6} {fmt_bytes(octets):<12} {iface}\n"

            # Acumular
            total_bytes += octets
            dst_ips[dst_ip]['bytes'] += octets
            dst_ips[dst_ip]['flows'] += 1
            dst_ips[dst_ip]['apps'].add(app)
            src_ips[src_ip]['bytes'] += octets
            src_ips[src_ip]['flows'] += 1
            dst_ports[dst_port]['bytes'] += octets
            dst_ports[dst_port]['flows'] += 1
            dst_ports[dst_port]['proto'] = proto
            apps_count[app]['bytes'] += octets
            apps_count[app]['flows'] += 1

        if len(flows) > top:
            resultado += f"\n   ... mostrando {top} de {len(flows)} flujos disponibles\n"

        # ── RESUMEN: TOP IPs DESTINO ──
        resultado += f"\n{'='*140}\n"
        resultado += f"🎯 TOP 15 IPs DESTINO:\n\n"
        resultado += f"{'#':<4} {'IP DESTINO':<18} {'TRÁFICO':<14} {'FLUJOS':<8} {'APLICACIONES'}\n"
        resultado += f"{'-'*80}\n"

        for i, (ip, data) in enumerate(sorted(dst_ips.items(), key=lambda x: x[1]['bytes'], reverse=True)[:15], 1):
            apps_str = ', '.join(sorted(data['apps']))[:45]
            resultado += f"{i:<4} {ip:<18} {fmt_bytes(data['bytes']):<14} {data['flows']:<8} {apps_str}\n"

        # ── RESUMEN: TOP IPs ORIGEN ──
        resultado += f"\n{'='*140}\n"
        resultado += f"📤 TOP 15 IPs ORIGEN (hosts internos):\n\n"
        resultado += f"{'#':<4} {'IP ORIGEN':<18} {'TRÁFICO':<14} {'FLUJOS':<8}\n"
        resultado += f"{'-'*45}\n"

        for i, (ip, data) in enumerate(sorted(src_ips.items(), key=lambda x: x[1]['bytes'], reverse=True)[:15], 1):
            resultado += f"{i:<4} {ip:<18} {fmt_bytes(data['bytes']):<14} {data['flows']:<8}\n"

        # ── RESUMEN: TOP PUERTOS ──
        resultado += f"\n{'='*140}\n"
        resultado += f"🔌 TOP 10 PUERTOS DESTINO:\n\n"

        well_known = {'443': 'HTTPS', '80': 'HTTP', '53': 'DNS', '22': 'SSH', '25': 'SMTP',
                      '110': 'POP3', '143': 'IMAP', '993': 'IMAPS', '995': 'POP3S',
                      '389': 'LDAP', '636': 'LDAPS', '3389': 'RDP', '5060': 'SIP',
                      '5061': 'SIPS', '8080': 'HTTP-Alt', '8443': 'HTTPS-Alt',
                      '445': 'SMB', '139': 'NetBIOS', '1433': 'MSSQL', '3306': 'MySQL',
                      '5432': 'PostgreSQL', '6379': 'Redis', '27017': 'MongoDB',
                      '7680': 'WUDO', '1723': 'PPTP', '500': 'IKE', '4500': 'IPsec-NAT'}

        resultado += f"{'#':<4} {'PUERTO':<8} {'SERVICIO':<14} {'PROTO':<6} {'TRÁFICO':<14} {'FLUJOS':<8}\n"
        resultado += f"{'-'*58}\n"

        for i, (port, data) in enumerate(sorted(dst_ports.items(), key=lambda x: x[1]['bytes'], reverse=True)[:10], 1):
            svc = well_known.get(str(port), '')
            resultado += f"{i:<4} {port:<8} {svc:<14} {data['proto']:<6} {fmt_bytes(data['bytes']):<14} {data['flows']:<8}\n"

        # ── RESUMEN: APPS EN ESTOS FLUJOS ──
        if not aplicacion and len(apps_count) > 1:
            resultado += f"\n{'='*140}\n"
            resultado += f"📱 APLICACIONES EN ESTOS FLUJOS:\n\n"
            for i, (app, data) in enumerate(sorted(apps_count.items(), key=lambda x: x[1]['bytes'], reverse=True)[:20], 1):
                pct = (data['bytes'] / total_bytes * 100) if total_bytes > 0 else 0
                resultado += f"   {i:>2}. {app:<30} {fmt_bytes(data['bytes']):<14} {pct:>5.1f}%  ({data['flows']} flujos)\n"

        resultado += f"\n{'='*140}\n"
        resultado += f"💡 HERRAMIENTAS RELACIONADAS:\n"
        resultado += f"  • ver_aplicaciones_sitio('{sitio or '318'}') — Ranking DPI agregado del sitio\n"
        resultado += f"  • ver_dpi_red_completa() — Ranking global de apps de toda la red\n"
        resultado += f"  • ver_top_consumidores_dpi(aplicacion='youtube') — Quién más consume una app\n"
        resultado += f"  • ver_dpi_red_completa(familia='audio-video') — Filtrar por familia\n"

        return resultado

    except Exception as e:
        return f"❌ Error al obtener flujos DPI: {str(e)}"


# =====================================================
# HERRAMIENTA 36: TOP CONSUMIDORES DPI (por app o global)
# =====================================================
@mcp.tool()
def ver_top_consumidores_dpi(
    aplicacion: str = "",
    top: int = 30,
    horas: int = 24
) -> str:
    """
    Identifica los sitios/dispositivos que más consumen una aplicación específica en toda la red,
    o los mayores consumidores globales. Ideal para detectar quién gasta más YouTube, torrent, etc.

    Args:
        aplicacion: Aplicación a analizar (ej: "youtube", "ssl", "torrent", "ms-teams").
                   Si se deja vacío, muestra el top de consumidores por tráfico total.
        top: Número de sitios/dispositivos a mostrar (default: 30)
        horas: Ventana de tiempo en horas (default: 24, máx 720)

    Returns:
        Ranking de sitios que más consumen la aplicación, con tráfico total, porcentaje
        y número de dispositivos. Si se especifica app, incluye detalle por dispositivo.

    Ejemplo:
        ver_top_consumidores_dpi(aplicacion="youtube") — Quién consume más YouTube
        ver_top_consumidores_dpi(aplicacion="torrent") — Detectar P2P
        ver_top_consumidores_dpi() — Top consumidores globales de la red
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Buscando top consumidores DPI...", file=sys.stderr)
        from collections import defaultdict

        session = get_vmanage_session()

        def fmt_bytes(b):
            try: b = int(b)
            except: return str(b)
            if b > 1024**4: return f"{b / (1024**4):.2f} TB"
            if b > 1024**3: return f"{b / (1024**3):.2f} GB"
            if b > 1024**2: return f"{b / (1024**2):.1f} MB"
            if b > 1024: return f"{b / 1024:.1f} KB"
            return f"{b} B"

        horas = max(1, min(horas, 720))

        # Mapear system_ip → hostname + site_id
        devices_result = session.get("/dataservice/device")
        dev_map = {}
        for dev in devices_result.get('data', []):
            sip = dev.get('system-ip', '')
            dev_map[sip] = {
                'hostname': dev.get('host-name', sip),
                'site_id': str(dev.get('site-id', 'N/A'))
            }

        # ── Query: tráfico por dispositivo + aplicación ──
        time_rules = []
        if horas != 24:
            time_rules.append({"field": "entry_time", "type": "date", "value": [str(horas)], "operator": "last_n_hours"})

        if aplicacion:
            app_name = aplicacion.strip()

            # Tráfico de la app por dispositivo
            payload_dev = {
                "query": {"condition": "AND", "rules": [
                    {"field": "application", "type": "string", "value": [app_name], "operator": "in"}
                ] + time_rules},
                "aggregation": {
                    "field": [{"property": "vdevice_name", "size": 400, "sequence": 1}],
                    "metrics": [
                        {"property": "octets", "type": "sum"},
                        {"property": "packets", "type": "sum"}
                    ]
                }
            }

            resp_dev = session.post("/dataservice/statistics/dpi/aggregation", payload_dev, timeout=60)
            dev_data = resp_dev.get('data', [])

            if not dev_data:
                # Búsqueda flexible: intentar con match parcial
                payload_all_apps = {
                    "query": {"condition": "AND", "rules": time_rules},
                    "aggregation": {
                        "field": [{"property": "application", "size": 500}],
                        "metrics": [{"property": "octets", "type": "sum"}]
                    }
                }
                resp_all = session.post("/dataservice/statistics/dpi/aggregation", payload_all_apps, timeout=60)
                all_apps = [a.get('application', '') for a in resp_all.get('data', [])]
                app_lower = app_name.lower()
                similares = [a for a in all_apps if app_lower in a.lower() or any(p in a.lower() for p in app_lower.split('-'))]

                resultado = f"❌ No se encontraron datos para la aplicación '{app_name}'\n\n"
                if similares:
                    resultado += f"📋 Aplicaciones similares ({len(similares)}):\n"
                    for a in sorted(similares)[:20]:
                        resultado += f"   • {a}\n"
                    resultado += f"\n💡 Intenta: ver_top_consumidores_dpi(aplicacion='{similares[0]}')\n"
                else:
                    resultado += f"📋 Primeras 30 aplicaciones disponibles:\n"
                    for a in sorted(all_apps)[:30]:
                        resultado += f"   • {a}\n"
                return resultado

            # También obtener tráfico total de la app
            payload_total = {
                "query": {"condition": "AND", "rules": [
                    {"field": "application", "type": "string", "value": [app_name], "operator": "in"}
                ] + time_rules},
                "aggregation": {
                    "field": [],
                    "metrics": [
                        {"property": "octets", "type": "sum"},
                        {"property": "packets", "type": "sum"}
                    ]
                }
            }
            try:
                resp_total = session.post("/dataservice/statistics/dpi/aggregation", payload_total, timeout=30)
                total_app_bytes = int(resp_total.get('data', [{}])[0].get('octets', 0))
            except:
                total_app_bytes = sum(int(d.get('octets', 0)) for d in dev_data)

            # Agrupar por sitio
            site_agg = defaultdict(lambda: {'bytes': 0, 'packets': 0, 'devices': []})
            for d in dev_data:
                sip = d.get('vdevice_name', '')
                info = dev_map.get(sip, {'hostname': sip, 'site_id': 'N/A'})
                sid = info['site_id']
                site_agg[sid]['bytes'] += int(d.get('octets', 0))
                site_agg[sid]['packets'] += int(d.get('packets', 0))
                site_agg[sid]['devices'].append({
                    'hostname': info['hostname'],
                    'bytes': int(d.get('octets', 0)),
                    'packets': int(d.get('packets', 0))
                })

            sites_ranked = sorted(site_agg.items(), key=lambda x: x[1]['bytes'], reverse=True)

            resultado = f"🎯 TOP CONSUMIDORES DE: {app_name.upper()}\n"
            resultado += f"{'='*120}\n\n"
            resultado += f"⏰ Ventana: últimas {horas} hora(s)\n"
            resultado += f"📊 Tráfico total de {app_name}: {fmt_bytes(total_app_bytes)}\n"
            resultado += f"🏢 Sitios con tráfico: {len(sites_ranked)}\n"
            resultado += f"📡 Dispositivos con tráfico: {len(dev_data)}\n\n"

            resultado += f"{'#':<5} {'SITE ID':<12} {'TRÁFICO':<14} {'% DEL TOTAL':<14} {'DISPOSITIVOS'}\n"
            resultado += f"{'-'*100}\n"

            for i, (sid, data) in enumerate(sites_ranked[:top], 1):
                pct = (data['bytes'] / total_app_bytes * 100) if total_app_bytes > 0 else 0
                devs = sorted(data['devices'], key=lambda x: x['bytes'], reverse=True)
                devs_str = ', '.join(f"{d['hostname']}({fmt_bytes(d['bytes'])})" for d in devs)[:55]

                if pct >= 10: icon = "🔴"
                elif pct >= 5: icon = "🟠"
                elif pct >= 1: icon = "🟡"
                else: icon = "🟢"

                resultado += f"{i:<5} {icon} {sid:<10} {fmt_bytes(data['bytes']):<14} {pct:>5.1f}%        {devs_str}\n"

            # Concentración
            if sites_ranked:
                top3_bytes = sum(s[1]['bytes'] for s in sites_ranked[:3])
                top10_bytes = sum(s[1]['bytes'] for s in sites_ranked[:10])
                top3_pct = (top3_bytes / total_app_bytes * 100) if total_app_bytes > 0 else 0
                top10_pct = (top10_bytes / total_app_bytes * 100) if total_app_bytes > 0 else 0

                resultado += f"\n{'='*120}\n"
                resultado += f"📈 CONCENTRACIÓN:\n\n"
                resultado += f"   Top 3 sitios:  {fmt_bytes(top3_bytes)} ({top3_pct:.1f}% del total)\n"
                resultado += f"   Top 10 sitios: {fmt_bytes(top10_bytes)} ({top10_pct:.1f}% del total)\n"
                resultado += f"   Todos ({len(sites_ranked)}):  {fmt_bytes(total_app_bytes)} (100%)\n"

                if top3_pct > 60:
                    resultado += f"\n   ⚠️  Alta concentración — El {top3_pct:.0f}% del tráfico de {app_name} viene de solo 3 sitios\n"

        else:
            # Sin filtro de app: top sitios por tráfico DPI total
            payload_sites = {
                "query": {"condition": "AND", "rules": time_rules},
                "aggregation": {
                    "field": [{"property": "vdevice_name", "size": 400, "sequence": 1}],
                    "metrics": [
                        {"property": "octets", "type": "sum"},
                        {"property": "packets", "type": "sum"}
                    ]
                }
            }

            resp_sites = session.post("/dataservice/statistics/dpi/aggregation", payload_sites, timeout=60)
            sites_data = resp_sites.get('data', [])

            if not sites_data:
                return "❌ No hay datos DPI de agregación en la red."

            # Agrupar por sitio
            site_agg = defaultdict(lambda: {'bytes': 0, 'packets': 0, 'devices': []})
            for sd in sites_data:
                sip = sd.get('vdevice_name', '')
                info = dev_map.get(sip, {'hostname': sip, 'site_id': 'N/A'})
                sid = info['site_id']
                site_agg[sid]['bytes'] += int(sd.get('octets', 0))
                site_agg[sid]['packets'] += int(sd.get('packets', 0))
                site_agg[sid]['devices'].append(info['hostname'])

            sites_ranked = sorted(site_agg.items(), key=lambda x: x[1]['bytes'], reverse=True)
            total_bytes = sum(s[1]['bytes'] for s in sites_ranked)

            resultado = f"🏆 TOP CONSUMIDORES DE LA RED (TRÁFICO DPI TOTAL)\n"
            resultado += f"{'='*120}\n\n"
            resultado += f"⏰ Ventana: últimas {horas} hora(s)\n"
            resultado += f"📊 Tráfico total clasificado: {fmt_bytes(total_bytes)}\n"
            resultado += f"🏢 Sitios con tráfico: {len(sites_ranked)}\n\n"

            resultado += f"{'#':<5} {'SITE ID':<12} {'TRÁFICO':<14} {'% RED':<10} {'PAQUETES':<16} {'DISPOSITIVOS'}\n"
            resultado += f"{'-'*105}\n"

            for i, (sid, data) in enumerate(sites_ranked[:top], 1):
                pct = (data['bytes'] / total_bytes * 100) if total_bytes > 0 else 0
                devs = ', '.join(sorted(set(data['devices'])))[:50]

                if pct >= 5: icon = "🔴"
                elif pct >= 2: icon = "🟠"
                elif pct >= 0.5: icon = "🟡"
                else: icon = "🟢"

                resultado += f"{i:<5} {icon} {sid:<10} {fmt_bytes(data['bytes']):<14} {pct:>5.1f}%     {data['packets']:<16,} {devs}\n"

            # Top apps globales rápido
            payload_top_apps = {
                "query": {"condition": "AND", "rules": time_rules},
                "aggregation": {
                    "field": [{"property": "application", "size": 10}],
                    "metrics": [{"property": "octets", "type": "sum"}]
                }
            }
            resp_ta = session.post("/dataservice/statistics/dpi/aggregation", payload_top_apps, timeout=30)
            top_apps = sorted(resp_ta.get('data', []), key=lambda x: int(x.get('octets', 0)), reverse=True)

            if top_apps:
                resultado += f"\n{'='*120}\n"
                resultado += f"📱 TOP 10 APLICACIONES GLOBALES:\n\n"
                for i, app in enumerate(top_apps[:10], 1):
                    pct = (int(app.get('octets', 0)) / total_bytes * 100) if total_bytes > 0 else 0
                    resultado += f"   {i:>2}. {app.get('application','?'):<30} {fmt_bytes(app.get('octets',0)):<14} ({pct:.1f}%)\n"

        resultado += f"\n{'='*120}\n"
        resultado += f"💡 HERRAMIENTAS RELACIONADAS:\n"
        resultado += f"  • ver_dpi_red_completa() — Ranking global de todas las apps\n"
        resultado += f"  • ver_flujos_dpi_detalle(sitio='318', aplicacion='youtube') — Flujos detallados\n"
        resultado += f"  • ver_aplicaciones_sitio('318') — DPI detallado de un sitio\n"
        resultado += f"  • ver_top_consumidores_dpi(aplicacion='ms-teams', horas=168) — Última semana\n"

        return resultado

    except Exception as e:
        return f"❌ Error al buscar consumidores DPI: {str(e)}"


# ==========================================
# HERRAMIENTAS CLOUD ON-RAMP / SaaS (CloudX)
# ==========================================

@mcp.tool()
def ver_aplicaciones_saas_sitio(
    sitio: str
) -> str:
    """
    Muestra las aplicaciones SaaS (Office365, Webex, etc.) que un sitio SD-WAN está usando 
    EN TIEMPO REAL, con métricas de calidad de experiencia (vQoE).
    
    Esto usa Cloud OnRamp for SaaS (CloudX) que funciona en TODOS los routers de la red
    y muestra datos ACTUALES a diferencia de DPI que requiere Data Policy especial.
    
    Args:
        sitio: ID del sitio, parcial o hostname (ej: "608", "51304", "SDWAN-CJF-608-RT01")
    
    Returns:
        Lista de aplicaciones SaaS con latencia, pérdida, interfaz de salida y score vQoE.
        El score vQoE va de 0 (malo) a 10 (excelente).
    
    Ejemplo:
        ver_aplicaciones_saas_sitio("608") — Apps SaaS del sitio 608
        ver_aplicaciones_saas_sitio("SDWAN-CJF-304-RT01") — Por hostname
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo aplicaciones SaaS del sitio: {sitio}", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Obtener dispositivos
        devices_result = session.get("/dataservice/device")
        all_devices = devices_result.get('data', [])
        
        # Buscar dispositivos del sitio
        sitio_lower = sitio.strip().lower()
        site_devices = []
        
        for dev in all_devices:
            if dev.get('device-type') not in ('vedge', 'cedge') or dev.get('reachability') != 'reachable':
                continue
            dev_site_id = str(dev.get('site-id', ''))
            dev_hostname = dev.get('host-name', '').lower()
            
            if (sitio_lower == dev_site_id.lower() or
                sitio_lower in dev_site_id or
                sitio_lower in dev_hostname):
                site_devices.append(dev)
        
        if not site_devices:
            return (f"❌ No se encontraron dispositivos WAN Edge para '{sitio}'\n"
                    f"Usa buscar_dispositivo() o listar_dispositivos() para encontrar el ID correcto.")
        
        resultado = ""
        site_id = site_devices[0].get('site-id', sitio)
        
        for dev in site_devices:
            dev_ip = dev.get('system-ip', '')
            hostname = dev.get('host-name', 'desconocido')
            
            resultado += f"\n📱 Dispositivo: {hostname} ({dev_ip}) — Sitio {site_id}\n"
            resultado += "=" * 70 + "\n"
            
            try:
                r = session.get(f"/dataservice/device/cloudx/applications?deviceId={dev_ip}", timeout=15)
                apps = r.get('data', [])
                
                if not apps:
                    resultado += "  ⚠️ Sin datos de aplicaciones SaaS (Cloud OnRamp no configurado)\n"
                    continue
                
                # Clasificar por estado vQoE
                good = [a for a in apps if a.get('vqe-status') == 'goodSites']
                average = [a for a in apps if a.get('vqe-status') == 'averageSites']
                bad = [a for a in apps if a.get('vqe-status') == 'badSites']
                
                resultado += f"\n  📊 RESUMEN: {len(apps)} aplicaciones SaaS monitoreadas\n"
                resultado += f"     ✅ Buena calidad: {len(good)}  ⚠️ Media: {len(average)}  ❌ Mala: {len(bad)}\n\n"
                
                # Ordenar por vqe-score descendente
                apps.sort(key=lambda x: float(x.get('vqe-score', 0)), reverse=True)
                
                resultado += f"  {'Aplicación':<35} {'vQoE':>5} {'Latencia':>10} {'Pérdida':>8} {'Estado':>12} {'Interfaz'}\n"
                resultado += f"  {'-'*35} {'-'*5} {'-'*10} {'-'*8} {'-'*12} {'-'*15}\n"
                
                for app in apps:
                    nombre = app.get('application', '?')
                    vqe = float(app.get('vqe-score', 0))
                    lat = app.get('latency', '?')
                    loss = app.get('loss', '?')
                    status = app.get('vqe-status', '?')
                    iface = app.get('interface', '?')
                    exit_type = app.get('exit-type', '?')
                    
                    # Emoji según estado
                    if status == 'goodSites':
                        emoji = '✅'
                        estado = 'Buena'
                    elif status == 'averageSites':
                        emoji = '⚠️'
                        estado = 'Media'
                    else:
                        emoji = '❌'
                        estado = 'Mala'
                    
                    resultado += f"  {emoji} {nombre:<33} {vqe:>5.1f} {lat:>8}ms {loss:>7}% {estado:>10}  {iface}\n"
                
                resultado += f"\n  💡 exit-type: {apps[0].get('exit-type', '?')} | VPN: {apps[0].get('vpn-id', '?')}\n"
                
            except Exception as e:
                resultado += f"  ❌ Error consultando dispositivo: {str(e)}\n"
        
        resultado += f"\n📌 NOTA: Estos datos son de Cloud OnRamp for SaaS (tiempo real).\n"
        resultado += f"   Para DPI profundo (todas las apps), usa ver_aplicaciones_sitio().\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener aplicaciones SaaS: {str(e)}"


@mcp.tool()
def ver_calidad_saas_red(
    horas: int = 1,
    aplicacion: str = "",
    sitio: str = ""
) -> str:
    """
    Muestra la calidad de experiencia (vQoE) de aplicaciones SaaS como Office365 y Webex
    a nivel de TODA LA RED o filtrado por sitio/aplicación, usando estadísticas CloudX históricas.
    
    Esta función usa analytics aggregation (POST) para obtener métricas promediadas de la red
    completa. Funciona con TODOS los routers que tengan Cloud OnRamp for SaaS habilitado (~95% de la red).
    
    Args:
        horas: Ventana de tiempo a analizar (default: 1 hora, max recomendado: 168 = 1 semana)
        aplicacion: (Opcional) Filtrar por nombre de aplicación (ej: "office365", "webex")
        sitio: (Opcional) Filtrar por site-id (ej: "52608", "51304")
    
    Returns:
        Ranking de aplicaciones SaaS por calidad vQoE con latencia y pérdida promedio.
        Incluye desglose por sitio si se filtra por aplicación.
    
    Ejemplo:
        ver_calidad_saas_red() — Vista global última hora
        ver_calidad_saas_red(horas=24) — Últimas 24 horas
        ver_calidad_saas_red(aplicacion="office365") — Solo Office365 por sitio
        ver_calidad_saas_red(sitio="52608", horas=24) — Un sitio, últimas 24h
    """
    try:
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Obteniendo calidad SaaS de la red (últimas {horas}h)", file=sys.stderr)
        
        session = get_vmanage_session()
        
        # Construir reglas de filtro
        rules = [{
            'value': [str(horas)],
            'field': 'entry_time',
            'type': 'date',
            'operator': 'last_n_hours'
        }]
        
        if sitio:
            # Resolver site-id completo si es parcial
            if not sitio.startswith('5'):
                sitio = f"5{sitio}"
            rules.append({
                'value': [sitio],
                'field': 'site_id',
                'type': 'long',
                'operator': 'in'
            })
        
        if aplicacion:
            rules.append({
                'value': [aplicacion.lower()],
                'field': 'application',
                'type': 'string',
                'operator': 'in'
            })
        
        # Decidir agrupación según filtros
        group_fields = [{'property': 'application', 'sequence': 1}]
        
        if aplicacion:
            # Si se filtra por app, desglosar por sitio
            group_fields.append({'property': 'site_id', 'sequence': 2})
        
        payload = {
            'query': {
                'condition': 'AND',
                'rules': rules
            },
            'aggregation': {
                'field': group_fields,
                'metrics': [
                    {'property': 'latency', 'type': 'avg'},
                    {'property': 'loss', 'type': 'avg'},
                    {'property': 'vqe_score', 'type': 'avg'}
                ]
            }
        }
        
        r = session.post('/dataservice/statistics/cloudx/aggregation', payload, timeout=30)
        data = r.get('data', [])
        
        if not data:
            return (f"⚠️ Sin datos CloudX para los filtros especificados (últimas {horas}h)\n\n"
                    f"💡 Para ver datos en tiempo real por dispositivo, usa:\n"
                    f"  ver_aplicaciones_saas_sitio('608')")
        
        # Ordenar por vqe_score descendente
        data.sort(key=lambda x: float(x.get('vqe_score', 0)), reverse=True)
        
        resultado = f"☁️ CALIDAD DE APLICACIONES SaaS — Últimas {horas}h\n"
        resultado += "=" * 75 + "\n\n"
        
        if aplicacion:
            # Desglose por sitio para una aplicación
            resultado += f"📱 Aplicación: {aplicacion.upper()}\n"
            resultado += f"📊 {len(data)} sitios con datos\n\n"
            
            resultado += f"  {'Sitio':>8} {'vQoE':>6} {'Latencia':>10} {'Pérdida':>8} {'Muestras':>10} {'Estado'}\n"
            resultado += f"  {'-'*8} {'-'*6} {'-'*10} {'-'*8} {'-'*10} {'-'*12}\n"
            
            for d in data:
                site = str(d.get('site_id', '?'))
                vqe = float(d.get('vqe_score', 0))
                lat = float(d.get('latency', 0))
                loss = float(d.get('loss', 0))
                count = d.get('count', 0)
                
                if vqe >= 7:
                    emoji = '✅'
                    estado = 'Buena'
                elif vqe >= 4:
                    emoji = '⚠️'
                    estado = 'Media'
                else:
                    emoji = '❌'
                    estado = 'Mala'
                
                resultado += f"  {emoji} {site:>6} {vqe:>6.1f} {lat:>8.0f}ms {loss:>7.1f}% {count:>10} {estado}\n"
            
            # Estadísticas globales
            avg_vqe = sum(float(d.get('vqe_score',0)) for d in data) / len(data)
            avg_lat = sum(float(d.get('latency',0)) for d in data) / len(data)
            bad_sites = sum(1 for d in data if float(d.get('vqe_score',0)) < 4)
            resultado += f"\n  📈 Promedio global: vQoE={avg_vqe:.1f}, Latencia={avg_lat:.0f}ms\n"
            resultado += f"  🔴 Sitios con mala calidad: {bad_sites}/{len(data)}\n"
            
        else:
            # Vista global por aplicación
            resultado += f"📊 {len(data)} aplicaciones SaaS monitoreadas\n"
            if sitio:
                resultado += f"📍 Filtrado por sitio: {sitio}\n"
            resultado += "\n"
            
            resultado += f"  {'Aplicación':<35} {'vQoE':>6} {'Latencia':>10} {'Pérdida':>8} {'Muestras':>10} {'Estado'}\n"
            resultado += f"  {'-'*35} {'-'*6} {'-'*10} {'-'*8} {'-'*10} {'-'*12}\n"
            
            for d in data:
                app = d.get('application', '?')
                vqe = float(d.get('vqe_score', 0))
                lat = float(d.get('latency', 0))
                loss = float(d.get('loss', 0))
                count = d.get('count', 0)
                
                if vqe >= 7:
                    emoji = '✅'
                    estado = 'Buena'
                elif vqe >= 4:
                    emoji = '⚠️'
                    estado = 'Media'
                else:
                    emoji = '❌'
                    estado = 'Mala'
                
                resultado += f"  {emoji} {app:<33} {vqe:>6.1f} {lat:>8.0f}ms {loss:>7.1f}% {count:>10} {estado}\n"
            
            # Resumen
            good = sum(1 for d in data if float(d.get('vqe_score',0)) >= 7)
            avg_count = sum(1 for d in data if 4 <= float(d.get('vqe_score',0)) < 7)
            bad = sum(1 for d in data if float(d.get('vqe_score',0)) < 4)
            resultado += f"\n  📈 Resumen: ✅ {good} buenas | ⚠️ {avg_count} medias | ❌ {bad} malas\n"
        
        resultado += f"\n💡 Tips:\n"
        resultado += f"  • ver_aplicaciones_saas_sitio('608') — Detalle real-time de un sitio\n"
        resultado += f"  • ver_calidad_saas_red(aplicacion='office365') — Office365 por sitio\n"
        resultado += f"  • ver_calidad_saas_red(horas=168) — Tendencia semanal\n"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al obtener calidad SaaS: {str(e)}"


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
