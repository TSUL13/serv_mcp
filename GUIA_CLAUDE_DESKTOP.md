# 🤖 Usar el Servidor MCP con Claude Desktop

## ✅ Configuración Actual

Tu Claude Desktop ya está configurado con el servidor MCP:
- **Servidor**: cisco-sdwan
- **4 Herramientas disponibles**:
  1. 📋 `listar_dispositivos` - Ver todos los dispositivos SD-WAN
  2. 🏥 `ver_salud_equipo` - Estado de un dispositivo específico
  3. 🔗 `ver_sesiones_bfd` - Sesiones BFD de un dispositivo
  4. 🚨 `listar_alarmas_criticas` - Alarmas críticas del sistema

## 🚀 Pasos para Usar

### 1. Asegúrate de tener sesión activa en Firefox

```bash
# Abre Firefox y ve a:
https://vmanage.cjf.gob.mx

# Inicia sesión con:
Usuario: jbahena
Password: jbahena@.

# DEJA LA PESTAÑA ABIERTA (no cierres Firefox)
```

### 2. Reinicia Claude Desktop

```bash
# Cierra Claude Desktop completamente
# Luego ábrelo nuevamente
```

### 3. Verifica que las herramientas estén disponibles

En Claude Desktop, escribe:
```
¿Qué herramientas MCP tienes disponibles?
```

Deberías ver las 4 herramientas de cisco-sdwan.

### 4. Empieza a usar las herramientas

Ejemplos de consultas que puedes hacer:

#### 📋 Listar dispositivos
```
Muéstrame todos los dispositivos SD-WAN
```

```
Lista los primeros 10 dispositivos
```

```
¿Cuántos dispositivos tenemos en total?
```

#### 🏥 Ver salud de un equipo
```
Muéstrame el estado de salud del dispositivo SDWAN-CJF-323-vManage01
```

```
¿Cómo está el equipo con IP 10.80.10.207?
```

#### 🔗 Ver sesiones BFD
```
Muéstrame las sesiones BFD del dispositivo 10.80.10.207
```

```
¿Cuántas sesiones BFD tiene el equipo SDWAN-CJF-323-vManage01?
```

#### 🚨 Listar alarmas críticas
```
¿Hay alarmas críticas en el sistema?
```

```
Muéstrame todas las alarmas críticas activas
```

## 🔧 Solución de Problemas

### "Las herramientas no aparecen"

**Solución:**
1. Cierra Claude Desktop completamente
2. Verifica que Firefox tenga sesión activa en vManage
3. Ejecuta el test: `python test_completo.py` (debe mostrar 332 dispositivos)
4. Abre Claude Desktop nuevamente

### "Error al ejecutar herramienta"

**Solución:**
1. Tu sesión en Firefox expiró
2. Refresca la página en Firefox
3. Inicia sesión nuevamente
4. Reintenta en Claude Desktop

### "No se encontraron cookies"

**Solución:**
1. Verifica que Firefox esté abierto
2. Ve a https://vmanage.cjf.gob.mx
3. Inicia sesión y deja la pestaña abierta
4. Ejecuta: `python browser_cookies.py` para verificar
5. Reintenta en Claude Desktop

## 💡 Tips

1. **Mantén Firefox abierto**: Mientras uses Claude Desktop, mantén Firefox con la sesión de vManage activa

2. **Consultas naturales**: Puedes hacer preguntas en lenguaje natural, Claude entiende y usa las herramientas correctas

3. **Combina consultas**: Puedes pedir múltiples cosas, por ejemplo:
   ```
   Lista los dispositivos y luego muéstrame las alarmas críticas
   ```

4. **Debugging**: Si algo falla, ejecuta `python test_completo.py` para verificar que el sistema funciona

## 🎯 Ejemplos Avanzados

### Análisis completo
```
Muéstrame un resumen del estado de la red: 
total de dispositivos, alarmas críticas y 
estado de los vManage
```

### Filtrado
```
De todos los dispositivos, muéstrame solo 
los que son de tipo vmanage
```

### Comparación
```
Compara el estado de salud de 
SDWAN-CJF-323-vManage01 y 
SDWAN-CJF-323-vManage02
```

## ⚙️ Configuración Técnica

**Archivo de configuración:**
```
~/.config/Claude/claude_desktop_config.json
```

**Servidor MCP:**
```
/home/tsul/Documentos/serv_mcp/server.py
```

**Python virtual environment:**
```
/home/tsul/Documentos/serv_mcp/venv
```

## 🔄 Actualizar el Servidor

Si haces cambios en el código:

```bash
# Cierra Claude Desktop
# Luego ábrelo nuevamente
# Los cambios se aplicarán automáticamente
```

## 📊 Estado Actual

- ✅ Servidor MCP configurado
- ✅ 4 herramientas disponibles
- ✅ Sistema de cookies automático funcionando
- ✅ 332 dispositivos accesibles
- ✅ Claude Desktop conectado

¡Todo listo para usar! 🎉
