#!/usr/bin/env python3
"""
Ejemplo de cómo usar la API REST con Gemini
Requiere: pip install google-generativeai
"""

import google.generativeai as genai
import requests
import json
import os

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Configura tu API Key de Google
# Obtén una en: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyDaCN3BkbmIZ5ogbuzm9jtk91WDaxllNnU"

# URL de tu API REST (debe estar corriendo)
API_BASE_URL = "http://localhost:8000"

# ============================================================================
# DEFINIR FUNCIONES PARA GEMINI
# ============================================================================

# ============================================================================
# TODAS LAS 15 FUNCIONES DISPONIBLES - Acceso Completo a MCP via API REST
# ============================================================================

functions = [
    # ========== FUNCIONES BÁSICAS (Original MCP) ==========
    {
        "name": "listar_dispositivos",
        "description": "Lista todos los dispositivos SD-WAN en la red con su estado",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "salud_dispositivo",
        "description": "Obtiene el estado de salud detallado de un dispositivo específico",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "System IP del dispositivo (ej: 10.1.1.1)"
                }
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "sesiones_bfd_dispositivo",
        "description": "Obtiene todas las sesiones BFD de un dispositivo específico",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "System IP del dispositivo"
                }
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "obtener_alarmas_criticas",
        "description": "Obtiene las alarmas críticas activas en la red SD-WAN",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    
    # ========== FUNCIONES FASE 1 (Monitoreo Avanzado) ==========
    {
        "name": "estadisticas_interfaces",
        "description": "Obtiene estadísticas detalladas de interfaces de un dispositivo",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "System IP del dispositivo"
                }
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "uso_cpu_memoria",
        "description": "Obtiene uso de CPU y memoria de un dispositivo",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "System IP del dispositivo"
                }
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "tuneles_omp",
        "description": "Obtiene información de túneles OMP de un dispositivo",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "System IP del dispositivo"
                }
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "conexiones_control",
        "description": "Obtiene conexiones de control activas en la red",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "obtener_resumen_red",
        "description": "Obtiene un resumen completo del estado de la red (dispositivos, alarmas, etc)",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    
    # ========== FUNCIONES FASE 2 (Análisis y Búsqueda) ==========
    {
        "name": "aplicaciones_top",
        "description": "Obtiene las aplicaciones con mayor tráfico en la red",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "buscar_dispositivo",
        "description": "Busca dispositivos por campo y valor (hostname, site-id, etc)",
        "parameters": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "Campo de búsqueda: host-name, site-id, device-type, etc"
                },
                "value": {
                    "type": "string",
                    "description": "Valor a buscar"
                }
            },
            "required": ["field", "value"]
        }
    },
    {
        "name": "dispositivos_por_sitio",
        "description": "Lista dispositivos de un sitio específico",
        "parameters": {
            "type": "object",
            "properties": {
                "site_id": {
                    "type": "string",
                    "description": "ID del sitio"
                }
            },
            "required": ["site_id"]
        }
    },
    {
        "name": "eventos_seguridad",
        "description": "Obtiene eventos de seguridad de la red",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "diagnostico_completo",
        "description": "Ejecuta diagnóstico completo de un dispositivo (salud, BFD, interfaces, OMP)",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "System IP del dispositivo"
                }
            },
            "required": ["device_id"]
        }
    },
    
    # ========== FUNCIÓN ESPECIAL (BFD Total) ==========
    {
        "name": "obtener_total_sesiones_bfd",
        "description": "Cuenta el total de sesiones BFD en toda la red (muestreo configurable)",
        "parameters": {
            "type": "object",
            "properties": {
                "sample_size": {
                    "type": "integer",
                    "description": "Número de dispositivos a muestrear (default: 10, usar 332 para todos)"
                }
            }
        }
    }
]

# ============================================================================
# EJECUTAR FUNCIONES (llamar a la API REST)
# ============================================================================

