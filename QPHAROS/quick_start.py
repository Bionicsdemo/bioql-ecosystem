#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Quick Start Demo
Run this to see QPHAROS in action with IBM Torino
"""

import os

from core.config import QPHAROSConfig
from core.pipeline import QuantumDrugDesignPipeline


def main():
    """Quick demonstration of QPHAROS capabilities"""

    print("\n" + "█" * 80)
    print("🧬 QPHAROS - Quantum Pharmaceutical Optimization System")
    print("█" * 80 + "\n")

    # Check for API key
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("⚠️  WARNING: BIOQL_API_KEY not set!")
        print("Set your API key:")
        print("  export BIOQL_API_KEY='your_key_here'")
        print("\nProceeding with demo mode...\n")

    # Quick configuration
    config = QPHAROSConfig(
        backend="ibm_torino",
        shots=2000,
        qec_enabled=True,
        qec_type="surface_code",
        logical_qubits=2,
    )

    # Initialize pipeline
    print("🔧 Initializing quantum pipeline...\n")

    pipeline = QuantumDrugDesignPipeline(
        target_protein="6B3J",  # GLP-1R for diabetes
        disease_profile="type 2 diabetes",
        config=config,
        backend="ibm_torino",
    )

    # Test molecule
    test_molecule = "COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2"  # Berberine

    print("=" * 80)
    print("🧪 TESTING WITH BERBERINE")
    print("=" * 80 + "\n")
    print(f"SMILES: {test_molecule}\n")

    # 1. Binding prediction
    print("─" * 80)
    print("1️⃣  BINDING AFFINITY PREDICTION")
    print("─" * 80 + "\n")

    binding_result = pipeline.binding_predictor.predict_binding(
        ligand_smiles=test_molecule, protein_pdb="6B3J"
    )

    # 2. ADMET analysis
    print("\n" + "─" * 80)
    print("2️⃣  ADMET ANALYSIS")
    print("─" * 80 + "\n")

    admet_result = pipeline.admet_optimizer.predict_admet(test_molecule)
    lipinski = pipeline.admet_optimizer.check_lipinski(test_molecule)

    # 3. Molecular dynamics
    print("\n" + "─" * 80)
    print("3️⃣  MOLECULAR DYNAMICS SIMULATION")
    print("─" * 80 + "\n")

    stability = pipeline.md_simulator.calculate_stability(
        ligand_smiles=test_molecule, protein_pdb="6B3J"
    )

    # Summary
    print("\n" + "=" * 80)
    print("📊 QUICK START SUMMARY")
    print("=" * 80 + "\n")

    print(f"✅ Binding Prediction: Complete")
    binding_affinity = binding_result.get("binding_affinity")
    if binding_affinity:
        print(f"   Affinity: {binding_affinity:.2f} kcal/mol")

    print(f"\n✅ ADMET Analysis: Complete")
    print(f"   Lipinski Pass: {'Yes ✓' if lipinski.get('all_pass') else 'No ✗'}")

    print(f"\n✅ MD Simulation: Complete")
    print(f"   Stability Score: {stability:.3f}")

    # Next steps
    print("\n" + "=" * 80)
    print("🚀 NEXT STEPS")
    print("=" * 80 + "\n")

    print("Try the full examples:")
    print("  1. python examples/example_binding_prediction.py")
    print("  2. python examples/example_admet_optimization.py")
    print("  3. python examples/example_molecular_generation.py")
    print("  4. python examples/example_complete_pipeline.py")

    print("\nFor full drug design:")
    print("  pipeline.design_drug(iterations=100)")

    print("\n" + "=" * 80)
    print("✅ QPHAROS QUICK START COMPLETE!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("  - BioQL is installed: pip install bioql")
        print("  - API key is set: export BIOQL_API_KEY='your_key'")
        print("  - Internet connection is active")
