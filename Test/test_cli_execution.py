#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test de ejecución usando BioQL con remote execution
"""
import sys

sys.path.insert(0, "/Users/heinzjungbluth/Desktop/Spectrix_BioQL/Spectrix_framework")

from bioql import quantum

api_key = "__BIOQL_REDACTED__"

print("=" * 80)
print("🧬 Test: BioQL Remote Execution")
print("=" * 80)
print("\n📊 Intentando ejecutar en IBM Torino via API...")
print("   (Sin IBM token local, debería usar remote execution)")

result = quantum(
    "Create a 2-qubit Bell state",
    backend="ibm_torino",
    shots=100,
    api_key=api_key,
    error_correction="surface_code",
    correction_level="low",
    num_logical_qubits=2,
)

print(f"\n✅ Resultado:")
print(f"   Success: {result.success}")
print(f"   Backend: {getattr(result, 'backend_name', 'unknown')}")

if not result.success:
    print(f"   Error: {getattr(result, 'error', 'Unknown')}")

print("\n" + "=" * 80)
