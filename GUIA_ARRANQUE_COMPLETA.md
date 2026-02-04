# 🚀 GUÍA COMPLETA: Arrancar Servidor MCP desde Cero

## 📋 PREREQUISITOS

- Python 3.12
- Chrome (para cookies de Analytics Cloud)
- Acceso a vManage (vmanage.cjf.gob.mx)
- Acceso a Analytics Cloud (us02.analytics.sdwan.cisco.com)
- Claude Desktop instalado

---

## 🔧 PASO 1: CONFIGURACIÓN INICIAL DEL PROYECTO

### 1.1 Clonar o posicionarse en el proyecto
```bash
cd /home/tsul/Documentos/serv_mcp
```

### 1.2 Crear entorno virtual
```bash
python3 -m venv venv
```

### 1.3 Activar entorno virtual
```bash
source venv/bin/activate
```

### 1.4 Instalar dependencias
```bash
pip install -r requirements.txt
```

**Dependencias principales:**
- `mcp` - Model Context Protocol
- `requests` - Peticiones HTTP
- `python-dotenv` - Variables de entorno
- `urllib3` - HTTP avanzado
- `browser_cookie3` - Extracción de cookies

---

## 🔑 PASO 2: CONFIGURAR CREDENCIALES DE VMANAGE

### 2.1 Editar archivo .env
```bash
nano .env
```

### 2.2 Configurar las siguientes variables:
```bash
# vManage Configuration
VMANAGE_HOST=vmanage.cjf.gob.mx
VMANAGE_USERNAME=jbahena
VMANAGE_PASSWORD="jbahen@."

# No tocar estas (se actualizan automáticamente):
# VMANAGE_JSESSIONID=...
# VMANAGE_XSRF_TOKEN=...
```

### 2.3 Verificar acceso a vManage
```bash
python test_vmanage_access.py
```

**Resultado esperado:**
```
✅ Servidor responde (Status: 200)
✅ Autenticación exitosa
✅ Token obtenido
✅ Lista de dispositivos: 332 registros
```

---

## 🍪 PASO 3: CONFIGURAR COOKIES DE ANALYTICS CLOUD

### 3.1 Abrir Analytics Cloud en Chrome
```bash
# Abre Chrome y navega a:
https://us02.analytics.sdwan.cisco.com
```

### 3.2 Iniciar sesión
- Usuario: jbahena (o tu usuario)
- Password: (tu contraseña de Analytics)
- **IMPORTANTE**: Espera a que cargue completamente el dashboard

### 3.3 Extraer y guardar cookies
```bash
cd /home/tsul/Documentos/serv_mcp
./refrescar_cookies_analytics.sh
```

**Resultado esperado:**
```
✅ Cookies guardadas correctamente
   Session: ***Jh9pDybsgI
   CSRF: ***9YcQzXmzk4
   Overlay: 164254
   Timestamp: 2026-02-04T11:31:53.083465
```

### 3.4 Verificar cookies guardadas
```bash
cat .analytics_cookies.json
```

Debe contener:
```json
{
  "session": "...",
  "csrf_token": "...",
  "overlay_id": "164254",
  "timestamp": "2026-02-04T11:31:53.083465"
}
```

---

## 🧪 PASO 4: PROBAR FUNCIONES DEL SERVIDOR

### 4.1 Probar función de Analytics Cloud
```bash
python test_funcion_actualizada.py
```

**Resultado esperado:**
```
🌐 ANÁLISIS DE TRÁFICO - RED COMPLETA
Total de aplicaciones: 435
Tráfico total: 16.21 TB

🏆 TOP 10 APLICACIONES:
1. ssl 🟢
   Familia: Encrypted
   Uso: 1944.54 GB (11.7%)
   ...
```

### 4.2 Probar función de detalle de aplicaciones
```bash
python test_detalle_aplicaciones.py
```

**Resultado esperado:**
```
📊 ANÁLISIS DETALLADO DE APLICACIONES
Total de sitios: 223
Total de dispositivos: 325

📱 APLICACIÓN: SSL 🟢
📍 TOP 5 SITIOS CON MAYOR TRÁFICO:
1. SITE_100 (tizapan) 🔴
   🖥️  Dispositivos principales:
      1. SDWAN-CJF-323-RT01 (10.97.250.193) ⚠️
   ...
```

---

## 🔧 PASO 5: CONFIGURAR CLAUDE DESKTOP

### 5.1 Ubicar archivo de configuración
```bash
# La ruta es:
~/.config/Claude/claude_desktop_config.json
```

### 5.2 Editar configuración
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

### 5.3 Agregar servidor MCP
```json
{
  "mcpServers": {
    "sdwan-analytics": {
      "command": "/home/tsul/Documentos/serv_mcp/venv/bin/python",
      "args": [
        "/home/tsul/Documentos/serv_mcp/server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/tsul/Documentos/serv_mcp"
      }
    }
  }
}
```

