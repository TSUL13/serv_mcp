# ⚠️ PROBLEMA: Autenticación con Cookies en Servidor Remoto

## 🔴 El Problema

El sistema actual usa `browser_cookies.py` que:
- ✅ Extrae cookies de Firefox/Chrome LOCAL
- ❌ No funciona en servidor Linux sin navegador
- ❌ El servidor remoto no tiene sesión activa en vManage

```
PC Local: Firefox con sesión vManage → ✅ Cookies disponibles
Servidor Linux: Sin navegador → ❌ Sin cookies
```

## ✅ Soluciones Disponibles

### **SOLUCIÓN 1: Pasar Cookies como Variables de Entorno (Recomendado)**

Extraer cookies localmente y pasarlas al servidor vía SSH.

#### Paso 1: Extraer cookies localmente

Crea script local: `extraer_cookies.py`
```python
#!/usr/bin/env python3
from browser_cookies import BrowserCookieExtractor
import os

extractor = BrowserCookieExtractor("vmanage.cjf.gob.mx")
jsessionid, xsrf_token = extractor.get_cookies()

if jsessionid:
    print(f"export VMANAGE_JSESSIONID='{jsessionid}'")
    print(f"export VMANAGE_XSRF_TOKEN='{xsrf_token}'")
else:
    print("echo 'Error: No se encontraron cookies'", file=sys.stderr)
```

#### Paso 2: Modificar servidor para usar variables de entorno

El servidor ya tiene esta capacidad - solo hay que exportar las cookies:

```bash
# En tu PC local, extrae cookies
eval $(python extraer_cookies.py)

# Ejecuta servidor remoto pasando cookies
ssh usuario@servidor \
  "export VMANAGE_JSESSIONID='$VMANAGE_JSESSIONID' && \
   export VMANAGE_XSRF_TOKEN='$VMANAGE_XSRF_TOKEN' && \
   cd /home/usuario/serv_mcp && \
   source venv/bin/activate && \
   python server.py"
```

---

### **SOLUCIÓN 2: Usar .env con Cookies (Más Persistente)**

#### Paso 1: Extraer cookies y guardar

```bash
# En PC local
python extraer_cookies.py > cookies.env
```

#### Paso 2: Copiar al servidor

```bash
# Copiar cookies al servidor
scp cookies.env usuario@servidor:/home/usuario/serv_mcp/.env.cookies

# O agregar directamente a .env
ssh usuario@servidor "cat /home/usuario/serv_mcp/.env.cookies >> /home/usuario/serv_mcp/.env"
```

#### Paso 3: Modificar browser_cookies.py

Ya está implementado - el código primero intenta variables de entorno antes de extraer del navegador.

---

### **SOLUCIÓN 3: Autenticación Directa (Bypass del Bloqueo)**

Intentar autenticación programática con técnicas avanzadas:

```python
# Modificación en browser_cookies.py para servidor remoto
def authenticate_direct(vmanage_ip, username, password):
    """Intento de autenticación directa con headers especiales"""
    session = requests.Session()
    session.verify = False
    
    # Headers que imitan navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'es-ES,es;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': f'https://{vmanage_ip}/',
        'Origin': f'https://{vmanage_ip}',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Intento 1: Login directo
    try:
        login_response = session.post(
            f'https://{vmanage_ip}/j_security_check',
            data={
                'j_username': username,
                'j_password': password
            },
            headers=headers,
            allow_redirects=True,
            timeout=30
        )
        
        if 'JSESSIONID' in session.cookies:
            # Obtener token
            token_response = session.get(
                f'https://{vmanage_ip}/dataservice/client/token',
                timeout=10
            )
            xsrf_token = token_response.text
            
            return session.cookies.get('JSESSIONID'), xsrf_token
    except:
        pass
    
    return None, None
```

**⚠️ Advertencia**: vManage puede seguir bloqueando esto.

---

### **SOLUCIÓN 4: Proxy de Cookies (Avanzado)**

Crear servicio local que provee cookies al servidor remoto.

#### En PC local: Servicio de cookies

```python
# cookie_proxy.py - Corre en PC local
from flask import Flask, jsonify
from browser_cookies import BrowserCookieExtractor

app = Flask(__name__)

@app.route('/cookies')
def get_cookies():
    extractor = BrowserCookieExtractor("vmanage.cjf.gob.mx")
    jsessionid, xsrf = extractor.get_cookies()
    return jsonify({
        'JSESSIONID': jsessionid,
        'XSRF-TOKEN': xsrf
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
```