def ejecutar_funcion(nombre_funcion, parametros=None):
    """
    Ejecuta una función llamando a la API REST
    Mapea las 15 funciones MCP a los endpoints HTTP
    """
    try:
        # ========== FUNCIONES BÁSICAS ==========
        if nombre_funcion == "listar_dispositivos":
            response = requests.get(f"{API_BASE_URL}/devices")
            return response.json()
        
        elif nombre_funcion == "salud_dispositivo":
            device_id = parametros.get("device_id")
            response = requests.get(f"{API_BASE_URL}/devices/{device_id}/health")
            return response.json()
        
        elif nombre_funcion == "sesiones_bfd_dispositivo":
            device_id = parametros.get("device_id")
            response = requests.get(f"{API_BASE_URL}/devices/{device_id}/bfd")
            return response.json()
        
        elif nombre_funcion == "obtener_alarmas_criticas":
            response = requests.get(f"{API_BASE_URL}/alarms/critical")
            return response.json()
        
        # ========== FUNCIONES FASE 1 ==========
        elif nombre_funcion == "estadisticas_interfaces":
            device_id = parametros.get("device_id")
            response = requests.get(f"{API_BASE_URL}/devices/{device_id}/interfaces")
            return response.json()
        
        elif nombre_funcion == "uso_cpu_memoria":
            device_id = parametros.get("device_id")
            response = requests.get(f"{API_BASE_URL}/devices/{device_id}/cpu-memory")
            return response.json()
        
        elif nombre_funcion == "tuneles_omp":
            device_id = parametros.get("device_id")
            response = requests.get(f"{API_BASE_URL}/devices/{device_id}/omp-tunnels")
            return response.json()
        
        elif nombre_funcion == "conexiones_control":
            response = requests.get(f"{API_BASE_URL}/control-connections")
            return response.json()
        
        elif nombre_funcion == "obtener_resumen_red":
            response = requests.get(f"{API_BASE_URL}/network-summary")
            return response.json()
        
        # ========== FUNCIONES FASE 2 ==========
        elif nombre_funcion == "aplicaciones_top":
            response = requests.get(f"{API_BASE_URL}/applications/top")
            return response.json()
        
        elif nombre_funcion == "buscar_dispositivo":
            field = parametros.get("field", "host-name")
            value = parametros.get("value", "")
            response = requests.get(f"{API_BASE_URL}/search?field={field}&value={value}")
            return response.json()
        
        elif nombre_funcion == "dispositivos_por_sitio":
            site_id = parametros.get("site_id")
            response = requests.get(f"{API_BASE_URL}/sites/{site_id}/devices")
            return response.json()
        
        elif nombre_funcion == "eventos_seguridad":
            response = requests.get(f"{API_BASE_URL}/security/events")
            return response.json()
        
        elif nombre_funcion == "diagnostico_completo":
            device_id = parametros.get("device_id")
            response = requests.get(f"{API_BASE_URL}/devices/{device_id}/diagnostic")
            return response.json()
        
        # ========== FUNCIÓN ESPECIAL ==========
        elif nombre_funcion == "obtener_total_sesiones_bfd":
            sample_size = parametros.get("sample_size", 10) if parametros else 10
            response = requests.get(f"{API_BASE_URL}/bfd/total?sample_size={sample_size}")
            return response.json()
        
        else:
            return {"error": f"Función {nombre_funcion} no implementada"}
    
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# CONFIGURAR GEMINI
# ============================================================================

def inicializar_gemini():
    """Configura Gemini con las funciones disponibles"""
    
    # Verificar API key
    if GEMINI_API_KEY == "AIzaSyDaCN3BkbmIZ5ogbuzm9jtk91WDaxllNnU":
        print("❌ Error: Debes configurar tu GEMINI_API_KEY")
        print("   Obtén una en: https://aistudio.google.com/app/apikey")
        print("   Edita este archivo y reemplaza AIzaSyDaCN3BkbmIZ5ogbuzm9jtk91WDaxllNnU")
        return None
    
    # Verificar que la API esté corriendo
    try:
        response = requests.get(API_BASE_URL, timeout=2)
        print(f"✅ API REST corriendo en {API_BASE_URL}")
    except:
        print(f"❌ Error: La API REST no está corriendo")
        print(f"   Inicia el servidor: python api_rest.py")
        return None
    
    # Configurar Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Crear modelo con funciones
    model = genai.GenerativeModel(
        model_name='gemini-1.5-pro',
        tools=functions
    )
    
    print("✅ Gemini configurado con funciones SD-WAN")
    return model

