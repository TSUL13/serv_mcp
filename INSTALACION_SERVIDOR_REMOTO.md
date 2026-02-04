# 🌐 Servidor MCP Remoto - Acceso desde Claude Desktop en Otro PC

## 📋 Escenario

```
┌─────────────────────┐         SSH         ┌─────────────────────┐
│   PC Cliente        │  ←───────────→      │  Servidor Linux     │
│   Claude Desktop    │                     │   Servidor MCP      │
│   (tu escritorio)   │                     │   (remoto)          │
└─────────────────────┘                     └─────────────────────┘
```

## ⚠️ Importante: MCP usa STDIO, no HTTP

MCP **NO es un servidor HTTP** tradicional. Usa comunicación por stdio (entrada/salida estándar).

**Opciones para acceso remoto:**
1. ✅ **SSH + stdio** (Recomendado)
2. ✅ **API REST** (alternativa - ya la tienes)
3. ❌ Acceso HTTP directo al servidor MCP (no posible)

---

## ✅ OPCIÓN 1: Claude Desktop vía SSH (Recomendado)

Claude Desktop puede ejecutar el servidor MCP en remoto vía SSH.

### 📦 Preparar Servidor Linux

#### 1. Copiar archivos al servidor

```bash
# Desde tu PC local
scp -r /home/tsul/Documentos/serv_mcp usuario@servidor:/home/usuario/

# O usar rsync
rsync -avz /home/tsul/Documentos/serv_mcp/ usuario@servidor:/home/usuario/serv_mcp/
```

#### 2. Instalar dependencias en el servidor

```bash
# Conectar por SSH
ssh usuario@servidor

# Ir al directorio
cd /home/usuario/serv_mcp

# Crear entorno virtual
python3 -m venv venv

# Activar
source venv/bin/activate

# Instalar dependencias
pip install fastmcp requests urllib3 python-dotenv browser-cookie3

# Verificar
python server.py --help
```

#### 3. Configurar .env en el servidor

```bash
nano .env
```

Contenido:
```env
VMANAGE_IP=vmanage.cjf.gob.mx
VMANAGE_USERNAME=jbahena
VMANAGE_PASSWORD=jbahena@.
```

#### 4. Configurar acceso SSH sin contraseña

```bash
# En tu PC local, generar clave SSH (si no tienes)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_mcp

# Copiar clave pública al servidor
ssh-copy-id -i ~/.ssh/id_rsa_mcp.pub usuario@servidor

# Probar conexión
ssh -i ~/.ssh/id_rsa_mcp usuario@servidor "echo 'Conexión OK'"
```

### 🔧 Configurar Claude Desktop (PC Cliente)

Edita: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vmanage-remoto": {
      "command": "ssh",
      "args": [
        "-i", "/home/tu-usuario/.ssh/id_rsa_mcp",
        "usuario@servidor",
        "/home/usuario/serv_mcp/venv/bin/python",
        "/home/usuario/serv_mcp/server.py"
      ]
    }
  }
}
```

**Explicación:**
- `command: "ssh"` - Usa SSH para conectar
- `args` - Argumentos:
  1. `-i` - Clave SSH privada
  2. `usuario@servidor` - Servidor remoto
  3. Ruta al Python del venv
  4. Ruta al server.py

### 🚀 Usar

1. Reinicia Claude Desktop
2. Claude se conectará al servidor remoto vía SSH
3. El servidor MCP se ejecuta en el servidor Linux
4. stdio se tuneliza a través de SSH

### ✅ Ventajas
- ✅ MCP nativo funcionando
- ✅ Seguro (SSH cifrado)
- ✅ Sin configuración de red adicional
- ✅ Funciona detrás de firewalls

### ⚠️ Desventajas
- ❌ Requiere SSH configurado
- ❌ Latencia de red
- ❌ El servidor remoto debe tener acceso a vManage

---

## ✅ OPCIÓN 2: API REST + Proxy (Más Flexible)

Usa la API REST que ya creamos, expuesta en el servidor.

### 📦 En el Servidor Linux

#### 1. Copiar archivos

```bash
scp -r /home/tsul/Documentos/serv_mcp usuario@servidor:/home/usuario/
```

#### 2. Instalar dependencias

```bash
ssh usuario@servidor
cd /home/usuario/serv_mcp
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn requests urllib3 python-dotenv browser-cookie3
```

#### 3. Iniciar API REST

```bash
# Exponer en todas las interfaces (0.0.0.0)
python api_rest.py
```

O mejor, con systemd:

```bash
# Crear servicio
sudo nano /etc/systemd/system/vmanage-api.service
```

Contenido:
```ini
[Unit]
Description=vManage API REST
After=network.target

