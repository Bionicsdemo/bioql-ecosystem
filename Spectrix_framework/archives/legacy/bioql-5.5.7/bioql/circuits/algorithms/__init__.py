"""
Quantum algorithm circuit templates.

This module provides circuit templates for common quantum algorithms
including VQE, QAOA, Grover's algorithm, and more.
"""

from typing import Any, List, Optional
from ..base import (
    CircuitTemplate,
    CircuitCategory,
    ComplexityRating,
    ParameterSpec,
    ResourceEstimate
)


class VQECircuit(CircuitTemplate):
    """
    Variational Quantum Eigensolver (VQE) circuit template.

    VQE is a hybrid quantum-classical algorithm for finding ground state
    energies of molecules and other quantum systems.

    Example:
        >>> vqe = VQECircuit()
        >>> circuit = vqe.build(num_qubits=4, num_layers=2, ansatz="hardware_efficient")
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="num_qubits",
                type="int",
                description="Number of qubits in the circuit",
                required=True,
                range=(1, 100)
            ),
            ParameterSpec(
                name="num_layers",
                type="int",
                description="Number of ansatz layers",
                default=1,
                range=(1, 20)
            ),
            ParameterSpec(
                name="ansatz",
                type="str",
                description="Ansatz type",
                default="hardware_efficient",
                constraints={"one_of": ["hardware_efficient", "uccsd", "custom"]}
            ),
            ParameterSpec(
                name="entanglement",
                type="str",
                description="Entanglement pattern",
                default="linear",
                constraints={"one_of": ["linear", "full", "circular"]}
            )
        ]

        super().__init__(
            name="vqe",
            description="Variational Quantum Eigensolver for ground state energy calculation",
            category=CircuitCategory.ALGORITHM,
            complexity=ComplexityRating.MEDIUM,
            parameters=parameters,
            tags=["vqe", "variational", "optimization", "ground_state", "chemistry"],
            use_cases=[
                "Molecular ground state energy calculation",
                "Quantum chemistry simulations",
                "Material property prediction"
            ],
            references=[
                "Peruzzo et al., Nat. Commun. 5, 4213 (2014)",
                "McClean et al., New J. Phys. 18, 023023 (2016)"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build VQE circuit."""
        # Placeholder - actual implementation would create quantum circuit
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        # Return placeholder
        return {"type": "vqe_circuit", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate VQE circuit resources."""
        num_qubits = kwargs.get("num_qubits", 4)
        num_layers = kwargs.get("num_layers", 1)

        # Estimate based on hardware-efficient ansatz
        gates_per_layer = num_qubits * 2 + (num_qubits - 1)  # RY + RZ + CNOTs
        total_gates = gates_per_layer * num_layers
        two_qubit_gates = (num_qubits - 1) * num_layers
        depth = num_layers * 3  # Approximate

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=two_qubit_gates,
            measurement_count=1,
            execution_time_estimate=0.1 * num_qubits * num_layers
        )


class QAOACircuit(CircuitTemplate):
    """
    Quantum Approximate Optimization Algorithm (QAOA) circuit template.

    QAOA is designed for solving combinatorial optimization problems.

    Example:
        >>> qaoa = QAOACircuit()
        >>> circuit = qaoa.build(num_qubits=6, num_layers=3, problem_type="max_cut")
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="num_qubits",
                type="int",
                description="Number of qubits",
                required=True,
                range=(2, 100)
            ),
            ParameterSpec(
                name="num_layers",
                type="int",
                description="Number of QAOA layers (p parameter)",
                default=1,
                range=(1, 10)
            ),
            ParameterSpec(
                name="problem_type",
                type="str",
                description="Optimization problem type",
                default="max_cut",
                constraints={"one_of": ["max_cut", "tsp", "portfolio", "custom"]}
            )
        ]

        super().__init__(
            name="qaoa",
            description="Quantum Approximate Optimization Algorithm for combinatorial optimization",
            category=CircuitCategory.ALGORITHM,
            complexity=ComplexityRating.MEDIUM,
            parameters=parameters,
            tags=["qaoa", "optimization", "combinatorial", "max_cut"],
            use_cases=[
                "Graph optimization problems",
                "Portfolio optimization",
                "Drug combination optimization"
            ],
            references=[
                "Farhi et al., arXiv:1411.4028 (2014)"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build QAOA circuit."""
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        return {"type": "qaoa_circuit", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate QAOA circuit resources."""
        num_qubits = kwargs.get("num_qubits", 4)
        num_layers = kwargs.get("num_layers", 1)

        # Each layer has mixer + problem Hamiltonian
        gates_per_layer = num_qubits * 4  # Approximate
        total_gates = gates_per_layer * num_layers
        two_qubit_gates = num_qubits * num_layers
        depth = num_layers * 4

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=two_qubit_gates,
            measurement_count=1,
            execution_time_estimate=0.15 * num_qubits * num_layers
        )


class GroverCircuit(CircuitTemplate):
    """
    Grover's search algorithm circuit template.

    Provides quadratic speedup for unstructured search problems.

    Example:
        >>> grover = GroverCircuit()
        >>> circuit = grover.build(num_qubits=5, num_iterations=3)
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="num_qubits",
                type="int",
                description="Number of qubits for search space",
                required=True,
                range=(2, 30)
            ),
            ParameterSpec(
                name="num_iterations",
                type="int",
                description="Number of Grover iterations",
                default=1,
                range=(1, 100)
            )
        ]

        super().__init__(
            name="grover",
            description="Grover's algorithm for quantum search",
            category=CircuitCategory.ALGORITHM,
            complexity=ComplexityRating.MEDIUM,
            parameters=parameters,
            tags=["grover", "search", "amplitude_amplification"],
            use_cases=[
                "Database search",
                "Pattern matching in molecular structures",
                "SAT solving"
            ],
            references=[
                "Grover, Proceedings of STOC 1996"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build Grover circuit."""
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        return {"type": "grover_circuit", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate Grover circuit resources."""
        num_qubits = kwargs.get("num_qubits", 4)
        num_iterations = kwargs.get("num_iterations", 1)

        # Each iteration: oracle + diffusion operator
        gates_per_iteration = num_qubits * 10  # Approximate
        total_gates = gates_per_iteration * num_iterations + num_qubits  # Include initial H gates
        two_qubit_gates = num_qubits * 2 * num_iterations
        depth = num_iterations * 20

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=two_qubit_gates,
            measurement_count=1,
            execution_time_estimate=0.05 * num_iterations
        )


# Export all algorithm circuits
__all__ = [
    "VQECircuit",
    "QAOACircuit",
    "GroverCircuit"
]
