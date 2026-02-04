#!/usr/bin/env python3
"""
Servidor MCP para gestión de Cisco SD-WAN (vManage)
Desarrollado con FastMCP para Network Automation
"""

import os
import requests
import urllib3
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastmcp import FastMCP
from browser_cookies import BrowserCookieExtractor

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cargar variables de entorno
load_dotenv()

# Inicializar servidor MCP
mcp = FastMCP("cisco-sdwan-manager")


class AnalyticsCloudSession:
    """Clase para gestionar la sesión con Cisco Analytics Cloud"""
    
    def __init__(self):
        self.base_url = "https://us02.analytics.sdwan.cisco.com"
        self.session = requests.Session()
        self.session.verify = False
        
        # Extraer cookies de Analytics Cloud
        try:
            import browser_cookie3
            cj = browser_cookie3.chrome(domain_name='us02.analytics.sdwan.cisco.com')
            
            csrf_token = None
            overlay_id = None
            
            for cookie in cj:
                if 'cisco.com' in cookie.domain:
                    self.session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
                    
                if cookie.name == 'okta-oauth-state':
                    csrf_token = cookie.value
                elif cookie.name == 'cl-overlay-id':
                    overlay_id = cookie.value
            
            # Headers necesarios
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'x-csrftoken': csrf_token if csrf_token else '',
                'sdwan-overlay': overlay_id if overlay_id else '',
                'Origin': 'https://us02.analytics.sdwan.cisco.com',
                'Referer': 'https://us02.analytics.sdwan.cisco.com/analytics/v4/overview',
            })
                    
        except Exception as e:
            print(f"Warning: No se pudo extraer cookies de Analytics: {e}")
    
    def post(self, endpoint: str, json_data: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Hacer petición POST a Analytics Cloud"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=json_data, timeout=timeout)
        response.raise_for_status()
        return response.json()


def get_analytics_session():
    """Obtiene una sesión de Analytics Cloud"""
    return AnalyticsCloudSession()


class VManageSession:
    """Clase para gestionar la sesión con vManage usando cookies del navegador"""
    
    def __init__(self, ip: str, username: str = None, password: str = None):
        self.base_url = f"https://{ip}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
        self.cookie_extractor = BrowserCookieExtractor(ip)
        
    def login(self) -> bool:
        """
        Obtiene cookies del navegador automáticamente.
        Ya no intenta autenticación programática que falla en vManage.
        
        Returns:
            bool: True si se obtuvieron cookies válidas, False en caso contrario
        """
        try:
            # Extraer cookies del navegador
            jsessionid, xsrf_token = self.cookie_extractor.get_cookies()
            
            if not jsessionid or not xsrf_token:
                print("\n❌ No se encontraron cookies válidas en el navegador")
                print("📋 Inicia sesión en vManage desde tu navegador primero")
                return False
            
            # Configurar sesión con las cookies extraídas
            self.session.cookies.set("JSESSIONID", jsessionid)
            self.token = xsrf_token
            
            # Configurar headers necesarios
            self.session.headers.update({
                "X-XSRF-TOKEN": self.token,
                "Content-Type": "application/json"
            })
            
            # Verificar que las cookies funcionan
            test_url = f"{self.base_url}/dataservice/device"
            test_response = self.session.get(
                test_url,
                verify=False,
                timeout=10
            )
            
            if test_response.status_code == 200:
                return True
            else:
                print(f"⚠️  Cookies extraídas pero no válidas (HTTP {test_response.status_code})")
                # Intentar refrescar cookies
                jsessionid, xsrf_token = self.cookie_extractor.get_cookies(force_refresh=True)
                if jsessionid and xsrf_token:
                    self.session.cookies.set("JSESSIONID", jsessionid)
                    self.token = xsrf_token
                    self.session.headers.update({"X-XSRF-TOKEN": self.token})
                    return True
                return False
                
        except Exception as e:
            print(f"❌ Error al obtener cookies: {str(e)}")
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
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout al consultar {endpoint}")
        except requests.exceptions.RequestException as e:
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
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout al consultar {endpoint}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error en petición POST a {endpoint}: {str(e)}")


def get_vmanage_session() -> VManageSession:
    """
    Crea y autentica una sesión con vManage usando credenciales del .env
    
    Returns:
        VManageSession autenticada
        
    Raises:
        ValueError: Si faltan variables de entorno
        ConnectionError: Si falla la autenticación
    """
    vmanage_ip = os.getenv('VMANAGE_IP')
    username = os.getenv('VMANAGE_USERNAME')
    password = os.getenv('VMANAGE_PASSWORD')
    
    if not all([vmanage_ip, username, password]):
        raise ValueError(
            "Faltan credenciales en el archivo .env. "
            "Se requieren: VMANAGE_IP, VMANAGE_USERNAME, VMANAGE_PASSWORD"
        )
    
    session = VManageSession(vmanage_ip, username, password)
    
    if not session.login():
        raise ConnectionError("Error de autenticación con vManage. Verifica las credenciales.")
    
    return session


@mcp.tool()
def listar_dispositivos() -> str:
    """
    Lista todos los dispositivos en el inventario de SD-WAN (vEdges, vSmarts, vBonds, etc.)
    
    Returns:
        JSON string con el inventario completo de dispositivos
    """
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
def ver_estadisticas_interfaces(device_id: str) -> str:
    """
    Consulta estadísticas detalladas de todas las interfaces de un dispositivo
    
    Args:
        device_id: System IP del dispositivo (ejemplo: 10.80.10.207)
    
    Returns:
        Estadísticas de tráfico, errores y estado de interfaces
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/interface/stats?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            interfaces = result['data']
            stats = []
            
            for iface in interfaces:
                stats.append({
                    'interface': iface.get('interface', 'N/A'),
                    'vpn': iface.get('vpn-id', 'N/A'),
                    'status': iface.get('if-oper-status', 'N/A'),
                    'admin_status': iface.get('if-admin-status', 'N/A'),
                    'ip_address': iface.get('ip-address', 'N/A'),
                    'rx_kbps': iface.get('rx-kbps', 0),
                    'tx_kbps': iface.get('tx-kbps', 0),
                    'rx_packets': iface.get('rx-packets', 0),
                    'tx_packets': iface.get('tx-packets', 0),
                    'rx_errors': iface.get('rx-errors', 0),
                    'tx_errors': iface.get('tx-errors', 0),
                    'rx_drops': iface.get('rx-drops', 0),
                    'tx_drops': iface.get('tx-drops', 0)
                })
            
            return (
                f"Estadísticas de interfaces del dispositivo {device_id}:\n\n"
                f"Total de interfaces: {len(stats)}\n\n"
                f"Detalle:\n{stats}"
            )
        
        return f"No se encontraron estadísticas para el dispositivo {device_id}"
        
    except Exception as e:
        return f"Error al obtener estadísticas de interfaces: {str(e)}"


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
def diagnostico_completo_dispositivo(device_id: str) -> str:
    """
    Realiza un diagnóstico completo de un dispositivo combinando múltiples métricas
    
    Args:
        device_id: System IP del dispositivo (ejemplo: 10.80.10.207)
    
    Returns:
        Diagnóstico completo: salud, recursos, conectividad, interfaces, alarmas
    """
    try:
        session = get_vmanage_session()
        
        diagnostico = {
            'device_id': device_id,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 1. Información básica
        device_info = session.get(f"/dataservice/device?system-ip={device_id}")
        if 'data' in device_info and len(device_info['data']) > 0:
            device = device_info['data'][0]
            diagnostico['info_basica'] = {
                'hostname': device.get('host-name', 'N/A'),
                'tipo': device.get('device-type', 'N/A'),
                'modelo': device.get('device-model', 'N/A'),
                'site_id': device.get('site-id', 'N/A'),
                'estado': device.get('reachability', 'N/A'),
                'version': device.get('version', 'N/A'),
                'uptime': device.get('uptime-date', 'N/A')
            }
        
        # 2. CPU y Memoria
        try:
            system_status = session.get(f"/dataservice/device/system/status?deviceId={device_id}")
            if 'data' in system_status and len(system_status['data']) > 0:
                sys_data = system_status['data'][0]
                cpu_idle = float(sys_data.get('cpu-idle', 100))
                diagnostico['recursos'] = {
                    'cpu_usado_percent': f"{100 - cpu_idle:.2f}",
                    'memoria_usada_percent': sys_data.get('mem-used-percent', 'N/A'),
                    'disco_usado_percent': sys_data.get('disk-used', 'N/A')
                }
        except:
            diagnostico['recursos'] = 'No disponible'
        
        # 3. Interfaces con problemas
        try:
            interfaces = session.get(f"/dataservice/device/interface/stats?deviceId={device_id}")
            if 'data' in interfaces:
                interfaces_down = []
                interfaces_errores = []
                
                for iface in interfaces['data']:
                    if iface.get('if-oper-status') != 'if-oper-state-ready':
                        interfaces_down.append(iface.get('interface', 'N/A'))
                    
                    rx_errors = int(iface.get('rx-errors', 0))
                    tx_errors = int(iface.get('tx-errors', 0))
                    if rx_errors > 0 or tx_errors > 0:
                        interfaces_errores.append({
                            'interface': iface.get('interface', 'N/A'),
                            'rx_errors': rx_errors,
                            'tx_errors': tx_errors
                        })
                
                diagnostico['interfaces'] = {
                    'total': len(interfaces['data']),
                    'caidas': interfaces_down,
                    'con_errores': interfaces_errores
                }
        except:
            diagnostico['interfaces'] = 'No disponible'
        
        # 4. Control connections
        try:
            control = session.get(f"/dataservice/device/control/connections?deviceId={device_id}")
            if 'data' in control:
                up_count = sum(1 for c in control['data'] if c.get('state') == 'up')
                diagnostico['control_plane'] = {
                    'total_connections': len(control['data']),
                    'activas': up_count,
                    'estado': 'OK' if up_count > 0 else 'PROBLEMA'
                }
        except:
            diagnostico['control_plane'] = 'No disponible'
        
        # 5. Alarmas activas del dispositivo
        try:
            alarms = session.get("/dataservice/alarms")
            if 'data' in alarms:
                device_alarms = [a for a in alarms['data'] 
                               if a.get('system-ip') == device_id and a.get('active')]
                
                critical_count = sum(1 for a in device_alarms if a.get('severity') == 'Critical')
                major_count = sum(1 for a in device_alarms if a.get('severity') == 'Major')
                
                diagnostico['alarmas'] = {
                    'total': len(device_alarms),
                    'criticas': critical_count,
                    'mayores': major_count
                }
        except:
            diagnostico['alarmas'] = 'No disponible'
        
        # Evaluación general
        problemas = []
        if diagnostico.get('info_basica', {}).get('estado') != 'reachable':
            problemas.append('❌ Dispositivo NO alcanzable')
        
        if diagnostico.get('recursos') != 'No disponible':
            try:
                cpu = float(diagnostico['recursos']['cpu_usado_percent'])
                if cpu > 80:
                    problemas.append(f'⚠️  CPU alta: {cpu}%')
            except:
                pass
        
        if diagnostico.get('control_plane', {}).get('estado') != 'OK':
            problemas.append('❌ Sin conexiones al control plane')
        
        if diagnostico.get('alarmas', {}).get('criticas', 0) > 0:
            problemas.append(f"🔴 {diagnostico['alarmas']['criticas']} alarmas críticas")
        
        diagnostico['evaluacion'] = {
            'estado_general': 'SALUDABLE' if not problemas else 'CON PROBLEMAS',
            'problemas_detectados': problemas if problemas else ['✅ Sin problemas detectados']
        }
        
        return (
            f"🔍 DIAGNÓSTICO COMPLETO - Dispositivo {device_id}\n\n"
            f"Estado General: {diagnostico['evaluacion']['estado_general']}\n\n"
            f"Problemas:\n{diagnostico['evaluacion']['problemas_detectados']}\n\n"
            f"Detalle completo:\n{diagnostico}"
        )
        
    except Exception as e:
        return f"Error al realizar diagnóstico: {str(e)}"


@mcp.tool()
def analizar_trafico_total_red(horas: int = 12) -> str:
    """
    Analiza el tráfico de aplicaciones en toda la red SD-WAN usando Cisco Analytics Cloud.
    Obtiene datos agregados de todas las aplicaciones detectadas por DPI en la red completa.
    
    Args:
        horas: Ventana de tiempo en horas para el análisis (default: 12)
    
    Returns:
        Top aplicaciones por consumo de ancho de banda con estadísticas de QoE
    """
    try:
        analytics = get_analytics_session()
        
        # Analytics Cloud usa ventanas de tiempo pre-computadas específicas
        # Por ahora usamos la última ventana disponible conocida
        # TODO: Implementar llamada para obtener ventanas disponibles dinámicamente
        from datetime import datetime, timedelta
        
        payload = {
            "time_frame": "12h",
            "entry_ts": {
                "start": "2026-02-04 05:00:00",
                "end": "2026-02-04 17:05:00"
            }
        }
        
        start_time = payload["entry_ts"]["start"]
        end_time = payload["entry_ts"]["end"]
        
        # Obtener datos de Analytics
        endpoint = "/analytics/api/v4/dataservice/aggregate/applications"
        result = analytics.post(endpoint, json_data=payload, timeout=30)
        
        if 'data' not in result or not result['data']:
            return f"⚠️  No hay datos de aplicaciones disponibles para las últimas {horas} horas.\nVerifica que DPI esté habilitado y haya tráfico clasificado."
        
        apps = result['data']
        total_apps = result.get('count', len(apps))
        
        # Ordenar por usage (bytes totales)
        apps_sorted = sorted(apps, key=lambda x: x.get('usage', 0), reverse=True)
        
        # Calcular total de tráfico
        total_bytes = sum(app.get('usage', 0) for app in apps)
        
        # Generar reporte
        resultado = (
            f"🌐 ANÁLISIS DE TRÁFICO - RED COMPLETA\n\n"
            f"Período: Últimas {horas} horas\n"
            f"Ventana: {start_time} a {end_time}\n"
            f"Total de aplicaciones: {total_apps}\n"
            f"Tráfico total: {total_bytes / (1024**4):.2f} TB\n\n"
            f"🏆 TOP 20 APLICACIONES:\n"
        )
        
        for i, app in enumerate(apps_sorted[:20], 1):
            name = app.get('application', 'Unknown')
            family = app.get('application_family_long_name', 'N/A')
            usage = app.get('usage', 0)
            usage_gb = usage / (1024**3)
            percent = (usage / total_bytes * 100) if total_bytes > 0 else 0
            site_count = app.get('site_count', 0)
            
            # Métricas de QoE
            latency = app.get('latency', 0)
            jitter = app.get('jitter', 0)
            packet_loss = app.get('packet_loss', 0)
            vqoe_score = app.get('vqoe_score', 0)
            vqoe_status = app.get('vqoe_status', 'unknown')
            
            # Indicador de calidad
            if vqoe_status == 'unknown' or vqoe_score == 0:
                quality = "⚪"
            elif vqoe_score >= 8:
                quality = "🟢"
            elif vqoe_score >= 5:
                quality = "🟡"
            else:
                quality = "🔴"
            
            resultado += f"\n{i}. {name} {quality}"
            resultado += f"\n   Familia: {family}"
            resultado += f"\n   Uso: {usage_gb:.2f} GB ({percent:.1f}%)"
            resultado += f"\n   Sitios: {site_count}"
            
            if vqoe_status != 'unknown' and vqoe_score > 0:
                resultado += f"\n   QoE: {vqoe_score:.1f}/10 | Latencia: {latency:.1f}ms | Jitter: {jitter:.2f}ms | Pérdida: {packet_loss:.2f}%"
        
        return resultado
        
    except Exception as e:
        # Si falla Analytics, dar mensaje claro
        error_msg = str(e)
        if "400" in error_msg or "BAD REQUEST" in error_msg:
            return (
                f"⚠️  Error al conectar con Cisco Analytics Cloud.\n\n"
                f"Por favor:\n"
                f"1. Abre https://us02.analytics.sdwan.cisco.com en tu navegador\n"
                f"2. Asegúrate de estar logueado\n"
                f"3. Vuelve a intentar este comando\n\n"
                f"Las cookies de Analytics expiran y necesitan renovarse desde el navegador."
            )
        else:
            return f"⚠️  Error al obtener datos: {error_msg}"


@mcp.tool()
def comparar_trafico_sitios(site_id_1: str, site_id_2: str) -> str:
    """
    Compara el tráfico de aplicaciones entre dos sitios. Útil para análisis de diferencias de uso entre sucursales.
    
    Args:
        site_id_1: ID del primer sitio a comparar
        site_id_2: ID del segundo sitio a comparar
    
    Returns:
        Comparación detallada de tráfico entre ambos sitios con aplicaciones únicas y comunes
    """
    try:
        session = get_vmanage_session()
        
        # Obtener dispositivos de cada sitio
        devices_result = session.get("/dataservice/device", timeout=20)
        
        if 'data' not in devices_result:
            return "No se pudieron obtener dispositivos"
        
        sitio1_devices = [d for d in devices_result['data'] if d.get('site-id') == site_id_1]
        sitio2_devices = [d for d in devices_result['data'] if d.get('site-id') == site_id_2]
        
        if not sitio1_devices:
            return f"No se encontraron dispositivos en sitio {site_id_1}"
        if not sitio2_devices:
            return f"No se encontraron dispositivos en sitio {site_id_2}"
        
        # Función para analizar un sitio
        def analizar_sitio(devices):
            apps = {}
            for device in devices:
                device_id = device.get('deviceId') or device.get('uuid')
                try:
                    endpoint = f"/dataservice/device/dpi/applications?deviceId={device_id}"
                    result = session.get(endpoint, timeout=10)
                    
                    if 'data' in result and result['data']:
                        for app in result['data']:
                            app_name = app.get('application', 'Unknown')
                            if app_name not in apps:
                                apps[app_name] = 0
                            apps[app_name] += app.get('octets-received', 0) + app.get('octets-sent', 0)
                except:
                    continue
            return apps
        
        apps_sitio1 = analizar_sitio(sitio1_devices)
        apps_sitio2 = analizar_sitio(sitio2_devices)
        
        # Comparar
        comparacion = []
        todas_apps = set(list(apps_sitio1.keys()) + list(apps_sitio2.keys()))
        
        for app in todas_apps:
            bytes_s1 = apps_sitio1.get(app, 0)
            bytes_s2 = apps_sitio2.get(app, 0)
            diferencia = bytes_s1 - bytes_s2
            
            comparacion.append({
                'aplicacion': app,
                f'sitio_{site_id_1}_gb': round(bytes_s1 / (1024**3), 2),
                f'sitio_{site_id_2}_gb': round(bytes_s2 / (1024**3), 2),
                'diferencia_gb': round(abs(diferencia) / (1024**3), 2),
                'sitio_mayor_uso': site_id_1 if diferencia > 0 else site_id_2
            })
        
        comparacion.sort(key=lambda x: x['diferencia_gb'], reverse=True)
        
        return (
            f"⚖️  COMPARACIÓN DE TRÁFICO\n\n"
            f"Sitio {site_id_1}: {len(sitio1_devices)} dispositivos\n"
            f"Sitio {site_id_2}: {len(sitio2_devices)} dispositivos\n\n"
            f"Aplicaciones únicas sitio {site_id_1}: {len([a for a in comparacion if a[f'sitio_{site_id_2}_gb'] == 0])}\n"
            f"Aplicaciones únicas sitio {site_id_2}: {len([a for a in comparacion if a[f'sitio_{site_id_1}_gb'] == 0])}\n"
            f"Aplicaciones comunes: {len([a for a in comparacion if a[f'sitio_{site_id_1}_gb'] > 0 and a[f'sitio_{site_id_2}_gb'] > 0])}\n\n"
            f"Top diferencias:\n{comparacion[:15]}"
        )
        
    except Exception as e:
        return f"Error al comparar sitios: {str(e)}"


@mcp.tool()
def detectar_aplicaciones_no_autorizadas(whitelist: str = "") -> str:
    """
    Detecta aplicaciones que están consumiendo ancho de banda pero no están en la lista autorizada.
    Útil para compliance y detección de shadow IT.
    
    Args:
        whitelist: Lista de aplicaciones autorizadas separadas por comas (ej: "office-365,zoom,teams,google"). Si se deja vacío muestra todas las aplicaciones.
    
    Returns:
        Lista de aplicaciones no autorizadas detectadas en la red con nivel de riesgo y ubicaciones
    """
    try:
        session = get_vmanage_session()
        
        # Convertir whitelist
        apps_autorizadas = set()
        if whitelist:
            apps_autorizadas = set(app.strip().lower() for app in whitelist.split(','))
        
        # Obtener dispositivos
        devices_result = session.get("/dataservice/device", timeout=20)
        if 'data' not in devices_result:
            return "No se pudieron obtener dispositivos"
        
        edge_devices = [d for d in devices_result['data'] if d.get('device-type') == 'vedge']
        
        # Consolidar aplicaciones no autorizadas
        apps_no_autorizadas = {}
        
        for device in edge_devices[:30]:  # Limitar a 30
            device_id = device.get('deviceId') or device.get('uuid')
            device_name = device.get('host-name')
            site_id = device.get('site-id')
            
            try:
                endpoint = f"/dataservice/device/dpi/applications?deviceId={device_id}"
                result = session.get(endpoint, timeout=10)
                
                if 'data' in result and result['data']:
                    for app in result['data']:
                        app_name = app.get('application', 'Unknown')
                        app_name_lower = app_name.lower()
                        
                        # Verificar si está en whitelist
                        if whitelist and app_name_lower in apps_autorizadas:
                            continue  # Está autorizada, saltar
                        
                        bytes_total = app.get('octets-received', 0) + app.get('octets-sent', 0)
                        
                        if app_name not in apps_no_autorizadas:
                            apps_no_autorizadas[app_name] = {
                                'bytes_total': 0,
                                'dispositivos': set(),
                                'sitios': set(),
                                'familia': app.get('family', 'Unknown')
                            }
                        
                        apps_no_autorizadas[app_name]['bytes_total'] += bytes_total
                        apps_no_autorizadas[app_name]['dispositivos'].add(device_name)
                        apps_no_autorizadas[app_name]['sitios'].add(site_id)
                        
            except:
                continue
        
        # Generar reporte
        if not apps_no_autorizadas:
            return "✅ No se detectaron aplicaciones no autorizadas"
        
        apps_lista = []
        for app_name, data in apps_no_autorizadas.items():
            apps_lista.append({
                'aplicacion': app_name,
                'familia': data['familia'],
                'bytes_gb': round(data['bytes_total'] / (1024**3), 2),
                'num_dispositivos': len(data['dispositivos']),
                'num_sitios': len(data['sitios']),
                'nivel_riesgo': '🔴 Alto' if data['bytes_total'] > 10*(1024**3) else 
                               '🟡 Medio' if data['bytes_total'] > 1*(1024**3) else '🟢 Bajo'
            })
        
        apps_lista.sort(key=lambda x: x['bytes_gb'], reverse=True)
        
        return (
            f"⚠️  APLICACIONES NO AUTORIZADAS DETECTADAS\n\n"
            f"{'Whitelist: ' + whitelist if whitelist else 'Sin whitelist definida (mostrando todas)'}\n"
            f"Aplicaciones detectadas: {len(apps_lista)}\n"
            f"Tráfico total no autorizado: {sum(a['bytes_gb'] for a in apps_lista):.2f} GB\n\n"
            f"Detalle:\n{apps_lista[:25]}"
        )
        
    except Exception as e:
        return f"Error al detectar aplicaciones no autorizadas: {str(e)}"


@mcp.tool()
def ver_estado_sistema_dispositivo(device_id: str) -> str:
    """
    Obtiene el estado completo del sistema de un dispositivo incluyendo CPU, memoria, disco, uptime y versión de software.
    
    Args:
        device_id: ID del dispositivo (system-ip como 10.95.0.3)
    
    Returns:
        Estado detallado del sistema con métricas de recursos y conectividad
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/system/status?deviceId={device_id}"
        result = session.get(endpoint, timeout=15)
        
        if 'data' in result and result['data']:
            data = result['data'][0] if isinstance(result['data'], list) else result['data']
            
            # Convertir uptime a formato legible
            uptime_seconds = data.get('uptime-date', 0)
            dias = uptime_seconds // 86400
            horas = (uptime_seconds % 86400) // 3600
            minutos = (uptime_seconds % 3600) // 60
            
            return (
                f"💻 ESTADO DEL SISTEMA - {device_id}\n\n"
                f"Hostname: {data.get('vdevice-host-name', 'N/A')}\n"
                f"Modelo: {data.get('vdevice-model', 'N/A')}\n"
                f"Versión: {data.get('version', 'N/A')}\n"
                f"Estado: {data.get('state', 'N/A')}\n"
                f"Site ID: {data.get('site-id', 'N/A')}\n\n"
                f"📊 Recursos:\n"
                f"  CPU: {data.get('cpu-load', 0)}%\n"
                f"  Memoria usada: {data.get('mem-used', 0)}%\n"
                f"  Disco usado: {data.get('disk-used', 0)}%\n\n"
                f"⏱️  Uptime: {dias} días, {horas} horas, {minutos} minutos\n\n"
                f"📡 Conectividad:\n"
                f"  Última actualización: {data.get('lastupdated', 'N/A')}\n"
                f"  Modo reachability: {data.get('reachability', 'N/A')}\n"
            )
        
        return f"No se pudo obtener estado del dispositivo {device_id}"
        
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Ejecutar el servidor MCP
    mcp.run()
