#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Ejecutar REAL quantum docking en IBM Torino
Directamente en el servidor api.bioql.bio via SSH
"""
import time

import paramiko

print("=" * 80)
print("⚛️  EJECUTANDO EN IBM TORINO (Servidor Real)")
print("=" * 80)

# Script a ejecutar en el servidor
remote_script = """#!/bin/bash
cd /tmp
cat > quantum_test_torino.py << 'PYTHON_EOF'
import os
import sys

# Add BioQL to path
sys.path.insert(0, '/home/bioql/Spectrix_framework')

from bioql import quantum

# IBM token ya configurado en servidor
os.environ['IBM_QUANTUM_TOKEN'] = 'sKwyF9w532GA_7aXLvKjKr6h5UQrM26Mcpv3QYKbunAC'

api_key = '__BIOQL_REDACTED__'

print("="*80)
print("🧬 QUANTUM Docking - IBM Torino")
print("="*80)

# Execute on IBM Torino with QEC
result = quantum(
    "Create 4-qubit Bell state for molecular simulation",
    backend='ibm_torino',
    shots=100,  # Solo 100 shots para test rápido
    api_key=api_key,
    error_correction='surface_code',
    correction_level='low',
    num_logical_qubits=2,
)

print(f"\\nSuccess: {result.success}")

if result.success:
    print(f"Backend: {result.backend_name}")
    print(f"Shots: {result.shots}")

    if hasattr(result, 'counts') and result.counts:
        print(f"\\n🔢 Top 5 States:")
        sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
        for state, count in sorted_counts[:5]:
            print(f"   |{state}⟩: {count}")

    if hasattr(result, 'metadata'):
        meta = result.metadata
        if 'job_id' in meta:
            print(f"\\n🆔 IBM Job ID: {meta['job_id']}")
else:
    print(f"Error: {getattr(result, 'error', 'Unknown')}")

print("\\n" + "="*80)
PYTHON_EOF

# Ejecutar el script Python
python3 quantum_test_torino.py
"""

# Intentar conectar al servidor
servers_to_try = [
    ("api.bioql.bio", "bioql", "tu_password"),  # Necesitas el password correcto
]

for hostname, username, password in servers_to_try:
    print(f"\n🔗 Intentando conectar a {hostname}...")

    if password == "tu_password":
        print(f"⚠️  Necesitas configurar el password SSH correcto")
        print(f"   El servidor requiere autenticación")
        break

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, timeout=10)

        print(f"✅ Conectado a {hostname}")
        print(f"\n🚀 Ejecutando quantum docking en servidor...")
        print("-" * 80)

        # Ejecutar el script
        stdin, stdout, stderr = ssh.exec_command(remote_script, timeout=300)

        # Mostrar output en tiempo real
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line.strip())

        # Mostrar errores si los hay
        errors = stderr.read().decode()
        if errors:
            print("\n⚠️  Warnings/Errors:")
            print(errors)

        ssh.close()
        print("\n" + "=" * 80)
        print("✅ Ejecución completada")
        print("=" * 80)
        break

    except paramiko.AuthenticationException:
        print(f"❌ Autenticación fallida en {hostname}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

print("\n💡 Nota: Para ejecutar en IBM Torino necesitas:")
print("   1. Acceso SSH al servidor")
print("   2. BioQL instalado en el servidor")
print("   3. IBM Quantum token configurado")
print("   4. Cola de IBM Quantum puede tardar minutos/horas")
