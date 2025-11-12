#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar configuración de Stripe en el servidor
"""
import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("💳 VERIFICANDO CONFIGURACIÓN DE STRIPE")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # 1. Verificar variables de entorno de Stripe
    print(f"\n🔐 PASO 1: Variables de entorno de Stripe")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep 'bioql_auth_server_stripe.py' | grep -v grep"
    )
    process_info = stdout.read().decode()
    print("Proceso corriendo:")
    print(process_info[:500])

    # 2. Ver logs del servidor para mensajes de Stripe
    print(f"\n📋 PASO 2: Últimos logs del servidor")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("tail -50 /tmp/bioql_auth_server.log | grep -i stripe")
    stripe_logs = stdout.read().decode()
    if stripe_logs:
        print("Logs de Stripe:")
        print(stripe_logs)
    else:
        print("⚠️  No se encontraron mensajes de Stripe en los logs")
        print("\nÚltimas 20 líneas del log completo:")
        stdin, stdout, stderr = ssh.exec_command("tail -20 /tmp/bioql_auth_server.log")
        print(stdout.read().decode())

    # 3. Verificar que las variables de entorno estén configuradas
    print(f"\n🔍 PASO 3: Verificar variables en el script de inicio")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "grep -i 'STRIPE' /opt/bioql/auth_server/bioql_auth_server_stripe.py | head -10"
    )
    stripe_vars = stdout.read().decode()
    print("Variables de Stripe en el código:")
    print(stripe_vars)

    # 4. Verificar usuario con API key
    print(f"\n👤 PASO 4: Verificar usuario con API key de test")
    print("-" * 80)

    # Conectar a la base de datos SQLite
    stdin, stdout, stderr = ssh.exec_command(
        """
sqlite3 /opt/bioql/auth_server/users.db "SELECT id, email, name, stripe_customer_id, stripe_setup_complete FROM users WHERE api_key = '__BIOQL_REDACTED__';"
"""
    )
    user_info = stdout.read().decode()

    if user_info.strip():
        print("✅ Usuario encontrado:")
        print(user_info)

        # Parsear la info
        fields = user_info.strip().split("|")
        if len(fields) >= 4:
            user_id, email, name, stripe_customer_id = fields[0], fields[1], fields[2], fields[3]

            if stripe_customer_id:
                print(f"\n✅ Usuario TIENE stripe_customer_id: {stripe_customer_id}")
            else:
                print(f"\n⚠️  Usuario NO TIENE stripe_customer_id")
                print(f"   User ID: {user_id}")
                print(f"   Email: {email}")
                print(f"\n💡 Solución: Crear Stripe customer para este usuario")
    else:
        print("❌ Usuario no encontrado en la base de datos")

    # 5. Verificar todos los usuarios y su estado de Stripe
    print(f"\n📊 PASO 5: Estado de Stripe de todos los usuarios")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        """
sqlite3 /opt/bioql/auth_server/users.db "SELECT id, email, stripe_customer_id, stripe_setup_complete, balance FROM users LIMIT 10;"
"""
    )
    all_users = stdout.read().decode()
    if all_users.strip():
        print("Usuarios en el sistema:")
        print(all_users)
    else:
        print("⚠️  No se encontraron usuarios")

    # 6. Verificar si Stripe está habilitado en el servidor
    print(f"\n🔍 PASO 6: Verificar integración de Stripe en startup")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "grep -A 2 'Stripe integration' /tmp/bioql_auth_server.log | tail -5"
    )
    startup_logs = stdout.read().decode()
    if startup_logs:
        print("Logs de inicio:")
        print(startup_logs)
    else:
        print("⚠️  No se encontraron logs de integración de Stripe")

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ VERIFICACIÓN COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
