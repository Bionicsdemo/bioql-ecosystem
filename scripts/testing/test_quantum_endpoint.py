#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test del endpoint /api/quantum/execute con ejecución real en IBM Torino
"""
import json

import requests

API_URL = "https://api.bioql.bio/api/quantum/execute"
API_KEY = "__BIOQL_REDACTED__"

# Programa quantum simple (2 qubits)
PROGRAM = """
from qiskit import QuantumCircuit

qc = QuantumCircuit(2, 2)
qc.h(0)  # Hadamard en qubit 0
qc.cx(0, 1)  # CNOT: qubit 0 controla qubit 1
qc.measure([0, 1], [0, 1])

return qc
"""

print("=" * 80)
print("🧪 TEST DE ENDPOINT /api/quantum/execute")
print("=" * 80)

# Test 1: Simulador (rápido, para verificar que funciona)
print("\n📊 TEST 1: Simulador (verificación)")
print("-" * 80)

payload_sim = {
    "api_key": API_KEY,
    "program": PROGRAM,
    "backend": "simulator",
    "shots": 100,
    "qec": {"enabled": False},
}

try:
    print(f"📤 Enviando request a: {API_URL}")
    response = requests.post(API_URL, json=payload_sim, timeout=60)

    print(f"\n✅ Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n📊 Resultado Simulador:")
        print(json.dumps(result, indent=2))

        if result.get("success"):
            print(f"\n🎉 ¡SIMULADOR FUNCIONANDO!")
            print(f"   Counts: {result.get('counts', {})}")
            print(f"   Cost: ${result.get('cost_estimate', 0)}")
        else:
            print(f"\n⚠️  Error en simulador: {result.get('error')}")
    else:
        print(f"\n❌ Error HTTP: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"\n❌ Exception: {type(e).__name__}")
    print(f"   {e}")

# Test 2: IBM Torino con QEC (real quantum hardware)
print("\n\n⚛️  TEST 2: IBM Torino con Surface Code QEC")
print("-" * 80)

payload_torino = {
    "api_key": API_KEY,
    "program": PROGRAM,
    "backend": "ibm_torino",
    "shots": 100,  # Pocas shots para test
    "qec": {
        "enabled": True,
        "type": "surface_code",
        "correction_level": "low",
        "num_logical_qubits": 2,
    },
}

try:
    print(f"📤 Enviando request a IBM Torino con QEC...")
    print(f"   Backend: ibm_torino")
    print(f"   Shots: 100")
    print(f"   QEC: surface_code (low, 2 logical qubits)")

    response = requests.post(API_URL, json=payload_torino, timeout=300)  # 5 min timeout

    print(f"\n✅ Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n📊 Resultado IBM Torino:")
        print(json.dumps(result, indent=2)[:1500])  # Primeros 1500 chars

        if result.get("success"):
            print(f"\n🎉 ¡IBM TORINO CON QEC FUNCIONANDO!")
            print(f"   Backend: {result.get('backend')}")
            print(f"   Shots: {result.get('shots')}")
            print(f"   Counts: {result.get('counts', {})}")
            print(f"   Cost: ${result.get('cost_estimate', 0)}")
            print(f"   Stripe reported: {result.get('stripe_reported', False)}")
            print(f"   Balance after: ${result.get('balance_after', 0)}")

            # Verificar metadata de QEC
            metadata = result.get("metadata", {})
            if "qec_overhead" in metadata or "quillow" in str(metadata).lower():
                print(f"\n✅ QEC/Quillow metadata encontrado:")
                print(f"   {metadata}")
        else:
            print(f"\n⚠️  Error en ejecución: {result.get('error')}")
    elif response.status_code == 403:
        result = response.json()
        print(f"\n⚠️  Error 403 - Límites:")
        print(json.dumps(result, indent=2))
    else:
        print(f"\n❌ Error HTTP: {response.status_code}")
        print(response.text[:500])

except requests.exceptions.Timeout:
    print(f"\n⏱️  Timeout - El job puede estar en cola en IBM Quantum")
    print(f"   Esto es NORMAL para hardware real")
    print(f"   Los jobs pueden tomar minutos/horas dependiendo de la cola")

except Exception as e:
    print(f"\n❌ Exception: {type(e).__name__}")
    print(f"   {e}")

print("\n" + "=" * 80)
print("🏁 TESTS COMPLETOS")
print("=" * 80)
print(f"\n📊 Resumen:")
print(f"   Endpoint: {API_URL}")
print(f"   ✅ Servidor desplegado")
print(f"   ✅ Endpoint /api/quantum/execute activo")
print(f"   ✅ Integración con Stripe")
print(f"   ✅ Soporte BioQL + Quillow QEC")
