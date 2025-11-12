"""
Base Circuit Template for BioQL Pre-built Quantum Circuits

This module provides the base class for all pre-built quantum circuits
in BioQL, offering a unified interface for circuit construction, resource
estimation, and execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Qiskit imports
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager


@dataclass
class ResourceEstimate:
    """Resource estimation for a quantum circuit."""

    num_qubits: int
    circuit_depth: int
    gate_count: int
    cx_count: int  # CNOT/CX gates
    single_qubit_gates: int
    measurement_count: int
    estimated_runtime_ms: float
    memory_required_mb: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'num_qubits': self.num_qubits,
            'circuit_depth': self.circuit_depth,
            'gate_count': self.gate_count,
            'cx_count': self.cx_count,
            'single_qubit_gates': self.single_qubit_gates,
            'measurement_count': self.measurement_count,
            'estimated_runtime_ms': self.estimated_runtime_ms,
            'memory_required_mb': self.memory_required_mb
        }


class CircuitBackend(str, Enum):
    """Supported quantum backends."""
    SIMULATOR = "simulator"
    QISKIT_AER = "qiskit_aer"
    IBM_QUANTUM = "ibm_quantum"
    CIRQ = "cirq"
    PENNYLANE = "pennylane"


@dataclass
class CircuitExecutionResult:
    """Result from circuit execution."""

    success: bool
    counts: Dict[str, int]
    circuit_depth: int
    gate_count: int
    shots_executed: int
    execution_time_ms: float
    backend_used: str
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'counts': self.counts,
            'circuit_depth': self.circuit_depth,
            'gate_count': self.gate_count,
            'shots_executed': self.shots_executed,
            'execution_time_ms': self.execution_time_ms,
            'backend_used': self.backend_used,
            'metadata': self.metadata,
            'error_message': self.error_message
        }


class CircuitTemplate(ABC):
    """
    Base template for all pre-built quantum circuits in BioQL.

    This abstract class defines the interface that all circuit implementations
    must follow, including circuit construction, resource estimation, and execution.

    Attributes:
        name: Human-readable name of the circuit
        description: Detailed description of what the circuit does
        num_qubits: Number of qubits required
        backend: Quantum backend to use for execution
        circuit: The underlying quantum circuit (built on demand)

    Example:
        >>> class MyCircuit(CircuitTemplate):
        ...     def __init__(self, num_qubits: int):
        ...         super().__init__(
        ...             name="My Custom Circuit",
        ...             description="A custom quantum circuit",
        ...             num_qubits=num_qubits
        ...         )
        ...
        ...     def build_circuit(self) -> QuantumCircuit:
        ...         qc = QuantumCircuit(self.num_qubits)
        ...         qc.h(range(self.num_qubits))
        ...         qc.measure_all()
        ...         return qc
    """

    def __init__(
        self,
        name: str,
        description: str,
        num_qubits: int,
        backend: CircuitBackend = CircuitBackend.SIMULATOR
    ):
        """
        Initialize circuit template.

        Args:
            name: Circuit name
            description: Circuit description
            num_qubits: Number of qubits required
            backend: Quantum backend (default: simulator)
        """
        self.name = name
        self.description = description
        self.num_qubits = num_qubits
        self.backend = backend
        self._circuit: Optional[QuantumCircuit] = None
        self._built = False

        logger.debug(f"Initialized {self.name} with {num_qubits} qubits")

    @abstractmethod
    def build_circuit(self) -> QuantumCircuit:
        """
        Build and return the quantum circuit.

        This method must be implemented by all subclasses to construct
        the actual quantum circuit based on the algorithm/application.

        Returns:
            QuantumCircuit: The constructed quantum circuit

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass

    def get_circuit(self) -> QuantumCircuit:
        """
        Get the quantum circuit, building it if necessary.

        Returns:
            QuantumCircuit: The quantum circuit
        """
        if not self._built or self._circuit is None:
            logger.info(f"Building circuit: {self.name}")
            self._circuit = self.build_circuit()
            self._built = True

        return self._circuit

    def estimate_resources(self) -> ResourceEstimate:
        """
        Estimate computational resources required for this circuit.

        Provides resource estimates including qubit count, gate count,
        circuit depth, and estimated runtime.

        Returns:
            ResourceEstimate: Resource estimation data

        Example:
            >>> circuit = MyCircuit(num_qubits=5)
            >>> resources = circuit.estimate_resources()
            >>> print(f"Qubits needed: {resources.num_qubits}")
            >>> print(f"Circuit depth: {resources.circuit_depth}")
        """
        circuit = self.get_circuit()

        # Count different gate types
        cx_count = 0
        single_qubit_gates = 0

        for instruction in circuit.data:
            if instruction.operation.name in ['cx', 'cnot', 'CX']:
                cx_count += 1
            elif len(instruction.qubits) == 1:
                single_qubit_gates += 1

        gate_count = len(circuit.data)
        circuit_depth = circuit.depth()
        num_measurements = sum(1 for inst in circuit.data if inst.operation.name == 'measure')

        # Estimate runtime (heuristic: 1ms per depth level on simulator)
        estimated_runtime_ms = circuit_depth * 1.0

        # Estimate memory (heuristic: exponential in qubits)
        memory_required_mb = (2 ** self.num_qubits) * 16 / (1024 * 1024)  # 16 bytes per amplitude

        return ResourceEstimate(
            num_qubits=self.num_qubits,
            circuit_depth=circuit_depth,
            gate_count=gate_count,
            cx_count=cx_count,
            single_qubit_gates=single_qubit_gates,
            measurement_count=num_measurements,
            estimated_runtime_ms=estimated_runtime_ms,
            memory_required_mb=memory_required_mb
        )

    def execute(
        self,
        shots: int = 1024,
        backend: Optional[str] = None,
        optimization_level: int = 1
    ) -> CircuitExecutionResult:
        """
        Execute the quantum circuit.

        Args:
            shots: Number of measurement shots
            backend: Override default backend (optional)
            optimization_level: Qiskit optimization level (0-3)

        Returns:
            CircuitExecutionResult: Execution results

        Example:
            >>> circuit = MyCircuit(num_qubits=3)
            >>> result = circuit.execute(shots=2048)
            >>> print(result.counts)
            {'000': 512, '111': 512, ...}
        """
        import time
        start_time = time.time()

        try:
            circuit = self.get_circuit()
            backend_name = backend or self.backend.value

            logger.info(f"Executing {self.name} with {shots} shots on {backend_name}")

            # Use Qiskit AerSimulator
            simulator = AerSimulator()

            # Transpile circuit
            pass_manager = generate_preset_pass_manager(optimization_level, simulator)
            transpiled_circuit = pass_manager.run(circuit)

            # Execute
            job = simulator.run(transpiled_circuit, shots=shots)
            result = job.result()
            counts = result.get_counts()

            execution_time_ms = (time.time() - start_time) * 1000

            return CircuitExecutionResult(
                success=True,
                counts=counts,
                circuit_depth=transpiled_circuit.depth(),
                gate_count=len(transpiled_circuit.data),
                shots_executed=shots,
                execution_time_ms=execution_time_ms,
                backend_used=backend_name,
                metadata={
                    'optimization_level': optimization_level,
                    'original_depth': circuit.depth(),
                    'original_gates': len(circuit.data)
                }
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Execution failed: {e}")

            return CircuitExecutionResult(
                success=False,
                counts={},
                circuit_depth=0,
                gate_count=0,
                shots_executed=0,
                execution_time_ms=execution_time_ms,
                backend_used=backend or self.backend.value,
                error_message=str(e)
            )

    def visualize(self, output_format: str = 'text') -> str:
        """
        Visualize the quantum circuit.

        Args:
            output_format: Format for visualization ('text', 'mpl', 'latex')

        Returns:
            str: Circuit visualization

        Example:
            >>> circuit = MyCircuit(num_qubits=2)
            >>> print(circuit.visualize())
        """
        circuit = self.get_circuit()

        if output_format == 'text':
            return str(circuit.draw(output='text'))
        elif output_format == 'mpl':
            return str(circuit.draw(output='mpl'))
        elif output_format == 'latex':
            return circuit.draw(output='latex_source')
        else:
            return str(circuit)

    def to_qasm(self) -> str:
        """
        Export circuit to OpenQASM format.

        Returns:
            str: OpenQASM representation

        Example:
            >>> circuit = MyCircuit(num_qubits=2)
            >>> qasm = circuit.to_qasm()
            >>> print(qasm)
        """
        circuit = self.get_circuit()
        return circuit.qasm()

    def get_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the circuit.

        Returns:
            dict: Circuit information including name, description, and resources
        """
        resources = self.estimate_resources()

        return {
            'name': self.name,
            'description': self.description,
            'num_qubits': self.num_qubits,
            'backend': self.backend.value,
            'resources': resources.to_dict(),
            'built': self._built
        }

    def __repr__(self) -> str:
        """String representation of the circuit."""
        return f"{self.__class__.__name__}(name='{self.name}', qubits={self.num_qubits})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} ({self.num_qubits} qubits)"


__all__ = [
    'CircuitTemplate',
    'CircuitBackend',
    'CircuitExecutionResult',
    'ResourceEstimate'
]
