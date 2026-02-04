#!/usr/bin/env python3
"""
CLI independiente para gestión de Cisco SD-WAN (vManage)
Sin dependencias de MCP - Completamente gratuito
Usa cookies del navegador automáticamente
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del servidor al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar las clases y funciones del servidor
from server import VManageSession, get_vmanage_session


def limpiar_pantalla():
    """Limpia la pantalla del terminal"""
    os.system('clear' if os.name != 'nt' else 'cls')


def mostrar_menu():
    """Muestra el menú principal"""
    limpiar_pantalla()
    print("\n" + "=" * 60)
    print("  🌐 CISCO SD-WAN MANAGER - CLI CON COOKIES")
    print("=" * 60)
    print("\n📋 Opciones disponibles:\n")
    print("  1. Listar todos los dispositivos")
    print("  2. Ver salud de un equipo específico")
    print("  3. Ver sesiones BFD de un dispositivo")
    print("  4. Listar alarmas críticas")
    print("  5. Salir")
    print("\n" + "=" * 60)


def listar_dispositivos_cli(session):
    """Lista todos los dispositivos"""
    try:
        print("\n🔄 Consultando dispositivos...")
        print("-" * 60)
        
        endpoint = "/dataservice/device"
        result = session.get(endpoint)
        
        if 'data' in result:
            devices = result['data']
            
            print(f"\n✅ Total de dispositivos: {len(devices)}\n")
            
            for idx, device in enumerate(devices, 1):
                hostname = device.get('host-name', 'N/A')
                device_id = device.get('system-ip', 'N/A')
                device_type = device.get('device-type', 'N/A')
                device_model = device.get('device-model', 'N/A')
                site_id = device.get('site-id', 'N/A')
                reachability = device.get('reachability', 'N/A')
                status = device.get('state', 'N/A')
                
                # Icono según reachabilidad
                icon = "🟢" if reachability == "reachable" else "🔴"
                
                print(f"{icon} Dispositivo #{idx}")
                print(f"   Hostname:       {hostname}")
                print(f"   Device ID:      {device_id}")
                print(f"   Tipo:           {device_type}")
                print(f"   Modelo:         {device_model}")
                print(f"   Site ID:        {site_id}")
                print(f"   Alcanzabilidad: {reachability}")
                print(f"   Estado:         {status}")
                print()
            
            return True
        else:
            print("⚠️  No se encontraron dispositivos")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def ver_salud_equipo_cli(session, device_id):
    """Consulta el estado de salud de un dispositivo"""
    try:
        print(f"\n🔄 Consultando salud del dispositivo {device_id}...")
        print("-" * 60)
        
        endpoint = f"/dataservice/device?system-ip={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result and len(result['data']) > 0:
            device = result['data'][0]
            
            reachability = device.get('reachability', 'N/A')
            icon = "🟢" if reachability == "reachable" else "🔴"
            
            print(f"\n{icon} Estado del dispositivo:\n")
            print(f"   Hostname:              {device.get('host-name', 'N/A')}")
            print(f"   Device ID:             {device.get('system-ip', 'N/A')}")
            print(f"   Tipo:                  {device.get('device-type', 'N/A')}")
            print(f"   Modelo:                {device.get('device-model', 'N/A')}")
            print(f"   Site ID:               {device.get('site-id', 'N/A')}")
            print(f"   Alcanzabilidad:        {reachability}")
            print(f"   Estado:                {device.get('state', 'N/A')}")
            print(f"   Uptime:                {device.get('uptime-date', 'N/A')}")
            print(f"   Versión:               {device.get('version', 'N/A')}")
            print(f"   Serial:                {device.get('board-serial', 'N/A')}")
            print(f"   Validez Certificado:   {device.get('validity', 'N/A')}")
            
            return True
        else:
            print(f"\n⚠️  No se encontró el dispositivo con ID: {device_id}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def ver_sesiones_bfd_cli(session, device_id):
    """Consulta las sesiones BFD de un dispositivo"""
    try:
        print(f"\n🔄 Consultando sesiones BFD del dispositivo {device_id}...")
        print("-" * 60)
        
        endpoint = f"/dataservice/device/bfd/sessions?deviceId={device_id}"
        result = session.get(endpoint)
        
        if 'data' in result:
            bfd_sessions = result['data']
            
            if not bfd_sessions:
                print(f"\n⚠️  No hay sesiones BFD activas para el dispositivo {device_id}")
                return False
            
            # Contar estados
            state_counts = {}
            for sess in bfd_sessions:
                state = sess.get('state', 'unknown')
                state_counts[state] = state_counts.get(state, 0) + 1
            
            print(f"\n✅ Total de sesiones BFD: {len(bfd_sessions)}")
            print(f"📊 Estados: {state_counts}\n")
            
            for idx, session_data in enumerate(bfd_sessions, 1):
                state = session_data.get('state', 'N/A')
                icon = "🟢" if state == "up" else "🔴" if state == "down" else "🟡"
                
                print(f"{icon} Sesión BFD #{idx}")
                print(f"   System IP:       {session_data.get('system-ip', 'N/A')}")
                print(f"   Site ID:         {session_data.get('site-id', 'N/A')}")
                print(f"   Color Local:     {session_data.get('local-color', 'N/A')}")
                print(f"   Color Remoto:    {session_data.get('color', 'N/A')}")
                print(f"   Estado:          {state}")
                print(f"   Peer IP:         {session_data.get('src-ip', 'N/A')}")
                print(f"   Destino IP:      {session_data.get('dst-ip', 'N/A')}")
                print(f"   Uptime:          {session_data.get('uptime-date', 'N/A')}")
                print(f"   Transiciones:    {session_data.get('transitions', 'N/A')}")
                print()
            
            return True
        else:
            print(f"\n⚠️  No se pudo obtener información de sesiones BFD")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def listar_alarmas_criticas_cli(session):
    """Lista las alarmas críticas de las últimas 24 horas"""
    try:
        from datetime import datetime, timedelta
        
        print("\n🔄 Consultando alarmas críticas...")
        print("-" * 60)
        
        # Calcular timestamp de hace 24 horas
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        from_time = int(yesterday.timestamp() * 1000)
        
        endpoint = "/dataservice/alarms"
        result = session.get(endpoint)
        
        if 'data' in result:
            all_alarms = result['data']
            
            # Filtrar alarmas críticas de las últimas 24 horas
            critical_alarms = []
            for alarm in all_alarms:
                severity = alarm.get('severity', '').lower()
                entry_time = alarm.get('entry_time', 0)
                
                if severity == 'critical' and entry_time >= from_time:
                    critical_alarms.append(alarm)
            
            if not critical_alarms:
                print("\n✅ No hay alarmas críticas en las últimas 24 horas")
                return True
            
            print(f"\n⚠️  Total de alarmas críticas: {len(critical_alarms)}\n")
            
            for idx, alarm in enumerate(critical_alarms, 1):
                entry_time = alarm.get('entry_time', 0)
                timestamp = datetime.fromtimestamp(entry_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"🔴 Alarma #{idx}")
                print(f"   Severidad:    {alarm.get('severity', 'N/A')}")
                print(f"   Mensaje:      {alarm.get('message', 'N/A')}")
                print(f"   Dispositivo:  {alarm.get('system-ip', 'N/A')}")
                print(f"   Hostname:     {alarm.get('host-name', 'N/A')}")
                print(f"   Site ID:      {alarm.get('site-id', 'N/A')}")
                print(f"   Fecha/Hora:   {timestamp}")
                print(f"   Reconocida:   {alarm.get('acknowledged', False)}")
                print(f"   Activa:       {alarm.get('active', 'N/A')}")
                print()
            
            return True
        else:
            print("\n⚠️  No se pudieron obtener las alarmas")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def verificar_autenticacion(session):
    """Verifica que la sesión esté autenticada correctamente"""
    try:
        # Intentar una consulta simple para verificar autenticación
        result = session.get("/dataservice/device", timeout=10)
        if isinstance(result, dict) and 'data' in result:
            return True
        return False
    except Exception:
        return False


def main():
    """Función principal del CLI"""
    try:
        # Crear sesión con vManage
        print("\n🔐 Conectando con vManage...")
        print("   Servidor: Vmanage.cjf.gob.mx")
        print("   Usuario: jbahena")
        
        session = get_vmanage_session()
        
        # Verificar que la autenticación fue exitosa
        if not verificar_autenticacion(session):
            raise ConnectionError("Autenticación fallida - Verifica las credenciales")
        
        print("✅ Autenticación exitosa\n")
        
        while True:
            mostrar_menu()
            
            opcion = input("\n👉 Selecciona una opción (1-5): ").strip()
            
            if opcion == "1":
                listar_dispositivos_cli(session)
                input("\n⏎ Presiona Enter para continuar...")
                
            elif opcion == "2":
                device_id = input("\n👉 Ingresa el System IP del dispositivo: ").strip()
                if device_id:
                    ver_salud_equipo_cli(session, device_id)
                else:
                    print("\n❌ Debes ingresar un Device ID válido")
                input("\n⏎ Presiona Enter para continuar...")
                
            elif opcion == "3":
                device_id = input("\n👉 Ingresa el System IP del dispositivo: ").strip()
                if device_id:
                    ver_sesiones_bfd_cli(session, device_id)
                else:
                    print("\n❌ Debes ingresar un Device ID válido")
                input("\n⏎ Presiona Enter para continuar...")
                
            elif opcion == "4":
                listar_alarmas_criticas_cli(session)
                input("\n⏎ Presiona Enter para continuar...")
                
            elif opcion == "5":
                limpiar_pantalla()
                print("\n👋 ¡Hasta luego!\n")
                sys.exit(0)
                
            else:
                print("\n❌ Opción inválida. Por favor selecciona 1-5")
                input("\n⏎ Presiona Enter para continuar...")
    
    except ValueError as e:
        print("\n" + "=" * 60)
        print("❌ ERROR DE CONFIGURACIÓN")
        print("=" * 60)
        print(f"\n{str(e)}")
        print("\n💡 Solución:")
        print("   1. Verifica el archivo .env en:")
        print("      /home/tsul/Documentos/serv_mcp/.env")
        print("\n   2. Debe contener:")
        print("      VMANAGE_IP=Vmanage.cjf.gob.mx")
        print("      VMANAGE_USERNAME=tu_usuario")
        print("      VMANAGE_PASSWORD=tu_contraseña")
        print("\n" + "=" * 60 + "\n")
        sys.exit(1)
    
    except ConnectionError as e:
        print("\n" + "=" * 60)
        print("❌ ERROR DE AUTENTICACIÓN")
        print("=" * 60)
        print(f"\n{str(e)}")
        print("\n💡 Posibles causas:")
        print("   1. Usuario o contraseña incorrectos")
        print("   2. Cuenta bloqueada (demasiados intentos fallidos)")
        print("   3. Contraseña expirada")
        print("   4. No hay conexión con vManage")
        print("\n💡 Solución:")
        print("   1. Verifica las credenciales en el archivo .env")
        print("   2. Intenta acceder a vManage desde el navegador:")
        print("      https://Vmanage.cjf.gob.mx")
        print("   3. Contacta al administrador si persiste el problema")
        print("\n" + "=" * 60 + "\n")
        sys.exit(1)
        
    except KeyboardInterrupt:
        limpiar_pantalla()
        print("\n\n👋 Interrumpido por el usuario. ¡Hasta luego!\n")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
