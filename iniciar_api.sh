#!/bin/bash

# Script para iniciar la API REST

echo "=================================================================="
echo "  🌐 Iniciando API REST para vManage"
echo "  Compatible con GPT, Gemini y cualquier cliente HTTP"
echo "=================================================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "api_rest.py" ]; then
    echo "❌ Error: No se encuentra api_rest.py"
    echo "   Ejecuta este script desde: /home/tsul/Documentos/serv_mcp"
    exit 1
fi

# Activar entorno virtual
if [ -d "venv" ]; then
    echo "🔧 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "❌ Error: No se encuentra el entorno virtual"
    echo "   Ejecuta: python3 -m venv venv"
    exit 1
fi

# Verificar dependencias
echo "📦 Verificando dependencias..."
python -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  FastAPI no instalado. Instalando..."
    pip install fastapi uvicorn -q
fi

python -c "import uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Uvicorn no instalado. Instalando..."
    pip install uvicorn -q
fi

# Verificar .env
if [ ! -f ".env" ]; then
    echo "❌ Error: No se encuentra el archivo .env"
    echo "   Crea uno con:"
    echo "   VMANAGE_IP=vmanage.cjf.gob.mx"
    echo "   VMANAGE_USERNAME=tu_usuario"
    echo "   VMANAGE_PASSWORD=tu_password"
    exit 1
fi

echo "✅ Todo listo. Iniciando servidor..."
echo ""
echo "=================================================================="
echo "  📡 Servidor disponible en: http://localhost:8000"
echo "  📚 Documentación: http://localhost:8000/docs"
echo "  🔧 Redoc: http://localhost:8000/redoc"
echo "=================================================================="
echo ""
echo "💡 Presiona Ctrl+C para detener el servidor"
echo ""

# Iniciar servidor
python api_rest.py
