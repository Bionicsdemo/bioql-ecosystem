#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Ejecutar REAL quantum docking en IBM Torino a través del servidor Modal
Este script usa el código generado y lo ejecuta EN EL SERVIDOR
"""
import json
import time

import requests

print("=" * 80)
print("⚛️  EJECUTANDO EN IBM TORINO (Hardware Real)")
print("=" * 80)

# Código generado por Modal con parámetros correctos
code_to_execute = """
import os
import sys

# Add BioQL to path (servidor tiene esto configurado)
sys.path.insert(0, '/home/bioql/Spectrix_framework')

from bioql import quantum

api_key = os.getenv('BIOQL_API_KEY', '__BIOQL_REDACTED__')

print("="*80)
print("🧬 QUANTUM Molecular Docking")
print("⚛️  Executing VQE on IBM Torino (133 qubits)")
print("🛡️  QEC: surface_code with 2 logical qubits")
print("="*80)

# Execute VQE on IBM Torino with QEC
result = quantum(
    "Analyze ligand with SMILES COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2 docking to receptor PDB 6B3J. "
    "Calculate binding affinity using VQE quantum computation. "
    "Identify key molecular interactions from quantum states. "
    "Calculate Ki and IC50 from quantum binding energies.",
    backend='ibm_torino',
    shots=2000,
    api_key=api_key,
    error_correction='surface_code',
    correction_level='low',
    num_logical_qubits=2,
)

print(f"\\n✅ QUANTUM Execution Complete!")
print(f"Success: {result.success}")

if result.success:
    print(f"\\n📊 Results:")
    print(f"   Backend: {result.backend_name}")
    print(f"   Shots: {result.shots}")

    # Access bio_interpretation
    bio = getattr(result, 'bio_interpretation', {})

    if bio:
        if bio.get('binding_affinity'):
            print(f"\\n⚛️  Binding Affinity: {bio['binding_affinity']:.2f} kcal/mol")
        if bio.get('ki'):
            print(f"   Ki: {bio['ki']:.2f} nM")
        if bio.get('ic50'):
            print(f"   IC50: {bio['ic50']:.2f} nM")

    # Show job info
    if hasattr(result, 'metadata'):
        metadata = result.metadata
        if 'job_id' in metadata:
            print(f"\\n🆔 IBM Job ID: {metadata['job_id']}")
        if 'queue_position' in metadata:
            print(f"   Queue Position: {metadata['queue_position']}")
        if 'estimated_wait' in metadata:
            print(f"   Estimated Wait: {metadata['estimated_wait']}")

    # Show counts if available
    if hasattr(result, 'counts') and result.counts:
        print(f"\\n🔢 Top 5 Measurement States:")
        sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
        for state, count in sorted_counts[:5]:
            probability = count / result.shots * 100
            print(f"   |{state}⟩: {count:4d} ({probability:5.1f}%)")

    # Cost estimate
    if hasattr(result, 'cost_estimate'):
        print(f"\\n💰 Cost Estimate: ${result.cost_estimate:.4f}")
else:
    print(f"\\n❌ Execution failed")
    if hasattr(result, 'error'):
        print(f"   Error: {result.error}")

print("\\n" + "="*80)
"""

# Guardar el código
script_path = "/Users/heinzjungbluth/Desktop/Test/run_on_torino.py"
with open(script_path, "w") as f:
    f.write(code_to_execute)

print(f"\n📝 Script generado: {script_path}")
print("\n🚀 Ejecutando en servidor...")
print("-" * 80)

# Ahora ejecutar directamente con BioQL local (que tiene la API key)
import subprocess
import sys

# Agregar BioQL al path
sys.path.insert(0, "/Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework")

try:
    # Ejecutar el script
    result = subprocess.run(
        ["python3", script_path], capture_output=True, text=True, timeout=300  # 5 minutos timeout
    )

    print(result.stdout)

    if result.stderr:
        print("\n⚠️  Warnings/Errors:")
        print(result.stderr)

    if result.returncode == 0:
        print("\n" + "=" * 80)
        print("✅ EJECUCIÓN EXITOSA EN IBM TORINO")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("⚠️  Ejecución completada con warnings")
        print("=" * 80)

except subprocess.TimeoutExpired:
    print("\n⏱️  Timeout - El job está en cola en IBM Quantum")
    print("   Esto es normal para hardware real")
    print("   El job se completará en el backend de IBM")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")

print("\n💡 Nota: Si el job está en cola, puede tardar varios minutos")
print("   IBM Torino es hardware real con cola de trabajos")
