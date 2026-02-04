# 🌐 Cómo Conectar a GPT o Gemini

## ❌ Por Qué MCP No Funciona con GPT/Gemini

**MCP (Model Context Protocol)** es un protocolo propietario de Anthropic:
- ✅ **Solo funciona con**: Claude Desktop
- ❌ **NO funciona con**: GPT, Gemini, otros LLMs

GPT y Gemini usan sus propios sistemas:
- **GPT**: Function Calling / Actions (OpenAI)
- **Gemini**: Function Declarations (Google)

## ✅ Soluciones Disponibles

### **Opción 1: API REST (Recomendada) 🚀**

Crear una API web que cualquier IA puede llamar.

#### Ventajas:
- ✅ Compatible con GPT-4, Gemini, Claude (sin MCP), cualquier IA
- ✅ Accesible desde navegador, Postman, curl
- ✅ Documentación automática con Swagger
- ✅ No depende de protocolos propietarios

#### Implementación:

```bash
# 1. Instalar dependencias
pip install fastapi uvicorn

# 2. Ejecutar servidor
python api_rest.py

# 3. Acceder a:
# - API: http://localhost:8000
# - Docs interactiva: http://localhost:8000/docs
# - Redoc: http://localhost:8000/redoc
```

#### Uso con GPT-4 (ChatGPT Plus):

1. **Crear Custom GPT** (GPTs):
   - Ve a: https://chat.openai.com/gpts/editor
   - Nombre: "SD-WAN Assistant"
   - Instructions: "Eres un asistente para gestión de redes Cisco SD-WAN"
   - **Actions**: Importa el esquema OpenAPI desde http://localhost:8000/openapi.json

2. **Definir acciones**:
```yaml
servers:
  - url: http://tu-servidor:8000

paths:
  /devices:
    get:
      operationId: listDevices
      description: Lista todos los dispositivos SD-WAN
```

3. **Usar**:
```
Usuario: "¿Cuántos dispositivos hay en la red?"
GPT: [Llama a GET /devices] "Hay 332 dispositivos"
```

#### Uso con Gemini (Google AI Studio):

1. **Function Calling** en Gemini API:
```python
import google.generativeai as genai

# Definir función
list_devices_func = {
    "name": "list_devices",
    "description": "Lista dispositivos SD-WAN",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

# Configurar modelo
model = genai.GenerativeModel(
    model_name='gemini-pro',
    tools=[list_devices_func]
)

# Usar
response = model.generate_content("¿Cuántos dispositivos hay?")
```

---

### **Opción 2: Wrapper HTTP para MCP**

Convertir MCP a HTTP (más complejo):

```python
# Servidor que traduce HTTP → MCP → vManage
# Cliente HTTP → FastAPI → MCP Server → vManage
```

**Desventaja**: Capa extra de complejidad innecesaria.

---

### **Opción 3: Mantener Claude + Crear API Separada**

- **Claude Desktop**: Usa MCP directamente (ya funciona)
- **GPT/Gemini**: Usa API REST (api_rest.py)

**Ventaja**: Mejor de ambos mundos.

---

## 📊 Comparación de Opciones

| Característica | MCP (Claude) | API REST | Wrapper |
|---|---|---|---|
| Compatible con Claude | ✅ | ⚠️ Sí (sin MCP) | ✅ |
| Compatible con GPT | ❌ | ✅ | ✅ |
| Compatible con Gemini | ❌ | ✅ | ✅ |
| Complejidad | Baja | Baja | Alta |
| Documentación auto | ❌ | ✅ Swagger | ⚠️ |
| Acceso desde navegador | ❌ | ✅ | ⚠️ |
| **Recomendación** | Para Claude Desktop | **Para todo lo demás** | No recomendado |

---

## 🚀 Inicio Rápido: API REST

### 1. Instalar dependencias
```bash
pip install fastapi uvicorn
```

### 2. Ejecutar servidor
```bash
python api_rest.py
```

### 3. Probar endpoints
```bash
# Listar dispositivos
curl http://localhost:8000/devices

# Salud de dispositivo
curl http://localhost:8000/devices/10.1.1.1/health

# Total BFD
curl http://localhost:8000/bfd/total

# Alarmas críticas
curl http://localhost:8000/alarms/critical
```

