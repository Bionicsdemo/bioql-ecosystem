#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar startup completo del servidor con Stripe
"""
import time

import paramiko

SERVER = "api.bioql.bio"
USERNAME = "root"
PASSWORD = "P31e27r12u1@HJG"

print("=" * 80)
print("🔍 VERIFICANDO STARTUP DEL SERVIDOR")
print("=" * 80)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USERNAME, password=PASSWORD, timeout=30)

    print(f"\n✅ Conectado a {SERVER}")

    # 1. Ver logs completos del startup
    print(f"\n📋 Últimas 50 líneas del log:")
    print("-" * 80)
    stdin, stdout, stderr = ssh.exec_command("tail -50 /tmp/bioql_auth_server.log")
    logs = stdout.read().decode()
    print(logs)

    # 2. Test del endpoint /health
    print(f"\n🧪 Test de /health")
    print("-" * 80)
    time.sleep(2)

    import requests

    try:
        response = requests.get("https://api.bioql.bio/health", timeout=10)
        if response.status_code == 200:
            import json

            health_data = response.json()
            print(f"✅ Health OK:")
            print(json.dumps(health_data, indent=2))

            if health_data.get("stripe_enabled"):
                print(f"\n✅ Stripe ENABLED: True")
            else:
                print(f"\n⚠️  Stripe ENABLED: False")
        else:
            print(f"⚠️  HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 3. Test de ejecución quantum (con stripe reporting)
    print(f"\n🧪 Test de /api/quantum/execute con Stripe")
    print("-" * 80)

    payload = {
        "api_key": "__BIOQL_REDACTED__",
        "program": "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2,2)\nqc.h(0)\nqc.cx(0,1)\nqc.measure([0,1],[0,1])\nreturn qc",
        "backend": "simulator",
        "shots": 10,
        "qec": {"enabled": False},
    }

    try:
        response = requests.post(
            "https://api.bioql.bio/api/quantum/execute", json=payload, timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ejecución exitosa:")
            print(f"   Success: {result.get('success')}")
            print(f"   Cost: ${result.get('cost_estimate')}")
            print(f"   Stripe reported: {result.get('stripe_reported')}")

            if result.get("stripe_reported"):
                print(f"\n🎉 ¡STRIPE REPORTING FUNCIONANDO!")
            else:
                print(f"\n⚠️  Stripe reported = False")
                print(f"   Posibles razones:")
                print(f"   1. stripe_integration no inicializó correctamente")
                print(f"   2. Error en report_usage_to_stripe()")
                print(f"   3. Usuario sin stripe_customer_id (pero ya vimos que SÍ tiene)")
        else:
            print(f"⚠️  HTTP {response.status_code}")
            print(response.text[:300])
    except Exception as e:
        print(f"❌ Error: {e}")

    ssh.close()

    print("\n" + "=" * 80)
    print("✅ VERIFICACIÓN COMPLETA")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()
