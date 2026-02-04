#!/bin/bash
################################################################################
# Sincronizar Cookies del Navegador Local al Servidor Remoto
# Extrae cookies de Firefox/Chrome y las copia al servidor Linux
################################################################################

set -e

# ============================================================================
# CONFIGURACIÓN - EDITA ESTOS VALORES
# ============================================================================

SERVER_USER="usuario"                      # Usuario en el servidor
SERVER_HOST="servidor.ejemplo.com"         # IP o hostname del servidor
REMOTE_PATH="/home/usuario/serv_mcp"       # Ruta en el servidor

# ============================================================================
# COLORES
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# FUNCIONES
# ============================================================================

print_step() {
    echo -e "${GREEN}▶${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ============================================================================
# INICIO
# ============================================================================

echo ""
echo "========================================================================"
echo -e "  ${BLUE}Sincronización de Cookies vManage${NC}"
echo "========================================================================"
echo ""
echo "Configuración:"
echo "  Servidor: $SERVER_USER@$SERVER_HOST"
echo "  Ruta: $REMOTE_PATH"
echo ""

# ============================================================================
# EXTRAER COOKIES DEL NAVEGADOR LOCAL
# ============================================================================

print_step "Extrayendo cookies del navegador local..."

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Extraer cookies
python3 extraer_cookies.py > /tmp/vmanage_cookies.env 2> /tmp/cookie_extraction.log

if [ $? -ne 0 ]; then
    print_error "No se pudieron extraer las cookies"
    echo ""
    cat /tmp/cookie_extraction.log
    echo ""
    echo "Soluciones:"
    echo "  1. Abre Firefox o Chrome"
    echo "  2. Navega a https://vmanage.cjf.gob.mx"
    echo "  3. Inicia sesión"
    echo "  4. Vuelve a ejecutar este script"
    rm -f /tmp/vmanage_cookies.env /tmp/cookie_extraction.log
    exit 1
fi

print_success "Cookies extraídas exitosamente"

# Verificar contenido
if grep -q "VMANAGE_JSESSIONID" /tmp/vmanage_cookies.env && \
   grep -q "VMANAGE_XSRF_TOKEN" /tmp/vmanage_cookies.env; then
    print_success "Cookies válidas encontradas"
else
    print_error "Cookies inválidas o incompletas"
    cat /tmp/vmanage_cookies.env
    rm -f /tmp/vmanage_cookies.env /tmp/cookie_extraction.log
    exit 1
fi

# ============================================================================
# COPIAR COOKIES AL SERVIDOR
# ============================================================================

print_step "Verificando conexión al servidor..."

if ! ssh -o ConnectTimeout=5 $SERVER_USER@$SERVER_HOST "echo OK" &>/dev/null; then
    print_error "No se puede conectar al servidor"
    echo ""
    echo "Verifica:"
    echo "  - Conexión de red"
    echo "  - Credenciales SSH: $SERVER_USER@$SERVER_HOST"
    echo "  - Configuración de claves SSH"
    rm -f /tmp/vmanage_cookies.env /tmp/cookie_extraction.log
    exit 1
fi

print_success "Conexión al servidor OK"

print_step "Copiando cookies al servidor..."

scp -q /tmp/vmanage_cookies.env $SERVER_USER@$SERVER_HOST:/tmp/

if [ $? -ne 0 ]; then
    print_error "Error copiando cookies"
    rm -f /tmp/vmanage_cookies.env /tmp/cookie_extraction.log
    exit 1
fi

print_success "Cookies copiadas"

# ============================================================================
# ACTUALIZAR .env EN EL SERVIDOR
# ============================================================================

print_step "Actualizando .env en el servidor..."

ssh $SERVER_USER@$SERVER_HOST << EOF
cd $REMOTE_PATH

# Crear backup
if [ -f .env ]; then
    cp .env .env.backup.\$(date +%Y%m%d_%H%M%S)
    echo "  ✓ Backup creado"
fi

# Remover cookies antiguas del .env
if [ -f .env ]; then
    sed -i.tmp '/VMANAGE_JSESSIONID/d' .env
    sed -i.tmp '/VMANAGE_XSRF_TOKEN/d' .env
    rm -f .env.tmp
fi

# Agregar nuevas cookies
cat /tmp/vmanage_cookies.env >> .env

# Limpiar
rm -f /tmp/vmanage_cookies.env

# Verificar
if grep -q "VMANAGE_JSESSIONID" .env && grep -q "VMANAGE_XSRF_TOKEN" .env; then
    echo "  ✓ Cookies actualizadas correctamente"
    
    # Proteger archivo
    chmod 600 .env
    
    # Mostrar timestamp
    echo "  ✓ Última actualización: \$(date '+%Y-%m-%d %H:%M:%S')"
else
    echo "  ✗ Error: Cookies no se actualizaron correctamente"
    exit 1
fi
EOF

if [ $? -eq 0 ]; then
    print_success "Cookies sincronizadas en el servidor"
else
    print_error "Error actualizando .env en el servidor"
    rm -f /tmp/vmanage_cookies.env /tmp/cookie_extraction.log
    exit 1
fi

# ============================================================================
# LIMPIAR ARCHIVOS TEMPORALES
# ============================================================================

rm -f /tmp/vmanage_cookies.env /tmp/cookie_extraction.log

# ============================================================================
# RESUMEN
# ============================================================================

echo ""
echo "========================================================================"
echo -e "  ${GREEN}✓ Sincronización Completa${NC}"
echo "========================================================================"
echo ""
echo "Estado:"
echo "  ✓ Cookies extraídas del navegador local"
echo "  ✓ Cookies copiadas al servidor"
echo "  ✓ .env actualizado en $SERVER_HOST"
echo ""
echo "Próximos pasos:"
echo "  1. El servidor MCP ya puede usar las cookies"
echo "  2. Reinicia el servidor MCP si ya estaba corriendo"
echo "  3. Las cookies expiran - vuelve a ejecutar este script periódicamente"
echo ""
echo "Automatización (opcional):"
echo "  Para sincronizar automáticamente cada 4 horas:"
echo "  crontab -e"
echo "  # Agregar: 0 */4 * * * $(realpath $0) >> /tmp/cookie_sync.log 2>&1"
echo ""
echo "Verificar en el servidor:"
echo "  ssh $SERVER_USER@$SERVER_HOST 'tail -3 $REMOTE_PATH/.env'"
echo ""
