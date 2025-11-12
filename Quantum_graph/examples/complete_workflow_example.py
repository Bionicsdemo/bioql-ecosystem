# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Complete Quantum_graph Workflow Example
========================================

This example demonstrates the full capabilities of Quantum_graph:
1. Protein structure visualization with quantum sampling
2. Metabolic network analysis
3. Drug-protein docking
4. Multi-omics integration
5. BioQL query integration

Author: Spectrix R&D / BioQL Team
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.services.bioql_integration import BioQLIntegrator
from quantum_core.optimizers.adaptive_quantum_optimizer import (
    AdaptiveQuantumOptimizer,
    MoleculeType,
    VisualizationType,
)
from visualization.metabolomics.quantum_metabolomics_viz import (
    MetabolicNetwork,
    Metabolite,
    QuantumMetabolomicsVisualizer,
    Reaction,
)
from visualization.protein.quantum_protein_viz import QuantumProteinVisualizer
from visualization.quantum_viz_engine import Atom, Bond, MolecularStructure, QuantumVizEngine


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print("=" * 70 + "\n")


def example_1_protein_folding():
    """Example 1: Quantum-enhanced protein folding simulation"""
    print_section("EXAMPLE 1: Protein Folding with Quantum Sampling")

    # Initialize visualizer
    engine = QuantumVizEngine()
    protein_viz = QuantumProteinVisualizer(engine)

    # Create example protein structure (mini-protein, 20 residues)
    print("📝 Creating mini-protein structure (20 residues)...")
    atoms = []
    bonds = []

    # Create helical backbone
    import numpy as np

    for i in range(20):
        # Alpha-helix geometry
        radius = 2.3  # Angstroms
        rise = 1.5  # Rise per residue
        angle = i * 100 * (np.pi / 180)  # 100° rotation per residue

        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        z = i * rise

        # Add C-alpha atom
        atoms.append(Atom("C", x, y, z, residue_id=i + 1, atom_id=len(atoms)))

        # Add backbone atoms (simplified)
        atoms.append(Atom("N", x + 0.5, y, z, residue_id=i + 1, atom_id=len(atoms)))
        atoms.append(Atom("C", x - 0.5, y, z, residue_id=i + 1, atom_id=len(atoms)))
        atoms.append(Atom("O", x, y + 0.5, z, residue_id=i + 1, atom_id=len(atoms)))

        # Bonds within residue
        if len(atoms) >= 4:
            ca_idx = len(atoms) - 4
            bonds.append(Bond(ca_idx, ca_idx + 1, order=1.0))  # CA-N
            bonds.append(Bond(ca_idx, ca_idx + 2, order=1.0))  # CA-C
            bonds.append(Bond(ca_idx + 2, ca_idx + 3, order=2.0))  # C=O

        # Bond to previous residue
        if i > 0:
            prev_c = len(atoms) - 6
            curr_n = len(atoms) - 3
            bonds.append(Bond(prev_c, curr_n, order=1.0))

    structure = MolecularStructure(
        atoms=atoms,
        bonds=bonds,
        name="MiniProtein_20aa",
        molecule_type=MoleculeType.PROTEIN,
        metadata={"sequence": "ACDEFGHIKLMNPQRSTVWY"},
    )

    print(f"✅ Structure created: {len(atoms)} atoms, {len(bonds)} bonds\n")

    # Quantum conformational sampling
    print("⚛️  Performing quantum conformational sampling...")
    result = engine.quantum_conformation_sampling(structure, num_conformations=10)

    print(f"\n📊 Quantum Results:")
    print(f"   Ground state energy: {result.energy:.2f} kcal/mol")
    print(f"   Conformations sampled: {len(result.conformations)}")
    print(f"   Quantum config:")
    print(f"      - Logical qubits: {result.quantum_config.logical_qubits}")
    print(f"      - Physical qubits: {result.quantum_config.physical_qubits}")
    print(f"      - Shots: {result.quantum_config.shots}")
    print(f"      - Backend: {result.quantum_config.backend_type}")
    print(f"      - Cost: ${result.quantum_config.estimated_cost_usd:.2f}")
    print(f"      - Time: {result.quantum_config.time_to_solution_hours:.2f} hours")

    # Generate visualizations
    print("\n🎨 Generating visualizations...")
    viz_files = []

    # 3D structure
    file1 = engine.visualize_3d_structure(structure, "example1_protein_3d.png")
    viz_files.append(file1)

    # Energy landscape
    file2 = engine.visualize_energy_landscape(result, "example1_energy_landscape.png")
    viz_files.append(file2)

    # Secondary structure
    file3 = protein_viz.visualize_secondary_structure(structure, "example1_secondary.png")
    viz_files.append(file3)

    # Folding pathway
    file4 = protein_viz.visualize_protein_folding_pathway(result, "example1_folding.png")
    viz_files.append(file4)

    print(f"\n✅ Generated {len(viz_files)} visualization files")
    return viz_files


