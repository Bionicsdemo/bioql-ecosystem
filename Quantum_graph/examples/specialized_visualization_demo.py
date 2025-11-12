#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Specialized Molecular Visualization Demo
=========================================

Demonstrates the new molecule-type-specific visualizations.

Author: Spectrix R&D / BioQL Team
Date: 2025-10-26
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from quantum_core.backends.visualization_generator import VisualizationGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_small_molecule():
    """Demo small molecule visualizations"""
    print("\n" + "=" * 80)
    print("DEMO 1: SMALL MOLECULE (Benzene-like compound)")
    print("=" * 80 + "\n")

    viz_gen = VisualizationGenerator(output_dir="/tmp/quantum_viz/small_molecule")

    # Simulated quantum results for a small organic molecule
    files = viz_gen.generate_from_quantum_results(
        job_id="benzene_001",
        counts={"0000": 456, "1111": 344, "0101": 200, "1010": 150, "0011": 120, "1100": 100},
        num_qubits=4,
        molecule_type="small_molecule",
        viz_type="molecular_orbitals",
        vqe_energies={
            "0000": -5.234,  # Ground state
            "1111": -3.456,
            "0101": -4.123,
            "1010": -3.987,
            "0011": -4.567,
            "1100": -4.012,
        },
        ground_state_energy=-5.234,
        energy_landscape=[-5.234, -4.8, -4.2, -4.5, -5.1, -5.234],
        hamiltonian_terms=25,
        convergence_history=[-3.5, -4.2, -4.8, -5.1, -5.234],
    )

    print("\nGenerated files:")
    for viz_type, file_path in files.items():
        print(f"  - {viz_type:25s} -> {Path(file_path).name}")

    print(f"\nTotal: {len(files)} visualization files")


def demo_protein():
    """Demo protein visualizations"""
    print("\n" + "=" * 80)
    print("DEMO 2: PROTEIN (Small peptide)")
    print("=" * 80 + "\n")

    viz_gen = VisualizationGenerator(output_dir="/tmp/quantum_viz/protein")

    files = viz_gen.generate_from_quantum_results(
        job_id="protein_hiv_protease",
        counts={"000000": 512, "111111": 288, "010101": 150, "101010": 140, "001100": 110},
        num_qubits=6,
        molecule_type="protein",
        viz_type="secondary_structure",
        vqe_energies={
            "000000": -125.4,  # Native fold
            "111111": -98.2,  # Partially unfolded
            "010101": -110.5,
            "101010": -105.3,
            "001100": -115.7,
        },
        ground_state_energy=-125.4,
        energy_landscape=[-125.4, -120.0, -110.0, -115.0, -125.4],
        hamiltonian_terms=150,
    )

    print("\nGenerated files:")
    for viz_type, file_path in files.items():
        print(f"  - {viz_type:25s} -> {Path(file_path).name}")

    print(f"\nTotal: {len(files)} visualization files")


def demo_dna():
    """Demo DNA/RNA visualizations"""
    print("\n" + "=" * 80)
    print("DEMO 3: DNA (Double helix fragment)")
    print("=" * 80 + "\n")

    viz_gen = VisualizationGenerator(output_dir="/tmp/quantum_viz/dna")

    files = viz_gen.generate_from_quantum_results(
        job_id="dna_aptamer_001",
        counts={"00000": 600, "11111": 250, "01010": 100, "10101": 90, "00110": 80},
        num_qubits=5,
        molecule_type="dna",
        viz_type="double_helix",
        vqe_energies={
            "00000": -45.2,  # B-DNA
            "11111": -38.5,  # Distorted
            "01010": -42.1,
            "10101": -41.8,
            "00110": -43.5,
        },
        ground_state_energy=-45.2,
        hamiltonian_terms=80,
    )

    print("\nGenerated files:")
    for viz_type, file_path in files.items():
        print(f"  - {viz_type:25s} -> {Path(file_path).name}")

    print(f"\nTotal: {len(files)} visualization files")


def demo_metabolite():
    """Demo metabolite visualizations"""
    print("\n" + "=" * 80)
    print("DEMO 4: METABOLITE (Glucose pathway)")
    print("=" * 80 + "\n")

    viz_gen = VisualizationGenerator(output_dir="/tmp/quantum_viz/metabolite")

    files = viz_gen.generate_from_quantum_results(
        job_id="metabolite_glucose",
        counts={"0000": 450, "1111": 300, "0101": 180, "1010": 120},
        num_qubits=4,
        molecule_type="metabolite",
        viz_type="metabolic_pathway",
        vqe_energies={"0000": -12.5, "1111": -10.2, "0101": -11.3, "1010": -11.0},
        ground_state_energy=-12.5,
        hamiltonian_terms=35,
    )

    print("\nGenerated files:")
    for viz_type, file_path in files.items():
        print(f"  - {viz_type:25s} -> {Path(file_path).name}")

    print(f"\nTotal: {len(files)} visualization files")


def demo_comparison():
    """Show comparison of visualization counts"""
    print("\n" + "=" * 80)
    print("VISUALIZATION COMPARISON ACROSS MOLECULE TYPES")
    print("=" * 80 + "\n")

    print("Molecule Type        | Base Viz | Specialized | Total |")
    print("---------------------|----------|-------------|-------|")
    print("Small Molecule       |    6     |      3      |   9   |")
    print("Protein              |    6     |      3      |   9   |")
    print("DNA/RNA              |    6     |      3      |   9   |")
    print("Metabolite           |    6     |      2      |   8   |")
    print("Generic (fallback)   |    6     |      1      |   7   |")
    print()

    print("Base Visualizations (All Types):")
    print("  1. Energy Histogram")
    print("  2. State Distribution")
    print("  3. Interactive Plot (Plotly)")
    print("  4. Energy Landscape (VQE)")
    print("  5. Hamiltonian Visualization")
    print("  6. VQE Convergence")
    print()

    print("Specialized by Type:")
    print()
    print("  Small Molecule:")
    print("    - Molecular Orbitals (HOMO-LUMO)")
    print("    - Electron Density (2D/3D)")
    print("    - Bond Energy Analysis")
    print()
    print("  Protein:")
    print("    - Secondary Structure")
    print("    - Protein Folding Landscape")
    print("    - Ramachandran Plot")
    print()
    print("  DNA/RNA:")
    print("    - Double Helix Structure")
    print("    - Base Pair Analysis")
    print("    - Groove Width Analysis")
    print()
    print("  Metabolite:")
    print("    - Metabolic Pathway Network")
    print("    - Reactivity Analysis")


def main():
    """Run all demos"""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  SPECIALIZED MOLECULAR VISUALIZATION DEMO".center(78) + "*")
    print("*" + "  Quantum Graph Platform - Version 2.0".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)

    try:
        # Run demos
        demo_small_molecule()
        demo_protein()
        demo_dna()
        demo_metabolite()
        demo_comparison()

        # Summary
        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print()
        print("All visualization files have been generated in:")
        print("  /tmp/quantum_viz/")
        print()
        print("Explore the generated visualizations to see:")
        print("  - Publication-quality scientific plots")
        print("  - Molecule-type-specific analysis")
        print("  - Interactive HTML visualizations")
        print("  - Comprehensive reports (TXT + JSON)")
        print()
        print("For more information, see:")
        print("  - docs/SPECIALIZED_VISUALIZATIONS_IMPLEMENTATION.md")
        print("  - docs/VISUALIZATION_QUICK_REFERENCE.md")
        print()

    except Exception as e:
        logger.error(f"Error running demo: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
