# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
ADMET Optimization Example
Optimize molecular properties for drug-likeness
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import QPHAROSConfig
from core.quantum_backend import QuantumBackend
from layers.layer3_admet import QuantumADMETOptimizer


def main():
    """
    Example: ADMET prediction and optimization
    """

    print("\n" + "=" * 80)
    print("💊 QUANTUM ADMET OPTIMIZATION EXAMPLE")
    print("=" * 80 + "\n")

    # Configuration
    config = QPHAROSConfig(backend="ibm_torino", shots=2000)

    # Initialize
    backend = QuantumBackend(config)
    optimizer = QuantumADMETOptimizer(backend, config)

    # Test molecule
    molecule = "COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2"  # Berberine
    print(f"Test Molecule: {molecule}\n")

    # 1. Predict ADMET properties
    print("─" * 80)
    print("1. ADMET PREDICTION")
    print("─" * 80 + "\n")

    admet = optimizer.predict_admet(molecule)

    # 2. Check Lipinski's Rule of Five
    print("\n" + "─" * 80)
    print("2. LIPINSKI'S RULE OF FIVE")
    print("─" * 80 + "\n")

    lipinski = optimizer.check_lipinski(molecule)

    # 3. Calculate drug-likeness score
    print("\n" + "─" * 80)
    print("3. DRUG-LIKENESS SCORE")
    print("─" * 80 + "\n")

    dl_score = optimizer.calculate_drug_likeness_score(molecule)
    print(f"Overall Drug-Likeness Score: {dl_score:.3f}")

    # 4. Optimize ADMET properties
    print("\n" + "─" * 80)
    print("4. ADMET OPTIMIZATION")
    print("─" * 80 + "\n")

    target_properties = {
        "high_bioavailability": True,
        "low_toxicity": True,
        "metabolic_stability": True,
    }

    optimization_result = optimizer.optimize_admet(
        molecule_smiles=molecule, target_properties=target_properties
    )

    # Summary
    print("\n" + "=" * 80)
    print("📊 OPTIMIZATION SUMMARY")
    print("=" * 80 + "\n")

    print(f"Original Molecule: {molecule}")
    print(f"Drug-Likeness Score: {dl_score:.3f}")
    print(f"Lipinski Compliant: {'✅ Yes' if lipinski.get('all_pass') else '❌ No'}")
    print(
        f"Constraints Satisfied: {'✅ Yes' if optimization_result.get('constraints_satisfied') else '❌ No'}"
    )

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