def example_2_metabolic_network():
    """Example 2: Metabolic network quantum optimization"""
    print_section("EXAMPLE 2: Metabolic Network Analysis with Quantum Optimization")

    viz = QuantumMetabolomicsVisualizer()

    # Create glycolysis pathway
    print("📝 Building glycolysis metabolic network...")

    metabolites = {
        "glc": Metabolite("glc", "Glucose", "C6H12O6", 180.16, 5000, "Glycolysis", "carbohydrate"),
        "g6p": Metabolite(
            "g6p", "Glucose-6-P", "C6H13O9P", 260.14, 2000, "Glycolysis", "carbohydrate"
        ),
        "f6p": Metabolite(
            "f6p", "Fructose-6-P", "C6H13O9P", 260.14, 1500, "Glycolysis", "carbohydrate"
        ),
        "fdp": Metabolite(
            "fdp", "Fructose-1,6-BP", "C6H14O12P2", 340.12, 1000, "Glycolysis", "carbohydrate"
        ),
        "g3p": Metabolite(
            "g3p", "Glyceraldehyde-3-P", "C3H7O6P", 170.06, 800, "Glycolysis", "carbohydrate"
        ),
        "13dpg": Metabolite(
            "13dpg",
            "1,3-Bisphosphoglycerate",
            "C3H8O10P2",
            266.04,
            500,
            "Glycolysis",
            "carbohydrate",
        ),
        "3pg": Metabolite(
            "3pg", "3-Phosphoglycerate", "C3H7O7P", 186.06, 1200, "Glycolysis", "carbohydrate"
        ),
        "2pg": Metabolite(
            "2pg", "2-Phosphoglycerate", "C3H7O7P", 186.06, 900, "Glycolysis", "carbohydrate"
        ),
        "pep": Metabolite(
            "pep", "Phosphoenolpyruvate", "C3H5O6P", 168.04, 700, "Glycolysis", "carbohydrate"
        ),
        "pyr": Metabolite("pyr", "Pyruvate", "C3H4O3", 88.06, 3000, "Glycolysis", "carbohydrate"),
    }

    reactions = {
        "HK": Reaction("HK", "Hexokinase", ["glc"], ["g6p"], "HK", False, 10.0),
        "PGI": Reaction("PGI", "Phosphoglucose isomerase", ["g6p"], ["f6p"], "PGI", True, 9.5),
        "PFK": Reaction("PFK", "Phosphofructokinase", ["f6p"], ["fdp"], "PFK", False, 9.0),
        "ALDO": Reaction("ALDO", "Aldolase", ["fdp"], ["g3p"], "ALDO", True, 8.5),
        "GAPDH": Reaction("GAPDH", "Glyceraldehyde-3-P DH", ["g3p"], ["13dpg"], "GAPDH", True, 8.0),
        "PGK": Reaction("PGK", "Phosphoglycerate kinase", ["13dpg"], ["3pg"], "PGK", True, 7.5),
        "PGM": Reaction("PGM", "Phosphoglycerate mutase", ["3pg"], ["2pg"], "PGM", True, 7.0),
        "ENO": Reaction("ENO", "Enolase", ["2pg"], ["pep"], "ENO", True, 6.5),
        "PK": Reaction("PK", "Pyruvate kinase", ["pep"], ["pyr"], "PK", False, 6.0),
    }

    network = MetabolicNetwork(
        metabolites=metabolites, reactions=reactions, name="Glycolysis", organism="E. coli"
    )

    print(f"✅ Network created: {len(metabolites)} metabolites, {len(reactions)} reactions\n")

    # Quantum pathway optimization
    print("⚛️  Performing quantum pathway optimization...")
    config = viz.quantum_pathway_optimization(network, "pyr")

    # Generate visualizations
    print("\n🎨 Generating metabolic visualizations...")
    viz_files = []

    file1 = viz.visualize_metabolic_network(network, "example2_network.png")
    viz_files.append(file1)

    file2 = viz.visualize_metabolite_heatmap(
        network, time_points=[0, 1, 2, 4, 8, 16, 32], output_file="example2_heatmap.png"
    )
    viz_files.append(file2)

    file3 = viz.visualize_flux_analysis(network, "example2_flux.png")
    viz_files.append(file3)

    print(f"\n✅ Generated {len(viz_files)} metabolic visualizations")
    return viz_files


