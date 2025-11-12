# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

import os
import sys

# Add BioQL to path (servidor tiene esto configurado)
sys.path.insert(0, "/home/bioql/Spectrix_framework")

from bioql import quantum

api_key = os.getenv("BIOQL_API_KEY", "__BIOQL_REDACTED__")

print("=" * 80)
print("🧬 QUANTUM Molecular Docking")
print("⚛️  Executing VQE on IBM Torino (133 qubits)")
print("🛡️  QEC: surface_code with 2 logical qubits")
print("=" * 80)

# Execute VQE on IBM Torino with QEC
result = quantum(
    "Analyze ligand with SMILES COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2 docking to receptor PDB 6B3J. "
    "Calculate binding affinity using VQE quantum computation. "
    "Identify key molecular interactions from quantum states. "
    "Calculate Ki and IC50 from quantum binding energies.",
    backend="ibm_torino",
    shots=2000,
    api_key=api_key,
    error_correction="surface_code",
    correction_level="low",
    num_logical_qubits=2,
)

print(f"\n✅ QUANTUM Execution Complete!")
print(f"Success: {result.success}")

if result.success:
    print(f"\n📊 Results:")
    print(f"   Backend: {result.backend_name}")
    print(f"   Shots: {result.shots}")

    # Access bio_interpretation
    bio = getattr(result, "bio_interpretation", {})

    if bio:
        if bio.get("binding_affinity"):
            print(f"\n⚛️  Binding Affinity: {bio['binding_affinity']:.2f} kcal/mol")
        if bio.get("ki"):
            print(f"   Ki: {bio['ki']:.2f} nM")
        if bio.get("ic50"):
            print(f"   IC50: {bio['ic50']:.2f} nM")

    # Show job info
    if hasattr(result, "metadata"):
        metadata = result.metadata
        if "job_id" in metadata:
            print(f"\n🆔 IBM Job ID: {metadata['job_id']}")
        if "queue_position" in metadata:
            print(f"   Queue Position: {metadata['queue_position']}")
        if "estimated_wait" in metadata:
            print(f"   Estimated Wait: {metadata['estimated_wait']}")

    # Show counts if available
    if hasattr(result, "counts") and result.counts:
        print(f"\n🔢 Top 5 Measurement States:")
        sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
        for state, count in sorted_counts[:5]:
            probability = count / result.shots * 100
            print(f"   |{state}⟩: {count:4d} ({probability:5.1f}%)")

    # Cost estimate
    if hasattr(result, "cost_estimate"):
        print(f"\n💰 Cost Estimate: ${result.cost_estimate:.4f}")
else:
    print(f"\n❌ Execution failed")
    if hasattr(result, "error"):
        print(f"   Error: {result.error}")

print("\n" + "=" * 80)
