#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar y reiniciar todos los servidores de BioQL
"""
import time

import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔍 VERIFICANDO TODOS LOS SERVIDORES BIOQL")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"\n📡 Conectando como {USERNAME}@{SERVER}...")
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)
    print(f"✅ Conectado")

    # 1. Ver todos los procesos corriendo
    print(f"\n{'='*80}")
    print(f"📊 PASO 1: Procesos Python corriendo")
    print(f"{'='*80}")
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'python' | grep -v grep")
    processes = stdout.read().decode()
    print(processes[:2000])

    # 2. Ver puertos escuchando
    print(f"\n{'='*80}")
    print(f"📡 PASO 2: Puertos escuchando")
    print(f"{'='*80}")
    stdin, stdout, stderr = ssh.exec_command(
        "ss -tulpn | grep LISTEN | grep -E '5001|5002|8080|8100|9000' | sort -t: -k2 -n"
    )
    ports = stdout.read().decode()
    print(ports)

    # 3. Identificar qué servidores están corriendo
    print(f"\n{'='*80}")
    print(f"🔍 PASO 3: Identificar servidores")
    print(f"{'='*80}")

    services = {
        "5001": {"name": "Auth & Billing (BioQL Core)", "process": None, "pid": None},
        "5002": {"name": "Workflows", "process": None, "pid": None},
        "8080": {"name": "Frontend", "process": None, "pid": None},
        "8100": {"name": "Quantum Docking", "process": None, "pid": None},
        "9000": {"name": "Quantum Graphs", "process": None, "pid": None},
    }

    # Verificar cada puerto
    for port, info in services.items():
        stdin, stdout, stderr = ssh.exec_command(f"lsof -ti:{port}")
        pid = stdout.read().decode().strip()

        if pid:
            # Obtener nombre del proceso
            stdin, stdout, stderr = ssh.exec_command(f"ps -p {pid} -o cmd --no-headers")
            cmd = stdout.read().decode().strip()

            info["pid"] = pid
            info["process"] = cmd[:100]
            print(f"✅ {info['name']} (Port {port})")
            print(f"   PID: {pid}")
            print(f"   Process: {cmd[:80]}...")
        else:
            print(f"❌ {info['name']} (Port {port})")
            print(f"   NOT RUNNING")

    # 4. Reiniciar servidores que no están corriendo
    print(f"\n{'='*80}")
    print(f"🔄 PASO 4: Reiniciar servidores offline")
    print(f"{'='*80}")

    # Verificar si hay que reiniciar alguno
    offline_services = [port for port, info in services.items() if info["pid"] is None]

    if not offline_services:
        print(f"✅ TODOS LOS SERVIDORES ESTÁN CORRIENDO")
    else:
        print(
            f"⚠️  {len(offline_services)} servidores offline: {', '.join([services[p]['name'] for p in offline_services])}"
        )

        # Reiniciar Auth Server (5001) si está offline
        if "5001" in offline_services:
            print(f"\n🔄 Reiniciando Auth & Billing Server (5001)...")
            start_cmd = """
