# 📊 Función: analizar_detalle_aplicaciones

## Descripción

Proporciona un desglose detallado de aplicaciones específicas mostrando:
- Uso total y métricas de QoE por aplicación
- Top sitios que más consumen
- Dispositivos principales por sitio con IPs
- Estado de disponibilidad de cada dispositivo

## Sintaxis

```
analizar_detalle_aplicaciones(aplicaciones, top_sitios=10)
```

### Parámetros

- **aplicaciones** (string, requerido): Nombres de aplicaciones separados por comas
  - Ejemplo: `"ssl,http,ms-office-365"`
  - Ejemplo: `"W3-Relaciones-familiare,google-services"`

- **top_sitios** (int, opcional): Cantidad de sitios principales a mostrar por aplicación
  - Default: `10`
  - Rango: `1-223` (total de sitios disponibles)

## Ejemplos de uso en Claude Desktop

### Ejemplo 1: Análisis de aplicaciones sospechosas
```
Dame una tabla detallada de las aplicaciones W3-Relaciones-familiare, 
torrent y shareaza mostrando por cada una los sitios y dispositivos que las usan
```

### Ejemplo 2: Top aplicaciones con desglose
```
Analiza las aplicaciones ssl, http y ms-office-365 mostrando 
los top 5 sitios por cada una con sus dispositivos
```

### Ejemplo 3: Aplicación específica en profundidad
```
Muéstrame el detalle completo de la aplicación W3-Relaciones-familiare 
indicando todos los sitios y sus dispositivos
```

## Estructura de respuesta

```
📊 ANÁLISIS DETALLADO DE APLICACIONES

Ventana: 2026-02-04 05:00:00 a 2026-02-04 17:05:00
Total de sitios: 223
Total de dispositivos: 325
Aplicaciones analizadas: 2
======================================================================

======================================================================
📱 APLICACIÓN: SSL 🟢
======================================================================
Familia: Encrypted
Uso total: 1944.54 GB
Sitios usando: 222
QoE global: 10.0/10 | Latencia: 14.6ms | Jitter: 0.16ms | Pérdida: 0.05%

📍 TOP 5 SITIOS CON MAYOR TRÁFICO:
----------------------------------------------------------------------

1. SITE_100 (tizapan) 🔴
   Uso total sitio: 3158.61 GB
   QoE sitio: 0.0/10
   Dispositivos: 0
   
   🖥️  Dispositivos principales:
      1. SDWAN-CJF-323-RT01 (10.97.250.193) ⚠️
         Uso: 2983.98 GB
      2. SDWAN-CJF-323-RT02 (10.97.250.194) ⚠️
         Uso: 174.64 GB

[... más sitios ...]

======================================================================
💡 NOTA: Los datos mostrados son agregados por sitio.
Para IPs origen/destino específicas, accede a:
vManage → Monitor → Applications → Application-Aware Routing
```

## Indicadores visuales

### Calidad QoE (Quality of Experience)
- 🟢 **QoE ≥ 7.0**: Excelente - Sin problemas
- 🟡 **QoE 5.0-6.9**: Aceptable - Posibles degradaciones
- 🔴 **QoE < 5.0**: Crítico - Requiere atención

### Estado de dispositivos
- ✅ **up**: Dispositivo operativo
- ⚠️ **down/unknown**: Dispositivo con problemas

## Datos mostrados

### Por aplicación:
- Familia de aplicación (ej: Encrypted, Web, File-Server)
- Uso total en GB/TB
- Cantidad de sitios que usan la aplicación
- Métricas globales:
  - QoE Score (0-10)
  - Latencia promedio (ms)
  - Jitter (ms)
  - Pérdida de paquetes (%)

### Por sitio:
- Nombre del sitio y ciudad
- Uso total del sitio (no solo de la aplicación específica)
- QoE del sitio
- Cantidad de dispositivos en el sitio

### Por dispositivo:
- Hostname
- IP del sistema (local_system_ip)
- Uso del dispositivo
- Estado de disponibilidad

## Limitaciones importantes

### ⚠️ Granularidad de datos

La función proporciona agregados por **sitio y dispositivo**, NO flujos individuales.

**Lo que SÍ proporciona:**
- ✅ Aplicación → Sitios que la usan
- ✅ Sitio → Dispositivos (routers SD-WAN)
- ✅ Dispositivo → IP del router y uso total

**Lo que NO proporciona:**
- ❌ IP origen (usuario final) → IP destino
- ❌ Flujos individuales por aplicación
- ❌ Usuarios específicos usando la aplicación
- ❌ Destinos específicos (IPs externas)

### 📍 Para obtener flujos IP origen/destino

Si necesitas ver:
- Qué usuarios (IPs LAN) están usando una aplicación
- A qué destinos se conectan
- Flujos activos en tiempo real

Debes acceder a **vManage GUI**:

1. Navega a: **Monitor** → **Applications** → **Application-Aware Routing**
2. Selecciona la aplicación específica
3. Filtra por sitio si es necesario
4. Verás flujos con:
   - IP origen (usuario/host)
   - IP destino (servidor remoto)
   - Puertos
   - Ancho de banda por flujo

