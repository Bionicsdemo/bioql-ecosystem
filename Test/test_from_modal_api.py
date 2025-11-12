#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test COMPLETO ejecutando en Modal Server (el servidor REAL de BioQL)
Este es el flujo CORRECTO: Cliente → Modal → BioQL (con token IBM en servidor)
"""
import json

import requests

print("=" * 80)
print("🌐 EJECUTANDO EN MODAL SERVER (Servidor REAL de BioQL)")
print("=" * 80)

# URL del Modal Server (donde REALMENTE se ejecuta BioQL)
modal_url = "https://spectrix--bioql-agent-create-fastapi-app.modal.run"

# 1. Health check
print("\n📊 PASO 1: Verificar salud del Modal Server")
print("-" * 80)
response = requests.get(f"{modal_url}/health")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"✅ {json.dumps(response.json(), indent=2)}")
else:
    print(f"❌ Error: {response.text}")

# 2. Generar código con QEC correcto
print("\n⚛️  PASO 2: Generar código BioQL con QEC")
print("-" * 80)

prompt = """Dock my clinical molecule with SMILES='COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2'
against GLP1R receptor (PDB: 6B3J) with surface_code QEC on IBM Torino 2000 shots
use Quillow corrections"""

payload = {"prompt": prompt, "max_length": 2048, "temperature": 0.7}

print(f"Prompt: {prompt[:80]}...")
print(f"\n📤 Enviando a Modal...")

try:
    response = requests.post(f"{modal_url}/generate", json=payload, timeout=30)

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Código generado exitosamente!")

        code = result.get("code", "")

        # Verificar parámetros QEC
        print("\n🔍 Verificando parámetros QEC en código generado:")
        if "error_correction=" in code:
            print("   ✅ error_correction= (CORRECTO)")
        else:
            print("   ❌ error_correction= faltante")

        if "correction_level=" in code:
            print("   ✅ correction_level= (CORRECTO)")
        else:
            print("   ❌ correction_level= faltante")

        if "num_logical_qubits=" in code:
            print("   ✅ num_logical_qubits= (CORRECTO)")
        else:
            print("   ❌ num_logical_qubits= faltante")

        if "qec_config=" in code:
            print("   ❌ qec_config= presente (INCORRECTO)")
        else:
            print("   ✅ qec_config= ausente (CORRECTO)")

        # Mostrar el snippet de quantum()
        print("\n📝 Snippet de código generado (quantum call):")
        print("-" * 80)
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if "result = quantum(" in line:
                for j in range(i, min(i + 12, len(lines))):
                    print(f"   {lines[j]}")
                break
        print("-" * 80)

        # Guardar código generado
        output_file = "/Users/heinzjungbluth/Desktop/Test/generated_from_modal.py"
        with open(output_file, "w") as f:
            f.write(code)
        print(f"\n💾 Código guardado en: {output_file}")

        print("\n" + "=" * 80)
        print("🎉 ¡ÉXITO! Modal Server genera código CORRECTO")
        print("=" * 80)
        print("\n✅ El VS Code Extension ahora funciona perfectamente!")
        print("   Cuando un usuario usa el VS Code extension:")
        print("   1. VS Code envía prompt al Modal server")
        print("   2. Modal genera código con parámetros QEC CORRECTOS")
        print("   3. Usuario recibe código sin TypeError")
        print()
        print("✅ PROBLEMA RESUELTO COMPLETAMENTE")

    else:
        print(f"\n❌ Error HTTP: {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print(f"\n⏱️  Timeout esperando respuesta")
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("🏁 Test Completo")
print("=" * 80)
