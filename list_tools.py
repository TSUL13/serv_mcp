#!/usr/bin/env python3
"""
Script para listar todas las herramientas MCP disponibles en el servidor
ACTUALIZADO: Solo muestra herramientas reales (sin Selenium)
"""

# Lista EXACTA de herramientas disponibles en server.py
# Actualizada el 2026-02-05 - SIN FUNCIONES DE SELENIUM

VMANAGE_TOOLS = [
    ("listar_dispositivos", "Lista todos los dispositivos en el inventario de vManage"),
    ("buscar_dispositivo", "Busca dispositivos por nombre, IP, modelo o site-id"),
    ("ver_dispositivos_por_sitio", "Lista dispositivos de un sitio específico"),
    ("ver_salud_equipo", "Estado de salud de un dispositivo específico"),
    ("ver_resumen_red", "Dashboard general del estado de la red SD-WAN"),
    ("diagnostico_completo_dispositivo", "Diagnóstico completo combinando múltiples métricas"),
    ("ver_sesiones_bfd", "Estado de sesiones BFD (túneles) de un dispositivo"),
    ("ver_total_sesiones_bfd", "Total de sesiones BFD en toda la red"),
    ("ver_tuneles_omp", "Lista túneles OMP de un dispositivo"),
    ("ver_control_connections", "Conexiones al control plane (vSmart)"),
    ("ver_estadisticas_interfaces", "Estadísticas de tráfico y errores de interfaces"),
    ("ver_uso_cpu_memoria", "Uso de CPU y memoria en tiempo real"),
    ("ver_estado_sistema_dispositivo", "Estado completo del sistema (CPU, memoria, disco, uptime)"),
    ("listar_alarmas_criticas", "Alarmas críticas de las últimas 24 horas"),
    ("ver_eventos_seguridad", "Eventos de seguridad recientes (IPS, firewall)"),
]

ANALYTICS_TOOLS = [
    ("ver_aplicaciones_top", "Top aplicaciones por consumo de ancho de banda"),
    ("analizar_trafico_total_red", "Análisis de tráfico de aplicaciones en toda la red (Analytics Cloud)"),
    ("analizar_detalle_aplicaciones", "Desglose detallado por aplicación → sitios → dispositivos"),
    ("comparar_trafico_sitios", "Compara tráfico entre dos sitios"),
    ("detectar_aplicaciones_no_autorizadas", "Detecta aplicaciones no autorizadas (shadow IT)"),
    ("analizar_aplicacion_vmanage", "Analiza aplicación específica usando vManage DPI API"),
    ("obtener_ips_destino_aplicacion", "IPs destino más comunes para una aplicación"),
    ("obtener_flujos_dpi_cedge", "Flujos DPI activos de un router cEdge vía SSH"),
]

CATALYST_TOOLS = [
    ("catalyst_listar_dispositivos_red", "Lista todos los dispositivos de red"),
    ("catalyst_salud_dispositivo", "Estado de salud de un dispositivo"),
    ("catalyst_topologia_red", "Obtiene topología de red (physical/layer2/layer3)"),
    ("catalyst_inventario_sitios", "Lista sitios con jerarquía"),
    ("catalyst_clientes_conectados", "Lista clientes conectados"),
    ("catalyst_issues_red", "Lista problemas detectados"),
    ("catalyst_resumen_red", "Dashboard general de Catalyst Center"),
]

print("\n" + "="*70)
print("📦 HERRAMIENTAS MCP DISPONIBLES EN EL SERVIDOR")
print("="*70 + "\n")

# Separar por categoría
vmanage_tools = VMANAGE_TOOLS
analytics_api_tools = ANALYTICS_TOOLS
catalyst_tools = CATALYST_TOOLS

# Mostrar herramientas por categoría
print(f"🔧 HERRAMIENTAS DE SD-WAN vMANAGE ({len(vmanage_tools)}):")
for i, (name, desc) in enumerate(sorted(vmanage_tools), 1):
    print(f"  {i:2d}. {name:40s} - {desc[:60]}")

print(f"\n📊 HERRAMIENTAS DE ANALYTICS CLOUD API ({len(analytics_api_tools)}):")
for i, (name, desc) in enumerate(sorted(analytics_api_tools), 1):
    print(f"  {i:2d}. {name:40s} - {desc[:60]}")

print(f"\n🏢 HERRAMIENTAS DE CATALYST CENTER ({len(catalyst_tools)}):")
for i, (name, desc) in enumerate(sorted(catalyst_tools), 1):
    print(f"  {i:2d}. {name:40s} - {desc[:60]}")

total_tools = len(vmanage_tools) + len(analytics_api_tools) + len(catalyst_tools)

print("\n" + "="*70)
print(f"✅ TOTAL: {total_tools} herramientas MCP disponibles")
print(f"❌ Funciones de Selenium: ELIMINADAS (ya no están en el servidor)")
print("="*70 + "\n")

print("💡 Para que Claude Desktop actualice la lista:")
print("   1. Cierra Claude Desktop completamente")
print("   2. Abre Claude Desktop nuevamente")
print("   3. Verifica el ícono 🔌 (debe aparecer abajo a la derecha)")
print("   4. Haz clic en 🔌 para ver las herramientas conectadas")
print("\n")

