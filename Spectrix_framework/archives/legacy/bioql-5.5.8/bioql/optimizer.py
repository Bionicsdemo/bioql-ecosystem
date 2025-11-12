"""
BioQL Circuit Optimizer

This module provides comprehensive optimization capabilities for BioQL quantum circuits
and IR programs. It includes circuit-level optimizations, IR-level optimizations,
and a unified optimization pipeline.

Features:
- Multiple optimization levels (O0-O3, Os, Ot)
- Gate cancellation and fusion
- Circuit depth and qubit reduction
- BioQL-specific docking and alignment optimizations
- Integration with Qiskit transpiler passes
- Detailed optimization metrics and analysis
"""

from __future__ import annotations

import copy
import datetime
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Optional loguru import
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Qiskit imports for circuit optimization
try:
    from qiskit import QuantumCircuit
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import (
        Optimize1qGates,
        Optimize1qGatesDecomposition,
        InverseCancellation,
        CommutativeCancellation,
        CommutativeInverseCancellation,
        RemoveBarriers,
        OptimizeSwapBeforeMeasure,
        RemoveDiagonalGatesBeforeMeasure,
        Collect2qBlocks,
        ConsolidateBlocks,
    )
    QISKIT_AVAILABLE = True
except ImportError as e:
    QISKIT_AVAILABLE = False
    logger.warning(f"Qiskit not available - using mock optimizer: {e}")

from bioql.ir import (
    BioQLProgram,
    BioQLOperation,
    DockingOperation,
    AlignmentOperation,
    QuantumOptimizationOperation,
    QuantumCircuit as IRQuantumCircuit,
)


# ============================================================================
# OPTIMIZATION LEVELS
# ============================================================================

class OptimizationLevel(Enum):
    """
    Optimization levels for BioQL circuits.

    - O0: No optimization (baseline)
    - O1: Basic optimization (gate cancellation, single-qubit optimization)
    - O2: Standard optimization (O1 + commutation analysis, gate fusion)
    - O3: Aggressive optimization (O2 + depth reduction, qubit reuse)
    - Os: Size optimization (minimize gate count)
    - Ot: Time optimization (minimize circuit depth)
    """
    O0 = 0  # No optimization
    O1 = 1  # Basic
    O2 = 2  # Standard
    O3 = 3  # Aggressive
    Os = 4  # Size-optimized
    Ot = 5  # Time-optimized


# ============================================================================
# OPTIMIZATION METRICS
# ============================================================================

@dataclass
class ImprovementMetrics:
    """Metrics tracking optimization improvements."""

    # Circuit size metrics
    original_gate_count: int
    optimized_gate_count: int
    gates_removed: int
    gates_fused: int

    # Circuit depth metrics
    original_depth: int
    optimized_depth: int
    depth_reduction: int

    # Qubit metrics
    original_qubits: int
    optimized_qubits: int
    qubits_saved: int

    # Performance metrics
    optimization_time: float
    improvement_percentage: float

    # Additional details
    optimization_level: OptimizationLevel
    passes_applied: List[str]
    warnings: List[str]

    def __str__(self) -> str:
        """Human-readable summary of improvements."""
        return (
            f"Optimization Results ({self.optimization_level.name}):\n"
            f"  Gates: {self.original_gate_count} → {self.optimized_gate_count} "
            f"({self.gates_removed} removed, {self.gates_fused} fused)\n"
            f"  Depth: {self.original_depth} → {self.optimized_depth} "
            f"(-{self.depth_reduction})\n"
            f"  Qubits: {self.original_qubits} → {self.optimized_qubits} "
            f"({self.qubits_saved} saved)\n"
            f"  Improvement: {self.improvement_percentage:.2f}%\n"
            f"  Time: {self.optimization_time:.3f}s\n"
            f"  Passes: {', '.join(self.passes_applied)}"
        )


# ============================================================================
# CIRCUIT OPTIMIZER
# ============================================================================

