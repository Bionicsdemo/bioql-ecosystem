#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Debug: Ver exactamente qué responde el workflow server
"""

import json

import requests

API_KEY = "__BIOQL_REDACTED__"

# Payload mínimo para testing
headers = {"Authorization": f"Bearer {API_KEY}"}

payload = {
    "node_type": "quantum",
    "node_id": f"debug_test_1234",
    "inputs": {
        "code": '// Test circuit\nOPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nh q[0];\ncx q[0],q[1];\nmeasure q -> c;',
        "backend": "ibm_torino",
        "shots": 10,
        "circuit_format": "qasm",
    },
}

print("=" * 80)
print("DEBUGGING WORKFLOW SERVER RESPONSE")
print("=" * 80)
print(f"\nEndpoint: https://api.bioql.bio/workflow/execute-node")
print(f"Backend requested: ibm_torino")
print(f"Shots: 10")
print("\n" + "-" * 80)

try:
    response = requests.post(
        "https://api.bioql.bio/workflow/execute-node", json=payload, headers=headers, timeout=30
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Time: {response.elapsed.total_seconds():.2f} seconds")
    print("\n" + "-" * 80)
    print("RESPONSE BODY:")
    print("-" * 80)

    try:
        data = response.json()
        print(json.dumps(data, indent=2))

        # Análisis
        print("\n" + "=" * 80)
        print("ANÁLISIS:")
        print("=" * 80)

        if data.get("success"):
            print("✅ Request marked as 'success'")

            result = data.get("result", {})
            print(f"\nResult keys: {list(result.keys())}")

            if "job_id" in result:
                print(f"📋 Job ID: {result['job_id']}")
                print("   ⚠️  Esto sugiere ejecución asíncrona")

            if "measurements" in result:
                meas = result["measurements"]
                if meas:
                    print(f"📊 Measurements returned: {len(meas)} shots")
                    print("   ⚠️  Respuesta inmediata = probablemente simulador")
                else:
                    print("📊 Measurements: empty list")

            if "backend" in result:
                print(f"🖥️  Backend returned: {result['backend']}")

            if "execution_time" in result:
                exec_time = result["execution_time"]
                print(f"⏱️  Execution time: {exec_time}s")
                if exec_time < 10:
                    print("   🔴 TOO FAST for real quantum hardware!")
                    print("   🔴 IBM hardware queue time: 5-30 minutes minimum")

        else:
            print("❌ Request failed")
            print(f"Error: {data.get('error', 'Unknown')}")

    except json.JSONDecodeError:
        print(response.text[:1000])

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("CONCLUSIÓN:")
print("=" * 80)
print(
    """
Si la respuesta llega en < 10 segundos con measurements:
  🔴 NO está usando IBM hardware real
  🔴 Probablemente está usando un simulador local

IBM Torino real debería:
  ✅ Devolver job_id inmediatamente
  ✅ Requerir polling con otro endpoint
  ✅ Tardar 5-30 minutos en completarse
  ✅ Status: 'queued' → 'running' → 'completed'
"""
)
print("=" * 80)