#### En servidor remoto: Obtener cookies del proxy

```python
# Modificar browser_cookies.py
def get_cookies_from_proxy(proxy_url):
    """Obtiene cookies de un proxy local"""
    try:
        response = requests.get(f"{proxy_url}/cookies", timeout=5)
        data = response.json()
        return data.get('JSESSIONID'), data.get('XSRF-TOKEN')
    except:
        return None, None
```

```bash
# Ejecutar con proxy
ssh usuario@servidor \
  "export COOKIE_PROXY_URL='http://tu-ip-local:5555' && \
   cd /home/usuario/serv_mcp && \
   python server.py"
```

---

### **SOLUCIÓN 5: Navegador en Servidor (Complejo)**

Instalar navegador en el servidor y hacer login allí.

```bash
# En el servidor Linux
sudo apt update
sudo apt install firefox

# Ejecutar Firefox con display virtual
sudo apt install xvfb
Xvfb :99 -ac &
export DISPLAY=:99
firefox &

# O usar navegador headless
sudo apt install chromium-browser
chromium-browser --headless --remote-debugging-port=9222
```

Luego conectarte por VNC o X11 forwarding para hacer login en vManage.

---

## 📊 Comparación de Soluciones

| Solución | Complejidad | Seguridad | Funciona? |
|---|---|---|---|
| **1. Variables de entorno** | ⭐ Baja | ⭐⭐⭐ Media | ✅ Sí |
| **2. .env con cookies** | ⭐ Baja | ⭐⭐ Baja | ✅ Sí |
| **3. Auth directa** | ⭐⭐ Media | ⭐⭐⭐ Alta | ⚠️ Puede fallar |
| **4. Proxy de cookies** | ⭐⭐⭐ Alta | ⭐⭐ Media | ✅ Sí |
| **5. Navegador en servidor** | ⭐⭐⭐⭐ Muy Alta | ⭐⭐⭐ Alta | ✅ Sí |

---

## 🚀 Implementación Recomendada

### **MEJOR OPCIÓN: Solución 1 + Solución 2 (Híbrido)**

1. Extraer cookies localmente
2. Pasarlas al servidor
3. Refrescar periódicamente

#### Script Completo: `sincronizar_cookies.sh`

```bash
#!/bin/bash
# Sincroniza cookies del navegador local al servidor remoto

SERVER_USER="usuario"
SERVER_HOST="servidor.com"
REMOTE_PATH="/home/usuario/serv_mcp"

echo "🔑 Extrayendo cookies del navegador local..."
python3 << 'PYTHON'
from browser_cookies import BrowserCookieExtractor
extractor = BrowserCookieExtractor("vmanage.cjf.gob.mx")
jsessionid, xsrf = extractor.get_cookies()
if jsessionid:
    print(f"VMANAGE_JSESSIONID={jsessionid}")
    print(f"VMANAGE_XSRF_TOKEN={xsrf}")
else:
    print("ERROR: No se encontraron cookies")
    exit(1)
PYTHON

# Si tuvo éxito, copiar al servidor
if [ $? -eq 0 ]; then
    echo "✅ Cookies extraídas"
    
    # Crear archivo temporal
    python3 << 'PYTHON' > /tmp/vmanage_cookies.env
from browser_cookies import BrowserCookieExtractor
extractor = BrowserCookieExtractor("vmanage.cjf.gob.mx")
jsessionid, xsrf = extractor.get_cookies()
print(f"VMANAGE_JSESSIONID={jsessionid}")
print(f"VMANAGE_XSRF_TOKEN={xsrf}")
PYTHON
    
    echo "📤 Copiando cookies al servidor..."
    scp /tmp/vmanage_cookies.env $SERVER_USER@$SERVER_HOST:$REMOTE_PATH/.env.cookies
    
    echo "🔄 Actualizando .env en servidor..."
    ssh $SERVER_USER@$SERVER_HOST << EOF
cd $REMOTE_PATH
# Backup de .env actual
cp .env .env.backup 2>/dev/null || true
# Remover cookies viejas
sed -i '/VMANAGE_JSESSIONID/d' .env
sed -i '/VMANAGE_XSRF_TOKEN/d' .env
# Agregar cookies nuevas
cat .env.cookies >> .env
rm .env.cookies
echo "✅ Cookies actualizadas en servidor"
EOF
    
    rm /tmp/vmanage_cookies.env
    echo "✅ Sincronización completa"
else
    echo "❌ Error extrayendo cookies"
    exit 1
fi
```