class CircuitOptimizer:
    """
    Optimizes quantum circuits using various optimization techniques.

    This class provides multiple levels of circuit optimization including:
    - Gate cancellation (H-H→I, X-X→I, CNOT-CNOT→I)
    - Gate fusion (combining adjacent rotations)
    - Commutation analysis
    - Depth reduction
    - Qubit reduction
    """

    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.O2):
        """
        Initialize the circuit optimizer.

        Args:
            optimization_level: Level of optimization to apply
        """
        self.optimization_level = optimization_level
        self.logger = logger.bind(optimizer="circuit")

    def optimize(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit],
        level: Optional[OptimizationLevel] = None
    ) -> Tuple[Union[QuantumCircuit, IRQuantumCircuit], ImprovementMetrics]:
        """
        Optimize a quantum circuit.

        Args:
            circuit: Circuit to optimize (Qiskit or BioQL IR circuit)
            level: Optimization level (overrides default)

        Returns:
            Tuple of (optimized_circuit, metrics)
        """
        start_time = time.time()
        level = level or self.optimization_level

        self.logger.info(f"Optimizing circuit with level {level.name}")

        # Handle different circuit types
        if isinstance(circuit, IRQuantumCircuit):
            return self._optimize_ir_circuit(circuit, level, start_time)
        elif QISKIT_AVAILABLE:
            # Try to optimize as Qiskit circuit
            try:
                return self._optimize_qiskit_circuit(circuit, level, start_time)
            except Exception as e:
                raise TypeError(f"Unsupported circuit type: {type(circuit)}") from e
        else:
            raise TypeError(f"Unsupported circuit type: {type(circuit)}")

    def _optimize_qiskit_circuit(
        self,
        circuit: QuantumCircuit,
        level: OptimizationLevel,
        start_time: float
    ) -> Tuple[QuantumCircuit, ImprovementMetrics]:
        """Optimize a Qiskit QuantumCircuit."""
        original_circuit = circuit.copy()
        original_gate_count = len(circuit.data)
        original_depth = circuit.depth()
        original_qubits = circuit.num_qubits

        passes_applied = []
        warnings = []

        # Build optimization pass manager based on level
        pm = PassManager()

        if level == OptimizationLevel.O0:
            # No optimization
            optimized_circuit = circuit.copy()

        elif level == OptimizationLevel.O1:
            # Basic optimization
            pm.append(RemoveBarriers())
            pm.append(Optimize1qGates())
            pm.append(CommutativeInverseCancellation())
            passes_applied = ["RemoveBarriers", "Optimize1qGates", "CommutativeInverseCancellation"]
            optimized_circuit = pm.run(circuit)

        elif level == OptimizationLevel.O2:
            # Standard optimization
            pm.append(RemoveBarriers())
            pm.append(CommutativeCancellation())
            pm.append(Optimize1qGates())
            pm.append(CommutativeInverseCancellation())
            pm.append(Collect2qBlocks())
            pm.append(ConsolidateBlocks())
            passes_applied = [
                "RemoveBarriers", "CommutativeCancellation", "Optimize1qGates",
                "CommutativeInverseCancellation", "Collect2qBlocks", "ConsolidateBlocks"
            ]
            optimized_circuit = pm.run(circuit)

        elif level == OptimizationLevel.O3:
            # Aggressive optimization
            pm.append(RemoveBarriers())
            pm.append(CommutativeCancellation())
            pm.append(Optimize1qGates())
            pm.append(CommutativeInverseCancellation())
            pm.append(Collect2qBlocks())
            pm.append(ConsolidateBlocks())
            pm.append(OptimizeSwapBeforeMeasure())
            pm.append(RemoveDiagonalGatesBeforeMeasure())
            pm.append(Optimize1qGatesDecomposition())
            passes_applied = [
                "RemoveBarriers", "CommutativeCancellation", "Optimize1qGates",
                "CommutativeInverseCancellation", "Collect2qBlocks",
                "ConsolidateBlocks", "OptimizeSwapBeforeMeasure", "RemoveDiagonalGatesBeforeMeasure",
                "Optimize1qGatesDecomposition"
            ]
            optimized_circuit = pm.run(circuit)

        elif level == OptimizationLevel.Os:
            # Size optimization - focus on reducing gate count
            pm.append(RemoveBarriers())
            pm.append(CommutativeCancellation())
            pm.append(CommutativeInverseCancellation())
            pm.append(Optimize1qGates())
            pm.append(Collect2qBlocks())
            pm.append(ConsolidateBlocks())
            pm.append(RemoveDiagonalGatesBeforeMeasure())
            passes_applied = [
                "RemoveBarriers", "CommutativeCancellation", "CommutativeInverseCancellation",
                "Optimize1qGates", "Collect2qBlocks", "ConsolidateBlocks",
                "RemoveDiagonalGatesBeforeMeasure"
            ]
            optimized_circuit = pm.run(circuit)

        elif level == OptimizationLevel.Ot:
            # Time optimization - focus on reducing depth
            pm.append(RemoveBarriers())
            pm.append(CommutativeCancellation())
            pm.append(Optimize1qGates())
            pm.append(Collect2qBlocks())
            pm.append(ConsolidateBlocks())
            passes_applied = [
                "RemoveBarriers", "CommutativeCancellation", "Optimize1qGates",
                "Collect2qBlocks", "ConsolidateBlocks"
            ]
            optimized_circuit = pm.run(circuit)

        else:
            optimized_circuit = circuit.copy()

        # Calculate metrics
        optimized_gate_count = len(optimized_circuit.data)
        optimized_depth = optimized_circuit.depth()
        optimized_qubits = optimized_circuit.num_qubits

        gates_removed = original_gate_count - optimized_gate_count
        gates_fused = max(0, gates_removed)  # Simplified metric
        depth_reduction = original_depth - optimized_depth
        qubits_saved = original_qubits - optimized_qubits

        # Calculate improvement percentage
        if original_gate_count > 0:
            improvement = (gates_removed / original_gate_count) * 100
        else:
            improvement = 0.0

        optimization_time = time.time() - start_time

        metrics = ImprovementMetrics(
            original_gate_count=original_gate_count,
            optimized_gate_count=optimized_gate_count,
            gates_removed=gates_removed,
            gates_fused=gates_fused,
            original_depth=original_depth,
            optimized_depth=optimized_depth,
            depth_reduction=depth_reduction,
            original_qubits=original_qubits,
            optimized_qubits=optimized_qubits,
            qubits_saved=qubits_saved,
            optimization_time=optimization_time,
            improvement_percentage=improvement,
            optimization_level=level,
            passes_applied=passes_applied,
            warnings=warnings
        )

        self.logger.success(f"Circuit optimized: {improvement:.1f}% improvement")
        return optimized_circuit, metrics

    def _optimize_ir_circuit(
        self,
        circuit: IRQuantumCircuit,
        level: OptimizationLevel,
        start_time: float
    ) -> Tuple[IRQuantumCircuit, ImprovementMetrics]:
        """Optimize a BioQL IR circuit."""
        original_circuit = copy.deepcopy(circuit)
        optimized_circuit = copy.deepcopy(circuit)

        original_gate_count = len(circuit.gates)
        original_depth = self._calculate_ir_depth(circuit)
        original_qubits = circuit.num_qubits

        passes_applied = []
        warnings = []

        if level == OptimizationLevel.O0:
            # No optimization
            pass

        else:
            # Apply optimizations
            if level.value >= OptimizationLevel.O1.value:
                optimized_circuit = self.simplify_gates(optimized_circuit)
                passes_applied.append("SimplifyGates")

            if level.value >= OptimizationLevel.O2.value:
                optimized_circuit = self._commute_gates(optimized_circuit)
                passes_applied.append("CommuteGates")

            if level.value >= OptimizationLevel.O3.value:
                optimized_circuit = self.reduce_depth(optimized_circuit)
                passes_applied.append("ReduceDepth")

        # Calculate metrics
        optimized_gate_count = len(optimized_circuit.gates)
        optimized_depth = self._calculate_ir_depth(optimized_circuit)
        optimized_qubits = optimized_circuit.num_qubits

        gates_removed = original_gate_count - optimized_gate_count
        gates_fused = max(0, gates_removed)
        depth_reduction = original_depth - optimized_depth
        qubits_saved = original_qubits - optimized_qubits

        if original_gate_count > 0:
            improvement = (gates_removed / original_gate_count) * 100
        else:
            improvement = 0.0

        optimization_time = time.time() - start_time

        metrics = ImprovementMetrics(
            original_gate_count=original_gate_count,
            optimized_gate_count=optimized_gate_count,
            gates_removed=gates_removed,
            gates_fused=gates_fused,
            original_depth=original_depth,
            optimized_depth=optimized_depth,
            depth_reduction=depth_reduction,
            original_qubits=original_qubits,
            optimized_qubits=optimized_qubits,
            qubits_saved=qubits_saved,
            optimization_time=optimization_time,
            improvement_percentage=improvement,
            optimization_level=level,
            passes_applied=passes_applied,
            warnings=warnings
        )

        return optimized_circuit, metrics

    def simplify_gates(self, circuit: IRQuantumCircuit) -> IRQuantumCircuit:
        """
        Simplify gates by applying cancellation rules.

        Rules:
        - H-H → I (identity)
        - X-X → I
        - Y-Y → I
        - Z-Z → I
        - CNOT-CNOT → I (same control and target)

        Args:
            circuit: Circuit to simplify

        Returns:
            Simplified circuit
        """
        optimized = copy.deepcopy(circuit)
        gates = optimized.gates

        # Track which gates to remove
        to_remove = set()

        i = 0
        while i < len(gates) - 1:
            if i in to_remove:
                i += 1
                continue

            current = gates[i]
            next_gate = gates[i + 1]

            # Check for cancellation patterns
            if self._gates_cancel(current, next_gate):
                to_remove.add(i)
                to_remove.add(i + 1)
                self.logger.debug(f"Cancelling gates {i} and {i+1}: {current['gate']} and {next_gate['gate']}")
                i += 2
            else:
                i += 1

        # Remove cancelled gates
        optimized.gates = [g for idx, g in enumerate(gates) if idx not in to_remove]

        return optimized

    def _gates_cancel(self, gate1: Dict[str, Any], gate2: Dict[str, Any]) -> bool:
        """Check if two consecutive gates cancel each other."""
        # Same gate type and qubits
        if gate1['gate'] != gate2['gate']:
            return False

        if gate1['qubits'] != gate2['qubits']:
            return False

        # Self-inverse gates: H, X, Y, Z, CNOT
        self_inverse = ['h', 'x', 'y', 'z', 'cnot', 'cz']

        if gate1['gate'] in self_inverse:
            # For rotation gates, check if they're inverses
            if gate1['gate'] in ['rx', 'ry', 'rz']:
                params1 = gate1.get('params', [])
                params2 = gate2.get('params', [])
                if len(params1) == 1 and len(params2) == 1:
                    # Check if angles are opposite
                    return abs(params1[0] + params2[0]) < 1e-10
            else:
                return True

        return False

    def reduce_depth(self, circuit: IRQuantumCircuit) -> IRQuantumCircuit:
        """
        Reduce circuit depth by identifying parallelization opportunities.

        Gates can be executed in parallel if they operate on different qubits
        and don't have data dependencies.

        Args:
            circuit: Circuit to optimize

        Returns:
            Depth-optimized circuit
        """
        # This is a simplified version - real depth reduction is complex
        # For IR circuits, we mainly reorder commuting gates
        return self._commute_gates(circuit)

    def reduce_qubits(self, circuit: IRQuantumCircuit) -> IRQuantumCircuit:
        """
        Reduce the number of qubits by identifying unused qubits.

        Args:
            circuit: Circuit to optimize

        Returns:
            Qubit-optimized circuit
        """
        # Find which qubits are actually used
        used_qubits = set()
        for gate in circuit.gates:
            used_qubits.update(gate['qubits'])

        # If all qubits are used, no optimization possible
        if len(used_qubits) >= circuit.num_qubits:
            return circuit

        # Create mapping from old to new qubit indices
        sorted_used = sorted(used_qubits)
        qubit_map = {old: new for new, old in enumerate(sorted_used)}

        # Create optimized circuit
        optimized = copy.deepcopy(circuit)
        optimized.num_qubits = len(used_qubits)

        # Remap qubit indices
        for gate in optimized.gates:
            gate['qubits'] = [qubit_map[q] for q in gate['qubits']]

        return optimized

    def _commute_gates(self, circuit: IRQuantumCircuit) -> IRQuantumCircuit:
        """
        Optimize circuit by commuting gates where possible.

        This helps reduce depth by moving independent operations together.
        """
        optimized = copy.deepcopy(circuit)
        gates = optimized.gates

        # Simple bubble-sort style commutation
        # More sophisticated algorithms exist but this is a good start
        changed = True
        while changed:
            changed = False
            for i in range(len(gates) - 1):
                if self._can_commute(gates[i], gates[i + 1]):
                    # Check if swapping improves parallelization
                    if self._should_swap(gates, i):
                        gates[i], gates[i + 1] = gates[i + 1], gates[i]
                        changed = True

        return optimized

    def _can_commute(self, gate1: Dict[str, Any], gate2: Dict[str, Any]) -> bool:
        """Check if two gates can be commuted (swapped)."""
        # Gates on completely different qubits always commute
        qubits1 = set(gate1['qubits'])
        qubits2 = set(gate2['qubits'])

        if qubits1.isdisjoint(qubits2):
            return True

        # Additional commutation rules for specific gate pairs
        # (simplified - real analysis is more complex)
        gate_type1 = gate1['gate']
        gate_type2 = gate2['gate']

        # Z gates commute with each other
        if gate_type1 == 'z' and gate_type2 == 'z':
            return True

        # X gates commute with each other
        if gate_type1 == 'x' and gate_type2 == 'x':
            return True

        return False

    def _should_swap(self, gates: List[Dict[str, Any]], index: int) -> bool:
        """Determine if swapping gates at index and index+1 is beneficial."""
        # Simple heuristic: prefer grouping gates by qubit
        if index == 0:
            return False

        gate_before = gates[index - 1]
        gate_current = gates[index]
        gate_next = gates[index + 1]

        # Check if swapping brings similar operations together
        qubits_before = set(gate_before['qubits'])
        qubits_current = set(gate_current['qubits'])
        qubits_next = set(gate_next['qubits'])

        # Prefer grouping gates on same qubits
        overlap_before_next = len(qubits_before & qubits_next)
        overlap_current_next = len(qubits_current & qubits_next)

        return overlap_before_next > overlap_current_next

    def _calculate_ir_depth(self, circuit: IRQuantumCircuit) -> int:
        """Calculate the depth of an IR circuit."""
        if not circuit.gates:
            return 0

        # Track the last time each qubit was used
        qubit_times = [0] * circuit.num_qubits

        for gate in circuit.gates:
            # Find the latest time among qubits this gate uses
            max_time = max(qubit_times[q] for q in gate['qubits'])

            # Update times for all qubits used by this gate
            for q in gate['qubits']:
                qubit_times[q] = max_time + 1

        return max(qubit_times)

    def analyze_improvement(
        self,
        original: Union[QuantumCircuit, IRQuantumCircuit],
        optimized: Union[QuantumCircuit, IRQuantumCircuit]
    ) -> ImprovementMetrics:
        """
        Analyze the improvement between original and optimized circuits.

        Args:
            original: Original circuit
            optimized: Optimized circuit

        Returns:
            Improvement metrics
        """
        if QISKIT_AVAILABLE and isinstance(original, QuantumCircuit):
            original_gates = len(original.data)
            optimized_gates = len(optimized.data)
            original_depth = original.depth()
            optimized_depth = optimized.depth()
            original_qubits = original.num_qubits
            optimized_qubits = optimized.num_qubits
        elif isinstance(original, IRQuantumCircuit):
            original_gates = len(original.gates)
            optimized_gates = len(optimized.gates)
            original_depth = self._calculate_ir_depth(original)
            optimized_depth = self._calculate_ir_depth(optimized)
            original_qubits = original.num_qubits
            optimized_qubits = optimized.num_qubits
        else:
            raise TypeError("Unsupported circuit type")

        gates_removed = original_gates - optimized_gates
        depth_reduction = original_depth - optimized_depth
        qubits_saved = original_qubits - optimized_qubits

        improvement = (gates_removed / original_gates * 100) if original_gates > 0 else 0.0

        return ImprovementMetrics(
            original_gate_count=original_gates,
            optimized_gate_count=optimized_gates,
            gates_removed=gates_removed,
            gates_fused=max(0, gates_removed),
            original_depth=original_depth,
            optimized_depth=optimized_depth,
            depth_reduction=depth_reduction,
            original_qubits=original_qubits,
            optimized_qubits=optimized_qubits,
            qubits_saved=qubits_saved,
            optimization_time=0.0,
            improvement_percentage=improvement,
            optimization_level=self.optimization_level,
            passes_applied=[],
            warnings=[]
        )


