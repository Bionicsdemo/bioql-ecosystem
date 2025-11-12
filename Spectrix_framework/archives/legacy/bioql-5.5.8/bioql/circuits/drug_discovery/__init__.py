"""
Drug discovery specific circuit templates.

This module provides circuit templates optimized for drug discovery
applications including molecular docking, protein folding, and
binding affinity calculations.
"""

from typing import Any, List, Optional
from ..base import (
    CircuitTemplate,
    CircuitCategory,
    ComplexityRating,
    ParameterSpec,
    ResourceEstimate
)


class MolecularDockingCircuit(CircuitTemplate):
    """
    Circuit template for quantum-enhanced molecular docking.

    Uses quantum algorithms to explore conformational space and
    calculate binding energies.

    Example:
        >>> docking = MolecularDockingCircuit()
        >>> circuit = docking.build(
        ...     num_rotatable_bonds=5,
        ...     energy_levels=16,
        ...     optimization_depth=3
        ... )
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="num_rotatable_bonds",
                type="int",
                description="Number of rotatable bonds in ligand",
                required=True,
                range=(1, 20)
            ),
            ParameterSpec(
                name="energy_levels",
                type="int",
                description="Number of energy levels to encode",
                default=8,
                range=(4, 32)
            ),
            ParameterSpec(
                name="optimization_depth",
                type="int",
                description="Depth of optimization layers",
                default=2,
                range=(1, 10)
            ),
            ParameterSpec(
                name="include_electrostatics",
                type="bool",
                description="Include electrostatic interactions",
                default=True
            )
        ]

        super().__init__(
            name="molecular_docking",
            description="Quantum circuit for molecular docking and binding pose prediction",
            category=CircuitCategory.DRUG_DISCOVERY,
            complexity=ComplexityRating.HIGH,
            parameters=parameters,
            tags=["docking", "binding", "drug_discovery", "molecular", "optimization"],
            use_cases=[
                "Protein-ligand docking",
                "Binding pose prediction",
                "Virtual screening of drug candidates",
                "Lead optimization"
            ],
            references=[
                "Quantum Drug Discovery Applications (2023)",
                "Variational Quantum Docking (2022)"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build molecular docking circuit."""
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        return {"type": "molecular_docking_circuit", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate molecular docking circuit resources."""
        num_bonds = kwargs.get("num_rotatable_bonds", 5)
        energy_levels = kwargs.get("energy_levels", 8)
        opt_depth = kwargs.get("optimization_depth", 2)

        # Qubits needed: log2(energy_levels) per bond
        import math
        qubits_per_bond = max(1, int(math.ceil(math.log2(energy_levels))))
        num_qubits = num_bonds * qubits_per_bond

        # Estimate circuit complexity
        gates_per_layer = num_qubits * 3 + num_bonds * 2
        total_gates = gates_per_layer * opt_depth * 2  # Forward + backward
        two_qubit_gates = num_bonds * opt_depth * 3
        depth = opt_depth * 15

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=two_qubit_gates,
            measurement_count=num_qubits,
            execution_time_estimate=0.5 * opt_depth * num_bonds,
            error_budget=0.02
        )


class ProteinFoldingCircuit(CircuitTemplate):
    """
    Circuit template for quantum protein folding simulation.

    Encodes protein structure and uses quantum optimization to find
    low-energy conformations.

    Example:
        >>> folding = ProteinFoldingCircuit()
        >>> circuit = folding.build(
        ...     sequence_length=10,
        ...     lattice_dimensions=2,
        ...     qaoa_layers=3
        ... )
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="sequence_length",
                type="int",
                description="Length of protein sequence",
                required=True,
                range=(3, 50)
            ),
            ParameterSpec(
                name="lattice_dimensions",
                type="int",
                description="Lattice dimensions (2D or 3D)",
                default=2,
                range=(2, 3)
            ),
            ParameterSpec(
                name="qaoa_layers",
                type="int",
                description="Number of QAOA layers",
                default=2,
                range=(1, 8)
            ),
            ParameterSpec(
                name="interaction_model",
                type="str",
                description="Interaction model to use",
                default="hp",
                constraints={"one_of": ["hp", "miyazawa_jernigan", "full"]}
            )
        ]

        super().__init__(
            name="protein_folding",
            description="Quantum circuit for protein structure prediction and folding",
            category=CircuitCategory.DRUG_DISCOVERY,
            complexity=ComplexityRating.VERY_HIGH,
            parameters=parameters,
            tags=["protein", "folding", "structure", "biology", "optimization"],
            use_cases=[
                "Protein structure prediction",
                "Enzyme design",
                "Antibody engineering",
                "Therapeutic protein development"
            ],
            references=[
                "Quantum protein folding (2012)",
                "QAOA for protein folding (2021)"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build protein folding circuit."""
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        return {"type": "protein_folding_circuit", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate protein folding circuit resources."""
        seq_length = kwargs.get("sequence_length", 10)
        dimensions = kwargs.get("lattice_dimensions", 2)
        qaoa_layers = kwargs.get("qaoa_layers", 2)

        # Qubits needed for encoding positions
        import math
        positions_per_residue = 2 ** dimensions
        qubits_per_residue = int(math.ceil(math.log2(positions_per_residue)))
        num_qubits = seq_length * qubits_per_residue

        # QAOA complexity
        gates_per_layer = num_qubits * 4 + seq_length * 3
        total_gates = gates_per_layer * qaoa_layers
        two_qubit_gates = seq_length * qaoa_layers * 2
        depth = qaoa_layers * 20

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=two_qubit_gates,
            measurement_count=num_qubits,
            execution_time_estimate=1.0 * qaoa_layers * seq_length,
            error_budget=0.03
        )


class BindingAffinityCircuit(CircuitTemplate):
    """
    Circuit template for quantum binding affinity calculation.

    Estimates protein-ligand binding affinity using quantum
    energy calculations.

    Example:
        >>> affinity = BindingAffinityCircuit()
        >>> circuit = affinity.build(
        ...     num_atoms=20,
        ...     basis_size=4,
        ...     vqe_layers=3
        ... )
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="num_atoms",
                type="int",
                description="Number of atoms in the system",
                required=True,
                range=(2, 100)
            ),
            ParameterSpec(
                name="basis_size",
                type="int",
                description="Size of basis set for each atom",
                default=4,
                range=(2, 8)
            ),
            ParameterSpec(
                name="vqe_layers",
                type="int",
                description="Number of VQE ansatz layers",
                default=2,
                range=(1, 10)
            ),
            ParameterSpec(
                name="include_solvation",
                type="bool",
                description="Include solvation effects",
                default=False
            )
        ]

        super().__init__(
            name="binding_affinity",
            description="Quantum circuit for protein-ligand binding affinity calculation",
            category=CircuitCategory.DRUG_DISCOVERY,
            complexity=ComplexityRating.HIGH,
            parameters=parameters,
            tags=["binding", "affinity", "energy", "drug_discovery", "vqe"],
            use_cases=[
                "Binding affinity prediction",
                "Lead compound ranking",
                "Structure-activity relationship analysis",
                "Virtual screening"
            ],
            references=[
                "Quantum chemistry for drug discovery (2020)",
                "VQE for binding energy (2021)"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build binding affinity circuit."""
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        return {"type": "binding_affinity_circuit", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate binding affinity circuit resources."""
        num_atoms = kwargs.get("num_atoms", 20)
        basis_size = kwargs.get("basis_size", 4)
        vqe_layers = kwargs.get("vqe_layers", 2)

        # Qubits for molecular orbitals
        import math
        num_orbitals = num_atoms * basis_size
        num_qubits = int(math.ceil(math.log2(num_orbitals))) + num_orbitals // 2

        # VQE circuit complexity
        gates_per_layer = num_qubits * 3 + num_qubits // 2
        total_gates = gates_per_layer * vqe_layers
        two_qubit_gates = (num_qubits // 2) * vqe_layers
        depth = vqe_layers * 10

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=two_qubit_gates,
            measurement_count=100,  # Multiple measurements for energy estimation
            execution_time_estimate=0.8 * vqe_layers * num_atoms,
            error_budget=0.015
        )


# Export all drug discovery circuits
__all__ = [
    "MolecularDockingCircuit",
    "ProteinFoldingCircuit",
    "BindingAffinityCircuit"
]
