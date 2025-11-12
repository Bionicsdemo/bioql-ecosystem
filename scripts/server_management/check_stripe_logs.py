#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar logs del servidor para ver errores de Stripe reporting
"""
import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔍 VERIFICANDO LOGS DE STRIPE REPORTING")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # Ver últimos 100 líneas del log
    print(f"\n📋 Últimas líneas del log (buscando stripe_reported):")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "tail -100 /tmp/bioql_auth_server.log | grep -A 5 -B 5 -i 'stripe\\|report\\|usage_log'"
    )
    logs = stdout.read().decode()

    if logs:
        print(logs)
    else:
        print("⚠️  No se encontraron mensajes de Stripe")
        print("\nÚltimas 30 líneas completas:")
        stdin, stdout, stderr = ssh.exec_command("tail -30 /tmp/bioql_auth_server.log")
        print(stdout.read().decode())

    # Verificar usage_logs en la database
    print(f"\n📊 Últimos 5 registros en usage_logs:")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        """
sqlite3 /opt/bioql/auth_server/users.db "SELECT id, user_id, usage_type, shots, backend, cost, success, stripe_reported FROM usage_logs ORDER BY id DESC LIMIT 5;"
"""
    )
    usage_logs = stdout.read().decode()
    if usage_logs:
        print("ID|UserID|Type|Shots|Backend|Cost|Success|StripeReported")
        print(usage_logs)
    else:
        print("⚠️  No hay registros")

    # Verificar el usuario específico
    print(f"\n👤 Usuario con API key:")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        """
sqlite3 /opt/bioql/auth_server/users.db "SELECT id, email, stripe_customer_id, balance FROM users WHERE api_key = '__BIOQL_REDACTED__';"
"""
    )
    user = stdout.read().decode()
    if user:
        print(user)
        fields = user.strip().split("|")
        if len(fields) >= 3:
            user_id, email, stripe_customer_id = fields[0], fields[1], fields[2]

            if stripe_customer_id and stripe_customer_id != "None":
                print(f"\n✅ Usuario TIENE stripe_customer_id: {stripe_customer_id}")

                # Verificar si stripe_integration está activo
                print(f"\n🔍 Verificando stripe_integration en el código:")
                stdin, stdout, stderr = ssh.exec_command(
                    "grep -n 'stripe_integration =' /opt/bioql/auth_server/bioql_auth_server_stripe.py | head -5"
                )
                print(stdout.read().decode())
            else:
                print(f"\n⚠️  Usuario NO TIENE stripe_customer_id válido")

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ VERIFICACIÓN COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
