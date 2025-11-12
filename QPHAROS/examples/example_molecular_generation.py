# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Molecular Generation Example
Generate novel drug candidates using Quantum GAN
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import QPHAROSConfig
from core.quantum_backend import QuantumBackend
from layers.layer4_generation import QuantumMolecularGAN


def main():
    """
    Example: Generate novel molecules using QGAN
    """

    print("\n" + "=" * 80)
    print("🧪 QUANTUM MOLECULAR GENERATION EXAMPLE")
    print("=" * 80 + "\n")

    # Configuration
    config = QPHAROSConfig(backend="ibm_torino", generator_qubits=15, generator_layers=8)

    # Initialize
    backend = QuantumBackend(config)
    qgan = QuantumMolecularGAN(backend, config)

    # 1. Generate from training set
    print("─" * 80)
    print("1. DE NOVO GENERATION")
    print("─" * 80 + "\n")

    training_molecules = [
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
        "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
        "CN(C)C(=N)NC(=N)N",  # Metformin
    ]

    generated = qgan.generate_molecules(
        training_molecules=training_molecules, n_generate=10, target_properties={"drug_like": True}
    )

    print(f"Generated {len(generated)} novel molecules")
    for i, mol in enumerate(generated, 1):
        print(f"{i}. {mol}")

    # 2. Generate analogs
    print("\n" + "─" * 80)
    print("2. ANALOG GENERATION")
    print("─" * 80 + "\n")

    reference = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"  # Caffeine
    print(f"Reference molecule: {reference}\n")

    analogs = qgan.generate_analogs(reference_molecule=reference, n_analogs=5)

    print(f"Generated {len(analogs)} analogs:")
    for i, mol in enumerate(analogs, 1):
        print(f"{i}. {mol}")

    # 3. Scaffold hopping
    print("\n" + "─" * 80)
    print("3. SCAFFOLD HOPPING")
    print("─" * 80 + "\n")

    scaffold_hops = qgan.scaffold_hopping(reference_molecule=reference, n_candidates=5)

    print(f"Generated {len(scaffold_hops)} scaffold-hopped candidates:")
    for i, mol in enumerate(scaffold_hops, 1):
        print(f"{i}. {mol}")

    # 4. Diversity-driven generation
    print("\n" + "─" * 80)
    print("4. DIVERSITY-DRIVEN GENERATION")
    print("─" * 80 + "\n")

    diverse_library = qgan.diversity_driven_generation(
        seed_molecules=training_molecules, n_generate=10
    )

    diversity_score = qgan.calculate_molecular_diversity(diverse_library)

    print(f"Generated diverse library of {len(diverse_library)} molecules")
    print(f"Diversity score: {diversity_score:.3f}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
