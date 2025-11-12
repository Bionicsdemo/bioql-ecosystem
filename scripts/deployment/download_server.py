#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Descargar el servidor actual para analizarlo
"""
import paramiko
from scp import SCPClient

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("📥 DESCARGANDO SERVIDOR ACTUAL")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # Primero, buscar dónde está el archivo
    print(f"\n🔍 Buscando bioql_auth_server_stripe.py...")
    stdin, stdout, stderr = ssh.exec_command(
        "find /opt/bioql /home/bioql -name '*auth_server*.py' 2>/dev/null"
    )
    files = stdout.read().decode().strip().split("\n")

    print(f"   Archivos encontrados:")
    for f in files:
        if f.strip():
            print(f"   - {f}")

    # Descargar con SCP
    with SCPClient(ssh.get_transport()) as scp:
        for remote_file in files:
            if remote_file.strip() and "auth_server" in remote_file:
                local_file = f"/Users/heinzjungbluth/Desktop/server_{remote_file.split('/')[-1]}"
                print(f"\n📥 Descargando: {remote_file}")
                print(f"   → {local_file}")
                try:
                    scp.get(remote_file, local_file)
                    print(f"   ✅ Descargado")

                    # Contar líneas
                    with open(local_file, "r") as f:
                        lines = len(f.readlines())
                    print(f"   📊 {lines} líneas")
                except Exception as e:
                    print(f"   ⚠️  Error: {e}")

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ DESCARGA COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
