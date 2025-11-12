#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar qué configuración se usa para HTTPS
"""
import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔍 VERIFICANDO CONFIGURACIÓN HTTPS")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # 1. Ver configuración bioql (que tiene HTTPS)
    print(f"\n📄 Archivo: /etc/nginx/sites-available/bioql (primeras 200 líneas)")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("head -200 /etc/nginx/sites-available/bioql")
    print(stdout.read().decode())

    # 2. Buscar server_name + listen 443
    print(f"\n🔍 Servidores HTTPS en api.bioql.bio:")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "grep -A 5 'listen.*443' /etc/nginx/sites-enabled/* | grep -A 5 'api.bioql.bio'"
    )
    print(stdout.read().decode()[:1500])

    ssh.close()

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
