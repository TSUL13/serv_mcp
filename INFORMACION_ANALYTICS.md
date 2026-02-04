# 📊 Cisco Analytics - Información Disponible

Este documento detalla qué información puedes obtener de Cisco Analytics para agregar a tu servidor MCP.

## 🎯 Resumen Ejecutivo

Tu vManage tiene **DPI (Deep Packet Inspection) básico** habilitado, pero **Analytics avanzado NO está configurado**.

### ✅ **Lo que SÍ puedes obtener:**

| Categoría | Información | Endpoint | Estado |
|-----------|------------|----------|--------|
| **DPI Básico** | Aplicaciones detectadas por dispositivo | `/dataservice/device/dpi/applications` | ✅ Disponible |
| **System Status** | CPU, RAM, disco, uptime | `/dataservice/device/system/status` | ✅ Disponible |
| **Dispositivos** | Inventario completo | `/dataservice/device` | ✅ Disponible |
| **Alarmas** | Alertas críticas | `/dataservice/alarms` | ✅ Disponible |
| **Interfaces** | Estado de interfaces | `/dataservice/device/interface` | ✅ Disponible |
| **Túneles** | Estado de BFD/IPsec | `/dataservice/device/bfd/sessions` | ✅ Disponible |

### ❌ **Lo que NO está disponible (requiere Analytics avanzado):**

| Característica | Endpoint | Información que Obtendría | Requerimiento |
|----------------|----------|---------------------------|---------------|
| **Application QoE** | `/dataservice/statistics/app-aware/app-agg-stats` | Latencia, jitter, pérdida por aplicación | Habilitar App-Aware Routing |
| **Flow Analytics** | `/dataservice/statistics/dpi/aggregation` | Análisis de flujos con agregación | Habilitar Analytics |
| **Predictive Analytics** | `/dataservice/statistics/interface/prediction` | Predicciones de capacidad | Habilitar Analytics + vManage 20.9+ |
| **Path Analytics** | `/dataservice/statistics/tunnel/aggregation` | Análisis de rutas alternativas | Habilitar Analytics |

---

## 🆕 Funciones Agregadas al MCP

### 1️⃣ **analizar_trafico_total_red()**

**¿Qué hace?**
- Consolida el tráfico DPI de TODOS los dispositivos edge
- Identifica las aplicaciones más consumidas a nivel red
- Calcula porcentajes de uso por aplicación

**Información que obtiene:**
```python
{
    'aplicacion': 'office-365',
    'familia': 'business-and-productivity-tools',
    'bytes_total_tb': 2.45,
    'num_dispositivos': 45,
    'sesiones_activas': 1234,
    'porcentaje_trafico': 15.3
}
```

**Cuándo usar:**
- Auditoría mensual de uso de aplicaciones
- Identificar aplicaciones que consumen más ancho de banda
- Reportes ejecutivos de utilización de red

**Ejemplo de uso con Claude:**
```
"Analiza el tráfico total de la red y dime qué aplicaciones están consumiendo más ancho de banda"
```

---

### 2️⃣ **comparar_trafico_sitios(site_id_1, site_id_2)**

**¿Qué hace?**
- Compara el uso de aplicaciones entre dos sitios
- Identifica aplicaciones únicas por sitio
- Detecta diferencias en patrones de uso

**Información que obtiene:**
```python
{
    'aplicacion': 'zoom',
    'sitio_100_gb': 50.2,
    'sitio_200_gb': 12.3,
    'diferencia_gb': 37.9,
    'sitio_mayor_uso': '100'
}
```

**Cuándo usar:**
- Comparar sucursales similares (oficinas del mismo tipo)
- Detectar anomalías en uso entre sitios
- Validar políticas de QoS aplicadas

**Ejemplo de uso con Claude:**
```
"Compara el tráfico del sitio 100 con el sitio 200 para ver si hay diferencias significativas"
```

---

### 3️⃣ **detectar_aplicaciones_no_autorizadas(whitelist)**

**¿Qué hace?**
- Detecta aplicaciones que NO están en tu lista autorizada
- Clasifica por nivel de riesgo (Alto/Medio/Bajo)
- Identifica dónde se están usando (sitios y dispositivos)

**Información que obtiene:**
```python
{
    'aplicacion': 'bittorrent',
    'familia': 'peer-to-peer',
    'bytes_gb': 150.5,
    'num_dispositivos': 5,
    'num_sitios': 3,
    'nivel_riesgo': '🔴 Alto'
}
```

**Cuándo usar:**
- Compliance y auditorías de seguridad
- Detección de Shadow IT
- Identificar aplicaciones de riesgo (P2P, streaming no autorizado)

**Ejemplo de uso con Claude:**
```
"Detecta aplicaciones no autorizadas, mi whitelist es: office-365,zoom,teams,google,salesforce"
```

---

### 4️⃣ **ver_estado_sistema_dispositivo(device_id)**

**¿Qué hace?**
- Obtiene métricas de recursos de un dispositivo
- Muestra uptime y estado de conectividad
- Información de versión de software

**Información que obtiene:**
```
💻 ESTADO DEL SISTEMA - 10.95.0.3

Hostname: SDWAN-CJF-300-RT01
Modelo: vedge-CSR-1000v
Versión: 20.12.1
Estado: normal
Site ID: 300

📊 Recursos:
  CPU: 12%
  Memoria usada: 45%
  Disco usado: 32%

⏱️  Uptime: 45 días, 12 horas, 30 minutos

📡 Conectividad:
  Última actualización: 2025-02-04T10:30:00
  Modo reachability: reachable
```

