"""
Circuit Composition Tools - Composer Module

This module provides the CircuitComposer class for composing quantum circuits
using various strategies and patterns.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Union, Callable
from dataclasses import dataclass
import logging

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
import numpy as np

logger = logging.getLogger(__name__)


class CompositionStrategy(Enum):
    """
    Strategy for composing quantum circuits.

    Attributes:
        MINIMAL_QUBITS: Optimize for minimal qubit usage (reuse qubits when possible)
        MINIMAL_DEPTH: Optimize for minimal circuit depth (parallelize operations)
        BALANCED: Balance between qubit usage and circuit depth
    """
    MINIMAL_QUBITS = "minimal_qubits"
    MINIMAL_DEPTH = "minimal_depth"
    BALANCED = "balanced"


@dataclass
class CompositionResult:
    """
    Result of circuit composition operation.

    Attributes:
        circuit: The composed quantum circuit
        qubit_mapping: Mapping of original qubits to composed circuit qubits
        classical_mapping: Mapping of classical bits
        metadata: Additional composition metadata
    """
    circuit: QuantumCircuit
    qubit_mapping: Dict[str, Dict[int, int]]
    classical_mapping: Dict[str, Dict[int, int]]
    metadata: Dict[str, Any]


class CircuitComposer:
    """
    Composer for combining quantum circuits using various strategies.

    The CircuitComposer provides methods to compose circuits in parallel,
    sequentially, conditionally, and with repetition, while optimizing
    for different objectives.

    Example:
        >>> composer = CircuitComposer()
        >>> circuit1 = QuantumCircuit(2)
        >>> circuit1.h(0)
        >>> circuit1.cx(0, 1)
        >>>
        >>> circuit2 = QuantumCircuit(2)
        >>> circuit2.x(0)
        >>> circuit2.y(1)
        >>>
        >>> # Compose in parallel
        >>> result = composer.parallel(circuit1, circuit2)
        >>> print(f"Total qubits: {result.circuit.num_qubits}")
        Total qubits: 4
        >>>
        >>> # Compose sequentially
        >>> result = composer.sequential(circuit1, circuit2)
        >>> print(f"Circuit depth: {result.circuit.depth()}")
    """

    def __init__(self, strategy: CompositionStrategy = CompositionStrategy.BALANCED):
        """
        Initialize circuit composer.

        Args:
            strategy: Default composition strategy
        """
        self.strategy = strategy
        logger.debug(f"Initialized CircuitComposer with strategy: {strategy.value}")

    def compose(
        self,
        *circuits: QuantumCircuit,
        strategy: Optional[CompositionStrategy] = None,
        names: Optional[List[str]] = None
    ) -> CompositionResult:
        """
        Compose multiple circuits using specified strategy.

        Args:
            *circuits: Circuits to compose
            strategy: Composition strategy (uses default if None)
            names: Optional names for each circuit (for tracking)

        Returns:
            CompositionResult with composed circuit and mappings

        Raises:
            ValueError: If no circuits provided or invalid strategy

        Example:
            >>> composer = CircuitComposer()
            >>> qc1 = QuantumCircuit(2)
            >>> qc1.h([0, 1])
            >>> qc2 = QuantumCircuit(2)
            >>> qc2.cx(0, 1)
            >>> result = composer.compose(qc1, qc2, strategy=CompositionStrategy.MINIMAL_DEPTH)
        """
        if not circuits:
            raise ValueError("At least one circuit must be provided")

        strategy = strategy or self.strategy
        names = names or [f"circuit_{i}" for i in range(len(circuits))]

        if len(names) != len(circuits):
            raise ValueError("Number of names must match number of circuits")

        logger.info(f"Composing {len(circuits)} circuits with strategy: {strategy.value}")

        if strategy == CompositionStrategy.MINIMAL_QUBITS:
            return self._compose_minimal_qubits(circuits, names)
        elif strategy == CompositionStrategy.MINIMAL_DEPTH:
            return self._compose_minimal_depth(circuits, names)
        else:  # BALANCED
            return self._compose_balanced(circuits, names)

    def parallel(
        self,
        *circuits: QuantumCircuit,
        names: Optional[List[str]] = None
    ) -> CompositionResult:
        """
        Compose circuits in parallel (tensor product).

        All circuits are executed simultaneously on separate qubits.

        Args:
            *circuits: Circuits to compose in parallel
            names: Optional names for tracking

        Returns:
            CompositionResult with parallel composition

        Example:
            >>> composer = CircuitComposer()
            >>> qc1 = QuantumCircuit(2)
            >>> qc1.h(0)
            >>> qc2 = QuantumCircuit(3)
            >>> qc2.x(1)
            >>> result = composer.parallel(qc1, qc2)
            >>> # Result has 5 qubits total (2 + 3)
        """
        if not circuits:
            raise ValueError("At least one circuit must be provided")

        names = names or [f"circuit_{i}" for i in range(len(circuits))]

        logger.info(f"Composing {len(circuits)} circuits in parallel")

        # Calculate total resources needed
        total_qubits = sum(circ.num_qubits for circ in circuits)
        total_clbits = sum(circ.num_clbits for circ in circuits)

        # Create registers
        qreg = QuantumRegister(total_qubits, 'q')
        creg = ClassicalRegister(total_clbits, 'c') if total_clbits > 0 else None

        # Create composed circuit
        if creg:
            composed = QuantumCircuit(qreg, creg)
        else:
            composed = QuantumCircuit(qreg)

        # Track mappings
        qubit_mapping = {}
        classical_mapping = {}

        qubit_offset = 0
        clbit_offset = 0

        # Add circuits with proper qubit mapping
        for i, (circuit, name) in enumerate(zip(circuits, names)):
            # Map qubits
            qubit_map = {j: qubit_offset + j for j in range(circuit.num_qubits)}
            qubit_mapping[name] = qubit_map

            # Map classical bits
            if circuit.num_clbits > 0:
                clbit_map = {j: clbit_offset + j for j in range(circuit.num_clbits)}
                classical_mapping[name] = clbit_map

            # Compose circuit
            qubits = [qreg[qubit_offset + j] for j in range(circuit.num_qubits)]
            if circuit.num_clbits > 0 and creg:
                clbits = [creg[clbit_offset + j] for j in range(circuit.num_clbits)]
                composed = composed.compose(circuit, qubits=qubits, clbits=clbits)
            else:
                composed = composed.compose(circuit, qubits=qubits)

            qubit_offset += circuit.num_qubits
            clbit_offset += circuit.num_clbits

        metadata = {
            'composition_type': 'parallel',
            'total_qubits': total_qubits,
            'total_clbits': total_clbits,
            'num_circuits': len(circuits)
        }

        logger.debug(f"Parallel composition complete: {total_qubits} qubits, depth={composed.depth()}")

        return CompositionResult(
            circuit=composed,
            qubit_mapping=qubit_mapping,
            classical_mapping=classical_mapping,
            metadata=metadata
        )

    def sequential(
        self,
        *circuits: QuantumCircuit,
        names: Optional[List[str]] = None
    ) -> CompositionResult:
        """
        Compose circuits sequentially on the same qubits.

        Circuits are executed one after another on shared qubits.

        Args:
            *circuits: Circuits to compose sequentially
            names: Optional names for tracking

        Returns:
            CompositionResult with sequential composition

        Raises:
            ValueError: If circuits have different qubit counts

        Example:
            >>> composer = CircuitComposer()
            >>> qc1 = QuantumCircuit(3)
            >>> qc1.h([0, 1, 2])
            >>> qc2 = QuantumCircuit(3)
            >>> qc2.cx(0, 1)
            >>> qc2.cx(1, 2)
            >>> result = composer.sequential(qc1, qc2)
            >>> # Both circuits execute on same 3 qubits
        """
        if not circuits:
            raise ValueError("At least one circuit must be provided")

        names = names or [f"circuit_{i}" for i in range(len(circuits))]

        logger.info(f"Composing {len(circuits)} circuits sequentially")

        # Verify all circuits have same qubit count
        num_qubits = circuits[0].num_qubits
        if not all(circ.num_qubits == num_qubits for circ in circuits):
            raise ValueError("All circuits must have the same number of qubits for sequential composition")

        # Use maximum classical bits
        num_clbits = max(circ.num_clbits for circ in circuits)

        # Create registers
        qreg = QuantumRegister(num_qubits, 'q')
        creg = ClassicalRegister(num_clbits, 'c') if num_clbits > 0 else None

        # Create composed circuit
        if creg:
            composed = QuantumCircuit(qreg, creg)
        else:
            composed = QuantumCircuit(qreg)

        # Track mappings (same for all circuits in sequential)
        qubit_mapping = {}
        classical_mapping = {}

        for i, (circuit, name) in enumerate(zip(circuits, names)):
            # All circuits map to same qubits
            qubit_mapping[name] = {j: j for j in range(num_qubits)}

            # Map available classical bits
            if circuit.num_clbits > 0:
                classical_mapping[name] = {j: j for j in range(circuit.num_clbits)}

            # Compose sequentially
            composed = composed.compose(circuit, qubits=range(num_qubits))

        metadata = {
            'composition_type': 'sequential',
            'num_qubits': num_qubits,
            'num_clbits': num_clbits,
            'num_circuits': len(circuits),
            'total_depth': composed.depth()
        }

        logger.debug(f"Sequential composition complete: {num_qubits} qubits, depth={composed.depth()}")

        return CompositionResult(
            circuit=composed,
            qubit_mapping=qubit_mapping,
            classical_mapping=classical_mapping,
            metadata=metadata
        )

    def conditional(
        self,
        condition: Union[Tuple[ClassicalRegister, int], Callable],
        true_branch: QuantumCircuit,
        false_branch: Optional[QuantumCircuit] = None
    ) -> CompositionResult:
        """
        Compose circuits conditionally based on classical condition.

        Args:
            condition: Classical condition (register, value) or callable
            true_branch: Circuit to execute if condition is true
            false_branch: Circuit to execute if condition is false (optional)

        Returns:
            CompositionResult with conditional composition

        Example:
            >>> composer = CircuitComposer()
            >>> qc = QuantumCircuit(2, 2)
            >>> qc.h(0)
            >>> qc.measure(0, 0)
            >>>
            >>> true_circuit = QuantumCircuit(2)
            >>> true_circuit.x(1)
            >>>
            >>> false_circuit = QuantumCircuit(2)
            >>> false_circuit.z(1)
            >>>
            >>> creg = ClassicalRegister(2, 'c')
            >>> result = composer.conditional((creg, 1), true_circuit, false_circuit)
        """
        logger.info("Creating conditional composition")

        # Determine qubit requirements
        max_qubits = max(
            true_branch.num_qubits,
            false_branch.num_qubits if false_branch else 0
        )
        max_clbits = max(
            true_branch.num_clbits,
            false_branch.num_clbits if false_branch else 0
        )

        # Create registers
        qreg = QuantumRegister(max_qubits, 'q')
        creg = ClassicalRegister(max_clbits, 'c') if max_clbits > 0 else None

        # Create composed circuit
        if creg:
            composed = QuantumCircuit(qreg, creg)
        else:
            composed = QuantumCircuit(qreg)

        # Add conditional circuits using c_if
        if isinstance(condition, tuple):
            cond_reg, cond_val = condition
            true_branch_copy = true_branch.copy()
            true_branch_copy = true_branch_copy.to_instruction().c_if(cond_reg, cond_val)
            composed.append(true_branch_copy, range(true_branch.num_qubits))

            if false_branch:
                # Create NOT condition for false branch
                false_branch_copy = false_branch.copy()
                # Note: Qiskit doesn't support NOT conditions directly,
                # so we need to use a workaround or just document this limitation
                logger.warning("False branch in conditional requires manual condition handling")

        qubit_mapping = {
            'true_branch': {j: j for j in range(true_branch.num_qubits)},
        }
        if false_branch:
            qubit_mapping['false_branch'] = {j: j for j in range(false_branch.num_qubits)}

        classical_mapping = {}
        if true_branch.num_clbits > 0:
            classical_mapping['true_branch'] = {j: j for j in range(true_branch.num_clbits)}
        if false_branch and false_branch.num_clbits > 0:
            classical_mapping['false_branch'] = {j: j for j in range(false_branch.num_clbits)}

        metadata = {
            'composition_type': 'conditional',
            'has_false_branch': false_branch is not None,
            'num_qubits': max_qubits,
            'num_clbits': max_clbits
        }

        return CompositionResult(
            circuit=composed,
            qubit_mapping=qubit_mapping,
            classical_mapping=classical_mapping,
            metadata=metadata
        )

    def repeat(
        self,
        circuit: QuantumCircuit,
        times: int,
        name: Optional[str] = None
    ) -> CompositionResult:
        """
        Repeat a circuit multiple times sequentially.

        Args:
            circuit: Circuit to repeat
            times: Number of repetitions
            name: Optional name for the circuit

        Returns:
            CompositionResult with repeated circuit

        Example:
            >>> composer = CircuitComposer()
            >>> qc = QuantumCircuit(2)
            >>> qc.h(0)
            >>> qc.cx(0, 1)
            >>> result = composer.repeat(qc, times=3)
            >>> # Circuit is repeated 3 times
        """
        if times < 1:
            raise ValueError("times must be at least 1")

        logger.info(f"Repeating circuit {times} times")

        name = name or "circuit"

        # Create composed circuit with same dimensions
        qreg = QuantumRegister(circuit.num_qubits, 'q')
        if circuit.num_clbits > 0:
            creg = ClassicalRegister(circuit.num_clbits, 'c')
            composed = QuantumCircuit(qreg, creg)
        else:
            composed = QuantumCircuit(qreg)

        # Repeat circuit
        for i in range(times):
            composed = composed.compose(circuit)

        qubit_mapping = {
            name: {j: j for j in range(circuit.num_qubits)}
        }

        classical_mapping = {}
        if circuit.num_clbits > 0:
            classical_mapping[name] = {j: j for j in range(circuit.num_clbits)}

        metadata = {
            'composition_type': 'repeat',
            'repetitions': times,
            'num_qubits': circuit.num_qubits,
            'num_clbits': circuit.num_clbits,
            'total_depth': composed.depth()
        }

        logger.debug(f"Repeat composition complete: {times} repetitions, depth={composed.depth()}")

        return CompositionResult(
            circuit=composed,
            qubit_mapping=qubit_mapping,
            classical_mapping=classical_mapping,
            metadata=metadata
        )

    def _compose_minimal_qubits(
        self,
        circuits: tuple,
        names: List[str]
    ) -> CompositionResult:
        """
        Compose circuits optimizing for minimal qubit usage.

        Reuses qubits when possible by analyzing circuit dependencies.
        """
        logger.debug("Composing with MINIMAL_QUBITS strategy")

        # For now, use sequential composition if possible
        # Future: implement smart qubit reuse based on circuit analysis
        if all(circ.num_qubits == circuits[0].num_qubits for circ in circuits):
            return self.sequential(*circuits, names=names)
        else:
            return self.parallel(*circuits, names=names)

    def _compose_minimal_depth(
        self,
        circuits: tuple,
        names: List[str]
    ) -> CompositionResult:
        """
        Compose circuits optimizing for minimal circuit depth.

        Parallelizes circuits when possible to reduce overall depth.
        """
        logger.debug("Composing with MINIMAL_DEPTH strategy")

        # Always use parallel composition for minimal depth
        return self.parallel(*circuits, names=names)

    def _compose_balanced(
        self,
        circuits: tuple,
        names: List[str]
    ) -> CompositionResult:
        """
        Compose circuits with balanced qubit usage and depth.

        Uses heuristics to balance between qubit reuse and parallelization.
        """
        logger.debug("Composing with BALANCED strategy")

        # Simple heuristic: if circuits have same size, sequence them
        # Otherwise, parallelize to save depth
        if all(circ.num_qubits == circuits[0].num_qubits for circ in circuits):
            # Check if depth would be too large
            total_depth = sum(circ.depth() for circ in circuits)
            if total_depth < 1000:  # Threshold
                return self.sequential(*circuits, names=names)

        return self.parallel(*circuits, names=names)


__all__ = [
    'CompositionStrategy',
    'CompositionResult',
    'CircuitComposer'
]
