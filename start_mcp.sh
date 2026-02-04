#!/bin/bash
# Script de inicio rápido del servidor MCP

echo "======================================================================"
echo "🚀 INICIANDO SERVIDOR MCP SD-WAN"
echo "======================================================================"
echo ""

cd /home/tsul/Documentos/serv_mcp

# 1. Verificar entorno virtual
if [ ! -d "venv" ]; then
    echo "❌ Entorno virtual no encontrado"
    echo "   Ejecuta: python3 -m venv venv"
    exit 1
fi

echo "1️⃣  Activando entorno virtual..."
source venv/bin/activate
echo "   ✅ Entorno activado"

# 2. Verificar .env
if [ ! -f ".env" ]; then
    echo "❌ Archivo .env no encontrado"
    echo "   Copia .env.example y configura credenciales"
    exit 1
fi

echo ""
echo "2️⃣  Verificando credenciales vManage..."
VMANAGE_HOST=$(grep VMANAGE_HOST .env | cut -d '=' -f2)
if [ -z "$VMANAGE_HOST" ]; then
    echo "   ⚠️  VMANAGE_HOST no configurado en .env"
else
    echo "   ✅ vManage: $VMANAGE_HOST"
fi

# 3. Verificar cookies de Analytics
echo ""
echo "3️⃣  Verificando cookies de Analytics Cloud..."
if [ ! -f ".analytics_cookies.json" ]; then
    echo "   ⚠️  Cookies no encontradas"
    echo "   Ejecutando extracción de cookies..."
    ./refrescar_cookies_analytics.sh
    
    if [ $? -ne 0 ]; then
        echo "   ❌ Error al extraer cookies"
        echo ""
        echo "   Solución:"
        echo "   1. Abre Chrome: https://us02.analytics.sdwan.cisco.com"
        echo "   2. Inicia sesión"
        echo "   3. Ejecuta: ./refrescar_cookies_analytics.sh"
        exit 1
    fi
else
    # Verificar antigüedad de cookies
    COOKIE_AGE=$(find .analytics_cookies.json -mmin +240 2>/dev/null)
    if [ -n "$COOKIE_AGE" ]; then
        echo "   ⚠️  Cookies tienen más de 4 horas"
        echo "   Refrescando cookies..."
        ./refrescar_cookies_analytics.sh
    else
        echo "   ✅ Cookies válidas"
    fi
fi

# 4. Test rápido
echo ""
echo "4️⃣  Ejecutando test de conectividad..."
python -c "
import sys
sys.path.insert(0, '/home/tsul/Documentos/serv_mcp')
try:
    from test_funcion_actualizada import get_analytics_session
    analytics = get_analytics_session()
    print('   ✅ Analytics Cloud: Conectado')
except Exception as e:
    print(f'   ❌ Analytics Cloud: Error - {str(e)[:50]}')
    sys.exit(1)
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo ""
    echo "   ⚠️  Problema de conectividad con Analytics Cloud"
    echo "   Verifica:"
    echo "   - Estás logueado en Analytics Cloud (Chrome)"
    echo "   - Las cookies están actualizadas"
    echo ""
    read -p "   ¿Continuar de todas formas? (s/n): " continuar
    if [ "$continuar" != "s" ]; then
        exit 1
    fi
fi

# 5. Verificar configuración de Claude Desktop
echo ""
echo "5️⃣  Verificando configuración de Claude Desktop..."
CLAUDE_CONFIG=~/.config/Claude/claude_desktop_config.json
if [ -f "$CLAUDE_CONFIG" ]; then
    if grep -q "sdwan-analytics" "$CLAUDE_CONFIG"; then
        echo "   ✅ Claude Desktop configurado"
    else
        echo "   ⚠️  Servidor MCP no encontrado en configuración"
        echo "   Agrega esto a $CLAUDE_CONFIG:"
        echo ""
        echo '   "sdwan-analytics": {'
        echo '     "command": "/home/tsul/Documentos/serv_mcp/venv/bin/python",'
        echo '     "args": ["/home/tsul/Documentos/serv_mcp/server.py"]'
        echo '   }'
    fi
else
    echo "   ⚠️  Archivo de configuración no encontrado"
    echo "   Ubicación: $CLAUDE_CONFIG"
fi

# 6. Reiniciar Claude Desktop
echo ""
echo "6️⃣  Reiniciando Claude Desktop..."
if pgrep -f claude-desktop > /dev/null; then
    echo "   🔄 Cerrando Claude Desktop..."
    pkill -9 -f claude-desktop
    sleep 2
    echo "   ✅ Claude Desktop cerrado"
else
    echo "   ℹ️  Claude Desktop no estaba corriendo"
fi

echo ""
echo "======================================================================"
echo "✅ PREPARACIÓN COMPLETA"
echo "======================================================================"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Abre Claude Desktop desde tu menú de aplicaciones"
echo "2. Espera 5-10 segundos para que cargue el servidor MCP"
echo "3. Prueba con: 'Dame un top 10 de las aplicaciones más usadas'"
echo ""
echo "🔧 Si hay problemas:"
echo "   - Ver logs: tail -f ~/.config/Claude/logs/mcp*.log"
echo "   - Test manual: python test_funcion_actualizada.py"
echo "   - Refrescar cookies: ./refrescar_cookies_analytics.sh"
echo ""
echo "📖 Documentación completa: cat GUIA_ARRANQUE_COMPLETA.md"
echo ""
echo "======================================================================"
echo ""
