# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Circuit Builder Module
======================

Converts molecular complexity data to quantum circuits for execution.
Supports multiple molecule types and generates VQE-like ansatz circuits
suitable for molecular simulation.

Molecule Types:
- protein: Protein folding and structure
- drug: Drug-target binding
- metabolomics: Metabolic pathway analysis
- antibody: Antibody-antigen interactions

Author: BioQL Team / Quantum_graph Integration
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter, ParameterVector
    from qiskit.circuit.library import EfficientSU2, RealAmplitudes, TwoLocal

    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    logging.warning("Qiskit not available")

logger = logging.getLogger(__name__)


@dataclass
class MolecularData:
    """Molecular complexity data structure"""

    molecule_type: str  # protein, drug, metabolomics, antibody
    complexity: float  # 0.0 to 1.0
    num_atoms: int
    num_bonds: int
    energy_estimate: Optional[float] = None
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class CircuitBuilderError(Exception):
    """Exception raised for circuit building errors"""

    pass


class MolecularCircuitBuilder:
    """
    Builder for quantum circuits from molecular data.

    Creates variational quantum circuits suitable for molecular
    simulation using VQE (Variational Quantum Eigensolver) approaches.

    Example:
        >>> builder = MolecularCircuitBuilder()
        >>> mol_data = MolecularData(
        ...     molecule_type='protein',
        ...     complexity=0.7,
        ...     num_atoms=24,
        ...     num_bonds=26
        ... )
        >>> circuit = builder.build_circuit(mol_data)
        >>> print(f"Circuit has {circuit.num_qubits} qubits")
    """

    # Mapping of molecule types to suggested qubit counts
    MOLECULE_QUBIT_MAP = {
        "protein": 8,  # Protein folding - medium complexity
        "drug": 6,  # Small molecules - lower complexity
        "metabolomics": 10,  # Pathway networks - higher complexity
        "antibody": 12,  # Large biomolecules - high complexity
        "general": 4,  # Default fallback
    }

    # Ansatz types for different molecules
    ANSATZ_MAP = {
        "protein": "two_local",
        "drug": "efficient_su2",
        "metabolomics": "real_amplitudes",
        "antibody": "two_local",
        "general": "two_local",
    }

    def __init__(self):
        """Initialize circuit builder"""
        if not QISKIT_AVAILABLE:
            raise CircuitBuilderError("Qiskit not available. Install: pip install qiskit")
        logger.info("🔧 MolecularCircuitBuilder initialized")

    def build_circuit(
        self,
        mol_data: MolecularData,
        custom_qubits: Optional[int] = None,
        custom_depth: Optional[int] = None,
    ) -> QuantumCircuit:
        """
        Build quantum circuit from molecular data.

        Args:
            mol_data: Molecular data structure
            custom_qubits: Override default qubit count
            custom_depth: Override default circuit depth

        Returns:
            Parameterized quantum circuit

        Raises:
            CircuitBuilderError: If circuit generation fails
        """
        # Determine number of qubits
        num_qubits = custom_qubits or self._estimate_qubits(mol_data)

        # Determine circuit depth (complexity-based)
        depth = custom_depth or self._estimate_depth(mol_data)

        # Select ansatz type
        ansatz_type = self.ANSATZ_MAP.get(mol_data.molecule_type, self.ANSATZ_MAP["general"])

        logger.info(
            f"Building {ansatz_type} circuit: "
            f"{num_qubits} qubits, depth={depth}, "
            f"molecule_type={mol_data.molecule_type}"
        )

        try:
            # Create variational ansatz
            circuit = self._create_ansatz(num_qubits, depth, ansatz_type, mol_data)

            # Add measurements
            circuit.measure_all()

            logger.info(f"✅ Circuit built: {circuit.depth()} gates, {circuit.num_qubits} qubits")
            return circuit

        except Exception as e:
            raise CircuitBuilderError(f"Failed to build circuit: {e}")

    def _estimate_qubits(self, mol_data: MolecularData) -> int:
        """
        Estimate required qubits based on molecular data.

        Uses molecule type and complexity to determine optimal qubit count.
        """
        base_qubits = self.MOLECULE_QUBIT_MAP.get(
            mol_data.molecule_type, self.MOLECULE_QUBIT_MAP["general"]
        )

        # Adjust based on complexity
        if mol_data.complexity > 0.8:
            # High complexity - add more qubits
            adjusted_qubits = int(base_qubits * 1.5)
        elif mol_data.complexity < 0.3:
            # Low complexity - can use fewer qubits
            adjusted_qubits = max(4, int(base_qubits * 0.75))
        else:
            adjusted_qubits = base_qubits

        # Also consider number of atoms (rough heuristic)
        if mol_data.num_atoms > 0:
            # Use log scale: more atoms need more qubits but not linearly
            atom_qubits = max(4, int(np.log2(mol_data.num_atoms) + 2))
            adjusted_qubits = max(adjusted_qubits, atom_qubits)

        # Cap at reasonable limits
        return min(32, max(4, adjusted_qubits))

    def _estimate_depth(self, mol_data: MolecularData) -> int:
        """
        Estimate circuit depth (repetitions) based on complexity.

        More complex molecules need deeper circuits for accurate simulation.
        """
        # Base depth on complexity
        if mol_data.complexity > 0.8:
            depth = 5
        elif mol_data.complexity > 0.6:
            depth = 4
        elif mol_data.complexity > 0.3:
            depth = 3
        else:
            depth = 2

        return depth

    def _create_ansatz(
        self, num_qubits: int, depth: int, ansatz_type: str, mol_data: MolecularData
    ) -> QuantumCircuit:
        """
        Create variational ansatz circuit.

        Args:
            num_qubits: Number of qubits
            depth: Circuit depth (repetitions)
            ansatz_type: Type of ansatz (two_local, efficient_su2, etc.)
            mol_data: Molecular data for customization

        Returns:
            Parameterized quantum circuit
        """
        if ansatz_type == "two_local":
            # TwoLocal ansatz - good for general molecular systems
            circuit = TwoLocal(
                num_qubits,
                rotation_blocks=["ry", "rz"],
                entanglement_blocks="cx",
                entanglement="linear",
                reps=depth,
                insert_barriers=True,
            )

        elif ansatz_type == "efficient_su2":
            # EfficientSU2 - compact representation for small molecules
            circuit = EfficientSU2(
                num_qubits, reps=depth, entanglement="linear", insert_barriers=True
            )

        elif ansatz_type == "real_amplitudes":
            # RealAmplitudes - good for chemical problems
            circuit = RealAmplitudes(
                num_qubits,
                reps=depth,
                entanglement="full" if num_qubits <= 6 else "linear",
                insert_barriers=True,
            )

        else:
            # Fallback to basic TwoLocal
            circuit = TwoLocal(
                num_qubits,
                rotation_blocks=["ry", "rz"],
                entanglement_blocks="cx",
                entanglement="linear",
                reps=depth,
            )

        return circuit

    def build_from_complexity(
        self, molecule_type: str, complexity: float, num_qubits: Optional[int] = None
    ) -> QuantumCircuit:
        """
        Build circuit from basic complexity score.

        Convenience method when full molecular data is not available.

        Args:
            molecule_type: Type of molecule (protein, drug, etc.)
            complexity: Complexity score (0.0 to 1.0)
            num_qubits: Optional override for qubit count

        Returns:
            Quantum circuit

        Example:
            >>> builder = MolecularCircuitBuilder()
            >>> circuit = builder.build_from_complexity('protein', 0.65)
            >>> print(circuit.num_qubits)
        """
        # Create basic molecular data
        mol_data = MolecularData(
            molecule_type=molecule_type,
            complexity=complexity,
            num_atoms=0,  # Unknown
            num_bonds=0,  # Unknown
        )

        return self.build_circuit(mol_data, custom_qubits=num_qubits)

    def add_hamiltonian_encoding(
        self, circuit: QuantumCircuit, hamiltonian_params: Dict[str, float]
    ) -> QuantumCircuit:
        """
        Add Hamiltonian encoding to circuit.

        For molecular simulations, encodes molecular Hamiltonian terms.

        Args:
            circuit: Base quantum circuit
            hamiltonian_params: Hamiltonian parameters (e.g., coupling strengths)

        Returns:
            Circuit with Hamiltonian encoding added
        """
        # This would add problem-specific Hamiltonian terms
        # For now, return circuit as-is
        logger.warning("Hamiltonian encoding not yet implemented")
        return circuit

    def optimize_for_backend(
        self, circuit: QuantumCircuit, backend_name: str, optimization_level: int = 3
    ) -> QuantumCircuit:
        """
        Optimize circuit for specific backend.

        Args:
            circuit: Circuit to optimize
            backend_name: Target backend name
            optimization_level: Optimization level (0-3)

        Returns:
            Optimized circuit
        """
        from qiskit import transpile

        # This is a placeholder - in production would transpile for actual backend
        logger.info(f"Optimizing circuit for {backend_name}, level={optimization_level}")

        # For now, just return original circuit
        # Real implementation would use:
        # optimized = transpile(circuit, backend, optimization_level=optimization_level)

        return circuit


