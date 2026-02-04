# 🎯 RESUMEN: Acceso a vManage GUI - IPs Origen/Destino

## ✅ CONFIGURACIÓN COMPLETADA

### Acceso configurado a:
- **vManage**: https://vmanage.cjf.gob.mx
- **Usuario**: jbahena
- **Estado**: ✅ Autenticado correctamente
- **Dispositivos**: 332 accesibles

## 📊 OBTENER IPs ORIGEN/DESTINO (3 MÉTODOS)

### MÉTODO 1: GUI - Exportar CSV ⭐ RECOMENDADO

**Pasos:**
1. Abre: https://vmanage.cjf.gob.mx
2. Login con tus credenciales
3. Navega: `Monitor → Applications → Application-Aware Routing`
4. Filtrar por aplicación: "W3-Relaciones-familiare"
5. Clic en botón **Export** (📥)
6. Descargar CSV con:
   - Source IP (usuarios LAN)
   - Destination IP (servidores externos)
   - Bytes, Site, QoE

**Ventajas:**
- ✅ Inmediato
- ✅ Datos completos
- ✅ Formato procesable (CSV)

---

### MÉTODO 2: GUI - Visualización directa

**Ruta alternativa:**
```
Monitor → Devices → [Selecciona router] → Real Time → DPI → Applications
```

**Verás tabla con:**
- Application name
- Source IP + Port
- Destination IP + Port
- Bytes sent/received
- QoE metrics

---

### MÉTODO 3: API (Requiere desarrollo)

**Estado actual:**
- ⚠️ Endpoints estándar retornan 404/400
- 🔄 Necesita captura de endpoints reales

**Para implementar:**
1. Abre vManage con Chrome DevTools (F12)
2. Tab Network → Filtro XHR
3. Navega a aplicaciones en GUI
4. Copia URLs de peticiones exitosas
5. Implementa función en MCP server

---

## 🎯 CASO DE USO: W3-Relaciones-familiare

### Objetivo:
Ver qué usuarios (IPs LAN) están usando esta aplicación y a qué servidores se conectan.

### Proceso:

1. **Abre vManage GUI**
   ```
   https://vmanage.cjf.gob.mx
   ```

2. **Navega a aplicaciones**
   ```
   Monitor → Applications
   ```

3. **Busca la aplicación**
   - En el filtro: "W3-Relaciones"
   - Se auto-completa: "W3-Relaciones-familiare"

4. **Analiza los datos**
   
   Verás tabla similar a:
   ```
   Application              | Source IP   | Dest IP      | Site      | Bytes   | QoE
   -------------------------|-------------|--------------|-----------|---------|-----
   W3-Relaciones-familiare  | 10.95.3.45  | 185.23.4.12  | SITE_304  | 1.2 GB  | 8.5
   W3-Relaciones-familiare  | 10.97.11.23 | 185.23.4.12  | SITE_367  | 850 MB  | 9.1
   W3-Relaciones-familiare  | 10.95.23.67 | 185.23.4.12  | SITE_366  | 650 MB  | 8.8
   ```

5. **Identifica patrones**
   - **IPs Origen**: Usuarios en LANs de cada sitio
   - **IPs Destino**: Servidores externos (posiblemente todos al mismo servidor)
   - **Sites**: Qué sucursales tienen el tráfico
   - **Volumen**: Quién consume más

6. **Exporta para análisis**
   - Botón Export → CSV
   - Abre en Excel/LibreOffice
   - Filtra, ordena, pivotea

---

## 📋 SCRIPTS DISPONIBLES

### Verificar conexión
```bash
cd /home/tsul/Documentos/serv_mcp
python test_vmanage_access.py
```

### Abrir GUI con guía
```bash
./abrir_vmanage_gui.sh
```

### Explorar API
```bash
python explorar_vmanage_api.py
```

---

## 💡 PRÓXIMAS ACCIONES

### AHORA (Inmediato):
1. ✅ Accede a vManage GUI
2. ✅ Ve a Monitor → Applications
3. ✅ Busca "W3-Relaciones-familiare"
4. ✅ Exporta CSV con IPs
5. ✅ Analiza datos en Excel

### PRÓXIMA SESIÓN (Automatización):
1. Captura endpoints con DevTools
2. Implementa función MCP `obtener_flujos_aplicacion(app_name)`
3. Integra con Claude Desktop
4. Consulta: "Dame IPs origen/destino de W3-Relaciones-familiare"

---

## 📖 DOCUMENTACIÓN COMPLETA

Ver: [VMANAGE_GUI_ACCESS.md](VMANAGE_GUI_ACCESS.md)

---

## ❓ FAQ

**P: ¿Por qué no usar solo Analytics Cloud?**
R: Analytics muestra agregados por sitio/dispositivo (routers), no flujos individuales con IPs de usuarios finales.

**P: ¿Puedo automatizar la exportación?**
R: Sí, pero necesitamos capturar los endpoints reales primero con DevTools.

**P: ¿Qué hago si no veo la aplicación?**
R: Verifica:
- Rango de tiempo (últimas 24h/7d)
- Sitio específico (filtro)
- DPI habilitado en policies

**P: ¿Las IPs destino son siempre las mismas?**
R: Si varios usuarios van al mismo servidor, sí. Esto indica posible CDN o servidor centralizado.

---

**Estado**: ✅ **LISTO PARA USAR GUI** - Automatización en desarrollo