def example_3_bioql_integration():
    """Example 3: BioQL integration for automated workflows"""
    print_section("EXAMPLE 3: BioQL Integration - Automated Queries")

    integrator = BioQLIntegrator()

    # Example BioQL queries
    queries = [
        "@BioQL SELECT protein WHERE name='P53' AND organism='human'",
        "@BioQL SELECT metabolite WHERE pathway='TCA cycle'",
        "@BioQL SELECT drug WHERE target='EGFR' AND phase='approved'",
    ]

    all_results = []

    for query in queries:
        print(f"\n📝 Executing: {query}")

        result = integrator.bioql_to_visualization(query, viz_type="structure_3d")

        if result.get("success"):
            print(f"✅ Success!")
            print(f"   Structures found: {result['num_structures']}")
            for viz in result["visualizations"]:
                print(f"   📊 {viz['structure_name']}")
                print(f"      File: {viz['visualization_file']}")
                qc = viz["quantum_config"]
                print(
                    f"      Qubits: {qc['logical_qubits']} logical, {qc['physical_qubits']} physical"
                )
                print(f"      Cost: ${qc['cost_usd']:.2f}")
        else:
            print(f"❌ Error: {result.get('error')}")

        all_results.append(result)

    return all_results


def example_4_comparative_analysis():
    """Example 4: Compare quantum backends"""
    print_section("EXAMPLE 4: Quantum Backend Comparison")

    optimizer = AdaptiveQuantumOptimizer()

    # Test molecule (medium-sized protein)
    molecule_data = {"num_atoms": 1500, "num_residues": 200, "molecular_weight": 22000}

    backends = ["simulator", "ibm_quantum", "azure_quantum", "aws_braket"]

    print("🔬 Analyzing computational requirements across backends...\n")
    print(f"{'Backend':<20} {'Qubits':>12} {'Shots':>12} {'Time (h)':>12} {'Cost ($)':>12}")
    print("-" * 70)

    results = []
    for backend in backends:
        config = optimizer.optimize(
            molecule_data=molecule_data,
            molecule_type=MoleculeType.PROTEIN,
            viz_type=VisualizationType.CONFORMATIONAL_SAMPLING,
            backend_preference=backend,
        )

        print(
            f"{backend:<20} {config.physical_qubits:>12} {config.shots:>12} "
            f"{config.time_to_solution_hours:>12.2f} {config.estimated_cost_usd:>12.2f}"
        )

        results.append({"backend": backend, "config": config})

    print("\n💡 Recommendation:")
    # Find best cost-performance
    free_options = [r for r in results if r["config"].estimated_cost_usd == 0]
    if free_options:
        print(f"   For testing: Use '{free_options[0]['backend']}' (free)")

    paid_options = [r for r in results if r["config"].estimated_cost_usd > 0]
    if paid_options:
        best_paid = min(paid_options, key=lambda r: r["config"].estimated_cost_usd)
        print(
            f"   For production: Use '{best_paid['backend']}' "
            f"(${best_paid['config'].estimated_cost_usd:.2f}, "
            f"{best_paid['config'].time_to_solution_hours:.1f}h)"
        )

    return results


