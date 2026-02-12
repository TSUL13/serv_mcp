# 🚀 Servidor MCP para Cisco SD-WAN

Servidor Model Context Protocol (MCP) para gestionar infraestructura de Cisco SD-WAN a través de vManage y Analytics Cloud.

## ⚡ INICIO RÁPIDO

```bash
cd /home/tsul/Documentos/serv_mcp
./start_mcp.sh
```

Luego abre **Claude Desktop** y pregunta:
```
Dame un top 10 de las aplicaciones más usadas en la red
```

**¿Primera vez?** Ver [GUIA_ARRANQUE_COMPLETA.md](GUIA_ARRANQUE_COMPLETA.md)

---

## 🚀 Características

- **Autenticación robusta** con vManage (sesión y tokens XSRF)
- **20+ herramientas MCP** para Network Automation:
  
  **Gestión de Dispositivos:**
  - `listar_dispositivos`: Inventario completo de dispositivos
  - `ver_salud_equipo`: Estado y salud de un dispositivo específico
  - `ver_estado_sistema_dispositivo`: CPU, memoria, disco, uptime
  - `ver_detalle_dispositivo`: Información detallada de hardware y software
  
  **Conectividad y Túneles:**
  - `ver_sesiones_bfd`: Estado de túneles BFD
  - `ver_total_sesiones_bfd`: Total de sesiones BFD en la red
  - `ver_tuneles_ipsec`: Túneles IPsec activos
  
  **Monitoreo y Alertas:**
  - `listar_alarmas_criticas`: Alarmas críticas de las últimas 24 horas
  - `diagnosticar_dispositivo`: Diagnóstico completo de salud
  
  **Analytics y Tráfico (Cisco Analytics):**
  - `ver_aplicaciones_top`: Top aplicaciones por dispositivo (DPI)
  - `analizar_trafico_total_red`: Tráfico consolidado de toda la red
  - `comparar_trafico_sitios`: Comparación entre dos sitios
  - `detectar_aplicaciones_no_autorizadas`: Detección de shadow IT
  
  **🆕 Acceso SSH Directo:**
  - `buscar_flujos_dpi_ssh`: Flujos DPI detallados con IPs origen→destino vía SSH
    - Búsqueda automática de dispositivo en vManage
    - Conexión SSH directa al dispositivo
    - Filtrado por aplicación o IP
    - Ver [GUIA_SSH_DPI.md](GUIA_SSH_DPI.md) para más detalles
  
  **Políticas y Configuración:**
  - `ver_politicas_activas`: Políticas aplicadas en la red
  - `ver_plantillas`: Templates de configuración
  - `ver_cambios_configuracion`: Auditoría de cambios
  
  **Interfaces y Rendimiento:**
  - `ver_interfaces_dispositivo`: Estado de interfaces
  - `ver_estadisticas_interfaz`: Métricas de rendimiento

## 📋 Requisitos

- Python 3.8+
- Acceso a vManage con credenciales administrativas
- Conectividad de red al vManage

## 🔧 Instalación

1. **Clonar o copiar el proyecto**

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

3. **Configurar credenciales**:
```bash
cp .env.example .env
# Editar .env con tus credenciales reales
```

4. **Configurar el archivo .env**:
```env
# vManage - API PURA (autenticación programática)
VMANAGE_IP=tu-vmanage-ip
VMANAGE_USERNAME=tu-usuario
VMANAGE_PASSWORD=tu-contraseña
# NO necesitas VMANAGE_JSESSIONID ni VMANAGE_XSRF_TOKEN
# Se generan automáticamente con API pura

# Analytics Cloud - Web API (requiere cookies del navegador)
# Ejecuta: python3 update_cookies.py para obtenerlas
ANALYTICS_SESSION_COOKIE=...
ANALYTICS_CSRF_TOKEN=...
ANALYTICS_OVERLAY_ID=...

# SSH Directo (opcional)
SDWAN_SSH_USER=admin
SDWAN_SSH_PASSWORD=tu-contraseña-ssh
```

## 🎯 Uso

### Ejecutar el servidor MCP:
```bash
python server.py
```

### Integración con Claude Desktop

Agregar al archivo de configuración de Claude (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cisco-sdwan": {
      "command": "python",
      "args": ["/ruta/completa/al/server.py"]
    }
  }
}
```

## 🔍 Herramientas Disponibles

### 1. listar_dispositivos
Lista todos los dispositivos del inventario con información detallada.

### 2. ver_salud_equipo
Consulta el estado de salud de un dispositivo específico.
- **Parámetro**: `device_id` (System IP del dispositivo)

### 3. ver_sesiones_bfd
Muestra todas las sesiones BFD (túneles) de un dispositivo.
- **Parámetro**: `device_id` (System IP del dispositivo)

### 4. listar_alarmas_criticas
Lista alarmas de nivel crítico de las últimas 24 horas.

## 🛡️ Seguridad

- Las credenciales se gestionan mediante variables de entorno
- El archivo `.env` **NO** debe subirse a control de versiones
- Las advertencias SSL están desactivadas (entornos de laboratorio)
- Manejo robusto de excepciones y timeouts

## � Validación y Mantenimiento de API

Este proyecto incluye **herramientas automatizadas** para detectar y adaptarse a cambios en la API de Cisco Analytics Cloud:

### Scripts Disponibles

- **`validar_api_analytics.py`** - Valida endpoints actuales contra Analytics Cloud
- **`capturar_api_analytics.py`** - Analiza tráfico HAR del navegador para detectar cambios
- **`ejemplo_workflow_api.sh`** - Workflow completo automatizado
- **`GUIA_RAPIDA_API.sh`** - Guía rápida de uso

### Uso Rápido

```bash
# Validación semanal de rutina
python3 validar_api_analytics.py

# Si detecta problemas, captura tráfico del navegador:
# 1. F12 → Network → Save as HAR
# 2. Analiza la captura
python3 capturar_api_analytics.py analytics_traffic.har

# Ver guía completa
./GUIA_RAPIDA_API.sh
```

Ver documentación completa en [README_API_VALIDATION.md](README_API_VALIDATION.md)

## �📝 Notas

- Desarrollado para entornos Cisco SD-WAN con vManage
- Compatible con APIs de vManage 19.x y 20.x
- Los certificados SSL se ignoran (típico en labs)

## 🐛 Troubleshooting

- **Error de autenticación**: Verificar credenciales en `.env`
- **Timeout**: Revisar conectividad de red al vManage
- **SSL Errors**: Las advertencias SSL están desactivadas por defecto

## 👨‍💻 Desarrollado por

Servidor MCP especializado en Network Automation para Cisco SD-WAN.
