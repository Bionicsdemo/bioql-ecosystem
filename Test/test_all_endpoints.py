#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Verificar todos los endpoints disponibles de BioQL
"""
import json

import requests

endpoints = [
    # Quantum Docking
    ("Quantum Docking Health", "GET", "https://api.bioql.bio/health/quantum-docking", None),
    ("Quantum Docking API Health", "GET", "https://api.bioql.bio/api/quantum-docking/health", None),
    # Modal Server (VS Code Extension)
    (
        "Modal Health",
        "GET",
        "https://spectrix--bioql-agent-create-fastapi-app.modal.run/health",
        None,
    ),
    (
        "Modal Generate",
        "POST",
        "https://spectrix--bioql-agent-create-fastapi-app.modal.run/generate",
        {"prompt": "test quantum docking with QEC"},
    ),
    # Main API
    ("Main API Health", "GET", "https://api.bioql.bio/api/health", None),
    ("Main API Root", "GET", "https://api.bioql.bio/", None),
]

print("=" * 80)
print("🔍 VERIFICANDO TODOS LOS ENDPOINTS DE BioQL")
print("=" * 80)

for name, method, url, payload in endpoints:
    print(f"\n📡 {name}")
    print(f"   {method} {url}")
    print("-" * 80)

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=payload, timeout=10)

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Response:")
                print(json.dumps(data, indent=6)[:500])
            except:
                print(f"   ✅ Response: {response.text[:200]}")
        else:
            print(f"   ❌ Error: {response.text[:200]}")

    except requests.exceptions.Timeout:
        print(f"   ⏱️  Timeout")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("✅ Verificación completa")
print("=" * 80)
