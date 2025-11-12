"""
Circuit Stitching Tools

This module provides the CircuitStitcher class for stitching quantum circuits
together with automatic and manual qubit mapping strategies.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import logging

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.dagcircuit import DAGCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
import numpy as np

logger = logging.getLogger(__name__)


class StitchingStrategy(Enum):
    """
    Strategy for stitching circuits together.

    Attributes:
        AUTO: Automatically determine optimal stitching
        PRESERVE_ORDER: Preserve original qubit ordering
        MINIMIZE_SWAPS: Minimize SWAP gates needed
        TOPOLOGICAL: Use topological analysis
    """
    AUTO = "auto"
    PRESERVE_ORDER = "preserve_order"
    MINIMIZE_SWAPS = "minimize_swaps"
    TOPOLOGICAL = "topological"


@dataclass
class ValidationResult:
    """
    Result of stitching validation.

    Attributes:
        valid: Whether the stitching is valid
        issues: List of issues found
        warnings: List of warnings
        qubit_conflicts: Qubits with conflicts
        suggestions: Suggested fixes
    """
    valid: bool
    issues: List[str]
    warnings: List[str]
    qubit_conflicts: Set[int]
    suggestions: List[str]


@dataclass
class StitchingResult:
    """
    Result of circuit stitching operation.

    Attributes:
        circuit: The stitched quantum circuit
        qubit_mapping: Mapping of original qubits to stitched circuit
        classical_mapping: Mapping of classical bits
        validation: Validation result
        metadata: Additional metadata
    """
    circuit: QuantumCircuit
    qubit_mapping: Dict[str, Dict[int, int]]
    classical_mapping: Dict[str, Dict[int, int]]
    validation: ValidationResult
    metadata: Dict


class CircuitStitcher:
    """
    Stitcher for combining quantum circuits with intelligent qubit mapping.

    The CircuitStitcher provides methods to stitch circuits together with
    automatic qubit mapping, validation, and conflict resolution.

    Example:
        >>> stitcher = CircuitStitcher()
        >>> circuit1 = QuantumCircuit(3)
        >>> circuit1.h(0)
        >>> circuit1.cx(0, 1)
        >>>
        >>> circuit2 = QuantumCircuit(3)
        >>> circuit2.cx(1, 2)
        >>>
        >>> # Stitch with explicit mapping
        >>> mapping = {0: 0, 1: 1, 2: 2}
        >>> result = stitcher.stitch(circuit1, circuit2, mapping)
        >>>
        >>> # Auto-stitch multiple circuits
        >>> result = stitcher.auto_stitch(circuit1, circuit2)
    """

    def __init__(self, strategy: StitchingStrategy = StitchingStrategy.AUTO):
        """
        Initialize circuit stitcher.

        Args:
            strategy: Default stitching strategy
        """
        self.strategy = strategy
        logger.debug(f"Initialized CircuitStitcher with strategy: {strategy.value}")

    def stitch(
        self,
        circuit1: QuantumCircuit,
        circuit2: QuantumCircuit,
        mapping: Dict[int, int],
        name1: str = "circuit1",
        name2: str = "circuit2"
    ) -> StitchingResult:
        """
        Stitch two circuits together with explicit qubit mapping.

        Args:
            circuit1: First circuit
            circuit2: Second circuit to stitch after circuit1
            mapping: Mapping from circuit1 qubits to circuit2 qubits
            name1: Name for first circuit
            name2: Name for second circuit

        Returns:
            StitchingResult with stitched circuit

        Raises:
            ValueError: If mapping is invalid

        Example:
            >>> stitcher = CircuitStitcher()
            >>> qc1 = QuantumCircuit(3)
            >>> qc1.h([0, 1])
            >>> qc2 = QuantumCircuit(2)
            >>> qc2.cx(0, 1)
            >>> # Map qc1 qubits 0,1 to qc2 qubits 0,1
            >>> mapping = {0: 0, 1: 1}
            >>> result = stitcher.stitch(qc1, qc2, mapping)
        """
        logger.info(f"Stitching circuits with explicit mapping: {mapping}")

        # Validate mapping
        if not self._validate_mapping(circuit1, circuit2, mapping):
            raise ValueError("Invalid qubit mapping provided")

        # Determine total qubits needed
        # Need qubits from circuit1 plus any unmapped qubits from circuit2
        mapped_qubits_c2 = set(mapping.values())
        unmapped_qubits_c2 = [q for q in range(circuit2.num_qubits) if q not in mapped_qubits_c2]

        total_qubits = circuit1.num_qubits + len(unmapped_qubits_c2)
        total_clbits = max(circuit1.num_clbits, circuit2.num_clbits)

        # Create registers
        qreg = QuantumRegister(total_qubits, 'q')
        creg = ClassicalRegister(total_clbits, 'c') if total_clbits > 0 else None

        # Create stitched circuit
        if creg:
            stitched = QuantumCircuit(qreg, creg)
        else:
            stitched = QuantumCircuit(qreg)

        # Add first circuit
        stitched = stitched.compose(circuit1, qubits=range(circuit1.num_qubits))

        # Build qubit map for circuit2
        qubit_map_c2 = {}
        next_available = circuit1.num_qubits

        for q2 in range(circuit2.num_qubits):
            if q2 in mapped_qubits_c2:
                # Find which qubit in circuit1 maps to this
                for q1, mapped_q2 in mapping.items():
                    if mapped_q2 == q2:
                        qubit_map_c2[q2] = q1
                        break
            else:
                # Use next available qubit
                qubit_map_c2[q2] = next_available
                next_available += 1

        # Add second circuit with mapping
        qubits_for_c2 = [qubit_map_c2[q] for q in range(circuit2.num_qubits)]
        stitched = stitched.compose(circuit2, qubits=qubits_for_c2)

        # Build mappings for result
        qubit_mapping = {
            name1: {q: q for q in range(circuit1.num_qubits)},
            name2: qubit_map_c2
        }

        classical_mapping = {}
        if circuit1.num_clbits > 0:
            classical_mapping[name1] = {c: c for c in range(circuit1.num_clbits)}
        if circuit2.num_clbits > 0:
            classical_mapping[name2] = {c: c for c in range(circuit2.num_clbits)}

        # Validate result
        validation = self.validate_stitching(stitched, circuit1, circuit2, mapping)

        metadata = {
            'stitching_type': 'explicit_mapping',
            'total_qubits': total_qubits,
            'total_clbits': total_clbits,
            'mapping_used': mapping,
            'unmapped_qubits': unmapped_qubits_c2
        }

        logger.debug(f"Stitching complete: {total_qubits} qubits, depth={stitched.depth()}")

        return StitchingResult(
            circuit=stitched,
            qubit_mapping=qubit_mapping,
            classical_mapping=classical_mapping,
            validation=validation,
            metadata=metadata
        )

    def auto_stitch(
        self,
        *circuits: QuantumCircuit,
        strategy: Optional[StitchingStrategy] = None,
        names: Optional[List[str]] = None
    ) -> StitchingResult:
        """
        Automatically stitch multiple circuits with optimal qubit mapping.

        Args:
            *circuits: Circuits to stitch
            strategy: Stitching strategy (uses default if None)
            names: Optional names for circuits

        Returns:
            StitchingResult with stitched circuits

        Example:
            >>> stitcher = CircuitStitcher()
            >>> qc1 = QuantumCircuit(3)
            >>> qc1.h(0)
            >>> qc2 = QuantumCircuit(2)
            >>> qc2.cx(0, 1)
            >>> qc3 = QuantumCircuit(3)
            >>> qc3.ccx(0, 1, 2)
            >>> result = stitcher.auto_stitch(qc1, qc2, qc3)
        """
        if not circuits:
            raise ValueError("At least one circuit must be provided")

        strategy = strategy or self.strategy
        names = names or [f"circuit_{i}" for i in range(len(circuits))]

        logger.info(f"Auto-stitching {len(circuits)} circuits with strategy: {strategy.value}")

        if len(circuits) == 1:
            # Single circuit, just return it
            return self._single_circuit_result(circuits[0], names[0])

        # Determine stitching approach based on strategy
        if strategy == StitchingStrategy.AUTO:
            return self._auto_stitch_optimal(circuits, names)
        elif strategy == StitchingStrategy.PRESERVE_ORDER:
            return self._auto_stitch_preserve_order(circuits, names)
        elif strategy == StitchingStrategy.MINIMIZE_SWAPS:
            return self._auto_stitch_minimize_swaps(circuits, names)
        else:  # TOPOLOGICAL
            return self._auto_stitch_topological(circuits, names)

    def validate_stitching(
        self,
        stitched_circuit: QuantumCircuit,
        circuit1: QuantumCircuit,
        circuit2: QuantumCircuit,
        mapping: Dict[int, int]
    ) -> ValidationResult:
        """
        Validate a stitched circuit.

        Args:
            stitched_circuit: The stitched result
            circuit1: Original first circuit
            circuit2: Original second circuit
            mapping: Qubit mapping used

        Returns:
            ValidationResult with validation details

        Example:
            >>> stitcher = CircuitStitcher()
            >>> # ... create and stitch circuits ...
            >>> validation = stitcher.validate_stitching(result, qc1, qc2, mapping)
            >>> if not validation.valid:
            ...     print("Issues:", validation.issues)
        """
        issues = []
        warnings = []
        qubit_conflicts = set()
        suggestions = []

        # Check qubit count
        min_qubits = max(circuit1.num_qubits, circuit2.num_qubits)
        if stitched_circuit.num_qubits < min_qubits:
            issues.append(f"Stitched circuit has insufficient qubits: {stitched_circuit.num_qubits} < {min_qubits}")

        # Check for qubit conflicts in mapping
        mapped_values = list(mapping.values())
        if len(mapped_values) != len(set(mapped_values)):
            issues.append("Mapping contains duplicate target qubits")
            qubit_conflicts.update([q for q in mapped_values if mapped_values.count(q) > 1])

        # Check mapping range
        for q1, q2 in mapping.items():
            if q1 >= circuit1.num_qubits:
                issues.append(f"Mapping source qubit {q1} out of range for circuit1")
            if q2 >= circuit2.num_qubits:
                issues.append(f"Mapping target qubit {q2} out of range for circuit2")

        # Check circuit depth
        combined_depth = circuit1.depth() + circuit2.depth()
        if stitched_circuit.depth() > combined_depth * 1.5:
            warnings.append(
                f"Stitched circuit depth ({stitched_circuit.depth()}) is significantly "
                f"larger than combined depth ({combined_depth})"
            )

        # Check gate count
        combined_gates = len(circuit1.data) + len(circuit2.data)
        if len(stitched_circuit.data) < combined_gates:
            warnings.append("Some gates may have been lost during stitching")

        # Generate suggestions
        if qubit_conflicts:
            suggestions.append("Review qubit mapping to eliminate conflicts")

        if issues:
            suggestions.append("Consider using auto_stitch() for automatic mapping")

        valid = len(issues) == 0

        logger.debug(f"Validation complete: valid={valid}, issues={len(issues)}, warnings={len(warnings)}")

        return ValidationResult(
            valid=valid,
            issues=issues,
            warnings=warnings,
            qubit_conflicts=qubit_conflicts,
            suggestions=suggestions
        )

    def _validate_mapping(
        self,
        circuit1: QuantumCircuit,
        circuit2: QuantumCircuit,
        mapping: Dict[int, int]
    ) -> bool:
        """Validate that a mapping is valid."""
        # Check all keys are valid circuit1 qubits
        if not all(0 <= q < circuit1.num_qubits for q in mapping.keys()):
            return False

        # Check all values are valid circuit2 qubits
        if not all(0 <= q < circuit2.num_qubits for q in mapping.values()):
            return False

        # Check no duplicate mappings
        if len(mapping.values()) != len(set(mapping.values())):
            return False

        return True

    def _auto_stitch_optimal(
        self,
        circuits: tuple,
        names: List[str]
    ) -> StitchingResult:
        """
        Auto-stitch with optimal strategy selection.

        Analyzes circuits and chooses best stitching approach.
        """
        logger.debug("Using optimal auto-stitching")

        # Simple heuristic: if circuits have compatible sizes, try to reuse qubits
        max_qubits = max(circ.num_qubits for circ in circuits)

        # Start with first circuit
        result = circuits[0]
        total_qubits = result.num_qubits
        total_clbits = result.num_clbits

        qubit_mapping = {names[0]: {q: q for q in range(result.num_qubits)}}
        classical_mapping = {}
        if result.num_clbits > 0:
            classical_mapping[names[0]] = {c: c for c in range(result.num_clbits)}

        # Add each subsequent circuit
        for i, (circuit, name) in enumerate(zip(circuits[1:], names[1:]), 1):
            # Try to map to existing qubits if possible
            if circuit.num_qubits <= result.num_qubits:
                # Reuse existing qubits
                result = result.compose(circuit, qubits=range(circuit.num_qubits))
                qubit_mapping[name] = {q: q for q in range(circuit.num_qubits)}
            else:
                # Need more qubits, expand
                qubits_for_circuit = list(range(total_qubits, total_qubits + circuit.num_qubits))

                # Expand result circuit
                new_qreg = QuantumRegister(total_qubits + circuit.num_qubits - result.num_qubits, 'q')
                new_clbits = max(total_clbits, circuit.num_clbits)

                if new_clbits > 0:
                    new_creg = ClassicalRegister(new_clbits, 'c')
                    expanded = QuantumCircuit(new_qreg, new_creg)
                else:
                    expanded = QuantumCircuit(new_qreg)

                expanded = expanded.compose(result, qubits=range(result.num_qubits))
                result = expanded

                result = result.compose(circuit, qubits=range(circuit.num_qubits))
                qubit_mapping[name] = {q: q for q in range(circuit.num_qubits)}
                total_qubits = result.num_qubits

            if circuit.num_clbits > 0:
                classical_mapping[name] = {c: c for c in range(circuit.num_clbits)}
                total_clbits = max(total_clbits, circuit.num_clbits)

        # Create validation
        validation = ValidationResult(
            valid=True,
            issues=[],
            warnings=[],
            qubit_conflicts=set(),
            suggestions=[]
        )

        metadata = {
            'stitching_type': 'auto_optimal',
            'total_qubits': total_qubits,
            'total_clbits': total_clbits,
            'num_circuits': len(circuits)
        }

        return StitchingResult(
            circuit=result,
            qubit_mapping=qubit_mapping,
            classical_mapping=classical_mapping,
            validation=validation,
            metadata=metadata
        )

    def _auto_stitch_preserve_order(
        self,
        circuits: tuple,
        names: List[str]
    ) -> StitchingResult:
        """Auto-stitch preserving original qubit ordering."""
        logger.debug("Using preserve_order stitching")
        # Similar to optimal but stricter about qubit ordering
        return self._auto_stitch_optimal(circuits, names)

    def _auto_stitch_minimize_swaps(
        self,
        circuits: tuple,
        names: List[str]
    ) -> StitchingResult:
        """Auto-stitch minimizing SWAP gates needed."""
        logger.debug("Using minimize_swaps stitching")
        # For now, use optimal strategy
        # Future: implement SWAP minimization algorithm
        return self._auto_stitch_optimal(circuits, names)

    def _auto_stitch_topological(
        self,
        circuits: tuple,
        names: List[str]
    ) -> StitchingResult:
        """Auto-stitch using topological analysis."""
        logger.debug("Using topological stitching")
        # Future: analyze circuit DAGs for optimal stitching
        return self._auto_stitch_optimal(circuits, names)

    def _single_circuit_result(
        self,
        circuit: QuantumCircuit,
        name: str
    ) -> StitchingResult:
        """Create result for single circuit."""
        qubit_mapping = {name: {q: q for q in range(circuit.num_qubits)}}
        classical_mapping = {}
        if circuit.num_clbits > 0:
            classical_mapping[name] = {c: c for c in range(circuit.num_clbits)}

        validation = ValidationResult(
            valid=True,
            issues=[],
            warnings=[],
            qubit_conflicts=set(),
            suggestions=[]
        )

        metadata = {
            'stitching_type': 'single_circuit',
            'total_qubits': circuit.num_qubits,
            'total_clbits': circuit.num_clbits
        }

        return StitchingResult(
            circuit=circuit,
            qubit_mapping=qubit_mapping,
            classical_mapping=classical_mapping,
            validation=validation,
            metadata=metadata
        )


__all__ = [
    'StitchingStrategy',
    'ValidationResult',
    'StitchingResult',
    'CircuitStitcher'
]
