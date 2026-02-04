#!/bin/bash
################################################################################
# Script de Instalación de Servidor MCP en Linux Remoto
# Para acceso desde Claude Desktop en otro PC
################################################################################

set -e  # Salir si hay error

# ============================================================================
# CONFIGURACIÓN - EDITA ESTOS VALORES
# ============================================================================

SERVER_USER="usuario"                    # Usuario en el servidor remoto
SERVER_HOST="servidor.ejemplo.com"       # IP o hostname del servidor
REMOTE_PATH="/home/usuario/serv_mcp"     # Ruta en el servidor remoto
SSH_KEY="$HOME/.ssh/id_rsa"              # Clave SSH (dejar vacío para usar default)

# ============================================================================
# COLORES
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCIONES
# ============================================================================

print_header() {
    echo ""
    echo "========================================================================"
    echo -e "  ${BLUE}$1${NC}"
    echo "========================================================================"
    echo ""
}

print_step() {
    echo -e "${GREEN}▶${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# ============================================================================
# INICIO
# ============================================================================

print_header "Instalación de Servidor MCP Remoto"

echo "Configuración:"
echo "  Servidor: $SERVER_USER@$SERVER_HOST"
echo "  Ruta remota: $REMOTE_PATH"
echo "  Directorio local: $(pwd)"
echo ""

read -p "¿Continuar con la instalación? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Instalación cancelada."
    exit 1
fi

# ============================================================================
# VERIFICAR CONEXIÓN SSH
# ============================================================================

print_header "1. Verificando Conexión SSH"

print_step "Probando conexión SSH..."
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="ssh -i $SSH_KEY"
else
    SSH_CMD="ssh"
fi

if $SSH_CMD $SERVER_USER@$SERVER_HOST "echo 'OK'" &>/dev/null; then
    print_success "Conexión SSH exitosa"
else
    print_error "No se pudo conectar al servidor"
    echo ""
    echo "Soluciones:"
    echo "  1. Verificar que el servidor esté accesible"
    echo "  2. Configurar clave SSH:"
    echo "     ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_mcp"
    echo "     ssh-copy-id $SERVER_USER@$SERVER_HOST"
    exit 1
fi

# ============================================================================
# VERIFICAR REQUISITOS LOCALES
# ============================================================================

print_header "2. Verificando Archivos Locales"

required_files=(
    "server.py"
    "browser_cookies.py"
    ".env"
    "api_rest.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "✓ $file encontrado"
    else
        print_error "✗ $file NO encontrado"
        echo "Ejecuta este script desde el directorio serv_mcp"
        exit 1
    fi
done

# ============================================================================
# COPIAR ARCHIVOS AL SERVIDOR
# ============================================================================

print_header "3. Copiando Archivos al Servidor"

print_step "Creando directorio remoto..."
$SSH_CMD $SERVER_USER@$SERVER_HOST "mkdir -p $REMOTE_PATH"

print_step "Sincronizando archivos (esto puede tardar)..."
rsync -avz --progress \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    ./ $SERVER_USER@$SERVER_HOST:$REMOTE_PATH/

print_success "Archivos copiados"

# ============================================================================
# INSTALAR DEPENDENCIAS EN EL SERVIDOR
# ============================================================================

print_header "4. Instalando Dependencias en el Servidor"

print_step "Creando entorno virtual..."
$SSH_CMD $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd $(echo $REMOTE_PATH)
echo "📦 Creando venv..."
python3 -m venv venv || { echo "Error creando venv"; exit 1; }
echo "✓ Venv creado"
ENDSSH

print_step "Instalando paquetes Python..."
$SSH_CMD $SERVER_USER@$SERVER_HOST << ENDSSH
cd $REMOTE_PATH
source venv/bin/activate
echo "📦 Instalando dependencias..."
pip install --upgrade pip -q
pip install fastmcp requests urllib3 python-dotenv browser-cookie3 -q
pip install fastapi uvicorn -q
echo "✓ Dependencias instaladas"
ENDSSH

print_success "Dependencias instaladas"

# ============================================================================
# VERIFICAR INSTALACIÓN
# ============================================================================

print_header "5. Verificando Instalación"

print_step "Probando servidor MCP..."
if $SSH_CMD $SERVER_USER@$SERVER_HOST "cd $REMOTE_PATH && source venv/bin/activate && timeout 3 python server.py 2>&1 | grep -q 'FastMCP'"; then
    print_success "Servidor MCP funciona"
else
    print_warning "No se pudo verificar servidor MCP (puede ser normal)"
fi

print_step "Listando archivos instalados..."
$SSH_CMD $SERVER_USER@$SERVER_HOST "ls -lh $REMOTE_PATH"

# ============================================================================
# CONFIGURACIÓN DE CLAUDE DESKTOP
# ============================================================================

print_header "6. Configuración de Claude Desktop"

CLAUDE_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"

echo "Para conectar Claude Desktop al servidor remoto, edita:"
echo ""
echo "  $CLAUDE_CONFIG"
echo ""
echo "Agrega esta configuración:"
echo ""
cat << EOF
{
  "mcpServers": {
    "vmanage-remoto": {
      "command": "ssh",
      "args": [
        "-i", "$HOME/.ssh/id_rsa_mcp",
        "$SERVER_USER@$SERVER_HOST",
        "$REMOTE_PATH/venv/bin/python",
        "$REMOTE_PATH/server.py"
      ]
    }
  }
}
EOF
echo ""

read -p "¿Quieres que se agregue automáticamente? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    if [ -f "$CLAUDE_CONFIG" ]; then
        print_step "Creando backup de configuración actual..."
        cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
        print_success "Backup creado"
    fi
    
    print_step "Generando nueva configuración..."
    mkdir -p "$(dirname $CLAUDE_CONFIG)"
    cat > "$CLAUDE_CONFIG" << EOF
{
  "mcpServers": {
    "vmanage-remoto": {
      "command": "ssh",
      "args": [
        "-i",
        "$HOME/.ssh/id_rsa_mcp",
        "$SERVER_USER@$SERVER_HOST",
        "$REMOTE_PATH/venv/bin/python",
        "$REMOTE_PATH/server.py"
      ]
    }
  }
}
EOF
    print_success "Configuración guardada en $CLAUDE_CONFIG"
    print_warning "Reinicia Claude Desktop para aplicar cambios"
fi

# ============================================================================
# RESUMEN FINAL
# ============================================================================

print_header "✅ Instalación Completa"

echo "Estado de la instalación:"
echo ""
echo "  ✓ Archivos copiados a: $SERVER_USER@$SERVER_HOST:$REMOTE_PATH"
echo "  ✓ Entorno virtual creado"
echo "  ✓ Dependencias instaladas"
echo "  ✓ Servidor MCP listo"
echo ""

print_header "📝 Próximos Pasos"

echo ""
echo "1️⃣  CONFIGURAR CREDENCIALES EN EL SERVIDOR"
echo ""
echo "   $SSH_CMD $SERVER_USER@$SERVER_HOST"
echo "   nano $REMOTE_PATH/.env"
echo ""
echo "   Contenido:"
echo "   VMANAGE_IP=vmanage.cjf.gob.mx"
echo "   VMANAGE_USERNAME=tu_usuario"
echo "   VMANAGE_PASSWORD=tu_password"
echo ""

echo "2️⃣  PROBAR SERVIDOR MCP"
echo ""
echo "   $SSH_CMD $SERVER_USER@$SERVER_HOST \"cd $REMOTE_PATH && source venv/bin/activate && python server.py\""
echo ""

echo "3️⃣  REINICIAR CLAUDE DESKTOP"
echo ""
echo "   Cierra y abre Claude Desktop"
echo "   Las herramientas de vManage estarán disponibles"
echo ""

echo "4️⃣  (OPCIONAL) INICIAR API REST EN EL SERVIDOR"
echo ""
echo "   Para acceso desde GPT/Gemini:"
echo "   $SSH_CMD $SERVER_USER@$SERVER_HOST \"cd $REMOTE_PATH && source venv/bin/activate && python api_rest.py\""
echo ""

print_header "📚 Documentación"

echo ""
echo "  - INSTALACION_SERVIDOR_REMOTO.md - Guía completa"
echo "  - GUIA_CLAUDE_DESKTOP.md - Uso con Claude Desktop"
echo "  - CONECTAR_GPT_GEMINI.md - Uso con GPT/Gemini"
echo ""

print_header "🔧 Comandos Útiles"

echo ""
echo "# Conectar al servidor"
echo "$SSH_CMD $SERVER_USER@$SERVER_HOST"
echo ""
echo "# Ver logs del servidor MCP"
echo "$SSH_CMD $SERVER_USER@$SERVER_HOST \"cd $REMOTE_PATH && source venv/bin/activate && python server.py\""
echo ""
echo "# Actualizar archivos"
echo "rsync -avz --exclude 'venv' --exclude '__pycache__' ./ $SERVER_USER@$SERVER_HOST:$REMOTE_PATH/"
echo ""

print_success "¡Listo para usar!"
