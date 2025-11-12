#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Agregar location /api/quantum/execute al archivo bioql (HTTPS)
"""
import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

# Nueva location para /api/quantum/execute
NEW_LOCATION = """
    # BioQL & Quillow Quantum Execution API (Port 5001 - Auth Server)
    location /api/quantum/execute {
        proxy_pass http://127.0.0.1:5001/api/quantum/execute;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-API-Key' always;

        # Timeouts for long quantum experiments
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;

        # Handle OPTIONS
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-API-Key';
            add_header 'Content-Length' '0';
            add_header 'Content-Type' 'text/plain';
            return 204;
        }
    }

"""

print("=" * 80)
print("🔧 AGREGANDO /api/quantum/execute AL ARCHIVO bioql (HTTPS)")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # 1. Backup
    print(f"\n💾 PASO 1: Backup de configuración")
    print("-" * 80)
    backup_cmd = "cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_$(date +%Y%m%d_%H%M%S)"
    stdin, stdout, stderr = ssh.exec_command(backup_cmd)
    stdout.channel.recv_exit_status()
    print(f"✅ Backup creado")

    # 2. Descargar configuración actual
    print(f"\n📥 PASO 2: Descargando configuración actual")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/bioql")
    current_config = stdout.read().decode()
    print(f"✅ Configuración descargada ({len(current_config)} bytes)")

    # 3. Insertar nueva location ANTES de "location /"
    print(f"\n🔧 PASO 3: Insertando nueva location")
    print("-" * 80)

    lines = current_config.split("\n")
    new_lines = []
    inserted = False

    for line in lines:
        # Insertar ANTES de "location / {" (que es el catch-all)
        if "location / {" in line and not inserted:
            # Agregar la nueva location
            new_lines.extend(NEW_LOCATION.split("\n"))
            inserted = True

        new_lines.append(line)

    if not inserted:
        print(f"❌ No se encontró 'location / {{' en la configuración")
        ssh.close()
        exit(1)

    updated_config = "\n".join(new_lines)
    print(f"✅ Nueva location insertada antes de 'location / {{'")

    # 4. Subir configuración actualizada
    print(f"\n📤 PASO 4: Subiendo configuración actualizada")
    print("-" * 80)

    # Escribir a archivo temporal
    temp_cmd = f"cat > /tmp/bioql.new << 'EOFCONFIG'\n{updated_config}\nEOFCONFIG"
    stdin, stdout, stderr = ssh.exec_command(temp_cmd)
    stdout.channel.recv_exit_status()

    # Mover al lugar correcto
    stdin, stdout, stderr = ssh.exec_command("mv /tmp/bioql.new /etc/nginx/sites-available/bioql")
    stdout.channel.recv_exit_status()
    print(f"✅ Configuración actualizada")

    # 5. Verificar sintaxis
    print(f"\n🔍 PASO 5: Verificando sintaxis de Nginx")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("nginx -t")
    test_output = stderr.read().decode()
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

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ ACTUALIZACIÓN COMPLETA")
    print("=" * 80)
    print(f"\n📊 Configuración HTTPS (api.bioql.bio):")
    print(f"   /api/quantum/execute → 127.0.0.1:5001 (BioQL + Quillow)")
    print(f"   /api/quantum-docking/ → 127.0.0.1:8100 (Quantum Docking)")
    print(f"   /api/quantum/ → 127.0.0.1:9000 (Quantum Graphs)")
    print(f"   /workflow → 127.0.0.1:5002 (Workflows)")
    print(f"   / → 127.0.0.1:5001 (Auth/Billing)")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
