# 🍪 Sistema de Cookies Automáticas para vManage

## ¿Por qué cookies del navegador?

vManage **bloquea la autenticación programática** pero **acepta sesiones del navegador**. Este sistema extrae automáticamente las cookies de tu navegador para que los scripts funcionen sin problemas.

## ✅ Ventajas

- ✨ **Automático**: No necesitas copiar/pegar cookies manualmente
- 🔄 **Actualización automática**: Detecta y refresca cookies cuando expiran
- 🌐 **Multi-navegador**: Soporta Chrome, Firefox, Edge y Chromium
- 🔒 **Seguro**: Las cookies se extraen directamente de tu navegador, no se almacenan

## 📋 Requisitos

1. **Tener una sesión activa en vManage**
   - Abre tu navegador (Chrome, Firefox o Edge)
   - Ve a `https://vmanage.cjf.gob.mx`
   - Inicia sesión con tus credenciales
   - **DEJA LA PESTAÑA ABIERTA** (no cierres la sesión)

2. **Python con dependencias instaladas**
   ```bash
   source venv/bin/activate
   pip install browser-cookie3
   ```

## 🚀 Uso Rápido

### Opción 1: CLI Independiente (Recomendado para empezar)

```bash
source venv/bin/activate
python cli.py
```

El CLI ahora usa cookies automáticamente. Solo asegúrate de tener vManage abierto en tu navegador.

### Opción 2: Servidor MCP con Claude Desktop

```bash
# 1. Asegúrate de tener vManage abierto en tu navegador
# 2. Reinicia Claude Desktop
# 3. Las herramientas MCP extraerán las cookies automáticamente
```

### Opción 3: Probar la extracción de cookies

```bash
source venv/bin/activate
python browser_cookies.py
```

Este script te mostrará si las cookies se extraen correctamente.

## 🔧 Cómo Funciona

1. **Cuando ejecutas el CLI o el servidor MCP:**
   - El sistema busca cookies de vManage en Chrome, Firefox y Edge
   - Extrae `JSESSIONID` y `X-XSRF-TOKEN`
   - Las usa para autenticar las peticiones al API

2. **Si las cookies expiran:**
   - El sistema detecta la expiración
   - Extrae nuevas cookies automáticamente
   - Continúa funcionando sin intervención

3. **Si no encuentra cookies:**
   - Te avisa que abras vManage en tu navegador
   - Espera a que inicies sesión
   - Reintenta la extracción

## ⚠️ Solución de Problemas

### "No se encontraron cookies en ningún navegador"

**Solución:**
1. Abre Chrome, Firefox o Edge (no otros navegadores)
2. Ve a `https://vmanage.cjf.gob.mx`
3. Inicia sesión
4. Deja la pestaña abierta
5. Ejecuta el script nuevamente

### "Cookies extraídas pero no válidas"

**Solución:**
1. Tu sesión en el navegador expiró
2. Refresca la página en el navegador
3. Si te pide login, inicia sesión nuevamente
4. Ejecuta el script nuevamente

### "Error al obtener cookies"

**Solución:**
1. Verifica que tienes `browser-cookie3` instalado:
   ```bash
   pip install browser-cookie3
   ```

2. En Linux, puede que necesites permisos:
   ```bash
   # Para Chrome
   chmod 600 ~/.config/google-chrome/Default/Cookies
   
   # Para Firefox
   chmod 600 ~/.mozilla/firefox/*.default*/cookies.sqlite
   ```

## 📚 Archivos del Sistema

- `browser_cookies.py` - Extractor de cookies del navegador
- `server.py` - Servidor MCP (actualizado con sistema de cookies)
- `cli.py` - CLI independiente (actualizado con sistema de cookies)
- `test_con_cookies.py` - Script de prueba con cookies manuales

## 🔒 Seguridad

- Las cookies se extraen **en tiempo real** del navegador
- **No se almacenan** en archivos
- Se mantienen solo en memoria durante la ejecución
- Se refrescan automáticamente cuando expiran

## 💡 Tips

1. **Mantén la sesión abierta**: Mientras trabajas con el CLI o MCP, deja vManage abierto en tu navegador

2. **Múltiples navegadores**: Si tienes sesiones en varios navegadores, el sistema intentará todos y usará el primero que funcione

3. **Renovación automática**: Si tu sesión expira después de 5 minutos, el sistema automáticamente extrae nuevas cookies

4. **Debugging**: Usa `python browser_cookies.py` para verificar que todo funciona antes de usar el CLI o MCP

## 🎯 Diferencia con el Sistema Anterior

| Aspecto | Sistema Anterior | Sistema Actual |
|---------|-----------------|----------------|
| Autenticación | POST a `/j_security_check` | Cookies del navegador |
| Resultado | ❌ Bloqueado por vManage | ✅ Funciona perfectamente |
| Configuración | Username/Password en `.env` | Sesión activa en navegador |
| Mantenimiento | Manual si falla | Automático |

## ✨ Próximos Pasos

1. **Abre vManage en tu navegador** e inicia sesión
2. **Ejecuta el CLI** con `python cli.py`
3. **O usa Claude Desktop** y las herramientas MCP
4. **¡Disfruta de las 332 dispositivos!** 🎉
