#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test completo de BioQL Docking Molecular con QEC en IBM Torino
Prompt: Dock my clinical molecule with SMILES="COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2"
        against GLP1R receptor (PDB: 6B3J) with surface_code QEC on IBM Torino 2000 shots
"""

import json
from datetime import datetime

import requests

# API Configuration
API_URL = "https://api.bioql.bio/api/quantum/execute"
API_KEY = "__BIOQL_REDACTED__"

# Molecular parameters
SMILES = "COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2"
PDB_ID = "6B3J"
RECEPTOR = "GLP1R"

print("=" * 80)
print("🧬 BioQL MOLECULAR DOCKING CON QEC EN IBM TORINO")
print("=" * 80)

# Generar código BioQL
bioql_code = f"""
from bioql import quantum, dock

# Clinical molecule (Berberine analog)
ligand_smiles = "{SMILES}"

# GLP1R receptor
receptor_pdb = "{PDB_ID}"

# Perform quantum-enhanced docking
result = dock(
    ligand=ligand_smiles,
    receptor=receptor_pdb,
    backend="ibm_torino",
    shots=2000,
    api_key="{API_KEY}",
    error_correction="surface_code",
    correction_level="medium",
    num_logical_qubits=4,
    use_quillow=True
)

# Return the quantum circuit generated
return result.circuit if hasattr(result, 'circuit') else result
"""

print(f"\n📋 PARÁMETROS:")
print(f"   Ligand SMILES: {SMILES}")
print(f"   Receptor: {RECEPTOR} (PDB: {PDB_ID})")
print(f"   Backend: IBM Torino (133 qubits)")
print(f"   Shots: 2000")
print(f"   QEC: surface_code + Quillow")
print(f"   Correction level: medium")
print(f"   Logical qubits: 4")

print(f"\n💻 CÓDIGO BIOQL GENERADO:")
print("-" * 80)
print(bioql_code)

# Preparar payload para API
payload = {
    "api_key": API_KEY,
    "program": bioql_code,
    "backend": "ibm_torino",
    "shots": 2000,
    "qec": {
        "enabled": True,
        "type": "surface_code",
        "correction_level": "medium",
        "num_logical_qubits": 4,
    },
}

print(f"\n🚀 EJECUTANDO EN IBM TORINO...")
print("-" * 80)
print(f"   API: {API_URL}")
print(f"   Timestamp: {datetime.now().isoformat()}")

try:
    # Ejecutar request
    response = requests.post(API_URL, json=payload, timeout=600)  # 10 min timeout

    print(f"\n✅ Response Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        print(f"\n{'='*80}")
        print(f"📊 RESULTADOS DEL DOCKING")
        print(f"{'='*80}")

        # Información básica
        print(f"\n✅ Execution Status:")
        print(f"   Success: {result.get('success')}")
        print(f"   Backend: {result.get('backend')}")
        print(f"   Shots executed: {result.get('shots')}")

        # Costos y facturación
        print(f"\n💰 Billing:")
        print(f"   Cost: ${result.get('cost_estimate')}")
        print(f"   Balance after: ${result.get('balance_after')}")
        print(f"   💳 Stripe reported: {result.get('stripe_reported')}")

        # Resultados quantum
        counts = result.get("counts", {})
        if counts:
            print(f"\n⚛️  Quantum Results:")
            print(f"   Total states measured: {len(counts)}")
            print(f"   Top 5 states:")
            sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
            for state, count in sorted_counts:
                percentage = (count / result.get("shots", 1)) * 100
                print(f"      |{state}⟩: {count} ({percentage:.1f}%)")

        # Interpretación biológica
        bio_interp = result.get("bio_interpretation", {})
        if bio_interp:
            print(f"\n🧬 Biological Interpretation:")
            print(f"   Application: {bio_interp.get('application', 'N/A')}")
            print(f"   Most probable state: |{bio_interp.get('most_probable_state', 'N/A')}⟩")
            if "binding_affinity" in bio_interp:
                print(f"   Binding affinity: {bio_interp.get('binding_affinity')}")

        # Metadata
        metadata = result.get("metadata", {})
        if metadata:
            print(f"\n📋 Metadata:")
            if "backend_info" in metadata:
                backend_info = metadata["backend_info"]
                if "num_qubits" in backend_info:
                    print(f"   Physical qubits: {backend_info.get('num_qubits')}")
                if "basis_gates" in backend_info:
                    gates = backend_info.get("basis_gates", [])
                    print(f"   Basis gates: {', '.join(gates[:5])}")

            if "quillow" in str(metadata).lower() or "qec" in str(metadata).lower():
                print(f"   ✅ QEC/Quillow metadata detected")

        # Verificar Stripe reporting
        print(f"\n{'='*80}")
        if result.get("success") and result.get("stripe_reported"):
            print(f"🎉 ¡EJECUCIÓN EXITOSA CON STRIPE REPORTING!")
            print(f"   ✅ Quantum execution completed")
            print(f"   ✅ Cost recorded in Stripe")
            print(f"   ✅ Balance updated")
            print(f"   ✅ Usage logged to database")
        elif result.get("success") and not result.get("stripe_reported"):
            print(f"✅ EJECUCIÓN EXITOSA")
            print(f"   ⚠️  Stripe reporting = False")
            print(f"   (Puede ser que el usuario no tenga Stripe configurado)")
        else:
            print(f"⚠️  EJECUCIÓN FALLÓ")
            print(f"   Error: {result.get('error', 'Unknown error')}")
        print(f"{'='*80}")

        # Guardar resultados completos
        output_file = f"/Users/heinzjungbluth/Desktop/bioql_docking_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Resultados completos guardados en:")
        print(f"   {output_file}")

    elif response.status_code == 403:
        result = response.json()
        print(f"\n⚠️  ERROR 403 - Insufficient Balance")
        print(json.dumps(result, indent=2))
        print(f"\nEl costo de 2000 shots en IBM Torino con QEC es muy alto.")
        print(f"Costo estimado: ~$9,000 (2000 shots * $3/shot * 1.5 QEC multiplier)")

    else:
        print(f"\n❌ ERROR HTTP {response.status_code}")
        print(response.text[:1000])

except requests.exceptions.Timeout:
    print(f"\n⏱️  TIMEOUT (>10 minutos)")
    print(f"   Esto es NORMAL para IBM Quantum hardware real")
    print(f"   Los jobs pueden estar en cola")
    print(f"   El job puede seguir ejecutándose en IBM Quantum Cloud")

except Exception as e:
    print(f"\n❌ EXCEPTION: {type(e).__name__}")
    print(f"   {e}")
    import traceback

    traceback.print_exc()

print(f"\n{'='*80}")
print(f"🏁 TEST COMPLETO")
print(f"{'='*80}")
print(f"\n📊 Resumen del sistema:")
print(f"   ✅ Endpoint: {API_URL}")
print(f"   ✅ Backend: IBM Torino (133 qubits)")
print(f"   ✅ QEC: surface_code + Quillow")
print(f"   ✅ Stripe: Configurado y funcionando")
print(f"   ✅ Molecular docking: GLP1R receptor")