### 🔧 Alternativa programática

Para flujos detallados via API (requiere desarrollo custom):

```python
# Endpoint de vManage (no Analytics Cloud)
POST /dataservice/statistics/dpi/aggregation

Payload:
{
  "aggregation": {
    "metrics": [
      {"property": "src_ip", "type": "groupBy"},
      {"property": "dst_ip", "type": "groupBy"},
      {"property": "traffic", "type": "sum"}
    ],
    "filter": {
      "application": {"value": ["W3-Relaciones-familiare"]}
    }
  }
}
```

## Casos de uso

### 1. Investigación de aplicación sospechosa

**Escenario**: Se detectó "W3-Relaciones-familiare" con 320GB de uso.

**Consulta:**
```
Dame detalle completo de W3-Relaciones-familiare mostrando 
todos los sitios y dispositivos que la están usando
```

**Resultado esperado:**
- Lista de sitios con mayor consumo de esta app
- Dispositivos específicos por sitio
- Podrás identificar qué routers SD-WAN están viendo este tráfico
- Siguiente paso: Acceder a esos sitios en vManage GUI para ver IPs de usuarios

### 2. Comparativa de aplicaciones críticas

**Escenario**: Verificar consumo de aplicaciones de negocio.

**Consulta:**
```
Analiza las aplicaciones ms-office-365, ms-teams y google-services 
mostrando los 10 sitios principales de cada una
```

**Resultado esperado:**
- Comparación de uso entre las 3 apps
- Identificación de sitios con mayor consumo
- Métricas de QoE para evaluar rendimiento

### 3. Troubleshooting de rendimiento

**Escenario**: Reportes de lentitud en aplicación específica.

**Consulta:**
```
Muéstrame el detalle de la aplicación salesforce con 
métricas de QoE y top 20 sitios
```

**Resultado esperado:**
- Identificar sitios con QoE bajo (🔴)
- Ver dispositivos con problemas de disponibilidad (⚠️)
- Priorizar sitios para investigación profunda

## Endpoints utilizados

La función consulta 3 endpoints de Cisco Analytics Cloud:

1. **Aplicaciones**
   - Endpoint: `/analytics/api/v4/dataservice/aggregate/applications`
   - Retorna: 435+ aplicaciones con métricas globales

2. **Sitios**
   - Endpoint: `/analytics/api/v4/dataservice/aggregate/sites`
   - Retorna: 223 sitios con uso total y QoE

3. **Dispositivos**
   - Endpoint: `/analytics/api/v4/dataservice/aggregate/devices`
   - Retorna: 325 dispositivos (routers SD-WAN) con IPs y uso

## Consideraciones de rendimiento

- **Timeout**: 30 segundos por endpoint
- **Datos procesados**: 
  - ~435 aplicaciones
  - ~223 sitios
  - ~325 dispositivos
- **Tiempo de respuesta**: 5-10 segundos típicamente

## Solución de problemas

### Error: "No se encontraron las aplicaciones especificadas"

**Causa**: Nombre de aplicación incorrecto o no existe en Analytics.

**Solución:**
1. El error muestra las primeras 20 aplicaciones disponibles
2. Usa nombres exactos (case-insensitive)
3. Para ver todas las aplicaciones: `dame un top 20 de aplicaciones`

### Error: "Error al conectar con Cisco Analytics Cloud"

**Causa**: Cookies de autenticación expiradas.

**Solución:**
```bash
cd /home/tsul/Documentos/serv_mcp
./refrescar_cookies_analytics.sh
pkill -9 -f claude-desktop  # Luego abre Claude Desktop
```

### Sin dispositivos mostrados para un sitio

**Causa**: El sitio existe en Analytics pero no tiene dispositivos reportando métricas.

**Verificar:**
- Estado del sitio en vManage
- Conectividad de routers SD-WAN
- Sincronización con Analytics Cloud

## Ejemplos avanzados

### Análisis multi-aplicación con contexto

```
Necesito investigar tráfico anormal. Muéstrame el detalle de:
- W3-Relaciones-familiare (app sospechosa)
- torrent (P2P)
- ssl (tráfico encriptado)

Incluye top 15 sitios de cada una para identificar 
dónde se concentra el uso
```

### Foco en sitio específico

```
Del análisis anterior vi que SITE_100 (tizapan) tiene 3TB de tráfico.
Muéstrame qué aplicaciones usa ese sitio y sus dispositivos
```

**Nota**: Para esto usa la función `comparar_trafico_sitios` que filtra por sitio específico.

## Roadmap / Mejoras futuras

- [ ] Filtrado por sitio específico en `analizar_detalle_aplicaciones`
- [ ] Integración con endpoint de flujos de vManage para IPs origen/destino
- [ ] Exportación a CSV/JSON
- [ ] Alertas automáticas en aplicaciones sospechosas
- [ ] Trending histórico (múltiples ventanas de tiempo)

## Referencias

- [ANALYTICS_SETUP.md](ANALYTICS_SETUP.md) - Configuración de cookies
- [server.py](server.py) - Implementación completa
- [test_detalle_aplicaciones.py](test_detalle_aplicaciones.py) - Tests de la función