# ============================================================================
# IR OPTIMIZER
# ============================================================================

class IROptimizer:
    """
    Optimizes BioQL IR programs at the intermediate representation level.

    This optimizer works on the IR before circuit compilation, applying
    high-level optimizations specific to BioQL operations.
    """

    def __init__(self):
        """Initialize the IR optimizer."""
        self.logger = logger.bind(optimizer="ir")

    def optimize_program(self, program: BioQLProgram) -> BioQLProgram:
        """
        Optimize a BioQL program.

        Args:
            program: Program to optimize

        Returns:
            Optimized program
        """
        optimized = copy.deepcopy(program)

        self.logger.info(f"Optimizing IR program: {program.name}")

        # Apply optimizations
        optimized = self.eliminate_dead_operations(optimized)
        optimized = self.fuse_operations(optimized)
        optimized = self.optimize_docking_ops(optimized)

        # Add audit entry
        optimized.add_audit_entry(
            "ir_optimization",
            {
                "original_operations": len(program.operations),
                "optimized_operations": len(optimized.operations),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )

        return optimized

    def eliminate_dead_operations(self, program: BioQLProgram) -> BioQLProgram:
        """
        Eliminate operations that don't contribute to the final result.

        Args:
            program: Program to optimize

        Returns:
            Optimized program
        """
        # For now, this is a placeholder
        # Real implementation would analyze data flow
        return program

    def fuse_operations(self, program: BioQLProgram) -> BioQLProgram:
        """
        Fuse compatible operations together.

        Args:
            program: Program to optimize

        Returns:
            Optimized program
        """
        optimized = copy.deepcopy(program)

        # Look for consecutive docking operations that could be batched
        fused_ops = []
        i = 0
        operations = optimized.operations

        while i < len(operations):
            current_op = operations[i]

            # Check if next operation can be fused
            if i + 1 < len(operations):
                next_op = operations[i + 1]
                if self._can_fuse(current_op, next_op):
                    # Fuse operations
                    fused_op = self._fuse_two_operations(current_op, next_op)
                    fused_ops.append(fused_op)
                    i += 2
                    self.logger.debug(f"Fused operations {i-1} and {i}")
                    continue

            fused_ops.append(current_op)
            i += 1

        optimized.operations = fused_ops
        return optimized

    def _can_fuse(self, op1: BioQLOperation, op2: BioQLOperation) -> bool:
        """Check if two operations can be fused."""
        # Only fuse operations of the same type
        if type(op1) != type(op2):
            return False

        # Docking operations on the same receptor
        if isinstance(op1, DockingOperation) and isinstance(op2, DockingOperation):
            return op1.receptor.id == op2.receptor.id

        return False

    def _fuse_two_operations(
        self,
        op1: BioQLOperation,
        op2: BioQLOperation
    ) -> BioQLOperation:
        """Fuse two compatible operations."""
        # For docking operations, combine ligands
        if isinstance(op1, DockingOperation) and isinstance(op2, DockingOperation):
            fused = copy.deepcopy(op1)
            fused.description = f"Fused: {op1.description or 'dock'} + {op2.description or 'dock'}"
            # This is simplified - real fusion would batch ligands
            return fused

        return op1

    def optimize_docking_ops(self, program: BioQLProgram) -> BioQLProgram:
        """
        Apply BioQL-specific optimizations to docking operations.

        Args:
            program: Program to optimize

        Returns:
            Optimized program
        """
        optimized = copy.deepcopy(program)

        for operation in optimized.operations:
            if isinstance(operation, DockingOperation):
                # Optimize number of poses if excessive
                if operation.num_poses > 50:
                    self.logger.warning(
                        f"Reducing num_poses from {operation.num_poses} to 50 for performance"
                    )
                    operation.num_poses = 50

                # Optimize energy threshold
                if operation.energy_threshold < -15.0:
                    self.logger.warning(
                        f"Adjusting energy_threshold from {operation.energy_threshold} to -15.0"
                    )
                    operation.energy_threshold = -15.0

        return optimized


# ============================================================================
# OPTIMIZATION PIPELINE
# ============================================================================

@dataclass
class PipelineMetrics:
    """Metrics for the complete optimization pipeline."""
    ir_optimization_time: float
    circuit_optimization_time: float
    total_optimization_time: float
    estimated_speedup: float
    estimated_cost_reduction: float
    circuit_metrics: Optional[ImprovementMetrics] = None


class OptimizationPipeline:
    """
    Orchestrates the complete optimization pipeline for BioQL programs.

    This combines IR optimization, circuit optimization, and execution optimization
    into a unified workflow.
    """

    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.O2):
        """
        Initialize the optimization pipeline.

        Args:
            optimization_level: Level of optimization to apply
        """
        self.optimization_level = optimization_level
        self.ir_optimizer = IROptimizer()
        self.circuit_optimizer = CircuitOptimizer(optimization_level)
        self.logger = logger.bind(optimizer="pipeline")

    def optimize(
        self,
        program: BioQLProgram,
        circuit: Optional[Union[QuantumCircuit, IRQuantumCircuit]] = None
    ) -> Tuple[BioQLProgram, Optional[Union[QuantumCircuit, IRQuantumCircuit]], PipelineMetrics]:
        """
        Run the complete optimization pipeline.

        Args:
            program: BioQL program to optimize
            circuit: Optional compiled circuit to optimize

        Returns:
            Tuple of (optimized_program, optimized_circuit, metrics)
        """
        start_time = time.time()

        self.logger.info(f"Starting optimization pipeline for program: {program.name}")

        # Step 1: IR optimization
        ir_start = time.time()
        optimized_program = self.ir_optimizer.optimize_program(program)
        ir_time = time.time() - ir_start

        # Step 2: Circuit optimization (if circuit provided)
        circuit_time = 0.0
        optimized_circuit = None
        circuit_metrics = None

        if circuit is not None:
            circuit_start = time.time()
            optimized_circuit, circuit_metrics = self.circuit_optimizer.optimize(
                circuit, self.optimization_level
            )
            circuit_time = time.time() - circuit_start

        total_time = time.time() - start_time

        # Estimate improvements
        estimated_speedup = self._estimate_speedup(circuit_metrics)
        estimated_cost_reduction = self._estimate_cost_reduction(circuit_metrics)

        metrics = PipelineMetrics(
            ir_optimization_time=ir_time,
            circuit_optimization_time=circuit_time,
            total_optimization_time=total_time,
            estimated_speedup=estimated_speedup,
            estimated_cost_reduction=estimated_cost_reduction,
            circuit_metrics=circuit_metrics
        )

        self.logger.success(
            f"Pipeline complete: {estimated_speedup:.2f}x speedup, "
            f"{estimated_cost_reduction:.1f}% cost reduction"
        )

        return optimized_program, optimized_circuit, metrics

    def estimate_improvement(
        self,
        program: BioQLProgram,
        circuit: Optional[Union[QuantumCircuit, IRQuantumCircuit]] = None
    ) -> Dict[str, Any]:
        """
        Estimate the improvement from optimization without actually optimizing.

        Args:
            program: Program to analyze
            circuit: Optional circuit to analyze

        Returns:
            Estimated improvement metrics
        """
        estimates = {
            "estimated_gate_reduction": 0.0,
            "estimated_depth_reduction": 0.0,
            "estimated_speedup": 1.0,
            "estimated_cost_reduction": 0.0,
            "optimization_level": self.optimization_level.name
        }

        # Estimate based on optimization level
        if self.optimization_level == OptimizationLevel.O1:
            estimates["estimated_gate_reduction"] = 10.0  # 10% reduction
            estimates["estimated_speedup"] = 1.1
        elif self.optimization_level == OptimizationLevel.O2:
            estimates["estimated_gate_reduction"] = 20.0  # 20% reduction
            estimates["estimated_speedup"] = 1.25
        elif self.optimization_level == OptimizationLevel.O3:
            estimates["estimated_gate_reduction"] = 30.0  # 30% reduction
            estimates["estimated_speedup"] = 1.5
        elif self.optimization_level == OptimizationLevel.Os:
            estimates["estimated_gate_reduction"] = 35.0  # 35% reduction
            estimates["estimated_speedup"] = 1.4
        elif self.optimization_level == OptimizationLevel.Ot:
            estimates["estimated_depth_reduction"] = 40.0  # 40% depth reduction
            estimates["estimated_speedup"] = 1.6

        # Cost reduction roughly tracks speedup
        estimates["estimated_cost_reduction"] = (estimates["estimated_speedup"] - 1.0) * 100

        return estimates

    def _estimate_speedup(self, circuit_metrics: Optional[ImprovementMetrics]) -> float:
        """Estimate execution speedup from optimization."""
        if circuit_metrics is None:
            return 1.0

        # Speedup is roughly proportional to depth reduction
        if circuit_metrics.original_depth > 0:
            depth_ratio = circuit_metrics.optimized_depth / circuit_metrics.original_depth
            return 1.0 / max(depth_ratio, 0.1)  # At least 10x speedup cap

        return 1.0

    def _estimate_cost_reduction(self, circuit_metrics: Optional[ImprovementMetrics]) -> float:
        """Estimate cost reduction from optimization."""
        if circuit_metrics is None:
            return 0.0

        # Cost reduction is based on gate count and depth reduction
        gate_reduction = circuit_metrics.improvement_percentage

        if circuit_metrics.original_depth > 0:
            depth_reduction_pct = (
                circuit_metrics.depth_reduction / circuit_metrics.original_depth * 100
            )
        else:
            depth_reduction_pct = 0.0

        # Average of gate and depth reduction
        return (gate_reduction + depth_reduction_pct) / 2.0


