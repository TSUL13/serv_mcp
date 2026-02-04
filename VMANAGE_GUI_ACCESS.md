# 🔍 Acceso a vManage GUI para Flujos Detallados

## ✅ Estado: CONFIGURADO Y OPERATIVO

### Credenciales configuradas

- **Host**: vmanage.cjf.gob.mx
- **Usuario**: jbahena
- **Password**: Configurado en `.env`
- **Estado**: ✅ Autenticación exitosa

## 🌐 Acceso Directo

### 1. Documentación de API

```
https://vmanage.cjf.gob.mx/apidocs
```

Busca endpoints de:
- `dpi` (Deep Packet Inspection)
- `applications`
- `flows`
- `statistics`

### 2. Monitor de Aplicaciones

**URL**: https://vmanage.cjf.gob.mx

**Navegación para ver flujos con IPs origen/destino:**

```
Monitor → Applications → Application-Aware Routing
```

**O también:**

```
Monitor → Devices → [Router] → Real Time → DPI → Applications
```

## 📊 Obtener IPs Origen/Destino

### Método 1: Exportar desde GUI (RECOMENDADO)

1. Login en vManage
2. `Monitor → Applications`
3. Filtrar por aplicación (ej: "W3-Relaciones-familiare")
4. Clic en botón **Export** o 📥
5. Descargar CSV con:
   - Source IP (usuarios)
   - Destination IP (servidores)
   - Bytes
   - Site

### Método 2: Capturar endpoints con DevTools

Para implementar función automatizada:

1. Abre Chrome con DevTools (F12)
2. Tab **Network**, filtra por **XHR**
3. Navega a aplicaciones en vManage GUI
4. Copia URLs de peticiones exitosas
5. Guarda en `endpoints_capturados.txt`

Ejemplos de endpoints que verás:
```
GET /dataservice/data/device/dpi?deviceId=10.95.3.3&hours=24
POST /dataservice/statistics/dpi/aggregation
GET /dataservice/monitor/network/flows?query=...
```

## 🛠️ Scripts Disponibles

### `test_vmanage_access.py`
Verifica conectividad y autenticación a vManage.

```bash
python test_vmanage_access.py
```

**Resultado:**
- ✅ Conectividad
- ✅ Autenticación
- ✅ Token CSRF
- ✅ 332 dispositivos
- ✅ 23 usuarios

### `explorar_vmanage_api.py`
Explora endpoints disponibles de DPI/aplicaciones.

```bash
python explorar_vmanage_api.py
```

### `abrir_vmanage_gui.sh`
Abre vManage en navegador y muestra guía completa.

```bash
./abrir_vmanage_gui.sh
```

## 📝 Ejemplo de Uso: W3-Relaciones-familiare

### En vManage GUI:

1. **Login**: https://vmanage.cjf.gob.mx
2. **Ir a**: Monitor → Applications
3. **Buscar**: "W3-Relaciones"
4. **Ver tabla**:
   ```
   | Application              | Source IP   | Dest IP      | Site      | Bytes    |
   |-------------------------|-------------|--------------|-----------|----------|
   | W3-Relaciones-familiare | 10.95.3.45  | 185.23.4.12  | SITE_304  | 1.2 GB   |
   | W3-Relaciones-familiare | 10.97.11.23 | 185.23.4.12  | SITE_367  | 850 MB   |
   ```
5. **Exportar**: Clic en botón Export → CSV

### Con función MCP (una vez implementada):

```
Dame el detalle de flujos de W3-Relaciones-familiare 
mostrando IPs origen, destino y sitios
```

## 🔧 Limitaciones Actuales

### ❌ API de flujos no disponible directamente

Los endpoints probados retornan 404/400:
- `/dataservice/statistics/dpi/flows`
- `/dataservice/statistics/approute/fec/flows`
- `/dataservice/data/dpi/applications/aggregation`

**Razón**: vManage requiere parámetros específicos o usa endpoints diferentes.

### ✅ Soluciones Alternativas

1. **GUI directa** (inmediato)
2. **Capturar endpoints reales** con DevTools
3. **Consultar `/apidocs`** para endpoints correctos
4. **Analytics Cloud** para agregados (ya implementado)

## 📊 Comparación de Capacidades

| Característica | Analytics Cloud | vManage GUI | vManage API |
|----------------|----------------|-------------|-------------|
| Aplicaciones agregadas | ✅ 435 apps | ✅ | ⚠️ (por implementar) |
| Sitios y dispositivos | ✅ 223/325 | ✅ | ✅ |
| IPs origen/destino | ❌ | ✅ | ⚠️ (por implementar) |
| Flujos individuales | ❌ | ✅ | ⚠️ (por implementar) |
| Métricas QoE | ✅ | ✅ | ⚠️ (por implementar) |
| Automatización | ✅ | ❌ | ⚠️ (por implementar) |

## 🎯 Próximos Pasos

### Para obtener flujos con IPs:

1. **Corto plazo** (ahora):
   - Usa vManage GUI
   - Exporta CSVs manualmente
   - Filtra por aplicación

2. **Mediano plazo** (próxima sesión):
   - Captura endpoints con DevTools
   - Implementa función MCP con endpoints reales
   - Automatiza consultas de flujos

3. **Largo plazo**:
   - Integración completa vManage API
   - Alertas automáticas
   - Dashboard consolidado

## 📖 Documentación Relacionada

- [ANALYTICS_SETUP.md](ANALYTICS_SETUP.md) - Configuración Analytics Cloud
- [DOCS_ANALIZAR_DETALLE_APLICACIONES.md](DOCS_ANALIZAR_DETALLE_APLICACIONES.md) - Función actual
- `.env` - Credenciales vManage (configurado)

## 💡 Tips

### Navegación rápida en vManage:

- **Monitor → Applications**: Vista agregada
- **Monitor → Devices → [Router] → Real Time**: Flujos en vivo
- **Configuration → Policies**: Configuración DPI
- **Dashboard → Application QoE**: Métricas de calidad

### Búsqueda eficiente:

- Usa filtros en tablas (icono 🔍)
- Exporta antes de cambiar de página
- Guarda vistas personalizadas
- Usa rangos de tiempo específicos

### Troubleshooting:

- Si no ves datos: Verifica que DPI esté habilitado en policies
- Si flujos están vacíos: Puede ser tráfico muy antiguo
- Si exportación falla: Reduce el rango de tiempo

---

**Estado del proyecto**: ✅ vManage accesible, GUI operativo, esperando captura de endpoints para automatización completa.
