#!/usr/bin/env python3
"""
API REST para vManage - Compatible con GPT y Gemini
Convierte las funciones MCP en endpoints HTTP
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional
import os
from dotenv import load_dotenv

# Importar la lógica existente
from browser_cookies import BrowserCookieExtractor
import requests
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

load_dotenv()

app = FastAPI(
    title="vManage API",
    description="API REST para consultar Cisco SD-WAN vManage - Compatible con GPT/Gemini",
    version="1.0.0"
)

# Habilitar CORS para llamadas desde navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clase de sesión reutilizable
class VManageSession:
    def __init__(self):
        self.vmanage_ip = os.getenv("VMANAGE_IP")
        self.base_url = f"https://{self.vmanage_ip}"
        self.session = requests.Session()
        self.session.verify = False
        self._authenticate()
    
    def _authenticate(self):
        """Obtener cookies del navegador"""
        extractor = BrowserCookieExtractor(self.vmanage_ip)
        cookies = extractor.get_cookies_dict()
        
        if not cookies.get('JSESSIONID'):
            raise Exception("No se encontró JSESSIONID en el navegador")
        
        self.session.cookies.set('JSESSIONID', cookies['JSESSIONID'])
        
        if cookies.get('XSRF-TOKEN'):
            self.session.headers.update({'X-XSRF-TOKEN': cookies['XSRF-TOKEN']})
    
    def get(self, endpoint: str, timeout: int = 10):
        """GET request a vManage"""
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# Inicializar sesión global
vmanage = VManageSession()

# Modelos Pydantic para requests
class DeviceHealthRequest(BaseModel):
    device_id: str

class BFDRequest(BaseModel):
    device_id: str

class CPUMemoryRequest(BaseModel):
    device_id: str

class InterfaceStatsRequest(BaseModel):
    device_id: str

class OMPTunnelsRequest(BaseModel):
    device_id: str

class DeviceSearchRequest(BaseModel):
    criterio: str
    valor: str

class SiteDevicesRequest(BaseModel):
    site_id: str

class DiagnosticRequest(BaseModel):
    device_id: str

# ============================================================================
# ENDPOINTS - Uno por cada función del servidor MCP
# ============================================================================

@app.get("/")
def root():
    """Información de la API"""
    return {
        "api": "vManage REST API",
        "version": "1.0.0",
        "compatible_with": ["GPT-4", "Gemini", "Claude (sin MCP)", "Cualquier IA"],
        "endpoints": [
            "/devices",
            "/devices/{device_id}/health",
            "/devices/{device_id}/bfd",
            "/devices/{device_id}/cpu-memory",
            "/devices/{device_id}/interfaces",
            "/devices/{device_id}/omp-tunnels",
            "/alarms/critical",
            "/control-connections",
            "/network-summary",
            "/bfd/total",
            "/applications/top",
            "/search",
            "/sites/{site_id}/devices",
            "/security/events",
            "/devices/{device_id}/diagnostic"
        ]
    }

@app.get("/devices")
def list_devices():
    """Listar todos los dispositivos"""
    data = vmanage.get("/dataservice/device")
    return {
        "total": len(data.get("data", [])),
        "devices": data.get("data", [])
    }

@app.get("/devices/{device_id}/health")
def device_health(device_id: str):
    """Salud de un dispositivo específico"""
    data = vmanage.get(f"/dataservice/device/system/status?deviceId={device_id}")
    return data

@app.get("/devices/{device_id}/bfd")
def bfd_sessions(device_id: str):
    """Sesiones BFD de un dispositivo"""
    data = vmanage.get(f"/dataservice/device/bfd/sessions?deviceId={device_id}")
    sessions = data.get("data", [])
    
    total = len(sessions)
    up = sum(1 for s in sessions if s.get("state") == "up")
    down = total - up
    
    return {
        "device_id": device_id,
        "total_sessions": total,
        "up": up,
        "down": down,
        "health_percentage": (up/total*100) if total > 0 else 0,
        "sessions": sessions
    }

@app.get("/devices/{device_id}/cpu-memory")
def cpu_memory(device_id: str):
    """Uso de CPU y memoria"""
    data = vmanage.get(f"/dataservice/device/system/status?deviceId={device_id}")
    return data

@app.get("/devices/{device_id}/interfaces")
def interface_stats(device_id: str):
    """Estadísticas de interfaces"""
    data = vmanage.get(f"/dataservice/device/interface?deviceId={device_id}")
    return data

@app.get("/devices/{device_id}/omp-tunnels")
def omp_tunnels(device_id: str):
    """Túneles OMP"""
    data = vmanage.get(f"/dataservice/device/omp/peers?deviceId={device_id}")
    return data

@app.get("/alarms/critical")
def critical_alarms():
    """Alarmas críticas"""
    data = vmanage.get("/dataservice/alarms")
    alarms = data.get("data", [])
    critical = [a for a in alarms if a.get("severity") == "Critical"]
    return {
        "total_critical": len(critical),
        "alarms": critical
    }

@app.get("/control-connections")
def control_connections():
    """Conexiones de control"""
    data = vmanage.get("/dataservice/device/control/connections")
    return data

@app.get("/network-summary")
def network_summary():
    """Resumen de la red"""
    devices = vmanage.get("/dataservice/device").get("data", [])
    alarms = vmanage.get("/dataservice/alarms").get("data", [])
    
    total_devices = len(devices)
    devices_up = sum(1 for d in devices if d.get("reachability") == "reachable")
    devices_down = total_devices - devices_up
    
    critical_alarms = sum(1 for a in alarms if a.get("severity") == "Critical")
    
    return {
        "total_devices": total_devices,
        "devices_up": devices_up,
        "devices_down": devices_down,
        "health_percentage": (devices_up/total_devices*100) if total_devices > 0 else 0,
        "critical_alarms": critical_alarms
    }

@app.get("/bfd/total")
def total_bfd_sessions(sample_size: int = 10):
    """Total de sesiones BFD en la red (muestreo)"""
    devices_data = vmanage.get("/dataservice/device").get("data", [])
    
    # Filtrar dispositivos alcanzables (excluir vManage)
    devices = [d for d in devices_data 
               if d.get("reachability") == "reachable" 
               and d.get("device-type") != "vmanage"]
    
    # Muestreo para evitar timeout
    sample = devices[:sample_size]
    
    total_sessions = 0
    total_up = 0
    total_down = 0
    devices_with_bfd = 0
    
    for device in sample:
        device_id = device.get("system-ip")
        try:
            bfd_data = vmanage.get(
                f"/dataservice/device/bfd/sessions?deviceId={device_id}",
                timeout=5
            )
            sessions = bfd_data.get("data", [])
            
            if sessions:
                devices_with_bfd += 1
                total_sessions += len(sessions)
                total_up += sum(1 for s in sessions if s.get("state") == "up")
                total_down += sum(1 for s in sessions if s.get("state") != "up")
        except:
            continue
    
    # Extrapolación
    if sample_size < len(devices):
        ratio = len(devices) / sample_size
        estimated_total = int(total_sessions * ratio)
        estimated_up = int(total_up * ratio)
        estimated_down = int(total_down * ratio)
    else:
        estimated_total = total_sessions
        estimated_up = total_up
        estimated_down = total_down
    
    return {
        "sample_size": sample_size,
        "total_devices_in_network": len(devices),
        "devices_sampled": len(sample),
        "devices_with_bfd": devices_with_bfd,
        "total_bfd_sessions": total_sessions,
        "sessions_up": total_up,
        "sessions_down": total_down,
        "health_percentage": (total_up/total_sessions*100) if total_sessions > 0 else 0,
        "estimated_total_sessions": estimated_total,
        "estimated_up": estimated_up,
        "estimated_down": estimated_down
    }

@app.get("/applications/top")
def top_applications():
    """Top aplicaciones por tráfico"""
    data = vmanage.get("/dataservice/statistics/approute/aggregation")
    return data

@app.get("/search")
def search_device(field: str, value: str):
    """Buscar dispositivos por criterio"""
    devices = vmanage.get("/dataservice/device").get("data", [])
    
    results = []
    for device in devices:
        device_value = str(device.get(field, "")).lower()
        if value.lower() in device_value:
            results.append(device)
    
    return {
        "search_field": field,
        "search_value": value,
        "results_found": len(results),
        "devices": results
    }

@app.get("/sites/{site_id}/devices")
def devices_by_site(site_id: str):
    """Dispositivos en un sitio"""
    devices = vmanage.get("/dataservice/device").get("data", [])
    site_devices = [d for d in devices if d.get("site-id") == site_id]
    
    return {
        "site_id": site_id,
        "total_devices": len(site_devices),
        "devices": site_devices
    }

@app.get("/security/events")
def security_events():
    """Eventos de seguridad"""
    data = vmanage.get("/dataservice/event/security")
    return data

@app.get("/devices/{device_id}/diagnostic")
def device_diagnostic(device_id: str):
    """Diagnóstico completo de un dispositivo"""
    try:
        health = vmanage.get(f"/dataservice/device/system/status?deviceId={device_id}")
        bfd = vmanage.get(f"/dataservice/device/bfd/sessions?deviceId={device_id}")
        interfaces = vmanage.get(f"/dataservice/device/interface?deviceId={device_id}")
        omp = vmanage.get(f"/dataservice/device/omp/peers?deviceId={device_id}")
        
        bfd_sessions = bfd.get("data", [])
        bfd_up = sum(1 for s in bfd_sessions if s.get("state") == "up")
        
        return {
            "device_id": device_id,
            "health": health,
            "bfd_summary": {
                "total": len(bfd_sessions),
                "up": bfd_up,
                "down": len(bfd_sessions) - bfd_up
            },
            "interfaces_count": len(interfaces.get("data", [])),
            "omp_peers_count": len(omp.get("data", [])),
            "full_data": {
                "bfd": bfd,
                "interfaces": interfaces,
                "omp": omp
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SERVIDOR
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  🌐 API REST para vManage - Compatible con GPT/Gemini")
    print("="*70)
    print("\n📡 Servidor iniciando en: http://localhost:8000")
    print("📚 Documentación automática: http://localhost:8000/docs")
    print("🔧 Redoc: http://localhost:8000/redoc")
    print("\n✅ Endpoints disponibles:")
    print("   GET /devices - Listar dispositivos")
    print("   GET /devices/{id}/health - Salud de dispositivo")
    print("   GET /devices/{id}/bfd - Sesiones BFD")
    print("   GET /alarms/critical - Alarmas críticas")
    print("   GET /bfd/total - Total sesiones BFD en red")
    print("   ... y 10 endpoints más")
    print("\n💡 Usa /docs para ver todos los endpoints interactivos")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
