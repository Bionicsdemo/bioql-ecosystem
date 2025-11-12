#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar estado completo de todos los servidores BioQL
"""
import json

import paramiko

print("=" * 80)
print("🔍 VERIFICANDO SERVIDORES BioQL")
print("=" * 80)

# Conectar a api.bioql.bio
hostname = "api.bioql.bio"
username = "bioql"
password = "P31e27r12u1@HJG"

print(f"\n📡 Conectando a {hostname}...")

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password, timeout=10)

    print(f"✅ Conectado a {hostname}\n")

    # 1. Verificar servicios activos
    print("🔍 PASO 1: Servicios systemd activos")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "systemctl list-units --type=service --state=running | grep bioql"
    )
    output = stdout.read().decode()
    if output:
        print(output)
    else:
        print("⚠️  No se encontraron servicios bioql activos")

    # 2. Verificar procesos Python
    print("\n🔍 PASO 2: Procesos Python de BioQL")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep -E '(backend|gunicorn|bioql)' | grep -v grep"
    )
    output = stdout.read().decode()
    if output:
        for line in output.split("\n")[:10]:  # Primeras 10 líneas
            if line.strip():
                print(line)
    else:
        print("⚠️  No se encontraron procesos activos")

    # 3. Verificar puertos escuchando
    print("\n🔍 PASO 3: Puertos activos")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "sudo netstat -tulpn 2>/dev/null | grep LISTEN | grep -E '(5001|5002|8100)' || ss -tulpn | grep LISTEN | grep -E '(5001|5002|8100)'"
    )
    output = stdout.read().decode()
    if output:
        print(output)
    else:
        print("⚠️  No se encontraron puertos 5001, 5002, 8100 activos")

    # 4. Verificar logs recientes
    print("\n🔍 PASO 4: Logs recientes de quantum-docking")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "tail -20 /var/log/bioql/quantum-docking.log 2>/dev/null || tail -20 /var/log/bioql/*.log 2>/dev/null | head -20"
    )
    output = stdout.read().decode()
    if output:
        print(output)
    else:
        print("⚠️  No se encontraron logs")

    # 5. Verificar el backend de quantum-docking
    print("\n🔍 PASO 5: Backend quantum-docking")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "ls -la /home/bioql/bioql_quillow_docking/web_interface/*.py 2>/dev/null | head -10"
    )
    output = stdout.read().decode()
    if output:
        print(output)
    else:
        print("⚠️  No se encontró el directorio")

    # 6. Test local del endpoint
    print("\n🔍 PASO 6: Test local del endpoint")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command(
        "curl -s http://localhost:8100/api/health 2>/dev/null || curl -s http://localhost:5001/api/health 2>/dev/null || curl -s http://localhost:5002/api/health 2>/dev/null"
    )
    output = stdout.read().decode()
    if output:
        try:
            health = json.loads(output)
            print(json.dumps(health, indent=2))
        except:
            print(output)
    else:
        print("⚠️  No responde en localhost")

    ssh.close()
    print("\n" + "=" * 80)
    print("✅ Verificación completa")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