### 5.4 Verificar sintaxis JSON
```bash
python -m json.tool ~/.config/Claude/claude_desktop_config.json
```

---

## 🚀 PASO 6: ARRANCAR EL SERVIDOR MCP

### 6.1 Cerrar Claude Desktop (si está abierto)
```bash
pkill -9 -f claude-desktop
```

### 6.2 Verificar que no hay procesos residuales
```bash
ps aux | grep claude-desktop
```

### 6.3 Abrir Claude Desktop
```bash
# Desde el menú de aplicaciones, o:
claude-desktop &
```

### 6.4 Esperar carga del servidor (5-10 segundos)
Claude Desktop debe mostrar en logs internos:
```
MCP Server 'sdwan-analytics' connected
```

---

## ✅ PASO 7: VERIFICAR FUNCIONAMIENTO

### 7.1 Probar en Claude Desktop

Abre Claude Desktop y pregunta:

**Test 1: Análisis general**
```
Dame un top 10 de las aplicaciones más usadas en la red
```

**Respuesta esperada:**
```
🌐 ANÁLISIS DE TRÁFICO - RED COMPLETA
Período: Últimas 12 horas
Total de aplicaciones: 435
Tráfico total: 16.21 TB

🏆 TOP 10 APLICACIONES:
1. ssl 🟢 - 1944.54 GB (11.7%)
2. google-services 🟢 - 1629.00 GB (9.8%)
...
```

**Test 2: Análisis detallado**
```
Dame detalle de las aplicaciones ssl y http por sitio y dispositivo
```

**Respuesta esperada:**
```
📊 ANÁLISIS DETALLADO DE APLICACIONES
Total de sitios: 223
Total de dispositivos: 325

📱 APLICACIÓN: SSL 🟢
📍 TOP 10 SITIOS CON MAYOR TRÁFICO:
1. SITE_100 (tizapan) 🔴
   🖥️  Dispositivos principales:
      1. SDWAN-CJF-323-RT01 (10.97.250.193)
...
```

---

## 🔄 PASO 8: MANTENIMIENTO DE COOKIES

### 8.1 Las cookies expiran después de algunas horas

**Síntoma**: Claude Desktop responde:
```
⚠️ Error al conectar con Cisco Analytics Cloud.
Por favor ejecuta: ./refrescar_cookies_analytics.sh
```

### 8.2 Refrescar cookies
```bash
cd /home/tsul/Documentos/serv_mcp

# 1. Asegúrate de estar logueado en Analytics Cloud (Chrome)
# 2. Ejecuta:
./refrescar_cookies_analytics.sh

# 3. Reinicia Claude Desktop
pkill -9 -f claude-desktop

# 4. Abre Claude Desktop nuevamente
```

### 8.3 Automatizar (opcional)
Crear cron job para refrescar cookies cada 4 horas:
```bash
crontab -e

# Agregar:
0 */4 * * * cd /home/tsul/Documentos/serv_mcp && ./refrescar_cookies_analytics.sh >> /tmp/cookies_refresh.log 2>&1
```

---

## 🐛 PASO 9: SOLUCIÓN DE PROBLEMAS

### Problema 1: "ModuleNotFoundError"
```bash
cd /home/tsul/Documentos/serv_mcp
source venv/bin/activate
pip install -r requirements.txt
```

### Problema 2: "No se encontraron cookies"
```bash
# Verifica que Chrome esté abierto con sesión activa en Analytics
# Luego:
./refrescar_cookies_analytics.sh
```

### Problema 3: Claude Desktop no conecta al servidor
```bash
# 1. Verificar configuración
cat ~/.config/Claude/claude_desktop_config.json

# 2. Verificar logs de Claude Desktop
tail -f ~/.config/Claude/logs/mcp*.log

# 3. Probar servidor manualmente
cd /home/tsul/Documentos/serv_mcp
source venv/bin/activate
python server.py
```

### Problema 4: "400 Bad Request" de Analytics
```bash
# Las cookies expiraron
./refrescar_cookies_analytics.sh
pkill -9 -f claude-desktop
# Abre Claude Desktop
```

### Problema 5: vManage no responde
```bash
# Verificar conectividad
ping vmanage.cjf.gob.mx

# Verificar credenciales
python test_vmanage_access.py
```

---

## 📊 PASO 10: FUNCIONES DISPONIBLES

### 1. `analizar_trafico_total_red()`
**Uso en Claude:**
```
Dame un top 10 de las aplicaciones más usadas
```

**Retorna:**
- Top 20 aplicaciones por uso
- Métricas QoE (latencia, jitter, pérdida)
- Cantidad de sitios usando cada app

---