[Service]
Type=simple
User=usuario
WorkingDirectory=/home/usuario/serv_mcp
Environment="PATH=/home/usuario/serv_mcp/venv/bin"
ExecStart=/home/usuario/serv_mcp/venv/bin/python /home/usuario/serv_mcp/api_rest.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y arrancar
sudo systemctl enable vmanage-api
sudo systemctl start vmanage-api
sudo systemctl status vmanage-api
```

#### 4. Configurar firewall

```bash
# Permitir puerto 8000
sudo ufw allow 8000/tcp
```

### 🔧 En el PC Cliente

Accede a la API REST:
```bash
curl http://servidor:8000/devices
```

Con Gemini o GPT (ya configurado en ejemplo_gemini.py):
```python
# Cambiar URL base
API_BASE_URL = "http://servidor:8000"
```

### ✅ Ventajas
- ✅ Acceso desde cualquier cliente HTTP
- ✅ Múltiples clientes simultáneos
- ✅ Documentación en /docs
- ✅ Compatible con GPT, Gemini, Claude (sin MCP)

### ⚠️ Desventajas
- ❌ Claude Desktop no usa MCP nativo
- ❌ Requiere abrir puertos en firewall
- ❌ Sin cifrado (necesitas HTTPS para producción)

---

## ✅ OPCIÓN 3: Túnel SSH (Port Forwarding)

Si el servidor está en red privada, crea túnel SSH.

### 📦 Configuración

#### En el servidor (ejecuta API REST local)
```bash
python api_rest.py  # Corre en localhost:8000
```

#### En tu PC local (crea túnel)
```bash
ssh -N -L 8000:localhost:8000 usuario@servidor
```

Ahora accede localmente:
```bash
curl http://localhost:8000/devices
```

Claude Desktop (API REST), Gemini, GPT pueden usar `http://localhost:8000`

### ✅ Ventajas
- ✅ No expone puerto públicamente
- ✅ Cifrado SSH
- ✅ Simple

---

## 📊 Comparación de Opciones

| Característica | SSH+MCP | API REST | Túnel SSH |
|---|---|---|---|
| Claude Desktop (MCP nativo) | ✅ | ❌ | ❌ |
| GPT/Gemini | ❌ | ✅ | ✅ |
| Seguridad | ✅ Alta | ⚠️ Media | ✅ Alta |
| Múltiples clientes | ❌ | ✅ | ✅ |
| Complejidad | Media | Baja | Baja |
| Requiere SSH | ✅ | ❌ | ✅ |
| **Recomendado para** | Claude Desktop | Producción | Desarrollo |

---

## 🚀 RECOMENDACIÓN FINAL

### Para Claude Desktop (MCP nativo):
→ **Opción 1: SSH + MCP**

### Para GPT/Gemini/Múltiples clientes:
→ **Opción 2: API REST con systemd**

### Mejor de ambos mundos:
→ **Instala AMBOS en el servidor:**
- `server.py` para Claude vía SSH
- `api_rest.py` como servicio systemd para otros clientes

---

## 🔐 Consideraciones de Seguridad

### Para SSH + MCP:
```bash
# Usar clave SSH específica
# Deshabilitar password auth en SSH
# Configurar fail2ban
```

### Para API REST pública:
```bash
# Agregar autenticación Bearer Token
# Usar HTTPS con Let's Encrypt
# Configurar rate limiting
# Usar nginx como reverse proxy
```

Ver `CONECTAR_GPT_GEMINI.md` sección de seguridad.

---

## 📝 Script de Instalación Rápida (Servidor)

