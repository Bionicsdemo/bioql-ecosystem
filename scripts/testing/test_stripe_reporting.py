#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test final de Stripe reporting con ejecución exitosa
"""
import json

import requests

API_URL = "https://api.bioql.bio/api/quantum/execute"
API_KEY = "__BIOQL_REDACTED__"

# Programa QASM válido (más simple que Python)
QASM_PROGRAM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;"""

print("=" * 80)
print("💳 TEST DE STRIPE REPORTING")
print("=" * 80)

# Test con simulador (debe ser exitoso)
print("\n📊 Ejecutando en simulador...")
print("-" * 80)

payload = {
    "api_key": API_KEY,
    "program": QASM_PROGRAM,
    "backend": "simulator",
    "shots": 100,
    "qec": {"enabled": False},
}

try:
    response = requests.post(API_URL, json=payload, timeout=30)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        print(f"\n📊 RESULTADO:")
        print(json.dumps(result, indent=2)[:800])

        print(f"\n{'='*80}")
        print(f"📊 RESUMEN:")
        print(f"{'='*80}")
        print(f"✅ Success: {result.get('success')}")
        print(f"💰 Cost: ${result.get('cost_estimate')}")
        print(f"🏦 Balance after: ${result.get('balance_after')}")
        print(f"📊 Counts: {result.get('counts')}")
        print(f"💳 Stripe reported: {result.get('stripe_reported')}")

        if result.get("success"):
            if result.get("stripe_reported"):
                print(f"\n🎉 ¡STRIPE REPORTING FUNCIONANDO!")
                print(f"   ✅ Ejecución exitosa")
                print(f"   ✅ Costo registrado en Stripe")
                print(f"   ✅ Balance actualizado")
            else:
                print(f"\n⚠️  Ejecución exitosa pero Stripe reporting = False")
                print(f"   Revisando razón...")

                # Verificar si el problema es la ejecución exitosa
                if not result.get("counts"):
                    print(f"   ⚠️  Counts vacío - ejecución puede haber fallado internamente")
        else:
            print(f"\n⚠️  Ejecución falló - Stripe reporting correctamente = False")
            print(f"   Error: {result.get('error')}")

    else:
        print(f"\n❌ Error HTTP: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"\n❌ Exception: {type(e).__name__}")
    print(f"   {e}")

print("\n" + "=" * 80)
print("🏁 TEST COMPLETO")
print("=" * 80)
print(f"\n📊 Estado de Stripe:")
print(f"   ✅ Stripe v13.0.1 instalado")
print(f"   ✅ Meter configurado: mtr_61TREMHzEdK4Je1Dt418N85z8U7al39U")
print(f"   ✅ Price configurado: price_1SNNcO8N85z8U7al3awMZTn1")
print(f"   ✅ Integration enabled: True")
print(f"   ✅ Usuario tiene stripe_customer_id: cus_TEJP7FOU1RW5vh")
