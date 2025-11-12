# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

import requests

servers = {
    "Health/Auth": "https://api.bioql.bio/health",
    "Workflows": "https://api.bioql.bio/workflows",
    "Notebook": "https://api.bioql.bio/notebook",
    "Graphs": "https://api.bioql.bio/graphs",
    "Quantum Docking": "https://api.bioql.bio/quantum-docking",
    "Quillow": "https://api.bioql.bio/quillow",
}

print("=" * 80)
print("🔍 Verificando todos los servidores en api.bioql.bio")
print("=" * 80)

for name, url in servers.items():
    print(f"\n📡 {name}:")
    print(f"   URL: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"   ✅ Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 80)
