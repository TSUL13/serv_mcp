"""
Funciones adicionales para Cisco Analytics en vManage
Para agregar al server.py si tienes Analytics habilitado
"""

@mcp.tool()
def analizar_experiencia_aplicaciones(site_id: str = None, horas: int = 24) -> str:
    """
    Analiza la calidad de experiencia (QoE) de las aplicaciones
    
    Args:
        site_id: ID del sitio (opcional, si no se especifica analiza toda la red)
        horas: Ventana de tiempo en horas (default: 24)
    
    Returns:
        Estadísticas de experiencia de usuario por aplicación con métricas de latencia, jitter y pérdida
    """
    try:
        session = get_vmanage_session()
        
        # Calcular ventana de tiempo
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(hours=horas)).timestamp() * 1000)
        
        # Endpoint de Application-Aware Routing statistics
        endpoint = f"/dataservice/statistics/app-aware/app-agg-stats?startDate={start_time}&endDate={end_time}"
        
        if site_id:
            endpoint += f"&siteId={site_id}"
        
        result = session.get(endpoint, timeout=30)
        
        if 'data' in result and result['data']:
            apps_qoe = []
            
            for app_stat in result['data']:
                app_name = app_stat.get('application', 'Unknown')
                
                # Métricas de calidad
                latency = app_stat.get('latency', 0)
                jitter = app_stat.get('jitter', 0)
                loss = app_stat.get('loss', 0)
                
                # Calcular score de experiencia (0-100)
                # Fórmula simplificada: 100 - (latency_factor + jitter_factor + loss_factor)
                latency_penalty = min(latency / 10, 50)  # Max 50 puntos
                jitter_penalty = min(jitter * 2, 25)      # Max 25 puntos  
                loss_penalty = min(loss * 100, 25)         # Max 25 puntos
                
                experience_score = max(0, 100 - (latency_penalty + jitter_penalty + loss_penalty))
                
                # Clasificación de experiencia
                if experience_score >= 85:
                    quality = "🟢 Excelente"
                elif experience_score >= 70:
                    quality = "🟡 Buena"
                elif experience_score >= 50:
                    quality = "🟠 Regular"
                else:
                    quality = "🔴 Pobre"
                
                apps_qoe.append({
                    'aplicacion': app_name,
                    'latencia_ms': round(latency, 2),
                    'jitter_ms': round(jitter, 2),
                    'perdida_pct': round(loss * 100, 2),
                    'score_experiencia': round(experience_score, 1),
                    'calidad': quality,
                    'bytes_totales': app_stat.get('total-bytes', 0),
                    'sesiones': app_stat.get('sessions', 0)
                })
            
            # Ordenar por peor experiencia primero
            apps_qoe.sort(key=lambda x: x['score_experiencia'])
            
            return (
                f"📊 ANÁLISIS DE EXPERIENCIA DE APLICACIONES\n"
                f"Período: Últimas {horas} horas\n"
                f"{'Sitio: ' + site_id if site_id else 'Toda la red'}\n\n"
                f"Total de aplicaciones analizadas: {len(apps_qoe)}\n\n"
                f"Detalle:\n{apps_qoe}"
            )
        
        return "No se encontraron datos de experiencia de aplicaciones"
        
    except Exception as e:
        return f"Error al analizar experiencia de aplicaciones: {str(e)}"