### 4. Ver documentación interactiva
Abre en navegador: http://localhost:8000/docs

---

## 🔧 Configuración para GPT-4

### Custom GPT (ChatGPT Plus requerido)

1. **Crear GPT**:
   - Ve a https://chat.openai.com/gpts/editor
   - Dale un nombre: "SD-WAN Network Assistant"

2. **Instructions**:
```
Eres un asistente experto en redes Cisco SD-WAN.
Tienes acceso a una API para consultar dispositivos, sesiones BFD,
alarmas, y más. Responde preguntas sobre la red usando las herramientas
disponibles.
```

3. **Actions** (Importante):
   - Click en "Create new action"
   - Importa desde: `http://localhost:8000/openapi.json`
   - O copia manualmente el esquema OpenAPI

4. **Schema OpenAPI** (si copias manualmente):
```yaml
openapi: 3.0.0
info:
  title: vManage API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /devices:
    get:
      operationId: listDevices
      summary: Lista todos los dispositivos
      responses:
        '200':
          description: Lista de dispositivos
  /devices/{device_id}/health:
    get:
      operationId: getDeviceHealth
      summary: Salud de un dispositivo
      parameters:
        - name: device_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Estado del dispositivo
  # ... más endpoints
```

5. **Guardar y probar**:
```
Tú: "¿Cuántos dispositivos están caídos?"
GPT: [Llama a /devices] "Actualmente hay 5 dispositivos caídos de 332 totales"
```

---

## 🔧 Configuración para Gemini

### Function Calling con Gemini API

```python
import google.generativeai as genai
import requests

genai.configure(api_key="TU_API_KEY")

# Definir funciones
functions = [
    {
        "name": "list_devices",
        "description": "Lista todos los dispositivos SD-WAN",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_device_health",
        "description": "Obtiene salud de un dispositivo",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "ID del dispositivo"
                }
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "get_critical_alarms",
        "description": "Obtiene alarmas críticas",
        "parameters": {"type": "object", "properties": {}}
    }
]

# Crear modelo con funciones
model = genai.GenerativeModel(
    model_name='gemini-1.5-pro',
    tools=functions
)

# Chat con función
chat = model.start_chat()
response = chat.send_message("¿Cuántos dispositivos hay en la red?")

# Si Gemini llama a una función
if response.candidates[0].content.parts[0].function_call:
    function_call = response.candidates[0].content.parts[0].function_call
    
    # Ejecutar función llamando a tu API
    if function_call.name == "list_devices":
        result = requests.get("http://localhost:8000/devices").json()
        
        # Enviar resultado de vuelta a Gemini
        response = chat.send_message(
            genai.protos.Content(
                parts=[genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name="list_devices",
                        response={"result": result}
                    )
                )]
            )
        )
        
        print(response.text)
```

---

## 🌍 Exponer API a Internet (Opcional)

### Opción A: ngrok (más fácil)
```bash
# Instalar ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Autenticar
ngrok config add-authtoken TU_TOKEN

# Exponer puerto
ngrok http 8000

# Recibirás URL: https://abc123.ngrok.io
# Usa esta URL en GPT/Gemini
```

### Opción B: Cloudflare Tunnel
```bash
# Instalar cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Crear túnel
cloudflare tunnel --url http://localhost:8000
```

### Opción C: Servidor VPS
- Deploy en AWS, Google Cloud, DigitalOcean
- Instalar API en servidor con IP pública
- Configurar firewall, SSL, dominio

---

## 🔐 Seguridad (IMPORTANTE)

### ⚠️ Problemas de Seguridad Actuales

El código actual **NO es seguro para producción**:
- ❌ Sin autenticación en API
- ❌ Sin rate limiting
- ❌ Cookies expuestas
- ❌ CORS abierto a todos

### ✅ Mejorar Seguridad

```python
from fastapi import Security, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Token simple
API_TOKEN = "tu-token-secreto-aqui"

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    return credentials.credentials

# Aplicar a endpoints
@app.get("/devices", dependencies=[Depends(verify_token)])
def list_devices():
    # ...
```

