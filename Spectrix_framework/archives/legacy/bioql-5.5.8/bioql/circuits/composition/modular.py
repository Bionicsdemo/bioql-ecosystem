"""
Modular Circuit Building Tools

This module provides the ModularCircuitBuilder for constructing quantum circuits
from reusable modules with flexible wiring and architecture visualization.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Instruction
import numpy as np

logger = logging.getLogger(__name__)


class WiringMode(Enum):
    """
    Mode for wiring modules together.

    Attributes:
        DIRECT: Direct qubit-to-qubit connections
        BROADCAST: Broadcast one module output to multiple inputs
        GATHER: Gather multiple module outputs to one input
        CUSTOM: Custom wiring pattern
    """
    DIRECT = "direct"
    BROADCAST = "broadcast"
    GATHER = "gather"
    CUSTOM = "custom"


@dataclass
class ModuleSpec:
    """
    Specification for a circuit module.

    Attributes:
        name: Unique module name
        circuit: The quantum circuit for this module
        inputs: Input qubit indices
        outputs: Output qubit indices
        metadata: Additional module metadata
    """
    name: str
    circuit: QuantumCircuit
    inputs: List[int]
    outputs: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WiringSpec:
    """
    Specification for module wiring.

    Attributes:
        source_module: Source module name
        target_module: Target module name
        connections: Mapping from source qubits to target qubits
        mode: Wiring mode
    """
    source_module: str
    target_module: str
    connections: Dict[int, int]
    mode: WiringMode = WiringMode.DIRECT


@dataclass
class ArchitectureDiagram:
    """
    Architecture diagram representation.

    Attributes:
        modules: List of module specifications
        connections: List of wiring specifications
        ascii_diagram: ASCII art representation
        metadata: Additional diagram metadata
    """
    modules: List[ModuleSpec]
    connections: List[WiringSpec]
    ascii_diagram: str
    metadata: Dict[str, Any]


class ModularCircuitBuilder:
    """
    Builder for constructing modular quantum circuits.

    The ModularCircuitBuilder allows you to create complex quantum circuits
    from reusable modules, manage their connections, and visualize the
    overall architecture.

    Example:
        >>> builder = ModularCircuitBuilder()
        >>>
        >>> # Add modules
        >>> prep_module = QuantumCircuit(2)
        >>> prep_module.h(0)
        >>> prep_module.cx(0, 1)
        >>> builder.add_module("preparation", prep_module)
        >>>
        >>> processing_module = QuantumCircuit(2)
        >>> processing_module.rz(np.pi/4, 0)
        >>> processing_module.cx(0, 1)
        >>> builder.add_module("processing", processing_module)
        >>>
        >>> # Connect modules
        >>> builder.connect("preparation", "processing", {0: 0, 1: 1})
        >>>
        >>> # Build final circuit
        >>> result = builder.build()
        >>> print(result.num_qubits)
    """

    def __init__(self, name: str = "modular_circuit"):
        """
        Initialize modular circuit builder.

        Args:
            name: Name for the modular circuit
        """
        self.name = name
        self.modules: Dict[str, ModuleSpec] = {}
        self.wirings: List[WiringSpec] = []
        self.execution_order: List[str] = []

        logger.debug(f"Initialized ModularCircuitBuilder: {name}")

    def add_module(
        self,
        name: str,
        circuit: QuantumCircuit,
        inputs: Optional[List[int]] = None,
        outputs: Optional[List[int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ModularCircuitBuilder':
        """
        Add a module to the builder.

        Args:
            name: Unique module name
            circuit: Quantum circuit for this module
            inputs: Input qubit indices (defaults to all qubits)
            outputs: Output qubit indices (defaults to all qubits)
            metadata: Optional metadata

        Returns:
            Self for method chaining

        Raises:
            ValueError: If module name already exists

        Example:
            >>> builder = ModularCircuitBuilder()
            >>> qc = QuantumCircuit(3)
            >>> qc.h([0, 1, 2])
            >>> builder.add_module("hadamard_layer", qc, inputs=[0,1,2], outputs=[0,1,2])
        """
        if name in self.modules:
            raise ValueError(f"Module '{name}' already exists")

        # Default inputs/outputs to all qubits
        if inputs is None:
            inputs = list(range(circuit.num_qubits))
        if outputs is None:
            outputs = list(range(circuit.num_qubits))

        # Validate inputs/outputs
        if not all(0 <= q < circuit.num_qubits for q in inputs):
            raise ValueError("Invalid input qubit indices")
        if not all(0 <= q < circuit.num_qubits for q in outputs):
            raise ValueError("Invalid output qubit indices")

        module = ModuleSpec(
            name=name,
            circuit=circuit,
            inputs=inputs,
            outputs=outputs,
            metadata=metadata or {}
        )

        self.modules[name] = module
        logger.info(f"Added module '{name}' with {circuit.num_qubits} qubits")

        return self

    def connect(
        self,
        module1: str,
        module2: str,
        wiring: Optional[Dict[int, int]] = None,
        mode: WiringMode = WiringMode.DIRECT
    ) -> 'ModularCircuitBuilder':
        """
        Connect two modules with wiring specification.

        Args:
            module1: Source module name
            module2: Target module name
            wiring: Qubit wiring map (auto-generated if None)
            mode: Wiring mode

        Returns:
            Self for method chaining

        Raises:
            ValueError: If modules don't exist or wiring is invalid

        Example:
            >>> builder = ModularCircuitBuilder()
            >>> # ... add modules ...
            >>> builder.connect("module1", "module2", {0: 0, 1: 1})
            >>> builder.connect("module2", "module3", mode=WiringMode.BROADCAST)
        """
        if module1 not in self.modules:
            raise ValueError(f"Module '{module1}' not found")
        if module2 not in self.modules:
            raise ValueError(f"Module '{module2}' not found")

        mod1 = self.modules[module1]
        mod2 = self.modules[module2]

        # Auto-generate wiring if not provided
        if wiring is None:
            wiring = self._auto_generate_wiring(mod1, mod2, mode)

        # Validate wiring
        for src_q, tgt_q in wiring.items():
            if src_q not in mod1.outputs:
                raise ValueError(f"Source qubit {src_q} not in outputs of '{module1}'")
            if tgt_q not in mod2.inputs:
                raise ValueError(f"Target qubit {tgt_q} not in inputs of '{module2}'")

        wiring_spec = WiringSpec(
            source_module=module1,
            target_module=module2,
            connections=wiring,
            mode=mode
        )

        self.wirings.append(wiring_spec)
        logger.info(f"Connected '{module1}' to '{module2}' with {len(wiring)} wire(s)")

        return self

    def build(self) -> QuantumCircuit:
        """
        Build the complete modular circuit.

        Analyzes module connections, determines execution order, and
        constructs the final quantum circuit.

        Returns:
            Complete quantum circuit

        Raises:
            ValueError: If circuit has cycles or is invalid

        Example:
            >>> builder = ModularCircuitBuilder()
            >>> # ... add modules and connections ...
            >>> circuit = builder.build()
            >>> print(f"Built circuit with {circuit.num_qubits} qubits")
        """
        logger.info(f"Building modular circuit '{self.name}'")

        # Determine execution order
        self.execution_order = self._determine_execution_order()

        # Calculate total qubits needed
        total_qubits = self._calculate_total_qubits()

        # Track qubit assignments
        qubit_assignments = self._assign_qubits(total_qubits)

        # Determine classical bits
        total_clbits = max(
            (mod.circuit.num_clbits for mod in self.modules.values()),
            default=0
        )

        # Create final circuit
        qreg = QuantumRegister(total_qubits, 'q')
        if total_clbits > 0:
            creg = ClassicalRegister(total_clbits, 'c')
            final_circuit = QuantumCircuit(qreg, creg)
        else:
            final_circuit = QuantumCircuit(qreg)

        # Add modules in execution order
        for module_name in self.execution_order:
            module = self.modules[module_name]
            qubits_for_module = qubit_assignments[module_name]

            # Compose module circuit
            final_circuit = final_circuit.compose(
                module.circuit,
                qubits=qubits_for_module
            )

        final_circuit.name = self.name

        logger.info(
            f"Built modular circuit: {total_qubits} qubits, "
            f"depth={final_circuit.depth()}, {len(self.modules)} modules"
        )

        return final_circuit

    def visualize_architecture(
        self,
        include_qubits: bool = True,
        include_metadata: bool = False
    ) -> ArchitectureDiagram:
        """
        Visualize the modular circuit architecture.

        Args:
            include_qubits: Include qubit information
            include_metadata: Include module metadata

        Returns:
            ArchitectureDiagram with ASCII representation

        Example:
            >>> builder = ModularCircuitBuilder()
            >>> # ... build circuit ...
            >>> diagram = builder.visualize_architecture()
            >>> print(diagram.ascii_diagram)
        """
        logger.info("Generating architecture diagram")

        # Build ASCII diagram
        lines = []
        lines.append(f"Modular Circuit Architecture: {self.name}")
        lines.append("=" * 60)
        lines.append("")

        # List modules
        lines.append("Modules:")
        lines.append("-" * 60)
        for name, module in self.modules.items():
            lines.append(f"  [{name}]")
            if include_qubits:
                lines.append(f"    Qubits: {module.circuit.num_qubits}")
                lines.append(f"    Inputs: {module.inputs}")
                lines.append(f"    Outputs: {module.outputs}")
            lines.append(f"    Depth: {module.circuit.depth()}")
            if include_metadata and module.metadata:
                lines.append(f"    Metadata: {module.metadata}")
            lines.append("")

        # Show connections
        if self.wirings:
            lines.append("Connections:")
            lines.append("-" * 60)
            for wiring in self.wirings:
                lines.append(
                    f"  {wiring.source_module} --> {wiring.target_module} "
                    f"[{wiring.mode.value}]"
                )
                if include_qubits:
                    for src_q, tgt_q in wiring.connections.items():
                        lines.append(f"    q{src_q} -> q{tgt_q}")
                lines.append("")

        # Show execution order
        if self.execution_order:
            lines.append("Execution Order:")
            lines.append("-" * 60)
            for i, module_name in enumerate(self.execution_order, 1):
                lines.append(f"  {i}. {module_name}")
            lines.append("")

        # Flow diagram
        lines.append("Flow Diagram:")
        lines.append("-" * 60)
        if self.execution_order:
            flow = " -> ".join(self.execution_order)
            lines.append(f"  {flow}")
        lines.append("")

        ascii_diagram = "\n".join(lines)

        metadata = {
            'num_modules': len(self.modules),
            'num_connections': len(self.wirings),
            'execution_order': self.execution_order
        }

        return ArchitectureDiagram(
            modules=list(self.modules.values()),
            connections=self.wirings,
            ascii_diagram=ascii_diagram,
            metadata=metadata
        )

    def get_module(self, name: str) -> Optional[ModuleSpec]:
        """
        Get a module by name.

        Args:
            name: Module name

        Returns:
            ModuleSpec or None if not found
        """
        return self.modules.get(name)

    def list_modules(self) -> List[str]:
        """
        Get list of all module names.

        Returns:
            List of module names
        """
        return list(self.modules.keys())

    def remove_module(self, name: str) -> 'ModularCircuitBuilder':
        """
        Remove a module and its connections.

        Args:
            name: Module name to remove

        Returns:
            Self for method chaining

        Raises:
            ValueError: If module not found
        """
        if name not in self.modules:
            raise ValueError(f"Module '{name}' not found")

        # Remove module
        del self.modules[name]

        # Remove associated wirings
        self.wirings = [
            w for w in self.wirings
            if w.source_module != name and w.target_module != name
        ]

        logger.info(f"Removed module '{name}'")

        return self

    def clear(self) -> 'ModularCircuitBuilder':
        """
        Clear all modules and connections.

        Returns:
            Self for method chaining
        """
        self.modules.clear()
        self.wirings.clear()
        self.execution_order.clear()

        logger.info("Cleared all modules and connections")

        return self

    def _auto_generate_wiring(
        self,
        source: ModuleSpec,
        target: ModuleSpec,
        mode: WiringMode
    ) -> Dict[int, int]:
        """Auto-generate wiring between modules."""
        wiring = {}

        if mode == WiringMode.DIRECT:
            # Direct 1-to-1 mapping
            pairs = min(len(source.outputs), len(target.inputs))
            for i in range(pairs):
                wiring[source.outputs[i]] = target.inputs[i]

        elif mode == WiringMode.BROADCAST:
            # Broadcast first output to all inputs
            if source.outputs:
                src_q = source.outputs[0]
                for tgt_q in target.inputs:
                    wiring[src_q] = tgt_q

        elif mode == WiringMode.GATHER:
            # Gather all outputs to first input
            if target.inputs:
                tgt_q = target.inputs[0]
                for src_q in source.outputs:
                    wiring[src_q] = tgt_q

        return wiring

    def _determine_execution_order(self) -> List[str]:
        """
        Determine execution order using topological sort.

        Returns:
            List of module names in execution order

        Raises:
            ValueError: If circuit has cycles
        """
        # Build dependency graph
        dependencies: Dict[str, Set[str]] = {name: set() for name in self.modules}

        for wiring in self.wirings:
            dependencies[wiring.target_module].add(wiring.source_module)

        # Topological sort using Kahn's algorithm
        in_degree = {name: len(deps) for name, deps in dependencies.items()}
        order = []
        queue = [name for name, degree in in_degree.items() if degree == 0]

        while queue:
            current = queue.pop(0)
            order.append(current)

            # Reduce in-degree for dependents
            for wiring in self.wirings:
                if wiring.source_module == current:
                    in_degree[wiring.target_module] -= 1
                    if in_degree[wiring.target_module] == 0:
                        queue.append(wiring.target_module)

        # Check for cycles
        if len(order) != len(self.modules):
            raise ValueError("Circuit has cycles - cannot determine execution order")

        return order

    def _calculate_total_qubits(self) -> int:
        """Calculate total qubits needed for the circuit."""
        # Strategy: analyze qubit reuse opportunities
        # For now, use simple approach: max qubits needed at any time

        max_qubits = 0
        active_qubits: Set[int] = set()
        qubit_counter = 0

        for module_name in self.execution_order:
            module = self.modules[module_name]

            # Check if we can reuse qubits from previous modules
            # This is a simplified version
            needed_qubits = module.circuit.num_qubits

            if qubit_counter + needed_qubits > max_qubits:
                max_qubits = qubit_counter + needed_qubits

            qubit_counter += needed_qubits

        # More sophisticated approach: track qubit lifetimes
        # For now, sum all qubits (conservative)
        total = sum(mod.circuit.num_qubits for mod in self.modules.values())

        return min(total, max_qubits) if max_qubits > 0 else total

    def _assign_qubits(self, total_qubits: int) -> Dict[str, List[int]]:
        """
        Assign physical qubits to each module.

        Args:
            total_qubits: Total available qubits

        Returns:
            Mapping of module names to qubit lists
        """
        assignments: Dict[str, List[int]] = {}
        next_qubit = 0

        for module_name in self.execution_order:
            module = self.modules[module_name]
            num_qubits = module.circuit.num_qubits

            # Assign qubits
            qubits = list(range(next_qubit, next_qubit + num_qubits))
            assignments[module_name] = qubits

            # Check wiring to see if we can reuse qubits
            # For now, always allocate new qubits
            next_qubit += num_qubits

        return assignments


__all__ = [
    'WiringMode',
    'ModuleSpec',
    'WiringSpec',
    'ArchitectureDiagram',
    'ModularCircuitBuilder'
]