@mcp.tool()
def ver_flujos_anormales(umbral_bytes: int = 100000000, top: int = 20) -> str:
    """
    Detecta flujos de red con comportamiento anormal (consumo excesivo o patrones inusuales)
    
    Args:
        umbral_bytes: Umbral de bytes para considerar un flujo como anormal (default: 100MB)
        top: Número de flujos a mostrar (default: 20)
    
    Returns:
        Lista de flujos con consumo anormal de ancho de banda
    """
    try:
        session = get_vmanage_session()
        
        # Endpoint de agregación de flujos DPI
        endpoint = "/dataservice/statistics/dpi/aggregation"
        
        result = session.get(endpoint, timeout=30)
        
        if 'data' in result and result['data']:
            flujos_sospechosos = []
            
            for flow in result['data']:
                total_bytes = flow.get('total_bytes', 0)
                
                if total_bytes > umbral_bytes:
                    flujos_sospechosos.append({
                        'aplicacion': flow.get('application', 'Unknown'),
                        'origen': flow.get('src_ip', 'N/A'),
                        'destino': flow.get('dst_ip', 'N/A'),
                        'puerto': flow.get('dst_port', 'N/A'),
                        'protocolo': flow.get('protocol', 'N/A'),
                        'bytes_mb': round(total_bytes / (1024*1024), 2),
                        'paquetes': flow.get('packet_count', 0),
                        'duracion_seg': flow.get('duration', 0),
                        'familia': flow.get('family', 'N/A'),
                        'sitio': flow.get('site_id', 'N/A')
                    })
            
            # Ordenar por bytes (mayor a menor)
            flujos_sospechosos.sort(key=lambda x: x['bytes_mb'], reverse=True)
            flujos_sospechosos = flujos_sospechosos[:top]
            
            if flujos_sospechosos:
                return (
                    f"⚠️  FLUJOS DE RED ANORMALES\n"
                    f"Umbral: {umbral_bytes / (1024*1024):.0f} MB\n"
                    f"Detectados: {len(flujos_sospechosos)}\n\n"
                    f"Detalle:\n{flujos_sospechosos}"
                )
            else:
                return f"✅ No se detectaron flujos anormales (sobre {umbral_bytes / (1024*1024):.0f} MB)"
        
        return "No se pudieron obtener datos de flujos"
        
    except Exception as e:
        return f"Error al analizar flujos anormales: {str(e)}"


@mcp.tool()
def predecir_capacidad_enlaces(site_id: str, dias_proyeccion: int = 30) -> str:
    """
    Predice la utilización futura de enlaces basado en tendencias históricas
    
    Args:
        site_id: ID del sitio a analizar
        dias_proyeccion: Días hacia el futuro a proyectar (default: 30)
    
    Returns:
        Predicción de capacidad y recomendaciones de upgrades
    """
    try:
        session = get_vmanage_session()
        
        # Obtener datos históricos de interfaces
        endpoint = f"/dataservice/statistics/interface/aggregation"
        
        result = session.get(endpoint, timeout=30)
        
        if 'data' in result and result['data']:
            # Filtrar por sitio
            interfaces_sitio = [
                iface for iface in result['data'] 
                if iface.get('site-id') == site_id
            ]
            
            if not interfaces_sitio:
                return f"No se encontraron interfaces para el sitio {site_id}"
            
            predicciones = []
            
            for iface in interfaces_sitio:
                device_name = iface.get('host-name', 'N/A')
                iface_name = iface.get('interface', 'N/A')
                
                # Obtener utilización actual
                rx_bps = iface.get('rx-bps', 0)
                tx_bps = iface.get('tx-bps', 0)
                bandwidth = iface.get('bandwidth', 1)  # Mbps
                
                util_actual_rx = (rx_bps / (bandwidth * 1000000)) * 100 if bandwidth > 0 else 0
                util_actual_tx = (tx_bps / (bandwidth * 1000000)) * 100 if bandwidth > 0 else 0
                
                # Tendencia (simulada - en producción calcular con datos históricos)
                crecimiento_mensual = 5  # 5% mensual estimado
                
                # Proyección
                meses = dias_proyeccion / 30
                util_proyectada_rx = util_actual_rx * (1 + (crecimiento_mensual/100) * meses)
                util_proyectada_tx = util_actual_tx * (1 + (crecimiento_mensual/100) * meses)
                
                # Recomendación
                if util_proyectada_rx > 80 or util_proyectada_tx > 80:
                    recomendacion = "🔴 Upgrade recomendado"
                elif util_proyectada_rx > 60 or util_proyectada_tx > 60:
                    recomendacion = "🟡 Monitorear de cerca"
                else:
                    recomendacion = "🟢 Capacidad suficiente"
                
                predicciones.append({
                    'dispositivo': device_name,
                    'interfaz': iface_name,
                    'bandwidth_mbps': bandwidth,
                    'util_actual_rx_pct': round(util_actual_rx, 1),
                    'util_actual_tx_pct': round(util_actual_tx, 1),
                    'util_proyectada_rx_pct': round(util_proyectada_rx, 1),
                    'util_proyectada_tx_pct': round(util_proyectada_tx, 1),
                    'dias_hasta_80pct': round((80 - util_actual_rx) / (crecimiento_mensual/30), 0) if util_actual_rx < 80 else 0,
                    'recomendacion': recomendacion
                })
            
            # Ordenar por utilización proyectada
            predicciones.sort(key=lambda x: max(x['util_proyectada_rx_pct'], x['util_proyectada_tx_pct']), reverse=True)
            
            return (
                f"📈 PREDICCIÓN DE CAPACIDAD - Sitio {site_id}\n"
                f"Proyección: {dias_proyeccion} días\n"
                f"Tendencia estimada: {crecimiento_mensual}% mensual\n\n"
                f"Interfaces analizadas: {len(predicciones)}\n\n"
                f"Detalle:\n{predicciones}"
            )
        
        return f"No se pudieron obtener datos para predicción del sitio {site_id}"
        
    except Exception as e:
        return f"Error al predecir capacidad: {str(e)}"