def example_5_full_pipeline():
    """Example 5: Complete drug discovery pipeline"""
    print_section("EXAMPLE 5: Complete Drug Discovery Pipeline")

    print("🎯 Simulating drug discovery workflow:")
    print("   1. Target protein structure analysis")
    print("   2. Binding site identification")
    print("   3. Ligand conformational sampling")
    print("   4. Docking simulation")
    print("   5. Affinity prediction\n")

    engine = QuantumVizEngine()
    protein_viz = QuantumProteinVisualizer(engine)

    # Step 1: Create target protein
    print("📝 Step 1: Analyzing target protein (EGFR kinase domain)...")
    import numpy as np

    # Create simplified protein structure
    protein_atoms = []
    for i in range(150):  # 150 residues
        x = 5 * np.cos(i * 0.1)
        y = 5 * np.sin(i * 0.1)
        z = i * 0.3
        protein_atoms.append(Atom("C", x, y, z, residue_id=i + 1, atom_id=i))

    protein = MolecularStructure(
        atoms=protein_atoms,
        bonds=[],
        name="EGFR_kinase",
        molecule_type=MoleculeType.PROTEIN,
        metadata={"target": "EGFR", "domain": "kinase"},
    )

    # Step 2: Create ligand
    print("📝 Step 2: Preparing ligand (tyrosine kinase inhibitor)...")
    ligand_atoms = [
        Atom("C", 0, 0, 15, atom_id=0),
        Atom("C", 1.5, 0, 15, atom_id=1),
        Atom("N", 2, 1.3, 15, atom_id=2),
        Atom("O", 0.5, 1.3, 15, atom_id=3),
        Atom("C", -1, 0.5, 15, atom_id=4),
    ]

    ligand = MolecularStructure(
        atoms=ligand_atoms,
        bonds=[Bond(0, 1), Bond(1, 2), Bond(0, 3), Bond(0, 4)],
        name="TKI_inhibitor",
        molecule_type=MoleculeType.SMALL_MOLECULE,
        metadata={"class": "tyrosine_kinase_inhibitor"},
    )

    # Step 3: Quantum conformational sampling of ligand
    print("⚛️  Step 3: Quantum conformational sampling of ligand...")
    ligand_result = engine.quantum_conformation_sampling(ligand, num_conformations=20)

    print(f"   ✅ Sampled {len(ligand_result.conformations)} conformations")
    print(f"   ✅ Quantum backend: {ligand_result.quantum_config.backend_type}")
    print(f"   ✅ Cost: ${ligand_result.quantum_config.estimated_cost_usd:.2f}")

    # Step 4: Visualize binding site
    print("\n🎨 Step 4: Generating binding site visualization...")
    binding_file = protein_viz.visualize_binding_site(protein, ligand, "example5_binding_site.png")

    # Step 5: Energy analysis
    print("📊 Step 5: Analyzing binding energy landscape...")
    energy_file = engine.visualize_energy_landscape(ligand_result, "example5_ligand_energy.png")

    print(f"\n✅ Drug discovery pipeline complete!")
    print(f"   📁 Binding site: {binding_file}")
    print(f"   📁 Energy landscape: {energy_file}")

    # Summary
    print(f"\n📈 Pipeline Summary:")
    print(f"   Target: {protein.name}")
    print(f"   Ligand: {ligand.name}")
    print(f"   Conformations: {len(ligand_result.conformations)}")
    print(f"   Ground state energy: {ligand_result.energy:.2f} kcal/mol")
    print(f"   Total quantum cost: ${ligand_result.quantum_config.estimated_cost_usd:.2f}")

    return {
        "protein": protein,
        "ligand": ligand,
        "result": ligand_result,
        "files": [binding_file, energy_file],
    }


def main():
    """Run all examples"""
    print(
        """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         QUANTUM_GRAPH: Complete Workflow Examples               ║
    ║                                                                  ║
    ║         Quantum-Enhanced Scientific Visualization               ║
    ║         for Advanced Biotechnology Research                     ║
    ║                                                                  ║
    ║         Spectrix R&D / BioQL Team                               ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    )

    # Run all examples
    try:
        # Example 1: Protein folding
        viz_files_1 = example_1_protein_folding()

        # Example 2: Metabolic networks
        viz_files_2 = example_2_metabolic_network()

        # Example 3: BioQL integration
        bioql_results = example_3_bioql_integration()

        # Example 4: Backend comparison
        backend_comparison = example_4_comparative_analysis()

        # Example 5: Full pipeline
        pipeline_result = example_5_full_pipeline()

        # Final summary
        print_section("FINAL SUMMARY")
        print("✅ All examples completed successfully!\n")
        print(
            f"📊 Total visualizations generated: {len(viz_files_1) + len(viz_files_2) + len(pipeline_result['files'])}"
        )
        print(f"⚛️  Quantum backends tested: 4 (simulator, IBM, Azure, AWS)")
        print(f"🧬 BioQL queries executed: 3")
        print(f"🎨 Visualization types: Structure, Energy, Network, Heatmap, Flux, Binding")

        print("\n🎉 Quantum_graph demonstration complete!")
        print("📁 Check current directory for generated visualization files.")

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
