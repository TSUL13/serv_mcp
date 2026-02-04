#!/bin/bash
################################################################################
# Script para actualizar cookies automáticamente cuando expiran
# Uso: ./refrescar_cookies.sh
################################################################################

cd "$(dirname "$0")"

echo "🔄 Refrescando cookies de vManage..."
echo ""

# Activar entorno virtual
source venv/bin/activate

# Ejecutar actualizador
python actualizar_cookies_env.py

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡Cookies actualizadas exitosamente!"
    echo ""
    echo "🔄 ¿Reiniciar Claude Desktop? (s/n)"
    read -r respuesta
    
    if [[ "$respuesta" =~ ^[Ss]$ ]]; then
        echo "⏹️  Cerrando Claude Desktop..."
        pkill -9 -f claude-desktop 2>/dev/null
        sleep 2
        echo "✅ Claude Desktop cerrado"
        echo "   Ábrelo manualmente para que use las nuevas cookies"
    else
        echo "💡 Recuerda reiniciar Claude Desktop manualmente:"
        echo "   $ pkill -9 -f claude-desktop"
    fi
else
    echo ""
    echo "❌ Error al actualizar cookies"
    echo "   Verifica que tengas sesión activa en vManage"
fi

echo ""