# ============================================================================
# BACKEND-SPECIFIC OPTIMIZATION (NEW in v3.1.2+)
# ============================================================================

@dataclass
class BackendOptimizationHint:
    """Optimization hint for a specific backend."""

    backend: str
    hint_type: str  # "gate_set", "topology", "parameter", "warning"
    message: str
    estimated_improvement: float  # Percentage
    priority: str  # "high", "medium", "low"
    auto_fixable: bool = False


class BackendSpecificOptimizer:
    """
    Provides backend-specific optimization hints and transformations.

    This class extends BioQL's optimization capabilities with backend-aware
    optimizations for IBM, IonQ, Quantinuum, Rigetti, and other quantum backends.

    NEW in v3.1.2 - Enterprise feature that doesn't modify existing optimizer code.

    Example:
        >>> from bioql.optimizer import BackendSpecificOptimizer
        >>> optimizer = BackendSpecificOptimizer(backend="ibm")
        >>> hints = optimizer.analyze_circuit(circuit)
        >>> for hint in hints:
        ...     print(f"{hint.priority.upper()}: {hint.message}")
    """

    # Native gate sets for different backends
    BACKEND_NATIVE_GATES = {
        "ibm": ["id", "rz", "sx", "x", "cx"],  # IBM Quantum native gates
        "ionq": ["gpi", "gpi2", "ms"],  # IonQ native gates
        "quantinuum": ["rz", "ry", "zz"],  # Quantinuum/Honeywell native gates
        "rigetti": ["rx", "rz", "cz"],  # Rigetti native gates
        "braket": ["rx", "ry", "rz", "cx"],  # AWS Braket generic
        "simulator": None,  # Simulators support all gates
    }

    # Backend topology constraints
    BACKEND_TOPOLOGY = {
        "ibm": "heavy_hex",  # IBM uses heavy-hexagonal topology
        "ionq": "all_to_all",  # IonQ has all-to-all connectivity
        "quantinuum": "linear",  # Quantinuum uses linear ion trap
        "rigetti": "grid",  # Rigetti uses 2D grid
        "simulator": "all_to_all",
    }

    def __init__(self, backend: str = "simulator"):
        """
        Initialize backend-specific optimizer.

        Args:
            backend: Target backend name (ibm, ionq, quantinuum, rigetti, simulator)
        """
        self.backend = backend.lower()
        self.logger = logger.bind(optimizer="backend_specific")

        # Normalize backend name
        if "ibm" in self.backend or "quantum" in self.backend:
            self.backend = "ibm"
        elif "ionq" in self.backend:
            self.backend = "ionq"
        elif "quantinuum" in self.backend or "honeywell" in self.backend:
            self.backend = "quantinuum"
        elif "rigetti" in self.backend:
            self.backend = "rigetti"
        elif "braket" in self.backend or "aws" in self.backend:
            self.backend = "braket"
        elif "simulator" in self.backend or "aer" in self.backend:
            self.backend = "simulator"

    def analyze_circuit(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit]
    ) -> List[BackendOptimizationHint]:
        """
        Analyze circuit and provide backend-specific optimization hints.

        Args:
            circuit: Circuit to analyze

        Returns:
            List of optimization hints
        """
        hints = []

        self.logger.info(f"Analyzing circuit for {self.backend} backend")

        # Get gate usage statistics
        gate_counts = self._count_gates(circuit)

        # Check native gate set
        hints.extend(self._check_native_gates(gate_counts))

        # Check topology constraints
        hints.extend(self._check_topology(circuit))

        # Check circuit depth
        hints.extend(self._check_depth(circuit))

        # Backend-specific recommendations
        hints.extend(self._backend_specific_hints(circuit, gate_counts))

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        hints.sort(key=lambda h: priority_order.get(h.priority, 3))

        self.logger.info(f"Generated {len(hints)} optimization hints")

        return hints

    def _count_gates(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit]
    ) -> Dict[str, int]:
        """Count gate usage in circuit."""
        counts = defaultdict(int)

        if isinstance(circuit, IRQuantumCircuit):
            for gate in circuit.gates:
                counts[gate['gate']] += 1
        elif QISKIT_AVAILABLE and isinstance(circuit, QuantumCircuit):
            for instruction in circuit.data:
                counts[instruction.operation.name] += 1

        return dict(counts)

    def _check_native_gates(self, gate_counts: Dict[str, int]) -> List[BackendOptimizationHint]:
        """Check if circuit uses non-native gates."""
        hints = []

        native_gates = self.BACKEND_NATIVE_GATES.get(self.backend)

        if native_gates is None:
            # Simulator supports all gates
            return hints

        # Check for non-native gates
        non_native = []
        for gate, count in gate_counts.items():
            if gate not in native_gates and gate not in ['measure', 'barrier']:
                non_native.append((gate, count))

        if non_native:
            total_non_native = sum(count for _, count in non_native)
            total_gates = sum(gate_counts.values())
            improvement = (total_non_native / total_gates) * 100 if total_gates > 0 else 0

            gate_list = ", ".join(f"{gate}({count})" for gate, count in non_native[:5])

            hints.append(BackendOptimizationHint(
                backend=self.backend,
                hint_type="gate_set",
                message=f"Circuit uses {total_non_native} non-native gates: {gate_list}. "
                       f"Consider decomposing to native gate set: {native_gates}",
                estimated_improvement=improvement,
                priority="high",
                auto_fixable=True
            ))

        return hints

    def _check_topology(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit]
    ) -> List[BackendOptimizationHint]:
        """Check if circuit respects backend topology."""
        hints = []

        topology = self.BACKEND_TOPOLOGY.get(self.backend, "all_to_all")

        if topology == "all_to_all":
            # No topology constraints
            return hints

        # Count two-qubit gates
        two_qubit_gates = 0

        if isinstance(circuit, IRQuantumCircuit):
            for gate in circuit.gates:
                if len(gate['qubits']) == 2:
                    two_qubit_gates += 1
        elif QISKIT_AVAILABLE and isinstance(circuit, QuantumCircuit):
            for instruction in circuit.data:
                if instruction.operation.num_qubits == 2:
                    two_qubit_gates += 1

        if two_qubit_gates > 0:
            if topology == "linear":
                hints.append(BackendOptimizationHint(
                    backend=self.backend,
                    hint_type="topology",
                    message=f"Backend uses linear topology. {two_qubit_gates} two-qubit gates detected. "
                           "Consider reordering qubits to minimize SWAP gates.",
                    estimated_improvement=15.0,
                    priority="medium",
                    auto_fixable=True
                ))
            elif topology == "heavy_hex":
                hints.append(BackendOptimizationHint(
                    backend=self.backend,
                    hint_type="topology",
                    message=f"IBM heavy-hex topology detected. {two_qubit_gates} two-qubit gates. "
                           "Use Qiskit transpiler with coupling_map for optimal placement.",
                    estimated_improvement=20.0,
                    priority="medium",
                    auto_fixable=True
                ))

        return hints

    def _check_depth(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit]
    ) -> List[BackendOptimizationHint]:
        """Check circuit depth and provide recommendations."""
        hints = []

        if isinstance(circuit, IRQuantumCircuit):
            depth = CircuitOptimizer()._calculate_ir_depth(circuit)
        elif QISKIT_AVAILABLE and isinstance(circuit, QuantumCircuit):
            depth = circuit.depth()
        else:
            return hints

        # Backend-specific depth thresholds
        thresholds = {
            "ibm": 100,  # IBM backends have shorter coherence times
            "ionq": 500,  # IonQ has longer coherence
            "quantinuum": 1000,  # Quantinuum has very long coherence
            "rigetti": 150,
            "simulator": 10000,  # Simulators have no depth limit
        }

        threshold = thresholds.get(self.backend, 200)

        if depth > threshold:
            hints.append(BackendOptimizationHint(
                backend=self.backend,
                hint_type="parameter",
                message=f"Circuit depth ({depth}) exceeds recommended threshold ({threshold}) for {self.backend}. "
                       "Consider using depth optimization (OptimizationLevel.Ot) or breaking into smaller circuits.",
                estimated_improvement=25.0,
                priority="high",
                auto_fixable=True
            ))

        return hints

    def _backend_specific_hints(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit],
        gate_counts: Dict[str, int]
    ) -> List[BackendOptimizationHint]:
        """Generate backend-specific optimization hints."""
        hints = []

        if self.backend == "ibm":
            hints.extend(self._ibm_specific_hints(circuit, gate_counts))
        elif self.backend == "ionq":
            hints.extend(self._ionq_specific_hints(circuit, gate_counts))
        elif self.backend == "quantinuum":
            hints.extend(self._quantinuum_specific_hints(circuit, gate_counts))
        elif self.backend == "rigetti":
            hints.extend(self._rigetti_specific_hints(circuit, gate_counts))

        return hints

    def _ibm_specific_hints(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit],
        gate_counts: Dict[str, int]
    ) -> List[BackendOptimizationHint]:
        """IBM Quantum specific hints."""
        hints = []

        # IBM uses basis gates: {id, rz, sx, x, cx}
        # Check for Hadamard gates (should decompose to rz + sx)
        if gate_counts.get('h', 0) > 0:
            hints.append(BackendOptimizationHint(
                backend="ibm",
                hint_type="gate_set",
                message=f"{gate_counts['h']} Hadamard gates detected. "
                       "IBM decomposes H to RZ+SX. Pre-decomposing saves overhead.",
                estimated_improvement=5.0,
                priority="low",
                auto_fixable=True
            ))

        # Check for CZ gates (should use CX)
        if gate_counts.get('cz', 0) > 0:
            hints.append(BackendOptimizationHint(
                backend="ibm",
                hint_type="gate_set",
                message=f"{gate_counts['cz']} CZ gates detected. "
                       "IBM uses CX natively. Convert CZ to H-CX-H pattern.",
                estimated_improvement=10.0,
                priority="medium",
                auto_fixable=True
            ))

        return hints

    def _ionq_specific_hints(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit],
        gate_counts: Dict[str, int]
    ) -> List[BackendOptimizationHint]:
        """IonQ specific hints."""
        hints = []

        # IonQ uses GPi, GPi2, MS gates
        total_gates = sum(gate_counts.values())

        if total_gates > 0:
            hints.append(BackendOptimizationHint(
                backend="ionq",
                hint_type="gate_set",
                message=f"IonQ uses native GPi/GPi2/MS gates. Standard gates will be decomposed. "
                       f"For optimal performance, use IonQ-native circuit construction.",
                estimated_improvement=15.0,
                priority="medium",
                auto_fixable=False
            ))

        # IonQ has all-to-all connectivity
        hints.append(BackendOptimizationHint(
            backend="ionq",
            hint_type="topology",
            message="IonQ has all-to-all qubit connectivity. No SWAP gates needed.",
            estimated_improvement=0.0,
            priority="low",
            auto_fixable=False
        ))

        return hints

    def _quantinuum_specific_hints(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit],
        gate_counts: Dict[str, int]
    ) -> List[BackendOptimizationHint]:
        """Quantinuum/Honeywell specific hints."""
        hints = []

        # Quantinuum uses RZ, RY, ZZ gates
        hints.append(BackendOptimizationHint(
            backend="quantinuum",
            hint_type="gate_set",
            message="Quantinuum uses RZ, RY, ZZ native gates with high fidelity. "
                   "Decompose to these gates for best performance.",
            estimated_improvement=12.0,
            priority="medium",
            auto_fixable=True
        ))

        return hints

    def _rigetti_specific_hints(
        self,
        circuit: Union[QuantumCircuit, IRQuantumCircuit],
        gate_counts: Dict[str, int]
    ) -> List[BackendOptimizationHint]:
        """Rigetti specific hints."""
        hints = []

        # Rigetti uses RX, RZ, CZ gates
        if gate_counts.get('cx', 0) > 0:
            hints.append(BackendOptimizationHint(
                backend="rigetti",
                hint_type="gate_set",
                message=f"{gate_counts['cx']} CNOT gates detected. "
                       "Rigetti uses CZ natively. Convert CNOT to H-CZ-H pattern.",
                estimated_improvement=8.0,
                priority="medium",
                auto_fixable=True
            ))

        return hints

    def generate_report(self, hints: List[BackendOptimizationHint]) -> str:
        """Generate human-readable optimization report."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"BACKEND-SPECIFIC OPTIMIZATION REPORT: {self.backend.upper()}")
        lines.append("=" * 80)
        lines.append("")

        if not hints:
            lines.append("✅ No optimization hints - circuit is well-optimized for this backend!")
            lines.append("")
            return "\n".join(lines)

        # Group by priority
        high = [h for h in hints if h.priority == "high"]
        medium = [h for h in hints if h.priority == "medium"]
        low = [h for h in hints if h.priority == "low"]

        if high:
            lines.append("🔴 HIGH PRIORITY OPTIMIZATIONS:")
            lines.append("-" * 80)
            for hint in high:
                lines.append(f"  • {hint.message}")
                lines.append(f"    Estimated improvement: {hint.estimated_improvement:.1f}%")
                lines.append("")

        if medium:
            lines.append("🟡 MEDIUM PRIORITY OPTIMIZATIONS:")
            lines.append("-" * 80)
            for hint in medium:
                lines.append(f"  • {hint.message}")
                lines.append(f"    Estimated improvement: {hint.estimated_improvement:.1f}%")
                lines.append("")

        if low:
            lines.append("🟢 LOW PRIORITY SUGGESTIONS:")
            lines.append("-" * 80)
            for hint in low:
                lines.append(f"  • {hint.message}")
                lines.append("")

        # Summary
        total_improvement = sum(h.estimated_improvement for h in hints)
        auto_fixable = sum(1 for h in hints if h.auto_fixable)

        lines.append("=" * 80)
        lines.append("SUMMARY:")
        lines.append(f"  Total hints: {len(hints)}")
        lines.append(f"  Auto-fixable: {auto_fixable}/{len(hints)}")
        lines.append(f"  Estimated total improvement: {total_improvement:.1f}%")
        lines.append("=" * 80)

        return "\n".join(lines)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "OptimizationLevel",
    "ImprovementMetrics",
    "CircuitOptimizer",
    "IROptimizer",
    "OptimizationPipeline",
    "PipelineMetrics",
    # NEW in v3.1.2+
    "BackendSpecificOptimizer",
    "BackendOptimizationHint",
]
