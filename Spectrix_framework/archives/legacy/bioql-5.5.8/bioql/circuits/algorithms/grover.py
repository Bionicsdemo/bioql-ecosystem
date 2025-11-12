"""
Grover's Algorithm Circuit Implementation

This module provides a pre-built implementation of Grover's quantum search
algorithm, optimized for searching unstructured databases and finding marked
states with quadratic speedup over classical algorithms.
"""

import math
from typing import Callable, List, Optional, Union

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import GroverOperator
import numpy as np

from ..templates.base import CircuitTemplate, CircuitBackend


class GroverCircuit(CircuitTemplate):
    """
    Grover's Algorithm Quantum Circuit.

    Implements Grover's quantum search algorithm for finding marked states
    in an unstructured search space with O(√N) complexity, providing quadratic
    speedup over classical O(N) search.

    The algorithm consists of:
    1. Initialization: Create superposition of all states
    2. Oracle: Mark target states with phase flip
    3. Diffusion: Amplify marked states
    4. Repeat iterations for optimal amplification

    Attributes:
        num_qubits: Number of qubits (search space size = 2^num_qubits)
        target_states: List of target state indices to search for
        num_iterations: Number of Grover iterations (auto-calculated if None)

    Example:
        >>> # Search for state |101⟩ in 3-qubit space
        >>> grover = GroverCircuit(num_qubits=3, target_states=[5])
        >>> result = grover.execute(shots=1024)
        >>> print(result.counts)
        {'101': 950, '000': 20, ...}  # |101⟩ is highly amplified
        >>>
        >>> # Search for multiple states
        >>> grover = GroverCircuit(num_qubits=4, target_states=[3, 7, 11])
        >>> grover.optimize_iterations()  # Get optimal iteration count
        3
    """

    def __init__(
        self,
        num_qubits: int,
        target_states: List[int],
        num_iterations: Optional[int] = None,
        backend: CircuitBackend = CircuitBackend.SIMULATOR
    ):
        """
        Initialize Grover's algorithm circuit.

        Args:
            num_qubits: Number of qubits for search space
            target_states: List of target state indices (e.g., [5] for |101⟩)
            num_iterations: Number of Grover iterations (auto-optimized if None)
            backend: Quantum backend to use

        Raises:
            ValueError: If invalid parameters provided

        Example:
            >>> grover = GroverCircuit(num_qubits=5, target_states=[10, 20])
        """
        if num_qubits < 1:
            raise ValueError("num_qubits must be at least 1")

        if not target_states:
            raise ValueError("target_states cannot be empty")

        max_state = 2 ** num_qubits
        if any(state < 0 or state >= max_state for state in target_states):
            raise ValueError(f"target_states must be in range [0, {max_state-1}]")

        super().__init__(
            name=f"Grover Search ({num_qubits} qubits)",
            description=f"Grover's algorithm searching for states {target_states}",
            num_qubits=num_qubits,
            backend=backend
        )

        self.target_states = sorted(target_states)
        self.num_iterations = num_iterations or self.optimize_iterations()

        logger.info(
            f"Initialized Grover circuit: {num_qubits} qubits, "
            f"{len(target_states)} target(s), {self.num_iterations} iterations"
        )

    def build_circuit(self) -> QuantumCircuit:
        """
        Build the complete Grover search circuit.

        Constructs:
        1. Superposition initialization (Hadamard gates)
        2. Grover iterations (Oracle + Diffusion)
        3. Measurement

        Returns:
            QuantumCircuit: Complete Grover circuit

        Example:
            >>> grover = GroverCircuit(num_qubits=3, target_states=[5])
            >>> circuit = grover.build_circuit()
            >>> print(circuit)
        """
        # Create quantum and classical registers
        qreg = QuantumRegister(self.num_qubits, 'q')
        creg = ClassicalRegister(self.num_qubits, 'c')
        circuit = QuantumCircuit(qreg, creg)

        # Step 1: Initialize superposition
        circuit.h(range(self.num_qubits))

        # Step 2: Apply Grover iterations
        for iteration in range(self.num_iterations):
            # Apply oracle
            self.add_oracle(circuit)

            # Apply diffusion operator
            self.add_diffusion(circuit)

        # Step 3: Measurement
        circuit.measure(range(self.num_qubits), range(self.num_qubits))

        logger.debug(
            f"Built Grover circuit: depth={circuit.depth()}, "
            f"gates={len(circuit.data)}"
        )

        return circuit

    def add_oracle(self, circuit: Optional[QuantumCircuit] = None) -> QuantumCircuit:
        """
        Add oracle operator to mark target states.

        The oracle flips the phase of target states:
        |x⟩ → -|x⟩ if x is a target state
        |x⟩ → |x⟩  otherwise

        Args:
            circuit: Circuit to add oracle to (creates new if None)

        Returns:
            QuantumCircuit: Circuit with oracle added

        Example:
            >>> grover = GroverCircuit(num_qubits=3, target_states=[5])
            >>> qc = QuantumCircuit(3)
            >>> grover.add_oracle(qc)
        """
        if circuit is None:
            qreg = QuantumRegister(self.num_qubits, 'q')
            circuit = QuantumCircuit(qreg)

        # Mark each target state with phase flip
        for target in self.target_states:
            # Convert target to binary and apply X gates to create the state
            binary = format(target, f'0{self.num_qubits}b')

            # Flip qubits that should be 0 in target state
            for i, bit in enumerate(binary):
                if bit == '0':
                    circuit.x(i)

            # Multi-controlled Z gate (marks the state)
            if self.num_qubits == 1:
                circuit.z(0)
            elif self.num_qubits == 2:
                circuit.cz(0, 1)
            else:
                # Use multi-controlled Z
                circuit.h(self.num_qubits - 1)
                circuit.mcx(list(range(self.num_qubits - 1)), self.num_qubits - 1)
                circuit.h(self.num_qubits - 1)

            # Flip qubits back
            for i, bit in enumerate(binary):
                if bit == '0':
                    circuit.x(i)

        return circuit

    def add_diffusion(self, circuit: Optional[QuantumCircuit] = None) -> QuantumCircuit:
        """
        Add diffusion operator (inversion about average).

        The diffusion operator amplifies marked states:
        D = 2|s⟩⟨s| - I, where |s⟩ is the equal superposition

        Args:
            circuit: Circuit to add diffusion to (creates new if None)

        Returns:
            QuantumCircuit: Circuit with diffusion operator added

        Example:
            >>> grover = GroverCircuit(num_qubits=3, target_states=[5])
            >>> qc = QuantumCircuit(3)
            >>> grover.add_diffusion(qc)
        """
        if circuit is None:
            qreg = QuantumRegister(self.num_qubits, 'q')
            circuit = QuantumCircuit(qreg)

        # Diffusion operator: 2|s⟩⟨s| - I
        # Step 1: Apply H gates
        circuit.h(range(self.num_qubits))

        # Step 2: Apply X gates
        circuit.x(range(self.num_qubits))

        # Step 3: Multi-controlled Z
        if self.num_qubits == 1:
            circuit.z(0)
        elif self.num_qubits == 2:
            circuit.cz(0, 1)
        else:
            circuit.h(self.num_qubits - 1)
            circuit.mcx(list(range(self.num_qubits - 1)), self.num_qubits - 1)
            circuit.h(self.num_qubits - 1)

        # Step 4: Apply X gates
        circuit.x(range(self.num_qubits))

        # Step 5: Apply H gates
        circuit.h(range(self.num_qubits))

        return circuit

    def optimize_iterations(self) -> int:
        """
        Calculate optimal number of Grover iterations.

        The optimal number of iterations is approximately:
        π/4 * √(N/M), where N is search space size and M is number of targets

        Returns:
            int: Optimal number of iterations

        Example:
            >>> grover = GroverCircuit(num_qubits=5, target_states=[10])
            >>> optimal = grover.optimize_iterations()
            >>> print(f"Optimal iterations: {optimal}")
            Optimal iterations: 4
        """
        N = 2 ** self.num_qubits  # Total search space
        M = len(self.target_states)  # Number of solutions

        # Optimal iterations: π/4 * √(N/M)
        optimal = int(math.pi / 4 * math.sqrt(N / M))

        # Ensure at least 1 iteration
        optimal = max(1, optimal)

        logger.debug(
            f"Optimal iterations for {self.num_qubits} qubits, "
            f"{M} targets: {optimal}"
        )

        return optimal

    def get_success_probability(self) -> float:
        """
        Calculate theoretical success probability.

        Returns:
            float: Probability of measuring a target state (0.0 to 1.0)

        Example:
            >>> grover = GroverCircuit(num_qubits=3, target_states=[5])
            >>> prob = grover.get_success_probability()
            >>> print(f"Success probability: {prob:.2%}")
            Success probability: 94.53%
        """
        N = 2 ** self.num_qubits
        M = len(self.target_states)
        k = self.num_iterations

        # Theoretical success probability after k iterations
        theta = math.asin(math.sqrt(M / N))
        probability = math.sin((2 * k + 1) * theta) ** 2

        return probability

    def validate_result(self, counts: dict) -> dict:
        """
        Validate and analyze execution results.

        Args:
            counts: Measurement counts from circuit execution

        Returns:
            dict: Analysis including success rate and distribution

        Example:
            >>> grover = GroverCircuit(num_qubits=3, target_states=[5])
            >>> result = grover.execute(shots=1024)
            >>> analysis = grover.validate_result(result.counts)
            >>> print(analysis['success_rate'])
            0.945
        """
        total_shots = sum(counts.values())
        target_counts = 0

        # Count shots that measured target states
        for state_str, count in counts.items():
            state_int = int(state_str, 2)
            if state_int in self.target_states:
                target_counts += count

        success_rate = target_counts / total_shots if total_shots > 0 else 0.0
        theoretical_prob = self.get_success_probability()

        return {
            'success_rate': success_rate,
            'theoretical_probability': theoretical_prob,
            'total_shots': total_shots,
            'target_counts': target_counts,
            'target_distribution': {
                state: counts.get(format(state, f'0{self.num_qubits}b'), 0)
                for state in self.target_states
            }
        }


__all__ = ['GroverCircuit']