# ============================================================================
# CHAT CON GEMINI
# ============================================================================

def chat_con_gemini():
    """Inicia un chat interactivo con Gemini"""
    
    print("\n" + "="*70)
    print("  🤖 Chat con Gemini - Consultas a Red SD-WAN")
    print("="*70)
    
    model = inicializar_gemini()
    if not model:
        return
    
    chat = model.start_chat()
    
    print("\n💡 Ejemplos de preguntas:")
    print("   - ¿Cuántos dispositivos hay en la red?")
    print("   - ¿Hay alarmas críticas?")
    print("   - Dame un resumen del estado de la red")
    print("   - ¿Cuántas sesiones BFD hay en total?")
    print("   - Muéstrame las interfaces del router 10.1.1.1")
    print("   - ¿Cuál es el uso de CPU del dispositivo 10.1.1.1?")
    print("   - Busca dispositivos que contengan 'CDMX' en el nombre")
    print("   - Dame un diagnóstico completo del 10.1.1.1")
    print("   - ¿Qué aplicaciones generan más tráfico?")
    print("\n   Escribe 'salir' para terminar\n")
    
    while True:
        # Obtener pregunta del usuario
        pregunta = input("👤 Tú: ").strip()
        
        if pregunta.lower() in ['salir', 'exit', 'quit']:
            print("👋 ¡Hasta luego!")
            break
        
        if not pregunta:
            continue
        
        try:
            # Enviar pregunta a Gemini
            response = chat.send_message(pregunta)
            
            # Verificar si Gemini quiere llamar a una función
            if response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
                
                print(f"\n🔧 Gemini llama a: {function_call.name}")
                
                # Extraer parámetros
                parametros = {}
                if hasattr(function_call, 'args'):
                    parametros = dict(function_call.args)
                
                # Ejecutar función (llamar a API REST)
                resultado = ejecutar_funcion(function_call.name, parametros)
                
                print(f"📊 Resultado obtenido: {len(str(resultado))} caracteres")
                
                # Enviar resultado de vuelta a Gemini
                response = chat.send_message(
                    genai.protos.Content(
                        parts=[genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=function_call.name,
                                response={"result": resultado}
                            )
                        )]
                    )
                )
            
            # Mostrar respuesta de Gemini
            print(f"\n🤖 Gemini: {response.text}\n")
        
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

# ============================================================================
# EJEMPLO SIMPLE (sin chat)
# ============================================================================

def ejemplo_simple():
    """Ejemplo simple de una consulta a Gemini"""
    
    print("\n" + "="*70)
    print("  📝 Ejemplo Simple")
    print("="*70)
    
    model = inicializar_gemini()
    if not model:
        return
    
    # Hacer una pregunta
    pregunta = "¿Cuántos dispositivos hay en la red y cuántos están operativos?"
    print(f"\n👤 Pregunta: {pregunta}")
    
    chat = model.start_chat()
    response = chat.send_message(pregunta)
    
    # Si Gemini llama a una función
    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        print(f"🔧 Gemini llama a: {function_call.name}")
        
        # Ejecutar
        resultado = ejecutar_funcion(function_call.name)
        print(f"📊 Datos obtenidos")
        
        # Enviar resultado
        response = chat.send_message(
            genai.protos.Content(
                parts=[genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=function_call.name,
                        response={"result": resultado}
                    )
                )]
            )
        )
    
    print(f"\n🤖 Respuesta: {response.text}\n")

# ============================================================================
# MENÚ PRINCIPAL
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  🌐 Ejemplo de Integración: Gemini + API REST vManage")
    print("="*70)
    print("\nOpciones:")
    print("  1. Ejemplo simple (una consulta)")
    print("  2. Chat interactivo")
    print("  3. Salir")
    
    opcion = input("\nElige una opción (1-3): ").strip()
    
    if opcion == "1":
        ejemplo_simple()
    elif opcion == "2":
        chat_con_gemini()
    else:
        print("👋 ¡Hasta luego!")

if __name__ == "__main__":
    main()