def build_molecular_circuit(
    num_qubits: int, molecule_type: str = "general", complexity: float = 0.5
) -> QuantumCircuit:
    """
    Convenience function to build molecular circuit.

    Args:
        num_qubits: Number of qubits
        molecule_type: Type of molecule
        complexity: Complexity score (0.0 to 1.0)

    Returns:
        Quantum circuit for molecular simulation

    Example:
        >>> circuit = build_molecular_circuit(6, 'drug', 0.4)
        >>> print(circuit.num_qubits)
        6
    """
    builder = MolecularCircuitBuilder()

    mol_data = MolecularData(
        molecule_type=molecule_type, complexity=complexity, num_atoms=0, num_bonds=0
    )

    return builder.build_circuit(mol_data, custom_qubits=num_qubits)


def convert_molecular_data_to_circuit(mol_data: Dict[str, Any]) -> QuantumCircuit:
    """
    Convert molecular data dictionary to quantum circuit.

    Args:
        mol_data: Dictionary with molecular information
                 Required keys: molecule_type, complexity
                 Optional keys: num_atoms, num_bonds, properties

    Returns:
        Quantum circuit

    Example:
        >>> mol_data = {
        ...     'molecule_type': 'protein',
        ...     'complexity': 0.7,
        ...     'num_atoms': 24,
        ...     'num_bonds': 26
        ... }
        >>> circuit = convert_molecular_data_to_circuit(mol_data)
    """
    # Extract required fields
    molecule_type = mol_data.get("molecule_type", "general")
    complexity = mol_data.get("complexity", 0.5)
    num_atoms = mol_data.get("num_atoms", 0)
    num_bonds = mol_data.get("num_bonds", 0)
    properties = mol_data.get("properties", {})

    # Create MolecularData object
    molecular_data = MolecularData(
        molecule_type=molecule_type,
        complexity=complexity,
        num_atoms=num_atoms,
        num_bonds=num_bonds,
        properties=properties,
    )

    # Build circuit
    builder = MolecularCircuitBuilder()
    return builder.build_circuit(molecular_data)


