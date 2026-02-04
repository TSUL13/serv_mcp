#!/usr/bin/env python3
"""
CLI gratuito para gestionar Cisco SD-WAN sin necesidad de Claude
Usa las mismas funciones del servidor MCP directamente
"""

import sys
import os
import requests
import urllib3
from typing import Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cargar variables de entorno
load_dotenv()


class VManageSession:
    """Clase para gestionar la sesión de autenticación con vManage"""
    
    def __init__(self, ip: str, username: str, password: str):
        self.base_url = f"https://{ip}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
        self.cookies = None
        
    def login(self) -> bool:
        """Realiza el login inicial en vManage"""
        try:
            login_url = f"{self.base_url}/j_security_check"
            payload = {
                'j_username': self.username,
                'j_password': self.password
            }
            
            response = self.session.post(login_url, data=payload, timeout=30)
            
            if response.status_code == 200 and 'JSESSIONID' in self.session.cookies:
                token_url = f"{self.base_url}/dataservice/client/token"
                token_response = self.session.get(token_url, timeout=30)
                
                if token_response.status_code == 200:
                    self.token = token_response.text
                    self.session.headers.update({
                        'X-XSRF-TOKEN': self.token,
                        'Content-Type': 'application/json'
                    })
                    return True
            
            return False
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error al conectar con vManage: {str(e)}")
    
    def get(self, endpoint: str, timeout: int = 30) -> Dict[str, Any]:
        """Realiza una petición GET al API de vManage"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout al consultar {endpoint}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error en petición GET a {endpoint}: {str(e)}")


def get_vmanage_session() -> VManageSession:
    """Crea y autentica una sesión con vManage"""
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


def listar_dispositivos() -> str:
    """Lista todos los dispositivos en el inventario de SD-WAN"""
    try:
        session = get_vmanage_session()
        endpoint = "/dataservice/device"
        result = session.get(endpoint)
        
        if 'data' in result:
            devices = result['data']
            
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
        
    except Exception as e:
        return f"Error: {str(e)}"


def ver_salud_equipo(device_id: str) -> str:
    """Consulta el estado de salud de un dispositivo específico"""
    try:
        session = get_vmanage_session()
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
            
            return f"Estado de salud del dispositivo {device_id}:\n\n{health_info}"
        
        return f"No se encontró el dispositivo con ID: {device_id}"
        
    except Exception as e:
        return f"Error: {str(e)}"


def ver_sesiones_bfd(device_id: str) -> str:
    """Consulta el estado de las sesiones BFD para un dispositivo"""
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/bfd/sessions?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            bfd_sessions = result['data']
            
            if not bfd_sessions:
                return f"No hay sesiones BFD activas para el dispositivo {device_id}"
            
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
        
    except Exception as e:
        return f"Error: {str(e)}"


def listar_alarmas_criticas() -> str:
    """Lista todas las alarmas de nivel crítico de las últimas 24 horas"""
    try:
        session = get_vmanage_session()
        
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        from_time = int(yesterday.timestamp() * 1000)
        
        endpoint = "/dataservice/alarms"
        result = session.get(endpoint)
        
        if 'data' in result:
            all_alarms = result['data']
            
            critical_alarms = []
            for alarm in all_alarms:
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
        
    except Exception as e:
        return f"Error: {str(e)}"

def print_menu():
    """Muestra el menú principal"""
    print("\n" + "="*60)
    print("  🌐 CISCO SD-WAN MANAGER - CLI")
    print("="*60)
    print("\n📋 Opciones disponibles:\n")
    print("  1. Listar todos los dispositivos")
    print("  2. Ver salud de un equipo específico")
    print("  3. Ver sesiones BFD de un dispositivo")
    print("  4. Listar alarmas críticas")
    print("  5. Salir")
    print("\n" + "="*60)

def main():
    """Función principal del CLI"""
    
    # Verificar credenciales
    if not all([os.getenv('VMANAGE_IP'), os.getenv('VMANAGE_USERNAME'), os.getenv('VMANAGE_PASSWORD')]):
        print("❌ Error: Configura las credenciales en el archivo .env")
        print("   Necesitas: VMANAGE_IP, VMANAGE_USERNAME, VMANAGE_PASSWORD")
        sys.exit(1)
    
    print("\n🔗 Conectando a vManage: {}".format(os.getenv('VMANAGE_IP')))
    
    while True:
        print_menu()
        
        try:
            opcion = input("\n👉 Selecciona una opción (1-5): ").strip()
            
            if opcion == "1":
                print("\n🔄 Consultando dispositivos...")
                print("-" * 60)
                resultado = server.listar_dispositivos()
                print(resultado)
                
            elif opcion == "2":
                device_id = input("\n📝 Ingresa el Device ID (System IP): ").strip()
                if device_id:
                    print(f"\n🔄 Consultando salud del dispositivo {device_id}...")
                    print("-" * 60)
                    resultado = server.ver_salud_equipo(device_id)
                    print(resultado)
                else:
                    print("❌ Device ID no puede estar vacío")
                    
            elif opcion == "3":
                device_id = input("\n📝 Ingresa el Device ID (System IP): ").strip()
                if device_id:
                    print(f"\n🔄 Consultando sesiones BFD de {device_id}...")
                    print("-" * 60)
                    resultado = server.ver_sesiones_bfd(device_id)
                    print(resultado)
                else:
                    print("❌ Device ID no puede estar vacío")
                    
            elif opcion == "4":
                print("\n🔄 Consultando alarmas críticas...")
                print("-" * 60)
                resultado = server.listar_alarmas_criticas()
                print(resultado)
                
            elif opcion == "5":
                print("\n👋 ¡Hasta luego!\n")
                sys.exit(0)
                
            else:
                print("\n❌ Opción inválida. Por favor selecciona 1-5.")
            
            input("\n⏎ Presiona Enter para continuar...")
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            input("\n⏎ Presiona Enter para continuar...")

if __name__ == "__main__":
    main()
