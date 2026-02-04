#!/usr/bin/env python3
"""
Test manual de la función analizar_trafico_total_red()
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, '/home/tsul/Documentos/serv_mcp')

# Importar la sesión
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

class VManageSession:
    def __init__(self):
        self.base_url = f"https://{os.getenv('VMANAGE_IP')}"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'Cookie': f"JSESSIONID={os.getenv('VMANAGE_JSESSIONID')}",
            'X-XSRF-TOKEN': os.getenv('VMANAGE_XSRF_TOKEN'),
            'Content-Type': 'application/json'
        })
    
    def get(self, endpoint, timeout=30):
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, timeout=timeout)
        return response.json()

def get_vmanage_session():
    return VManageSession()

# Copiar la función exacta de server.py
def analizar_trafico_total_red() -> str:
    try:
        session = get_vmanage_session()
        
        # 1. Obtener todos los dispositivos edge
        print("🔍 Obteniendo dispositivos...")
        devices_result = session.get("/dataservice/device", timeout=20)
        
        if 'data' not in devices_result:
            return "No se pudieron obtener dispositivos"
        
        edge_devices = [
            d for d in devices_result['data'] 
            if d.get('device-type') in ['vedge', 'vmanage']
        ]
        
        print(f"   ✅ Encontrados {len(edge_devices)} dispositivos edge")
        
        # 2. Consolidar aplicaciones de todos los dispositivos
        apps_consolidadas = {}
        dispositivos_procesados = 0
        dispositivos_con_error = 0
        dispositivos_sin_datos = 0
        
        print(f"\n🔄 Procesando dispositivos (limitado a 50)...")
        
        for i, device in enumerate(edge_devices[:50], 1):
            device_id = device.get('deviceId') or device.get('uuid')
            device_name = device.get('host-name')
            
            print(f"   [{i}/50] {device_name} ({device_id})...", end=" ")
            
            try:
                endpoint = f"/dataservice/device/dpi/applications?deviceId={device_id}"
                result = session.get(endpoint, timeout=10)
                
                if 'data' in result and result['data']:
                    dispositivos_procesados += 1
                    num_apps = len(result['data'])
                    print(f"✅ {num_apps} apps")
                    
                    for app in result['data']:
                        app_name = app.get('application', 'Unknown')
                        app_family = app.get('family', 'Other')
                        
                        if app_name not in apps_consolidadas:
                            apps_consolidadas[app_name] = {
                                'familia': app_family,
                                'bytes_rx': 0,
                                'bytes_tx': 0,
                                'paquetes_rx': 0,
                                'paquetes_tx': 0,
                                'dispositivos': set(),
                                'sesiones_totales': 0
                            }
                        
                        apps_consolidadas[app_name]['bytes_rx'] += app.get('octets-received', 0)
                        apps_consolidadas[app_name]['bytes_tx'] += app.get('octets-sent', 0)
                        apps_consolidadas[app_name]['paquetes_rx'] += app.get('packets-received', 0)
                        apps_consolidadas[app_name]['paquetes_tx'] += app.get('packets-sent', 0)
                        apps_consolidadas[app_name]['sesiones_totales'] += app.get('active-flows', 0)
                        apps_consolidadas[app_name]['dispositivos'].add(device_name)
                else:
                    dispositivos_sin_datos += 1
                    print("⚠️  Sin datos")
                        
            except Exception as e:
                dispositivos_con_error += 1
                print(f"❌ Error: {str(e)[:50]}")
                continue
        
        # 3. Generar reporte
        print(f"\n📊 RESUMEN:")
        print(f"   Dispositivos con datos: {dispositivos_procesados}")
        print(f"   Dispositivos sin datos: {dispositivos_sin_datos}")
        print(f"   Dispositivos con error: {dispositivos_con_error}")
        print(f"   Total aplicaciones encontradas: {len(apps_consolidadas)}")
        
        if not apps_consolidadas:
            return "\n⚠️  No se encontraron datos de aplicaciones en ningún dispositivo\n\nPosibles causas:\n1. DPI no está habilitado en los dispositivos\n2. No hay tráfico clasificado aún\n3. Los dispositivos no tienen datos históricos"
        
        apps_lista = []
        total_bytes_red = 0
        
        for app_name, data in apps_consolidadas.items():
            bytes_total = data['bytes_rx'] + data['bytes_tx']
            total_bytes_red += bytes_total
            
            apps_lista.append({
                'aplicacion': app_name,
                'familia': data['familia'],
                'bytes_total_tb': round(bytes_total / (1024**4), 3),
                'bytes_rx_tb': round(data['bytes_rx'] / (1024**4), 3),
                'bytes_tx_tb': round(data['bytes_tx'] / (1024**4), 3),
                'num_dispositivos': len(data['dispositivos']),
                'sesiones_activas': data['sesiones_totales'],
                'porcentaje_trafico': 0
            })
        
        # Calcular porcentajes
        for app in apps_lista:
            app['porcentaje_trafico'] = round(
                (app['bytes_total_tb'] / (total_bytes_red / (1024**4))) * 100, 2
            )
        
        # Ordenar por bytes totales
        apps_lista.sort(key=lambda x: x['bytes_total_tb'], reverse=True)
        
        resultado = (
            f"\n🌐 ANÁLISIS DE TRÁFICO - RED COMPLETA\n\n"
            f"Dispositivos analizados: {dispositivos_procesados}/{len(edge_devices)}\n"
            f"Aplicaciones detectadas: {len(apps_lista)}\n"
            f"Tráfico total: {total_bytes_red / (1024**4):.2f} TB\n\n"
            f"Top 20 aplicaciones:\n"
        )
        
        for i, app in enumerate(apps_lista[:20], 1):
            resultado += f"\n{i}. {app['aplicacion']}"
            resultado += f"\n   Familia: {app['familia']}"
            resultado += f"\n   Tráfico: {app['bytes_total_tb']} TB ({app['porcentaje_trafico']}%)"
            resultado += f"\n   Dispositivos: {app['num_dispositivos']}"
            resultado += f"\n   Sesiones: {app['sesiones_activas']}"
        
        return resultado
        
    except Exception as e:
        return f"Error al analizar tráfico de red: {str(e)}"

# Ejecutar test
if __name__ == "__main__":
    print("=" * 70)
    print("TEST DE FUNCIÓN: analizar_trafico_total_red()")
    print("=" * 70)
    
    resultado = analizar_trafico_total_red()
    print("\n" + "=" * 70)
    print("RESULTADO:")
    print("=" * 70)
    print(resultado)
