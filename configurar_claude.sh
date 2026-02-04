#!/bin/bash

# Script para configurar el servidor MCP en Claude Desktop
# Ejecutar con: bash configurar_claude.sh

echo "================================================"
echo "  Configurando servidor MCP en Claude Desktop"
echo "================================================"
echo ""

# Obtener la ruta absoluta del directorio actual
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
SERVER_PATH="$SCRIPT_DIR/server.py"

# Directorio de configuración de Claude Desktop
CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

# Crear directorio si no existe
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo "📁 Creando directorio de configuración..."
    mkdir -p "$CLAUDE_CONFIG_DIR"
    echo "   ✓ Directorio creado: $CLAUDE_CONFIG_DIR"
else
    echo "📁 Directorio de configuración existe"
fi

echo ""
echo "📝 Configurando servidor MCP..."

# Crear o actualizar el archivo de configuración
cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "cisco-sdwan": {
      "command": "$PYTHON_PATH",
      "args": ["$SERVER_PATH"]
    }
  }
}
EOF

if [ $? -eq 0 ]; then
    echo "   ✓ Configuración creada exitosamente"
    echo ""
    echo "================================================"
    echo "  ✅ CONFIGURACIÓN COMPLETADA"
    echo "================================================"
    echo ""
    echo "📄 Archivo de configuración:"
    echo "   $CLAUDE_CONFIG_FILE"
    echo ""
    echo "🔧 Configuración aplicada:"
    echo "   Servidor: cisco-sdwan"
    echo "   Python:   $PYTHON_PATH"
    echo "   Script:   $SERVER_PATH"
    echo ""
    echo "📋 Próximos pasos:"
    echo "   1. Reinicia Claude Desktop"
    echo "   2. Busca el ícono 🔧 en la interfaz"
    echo "   3. Deberías ver 4 herramientas disponibles:"
    echo "      • listar_dispositivos"
    echo "      • ver_salud_equipo"
    echo "      • ver_sesiones_bfd"
    echo "      • listar_alarmas_criticas"
    echo ""
    echo "================================================"
    echo ""
    
    # Mostrar el contenido del archivo
    echo "📄 Contenido del archivo de configuración:"
    echo ""
    cat "$CLAUDE_CONFIG_FILE"
    echo ""
    
else
    echo "   ❌ Error al crear la configuración"
    exit 1
fi
