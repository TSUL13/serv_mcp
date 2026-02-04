# Integración con Cisco Analytics Cloud

## ⚠️ Configuración requerida

El servidor MCP requiere cookies de autenticación de Cisco Analytics Cloud para funcionar.

### Paso 1: Iniciar sesión en Analytics Cloud

1. Abre Chrome y ve a: https://us02.analytics.sdwan.cisco.com
2. Inicia sesión con tus credenciales de Cisco
3. Espera a que cargue completamente el dashboard
4. Verifica que puedas ver datos de aplicaciones

### Paso 2: Extraer cookies

Ejecuta el script para extraer y guardar las cookies:

```bash
cd /home/tsul/Documentos/serv_mcp
./refrescar_cookies_analytics.sh
```

Deberías ver:
```
✅ Cookies guardadas correctamente
   Session: ***xxxxxxxxxx
   CSRF: ***xxxxxxxxxx
   Overlay: 164254
   Timestamp: 2026-02-04T11:31:53.083465
```

### Paso 3: Reiniciar Claude Desktop

```bash
pkill -9 -f claude-desktop
```

Luego abre Claude Desktop nuevamente desde tu menú de aplicaciones.

## 🔄 Mantener cookies actualizadas

Las cookies de Analytics Cloud expiran después de algunas horas. Si Claude Desktop reporta error de conexión:

1. Verifica que estés logueado en Analytics Cloud (abre en Chrome)
2. Ejecuta nuevamente: `./refrescar_cookies_analytics.sh`
3. Reinicia Claude Desktop

## 📝 Funciones disponibles

### `analizar_trafico_total_red`

Analiza el tráfico de toda la red SD-WAN.

**Ejemplo de uso en Claude Desktop:**
```
Dame un top 10 de las aplicaciones más usadas en la red
```

**Respuesta esperada:**
- Lista de aplicaciones ordenadas por uso
- Consumo de ancho de banda en GB/TB
- Métricas de QoE (calidad de experiencia):
  - Score QoE (0-10)
  - Latencia promedio
  - Jitter
  - Pérdida de paquetes
- Número de sitios usando cada aplicación

## 🐛 Solución de problemas

### Error: "No se pudo conectar a Analytics Cloud"

**Causa:** Cookies expiradas o no disponibles

**Solución:**
1. Verifica login en Chrome: https://us02.analytics.sdwan.cisco.com
2. Ejecuta: `./refrescar_cookies_analytics.sh`
3. Reinicia Claude Desktop

### Error: "No se encontraron cookies"

**Causa:** No estás logueado en Chrome

**Solución:**
1. Abre Chrome (no otro navegador)
2. Ve a: https://us02.analytics.sdwan.cisco.com
3. Inicia sesión
4. Ejecuta el script de refresh de cookies

### Las cookies se extraen pero Claude Desktop no funciona

**Causa:** Claude Desktop no relee el archivo de cookies

**Solución:**
1. Cierra completamente Claude Desktop: `pkill -9 -f claude-desktop`
2. Abre Claude Desktop desde el menú
3. Espera 5-10 segundos antes de hacer consultas

## 📊 Ventana de tiempo

Actualmente Analytics Cloud está configurado para usar una ventana de 12 horas fija:
- **Inicio:** 2026-02-04 05:00:00
- **Fin:** 2026-02-04 17:05:00

> **Nota:** Esta es una limitación temporal mientras se implementa la detección automática de ventanas disponibles. Los datos son reales pero pueden no ser de las últimas horas exactas.

## 🔐 Seguridad

- El archivo `.analytics_cookies.json` contiene credenciales sensibles
- Está incluido en `.gitignore` para no subirlo a Git
- Las cookies expiran automáticamente después de algunas horas
- Solo son válidas mientras tu sesión de Analytics esté activa

## 📁 Archivos relevantes

- `refrescar_cookies_analytics.sh` - Script para extraer cookies
- `.analytics_cookies.json` - Cookies guardadas (no en Git)
- `server.py` - Servidor MCP con integración de Analytics
- `test_funcion_actualizada.py` - Test de la función
