#!/bin/bash
# Script para extraer y guardar cookies de Analytics Cloud para el servidor MCP

echo "🔄 Extrayendo cookies de Analytics Cloud..."

cd /home/tsul/Documentos/serv_mcp
source venv/bin/activate

python3 << 'EOF'
import browser_cookie3
import json
import os

try:
    cj = browser_cookie3.chrome(domain_name='us02.analytics.sdwan.cisco.com')
    
    cookies_data = {
        'session': None,
        'csrf_token': None,
        'overlay_id': None,
        'timestamp': None
    }
    
    for cookie in cj:
        if cookie.name == 'session':
            cookies_data['session'] = cookie.value
        elif cookie.name == 'okta-oauth-state':
            cookies_data['csrf_token'] = cookie.value
        elif cookie.name == 'cl-overlay-id':
            cookies_data['overlay_id'] = cookie.value
    
    if cookies_data['session'] and cookies_data['csrf_token']:
        from datetime import datetime
        cookies_data['timestamp'] = datetime.now().isoformat()
        
        # Guardar en archivo oculto
        with open('.analytics_cookies.json', 'w') as f:
            json.dump(cookies_data, f)
        
        print(f"✅ Cookies guardadas correctamente")
        print(f"   Session: {'***' + cookies_data['session'][-10:]}")
        print(f"   CSRF: {'***' + cookies_data['csrf_token'][-10:]}")
        print(f"   Overlay: {cookies_data['overlay_id']}")
        print(f"   Timestamp: {cookies_data['timestamp']}")
    else:
        print("❌ No se encontraron todas las cookies necesarias")
        print("   Por favor, inicia sesión en Analytics Cloud en Chrome")
        exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
EOF

echo ""
echo "✅ Listo. Reinicia Claude Desktop para que use las nuevas cookies."