### 2. `analizar_detalle_aplicaciones(aplicaciones, top_sitios)`
**Uso en Claude:**
```
Dame detalle de ssl, http y W3-Relaciones-familiare 
mostrando top 5 sitios de cada una
```

**Retorna:**
- Uso total por aplicación
- Top N sitios con mayor tráfico
- Top 3 dispositivos por sitio con IPs
- Métricas QoE por sitio

---

### 3. `comparar_trafico_sitios(site_id_1, site_id_2)`
**Uso en Claude:**
```
Compara el tráfico entre SITE_100 y SITE_200
```

**Retorna:**
- Aplicaciones comunes y exclusivas
- Diferencias de uso
- Comparativa de QoE

---

### 4. Otras funciones disponibles
```
- listar_dispositivos()
- ver_estado_dispositivo(device_id)
- obtener_metricas_device(system_ip)
- listar_templates()
- ver_informacion_template(template_id)
- listar_politicas()
```

---

## 🔐 SEGURIDAD

### Archivos sensibles (NO subir a Git):
- `.env` - Credenciales vManage
- `.analytics_cookies.json` - Cookies Analytics Cloud
- `venv/` - Entorno virtual

### Ya configurado en .gitignore:
```
.env
.analytics_cookies.json
venv/
__pycache__/
*.pyc
```

---

## 📁 ESTRUCTURA DEL PROYECTO

```
serv_mcp/
├── server.py                              # 🔥 Servidor MCP principal
├── .env                                   # 🔑 Credenciales vManage
├── .analytics_cookies.json                # 🍪 Cookies Analytics (auto-generado)
├── requirements.txt                       # 📦 Dependencias Python
├── venv/                                  # 🐍 Entorno virtual
│
├── 🧪 Tests:
├── test_vmanage_access.py                 # Test vManage
├── test_funcion_actualizada.py            # Test Analytics
├── test_detalle_aplicaciones.py           # Test detalles
│
├── 🔧 Scripts:
├── refrescar_cookies_analytics.sh         # Refresh cookies Analytics
├── abrir_vmanage_gui.sh                   # Abrir vManage GUI
├── explorar_vmanage_api.py                # Explorar API
│
└── 📖 Documentación:
    ├── ANALYTICS_SETUP.md                 # Setup Analytics Cloud
    ├── DOCS_ANALIZAR_DETALLE_APLICACIONES.md  # Docs función detalle
    ├── VMANAGE_GUI_ACCESS.md              # Acceso vManage GUI
    └── RESUMEN_VMANAGE_IPS.md             # Obtener IPs origen/destino
```

---

## 🎯 CHECKLIST RÁPIDO

Antes de arrancar, verifica:

- [ ] Python 3.12 instalado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] `.env` configurado con credenciales vManage
- [ ] Sesión activa en Analytics Cloud (Chrome)
- [ ] Cookies extraídas (`./refrescar_cookies_analytics.sh`)
- [ ] `claude_desktop_config.json` configurado
- [ ] Tests ejecutados exitosamente
- [ ] Claude Desktop reiniciado

---

## 🚀 COMANDO ÚNICO PARA ARRANCAR

Si ya tienes todo configurado:

```bash
#!/bin/bash
cd /home/tsul/Documentos/serv_mcp

# 1. Activar entorno
source venv/bin/activate

# 2. Refrescar cookies (si han pasado >4 horas)
./refrescar_cookies_analytics.sh

# 3. Test rápido
echo "🧪 Probando Analytics..."
python -c "from test_funcion_actualizada import analizar_trafico_total_red; print('✅ OK' if analizar_trafico_total_red() else '❌ FAIL')" | head -5

# 4. Reiniciar Claude Desktop
echo "🔄 Reiniciando Claude Desktop..."
pkill -9 -f claude-desktop
sleep 2

echo "✅ Listo. Abre Claude Desktop manualmente."
echo "📝 Prueba: 'Dame un top 10 de las aplicaciones más usadas'"
```

Guarda como `start_mcp.sh` y ejecuta:
```bash
chmod +x start_mcp.sh
./start_mcp.sh
```

---

## 📞 AYUDA ADICIONAL

### Logs de Claude Desktop
```bash
tail -f ~/.config/Claude/logs/mcp*.log
```

### Logs del servidor MCP
```bash
# El servidor imprime a stdout/stderr que Claude Desktop captura
# Ver en logs de Claude Desktop
```

### Verificar servidor funcionando
```bash
# Si Claude Desktop está abierto, el servidor debe estar corriendo
ps aux | grep "server.py"
```

---

**¡Servidor MCP listo! 🚀**

Para actualizaciones de código:
```bash
cd /home/tsul/Documentos/serv_mcp
git pull
pkill -9 -f claude-desktop  # Reiniciar Claude Desktop
```
