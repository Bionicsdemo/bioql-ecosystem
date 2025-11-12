#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Ver configuración completa de bioql-api
"""
import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("📄 CONFIGURACIÓN DE NGINX bioql-api")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # Ver archivo bioql-api completo
    print(f"\n📄 Archivo: /etc/nginx/sites-available/bioql-api")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/bioql-api")
    config = stdout.read().decode()
    print(config)

    ssh.close()

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
