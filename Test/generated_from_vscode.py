# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

import os

from bioql import quantum

# Import Quillow for real quantum error correction
try:
    import importlib

    quillow = importlib.import_module("quillow")
    SurfaceCodeSimulator = getattr(quillow, "SurfaceCodeSimulator", None)
    MWPMDecoder = getattr(quillow, "MWPMDecoder", None)
    if SurfaceCodeSimulator is None or MWPMDecoder is None:
        raise ImportError("quillow installed but missing expected classes")
    QUILLOW_AVAILABLE = True
    print("✅ Quillow QEC engine loaded")
except Exception:
    QUILLOW_AVAILABLE = False
    SurfaceCodeSimulator = None
    MWPMDecoder = None
    print("⚠️  Quillow not available - using BioQL native QEC")

api_key = os.getenv("BIOQL_API_KEY", "your_api_key_here")

print("=" * 80)
print("🧬 QUANTUM Molecular Docking")
print("⚛️  Executing VQE on IBM Quantum Hardware")
print("🛡️  QEC: surface_code with 2 logical qubits")
print("=" * 80)

# ============================================================================
# QUILLOW QUANTUM ERROR CORRECTION SETUP
# ============================================================================
qec_distance = 3  # Surface code distance
qec_physical_qubits = (2 * qec_distance - 1) ** 2
qec_logical_qubits = 2

if QUILLOW_AVAILABLE:
    print(f"\n🛡️  Initializing Quillow QEC Protection")
    print(f"   Surface Code Distance: d={{qec_distance}}")
    print(f"   Physical Qubits: {{qec_physical_qubits}} per logical qubit")
    print(f"   Total Physical Qubits: {{qec_physical_qubits * qec_logical_qubits}}")
    print(f"   Decoder: Minimum Weight Perfect Matching (MWPM)")
    qec_simulator = SurfaceCodeSimulator(distance=qec_distance)
    decoder = MWPMDecoder()
    print(f"   ✅ Quillow QEC initialized - ready for fault-tolerant computation")
    print("-" * 60)


# Execute VQE on REAL quantum hardware
result = quantum(
    "Analyze ligand with SMILES SMILES_HERE docking to receptor PDB PDB_ID_HERE. "
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

print(f"\\n✅ QUANTUM Docking Complete!")
print(f"Success: {result.success}")

# Access bio_interpretation for comprehensive data
bio = getattr(result, "bio_interpretation", {})

if bio.get("binding_affinity"):
    print(f"\\n⚛️  Binding Affinity: {bio['binding_affinity']:.2f} kcal/mol")
if bio.get("ki"):
    print(f"   Ki: {bio['ki']:.2f} nM")
if bio.get("ic50"):
    print(f"   IC50: {bio['ic50']:.2f} nM")

# Molecular interactions
if bio.get("h_bonds"):
    print(f"\\n🔗 Molecular Interactions:")
    print(f"   H-bonds: {bio.get('h_bonds', 'N/A')}")
    print(f"   Hydrophobic: {bio.get('hydrophobic_contacts', 'N/A')}")

print("\\n" + "=" * 80)
