#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test rápido de ejecución en IBM Torino via BioQL
"""

import sys

sys.path.insert(0, "/Users/heinzjungbluth/Desktop/Quillow")

from quillow.backends.bioql_backend import BioQLBackend, BioQLConfig
from quillow.core import RotatedSurfaceCode
from quillow.core.noise_models import DepolarizingNoise

API_KEY = "__BIOQL_REDACTED__"

print("=" * 70)
print("TEST: Quillow + BioQL + IBM Torino")
print("=" * 70)

# 1. Validar API key
print("\n1. Validando API key...")
config = BioQLConfig(api_key=API_KEY, base_url="https://api.bioql.bio")
backend = BioQLBackend(config, qec_distance=5)

if not backend.validate_api_key():
    print("❌ API key inválida")
    sys.exit(1)

print("✅ API key válida")

# 2. Verificar balance
print("\n2. Verificando balance...")
quota = backend.check_quota()
print(f"   Balance: ${quota.get('balance', 0):,.2f}")
print(f"   Tier: {quota.get('tier', 'N/A')}")

# 3. Construir circuito QEC
print("\n3. Construyendo circuito QEC d=5...")
surface_code = RotatedSurfaceCode(distance=5, rounds=5)
noise_model = DepolarizingNoise(error_rate=0.001)
circuit = surface_code.build_stim_circuit(noise_model=noise_model)

print(f"   Qubits: {circuit.num_qubits}")
print(f"   Detectores: {circuit.num_detectors}")

# 4. Ejecutar en IBM Torino
print("\n4. Ejecutando en IBM Torino...")
print("   ⚠️  ESTO EJECUTARÁ EN HARDWARE REAL")
print("   Backend: ibm_torino")
print("   Shots: 100 (para testing)")
print("   Costo estimado: ~$300")

try:
    result = backend.execute(circuit, shots=100, backend="ibm_torino")

    print("\n✅ Ejecución completada!")
    print(f"   Backend: {result.backend_name}")
    print(f"   Syndromes shape: {result.syndromes.shape}")
    print(f"   QEC enabled: {result.metadata.get('qec_enabled', False)}")
    print(f"   Logical error rate: {result.metadata.get('logical_error_rate', 'N/A')}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 70)
