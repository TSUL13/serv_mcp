#!/bin/bash
################################################################################
# Verificar Estado del Servidor MCP
# Comandos útiles para ver si el servidor está corriendo
################################################################################

echo "========================================================================"
echo "  🔍 Verificación de Servidor MCP"
echo "========================================================================"
echo ""

# ============================================================================
# MÉTODO 1: Buscar proceso por nombre
# ============================================================================
echo "1️⃣  Buscar proceso server.py:"
echo "   Comando: ps aux | grep server.py | grep -v grep"
echo ""
ps aux | grep server.py | grep -v grep
if [ $? -eq 0 ]; then
    echo "   ✅ Servidor MCP está corriendo"
else
    echo "   ❌ Servidor MCP no está corriendo"
fi
echo ""

# ============================================================================
# MÉTODO 2: Buscar por Python con FastMCP
# ============================================================================
echo "2️⃣  Buscar procesos Python de FastMCP:"
echo "   Comando: ps aux | grep python | grep serv_mcp"
echo ""
ps aux | grep python | grep serv_mcp | grep -v grep
echo ""

# ============================================================================
# MÉTODO 3: Ver detalles del proceso
# ============================================================================
echo "3️⃣  Detalles del proceso (PID, memoria, CPU):"
PID=$(ps aux | grep "server.py" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "   PID: $PID"
    echo "   Comando: ps -p $PID -o pid,ppid,%cpu,%mem,etime,cmd"
    echo ""
    ps -p $PID -o pid,ppid,%cpu,%mem,etime,cmd
else
    echo "   ❌ No se encontró proceso"
fi
echo ""

# ============================================================================
# MÉTODO 4: Ver procesos hijos (Claude Desktop)
# ============================================================================
echo "4️⃣  Proceso padre (Claude Desktop):"
if [ -n "$PID" ]; then
    PPID=$(ps -p $PID -o ppid= | tr -d ' ')
    echo "   PPID: $PPID"
    ps -p $PPID -o pid,cmd 2>/dev/null || echo "   (proceso padre ya no existe)"
fi
echo ""

# ============================================================================
# MÉTODO 5: Ver logs recientes
# ============================================================================
echo "5️⃣  Logs del servidor (si existen):"
if [ -f "/tmp/mcp_server.log" ]; then
    echo "   Últimas 10 líneas de /tmp/mcp_server.log:"
    tail -10 /tmp/mcp_server.log
elif [ -n "$PID" ]; then
    echo "   (No hay archivo de log, servidor corre en modo stdio)"
    echo "   Los logs van a Claude Desktop"
fi
echo ""

# ============================================================================
# MÉTODO 6: Verificar puertos abiertos (si aplica)
# ============================================================================
echo "6️⃣  Puertos en uso por el proceso:"
if [ -n "$PID" ]; then
    echo "   Comando: lsof -p $PID -i -n -P 2>/dev/null"
    lsof -p $PID -i -n -P 2>/dev/null || echo "   (MCP usa stdio, no abre puertos)"
fi
echo ""

# ============================================================================
# RESUMEN
# ============================================================================
echo "========================================================================"
echo "  📊 RESUMEN"
echo "========================================================================"
echo ""

if [ -n "$PID" ]; then
    echo "✅ SERVIDOR MCP ACTIVO"
    echo ""
    echo "Detalles:"
    echo "  PID: $PID"
    echo "  Ruta: /home/tsul/Documentos/serv_mcp/server.py"
    echo "  Python: /home/tsul/Documentos/serv_mcp/venv/bin/python"
    echo "  Tiempo corriendo: $(ps -p $PID -o etime= | tr -d ' ')"
    echo "  CPU: $(ps -p $PID -o %cpu= | tr -d ' ')%"
    echo "  Memoria: $(ps -p $PID -o %mem= | tr -d ' ')%"
    echo ""
    echo "Comandos útiles:"
    echo "  Ver proceso: ps -p $PID -f"
    echo "  Detener: kill $PID"
    echo "  Ver en tiempo real: watch -n 1 'ps -p $PID -o pid,%cpu,%mem,etime,cmd'"
else
    echo "❌ SERVIDOR MCP NO ACTIVO"
    echo ""
    echo "Para iniciarlo:"
    echo "  1. Abre Claude Desktop (inicia automáticamente)"
    echo "  2. O manualmente: python /home/tsul/Documentos/serv_mcp/server.py"
fi
echo ""
