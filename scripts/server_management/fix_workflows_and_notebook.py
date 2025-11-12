#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Arreglar Workflows health endpoint y verificar Lab Notebook
"""
import time

import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔧 ARREGLANDO WORKFLOWS Y VERIFICANDO LAB NOTEBOOK")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"\n📡 Conectando como {USERNAME}@{SERVER}...")
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)
    print(f"✅ Conectado")

    # ============================================================================
    # 1. WORKFLOWS SERVER (Puerto 5002)
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"🔍 PASO 1: Investigar Workflows Server")
    print(f"{'='*80}")

    # Ver estructura de workflow_server
    stdin, stdout, stderr = ssh.exec_command("ls -la /opt/bioql/workflow_server/")
    workflow_files = stdout.read().decode()
    print(f"\n📁 Archivos en /opt/bioql/workflow_server/:")
    print(workflow_files[:800])

    # Buscar archivos Python
    stdin, stdout, stderr = ssh.exec_command("find /opt/bioql/workflow_server -name '*.py' -type f")
    py_files = stdout.read().decode().strip().split("\n")

    print(f"\n📄 Archivos Python encontrados:")
    for f in py_files[:10]:
        if f:
            print(f"   - {f}")

    # Ver proceso corriendo
    stdin, stdout, stderr = ssh.exec_command("lsof -ti:5002")
    pid = stdout.read().decode().strip()

    if pid:
        print(f"\n✅ Workflows corriendo en PID: {pid}")

        # Ver qué archivo está ejecutando
        stdin, stdout, stderr = ssh.exec_command(f"ps -p {pid} -o cmd --no-headers")
        cmd = stdout.read().decode().strip()
        print(f"   Comando: {cmd}")

        # Extraer el archivo principal
        if ".py" in cmd:
            main_file = [part for part in cmd.split() if part.endswith(".py")][0]
            print(f"   Archivo principal: {main_file}")

            # Leer el archivo para ver si tiene endpoint /health
            stdin, stdout, stderr = ssh.exec_command(f"grep -n '/health' {main_file}")
            health_routes = stdout.read().decode()

            if health_routes:
                print(f"\n✅ Endpoints /health encontrados:")
                print(health_routes)
            else:
                print(f"\n⚠️  NO hay endpoint /health definido")
                print(f"   Voy a leer el archivo para ver la estructura...")

                # Leer primeras 100 líneas
                stdin, stdout, stderr = ssh.exec_command(f"head -100 {main_file}")
                content = stdout.read().decode()
                print(f"\n📄 Primeras líneas del archivo:")
                print(content[:1000])

    else:
        print(f"\n❌ Workflows NO está corriendo en puerto 5002")

    # ============================================================================
    # 2. LAB NOTEBOOK SERVER
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"🔍 PASO 2: Buscar Lab Notebook Server")
    print(f"{'='*80}")

    # Buscar directorio lab_notebook
    stdin, stdout, stderr = ssh.exec_command(
        "find /opt/bioql /home/bioql -name '*lab*notebook*' -o -name '*notebook*' -type d 2>/dev/null | head -10"
    )
    notebook_dirs = stdout.read().decode().strip().split("\n")

    print(f"\n📁 Directorios encontrados:")
    for d in notebook_dirs:
        if d and "lab" in d.lower():
            print(f"   - {d}")

    # Verificar si existe /opt/bioql/lab_notebook
    stdin, stdout, stderr = ssh.exec_command("ls -la /opt/bioql/lab_notebook/ 2>/dev/null")
    notebook_files = stdout.read().decode()

    if notebook_files and "total" in notebook_files:
        print(f"\n✅ Lab Notebook encontrado en /opt/bioql/lab_notebook/")
        print(notebook_files[:600])

        # Buscar archivos Python
        stdin, stdout, stderr = ssh.exec_command(
            "find /opt/bioql/lab_notebook -name '*.py' -type f | head -10"
        )
        py_files = stdout.read().decode().strip().split("\n")

        print(f"\n📄 Archivos Python:")
        for f in py_files[:10]:
            if f:
                print(f"   - {f}")

        # Buscar si hay algún servidor corriendo
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i notebook | grep -v grep")
        notebook_processes = stdout.read().decode()

        if notebook_processes:
            print(f"\n✅ Procesos relacionados con notebook:")
            print(notebook_processes[:500])
        else:
            print(f"\n⚠️  No hay procesos de notebook corriendo")

    else:
        print(f"\n⚠️  No se encontró /opt/bioql/lab_notebook/")

    # ============================================================================
    # 3. Ver todos los puertos escuchando
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"📡 PASO 3: Todos los puertos escuchando")
    print(f"{'='*80}")

    stdin, stdout, stderr = ssh.exec_command(
        "ss -tulpn | grep LISTEN | grep python | sort -t: -k2 -n"
    )
    ports = stdout.read().decode()
    print(ports[:1500])

    ssh.close()

    print(f"\n{'='*80}")
    print(f"✅ INVESTIGACIÓN COMPLETA")
    print(f"{'='*80}")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
