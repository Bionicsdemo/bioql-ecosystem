"""
Reusable circuit templates and building blocks.

This module provides common circuit patterns and building blocks
that can be composed to create more complex circuits.
"""

from typing import Any, List, Optional
from ..base import (
    CircuitTemplate,
    CircuitCategory,
    ComplexityRating,
    ParameterSpec,
    ResourceEstimate
)


class HardwareEfficientAnsatz(CircuitTemplate):
    """
    Hardware-efficient ansatz template.

    A parameterized circuit optimized for near-term quantum hardware
    with minimal gate count and depth.

    Example:
        >>> ansatz = HardwareEfficientAnsatz()
        >>> circuit = ansatz.build(num_qubits=4, num_layers=2)
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="num_qubits",
                type="int",
                description="Number of qubits",
                required=True,
                range=(1, 100)
            ),
            ParameterSpec(
                name="num_layers",
                type="int",
                description="Number of ansatz layers",
                default=1,
                range=(1, 50)
            ),
            ParameterSpec(
                name="rotation_gates",
                type="list",
                description="List of single-qubit rotation gates to use",
                default=["RY", "RZ"]
            ),
            ParameterSpec(
                name="entanglement",
                type="str",
                description="Entanglement pattern",
                default="linear",
                constraints={"one_of": ["linear", "circular", "full"]}
            )
        ]

        super().__init__(
            name="hardware_efficient_ansatz",
            description="Hardware-efficient variational ansatz for NISQ devices",
            category=CircuitCategory.UTILITY,
            complexity=ComplexityRating.LOW,
            parameters=parameters,
            tags=["ansatz", "variational", "vqe", "hardware_efficient"],
            use_cases=[
                "VQE ansatz",
                "Variational quantum algorithms",
                "NISQ-friendly circuits"
            ],
            references=[
                "Kandala et al., Nature 549, 242-246 (2017)"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build hardware-efficient ansatz."""
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        return {"type": "hardware_efficient_ansatz", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate ansatz resources."""
        num_qubits = kwargs.get("num_qubits", 4)
        num_layers = kwargs.get("num_layers", 1)
        rotation_gates = kwargs.get("rotation_gates", ["RY", "RZ"])
        entanglement = kwargs.get("entanglement", "linear")

        # Calculate gates per layer
        rotation_count = len(rotation_gates)
        single_qubit_gates = num_qubits * rotation_count

        if entanglement == "linear":
            two_qubit_gates_per_layer = num_qubits - 1
        elif entanglement == "circular":
            two_qubit_gates_per_layer = num_qubits
        else:  # full
            two_qubit_gates_per_layer = num_qubits * (num_qubits - 1) // 2

        total_gates = (single_qubit_gates + two_qubit_gates_per_layer) * num_layers
        total_two_qubit = two_qubit_gates_per_layer * num_layers
        depth = num_layers * (rotation_count + 2)

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=total_two_qubit,
            measurement_count=0,
            execution_time_estimate=0.01 * depth
        )


class UCCSDAnsatz(CircuitTemplate):
    """
    Unitary Coupled Cluster Singles and Doubles (UCCSD) ansatz.

    Chemistry-inspired ansatz for molecular simulations.

    Example:
        >>> uccsd = UCCSDAnsatz()
        >>> circuit = uccsd.build(num_qubits=8, num_electrons=4)
    """

    def __init__(self):
        parameters = [
            ParameterSpec(
                name="num_qubits",
                type="int",
                description="Number of qubits (spin-orbitals)",
                required=True,
                range=(2, 100)
            ),
            ParameterSpec(
                name="num_electrons",
                type="int",
                description="Number of electrons",
                required=True,
                range=(1, 50)
            ),
            ParameterSpec(
                name="include_singles",
                type="bool",
                description="Include single excitations",
                default=True
            ),
            ParameterSpec(
                name="include_doubles",
                type="bool",
                description="Include double excitations",
                default=True
            )
        ]

        super().__init__(
            name="uccsd_ansatz",
            description="Unitary Coupled Cluster Singles and Doubles ansatz for quantum chemistry",
            category=CircuitCategory.CHEMISTRY,
            complexity=ComplexityRating.HIGH,
            parameters=parameters,
            tags=["uccsd", "chemistry", "vqe", "molecular"],
            use_cases=[
                "Molecular ground state calculations",
                "Quantum chemistry simulations",
                "Electronic structure calculations"
            ],
            references=[
                "Romero et al., Quantum Sci. Technol. 4, 014008 (2019)"
            ]
        )

    def build(self, **kwargs) -> Any:
        """Build UCCSD ansatz."""
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            raise ValueError(error)

        return {"type": "uccsd_ansatz", "params": kwargs}

    def estimate_resources(self, **kwargs) -> ResourceEstimate:
        """Estimate UCCSD ansatz resources."""
        num_qubits = kwargs.get("num_qubits", 8)
        num_electrons = kwargs.get("num_electrons", 4)
        include_singles = kwargs.get("include_singles", True)
        include_doubles = kwargs.get("include_doubles", True)

        # Estimate number of excitations
        num_occupied = num_electrons
        num_virtual = num_qubits - num_electrons

        singles_count = num_occupied * num_virtual if include_singles else 0
        doubles_count = (num_occupied * (num_occupied - 1) * num_virtual * (num_virtual - 1)) // 4 if include_doubles else 0

        total_excitations = singles_count + doubles_count

        # Each excitation is a parameterized gate sequence
        gates_per_excitation = 20  # Approximate
        total_gates = total_excitations * gates_per_excitation
        two_qubit_gates = total_excitations * 10
        depth = total_excitations * 15

        return ResourceEstimate(
            num_qubits=num_qubits,
            circuit_depth=depth,
            gate_count=total_gates,
            two_qubit_gates=two_qubit_gates,
            measurement_count=0,
            execution_time_estimate=0.5 * total_excitations,
            error_budget=0.02
        )


# Export all template circuits
__all__ = [
    "HardwareEfficientAnsatz",
    "UCCSDAnsatz"
]
