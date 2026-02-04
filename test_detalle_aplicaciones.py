#!/usr/bin/env python3
"""
Test de la función analizar_detalle_aplicaciones
"""

import sys
sys.path.insert(0, '/home/tsul/Documentos/serv_mcp')

import os
import requests
import urllib3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

class AnalyticsCloudSession:
    def __init__(self):
        self.base_url = "https://us02.analytics.sdwan.cisco.com"
        self.session = requests.Session()
        self.session.verify = False
        
        csrf_token = None
        overlay_id = None
        session_cookie = None
        
        cookies_file = '.analytics_cookies.json'
        
        if os.path.exists(cookies_file):
            with open(cookies_file, 'r') as f:
                cookies_data = json.load(f)
            
            session_cookie = cookies_data.get('session')
            csrf_token = cookies_data.get('csrf_token')
            overlay_id = cookies_data.get('overlay_id')
            
            if session_cookie:
                self.session.cookies.set('session', session_cookie, 
                                        domain='.analytics.sdwan.cisco.com', 
                                        path='/')
            if csrf_token:
                self.session.cookies.set('okta-oauth-state', csrf_token,
                                        domain='.analytics.sdwan.cisco.com',
                                        path='/')
            if overlay_id:
                self.session.cookies.set('cl-overlay-id', overlay_id,
                                        domain='.analytics.sdwan.cisco.com',
                                        path='/')
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'x-csrftoken': csrf_token if csrf_token else '',
            'sdwan-overlay': overlay_id if overlay_id else '',
            'Origin': 'https://us02.analytics.sdwan.cisco.com',
            'Referer': 'https://us02.analytics.sdwan.cisco.com/analytics/v4/overview',
        })
    
    def post(self, endpoint, json_data, timeout=30):
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=json_data, timeout=timeout)
        response.raise_for_status()
        return response.json()

def get_analytics_session():
    return AnalyticsCloudSession()