def create_protein_circuit(num_residues: int, folding_complexity: float = 0.5) -> QuantumCircuit:
    """
    Create circuit specifically for protein folding simulation.

    Args:
        num_residues: Number of amino acid residues
        folding_complexity: Complexity of folding problem (0.0 to 1.0)

    Returns:
        Quantum circuit for protein simulation

    Example:
        >>> circuit = create_protein_circuit(num_residues=20, folding_complexity=0.8)
        >>> print(f"Circuit depth: {circuit.depth()}")
    """
    mol_data = MolecularData(
        molecule_type="protein",
        complexity=folding_complexity,
        num_atoms=num_residues * 10,  # Rough estimate: ~10 atoms per residue
        num_bonds=num_residues * 11,  # Rough estimate
        properties={"num_residues": num_residues},
    )

    builder = MolecularCircuitBuilder()
    return builder.build_circuit(mol_data)


def create_drug_circuit(molecular_weight: float, binding_affinity: float = 0.5) -> QuantumCircuit:
    """
    Create circuit for drug-target binding simulation.

    Args:
        molecular_weight: Molecular weight of drug compound
        binding_affinity: Expected binding affinity (0.0 to 1.0)

    Returns:
        Quantum circuit for drug simulation

    Example:
        >>> circuit = create_drug_circuit(molecular_weight=450.0, binding_affinity=0.7)
    """
    # Estimate atoms from molecular weight (rough heuristic)
    num_atoms = int(molecular_weight / 15)  # ~15 Da per atom average

    mol_data = MolecularData(
        molecule_type="drug",
        complexity=binding_affinity,
        num_atoms=num_atoms,
        num_bonds=num_atoms - 1,  # Rough estimate
        properties={"molecular_weight": molecular_weight, "binding_affinity": binding_affinity},
    )

    builder = MolecularCircuitBuilder()
    return builder.build_circuit(mol_data)


# Module-level logger configuration
logging.basicConfig(level=logging.INFO)
