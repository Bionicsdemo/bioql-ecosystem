# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Layer 1: Quantum Molecular Encoding
Encodes molecular structure into quantum states using graph representation
"""

from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np


class QuantumMolecularEncoder:
    """
    Encodes molecular graphs into quantum circuits
    Uses 3 qubits per atom to encode atomic properties
    """

    def __init__(self, backend, config):
        """
        Initialize molecular encoder

        Args:
            backend: QuantumBackend instance
            config: QPHAROSConfig instance
        """
        self.backend = backend
        self.config = config
        self.qubits_per_atom = config.qubits_per_atom

    def encode_molecule(self, molecule_graph: nx.Graph) -> Dict:
        """
        Encode molecular structure into quantum state

        Args:
            molecule_graph: NetworkX graph with atom nodes and bond edges

        Returns:
            Dictionary with encoding information and quantum circuit
        """
        n_atoms = len(molecule_graph.nodes)
        n_qubits = n_atoms * self.qubits_per_atom

        print(f"\n{'='*80}")
        print(f"🧬 QUANTUM MOLECULAR ENCODING")
        print(f"{'='*80}")
        print(f"Atoms: {n_atoms}")
        print(f"Bonds: {len(molecule_graph.edges)}")
        print(f"Qubits required: {n_qubits} ({self.qubits_per_atom} per atom)")

        # Build circuit description for BioQL
        circuit_description = self._build_encoding_description(molecule_graph)

        # Execute encoding circuit
        result = self.backend.execute_circuit(circuit_description)

        # Store molecular graph for later use
        result["molecule_graph"] = molecule_graph
        result["n_qubits"] = n_qubits
        result["n_atoms"] = n_atoms

        print(f"\n✅ Molecular encoding complete")
        print(f"{'='*80}\n")

        return result

    def encode_from_smiles(self, smiles: str) -> Dict:
        """
        Encode molecule from SMILES string

        Args:
            smiles: SMILES representation

        Returns:
            Encoding result
        """
        # Convert SMILES to graph
        molecule_graph = self._smiles_to_graph(smiles)
        return self.encode_molecule(molecule_graph)

    def _build_encoding_description(self, mol_graph: nx.Graph) -> str:
        """Build circuit description for BioQL"""

        atoms_info = []
        for node_id, node_data in mol_graph.nodes(data=True):
            atom_type = node_data.get("element", "C")
            atoms_info.append(f"Atom {node_id}: {atom_type}")

        bonds_info = []
        for u, v, edge_data in mol_graph.edges(data=True):
            bond_type = edge_data.get("bond_type", "single")
            bonds_info.append(f"Bond {u}-{v}: {bond_type}")

        description = f"""
        Encode molecular structure into quantum state:

        Molecular Graph:
        - Atoms: {len(mol_graph.nodes)}
        {chr(10).join([f"  {info}" for info in atoms_info])}

        - Bonds: {len(mol_graph.edges)}
        {chr(10).join([f"  {info}" for info in bonds_info])}

        Encoding scheme:
        - Use {self.qubits_per_atom} qubits per atom
        - Encode atomic properties (mass, electronegativity, radius) as rotation angles
        - Create entanglement between bonded atoms
        - Apply bond-type-specific quantum gates

        Generate quantum state that preserves:
        1. Atomic identities and properties
        2. Bonding topology
        3. Molecular geometry
        """

        return description

    def _smiles_to_graph(self, smiles: str) -> nx.Graph:
        """
        Convert SMILES to molecular graph
        Uses RDKit if available, otherwise creates simple graph
        """
        try:
            from rdkit import Chem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {smiles}")

            # Build NetworkX graph from RDKit molecule
            G = nx.Graph()

            # Add atoms as nodes
            for atom in mol.GetAtoms():
                G.add_node(
                    atom.GetIdx(),
                    element=atom.GetSymbol(),
                    atomic_num=atom.GetAtomicNum(),
                    charge=atom.GetFormalCharge(),
                    aromatic=atom.GetIsAromatic(),
                )

            # Add bonds as edges
            for bond in mol.GetBonds():
                bond_type_map = {
                    Chem.BondType.SINGLE: "single",
                    Chem.BondType.DOUBLE: "double",
                    Chem.BondType.TRIPLE: "triple",
                    Chem.BondType.AROMATIC: "aromatic",
                }
                G.add_edge(
                    bond.GetBeginAtomIdx(),
                    bond.GetEndAtomIdx(),
                    bond_type=bond_type_map.get(bond.GetBondType(), "single"),
                )

            return G

        except ImportError:
            print("⚠️  RDKit not available. Using simplified molecular graph.")
            return self._create_simple_graph(smiles)

    def _create_simple_graph(self, smiles: str) -> nx.Graph:
        """Create simplified molecular graph without RDKit"""
        # Very basic SMILES parser for demonstration
        G = nx.Graph()

        # Count atoms (very simplified)
        atom_count = 0
        for char in smiles:
            if char.isupper():
                G.add_node(atom_count, element=char)
                if atom_count > 0:
                    G.add_edge(atom_count - 1, atom_count, bond_type="single")
                atom_count += 1

        return G

    def calculate_encoding_cost(self, n_atoms: int) -> Dict:
        """
        Calculate quantum resource requirements for encoding

        Args:
            n_atoms: Number of atoms in molecule

        Returns:
            Resource estimates
        """
        n_qubits = n_atoms * self.qubits_per_atom
        circuit_depth = 3 + n_atoms  # initialization + entanglement layers

        return self.backend.estimate_resources(n_qubits, circuit_depth)

    def compare_molecules(self, molecule1_graph: nx.Graph, molecule2_graph: nx.Graph) -> float:
        """
        Compare two molecules using quantum state fidelity

        Args:
            molecule1_graph: First molecule
            molecule2_graph: Second molecule

        Returns:
            Similarity score (0-1)
        """
        # Encode both molecules
        state1 = self.encode_molecule(molecule1_graph)
        state2 = self.encode_molecule(molecule2_graph)

        # Calculate quantum state overlap
        # This would use quantum state tomography in practice
        similarity = self._calculate_state_similarity(state1, state2)

        return similarity

    def _calculate_state_similarity(self, state1: Dict, state2: Dict) -> float:
        """Calculate quantum state similarity"""
        # Simplified similarity based on structure
        n_atoms_1 = state1.get("n_atoms", 0)
        n_atoms_2 = state2.get("n_atoms", 0)

        if n_atoms_1 == 0 or n_atoms_2 == 0:
            return 0.0

        # Size similarity
        size_sim = 1.0 - abs(n_atoms_1 - n_atoms_2) / max(n_atoms_1, n_atoms_2)

        return size_sim
