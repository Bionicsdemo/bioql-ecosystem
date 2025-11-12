#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar y actualizar configuración de Nginx para proxy /api/*
"""
import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔍 VERIFICANDO CONFIGURACIÓN DE NGINX")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # 1. Buscar archivos de configuración de Nginx
    print(f"\n📁 PASO 1: Archivos de configuración Nginx")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("ls -la /etc/nginx/sites-enabled/")
    print(stdout.read().decode())

    # 2. Ver configuración principal de bioql
    print(f"\n📄 PASO 2: Configuración de bioql")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "cat /etc/nginx/sites-enabled/bioql 2>/dev/null || cat /etc/nginx/sites-available/bioql 2>/dev/null"
    )
    config = stdout.read().decode()
    if config:
        print(config[:2000])  # Primeros 2000 chars
    else:
        print("⚠️  No se encontró configuración bioql")

    # 3. Verificar si ya existe proxy para /api/
    print(f"\n🔍 PASO 3: Buscar proxy para /api/")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "grep -n 'location /api' /etc/nginx/sites-enabled/* 2>/dev/null"
    )
    api_proxy = stdout.read().decode()
    if api_proxy:
        print("✅ Proxy /api/ encontrado:")
        print(api_proxy)
    else:
        print("❌ NO se encontró proxy para /api/")
        print("   Necesitamos agregarlo")

    # 4. Verificar puertos en configuración
    print(f"\n🔍 PASO 4: Puertos configurados en Nginx")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "grep -n 'proxy_pass.*:' /etc/nginx/sites-enabled/* 2>/dev/null | head -20"
    )
    print(stdout.read().decode())

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ VERIFICACIÓN COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
