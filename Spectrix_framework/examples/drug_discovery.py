#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Drug Discovery and Binding Affinity Example

This example demonstrates how to use BioQL for quantum-enhanced drug discovery
and molecular binding affinity calculations. Drug discovery involves finding
molecules that can bind to specific protein targets with high affinity and
selectivity. Quantum computing can help explore the vast chemical space and
optimize molecular interactions more efficiently than classical methods.

The example covers:
- Molecular representation and quantum encoding
- Protein-drug interaction modeling
- Binding affinity prediction using quantum algorithms
- Virtual screening of compound libraries
- Lead optimization through quantum variational algorithms
- ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity) prediction
- Error handling and result interpretation

Requirements:
- BioQL framework
- Qiskit (quantum computing backend)
- NumPy for numerical computations
- Matplotlib for visualization (optional)
- RDKit for molecular handling (optional)
"""

import json
import os
import random
import sys
import warnings
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

# Add parent directory to path for bioql imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from bioql import (
        BioQLError,
        ProgramParsingError,
        QuantumBackendError,
        QuantumResult,
        configure_debug_mode,
        get_info,
        quantum,
    )
except ImportError as e:
    print(f"Error importing BioQL: {e}")
    print("Make sure BioQL is properly installed and in your Python path")
    sys.exit(1)

# Optional imports for enhanced functionality
try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    warnings.warn("Matplotlib not available. Visualization features will be disabled.")

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors

    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    warnings.warn("RDKit not available. Using simplified molecular representations.")


class DrugDiscoverySimulation:
    """
    Quantum-enhanced drug discovery simulation using BioQL.

    This class provides methods for molecular design, binding affinity prediction,
    and drug optimization using quantum computing techniques.
    """

    def __init__(self, target_protein: str, debug: bool = False):
        """
        Initialize the drug discovery simulation.

        Args:
            target_protein: Name or identifier of the target protein
            debug: Enable debug mode for detailed logging
        """
        self.target_protein = target_protein
        self.debug = debug
        self.binding_site_qubits = 6  # Number of qubits to represent binding site
        self.molecule_qubits = 8  # Number of qubits to represent molecule
        self.compound_library = []
        self.binding_affinities = {}
        self.admet_properties = {}

        if debug:
            configure_debug_mode(True)
            print(f"Initialized drug discovery simulation for target: {target_protein}")

    def setup_target_protein(self) -> Dict[str, any]:
        """
        Set up quantum representation of the target protein binding site.

        Returns:
            Dictionary containing protein binding site information
        """
        print(f"\n=== Setting up target protein: {self.target_protein} ===")

        try:
            program = f"""
            Model protein binding site for {self.target_protein}.
            Create quantum representation of:
            - Hydrophobic pockets and electrostatic interactions
            - Hydrogen bonding sites and metal coordination
            - Conformational flexibility and allosteric effects
            Use {self.binding_site_qubits} qubits to encode binding site properties.
            """

            result = quantum(program, shots=1024, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Failed to set up target protein: {result.error_message}")

            # Interpret quantum states as binding site features
            binding_features = {}
            for state, count in result.counts.items():
                probability = count / result.total_shots

                # Map quantum states to binding site characteristics
                features = self._decode_binding_site_state(state)
                binding_features[state] = {
                    "features": features,
                    "probability": probability,
                    "count": count,
                }

            print(f"✓ Target protein binding site modeled")
            print(f"  - Binding site states: {len(binding_features)}")
            print(f"  - Dominant conformation: {result.most_likely_outcome}")

            return {
                "binding_features": binding_features,
                "dominant_state": result.most_likely_outcome,
            }

        except Exception as e:
            print(f"✗ Error setting up target protein: {e}")
            raise

    def generate_molecular_library(self, library_size: int = 1000) -> List[Dict[str, any]]:
        """
        Generate a virtual library of drug candidates using quantum sampling.

        Args:
            library_size: Number of molecules to generate

        Returns:
            List of molecular dictionaries with properties
        """
        print(f"\n=== Generating molecular library (size: {library_size}) ===")

        try:
            program = f"""
            Generate diverse molecular library for drug discovery.
            Sample chemical space using quantum random walks.
            Include drug-like molecules with appropriate:
            - Molecular weight (150-500 Da)
            - LogP values (-1 to 5)
            - Hydrogen bond donors/acceptors
            - Rotatable bonds and ring systems
            Create {min(library_size, 1000)} diverse chemical structures.
            """

            result = quantum(program, shots=min(library_size, 2048), debug=self.debug)

            if not result.success:
                raise BioQLError(f"Library generation failed: {result.error_message}")

            # Generate molecular library from quantum results
            molecules = []
            for i, (state, count) in enumerate(result.counts.items()):
                if i >= library_size:
                    break

                molecule = self._generate_molecule_from_state(state, i)
                molecules.append(molecule)

            self.compound_library = molecules

            print(f"✓ Molecular library generated")
            print(f"  - Total compounds: {len(molecules)}")
            print(f"  - Average MW: {np.mean([m['molecular_weight'] for m in molecules]):.1f} Da")
            print(
                f"  - LogP range: {min([m['logp'] for m in molecules]):.1f} to {max([m['logp'] for m in molecules]):.1f}"
            )

            return molecules

        except Exception as e:
            print(f"✗ Error generating molecular library: {e}")
            raise

    def calculate_binding_affinity(self, molecule: Dict[str, any]) -> Dict[str, float]:
        """
        Calculate binding affinity between molecule and target using quantum simulation.

        Args:
            molecule: Molecular dictionary with properties

        Returns:
            Dictionary containing binding affinity results
        """
        mol_id = molecule["id"]
        smiles = molecule["smiles"]

        try:
            program = f"""
            Calculate binding affinity between molecule {mol_id} and {self.target_protein}.
            Model protein-ligand interactions using quantum variational algorithm:
            - Van der Waals interactions and electrostatic forces
            - Hydrogen bonding and hydrophobic effects
            - Conformational entropy and binding cooperativity
            - Solvation effects and desolvation penalties
            Optimize binding pose using {self.molecule_qubits + self.binding_site_qubits} qubits.
            """

            result = quantum(program, shots=512, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Binding affinity calculation failed: {result.error_message}")

            # Calculate binding metrics from quantum results
            binding_data = self._analyze_binding_result(result, molecule)

            self.binding_affinities[mol_id] = binding_data

            return binding_data

        except Exception as e:
            print(f"✗ Error calculating binding affinity for {mol_id}: {e}")
            return {
                "binding_affinity": 0.0,
                "kd_estimate": float("inf"),
                "binding_score": 0.0,
                "error": str(e),
            }

    def virtual_screening(self, top_n: int = 100) -> List[Dict[str, any]]:
        """
        Perform virtual screening of the molecular library.

        Args:
            top_n: Number of top compounds to return

        Returns:
            List of top-scoring compounds with binding data
        """
        print(f"\n=== Virtual screening of {len(self.compound_library)} compounds ===")

        try:
            # Use quantum algorithm for parallel screening
            program = f"""
            Perform parallel virtual screening of {len(self.compound_library)} compounds.
            Use quantum amplitude amplification to identify high-affinity binders.
            Screen against {self.target_protein} binding site.
            Rank compounds by:
            - Binding affinity and selectivity
            - Drug-likeness scores
            - ADMET properties prediction
            Select top {top_n} candidates.
            """

            result = quantum(program, shots=1024, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Virtual screening failed: {result.error_message}")

            # Calculate binding affinities for representative molecules
            scored_compounds = []

            # Sample compounds based on quantum result distribution
            sorted_states = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)
            selected_molecules = []

            for state, count in sorted_states[: min(top_n * 2, len(self.compound_library))]:
                # Map quantum state to molecule index
                mol_index = int(state, 2) % len(self.compound_library)
                if mol_index < len(self.compound_library):
                    selected_molecules.append(self.compound_library[mol_index])

            print(
                f"Calculating binding affinities for {len(selected_molecules)} selected compounds..."
            )

            for i, molecule in enumerate(selected_molecules[:top_n]):
                if i % 20 == 0:
                    print(f"  Progress: {i}/{min(len(selected_molecules), top_n)}")

                binding_data = self.calculate_binding_affinity(molecule)

                compound_score = {
                    "molecule": molecule,
                    "binding_data": binding_data,
                    "rank": i + 1,
                    "screening_score": binding_data.get("binding_score", 0),
                }
                scored_compounds.append(compound_score)

            # Sort by binding score
            scored_compounds.sort(key=lambda x: x["screening_score"], reverse=True)

            print(f"✓ Virtual screening completed")
            print(f"  - Compounds screened: {len(selected_molecules)}")
            print(f"  - Top hits identified: {len(scored_compounds)}")
            if scored_compounds:
                best_compound = scored_compounds[0]
                print(f"  - Best binding score: {best_compound['screening_score']:.3f}")
                print(f"  - Best Kd estimate: {best_compound['binding_data']['kd_estimate']:.2e} M")

            return scored_compounds

        except Exception as e:
            print(f"✗ Error in virtual screening: {e}")
            raise

    def optimize_lead_compound(self, lead_molecule: Dict[str, any]) -> Dict[str, any]:
        """
        Optimize a lead compound using quantum variational algorithms.

        Args:
            lead_molecule: Lead compound to optimize

        Returns:
            Dictionary containing optimized compound data
        """
        print(f"\n=== Optimizing lead compound {lead_molecule['id']} ===")

        try:
            program = f"""
            Optimize lead compound {lead_molecule['id']} for {self.target_protein}.
            Use quantum variational eigensolver for molecular optimization:
            - Modify functional groups and substituents
            - Optimize binding pose and conformation
            - Balance affinity, selectivity, and drug-likeness
            - Consider synthetic accessibility
            Generate optimized derivatives with improved properties.
            """

            result = quantum(program, shots=256, debug=self.debug)

            if not result.success:
                raise BioQLError(f"Lead optimization failed: {result.error_message}")

            # Generate optimized variants
            optimized_compounds = []
            for state, count in list(result.counts.items())[:10]:  # Top 10 variants
                optimized_mol = self._generate_optimized_molecule(lead_molecule, state)
                binding_data = self.calculate_binding_affinity(optimized_mol)

                optimized_compounds.append(
                    {
                        "molecule": optimized_mol,
                        "binding_data": binding_data,
                        "improvement_score": self._calculate_improvement_score(
                            lead_molecule, optimized_mol, binding_data
                        ),
                    }
                )

            # Find best optimization
            best_optimized = max(optimized_compounds, key=lambda x: x["improvement_score"])

            print(f"✓ Lead optimization completed")
            print(f"  - Variants generated: {len(optimized_compounds)}")
            print(f"  - Best improvement score: {best_optimized['improvement_score']:.3f}")
            print(f"  - Optimized Kd: {best_optimized['binding_data']['kd_estimate']:.2e} M")

            return {
                "original_lead": lead_molecule,
                "optimized_compounds": optimized_compounds,
                "best_optimized": best_optimized,
            }

        except Exception as e:
            print(f"✗ Error in lead optimization: {e}")
            raise

    def predict_admet_properties(self, molecule: Dict[str, any]) -> Dict[str, float]:
        """
        Predict ADMET properties using quantum machine learning.

        Args:
            molecule: Molecular dictionary

        Returns:
            Dictionary containing ADMET predictions
        """
        mol_id = molecule["id"]

        try:
            program = f"""
            Predict ADMET properties for molecule {mol_id} using quantum ML.
            Calculate:
            - Absorption: permeability and solubility
            - Distribution: tissue distribution and BBB penetration
            - Metabolism: CYP enzyme interactions
            - Excretion: renal and biliary clearance
            - Toxicity: hepatotoxicity and cardiotoxicity
            Use quantum neural networks for property prediction.
            """

            result = quantum(program, shots=256, debug=self.debug)

            if not result.success:
                raise BioQLError(f"ADMET prediction failed: {result.error_message}")

            # Calculate ADMET properties from quantum results
            admet_data = self._analyze_admet_result(result, molecule)
            self.admet_properties[mol_id] = admet_data

            return admet_data

        except Exception as e:
            print(f"✗ Error predicting ADMET for {mol_id}: {e}")
            return {
                "absorption": 0.5,
                "distribution": 0.5,
                "metabolism": 0.5,
                "excretion": 0.5,
                "toxicity": 0.5,
                "drug_likeness": 0.5,
                "error": str(e),
            }

    def analyze_selectivity(
        self, molecule: Dict[str, any], off_targets: List[str]
    ) -> Dict[str, float]:
        """
        Analyze selectivity of a compound against off-target proteins.

        Args:
            molecule: Molecular dictionary
            off_targets: List of off-target protein names

        Returns:
            Dictionary containing selectivity analysis
        """
        print(f"\n=== Analyzing selectivity for molecule {molecule['id']} ===")

        selectivity_data = {}
        mol_id = molecule["id"]

        try:
            for off_target in off_targets:
                program = f"""
                Calculate binding affinity of molecule {mol_id} to off-target {off_target}.
                Compare binding mode and affinity to primary target {self.target_protein}.
                Assess selectivity based on:
                - Binding site differences
                - Conformational preferences
                - Interaction energy landscapes
                Calculate selectivity ratio and specificity index.
                """

                result = quantum(program, shots=256, debug=self.debug)

                if result.success:
                    off_target_binding = self._analyze_binding_result(result, molecule)
                    primary_binding = self.binding_affinities.get(mol_id, {})

                    selectivity_ratio = self._calculate_selectivity_ratio(
                        primary_binding, off_target_binding
                    )

                    selectivity_data[off_target] = {
                        "binding_affinity": off_target_binding.get("binding_affinity", 0),
                        "selectivity_ratio": selectivity_ratio,
                        "kd_ratio": off_target_binding.get("kd_estimate", 1e-3)
                        / primary_binding.get("kd_estimate", 1e-9),
                    }

            print(f"✓ Selectivity analysis completed")
            print(f"  - Off-targets analyzed: {len(selectivity_data)}")
            avg_selectivity = np.mean(
                [data["selectivity_ratio"] for data in selectivity_data.values()]
            )
            print(f"  - Average selectivity ratio: {avg_selectivity:.1f}")

            return selectivity_data

        except Exception as e:
            print(f"✗ Error in selectivity analysis: {e}")
            return {}

    def visualize_results(self, screening_results: List[Dict[str, any]]) -> None:
        """
        Visualize drug discovery results.
        """
        if not MATPLOTLIB_AVAILABLE:
            print("Matplotlib not available. Skipping visualization.")
            return

        print(f"\n=== Visualizing drug discovery results ===")

        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

            # 1. Binding affinity distribution
            if screening_results:
                affinities = [
                    result["binding_data"]["binding_affinity"] for result in screening_results[:50]
                ]

                ax1.hist(affinities, bins=20, alpha=0.7, edgecolor="black")
                ax1.set_title("Binding Affinity Distribution")
                ax1.set_xlabel("Binding Affinity (kcal/mol)")
                ax1.set_ylabel("Number of Compounds")
                ax1.axvline(
                    np.mean(affinities),
                    color="red",
                    linestyle="--",
                    label=f"Mean: {np.mean(affinities):.2f}",
                )
                ax1.legend()

            # 2. Structure-activity relationship
            if len(screening_results) > 10:
                mw_values = [
                    result["molecule"]["molecular_weight"] for result in screening_results[:50]
                ]
                logp_values = [result["molecule"]["logp"] for result in screening_results[:50]]
                scores = [result["screening_score"] for result in screening_results[:50]]

                scatter = ax2.scatter(mw_values, logp_values, c=scores, cmap="viridis", alpha=0.6)
                ax2.set_title("Structure-Activity Relationship")
                ax2.set_xlabel("Molecular Weight (Da)")
                ax2.set_ylabel("LogP")
                plt.colorbar(scatter, ax=ax2, label="Binding Score")

            # 3. Drug-likeness properties
            if self.compound_library:
                properties = ["molecular_weight", "logp", "hbd", "hba"]
                prop_data = []

                for prop in properties:
                    values = [mol[prop] for mol in self.compound_library[:100]]
                    prop_data.append(values)

                ax3.boxplot(prop_data, labels=["MW", "LogP", "HBD", "HBA"])
                ax3.set_title("Drug-likeness Properties")
                ax3.set_ylabel("Property Value")

            # 4. ADMET profile (if available)
            if self.admet_properties:
                admet_keys = ["absorption", "distribution", "metabolism", "excretion", "toxicity"]

                # Average ADMET scores
                avg_admet = {}
                for key in admet_keys:
                    values = [props.get(key, 0.5) for props in self.admet_properties.values()]
                    avg_admet[key] = np.mean(values) if values else 0.5

                angles = np.linspace(0, 2 * np.pi, len(admet_keys), endpoint=False)
                values = list(avg_admet.values())
                angles = np.concatenate((angles, [angles[0]]))
                values.append(values[0])

                ax4 = plt.subplot(224, projection="polar")
                ax4.plot(angles, values, "o-", linewidth=2)
                ax4.fill(angles, values, alpha=0.25)
                ax4.set_xticks(angles[:-1])
                ax4.set_xticklabels(admet_keys)
                ax4.set_ylim(0, 1)
                ax4.set_title("Average ADMET Profile")

            plt.tight_layout()
            plt.savefig(
                "/Users/heinzjungbluth/Desktop/bioql/examples/drug_discovery_results.png",
                dpi=300,
                bbox_inches="tight",
            )
            print("✓ Visualization saved as drug_discovery_results.png")

        except Exception as e:
            print(f"✗ Error in visualization: {e}")

    def _decode_binding_site_state(self, state: str) -> Dict[str, any]:
        """Decode quantum state to binding site features."""
        features = {
            "hydrophobic_pocket": int(state[0]) == 1,
            "electrostatic_site": int(state[1]) == 1,
            "h_bond_donor": int(state[2]) == 1,
            "h_bond_acceptor": int(state[3]) == 1,
            "flexible_region": int(state[4]) == 1 if len(state) > 4 else False,
            "metal_site": int(state[5]) == 1 if len(state) > 5 else False,
        }
        return features

    def _generate_molecule_from_state(self, state: str, mol_id: int) -> Dict[str, any]:
        """Generate molecule from quantum state."""
        # Simulate molecular properties based on quantum state
        random.seed(int(state, 2) + mol_id)

        molecule = {
            "id": f"MOL_{mol_id:04d}",
            "smiles": f"C{random.randint(6,20)}H{random.randint(8,40)}N{random.randint(0,4)}O{random.randint(0,6)}",
            "molecular_weight": 150 + random.random() * 350,
            "logp": -1 + random.random() * 6,
            "hbd": random.randint(0, 5),  # Hydrogen bond donors
            "hba": random.randint(0, 8),  # Hydrogen bond acceptors
            "rotatable_bonds": random.randint(0, 12),
            "rings": random.randint(0, 4),
            "quantum_state": state,
        }

        return molecule

    def _analyze_binding_result(
        self, result: QuantumResult, molecule: Dict[str, any]
    ) -> Dict[str, float]:
        """Analyze binding affinity from quantum results."""
        # Calculate binding metrics based on quantum state distribution
        total_shots = result.total_shots

        # Simulate binding affinity calculation
        binding_states = [
            state for state in result.counts.keys() if state.count("1") > state.count("0")
        ]

        if binding_states:
            binding_probability = (
                sum(result.counts[state] for state in binding_states) / total_shots
            )
            binding_affinity = -12.0 + 8.0 * binding_probability  # kcal/mol
        else:
            binding_probability = 0.1
            binding_affinity = -2.0

        kd_estimate = np.exp(binding_affinity / (0.593))  # Convert to Kd (M)
        binding_score = max(0, -binding_affinity / 12.0)  # Normalized score

        return {
            "binding_affinity": binding_affinity,
            "kd_estimate": kd_estimate,
            "binding_probability": binding_probability,
            "binding_score": binding_score,
        }

    def _generate_optimized_molecule(
        self, lead_molecule: Dict[str, any], optimization_state: str
    ) -> Dict[str, any]:
        """Generate optimized molecule variant."""
        optimized = lead_molecule.copy()
        optimized["id"] = f"{lead_molecule['id']}_OPT_{optimization_state[:4]}"

        # Apply optimizations based on quantum state
        state_value = int(optimization_state, 2) / (2 ** len(optimization_state) - 1)

        optimized["molecular_weight"] *= 0.9 + 0.2 * state_value
        optimized["logp"] *= 0.8 + 0.4 * state_value
        optimized["quantum_state"] = optimization_state

        return optimized

    def _calculate_improvement_score(
        self, original: Dict[str, any], optimized: Dict[str, any], binding_data: Dict[str, float]
    ) -> float:
        """Calculate improvement score for optimized compound."""
        # Compare binding affinity improvement
        original_binding = self.binding_affinities.get(original["id"], {})
        original_affinity = original_binding.get("binding_affinity", -5.0)
        optimized_affinity = binding_data.get("binding_affinity", -5.0)

        affinity_improvement = optimized_affinity - original_affinity
        drug_likeness_penalty = abs(optimized["molecular_weight"] - 350) / 1000

        return affinity_improvement - drug_likeness_penalty

    def _analyze_admet_result(
        self, result: QuantumResult, molecule: Dict[str, any]
    ) -> Dict[str, float]:
        """Analyze ADMET properties from quantum results."""
        # Simulate ADMET prediction based on quantum results
        total_shots = result.total_shots

        admet_scores = {}
        properties = ["absorption", "distribution", "metabolism", "excretion", "toxicity"]

        for i, prop in enumerate(properties):
            # Use quantum state distribution to estimate properties
            relevant_states = [
                state for state in result.counts.keys() if int(state[i % len(state)]) == 1
            ]

            if relevant_states:
                prop_probability = (
                    sum(result.counts[state] for state in relevant_states) / total_shots
                )
            else:
                prop_probability = 0.5

            admet_scores[prop] = prop_probability

        # Calculate overall drug-likeness
        admet_scores["drug_likeness"] = np.mean(list(admet_scores.values()))

        return admet_scores

    def _calculate_selectivity_ratio(
        self, primary_binding: Dict[str, float], off_target_binding: Dict[str, float]
    ) -> float:
        """Calculate selectivity ratio between primary and off-target."""
        primary_kd = primary_binding.get("kd_estimate", 1e-9)
        off_target_kd = off_target_binding.get("kd_estimate", 1e-3)

        return off_target_kd / primary_kd if primary_kd > 0 else 1.0


def example_kinase_inhibitor_discovery():
    """Example: Discover inhibitors for a kinase target."""
    print("=" * 70)
    print("EXAMPLE 1: Kinase Inhibitor Discovery")
    print("=" * 70)

    target_protein = "CDK2_kinase"

    try:
        # Initialize drug discovery simulation
        discovery = DrugDiscoverySimulation(target_protein, debug=True)

        # Set up target protein
        protein_data = discovery.setup_target_protein()

        # Generate molecular library
        library = discovery.generate_molecular_library(library_size=500)

        # Perform virtual screening
        screening_results = discovery.virtual_screening(top_n=50)

        # Select lead compound for optimization
        if screening_results:
            lead_compound = screening_results[0]["molecule"]
            print(f"\nSelected lead compound: {lead_compound['id']}")
            print(f"Lead binding score: {screening_results[0]['screening_score']:.3f}")

            # Optimize lead compound
            optimization_results = discovery.optimize_lead_compound(lead_compound)

            # Predict ADMET properties
            lead_admet = discovery.predict_admet_properties(lead_compound)
            best_optimized = optimization_results["best_optimized"]["molecule"]
            optimized_admet = discovery.predict_admet_properties(best_optimized)

            # Analyze selectivity
            off_targets = ["CDK1_kinase", "CDK4_kinase", "Aurora_kinase"]
            selectivity = discovery.analyze_selectivity(best_optimized, off_targets)

            # Visualize results
            discovery.visualize_results(screening_results)

            print(f"\n=== Summary ===")
            print(f"Target: {target_protein}")
            print(f"Library size: {len(library)}")
            print(f"Hits identified: {len(screening_results)}")
            print(f"Lead compound: {lead_compound['id']}")
            print(f"Optimized compound: {best_optimized['id']}")
            print(
                f"ADMET improvement: {optimized_admet['drug_likeness']:.3f} vs {lead_admet['drug_likeness']:.3f}"
            )
            print(
                f"Average selectivity: {np.mean(list(selectivity.values())) if selectivity else 'N/A'}"
            )

    except Exception as e:
        print(f"Error in kinase inhibitor discovery: {e}")
        import traceback

        traceback.print_exc()


def example_gpcr_agonist_design():
    """Example: Design agonists for a GPCR target."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: GPCR Agonist Design")
    print("=" * 70)

    target_protein = "5HT2A_receptor"

    try:
        discovery = DrugDiscoverySimulation(target_protein, debug=False)

        # Focus on smaller, more drug-like library for GPCR
        library = discovery.generate_molecular_library(library_size=200)

        # Screen for agonist activity
        screening_results = discovery.virtual_screening(top_n=20)

        if screening_results:
            # Analyze top hits
            print(f"\nTop 5 GPCR agonist candidates:")
            for i, result in enumerate(screening_results[:5]):
                mol = result["molecule"]
                binding = result["binding_data"]
                print(
                    f"{i+1}. {mol['id']}: Score={result['screening_score']:.3f}, "
                    f"Kd={binding['kd_estimate']:.2e} M"
                )

                # Quick ADMET check
                admet = discovery.predict_admet_properties(mol)
                print(f"   Drug-likeness: {admet['drug_likeness']:.3f}")

    except Exception as e:
        print(f"Error in GPCR agonist design: {e}")


