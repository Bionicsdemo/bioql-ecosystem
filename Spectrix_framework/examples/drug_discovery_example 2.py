#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Drug Discovery Pack - Example Usage

This script demonstrates the new drug discovery capabilities in BioQL v2.1.0:
- Molecular docking (Vina + Quantum backends)
- Ligand/receptor preparation
- Molecular visualization
- Dynamic library calls via natural language

Author: BioQL Development Team
License: MIT
"""

import os
from pathlib import Path


# Example 1: Molecular Docking with AutoDock Vina
def example_vina_docking():
    """Example: Classical molecular docking using AutoDock Vina"""
    print("=" * 70)
    print("Example 1: Molecular Docking with AutoDock Vina")
    print("=" * 70)

    from bioql.docking import dock

    # Docking aspirin to COX-2 enzyme
    result = dock(
        receptor="inputs/cox2.pdb",  # Receptor PDB file
        ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin SMILES
        backend="vina",  # Use Vina backend
        center=(10.0, 15.0, 20.0),  # Binding site center (optional)
        box_size=(20, 20, 20),  # Search box size
        output_dir="outputs/cox2_aspirin",
    )

    if result.success:
        print(f"✅ Docking successful!")
        print(f"   Job ID: {result.job_id}")
        print(f"   Binding score: {result.score:.2f} kcal/mol")
        print(f"   Output: {result.output_complex}")
    else:
        print(f"❌ Docking failed: {result.error_message}")

    print()


# Example 2: Quantum Docking
def example_quantum_docking():
    """Example: Quantum computing-based molecular docking"""
    print("=" * 70)
    print("Example 2: Quantum Molecular Docking")
    print("=" * 70)

    from bioql.docking import dock

    # Get API key from environment
    api_key = os.getenv("BIOQL_API_KEY")

    if not api_key:
        print("⚠️  BIOQL_API_KEY not set. Skipping quantum example.")
        print("   Get your key at: https://bioql.com/signup")
        return

    # Quantum docking with ethanol
    result = dock(
        receptor="inputs/protein.pdb",
        ligand_smiles="CCO",  # Ethanol
        backend="quantum",
        api_key=api_key,
        shots=1024,  # Quantum shots
        output_dir="outputs/quantum_ethanol",
    )

    if result.success:
        print(f"✅ Quantum docking successful!")
        print(f"   Job ID: {result.job_id}")
        print(f"   Binding energy: {result.metadata.get('energy')} Hartrees")
        print(f"   Score: {result.score:.2f} kcal/mol")
    else:
        print(f"❌ Quantum docking failed: {result.error_message}")

    print()


# Example 3: Ligand Preparation
def example_ligand_prep():
    """Example: Prepare ligand from SMILES"""
    print("=" * 70)
    print("Example 3: Ligand Preparation from SMILES")
    print("=" * 70)

    from bioql.chem import prepare_ligand

    # Prepare caffeine molecule
    result = prepare_ligand(
        smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
        output_path="outputs/caffeine.pdb",
        output_format="pdb",
        add_hydrogens=True,
        optimize_geometry=True,
    )

    if result.success:
        print(f"✅ Ligand prepared successfully!")
        print(f"   Output: {result.output_path}")
        print(f"   Molecular weight: {result.molecular_weight:.2f} g/mol")
        print(f"   Number of atoms: {result.num_atoms}")
    else:
        print(f"❌ Preparation failed: {result.error_message}")

    print()


# Example 4: Visualization
def example_visualization():
    """Example: Visualize protein-ligand complex"""
    print("=" * 70)
    print("Example 4: Molecular Visualization")
    print("=" * 70)

    from bioql.visualize import save_image, visualize_complex

    # Visualize complex and save image
    result = visualize_complex(
        receptor_path="outputs/cox2_aspirin/receptor_prepared.pdb",
        ligand_path="outputs/caffeine.pdb",
        output_image="outputs/complex_visualization.png",
        output_session="outputs/complex.pse",  # PyMOL session
    )

    if result.success:
        print(f"✅ Visualization complete!")
        print(f"   Image: {result.output_path}")
    else:
        print(f"❌ Visualization failed: {result.error_message}")
        print(f"   Note: PyMOL may not be installed. Install with: pip install bioql[viz]")

    print()


# Example 5: Dynamic Library Calls (Meta-wrapper)
def example_dynamic_calls():
    """Example: Call any Python library via natural language"""
    print("=" * 70)
    print("Example 5: Dynamic Library Calls (Meta-wrapper)")
    print("=" * 70)

    from bioql import dynamic_call

    # Example 5a: Calculate molecular weight with RDKit
    print("\\n5a. Calculate molecular weight of aspirin:")
    result = dynamic_call(
        "Use RDKit to calculate molecular weight of aspirin SMILES CC(=O)OC1=CC=CC=C1C(=O)O"
    )

    if result.success:
        print(f"   ✅ Molecular weight: {result.result:.2f} g/mol")
        print(f"   Code executed: {result.code_executed}")
    else:
        print(f"   ❌ Failed: {result.error_message}")

    # Example 5b: Numpy calculations
    print("\\n5b. Calculate mean with numpy:")
    result = dynamic_call("Use numpy to calculate mean of array [1, 2, 3, 4, 5]")

    if result.success:
        print(f"   ✅ Mean: {result.result}")
    else:
        print(f"   ❌ Failed: {result.error_message}")

    # Example 5c: Pandas data analysis
    print("\\n5c. Read CSV with pandas:")
    result = dynamic_call("Use pandas to read CSV file data/compounds.csv and show first 5 rows")

    if result.success:
        print(f"   ✅ DataFrame loaded")
        print(result.result)
    else:
        print(f"   ❌ Failed: {result.error_message}")

    print()


# Example 6: Complete Drug Discovery Workflow
def example_complete_workflow():
    """Example: Complete drug discovery workflow"""
    print("=" * 70)
    print("Example 6: Complete Drug Discovery Workflow")
    print("=" * 70)

    from bioql.chem import prepare_ligand, prepare_receptor
    from bioql.docking import dock
    from bioql.visualize import visualize_complex

    # Step 1: Prepare receptor
    print("\\nStep 1: Preparing receptor...")
    receptor_result = prepare_receptor(
        "inputs/target_protein.pdb",
        output_path="outputs/workflow/receptor.pdb",
        remove_waters=True,
    )

    if not receptor_result.success:
        print(f"❌ Receptor preparation failed: {receptor_result.error_message}")
        return

    # Step 2: Prepare ligand
    print("Step 2: Preparing ligand from SMILES...")
    ligand_result = prepare_ligand(
        "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
        output_path="outputs/workflow/ligand.pdb",
    )

    if not ligand_result.success:
        print(f"❌ Ligand preparation failed: {ligand_result.error_message}")
        return

    # Step 3: Perform docking
    print("Step 3: Performing molecular docking...")
    dock_result = dock(
        receptor=receptor_result.output_path,
        ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        backend="auto",  # Auto-select best backend
        output_dir="outputs/workflow/docking",
    )

    if not dock_result.success:
        print(f"❌ Docking failed: {dock_result.error_message}")
        return

    # Step 4: Visualize results
    print("Step 4: Visualizing complex...")
    viz_result = visualize_complex(
        receptor_path=receptor_result.output_path,
        ligand_path=ligand_result.output_path,
        output_image="outputs/workflow/complex.png",
    )

    # Summary
    print("\\n" + "=" * 70)
    print("Workflow Summary:")
    print("=" * 70)
    print(f"✅ Receptor prepared: {receptor_result.num_residues} residues")
    print(f"✅ Ligand prepared: MW = {ligand_result.molecular_weight:.2f} g/mol")
    print(f"✅ Docking complete: Score = {dock_result.score:.2f} kcal/mol")
    print(f"✅ Visualization saved")
    print(f"\\n📁 Results directory: outputs/workflow/")
    print()


def main():
    """Run all examples"""
    print("\\n" + "=" * 70)
    print("BioQL Drug Discovery Pack - Example Demonstrations")
    print("Version: 2.1.0")
    print("=" * 70)
    print()

    # Create output directories
    Path("outputs").mkdir(exist_ok=True)
    Path("inputs").mkdir(exist_ok=True)

    # Run examples
    examples = [
        ("Vina Docking", example_vina_docking),
        ("Quantum Docking", example_quantum_docking),
        ("Ligand Preparation", example_ligand_prep),
        ("Visualization", example_visualization),
        ("Dynamic Library Calls", example_dynamic_calls),
        ("Complete Workflow", example_complete_workflow),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\\n❌ Example '{name}' failed with error: {e}\\n")
            continue

    print("=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\\nNext steps:")
    print("  1. Install optional dependencies: pip install bioql[vina,viz,openmm]")
    print("  2. Set up API key: export BIOQL_API_KEY=your_key")
    print("  3. Prepare your input files (PDB receptors, ligand SMILES)")
    print("  4. Run your own docking simulations!")
    print("\\n📚 Documentation: https://docs.bioql.com/drug-discovery")
    print("💬 Support: https://github.com/bioql/bioql/issues")


if __name__ == "__main__":
    main()