---

## ⚙️ Modificación de Código Necesaria

### Actualizar `browser_cookies.py` para priorizar variables de entorno:

```python
# Al inicio de BrowserCookieExtractor.__init__
def __init__(self, vmanage_host: str):
    self.vmanage_host = vmanage_host
    
    # NUEVO: Primero intentar variables de entorno
    env_jsessionid = os.getenv('VMANAGE_JSESSIONID')
    env_xsrf = os.getenv('VMANAGE_XSRF_TOKEN')
    
    if env_jsessionid and env_xsrf:
        print("✅ Usando cookies de variables de entorno")
        self.jsessionid = env_jsessionid
        self.xsrf_token = env_xsrf
        self.last_extraction = datetime.now()
        self.from_env = True
    else:
        self.from_env = False
        self.jsessionid = None
        self.xsrf_token = None
        self.last_extraction = None
```

### Actualizar `get_cookies()`:

```python
def get_cookies(self, force_refresh: bool = False) -> Tuple[Optional[str], Optional[str]]:
    # Si ya tenemos de variables de entorno, retornar
    if self.from_env and not force_refresh:
        return self.jsessionid, self.xsrf_token
    
    # Si no hay o se fuerza refresh, extraer del navegador
    if force_refresh or not self.jsessionid or not self.xsrf_token:
        return self.extract_cookies()
    
    return self.jsessionid, self.xsrf_token
```

---

## 🔄 Flujo Completo Recomendado

```
1. PC Local:
   - Navegador abierto con sesión vManage ✅
   - Ejecutar: ./sincronizar_cookies.sh
   - Cookies extraídas y copiadas al servidor

2. Servidor Remoto:
   - .env actualizado con cookies frescas ✅
   - Servidor MCP usa cookies del .env
   - Claude Desktop se conecta vía SSH

3. Mantenimiento:
   - Ejecutar sincronizar_cookies.sh cada N horas
   - O crear cron job para automatizar
```

---

## ⏰ Automatización (Opcional)

### Cron job para sincronizar cookies cada 4 horas:

```bash
# En tu PC local
crontab -e

# Agregar:
0 */4 * * * /home/tsul/Documentos/serv_mcp/sincronizar_cookies.sh >> /tmp/cookie_sync.log 2>&1
```

---

## 🔒 Seguridad

### Consideraciones importantes:

1. **Las cookies son credenciales**: Protegerlas como passwords
2. **Transmisión segura**: Usar SSH para copiar
3. **Permisos de archivo**: 
   ```bash
   chmod 600 .env
   chmod 600 .env.cookies
   ```
4. **Rotación**: Cookies expiran - sincronizar regularmente
5. **No commitear**: Agregar a .gitignore

```bash
# .gitignore
.env
.env.cookies
.env.backup
cookies.env
```

---

## 🆘 Troubleshooting

### "Error: No se encontraron cookies"
- Asegúrate de tener sesión activa en Firefox/Chrome
- Verifica que el dominio sea exactamente "vmanage.cjf.gob.mx"

### "Cookies expiradas en el servidor"
- Vuelve a ejecutar sincronizar_cookies.sh
- Considera automatizar con cron

### "Permission denied al copiar cookies"
- Verifica permisos SSH
- Verifica permisos del directorio remoto

---

## 📝 Resumen

**PROBLEMA**: Servidor remoto no tiene navegador con cookies

**SOLUCIÓN RECOMENDADA**:
1. Extraer cookies del navegador local
2. Copiar al servidor vía SSH
3. Servidor usa cookies del .env
4. Automatizar sincronización cada 4 horas

**ARCHIVOS NECESARIOS**:
- `extraer_cookies.py` (nuevo)
- `sincronizar_cookies.sh` (nuevo)
- `browser_cookies.py` (modificar)

**RESULTADO**: Servidor MCP funciona en Linux remoto con cookies del navegador local
