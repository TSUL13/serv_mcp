#!/bin/bash
# Script para iniciar el servidor MCP de Cisco SD-WAN

echo "🚀 Iniciando servidor MCP para Cisco SD-WAN..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "server.py" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio serv_mcp"
    exit 1
fi

# Activar entorno virtual
echo "1️⃣  Activando entorno virtual..."
source venv/bin/activate

# Verificar archivo .env
echo ""
echo "2️⃣  Verificando configuración..."
if [ ! -f ".env" ]; then
    echo "❌ Error: Archivo .env no encontrado"
    exit 1
fi

if grep -q "ANALYTICS_SESSION_COOKIE" .env; then
    echo "✅ Cookies de Analytics Cloud configuradas"
else
    echo "⚠️  Cookies de Analytics Cloud no configuradas en .env"
fi

echo ""
echo "=============================================="
echo "✅ SERVIDOR MCP LISTO"
echo "=============================================="
echo ""
echo "📦 Herramientas disponibles: 19+"
echo "   • Herramientas de vManage/Analytics (API REST)"
echo ""
echo "🌐 Para usar con Claude Desktop:"
echo "   1. Cierra Claude Desktop si está abierto"
echo "   2. Abre Claude Desktop nuevamente"
echo "   3. El servidor se iniciará automáticamente"
echo "   4. Verifica que aparezca el ícono 🔌 en Claude"
echo ""
echo "💬 Ejemplos de consultas:"
echo "   • 'Dame un top 10 de aplicaciones más usadas'"
echo "   • 'Muéstrame la salud de la red'"
echo "   • 'Lista los dispositivos activos'"
echo ""
echo "=============================================="
echo ""

# El servidor se ejecuta automáticamente cuando Claude Desktop lo invoca
# No es necesario dejarlo corriendo aquí
