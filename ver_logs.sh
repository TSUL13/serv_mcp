#!/bin/bash
# Script para monitorear logs del servidor MCP en tiempo real

echo "======================================================================"
echo "📊 MONITOR DE LOGS - Servidor MCP Cisco SD-WAN"
echo "======================================================================"
echo ""

LOG_FILE=~/.config/Claude/logs/mcp-server-cisco-sdwan.log

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Archivo de log no encontrado: $LOG_FILE"
    echo ""
    echo "Posibles causas:"
    echo "  - Claude Desktop no está corriendo"
    echo "  - El servidor MCP no se ha iniciado"
    echo "  - El nombre del servidor en claude_desktop_config.json es diferente"
    echo ""
    echo "Archivos de log disponibles:"
    ls -lh ~/.config/Claude/logs/mcp*.log 2>/dev/null || echo "  (ninguno)"
    exit 1
fi

echo "📁 Archivo: $LOG_FILE"
echo "📏 Tamaño: $(du -h "$LOG_FILE" | cut -f1)"
echo "🕐 Última modificación: $(stat -c %y "$LOG_FILE" | cut -d'.' -f1)"
echo ""
echo "Selecciona modo de visualización:"
echo ""
echo "1) 📜 Ver últimas 50 líneas"
echo "2) 🔄 Seguir en tiempo real (tail -f)"
echo "3) 🔍 Buscar texto específico"
echo "4) ⏱️  Ver solo peticiones de cliente (tools/call)"
echo "5) ⚠️  Ver solo errores"
echo "6) 📊 Estadísticas de uso"
echo ""
read -p "Opción (1-6): " opcion

case $opcion in
    1)
        echo ""
        echo "======================================================================"
        echo "📜 ÚLTIMAS 50 LÍNEAS"
        echo "======================================================================"
        tail -50 "$LOG_FILE"
        ;;
    2)
        echo ""
        echo "======================================================================"
        echo "🔄 SIGUIENDO LOG EN TIEMPO REAL (Ctrl+C para salir)"
        echo "======================================================================"
        echo ""
        tail -f "$LOG_FILE" | while read line; do
            # Colorear según tipo de mensaje
            if [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"error"* ]]; then
                echo -e "\033[0;31m$line\033[0m"  # Rojo
            elif [[ "$line" == *"tools/call"* ]]; then
                echo -e "\033[0;32m$line\033[0m"  # Verde
            elif [[ "$line" == *"result"* ]]; then
                echo -e "\033[0;36m$line\033[0m"  # Cyan
            else
                echo "$line"
            fi
        done
        ;;
    3)
        echo ""
        read -p "Texto a buscar: " texto
        echo ""
        echo "======================================================================"
        echo "🔍 RESULTADOS DE BÚSQUEDA: '$texto'"
        echo "======================================================================"
        grep -i --color=always "$texto" "$LOG_FILE" | tail -30
        ;;
    4)
        echo ""
        echo "======================================================================"
        echo "⏱️  PETICIONES DE CLIENTE (tools/call)"
        echo "======================================================================"
        grep "tools/call" "$LOG_FILE" | tail -20 | while read line; do
            # Extraer nombre de la función
            if [[ "$line" =~ \"name\":\"([^\"]+)\" ]]; then
                func="${BASH_REMATCH[1]}"
                timestamp=$(echo "$line" | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
                echo "[$timestamp] 🔧 $func"
            fi
        done
        ;;
    5)
        echo ""
        echo "======================================================================"
        echo "⚠️  ERRORES DETECTADOS"
        echo "======================================================================"
        grep -i "error\|exception\|traceback\|failed" "$LOG_FILE" | tail -30 | while read line; do
            echo -e "\033[0;31m$line\033[0m"
        done
        ;;
    6)
        echo ""
        echo "======================================================================"
        echo "📊 ESTADÍSTICAS DE USO"
        echo "======================================================================"
        echo ""
        echo "📝 Total de líneas: $(wc -l < "$LOG_FILE")"
        echo "📦 Tamaño del archivo: $(du -h "$LOG_FILE" | cut -f1)"
        echo ""
        echo "🔧 Funciones más llamadas (últimas 100 peticiones):"
        grep "tools/call" "$LOG_FILE" | tail -100 | grep -oP '"name":"[^"]+' | \
            cut -d'"' -f4 | sort | uniq -c | sort -rn | head -10 | \
            while read count func; do
                printf "   %3d veces: %s\n" "$count" "$func"
            done
        echo ""
        echo "⚠️  Total de errores: $(grep -ic "error\|exception" "$LOG_FILE")"
        echo "✅ Última petición exitosa:"
        grep "result" "$LOG_FILE" | tail -1 | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}' || echo "   (ninguna)"
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

echo ""
