#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

import time

import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔧 CONFIGURACIÓN FINAL - WORKFLOWS Y LAB NOTEBOOK")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("\n📡 Conectando...")
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)
    print("✅ Conectado")

    # 1. Configurar Workflows
    print("\n" + "=" * 80)
    print("🔧 CONFIGURANDO WORKFLOWS")
    print("=" * 80)

    # Backup
    stdin, stdout, stderr = ssh.exec_command(
        "cp /etc/nginx/sites-available/bioql /etc/nginx/sites-available/bioql.backup_workflows_$(date +%Y%m%d_%H%M%S)"
    )
    stdout.channel.recv_exit_status()
    print("✅ Backup creado")

    # Descargar config
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/bioql")
    config = stdout.read().decode()

    # Check si ya tiene workflows
    if "location /workflow" in config:
        print("✅ Workflows YA está configurado en Nginx")
    else:
        workflows_block = """    # Workflows Server (Port 5002)
    location /workflow/ {
        proxy_pass http://127.0.0.1:5002/;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        if ($request_method = OPTIONS) {
            return 204;
        }
    }

"""

        lines = config.split("\n")
        new_lines = []
        inserted = False

        for line in lines:
            if "location / {" in line and not inserted:
                new_lines.extend(workflows_block.split("\n"))
                inserted = True
            new_lines.append(line)

        if inserted:
            new_config = "\n".join(new_lines)

            # Escribir a archivo temporal
            temp_file = "/tmp/bioql_workflows.conf"
            stdin, stdout, stderr = ssh.exec_command(
                f"cat > {temp_file} << 'EOFCONFIG'\n{new_config}\nEOFCONFIG"
            )
            stdout.channel.recv_exit_status()

            stdin, stdout, stderr = ssh.exec_command(
                f"mv {temp_file} /etc/nginx/sites-available/bioql"
            )
            stdout.channel.recv_exit_status()
            print("✅ Configuración actualizada")

            # Test sintaxis
            stdin, stdout, stderr = ssh.exec_command("nginx -t")
            test_out = stderr.read().decode()

            if "syntax is ok" in test_out and "test is successful" in test_out:
                stdin, stdout, stderr = ssh.exec_command("systemctl reload nginx")
                stdout.channel.recv_exit_status()
                print("✅ Nginx recargado")

                # Test endpoint
                time.sleep(2)
                import requests

                try:
                    resp = requests.get("https://api.bioql.bio/workflow/", timeout=5)
                    if resp.status_code != 404:
                        print(f"✅ Endpoint /workflow/ responde: HTTP {resp.status_code}")
                    else:
                        print(f"⚠️  Endpoint /workflow/ → 404 (servidor puede no tener ruta raíz)")
                except:
                    print("⚠️  No se pudo testear endpoint")
            else:
                print(f"❌ Error sintaxis Nginx")
                print(test_out[:300])

    # 2. Verificar Lab Notebook
    print("\n" + "=" * 80)
    print("🔍 VERIFICANDO LAB NOTEBOOK")
    print("=" * 80)

    stdin, stdout, stderr = ssh.exec_command("ls -la /opt/bioql/lab_notebook/ 2>/dev/null")
    notebook = stdout.read().decode()

    if notebook and "total" in notebook:
        print("✅ Lab Notebook ENCONTRADO")
        print(notebook[:500])

        # Buscar procesos
        stdin, stdout, stderr = ssh.exec_command(
            "ps aux | grep -i notebook | grep python | grep -v grep"
        )
        procs = stdout.read().decode()

        if procs:
            print("\n✅ Proceso notebook corriendo:")
            print(procs[:300])
        else:
            print("\n⚠️  NO hay proceso notebook corriendo")
            print("   Archivos existen pero servidor no está activo")
    else:
        print("⚠️  Lab Notebook NO encontrado")
        print("   El servicio puede no estar desplegado en producción")

    # 3. Test final de todos los servicios
    print("\n" + "=" * 80)
    print("🧪 TEST FINAL DE SERVICIOS")
    print("=" * 80)

    ssh.close()

    import requests

    services = [
        ("BioQL Core", "https://api.bioql.bio/health"),
        ("Workflows", "https://api.bioql.bio/workflow/"),
        ("Quantum Graphs", "https://api.bioql.bio/quantum-graph/health"),
        ("Quantum Docking", "https://api.bioql.bio/health/quantum-docking"),
    ]

    for name, url in services:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print(f"✅ {name}: ONLINE")
            elif resp.status_code == 404:
                print(f"⚠️  {name}: 404 (endpoint no existe o ruta incorrecta)")
            else:
                print(f"⚠️  {name}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"❌ {name}: {type(e).__name__}")

    print("\n" + "=" * 80)
    print("✅ CONFIGURACIÓN COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
