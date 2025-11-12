#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Probar diferentes endpoints para Workflows y Lab Notebook
"""
import requests

print("=" * 80)
print("🔍 PROBANDO ENDPOINTS DE WORKFLOWS Y LAB NOTEBOOK")
print("=" * 80)

endpoints = [
    # Workflows
    ("Workflows - /workflow", "https://api.bioql.bio/workflow"),
    ("Workflows - /workflow/", "https://api.bioql.bio/workflow/"),
    ("Workflows - /workflow/health", "https://api.bioql.bio/workflow/health"),
    ("Workflows - /api/workflow/health", "https://api.bioql.bio/api/workflow/health"),
    ("Workflows - /api/workflows/health", "https://api.bioql.bio/api/workflows/health"),
    # Lab Notebook
    ("Lab Notebook - /lab-notebook", "https://api.bioql.bio/lab-notebook"),
    ("Lab Notebook - /lab-notebook/health", "https://api.bioql.bio/lab-notebook/health"),
    ("Lab Notebook - /notebook", "https://api.bioql.bio/notebook"),
    ("Lab Notebook - /notebook/health", "https://api.bioql.bio/notebook/health"),
    ("Lab Notebook - /api/notebook/health", "https://api.bioql.bio/api/notebook/health"),
]

for name, url in endpoints:
    print(f"\n{'='*80}")
    print(f"🔍 {name}")
    print(f"   URL: {url}")
    print(f"{'='*80}")

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            print(f"   ✅ STATUS: 200 OK")
            try:
                data = response.json()
                print(f"   Response (JSON):")
                import json

                print(f"      {json.dumps(data, indent=6)[:300]}")
            except:
                print(f"   Response (TEXT):")
                print(f"      {response.text[:200]}")

        elif response.status_code == 404:
            print(f"   ❌ STATUS: 404 Not Found")

        elif response.status_code == 502:
            print(f"   ⚠️  STATUS: 502 Bad Gateway (Servidor existe pero no responde)")

        else:
            print(f"   ⚠️  STATUS: {response.status_code}")
            print(f"      {response.text[:100]}")

    except requests.exceptions.Timeout:
        print(f"   ⏱️  TIMEOUT")

    except requests.exceptions.ConnectionError:
        print(f"   ❌ CONNECTION ERROR")

    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}")

print(f"\n{'='*80}")
print(f"✅ PRUEBAS COMPLETAS")
print(f"{'='*80}")
