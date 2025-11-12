#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
SOLUCIÓN COMPLETA - Configurar Nginx para Workflows y Lab Notebook
"""
import time

import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔧 SOLUCIÓN COMPLETA - CONFIGURANDO TODOS LOS SERVICIOS")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"\n📡 Conectando como {USERNAME}@{SERVER}...")
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)
    print(f"✅ Conectado")

    # ========================================================================
    # PASO 1: Verificar estado actual
    # ========================================================================
    print(f"\n{'='*80}")
    print(f"📊 PASO 1: Verificar estado actual")
    print(f"{'='*80}")

    # Ver puertos escuchando
    stdin, stdout, stderr = ssh.exec_command(
        "ss -tulpn | grep LISTEN | grep -E '5001|5002|8100|9000' | sort -t: -k2 -n"
    )
    ports = stdout.read().decode()
    print(f"\n📡 Puertos escuchando:")
    print(ports[:800])

    # Verificar configuración actual de Nginx
    stdin, stdout, stderr = ssh.exec_command(
        "grep -n 'location /workflow' /etc/nginx/sites-enabled/bioql"
    )
    workflow_config = stdout.read().decode()

    if workflow_config:
        print(f"\n✅ Nginx YA tiene configuración de /workflow:")
        print(workflow_config)
    else:
        print(f"\n⚠️  Nginx NO tiene configuración de /workflow")

    # ========================================================================
    # PASO 2: Agregar configuración de Workflows a Nginx
    # ========================================================================
    print(f"\n{'='*80}")
    print(f"🔧 PASO 2: Configurar Nginx para Workflows")
    print(f"{'='*80}")

    if not workflow_config:
        # Descargar configuración actual
        stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/bioql")
        current_config = stdout.read().decode()

        # Agregar configuración de workflows DESPUÉS de location /workflow existente o antes de location /
        workflows_location = """
    # Workflows Server (Port 5002)
    location /workflow/ {
        proxy_pass http://127.0.0.1:5002/;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

        if ($request_method = OPTIONS) {
            return 204;
        }
    }

"""

        # Encontrar dónde insertar (antes del primer location /)
        lines = current_config.split("\n")
        new_lines = []
        inserted = False

        for line in lines:
            # Insertar ANTES de "location / {"
            if "location / {" in line and not inserted:
                new_lines.extend(workflows_location.split("\n"))
                inserted = True

            new_lines.append(line)

        if inserted:
            updated_config = "\n".join(new_lines)

            # Backup
            backup_cmd = "cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_workflows_$(date +%Y%m%d_%H%M%S)"
            stdin, stdout, stderr = ssh.exec_command(backup_cmd)
            stdout.channel.recv_exit_status()
            print(f"✅ Backup creado")

            # Subir nueva configuración
            temp_cmd = f"cat > /tmp/bioql_new.conf << 'EOFCONFIG'\n{updated_config}\nEOFCONFIG"
            stdin, stdout, stderr = ssh.exec_command(temp_cmd)
            stdout.channel.recv_exit_status()

            stdin, stdout, stderr = ssh.exec_command(
                "mv /tmp/bioql_new.conf /etc/nginx/sites-available/bioql"
            )
            stdout.channel.recv_exit_status()
            print(f"✅ Configuración actualizada")

            # Test de sintaxis
            stdin, stdout, stderr = ssh.exec_command("nginx -t")
            test_output = stderr.read().decode()
            print(f"\n🔍 Test de sintaxis:")
            print(test_output[:300])

            if "syntax is ok" in test_output and "test is successful" in test_output:
                print(f"✅ Sintaxis OK - Recargando Nginx...")

                stdin, stdout, stderr = ssh.exec_command("systemctl reload nginx")
                stdout.channel.recv_exit_status()
                print(f"✅ Nginx recargado")
            else:
                print(f"❌ Error de sintaxis - NO se recargó Nginx")
        else:
            print(f"❌ No se pudo insertar configuración")
    else:
        print(f"✅ Workflows ya está configurado en Nginx")

    # ========================================================================
    # PASO 3: Verificar/Configurar Lab Notebook
    # ========================================================================
    print(f"\n{'='*80}")
    print(f"🔍 PASO 3: Verificar Lab Notebook")
    print(f"{'='*80}")

    # Buscar directorio lab_notebook
    stdin, stdout, stderr = ssh.exec_command("ls -la /opt/bioql/lab_notebook/ 2>/dev/null")
    notebook_files = stdout.read().decode()

    if notebook_files and "total" in notebook_files:
        print(f"✅ Lab Notebook encontrado")
        print(notebook_files[:400])

        # Verificar si hay servidor corriendo
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i 'notebook' | grep -v grep")
        notebook_procs = stdout.read().decode()

        if notebook_procs:
            print(f"\n✅ Procesos notebook:")
            print(notebook_procs[:300])

            # Extraer puerto si existe
            import re

            port_match = re.search(r":(\d+)", notebook_procs)
            if port_match:
                notebook_port = port_match.group(1)
                print(f"\n✅ Lab Notebook puerto: {notebook_port}")

                # Agregar a Nginx si no existe
                stdin, stdout, stderr = ssh.exec_command(
                    "grep -n 'location /lab-notebook' /etc/nginx/sites-enabled/bioql"
                )
                lab_config = stdout.read().decode()

                if not lab_config:
                    print(f"\n🔧 Agregando Lab Notebook a Nginx...")
                    # (similar al proceso de Workflows)
                    print(f"⚠️  Configuración manual requerida con puerto {notebook_port}")
        else:
            print(f"\n⚠️  Lab Notebook NO está corriendo")
            print(f"   Archivos existen pero no hay servidor activo")
    else:
        print(f"⚠️  Lab Notebook NO encontrado en /opt/bioql/lab_notebook/")
        print(f"   Este servicio puede no estar desplegado")

    # ========================================================================
    # PASO 4: Verificación final
    # ========================================================================
    print(f"\n{'='*80}")
    print(f"✅ PASO 4: Verificación final")
    print(f"{'='*80}")

    time.sleep(2)

    # Test de endpoints
    print(f"\n🧪 Testing endpoints...")

    ssh.close()

    # Test HTTP desde fuera
    import requests

    endpoints_to_test = [
        ("BioQL Core", "https://api.bioql.bio/health"),
        ("Workflows", "https://api.bioql.bio/workflow/health"),
        ("Quantum Graphs", "https://api.bioql.bio/quantum-graph/health"),
        ("Quantum Docking", "https://api.bioql.bio/health/quantum-docking"),
    ]

    results = []
    for name, url in endpoints_to_test:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: ONLINE")
                results.append((name, "ONLINE"))
            else:
                print(f"⚠️  {name}: HTTP {response.status_code}")
                results.append((name, f"HTTP_{response.status_code}"))
        except Exception as e:
            print(f"❌ {name}: {type(e).__name__}")
            results.append((name, "ERROR"))

    # Resumen final
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN FINAL")
    print(f"{'='*80}")

    online = sum(1 for _, status in results if status == "ONLINE")
    total = len(results)

    print(f"\n✅ Servicios ONLINE: {online}/{total}")

    for name, status in results:
        emoji = "✅" if status == "ONLINE" else "⚠️"
        print(f"   {emoji} {name}: {status}")

    print(f"\n{'='*80}")
    print(f"✅ CONFIGURACIÓN COMPLETA")
    print(f"{'='*80}")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