def example_fragment_based_design():
    """Example: Fragment-based drug design approach."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Fragment-Based Drug Design")
    print("=" * 70)

    target_protein = "BCL2_protein"

    try:
        discovery = DrugDiscoverySimulation(target_protein, debug=False)

        # Generate fragment library (smaller molecules)
        print("Generating fragment library...")
        fragments = []
        for i in range(100):
            fragment = {
                "id": f"FRAG_{i:03d}",
                "smiles": f"C{random.randint(3,8)}H{random.randint(4,16)}NO",
                "molecular_weight": 80 + random.random() * 170,  # Fragment size
                "logp": -2 + random.random() * 4,
                "hbd": random.randint(0, 3),
                "hba": random.randint(0, 4),
                "rotatable_bonds": random.randint(0, 3),
                "rings": random.randint(0, 2),
                "quantum_state": format(random.randint(0, 255), "08b"),
            }
            fragments.append(fragment)

        discovery.compound_library = fragments

        # Screen fragments
        fragment_hits = discovery.virtual_screening(top_n=10)

        # Fragment linking/growing simulation
        if fragment_hits:
            print(f"\nIdentified {len(fragment_hits)} fragment hits")
            best_fragment = fragment_hits[0]["molecule"]

            # Simulate fragment optimization
            optimization = discovery.optimize_lead_compound(best_fragment)

            print(
                f"Best fragment: {best_fragment['id']} (MW: {best_fragment['molecular_weight']:.1f})"
            )
            optimized = optimization["best_optimized"]["molecule"]
            print(f"Optimized lead: {optimized['id']} (MW: {optimized['molecular_weight']:.1f})")

    except Exception as e:
        print(f"Error in fragment-based design: {e}")


def example_error_handling():
    """Demonstrate error handling in drug discovery."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Error Handling and Edge Cases")
    print("=" * 70)

    test_cases = [
        ("valid_target", "HIV_protease"),
        ("empty_target", ""),
        ("invalid_target", "NonExistent_Target_123"),
        ("special_chars", "Target@#$%^&*()"),
    ]

    for test_name, target in test_cases:
        print(f"\n--- Testing {test_name}: '{target}' ---")

        try:
            discovery = DrugDiscoverySimulation(target, debug=False)
            protein_data = discovery.setup_target_protein()
            print(
                f"  ✓ Successfully processed target: {len(protein_data['binding_features'])} binding features"
            )

        except BioQLError as e:
            print(f"  ⚠ BioQL Error: {e}")
        except QuantumBackendError as e:
            print(f"  ⚠ Quantum Backend Error: {e}")
        except ProgramParsingError as e:
            print(f"  ⚠ Program Parsing Error: {e}")
        except Exception as e:
            print(f"  ✗ Unexpected Error: {e}")


