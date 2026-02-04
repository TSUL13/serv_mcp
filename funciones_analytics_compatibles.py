"""
FUNCIONES DE ANALYTICS COMPATIBLES CON TU VMANAGE
Basadas en los endpoints reales que tienes disponibles
"""

from datetime import datetime, timedelta

# ========== FUNCIONES YA FUNCIONANDO ==========

@mcp.tool()
def ver_aplicaciones_por_dispositivo(device_id: str) -> str:
    """
    Obtiene aplicaciones detectadas por DPI en un dispositivo específico
    (Función existente mejorada con más detalles)
    
    Args:
        device_id: ID del dispositivo (system-ip)
    
    Returns:
        Lista detallada de aplicaciones con estadísticas
    """
    try:
        session = get_vmanage_session()
        endpoint = f"/dataservice/device/dpi/applications?deviceId={device_id}"
        result = session.get(endpoint, timeout=20)
        
        if 'data' in result and result['data']:
            apps = []
            total_bytes = 0
            
            for app in result['data']:
                bytes_total = app.get('octets-received', 0) + app.get('octets-sent', 0)
                total_bytes += bytes_total
                
                apps.append({
                    'aplicacion': app.get('application', 'Unknown'),
                    'familia': app.get('family', 'N/A'),
                    'bytes_rx_gb': round(app.get('octets-received', 0) / (1024**3), 2),
                    'bytes_tx_gb': round(app.get('octets-sent', 0) / (1024**3), 2),
                    'bytes_total_gb': round(bytes_total / (1024**3), 2),
                    'paquetes_rx': app.get('packets-received', 0),
                    'paquetes_tx': app.get('packets-sent', 0),
                    'sesiones_activas': app.get('active-flows', 0)
                })
            
            # Ordenar por bytes totales
            apps.sort(key=lambda x: x['bytes_total_gb'], reverse=True)
            
            return (
                f"📊 APLICACIONES DETECTADAS - Dispositivo {device_id}\n\n"
                f"Total aplicaciones: {len(apps)}\n"
                f"Tráfico total: {total_bytes / (1024**3):.2f} GB\n\n"
                f"Top aplicaciones:\n{apps[:20]}"
            )
        
        return f"No se encontraron aplicaciones para el dispositivo {device_id}"
        
    except Exception as e:
        return f"Error: {str(e)}"


# ========== NUEVAS FUNCIONES PARA AGREGAR ==========

@mcp.tool()
def analizar_trafico_total_red() -> str:
    """
    Analiza el tráfico de aplicaciones en toda la red SD-WAN
    Consolida datos de todos los dispositivos edge
    
    Returns:
        Análisis agregado de tráfico por aplicación en toda la red
    """
    try:
        session = get_vmanage_session()
        
        # 1. Obtener todos los dispositivos edge
        devices_result = session.get("/dataservice/device", timeout=20)
        
        if 'data' not in devices_result:
            return "No se pudieron obtener dispositivos"
        
        edge_devices = [
            d for d in devices_result['data'] 
            if d.get('device-type') in ['vedge', 'vmanage']
        ]
        
        # 2. Consolidar aplicaciones de todos los dispositivos
        apps_consolidadas = {}
        dispositivos_procesados = 0
        
        for device in edge_devices[:50]:  # Limitar a 50 para no saturar
            device_id = device.get('deviceId') or device.get('uuid')
            device_name = device.get('host-name')
            
            try:
                endpoint = f"/dataservice/device/dpi/applications?deviceId={device_id}"
                result = session.get(endpoint, timeout=10)
                
                if 'data' in result and result['data']:
                    dispositivos_procesados += 1
                    
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
                        
            except Exception as e:
                continue  # Saltar dispositivos con error
        
        # 3. Generar reporte
        if not apps_consolidadas:
            return "No se encontraron datos de aplicaciones en la red"
        
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
                'porcentaje_trafico': 0  # Se calculará después
            })
        
        # Calcular porcentajes
        for app in apps_lista:
            app['porcentaje_trafico'] = round(
                (app['bytes_total_tb'] / (total_bytes_red / (1024**4))) * 100, 2
            )
        
        # Ordenar por bytes totales
        apps_lista.sort(key=lambda x: x['bytes_total_tb'], reverse=True)
        
        return (
            f"🌐 ANÁLISIS DE TRÁFICO - RED COMPLETA\n\n"
            f"Dispositivos analizados: {dispositivos_procesados}/{len(edge_devices)}\n"
            f"Aplicaciones detectadas: {len(apps_lista)}\n"
            f"Tráfico total: {total_bytes_red / (1024**4):.2f} TB\n\n"
            f"Top 20 aplicaciones:\n{apps_lista[:20]}"
        )
        
    except Exception as e:
        return f"Error al analizar tráfico de red: {str(e)}"


@mcp.tool()
def comparar_trafico_sitios(site_id_1: str, site_id_2: str) -> str:
    """
    Compara el tráfico de aplicaciones entre dos sitios
    Útil para análisis de diferencias de uso
    
    Args:
        site_id_1: ID del primer sitio
        site_id_2: ID del segundo sitio
    
    Returns:
        Comparación detallada de tráfico entre ambos sitios
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
    Detecta aplicaciones que están consumiendo ancho de banda pero no están en la lista autorizada
    
    Args:
        whitelist: Lista de aplicaciones autorizadas separadas por comas (ej: "office-365,zoom,teams")
    
    Returns:
        Lista de aplicaciones no autorizadas detectadas en la red
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
    Obtiene el estado completo del sistema de un dispositivo
    (CPU, memoria, uptime, versión, etc.)
    
    Args:
        device_id: ID del dispositivo (system-ip)
    
    Returns:
        Estado detallado del sistema
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
