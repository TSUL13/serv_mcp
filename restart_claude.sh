#!/bin/bash
# Verificar y reiniciar Claude Desktop para detectar nuevas herramientas

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   🔄 REINICIAR CLAUDE DESKTOP PARA DETECTAR HERRAMIENTAS     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar configuración
echo "1️⃣  Verificando configuración MCP..."
if [ -f ~/.config/Claude/claude_desktop_config.json ]; then
    echo "   ✅ Archivo de configuración encontrado"
    cat ~/.config/Claude/claude_desktop_config.json
else
    echo "   ❌ No se encontró configuración de Claude Desktop"
    exit 1
fi

echo ""
echo "2️⃣  Verificando herramientas en server.py..."
TOOL_COUNT=$(grep -c "@mcp.tool()" /home/tsul/Documentos/serv_mcp/server.py)
echo "   ✅ Total de herramientas: $TOOL_COUNT"

echo ""
echo "3️⃣  Cerrando Claude Desktop..."
# Cerrar todos los procesos de Claude
pkill -f "claude" 2>/dev/null
sleep 2

if pgrep -f "claude" > /dev/null; then
    echo "   ⚠️  Claude Desktop aún está ejecutándose"
    echo "   Por favor, ciérralo manualmente"
else
    echo "   ✅ Claude Desktop cerrado"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📱 AHORA ABRE CLAUDE DESKTOP Y VERIFICA:"
echo ""
echo "   1. Busca el ícono 🔌 en la esquina inferior derecha"
echo ""
echo "   2. Haz clic en 🔌 para ver las herramientas conectadas"
echo ""
echo "   3. Deberías ver:"
echo "      • Servidor: 'cisco-sdwan'"
echo "      • Herramientas: $TOOL_COUNT"
echo ""
echo "   4. Prueba con estas consultas:"
echo "      • 'Lista los dispositivos activos'"
echo "      • 'Dame las aplicaciones más usadas'"
echo "      • 'Muéstrame las alarmas críticas'"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "💡 Si no aparecen las herramientas:"
echo "   • Verifica que el archivo .env tenga las cookies"
echo "   • Revisa los logs en: ~/.config/Claude/logs/"
echo "   • Ejecuta: ./start_mcp.sh para verificar dependencias"
echo ""