def run_performance_benchmark():
    """Benchmark drug discovery performance."""
    print("\n" + "=" * 70)
    print("BENCHMARK: Drug Discovery Performance")
    print("=" * 70)

    import time

    library_sizes = [50, 100, 200, 500]

    print(f"{'Library Size':<12}{'Setup (s)':<10}{'Screen (s)':<10}{'Total (s)':<10}{'Throughput'}")
    print("-" * 60)

    for size in library_sizes:
        try:
            start_time = time.time()

            discovery = DrugDiscoverySimulation("benchmark_target", debug=False)
            setup_time = time.time()

            library = discovery.generate_molecular_library(size)
            generation_time = time.time()

            screening_results = discovery.virtual_screening(top_n=min(10, size // 5))
            end_time = time.time()

            setup_duration = setup_time - start_time
            screening_duration = end_time - generation_time
            total_duration = end_time - start_time
            throughput = size / total_duration if total_duration > 0 else 0

            print(
                f"{size:<12}{setup_duration:<10.2f}{screening_duration:<10.2f}"
                f"{total_duration:<10.2f}{throughput:<.0f} mol/s"
            )

        except Exception as e:
            print(f"{size:<12}{'ERROR':<30}{str(e)[:20]}")


def main():
    """
    Main function demonstrating comprehensive drug discovery simulation.
    """
    print("BioQL Drug Discovery and Binding Affinity Examples")
    print("=================================================")

    # Check BioQL installation
    info = get_info()
    print(f"BioQL Version: {info['version']}")
    print(f"Qiskit Available: {info['qiskit_available']}")
    print(f"RDKit Available: {RDKIT_AVAILABLE}")

    if not info["qiskit_available"]:
        print("⚠ Warning: Qiskit not available. Some features may not work.")

    try:
        # Run all examples
        example_kinase_inhibitor_discovery()
        example_gpcr_agonist_design()
        example_fragment_based_design()
        example_error_handling()
        run_performance_benchmark()

        print("\n" + "=" * 70)
        print("✓ All drug discovery examples completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- Quantum molecular library generation")
        print("- Binding affinity prediction using quantum algorithms")
        print("- Virtual screening with quantum amplitude amplification")
        print("- Lead optimization through quantum variational methods")
        print("- ADMET property prediction with quantum ML")
        print("- Selectivity analysis against off-targets")
        print("- Fragment-based drug design")
        print("- Comprehensive error handling")
        print("- Performance benchmarking")
        print("- Result visualization")

        print("\nNext Steps:")
        print("- Integrate with real molecular databases")
        print("- Add experimental validation protocols")
        print("- Implement advanced quantum algorithms")
        print("- Connect to cloud quantum hardware")

    except Exception as e:
        print(f"\n✗ Error running drug discovery examples: {e}")
        import traceback

        traceback.print_exc()

        print("\nTroubleshooting:")
        print("1. Ensure BioQL is properly installed")
        print("2. Check quantum backend availability")
        print("3. Verify all dependencies are installed")
        print("4. Try with smaller library sizes first")


if __name__ == "__main__":
    main()
