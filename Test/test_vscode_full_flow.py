#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test completo del flujo VS Code → Modal → BioQL
Simula exactamente lo que hace el VS Code extension
"""
import json

import requests

print("=" * 80)
print("🧬 TEST COMPLETO: VS Code → Modal → BioQL")
print("=" * 80)

# PASO 1: Simular lo que VS Code envía al Modal server
print("\n📤 PASO 1: VS Code envía prompt al Modal server")
print("-" * 80)

url = "https://spectrix--bioql-agent-create-fastapi-app.modal.run/generate"
prompt = """Dock my clinical molecule with SMILES='COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2'
against GLP1R receptor (PDB: 6B3J) with surface_code QEC on IBM Torino 2000 shots
use Quillow corrections"""

payload = {"prompt": prompt, "max_length": 2048, "temperature": 0.7}

print(f"URL: {url}")
print(f"Prompt: {prompt[:80]}...")

# PASO 2: Modal genera el código
print("\n⚙️  PASO 2: Modal genera código con parámetros correctos")
print("-" * 80)

response = requests.post(url, json=payload, timeout=30)

if response.status_code != 200:
    print(f"❌ Error: HTTP {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()

print(f"✅ Response Status: {response.status_code}")
print(f"✅ Response has 'code': {'code' in data}")
print(f"✅ Response has 'success': {'success' in data}")

code = data.get("code", "")

# PASO 3: Verificar parámetros generados
print("\n🔍 PASO 3: Verificar que usa parámetros CORRECTOS")
print("-" * 80)

# Buscar la llamada a quantum()
import re

quantum_call_match = re.search(r"result = quantum\((.*?)\)", code, re.DOTALL)

if quantum_call_match:
    quantum_call = quantum_call_match.group(0)

    checks = [
        ("error_correction=", "✅ Usa error_correction=", "❌ Falta error_correction="),
        ("correction_level=", "✅ Usa correction_level=", "❌ Falta correction_level="),
        ("num_logical_qubits=", "✅ Usa num_logical_qubits=", "❌ Falta num_logical_qubits="),
    ]

    all_correct = True
    for param, success_msg, fail_msg in checks:
        if param in quantum_call:
            print(success_msg)
        else:
            print(fail_msg)
            all_correct = False

    # Verificar que NO usa qec_config
    if "qec_config=" in quantum_call:
        print("❌ ERROR: Todavía usa qec_config= (INCORRECTO)")
        all_correct = False
    else:
        print("✅ NO usa qec_config= (CORRECTO)")

    # Verificar Quillow setup
    if "import quillow" in code or "importlib.import_module" in code:
        print("✅ Incluye setup de Quillow")
    else:
        print("⚠️  No incluye setup de Quillow")

    print("\n" + "=" * 80)
    if all_correct:
        print("✅ ¡TODOS LOS PARÁMETROS SON CORRECTOS!")
        print("=" * 80)

        # PASO 4: Mostrar código generado
        print("\n📝 CÓDIGO GENERADO (primeras líneas):")
        print("-" * 80)
        lines = code.split("\n")[:35]
        for i, line in enumerate(lines, 1):
            print(f"{i:3d} | {line}")
        print("-" * 80)

        # PASO 5: Guardar código para ejecución
        print("\n💾 PASO 4: Guardar código generado")
        print("-" * 80)

        output_file = "/Users/heinzjungbluth/Desktop/Test/generated_from_vscode.py"
        with open(output_file, "w") as f:
            f.write(code)

        print(f"✅ Código guardado en: {output_file}")

        print("\n" + "=" * 80)
        print("🎉 TEST EXITOSO - EL FLUJO COMPLETO FUNCIONA")
        print("=" * 80)
        print("\n📋 Para ejecutar el código generado:")
        print(f"   export BIOQL_API_KEY='tu_api_key'")
        print(f"   python3 {output_file}")

    else:
        print("❌ HAY PARÁMETROS INCORRECTOS")
        print("=" * 80)
else:
    print("❌ No se encontró llamada a quantum() en el código")
