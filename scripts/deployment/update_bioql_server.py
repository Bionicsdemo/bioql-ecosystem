#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Actualizar el servidor BioQL en api.bioql.bio
Agrega endpoint de ejecución quantum sin romper funcionalidad existente
"""
import os
import sys

import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔍 VERIFICANDO SERVIDOR BioQL en /opt/bioql/")
print("=" * 80)

try:
    # Conectar
    print(f"\n📡 Conectando a {SERVER}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)
    print(f"✅ Conectado")

    # 1. Verificar estructura /opt/bioql/
    print(f"\n📁 PASO 1: Estructura de /opt/bioql/")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("ls -la /opt/bioql/")
    print(stdout.read().decode())

    # 2. Ver el servidor actual (primeras 100 líneas)
    print(f"\n📄 PASO 2: Servidor actual (bioql_auth_server_stripe.py)")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("head -100 /opt/bioql/bioql_auth_server_stripe.py")
    content = stdout.read().decode()
    print(content)
    print("...")

    # 3. Buscar BioQL framework
    print(f"\n🔍 PASO 3: Buscar BioQL framework")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        """
find /opt /home /root -name "bioql" -type d 2>/dev/null | grep -E "(Spectrix_framework|bioql)" | head -10
"""
    )
    bioql_paths = stdout.read().decode()
    print(bioql_paths)

    # 4. Verificar imports necesarios en el servidor
    print(f"\n📦 PASO 4: Verificar imports en servidor actual")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "grep -E '^(import|from)' /opt/bioql/bioql_auth_server_stripe.py | head -30"
    )
    imports = stdout.read().decode()
    print(imports)

    # 5. Contar líneas del servidor
    print(f"\n📊 PASO 5: Tamaño del servidor actual")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("wc -l /opt/bioql/bioql_auth_server_stripe.py")
    print(stdout.read().decode())

    # 6. Buscar si ya tiene endpoint de ejecución
    print(f"\n🔍 PASO 6: Buscar endpoints existentes")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "grep -n '@app.route' /opt/bioql/bioql_auth_server_stripe.py"
    )
    routes = stdout.read().decode()
    print(routes)

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ VERIFICACIÓN COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