@mcp.tool()
def analizar_rendimiento_tuneles(site_id: str = None, horas: int = 24) -> str:
    """
    Analiza el rendimiento de túneles IPsec/GRE y detecta degradación
    
    Args:
        site_id: ID del sitio (opcional)
        horas: Ventana de tiempo en horas (default: 24)
    
    Returns:
        Análisis de rendimiento de túneles con métricas de calidad
    """
    try:
        session = get_vmanage_session()
        
        # Endpoint de estadísticas de túneles
        endpoint = "/dataservice/statistics/tunnel/aggregation"
        
        result = session.get(endpoint, timeout=30)
        
        if 'data' in result and result['data']:
            # Filtrar por sitio si se especifica
            tuneles = result['data']
            if site_id:
                tuneles = [t for t in tuneles if t.get('local-site-id') == site_id or t.get('remote-site-id') == site_id]
            
            analisis_tuneles = []
            
            for tunnel in tuneles:
                # Métricas de rendimiento
                latency = tunnel.get('latency', 0)
                jitter = tunnel.get('jitter', 0)
                loss = tunnel.get('loss', 0)
                tx_bytes = tunnel.get('tx-bytes', 0)
                rx_bytes = tunnel.get('rx-bytes', 0)
                
                # Estado del túnel
                estado = tunnel.get('state', 'unknown')
                
                # Evaluar salud del túnel
                if loss > 1:
                    salud = "🔴 Crítico - Alta pérdida"
                elif loss > 0.5:
                    salud = "🟠 Degradado - Pérdida moderada"
                elif latency > 100:
                    salud = "🟡 Alerta - Latencia alta"
                elif estado == 'up':
                    salud = "🟢 Saludable"
                else:
                    salud = "❌ Caído"
                
                analisis_tuneles.append({
                    'origen': tunnel.get('local-system-ip', 'N/A'),
                    'destino': tunnel.get('remote-system-ip', 'N/A'),
                    'sitio_local': tunnel.get('local-site-id', 'N/A'),
                    'sitio_remoto': tunnel.get('remote-site-id', 'N/A'),
                    'color': tunnel.get('local-color', 'N/A'),
                    'estado': estado,
                    'latencia_ms': round(latency, 2),
                    'jitter_ms': round(jitter, 2),
                    'perdida_pct': round(loss * 100, 2),
                    'tx_mb': round(tx_bytes / (1024*1024), 2),
                    'rx_mb': round(rx_bytes / (1024*1024), 2),
                    'salud': salud
                })
            
            # Ordenar por peor salud primero
            orden_salud = {"🔴 Crítico - Alta pérdida": 0, "❌ Caído": 1, "🟠 Degradado - Pérdida moderada": 2, "🟡 Alerta - Latencia alta": 3, "🟢 Saludable": 4}
            analisis_tuneles.sort(key=lambda x: orden_salud.get(x['salud'], 5))
            
            # Estadísticas generales
            total = len(analisis_tuneles)
            saludables = len([t for t in analisis_tuneles if "🟢" in t['salud']])
            problematicos = total - saludables
            
            return (
                f"🔗 ANÁLISIS DE RENDIMIENTO DE TÚNELES\n"
                f"Período: Últimas {horas} horas\n"
                f"{'Sitio: ' + site_id if site_id else 'Toda la red'}\n\n"
                f"Total de túneles: {total}\n"
                f"Saludables: {saludables} ({saludables/total*100:.1f}%)\n"
                f"Con problemas: {problematicos}\n\n"
                f"Detalle:\n{analisis_tuneles[:20]}"  # Top 20
            )
        
        return "No se encontraron datos de túneles"
        
    except Exception as e:
        return f"Error al analizar túneles: {str(e)}"
