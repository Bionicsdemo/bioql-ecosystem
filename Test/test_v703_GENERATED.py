# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

import os

from bioql import quantum

api_key = os.getenv("BIOQL_API_KEY", "your_api_key_here")

print("=" * 80)
print("🧬 QUANTUM Molecular Docking")
print("⚛️  Executing VQE on IBM Quantum Hardware")
print("🛡️  QEC: surface_code with 2 logical qubits")
print("=" * 80)

# Execute VQE on REAL quantum hardware
result = quantum(
    "Analyze ligand with SMILES COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2 docking to receptor PDB 6B3J. "
    "Calculate binding affinity using VQE quantum computation. "
    "Identify key molecular interactions from quantum states. "
    "Calculate Ki and IC50 from quantum binding energies.",
    backend="ibm_torino",
    shots=2000,
    api_key=api_key,
    qec_enabled=True,
    qec_type="surface_code",
    logical_qubits=2,
)

print(f"\n✅ QUANTUM Docking Complete!")
print(f"Success: {result.success}")

# Access bio_interpretation for comprehensive data
bio = getattr(result, "bio_interpretation", {})

if bio.get("binding_affinity"):
    print(f"\n⚛️  Binding Affinity: {bio['binding_affinity']:.2f} kcal/mol")
if bio.get("ki"):
    print(f"   Ki: {bio['ki']:.2f} nM")
if bio.get("ic50"):
    print(f"   IC50: {bio['ic50']:.2f} nM")

# Molecular interactions
if bio.get("h_bonds"):
    print(f"\n🔗 Molecular Interactions:")
    print(f"   H-bonds: {bio.get('h_bonds', 'N/A')}")
    print(f"   Hydrophobic: {bio.get('hydrophobic_contacts', 'N/A')}")

print("\n" + "=" * 80)
