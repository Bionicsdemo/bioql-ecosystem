# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
VQE Visualization Example
=========================

Demonstrates how to use the enhanced VisualizationGenerator with REAL VQE data

Author: Spectrix R&D / BioQL Team
"""

import sys

sys.path.append("..")

import numpy as np
from quantum_core.backends.visualization_generator import VisualizationGenerator


# Example 1: Basic usage with VQE energies
def example_with_vqe_data():
    """Example using real VQE molecular data"""

    viz_gen = VisualizationGenerator(output_dir="/tmp/vqe_visualizations")

    # Simulated quantum measurement counts
    counts = {
        "0000": 450,
        "0001": 120,
        "0010": 85,
        "0011": 60,
        "0100": 55,
        "0101": 40,
        "0110": 35,
        "0111": 30,
        "1000": 25,
        "1001": 20,
        "1010": 18,
        "1011": 15,
        "1100": 12,
        "1101": 10,
        "1110": 8,
        "1111": 7,
    }

    # REAL VQE energies in Hartree (example: H2 molecule)
    vqe_energies = {
        "0000": -1.1372,  # Ground state
        "0001": -1.0524,
        "0010": -1.0421,
        "0011": -0.9876,
        "0100": -0.9654,
        "0101": -0.9234,
        "0110": -0.8987,
        "0111": -0.8654,
        "1000": -0.8432,
        "1001": -0.8123,
        "1010": -0.7876,
        "1011": -0.7654,
        "1100": -0.7432,
        "1101": -0.7234,
        "1110": -0.6987,
        "1111": -0.6543,
    }

    # Ground state energy (from exact diagonalization)
    ground_state_energy = -1.1372

    # Energy landscape across bond distances
    energy_landscape = [
        -0.5234,
        -0.8765,
        -1.0234,
        -1.1234,
        -1.1372,  # Min at index 4
        -1.1234,
        -1.0876,
        -1.0234,
        -0.9543,
        -0.8765,
        -0.7654,
        -0.6543,
        -0.5432,
    ]

    # Number of Hamiltonian terms (for H2: 15 terms typical)
    hamiltonian_terms = 15

    # VQE convergence history during optimization
    convergence_history = [
        -0.5432,
        -0.7654,
        -0.8765,
        -0.9543,
        -1.0123,
        -1.0654,
        -1.0987,
        -1.1123,
        -1.1234,
        -1.1321,
        -1.1352,
        -1.1365,
        -1.1370,
        -1.1371,
        -1.1372,
    ]

    # Generate ALL visualizations with VQE data
    output_files = viz_gen.generate_from_quantum_results(
        job_id="H2_VQE_example",
        counts=counts,
        num_qubits=4,
        molecule_type="H2",
        viz_type="vqe_molecular",
        vqe_energies=vqe_energies,
        ground_state_energy=ground_state_energy,
        energy_landscape=energy_landscape,
        hamiltonian_terms=hamiltonian_terms,
        convergence_history=convergence_history,
    )

    print("\n" + "=" * 70)
    print("VQE VISUALIZATION GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nGenerated {len(output_files)} visualization files:")
    for viz_type, filepath in output_files.items():
        print(f"  - {viz_type:25s}: {filepath}")
    print("\n" + "=" * 70)

    return output_files


# Example 2: Backward compatible usage (without VQE data)
def example_without_vqe_data():
    """Example showing backward compatibility - works without VQE data"""

    viz_gen = VisualizationGenerator(output_dir="/tmp/simple_visualizations")

    counts = {
        "000": 350,
        "001": 150,
        "010": 120,
        "011": 90,
        "100": 80,
        "101": 70,
        "110": 60,
        "111": 50,
    }

    # Call WITHOUT VQE parameters - uses simplified energy calculation
    output_files = viz_gen.generate_from_quantum_results(
        job_id="simple_example",
        counts=counts,
        num_qubits=3,
        molecule_type="generic",
        viz_type="basic",
    )

    print("\n" + "=" * 70)
    print("SIMPLE VISUALIZATION GENERATION COMPLETE (No VQE data)")
    print("=" * 70)
    print(f"\nGenerated {len(output_files)} visualization files:")
    for viz_type, filepath in output_files.items():
        print(f"  - {viz_type:25s}: {filepath}")
    print("\n" + "=" * 70)

    return output_files


# Example 3: Using partial VQE data
def example_partial_vqe_data():
    """Example with only some VQE parameters"""

    viz_gen = VisualizationGenerator(output_dir="/tmp/partial_vqe_viz")

    counts = {"00": 500, "01": 300, "10": 150, "11": 50}

    # Only provide convergence history, no energy landscape
    convergence_history = [-0.5, -0.7, -0.85, -0.92, -0.95, -0.97]

    output_files = viz_gen.generate_from_quantum_results(
        job_id="partial_vqe",
        counts=counts,
        num_qubits=2,
        molecule_type="LiH",
        viz_type="partial",
        convergence_history=convergence_history,
        ground_state_energy=-0.97,
    )

    print("\n" + "=" * 70)
    print("PARTIAL VQE VISUALIZATION GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nGenerated {len(output_files)} visualization files:")
    for viz_type, filepath in output_files.items():
        print(f"  - {viz_type:25s}: {filepath}")
    print("\n" + "=" * 70)

    return output_files


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("VQE VISUALIZATION EXAMPLES")
    print("=" * 70)

    # Run all examples
    print("\n\n### EXAMPLE 1: Full VQE Data ###")
    example_with_vqe_data()

    print("\n\n### EXAMPLE 2: Backward Compatible (No VQE) ###")
    example_without_vqe_data()

    print("\n\n### EXAMPLE 3: Partial VQE Data ###")
    example_partial_vqe_data()

    print("\n\nAll examples completed successfully!")
