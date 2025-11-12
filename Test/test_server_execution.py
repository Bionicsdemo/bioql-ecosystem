#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test completo ejecutando en el servidor de BioQL
NO local - todo en api.bioql.bio
"""
import json
import time

import requests

print("=" * 80)
print("🌐 EJECUTANDO EN SERVIDOR: api.bioql.bio")
print("=" * 80)

# 1. Verificar salud del servidor
print("\n📊 PASO 1: Verificar servidor quantum-docking")
health_url = "https://api.bioql.bio/health/quantum-docking"
response = requests.get(health_url)
print(f"Status: {response.status_code}")
print(f"Health: {json.dumps(response.json(), indent=2)}")

# 2. Ejecutar docking en el servidor con QEC
print("\n⚛️  PASO 2: Ejecutar docking en servidor con QEC")
execute_url = "https://api.bioql.bio/api/quantum-docking/execute"

payload = {
    "smiles": "COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2",
    "pdb_id": "6B3J",
    "backend": "ibm_torino",
    "shots": 2000,
    "qec": {"enabled": True, "type": "surface_code", "distance": 3},
    "api_key": "__BIOQL_REDACTED__",
}

print(f"\n📤 Enviando request a: {execute_url}")
print(f"   SMILES: {payload['smiles'][:50]}...")
print(f"   PDB: {payload['pdb_id']}")
print(f"   Backend: {payload['backend']}")
print(f"   Shots: {payload['shots']}")
print(f"   QEC: surface_code d=3")

try:
    response = requests.post(execute_url, json=payload, timeout=60)
    print(f"\n✅ Response Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n📊 Resultado:")
        print(json.dumps(result, indent=2))

        # Check if execution was successful
        if result.get("success"):
            print(f"\n🎉 ¡EJECUCIÓN EXITOSA EN SERVIDOR!")

            if "binding_affinity" in result:
                print(f"\n⚛️  Binding Affinity: {result['binding_affinity']}")
            if "ki" in result:
                print(f"   Ki: {result['ki']}")
            if "job_id" in result:
                print(f"\n🆔 Job ID: {result['job_id']}")
        else:
            print(f"\n⚠️  Ejecución en progreso o error")
            if "message" in result:
                print(f"   Mensaje: {result['message']}")
    else:
        print(f"\n❌ Error HTTP: {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print(f"\n⏱️  Timeout - El job puede estar en cola en IBM Quantum")
    print(f"   Esto es normal para hardware real")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {e}")

print("\n" + "=" * 80)
print("🏁 Test de Servidor Completo")
print("=" * 80)
