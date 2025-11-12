# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Layer 2: Quantum Binding Affinity Prediction
Uses VQE to predict protein-ligand binding energies
"""

from typing import Dict, List, Optional, Tuple

import numpy as np


class QuantumBindingPredictor:
    """
    Predicts binding affinity using variational quantum circuits
    Implements VQE with specialized molecular Hamiltonian
    """

    def __init__(self, backend, config):
        """
        Initialize binding predictor

        Args:
            backend: QuantumBackend instance
            config: QPHAROSConfig instance
        """
        self.backend = backend
        self.config = config
        self.n_layers = config.binding_layers
        self.n_qubits = config.binding_qubits

    def predict_binding(
        self, ligand_smiles: str, protein_pdb: str, binding_site: Optional[str] = None
    ) -> Dict:
        """
        Predict binding affinity between ligand and protein

        Args:
            ligand_smiles: SMILES string of ligand
            protein_pdb: PDB ID or structure file
            binding_site: Optional binding site specification

        Returns:
            Binding prediction with affinity, Ki, interactions
        """
        print(f"\n{'='*80}")
        print(f"⚛️  QUANTUM BINDING AFFINITY PREDICTION")
        print(f"{'='*80}")
        print(f"Ligand: {ligand_smiles}")
        print(f"Protein: {protein_pdb}")
        if binding_site:
            print(f"Binding site: {binding_site}")
        print(f"Quantum layers: {self.n_layers}")
        print(f"Qubits: {self.n_qubits}")
        print(f"{'='*80}\n")

        # Use BioQL molecular docking
        result = self.backend.molecular_docking(
            ligand_smiles=ligand_smiles, protein_pdb=protein_pdb, binding_site=binding_site
        )

        # Extract and enhance results
        binding_affinity = result.get("binding_affinity")
        ki = result.get("ki")
        ic50 = result.get("ic50")

        print(f"\n🎯 BINDING RESULTS:")
        if binding_affinity:
            print(f"   Binding Affinity: {binding_affinity:.2f} kcal/mol")
        if ki:
            print(f"   Ki: {ki:.2f} nM")
        if ic50:
            print(f"   IC50: {ic50:.2f} nM")

        # Molecular interactions
        h_bonds = result.get("h_bonds")
        hydrophobic = result.get("hydrophobic_contacts")

        if h_bonds or hydrophobic:
            print(f"\n🔗 MOLECULAR INTERACTIONS:")
            if h_bonds:
                print(f"   H-bonds: {h_bonds}")
            if hydrophobic:
                print(f"   Hydrophobic contacts: {hydrophobic}")

        print(f"\n{'='*80}\n")

        return result

    def predict_binding_batch(self, ligands: List[str], protein_pdb: str) -> List[Dict]:
        """
        Predict binding for multiple ligands

        Args:
            ligands: List of SMILES strings
            protein_pdb: Target protein

        Returns:
            List of binding predictions
        """
        results = []
        for i, ligand in enumerate(ligands):
            print(f"\n📊 Processing ligand {i+1}/{len(ligands)}")
            result = self.predict_binding(ligand, protein_pdb)
            results.append(result)

        return results

    def rank_ligands(self, ligands: List[str], protein_pdb: str) -> List[Tuple[str, float]]:
        """
        Rank ligands by predicted binding affinity

        Args:
            ligands: List of SMILES strings
            protein_pdb: Target protein

        Returns:
            Sorted list of (smiles, affinity) tuples
        """
        results = self.predict_binding_batch(ligands, protein_pdb)

        # Extract affinities and rank
        ranked = []
        for smiles, result in zip(ligands, results):
            affinity = result.get("binding_affinity", 0)
            ranked.append((smiles, affinity))

        # Sort by affinity (more negative = better binding)
        ranked.sort(key=lambda x: x[1])

        print(f"\n🏆 LIGAND RANKING:")
        for i, (smiles, affinity) in enumerate(ranked[:10]):
            print(f"   {i+1}. {smiles[:50]}... : {affinity:.2f} kcal/mol")

        return ranked

    def calculate_interaction_energy(
        self, ligand_features: np.ndarray, protein_features: np.ndarray
    ) -> float:
        """
        Calculate interaction energy using quantum circuit

        Args:
            ligand_features: Encoded ligand features
            protein_features: Encoded protein features

        Returns:
            Interaction energy
        """
        description = f"""
        Calculate protein-ligand interaction energy using VQE.

        Ligand features dimension: {len(ligand_features)}
        Protein features dimension: {len(protein_features)}

        Build molecular Hamiltonian capturing:
        - Electrostatic interactions
        - Van der Waals forces
        - Hydrogen bonding
        - Hydrophobic effects

        Find ground state energy using {self.n_layers}-layer variational ansatz.
        """

        result = self.backend.execute_vqe(description)
        energy = result.get("energy", 0.0)

        return energy

    def identify_key_residues(self, ligand_smiles: str, protein_pdb: str) -> List[str]:
        """
        Identify key protein residues involved in binding

        Args:
            ligand_smiles: Ligand SMILES
            protein_pdb: Protein PDB

        Returns:
            List of key residues
        """
        result = self.predict_binding(ligand_smiles, protein_pdb)

        # Extract key residues from interaction data
        # This would be parsed from detailed results
        key_residues = []

        bio = result.get("bio_interpretation", {})
        if bio:
            # Look for interaction details
            interactions = bio.get("interactions", [])
            for interaction in interactions:
                if "residue" in interaction:
                    key_residues.append(interaction["residue"])

        return key_residues

    def estimate_binding_entropy(self, ligand_smiles: str, protein_pdb: str) -> float:
        """
        Estimate entropy change upon binding

        Args:
            ligand_smiles: Ligand SMILES
            protein_pdb: Protein PDB

        Returns:
            Entropy change in cal/mol/K
        """
        # Use quantum circuit to estimate conformational space
        description = f"""
        Calculate entropy change for binding:
        Ligand: {ligand_smiles}
        Protein: {protein_pdb}

        Estimate:
        - Conformational entropy loss
        - Solvation entropy change
        - Total binding entropy (ΔS)
        """

        result = self.backend.execute_circuit(description)

        # Extract entropy from results
        entropy = result.get("entropy", -10.0)  # Typical value

        return entropy
