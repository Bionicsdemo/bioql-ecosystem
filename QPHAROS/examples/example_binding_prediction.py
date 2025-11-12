# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Binding Affinity Prediction Example
Predict binding for a set of ligands against target protein
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import QPHAROSConfig
from core.quantum_backend import QuantumBackend
from layers.layer2_binding import QuantumBindingPredictor


def main():
    """
    Example: Predict binding affinity for multiple ligands
    """

    print("\n" + "=" * 80)
    print("⚛️  QUANTUM BINDING PREDICTION EXAMPLE")
    print("=" * 80 + "\n")

    # Configuration
    config = QPHAROSConfig(
        backend="ibm_torino", shots=2000, qec_enabled=True, qec_type="surface_code"
    )

    # Initialize backend and predictor
    backend = QuantumBackend(config)
    predictor = QuantumBindingPredictor(backend, config)

    # Target protein
    protein_pdb = "6B3J"  # GLP-1R

    # Candidate ligands
    ligands = [
        ("Metformin", "CN(C)C(=N)NC(=N)N"),
        ("Berberine", "COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2"),
        ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
        ("Caffeine", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"),
    ]

    # Predict binding for each ligand
    results = []

    for name, smiles in ligands:
        print(f"\n{'─'*80}")
        print(f"🔬 Testing: {name}")
        print(f"   SMILES: {smiles}")
        print(f"{'─'*80}\n")

        result = predictor.predict_binding(ligand_smiles=smiles, protein_pdb=protein_pdb)

        results.append({"name": name, "smiles": smiles, "result": result})

    # Rank by binding affinity
    print(f"\n{'='*80}")
    print(f"🏆 LIGAND RANKING BY BINDING AFFINITY")
    print(f"{'='*80}\n")

    # Sort by binding affinity (more negative = better)
    ranked = sorted(results, key=lambda x: x["result"].get("binding_affinity", 0))

    for i, entry in enumerate(ranked, 1):
        name = entry["name"]
        result = entry["result"]
        affinity = result.get("binding_affinity", 0)
        ki = result.get("ki", 0)

        print(f"{i}. {name}")
        if affinity:
            print(f"   Binding Affinity: {affinity:.2f} kcal/mol")
        if ki:
            print(f"   Ki: {ki:.2f} nM")
        print()

    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