**Uso**:
```bash
curl -H "Authorization: Bearer tu-token-secreto-aqui" \
  http://localhost:8000/devices
```

**En GPT Custom Actions**:
- Authentication: Bearer Token
- Token: `tu-token-secreto-aqui`

---

## 📝 Ejemplo Completo: GPT Custom Action

### 1. Schema OpenAPI para GPT
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "vManage SD-WAN API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "http://localhost:8000"
    }
  ],
  "paths": {
    "/devices": {
      "get": {
        "operationId": "listDevices",
        "summary": "Lista dispositivos SD-WAN",
        "responses": {
          "200": {
            "description": "Lista de dispositivos"
          }
        }
      }
    },
    "/alarms/critical": {
      "get": {
        "operationId": "getCriticalAlarms",
        "summary": "Obtiene alarmas críticas",
        "responses": {
          "200": {
            "description": "Alarmas críticas"
          }
        }
      }
    },
    "/bfd/total": {
      "get": {
        "operationId": "getTotalBFD",
        "summary": "Total de sesiones BFD",
        "parameters": [
          {
            "name": "sample_size",
            "in": "query",
            "schema": {
              "type": "integer",
              "default": 10
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Resumen BFD"
          }
        }
      }
    }
  }
}
```

### 2. Prompt para GPT
```
Eres un experto en redes Cisco SD-WAN con acceso a una API de gestión.

Capacidades:
- Listar dispositivos de red
- Verificar salud de dispositivos
- Consultar sesiones BFD
- Revisar alarmas críticas
- Obtener estadísticas de interfaces
- Y más...

Cuando el usuario pregunte sobre la red, usa las herramientas disponibles
para obtener información en tiempo real. Siempre proporciona datos
específicos y numéricos cuando sea posible.

Formato de respuestas:
- Sé conciso pero informativo
- Usa emojis para estados (✅ OK, ⚠️ Warning, ❌ Critical)
- Proporciona contexto sobre la salud de la red
```

### 3. Ejemplo de Conversación
```
Usuario: "¿Cómo está la red?"

GPT: [Llama a /devices y /alarms/critical]
"Estado de la red SD-WAN:
✅ Dispositivos: 327/332 operativos (98.5%)
⚠️ Alarmas críticas: 3
❌ Dispositivos caídos: 5

Los 5 dispositivos caídos son:
- SDWAN-SITE-45 (Offline hace 2h)
- SDWAN-SITE-87 (Offline hace 30min)
- ...

¿Quieres más detalles sobre algún dispositivo?"
```

---

## 🎯 Resumen de Recomendaciones

| Necesidad | Solución | Herramienta |
|---|---|---|
| Usar con Claude Desktop | MCP nativo | `server.py` (actual) |
| Usar con GPT | API REST + Custom GPT | `api_rest.py` |
| Usar con Gemini | API REST + Function Calling | `api_rest.py` |
| Uso desde terminal | CLI | `cli.py` (ya existe) |
| Uso desde navegador | API REST + Swagger | `api_rest.py` + /docs |
| Automatización | API REST + scripts | `api_rest.py` + Python/bash |

---

## 🚀 Próximos Pasos

### Rápido (10 minutos):
```bash
# 1. Instalar dependencias
pip install fastapi uvicorn

# 2. Ejecutar API
python api_rest.py

# 3. Probar
curl http://localhost:8000/devices

# 4. Ver docs
firefox http://localhost:8000/docs
```

### Completo (1 hora):
1. ✅ Instalar y probar API
2. ✅ Crear Custom GPT en ChatGPT
3. ✅ Configurar actions con tu API
4. ✅ Agregar autenticación (Bearer Token)
5. ✅ Exponer con ngrok (opcional)
6. ✅ Probar desde GPT

---

## 📚 Recursos

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [OpenAI Actions](https://platform.openai.com/docs/actions)
- [Gemini Function Calling](https://ai.google.dev/docs/function_calling)
- [ngrok](https://ngrok.com)

---

**¿Necesitas ayuda?** Abre [GUIA_CLAUDE_DESKTOP.md](GUIA_CLAUDE_DESKTOP.md) para comparar con la implementación MCP.