cd /opt/bioql/auth_server && \
export IBM_QUANTUM_TOKEN='sKwyF9w532GA_7aXLvKjKr6h5UQrM26Mcpv3QYKbunAC' && \
export BIOQL_AUTH_PORT=5001 && \
export BIOQL_AUTH_HOST='0.0.0.0' && \
export BIOQL_DB_PATH='./users.db' && \
export STRIPE_SECRET_KEY='__STRIPE_REDACTED__' && \
export STRIPE_WEBHOOK_SECRET='whsec_FWfw9QSSHIGm1DOVc8mCVhaObn4QNZxi' && \
export BIOQL_INVOICE_THRESHOLD_USD='3000' && \
nohup /opt/bioql/venv/bin/python bioql_auth_server_stripe.py > /tmp/bioql_auth_server.log 2>&1 &
"""
            stdin, stdout, stderr = ssh.exec_command(start_cmd)
            stdout.channel.recv_exit_status()
            print(f"   ✅ Comando ejecutado")
            time.sleep(3)

        # Reiniciar Workflows (5002) si está offline
        if "5002" in offline_services:
            print(f"\n🔄 Reiniciando Workflows Server (5002)...")
            stdin, stdout, stderr = ssh.exec_command("ls -la /opt/bioql/workflow_server/")
            workflow_files = stdout.read().decode()
            if workflow_files:
                print(f"   Archivos encontrados:")
                print(f"   {workflow_files[:300]}")

                # Buscar script de inicio
                stdin, stdout, stderr = ssh.exec_command(
                    "find /opt/bioql/workflow_server -name '*.py' | head -5"
                )
                py_files = stdout.read().decode().strip().split("\n")

                if py_files and py_files[0]:
                    main_file = py_files[0]
                    print(f"   Iniciando: {main_file}")
                    start_cmd = f"cd /opt/bioql/workflow_server && nohup /opt/bioql/venv/bin/python {main_file.split('/')[-1]} > /tmp/workflow_server.log 2>&1 &"
                    stdin, stdout, stderr = ssh.exec_command(start_cmd)
                    stdout.channel.recv_exit_status()
                    print(f"   ✅ Comando ejecutado")
                    time.sleep(2)
            else:
                print(f"   ⚠️  No se encontró directorio workflow_server")

        # Reiniciar Quantum Graphs (9000) si está offline
        if "9000" in offline_services:
            print(f"\n🔄 Reiniciando Quantum Graphs Server (9000)...")
            stdin, stdout, stderr = ssh.exec_command("ls -la /opt/bioql/quantum_graph/")
            graph_files = stdout.read().decode()
            if graph_files:
                print(f"   Archivos encontrados:")
                print(f"   {graph_files[:300]}")

                # Buscar script de inicio
                stdin, stdout, stderr = ssh.exec_command(
                    "find /opt/bioql/quantum_graph -name '*api*.py' -o -name '*server*.py' | head -5"
                )
                py_files = stdout.read().decode().strip().split("\n")

                if py_files and py_files[0]:
                    main_file = py_files[0]
                    print(f"   Iniciando: {main_file}")
                    start_cmd = f"cd /opt/bioql/quantum_graph && nohup /opt/bioql/venv/bin/python {main_file.split('/')[-1]} > /tmp/quantum_graph.log 2>&1 &"
                    stdin, stdout, stderr = ssh.exec_command(start_cmd)
                    stdout.channel.recv_exit_status()
                    print(f"   ✅ Comando ejecutado")
                    time.sleep(2)

        # Reiniciar Quantum Docking (8100) si está offline
        if "8100" in offline_services:
            print(f"\n🔄 Reiniciando Quantum Docking Server (8100)...")
            # Este usa Gunicorn, verificar systemd
            stdin, stdout, stderr = ssh.exec_command(
                "systemctl status bioql-docking 2>&1 | head -15"
            )
            status = stdout.read().decode()
            print(f"   Status:")
            print(f"   {status[:400]}")

            if "inactive" in status or "failed" in status:
                print(f"   Reiniciando servicio systemd...")
                stdin, stdout, stderr = ssh.exec_command("systemctl restart bioql-docking")
                stdout.channel.recv_exit_status()
                print(f"   ✅ Servicio reiniciado")
                time.sleep(2)

    # 5. Verificación final
    print(f"\n{'='*80}")
    print(f"✅ PASO 5: Verificación final")
    print(f"{'='*80}")

    time.sleep(3)

    for port, info in services.items():
        stdin, stdout, stderr = ssh.exec_command(f"lsof -ti:{port}")
        pid = stdout.read().decode().strip()

        if pid:
            print(f"✅ {info['name']} (Port {port}) - PID: {pid}")
        else:
            print(f"❌ {info['name']} (Port {port}) - STILL OFFLINE")

    ssh.close()

    print(f"\n{'='*80}")
    print(f"✅ VERIFICACIÓN COMPLETA")
    print(f"{'='*80}")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
