#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Desplegar servidor BioQL actualizado con endpoint de ejecución quantum
"""
import time

import paramiko
from scp import SCPClient

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"
REMOTE_PATH = "/opt/bioql/auth_server"
LOCAL_FILE = "/Users/heinzjungbluth/Desktop/server_bioql_auth_server_stripe.py"

print("=" * 80)
print("🚀 DESPLEGANDO SERVIDOR BioQL ACTUALIZADO")
print("=" * 80)

try:
    # Conectar
    print(f"\n📡 Conectando a {SERVER}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)
    print(f"✅ Conectado")

    # 1. Hacer backup
    print(f"\n💾 PASO 1: Haciendo backup del servidor actual")
    print("-" * 80)
    backup_cmd = f"cp {REMOTE_PATH}/bioql_auth_server_stripe.py {REMOTE_PATH}/bioql_auth_server_stripe.py.backup_$(date +%Y%m%d_%H%M%S)"
    stdin, stdout, stderr = ssh.exec_command(backup_cmd)
    exit_status = stdout.channel.recv_exit_status()

    if exit_status == 0:
        print(f"✅ Backup creado")
    else:
        print(f"⚠️  Backup falló: {stderr.read().decode()}")

    # Verificar backup
    stdin, stdout, stderr = ssh.exec_command(f"ls -la {REMOTE_PATH}/*.backup* | tail -1")
    print(f"   {stdout.read().decode().strip()}")

    # 2. Subir archivo actualizado
    print(f"\n📤 PASO 2: Subiendo archivo actualizado")
    print("-" * 80)
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(LOCAL_FILE, f"{REMOTE_PATH}/bioql_auth_server_stripe.py")
    print(f"✅ Archivo subido: bioql_auth_server_stripe.py")

    # 3. Verificar el archivo
    print(f"\n🔍 PASO 3: Verificando archivo subido")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(f"wc -l {REMOTE_PATH}/bioql_auth_server_stripe.py")
    lines = stdout.read().decode().strip()
    print(f"   Líneas: {lines}")

    # Verificar que tiene el nuevo endpoint
    stdin, stdout, stderr = ssh.exec_command(
        f"grep -n '/api/quantum/execute' {REMOTE_PATH}/bioql_auth_server_stripe.py"
    )
    endpoint_check = stdout.read().decode().strip()
    if endpoint_check:
        print(f"✅ Endpoint /api/quantum/execute encontrado:")
        print(f"   {endpoint_check}")
    else:
        print(f"❌ Endpoint /api/quantum/execute NO encontrado!")

    # 4. Matar proceso actual
    print(f"\n🔄 PASO 4: Reiniciando servidor")
    print("-" * 80)

    # Encontrar PID
    stdin, stdout, stderr = ssh.exec_command("pgrep -f 'bioql_auth_server_stripe.py'")
    old_pid = stdout.read().decode().strip()

    if old_pid:
        print(f"   PID actual: {old_pid}")
        stdin, stdout, stderr = ssh.exec_command(f"kill {old_pid}")
        stdout.channel.recv_exit_status()
        print(f"✅ Servidor antiguo detenido")
        time.sleep(2)
    else:
        print(f"⚠️  No se encontró proceso corriendo")

    # 5. Iniciar nuevo servidor
    print(f"\n🚀 PASO 5: Iniciando servidor actualizado")
    print("-" * 80)

    start_cmd = f"""
cd {REMOTE_PATH} && \
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
    print(f"✅ Comando de inicio ejecutado")

    # Esperar a que el servidor inicie
    time.sleep(4)

    # 6. Verificar que el servidor está corriendo
    print(f"\n🔍 PASO 6: Verificando servidor")
    print("-" * 80)

    # Verificar proceso
    stdin, stdout, stderr = ssh.exec_command("pgrep -f 'bioql_auth_server_stripe.py'")
    new_pid = stdout.read().decode().strip()

    if new_pid:
        print(f"✅ Servidor corriendo")
        print(f"   PID: {new_pid}")
    else:
        print(f"❌ Servidor NO está corriendo")
        print(f"\n📋 Últimas líneas del log:")
        stdin, stdout, stderr = ssh.exec_command("tail -30 /tmp/bioql_auth_server.log")
        print(stdout.read().decode())

    # Verificar puerto
    stdin, stdout, stderr = ssh.exec_command("ss -tulpn | grep :5001 | grep LISTEN")
    port_check = stdout.read().decode().strip()
    if port_check:
        print(f"✅ Puerto 5001 escuchando:")
        print(f"   {port_check}")
    else:
        print(f"⚠️  Puerto 5001 NO está escuchando")

    ssh.close()

    # 7. Test del endpoint desde fuera del servidor
    print(f"\n🧪 PASO 7: Testeando endpoint /health")
    print("-" * 80)
    import requests

    time.sleep(2)

    try:
        response = requests.get(f"https://{SERVER}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Health check OK")
            import json

            print(f"   {json.dumps(response.json(), indent=2)}")
        else:
            print(f"⚠️  Health check HTTP {response.status_code}")
            print(f"   {response.text[:500]}")
    except Exception as e:
        print(f"❌ Health check falló: {e}")

    print("\n" + "=" * 80)
    print("✅ DESPLIEGUE COMPLETO")
    print("=" * 80)
    print(f"\n📊 Endpoints disponibles:")
    print(f"   GET  https://{SERVER}/health")
    print(f"   POST https://{SERVER}/api/quantum/execute  ← NUEVO!")
    print(f"   POST https://{SERVER}/auth/validate")
    print(f"   POST https://{SERVER}/billing/record-usage")
    print(f"\n📝 Ver logs:")
    print(f"   ssh {USERNAME}@{SERVER}")
    print(f"   tail -f /tmp/bioql_auth_server.log")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
