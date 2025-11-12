#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Actualizar librería Stripe en el servidor
"""
import time

import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("⬆️  ACTUALIZANDO STRIPE EN EL SERVIDOR")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # 1. Verificar versión actual de Stripe
    print(f"\n📊 PASO 1: Versión actual de Stripe")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("/opt/bioql/venv/bin/pip show stripe")
    current_version = stdout.read().decode()
    print(current_version)

    # 2. Actualizar Stripe
    print(f"\n⬆️  PASO 2: Actualizando Stripe")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("/opt/bioql/venv/bin/pip install --upgrade stripe")
    upgrade_output = stdout.read().decode()
    print(upgrade_output[-500:])  # Últimas 500 chars

    # 3. Verificar nueva versión
    print(f"\n✅ PASO 3: Nueva versión de Stripe")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("/opt/bioql/venv/bin/pip show stripe")
    new_version = stdout.read().decode()
    print(new_version)

    # 4. Reiniciar el servidor
    print(f"\n🔄 PASO 4: Reiniciando servidor")
    print("-" * 80)

    # Matar proceso actual
    stdin, stdout, stderr = ssh.exec_command("pgrep -f 'bioql_auth_server_stripe.py'")
    old_pid = stdout.read().decode().strip()

    if old_pid:
        print(f"   Deteniendo PID: {old_pid}")
        stdin, stdout, stderr = ssh.exec_command(f"kill {old_pid}")
        stdout.channel.recv_exit_status()
        time.sleep(2)

    # Iniciar nuevo servidor
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
    print(f"✅ Servidor reiniciado")

    time.sleep(4)

    # 5. Verificar que está corriendo
    print(f"\n🔍 PASO 5: Verificando servidor")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("pgrep -f 'bioql_auth_server_stripe.py'")
    new_pid = stdout.read().decode().strip()

    if new_pid:
        print(f"✅ Servidor corriendo - PID: {new_pid}")
    else:
        print(f"❌ Servidor NO está corriendo")

    # 6. Verificar logs de Stripe
    print(f"\n📋 PASO 6: Verificar logs de Stripe")
    print("-" * 80)
    time.sleep(2)
    stdin, stdout, stderr = ssh.exec_command("tail -30 /tmp/bioql_auth_server.log | grep -i stripe")
    stripe_logs = stdout.read().decode()

    if stripe_logs:
        print("Logs de Stripe:")
        print(stripe_logs)

        if "Failed to setup meter" in stripe_logs:
            print("\n⚠️  ERROR: Stripe billing meters aún fallan")
            print("   Verificando versión de Stripe API...")
        elif "Stripe integration enabled" in stripe_logs:
            print("\n✅ Stripe integración OK!")
    else:
        print("⚠️  No hay logs de Stripe todavía")
        print("\nÚltimas 15 líneas del log:")
        stdin, stdout, stderr = ssh.exec_command("tail -15 /tmp/bioql_auth_server.log")
        print(stdout.read().decode())

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ ACTUALIZACIÓN COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
