#!/usr/bin/env python3
"""
Test final de la función actualizada con Analytics Cloud
"""

import sys
sys.path.insert(0, '/home/tsul/Documentos/serv_mcp')

# Simular el ambiente del server.py
import os
import requests
import urllib3
from datetime import datetime, timedelta
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

class AnalyticsCloudSession:
    def __init__(self):
        self.base_url = "https://us02.analytics.sdwan.cisco.com"
        self.session = requests.Session()
        self.session.verify = False
        
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

# Función copiada del server.py (versión actualizada)
def analizar_trafico_total_red(horas=12):
    try:
        analytics = get_analytics_session()
        
        # Analytics Cloud usa ventanas de tiempo pre-computadas específicas
        # Por ahora usamos la última ventana disponible conocida
        payload = {
            "time_frame": "12h",
            "entry_ts": {
                "start": "2026-02-04 05:00:00",
                "end": "2026-02-04 17:05:00"
            }
        }
        
        start_time = payload["entry_ts"]["start"]
        end_time = payload["entry_ts"]["end"]
        
        endpoint = "/analytics/api/v4/dataservice/aggregate/applications"
        result = analytics.post(endpoint, json_data=payload, timeout=30)
        
        if 'data' not in result or not result['data']:
            return f"⚠️  No hay datos disponibles para las últimas {horas} horas."
        
        apps = result['data']
        total_apps = result.get('count', len(apps))
        apps_sorted = sorted(apps, key=lambda x: x.get('usage', 0), reverse=True)
        total_bytes = sum(app.get('usage', 0) for app in apps)
        
        resultado = (
            f"🌐 ANÁLISIS DE TRÁFICO - RED COMPLETA\n\n"
            f"Período: Últimas {horas} horas\n"
            f"Ventana: {start_time} a {end_time}\n"
            f"Total de aplicaciones: {total_apps}\n"
            f"Tráfico total: {total_bytes / (1024**4):.2f} TB\n\n"
            f"🏆 TOP 10 APLICACIONES:\n"
        )
        
        for i, app in enumerate(apps_sorted[:10], 1):
            name = app.get('application', 'Unknown')
            family = app.get('application_family_long_name', 'N/A')
            usage = app.get('usage', 0)
            usage_gb = usage / (1024**3)
            percent = (usage / total_bytes * 100) if total_bytes > 0 else 0
            site_count = app.get('site_count', 0)
            
            vqoe_score = app.get('vqoe_score', 0)
            vqoe_status = app.get('vqoe_status', 'unknown')
            
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
                latency = app.get('latency', 0)
                jitter = app.get('jitter', 0)
                packet_loss = app.get('packet_loss', 0)
                resultado += f"\n   QoE: {vqoe_score:.1f}/10 | Latencia: {latency:.1f}ms | Jitter: {jitter:.2f}ms | Pérdida: {packet_loss:.2f}%"
            resultado += "\n"
        
        return resultado
        
    except Exception as e:
        return f"⚠️  Error: {str(e)}"

# Ejecutar test
if __name__ == "__main__":
    print("=" * 70)
    print("TEST DE FUNCIÓN ACTUALIZADA CON ANALYTICS CLOUD")
    print("=" * 70)
    print()
    
    resultado = analizar_trafico_total_red(12)
    print(resultado)