```bash
#!/bin/bash
# install_servidor.sh - Instalar en servidor Linux remoto

SERVER_USER="usuario"
SERVER_HOST="servidor.ejemplo.com"
REMOTE_PATH="/home/usuario/serv_mcp"

echo "🚀 Instalando servidor MCP en $SERVER_HOST..."

# 1. Copiar archivos
echo "📦 Copiando archivos..."
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  /home/tsul/Documentos/serv_mcp/ \
  $SERVER_USER@$SERVER_HOST:$REMOTE_PATH/

# 2. Instalar dependencias remotamente
echo "📦 Instalando dependencias..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/usuario/serv_mcp
python3 -m venv venv
source venv/bin/activate
pip install fastmcp fastapi uvicorn requests urllib3 python-dotenv browser-cookie3 -q
echo "✅ Dependencias instaladas"
ENDSSH

# 3. Probar servidor
echo "🧪 Probando servidor..."
ssh $SERVER_USER@$SERVER_HOST "cd $REMOTE_PATH && source venv/bin/activate && timeout 3 python server.py"

echo ""
echo "✅ Instalación completa"
echo ""
echo "📝 Próximos pasos:"
echo "1. Configurar .env en el servidor"
echo "2. Para MCP: Editar ~/.config/Claude/claude_desktop_config.json"
echo "3. Para API REST: Iniciar api_rest.py en el servidor"
echo ""
echo "Ver INSTALACION_SERVIDOR_REMOTO.md para más detalles"
```

---

## 🔧 Configuración Avanzada: Nginx Reverse Proxy

Para producción con API REST:

```nginx
# /etc/nginx/sites-available/vmanage-api
server {
    listen 443 ssl http2;
    server_name api.ejemplo.com;

    ssl_certificate /etc/letsencrypt/live/api.ejemplo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.ejemplo.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS
        add_header Access-Control-Allow-Origin * always;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20;
}
```

---

## 📚 Archivos Necesarios en el Servidor

```
/home/usuario/serv_mcp/
├── server.py              # Servidor MCP (para Claude vía SSH)
├── api_rest.py            # API REST (para GPT/Gemini)
├── browser_cookies.py     # Sistema de autenticación
├── .env                   # Credenciales vManage
├── venv/                  # Entorno virtual
├── requirements.txt       # Dependencias
└── README.md              # Documentación
```

---

## ✅ Verificación

### Probar MCP vía SSH (desde PC local):
```bash
ssh usuario@servidor "/home/usuario/serv_mcp/venv/bin/python /home/usuario/serv_mcp/server.py" << EOF
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
EOF
```

### Probar API REST:
```bash
curl http://servidor:8000/devices
```

---

## 🆘 Troubleshooting

### Error: "Permission denied (publickey)"
```bash
# Verificar clave SSH
ssh-add ~/.ssh/id_rsa_mcp
ssh -v usuario@servidor
```

### Error: "Connection refused"
```bash
# Verificar firewall
sudo ufw status
sudo ufw allow 8000/tcp

# Verificar servicio
sudo systemctl status vmanage-api
```

### Error: "Module not found"
```bash
# Verificar Python y dependencias
ssh usuario@servidor
cd /home/usuario/serv_mcp
source venv/bin/activate
python -c "import fastmcp; print('OK')"
```

### Error: Cookies no funcionan en servidor
```bash
# Solución: Usar credenciales directamente (no cookies)
# O: Configurar servidor con navegador y extraer cookies manualmente
```

---

## 📖 Documentación Relacionada

- `GUIA_CLAUDE_DESKTOP.md` - Configuración Claude Desktop
- `CONECTAR_GPT_GEMINI.md` - API REST para GPT/Gemini
- `README_COOKIES.md` - Sistema de autenticación
- `INSTALACION_COMPLETA.txt` - Instalación desde cero

---

## 💡 Consejos Finales

1. **Para Claude Desktop**: Usa SSH + MCP (Opción 1)
2. **Para producción multicliente**: Usa API REST (Opción 2)
3. **Siempre**: Configura SSH keys, no uses passwords
4. **Producción**: Usa HTTPS, autenticación, rate limiting
5. **Monitoreo**: Usa systemd para auto-restart
6. **Logs**: Configura logging en `/var/log/vmanage-api/`

