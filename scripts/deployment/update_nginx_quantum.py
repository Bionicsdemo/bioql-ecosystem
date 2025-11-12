#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Actualizar Nginx para agregar proxy de /api/quantum/execute al puerto 5001
"""
import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

# Nueva configuración para agregar ANTES de location /api/
NEW_LOCATION = """
    # BioQL Quantum Execution API (Auth Server - Port 5001)
    location /api/quantum/execute {
        proxy_pass http://127.0.0.1:5001/api/quantum/execute;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;

        # Timeouts for long quantum experiments
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;

        # Handle OPTIONS
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization';
            add_header 'Content-Length' '0';
            add_header 'Content-Type' 'text/plain';
            return 204;
        }
    }

"""

print("=" * 80)
print("🔧 ACTUALIZANDO NGINX PARA /api/quantum/execute")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # 1. Backup de configuración actual
    print(f"\n💾 PASO 1: Backup de configuración")
    print("-" * 80)
    backup_cmd = "cp /etc/nginx/sites-available/bioql-api /etc/nginx/sites-available/bioql-api.backup_$(date +%Y%m%d_%H%M%S)"
    stdin, stdout, stderr = ssh.exec_command(backup_cmd)
    stdout.channel.recv_exit_status()
    print(f"✅ Backup creado")

    # 2. Descargar configuración actual
    print(f"\n📥 PASO 2: Descargando configuración actual")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/bioql-api")
    current_config = stdout.read().decode()
    print(f"✅ Configuración descargada ({len(current_config)} bytes)")

    # 3. Insertar nueva location ANTES de "location /api/"
    print(f"\n🔧 PASO 3: Insertando nueva location")
    print("-" * 80)

    # Encontrar la posición de "location /api/"
    lines = current_config.split("\n")
    new_lines = []
    inserted = False

    for line in lines:
        # Insertar ANTES de la primera "location /api/"
        if "location /api/" in line and not inserted:
            # Agregar la nueva location
            new_lines.extend(NEW_LOCATION.split("\n"))
            inserted = True

        new_lines.append(line)

    if not inserted:
        print(f"❌ No se encontró 'location /api/' en la configuración")
        ssh.close()
        exit(1)

    updated_config = "\n".join(new_lines)
    print(f"✅ Nueva location insertada")

    # 4. Subir configuración actualizada
    print(f"\n📤 PASO 4: Subiendo configuración actualizada")
    print("-" * 80)

    # Escribir a archivo temporal
    temp_cmd = f"cat > /tmp/bioql-api.new << 'EOFCONFIG'\n{updated_config}\nEOFCONFIG"
    stdin, stdout, stderr = ssh.exec_command(temp_cmd)
    stdout.channel.recv_exit_status()

    # Mover al lugar correcto
    stdin, stdout, stderr = ssh.exec_command(
        "mv /tmp/bioql-api.new /etc/nginx/sites-available/bioql-api"
    )
    stdout.channel.recv_exit_status()
    print(f"✅ Configuración actualizada")

    # 5. Verificar sintaxis de Nginx
    print(f"\n🔍 PASO 5: Verificando sintaxis de Nginx")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("nginx -t")
    test_output = stderr.read().decode()  # nginx -t escribe en stderr
    print(test_output)

    if "syntax is ok" in test_output and "test is successful" in test_output:
        print(f"✅ Sintaxis OK")

        # 6. Recargar Nginx
        print(f"\n🔄 PASO 6: Recargando Nginx")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl reload nginx")
        stdout.channel.recv_exit_status()

        # Verificar status
        stdin, stdout, stderr = ssh.exec_command("systemctl status nginx | head -10")
        status = stdout.read().decode()
        print(status)

        if "active (running)" in status:
            print(f"\n✅ Nginx recargado exitosamente")
        else:
            print(f"\n⚠️  Nginx status no muestra 'active (running)'")
    else:
        print(f"\n❌ Error de sintaxis en Nginx - NO se recargó")
        print(f"   Se puede restaurar con:")
        print(
            f"   cp /etc/nginx/sites-available/bioql-api.backup_* /etc/nginx/sites-available/bioql-api"
        )

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ ACTUALIZACIÓN COMPLETA")
    print("=" * 80)
    print(f"\n📊 Nueva configuración:")
    print(f"   /api/quantum/execute → 127.0.0.1:5001")
    print(f"   /api/* (resto) → 127.0.0.1:8100 (quantum-docking)")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