# Función del server.py
def analizar_detalle_aplicaciones(aplicaciones: str, top_sitios: int = 10) -> str:
    try:
        analytics = get_analytics_session()
        
        payload = {
            "time_frame": "12h",
            "entry_ts": {
                "start": "2026-02-04 05:00:00",
                "end": "2026-02-04 17:05:00"
            }
        }
        
        start_time = payload["entry_ts"]["start"]
        end_time = payload["entry_ts"]["end"]
        
        # Obtener datos de aplicaciones
        endpoint_apps = "/analytics/api/v4/dataservice/aggregate/applications"
        result_apps = analytics.post(endpoint_apps, json_data=payload, timeout=30)
        
        if 'data' not in result_apps or not result_apps['data']:
            return "⚠️  No hay datos de aplicaciones disponibles."
        
        # Obtener datos de sitios
        endpoint_sites = "/analytics/api/v4/dataservice/aggregate/sites"
        result_sites = analytics.post(endpoint_sites, json_data=payload, timeout=30)
        
        sites_data = result_sites.get('data', [])
        
        # Obtener datos de dispositivos
        endpoint_devices = "/analytics/api/v4/dataservice/aggregate/devices"
        result_devices = analytics.post(endpoint_devices, json_data=payload, timeout=30)
        
        devices_data = result_devices.get('data', [])
        
        # Filtrar aplicaciones solicitadas
        apps_solicitadas = [a.strip().lower() for a in aplicaciones.split(',')]
        apps_data = [app for app in result_apps['data'] 
                     if app.get('application', '').lower() in apps_solicitadas]
        
        if not apps_data:
            return f"⚠️  No se encontraron las aplicaciones especificadas: {aplicaciones}\n\nAplicaciones disponibles: {', '.join([a['application'] for a in result_apps['data'][:20]])}"
        
        # Generar reporte
        resultado = (
            f"📊 ANÁLISIS DETALLADO DE APLICACIONES\n\n"
            f"Ventana: {start_time} a {end_time}\n"
            f"Total de sitios: {len(sites_data)}\n"
            f"Total de dispositivos: {len(devices_data)}\n"
            f"Aplicaciones analizadas: {len(apps_data)}\n"
            f"{'='*70}\n"
        )
        
        # Ordenar aplicaciones por uso
        apps_data_sorted = sorted(apps_data, key=lambda x: x.get('usage', 0), reverse=True)
        
        for app in apps_data_sorted:
            name = app.get('application', 'unknown')
            family = app.get('application_family_long_name', 'N/A')
            usage = app.get('usage', 0)
            usage_gb = usage / (1024**3)
            site_count = app.get('site_count', 0)
            
            vqoe_score = app.get('vqoe_score', 0)
            latency = app.get('latency', 0)
            jitter = app.get('jitter', 0)
            packet_loss = app.get('packet_loss', 0)
            
            # Indicador de calidad
            if vqoe_score >= 7:
                quality = "🟢"
            elif vqoe_score >= 5:
                quality = "🟡"
            else:
                quality = "🔴"
            
            resultado += f"\n\n{'='*70}\n"
            resultado += f"📱 APLICACIÓN: {name.upper()} {quality}\n"
            resultado += f"{'='*70}\n"
            resultado += f"Familia: {family}\n"
            resultado += f"Uso total: {usage_gb:.2f} GB\n"
            resultado += f"Sitios usando: {site_count}\n"
            resultado += f"QoE global: {vqoe_score:.1f}/10 | Latencia: {latency:.1f}ms | "
            resultado += f"Jitter: {jitter:.2f}ms | Pérdida: {packet_loss:.2f}%\n"
            
            # Top sitios para esta aplicación (ordenados por uso total del sitio)
            resultado += f"\n📍 TOP {min(top_sitios, len(sites_data))} SITIOS CON MAYOR TRÁFICO:\n"
            resultado += f"{'-'*70}\n"
            
            # Ordenar sitios por uso total
            sites_sorted = sorted(sites_data, key=lambda x: x.get('usage', 0), reverse=True)[:top_sitios]
            
            for i, site in enumerate(sites_sorted, 1):
                site_name = site.get('site_name', site.get('site_id', 'unknown'))
                site_usage = site.get('usage', 0)
                site_usage_gb = site_usage / (1024**3)
                site_qoe = site.get('vqoe_score', 0)
                site_devices = site.get('device_count', 0)
                site_city = site.get('city', 'N/A')
                
                # Indicador QoE del sitio
                if site_qoe >= 7:
                    site_quality = "🟢"
                elif site_qoe >= 5:
                    site_quality = "🟡"
                else:
                    site_quality = "🔴"
                
                resultado += f"\n{i}. {site_name} ({site_city}) {site_quality}\n"
                resultado += f"   Uso total sitio: {site_usage_gb:.2f} GB\n"
                resultado += f"   QoE sitio: {site_qoe:.1f}/10\n"
                resultado += f"   Dispositivos: {site_devices}\n"
                
                # Buscar dispositivos de este sitio
                site_id = site.get('site_id', '')
                site_devices_list = [d for d in devices_data 
                                   if d.get('site_id') == site_id or 
                                   d.get('site_name') == site_name]
                
                if site_devices_list:
                    # Top 3 dispositivos del sitio
                    devices_sorted = sorted(site_devices_list, 
                                          key=lambda x: x.get('usage', 0), 
                                          reverse=True)[:3]
                    
                    resultado += f"   \n   🖥️  Dispositivos principales:\n"
                    for j, dev in enumerate(devices_sorted, 1):
                        dev_name = dev.get('local_host_name', 'unknown')
                        dev_ip = dev.get('local_system_ip', 'N/A')
                        dev_usage = dev.get('usage', 0)
                        dev_usage_gb = dev_usage / (1024**3)
                        dev_status = dev.get('availability_status', 'unknown')
                        
                        status_icon = "✅" if dev_status == 'up' else "⚠️"
                        
                        resultado += f"      {j}. {dev_name} ({dev_ip}) {status_icon}\n"
                        resultado += f"         Uso: {dev_usage_gb:.2f} GB\n"
        
        resultado += f"\n\n{'='*70}\n"
        resultado += f"💡 NOTA: Los datos mostrados son agregados por sitio.\n"
        resultado += f"Para IPs origen/destino específicas, accede a:\n"
        resultado += f"vManage → Monitor → Applications → Application-Aware Routing\n"
        
        return resultado
        
    except Exception as e:
        return f"⚠️  Error: {e}"


# Test
print("="*70)
print("TEST: analizar_detalle_aplicaciones")
print("="*70)

print("\n🔍 Probando con aplicaciones: ssl, http\n")
resultado = analizar_detalle_aplicaciones("ssl,http", top_sitios=5)
print(resultado)
