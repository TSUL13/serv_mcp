# Servidor MCP para Cisco SD-WAN

Servidor Model Context Protocol (MCP) para gestionar infraestructura de Cisco SD-WAN a través de vManage.

## 🚀 Características

- **Autenticación robusta** con vManage (sesión y tokens XSRF)
- **4 herramientas MCP** para Network Automation:
  - `listar_dispositivos`: Inventario completo de dispositivos
  - `ver_salud_equipo`: Estado y salud de un dispositivo específico
  - `ver_sesiones_bfd`: Estado de túneles BFD
  - `listar_alarmas_criticas`: Alarmas críticas de las últimas 24 horas

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
VMANAGE_IP=tu-vmanage-ip
VMANAGE_USERNAME=tu-usuario
VMANAGE_PASSWORD=tu-contraseña
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

## 📝 Notas

- Desarrollado para entornos Cisco SD-WAN con vManage
- Compatible con APIs de vManage 19.x y 20.x
- Los certificados SSL se ignoran (típico en labs)

## 🐛 Troubleshooting

- **Error de autenticación**: Verificar credenciales en `.env`
- **Timeout**: Revisar conectividad de red al vManage
- **SSL Errors**: Las advertencias SSL están desactivadas por defecto

## 👨‍💻 Desarrollado por

Servidor MCP especializado en Network Automation para Cisco SD-WAN.