**Cuándo usar:**
- Troubleshooting de rendimiento
- Verificar antes de aplicar cambios
- Identificar dispositivos con alta carga

**Ejemplo de uso con Claude:**
```
"Muestra el estado del sistema del dispositivo 10.95.0.3"
```

---

## 🚀 Cómo Usar las Nuevas Funciones

### Opción 1: Reiniciar Claude Desktop (Recomendado)

```bash
# Las nuevas funciones ya están en server.py
# Solo reinicia Claude Desktop para que las detecte:
pkill -9 -f claude-desktop
```

### Opción 2: Probar Manualmente

```bash
# Ejecutar server.py en modo test
python server.py
```

---

## 📈 Casos de Uso Reales

### **Caso 1: Auditoría Mensual de Tráfico**

**Pregunta a Claude:**
```
"Necesito un reporte mensual de uso de aplicaciones:
1. Analiza el tráfico total de la red
2. Detecta aplicaciones no autorizadas (whitelist: office-365,zoom,teams)
3. Compara el tráfico del sitio 100 con el sitio 200"
```

**Resultado:**
- Lista de top 20 aplicaciones con porcentajes
- Aplicaciones de riesgo detectadas
- Diferencias entre sucursales

---

### **Caso 2: Detección de Shadow IT**

**Pregunta a Claude:**
```
"Detecta aplicaciones no autorizadas que estén consumiendo más de 10GB.
Mi whitelist es: office-365,zoom,google,salesforce,dropbox"
```

**Resultado:**
- Aplicaciones P2P, VPN personales, streaming no corporativo
- Ubicación exacta (sitios y dispositivos)
- Nivel de riesgo por volumen de tráfico

---

### **Caso 3: Troubleshooting de Rendimiento**

**Pregunta a Claude:**
```
"El sitio 300 está lento. Muéstrame:
1. Estado del sistema de todos los dispositivos del sitio 300
2. Qué aplicaciones están consumiendo más ancho de banda allí"
```

**Resultado:**
- CPU/RAM/Disco de cada dispositivo
- Aplicaciones con mayor consumo en ese sitio
- Recomendaciones de optimización

---

## 🔧 Cómo Habilitar Analytics Avanzado

Si tu administrador de vManage quiere habilitar **Analytics avanzado** para obtener QoE y predicciones:

### **Pasos en vManage:**

1. **Login a vManage** → Administration → Settings

2. **Habilitar Application Aware Routing:**
   - Configuration → Policies → Application Aware Routing
   - Enable App-Route SLA Classes
   - Configure latency/jitter/loss thresholds

3. **Habilitar DPI Analytics:**
   - Administration → Settings
   - Enable "Flow Analytics"
   - Enable "Application Analytics"

4. **Configurar Data Collection:**
   - Configuration → Templates
   - Agregar DPI data collection en device templates
   - Aplicar templates a dispositivos

5. **Esperar 24-48 horas** para que se acumulen datos históricos

### **Requisitos:**

- vManage versión **20.9 o superior** (para predictive analytics)
- Licencias **Cisco DNA Advantage/Premier**
- Dispositivos con **DPI habilitado** en templates

### **Una vez habilitado, podrás agregar estas funciones:**

```python
# Estas funciones están en funciones_analytics.py (esperando Analytics avanzado)

analizar_experiencia_aplicaciones()  # Latencia, jitter, MOS score por app
ver_flujos_anormales()               # Detección de anomalías con ML
predecir_capacidad_enlaces()         # Proyecciones de crecimiento
analizar_rendimiento_tuneles()       # QoS y SLA compliance por túnel
```

---

## 📊 Diferencia: Analytics Básico vs Avanzado

| Característica | DPI Básico (Lo que tienes) | Analytics Avanzado (Requiere habilitación) |
|----------------|---------------------------|---------------------------------------------|
| **Aplicaciones detectadas** | ✅ Nombres, familias, bytes | ✅ + Latencia, jitter, pérdida |
| **Tráfico por dispositivo** | ✅ Bytes RX/TX | ✅ + QoE score, SLA compliance |
| **Análisis de red completa** | ✅ Consolidación manual | ✅ Agregación automática |
| **Predicciones** | ❌ No disponible | ✅ Proyecciones de capacidad |
| **Anomalías** | ⚠️ Manual (umbral fijo) | ✅ Machine Learning |
| **Histórico** | ⚠️ Solo snapshot actual | ✅ Tendencias de 7-90 días |

---

## 🎓 Resumen para Auditoría

**Pregunta:** *"¿Qué información de Analytics puedes obtener?"*

**Respuesta corta:**
- ✅ **DPI básico**: Aplicaciones, bytes, sesiones por dispositivo
- ✅ **System status**: CPU, RAM, uptime
- ✅ **Consolidación de red**: Tráfico total, comparación de sitios
- ✅ **Compliance**: Detección de apps no autorizadas
- ❌ **Analytics avanzado**: Requiere habilitación (QoE, predicciones, ML)

**Funciones disponibles ahora:** 19 herramientas MCP
**Funciones adicionales si se habilita Analytics:** +4 herramientas (QoE, predicción)

---

## 📞 Soporte

Si necesitas habilitar Analytics avanzado:
1. Contacta a tu administrador de vManage
2. Verifica tu licencia Cisco DNA
3. Consulta [Cisco SD-WAN Analytics Guide](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/analytics/ios-xe-17/analytics-book-xe/m-application-aware-routing.html)

## 🔗 Enlaces

- **GitHub Repository:** https://github.com/TSUL13/serv_mcp
- **Documentación vManage API:** `/dataservice/docs` en tu vManage
- **Test de endpoints:** Ejecuta `python test_analytics_detallado.py`
