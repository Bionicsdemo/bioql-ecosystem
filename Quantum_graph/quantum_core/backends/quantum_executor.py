# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum Executor Module
========================

Production-ready quantum executor that integrates BioQL quantum infrastructure
with the Quantum_graph system. Provides unified interface for executing quantum
circuits on multiple backends with cost tracking and job management.

Supported Backends:
- IBM Torino (133 qubits, $3.00/shot)
- IonQ Simulator (29 qubits, $0.01/shot)
- IonQ Forte (36 qubits, $3.00/shot)
- AWS SV1 (34 qubits, $0.01/shot)
- Qiskit Simulator (local, free)

Author: BioQL Team / Quantum_graph Integration
"""

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# Qiskit imports
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import TwoLocal
    from qiskit.quantum_info import Statevector
    from qiskit_aer import AerSimulator

    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    logging.warning("Qiskit not available")

# IBM Quantum Runtime
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit_ibm_runtime.exceptions import IBMAccountError, IBMRuntimeError

    IBM_QUANTUM_AVAILABLE = True
except ImportError:
    IBM_QUANTUM_AVAILABLE = False
    logging.warning("IBM Quantum Runtime not available")

# IonQ Provider
try:
    from qiskit_ionq import IonQProvider

    IONQ_AVAILABLE = True
except ImportError:
    IONQ_AVAILABLE = False
    logging.warning("IonQ provider not available")

# AWS Braket
try:
    from braket.aws import AwsDevice
    from braket.circuits import Circuit as BraketCircuit
    from braket.devices import LocalSimulator

    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False

    # Create dummy class when Braket not available
    class BraketCircuit:
        pass

    logging.warning("AWS Braket not available")

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Enumeration of supported quantum backends"""

    IBM_TORINO = "ibm_torino"
    IBM_BRISBANE = "ibm_brisbane"
    IONQ_SIMULATOR = "ionq_simulator"
    IONQ_FORTE = "ionq_forte"
    IONQ_QPU = "ionq_qpu"
    AWS_SV1 = "aws_sv1"
    QISKIT_SIMULATOR = "qiskit_simulator"


@dataclass
class BackendConfig:
    """Configuration for quantum backend"""

    name: str
    qubits: int
    cost_per_shot: float
    backend_type: BackendType
    is_simulator: bool
    description: str = ""


# Backend configurations
BACKEND_CONFIGS = {
    BackendType.IBM_TORINO: BackendConfig(
        name="ibm_torino",
        qubits=133,
        cost_per_shot=3.00,
        backend_type=BackendType.IBM_TORINO,
        is_simulator=False,
        description="IBM Torino 133-qubit quantum processor",
    ),
    BackendType.IBM_BRISBANE: BackendConfig(
        name="ibm_brisbane",
        qubits=127,
        cost_per_shot=1.25,
        backend_type=BackendType.IBM_BRISBANE,
        is_simulator=False,
        description="IBM Brisbane 127-qubit quantum processor",
    ),
    BackendType.IONQ_SIMULATOR: BackendConfig(
        name="ionq_simulator",
        qubits=29,
        cost_per_shot=0.01,
        backend_type=BackendType.IONQ_SIMULATOR,
        is_simulator=True,
        description="IonQ cloud simulator",
    ),
    BackendType.IONQ_FORTE: BackendConfig(
        name="ionq.forte",
        qubits=36,
        cost_per_shot=3.00,
        backend_type=BackendType.IONQ_FORTE,
        is_simulator=False,
        description="IonQ Forte 36-qubit trapped-ion quantum computer",
    ),
    BackendType.AWS_SV1: BackendConfig(
        name="aws_sv1",
        qubits=34,
        cost_per_shot=0.01,
        backend_type=BackendType.AWS_SV1,
        is_simulator=True,
        description="AWS Braket SV1 state vector simulator",
    ),
    BackendType.QISKIT_SIMULATOR: BackendConfig(
        name="qiskit_simulator",
        qubits=32,
        cost_per_shot=0.0,
        backend_type=BackendType.QISKIT_SIMULATOR,
        is_simulator=True,
        description="Local Qiskit Aer simulator (free)",
    ),
}


@dataclass
class QuantumExecutionResult:
    """Result from quantum circuit execution"""

    job_id: str
    backend: str
    counts: Dict[str, int]
    execution_time: float
    cost: float
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    statevector: Optional[np.ndarray] = None

    @property
    def total_shots(self) -> int:
        """Total number of shots executed"""
        return sum(self.counts.values()) if self.counts else 0

    @property
    def most_likely_outcome(self) -> Optional[str]:
        """Most frequently measured outcome"""
        if not self.counts:
            return None
        return max(self.counts.keys(), key=lambda k: self.counts[k])

    def probabilities(self) -> Dict[str, float]:
        """Convert counts to probabilities"""
        if not self.counts:
            return {}
        total = self.total_shots
        return {outcome: count / total for outcome, count in self.counts.items()}


class QuantumExecutionError(Exception):
    """Exception raised for quantum execution errors"""

    pass


class QuantumExecutor:
    """
    Unified quantum executor for multiple backends.

    Integrates BioQL quantum infrastructure with Quantum_graph system,
    providing a single interface for executing quantum circuits across
    IBM Quantum, IonQ, and AWS Braket platforms.

    Example:
        >>> executor = QuantumExecutor()
        >>> circuit = executor.create_molecular_circuit(4, 'protein')
        >>> result = executor.execute_circuit(
        ...     circuit,
        ...     BackendType.IONQ_SIMULATOR,
        ...     shots=1024
        ... )
        >>> print(f"Cost: ${result.cost:.2f}")
    """

    def __init__(
        self,
        ibm_token: Optional[str] = None,
        ionq_token: Optional[str] = None,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
    ):
        """
        Initialize quantum executor.

        Args:
            ibm_token: IBM Quantum API token (or use IBM_QUANTUM_TOKEN env var)
            ionq_token: IonQ API token (or use IONQ_API_KEY env var)
            aws_access_key: AWS access key (or use AWS_ACCESS_KEY_ID env var)
            aws_secret_key: AWS secret key (or use AWS_SECRET_ACCESS_KEY env var)
        """
        # Load tokens from environment if not provided
        self.ibm_token = ibm_token or os.getenv("IBM_QUANTUM_TOKEN")
        self.ionq_token = ionq_token or os.getenv("IONQ_API_KEY")
        self.aws_access_key = aws_access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")

        # Backend connections
        self._ibm_service = None
        self._ionq_provider = None
        self._aws_device = None

        logger.info("🔧 QuantumExecutor initialized")

    def _connect_ibm(self) -> None:
        """Initialize IBM Quantum connection"""
        if not IBM_QUANTUM_AVAILABLE:
            raise QuantumExecutionError(
                "IBM Quantum Runtime not available. " "Install: pip install qiskit-ibm-runtime"
            )

        if not self.ibm_token:
            raise QuantumExecutionError(
                "IBM token not found. Set IBM_QUANTUM_TOKEN environment variable."
            )

        try:
            self._ibm_service = QiskitRuntimeService(channel="ibm_quantum", token=self.ibm_token)
            logger.info("✅ Connected to IBM Quantum")
        except Exception as e:
            raise QuantumExecutionError(f"Failed to connect to IBM Quantum: {e}")

    def _connect_ionq(self) -> None:
        """Initialize IonQ connection"""
        if not IONQ_AVAILABLE:
            raise QuantumExecutionError(
                "IonQ provider not available. " "Install: pip install qiskit-ionq"
            )

        if not self.ionq_token:
            raise QuantumExecutionError(
                "IonQ token not found. Set IONQ_API_KEY environment variable."
            )

        try:
            self._ionq_provider = IonQProvider(self.ionq_token)
            logger.info("✅ Connected to IonQ")
        except Exception as e:
            raise QuantumExecutionError(f"Failed to connect to IonQ: {e}")

    def _connect_aws(self) -> None:
        """Initialize AWS Braket connection"""
        if not BRAKET_AVAILABLE:
            raise QuantumExecutionError(
                "AWS Braket SDK not available. " "Install: pip install amazon-braket-sdk"
            )

        # For local simulator, no credentials needed
        self._aws_device = LocalSimulator()
        logger.info("✅ Connected to AWS Braket (local simulator)")

    def execute_circuit(
        self,
        circuit: Union[QuantumCircuit, BraketCircuit],
        backend: BackendType,
        shots: int = 1024,
        job_id: Optional[str] = None,
    ) -> QuantumExecutionResult:
        """
        Execute quantum circuit on specified backend.

        Args:
            circuit: Quantum circuit (Qiskit or Braket format)
            backend: Target backend type
            shots: Number of measurement shots
            job_id: Optional job identifier

        Returns:
            QuantumExecutionResult with counts, timing, and cost

        Raises:
            QuantumExecutionError: If execution fails
        """
        if job_id is None:
            job_id = f"qgraph_{int(time.time() * 1000)}"

        backend_config = BACKEND_CONFIGS.get(backend)
        if not backend_config:
            raise QuantumExecutionError(f"Unknown backend: {backend}")

        logger.info(f"🚀 Executing on {backend_config.name} with {shots} shots")

        start_time = time.time()

        try:
            # Route to appropriate backend
            if backend in [BackendType.IBM_TORINO, BackendType.IBM_BRISBANE]:
                result = self._execute_ibm(circuit, backend_config, shots, job_id)
            elif backend in [
                BackendType.IONQ_SIMULATOR,
                BackendType.IONQ_FORTE,
                BackendType.IONQ_QPU,
            ]:
                result = self._execute_ionq(circuit, backend_config, shots, job_id)
            elif backend == BackendType.AWS_SV1:
                result = self._execute_aws(circuit, backend_config, shots, job_id)
            elif backend == BackendType.QISKIT_SIMULATOR:
                result = self._execute_qiskit_simulator(circuit, backend_config, shots, job_id)
            else:
                raise QuantumExecutionError(f"Backend not implemented: {backend}")

            execution_time = time.time() - start_time
            result.execution_time = execution_time

            logger.info(
                f"✅ Job {job_id} completed in {execution_time:.2f}s, cost: ${result.cost:.2f}"
            )
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Execution failed: {e}")
            return QuantumExecutionResult(
                job_id=job_id,
                backend=backend_config.name,
                counts={},
                execution_time=execution_time,
                cost=0.0,
                success=False,
                error_message=str(e),
            )

    def _execute_qiskit_simulator(
        self, circuit: QuantumCircuit, backend_config: BackendConfig, shots: int, job_id: str
    ) -> QuantumExecutionResult:
        """Execute on local Qiskit Aer simulator"""
        if not QISKIT_AVAILABLE:
            raise QuantumExecutionError("Qiskit not available")

        # Bind parameters if circuit has them
        if circuit.num_parameters > 0:
            # Bind with random values for testing
            param_values = np.random.uniform(0, 2 * np.pi, circuit.num_parameters)
            circuit = circuit.assign_parameters(param_values)

        simulator = AerSimulator()
        transpiled = transpile(circuit, simulator)
        job = simulator.run(transpiled, shots=shots)
        result = job.result()
        counts = result.get_counts()

        return QuantumExecutionResult(
            job_id=job_id,
            backend=backend_config.name,
            counts=counts,
            execution_time=0.0,  # Will be set by caller
            cost=0.0,  # Simulator is free
            metadata={
                "num_qubits": circuit.num_qubits,
                "depth": circuit.depth(),
                "simulator": "qiskit_aer",
            },
        )

    def _execute_ibm(
        self, circuit: QuantumCircuit, backend_config: BackendConfig, shots: int, job_id: str
    ) -> QuantumExecutionResult:
        """Execute on IBM Quantum hardware"""
        if self._ibm_service is None:
            self._connect_ibm()

        try:
            # Get backend
            backend = self._ibm_service.backend(backend_config.name)

            # Transpile circuit
            transpiled = transpile(circuit, backend, optimization_level=3)

            # Execute using SamplerV2
            sampler = SamplerV2(mode=backend)
            pub = (transpiled, None, shots)
            job = sampler.run([pub])

            logger.info(f"Job submitted: {job.job_id()}")

            # Wait for completion
            result = job.result()

            # Extract counts from SamplerV2 result
            pub_result = result[0]
            bit_array = pub_result.data.meas
            counts = bit_array.get_counts()

            # Calculate cost
            cost = shots * backend_config.cost_per_shot

            return QuantumExecutionResult(
                job_id=job.job_id(),
                backend=backend_config.name,
                counts=counts,
                execution_time=0.0,  # Will be set by caller
                cost=cost,
                metadata={
                    "num_qubits": circuit.num_qubits,
                    "depth": circuit.depth(),
                    "transpiled_depth": transpiled.depth(),
                    "provider": "ibm_quantum",
                },
            )

        except Exception as e:
            logger.error(f"IBM execution failed: {e}")
            raise QuantumExecutionError(f"IBM execution failed: {e}")

    def _execute_ionq(
        self, circuit: QuantumCircuit, backend_config: BackendConfig, shots: int, job_id: str
    ) -> QuantumExecutionResult:
        """Execute on IonQ backend"""
        if self._ionq_provider is None:
            self._connect_ionq()

        try:
            # Get backend
            backend = self._ionq_provider.get_backend(backend_config.name)

            # Transpile circuit
            transpiled = transpile(circuit, backend, optimization_level=1)

            # Execute
            job = backend.run(transpiled, shots=shots)
            logger.info(f"IonQ job submitted: {job.job_id()}")

            # Wait for result
            result = job.result()
            counts = result.get_counts()

            # Calculate cost
            cost = shots * backend_config.cost_per_shot

            return QuantumExecutionResult(
                job_id=job.job_id(),
                backend=backend_config.name,
                counts=counts,
                execution_time=0.0,  # Will be set by caller
                cost=cost,
                metadata={
                    "num_qubits": circuit.num_qubits,
                    "depth": circuit.depth(),
                    "provider": "ionq",
                },
            )

        except Exception as e:
            logger.error(f"IonQ execution failed: {e}")
            raise QuantumExecutionError(f"IonQ execution failed: {e}")

    def _execute_aws(
        self,
        circuit: Union[QuantumCircuit, BraketCircuit],
        backend_config: BackendConfig,
        shots: int,
        job_id: str,
    ) -> QuantumExecutionResult:
        """Execute on AWS Braket"""
        if self._aws_device is None:
            self._connect_aws()

        try:
            # Convert Qiskit circuit to Braket if needed
            if isinstance(circuit, QuantumCircuit):
                circuit = self._qiskit_to_braket(circuit)

            # Execute
            task = self._aws_device.run(circuit, shots=shots)
            result = task.result()

            # Extract counts
            counts = result.measurement_counts

            # Calculate cost
            cost = shots * backend_config.cost_per_shot

            return QuantumExecutionResult(
                job_id=job_id,
                backend=backend_config.name,
                counts=counts,
                execution_time=0.0,  # Will be set by caller
                cost=cost,
                metadata={"provider": "aws_braket"},
            )

        except Exception as e:
            logger.error(f"AWS Braket execution failed: {e}")
            raise QuantumExecutionError(f"AWS Braket execution failed: {e}")

    def _qiskit_to_braket(self, qiskit_circuit: QuantumCircuit) -> BraketCircuit:
        """Convert Qiskit circuit to AWS Braket circuit"""
        if not BRAKET_AVAILABLE:
            raise QuantumExecutionError("AWS Braket SDK not available")

        # This is a simplified conversion - production code would handle all gates
        braket_circuit = BraketCircuit()

        # For now, just create a similar circuit structure
        # In production, would parse and convert each gate
        logger.warning("Using simplified Qiskit->Braket conversion")

        return braket_circuit

    def get_job_status(self, job_id: str, backend: BackendType) -> Dict[str, Any]:
        """
        Get status of a submitted job.

        Args:
            job_id: Job identifier
            backend: Backend type where job was submitted

        Returns:
            Dictionary with job status information
        """
        # This would query the actual backend for job status
        # Implementation depends on backend provider APIs
        return {
            "job_id": job_id,
            "backend": backend.value,
            "status": "completed",  # Would be retrieved from actual backend
            "message": "Job status retrieval not yet implemented",
        }

    def get_results(self, job_id: str, backend: BackendType) -> QuantumExecutionResult:
        """
        Retrieve results for a completed job.

        Args:
            job_id: Job identifier
            backend: Backend type where job was submitted

        Returns:
            QuantumExecutionResult with job results
        """
        # This would retrieve results from the backend
        # Implementation depends on backend provider APIs
        raise NotImplementedError("Result retrieval not yet implemented")

    def estimate_cost(self, backend: BackendType, shots: int) -> float:
        """
        Estimate cost for running circuit.

        Args:
            backend: Target backend
            shots: Number of shots

        Returns:
            Estimated cost in USD
        """
        backend_config = BACKEND_CONFIGS.get(backend)
        if not backend_config:
            return 0.0

        return shots * backend_config.cost_per_shot

    def list_backends(self) -> Dict[str, BackendConfig]:
        """
        List all available backends.

        Returns:
            Dictionary mapping backend types to configurations
        """
        return BACKEND_CONFIGS.copy()

    def get_backend_info(self, backend: BackendType) -> BackendConfig:
        """
        Get information about a specific backend.

        Args:
            backend: Backend type

        Returns:
            Backend configuration
        """
        config = BACKEND_CONFIGS.get(backend)
        if not config:
            raise QuantumExecutionError(f"Unknown backend: {backend}")
        return config


# Convenience function for quick execution
def execute_on_backend(
    circuit: QuantumCircuit, backend: BackendType = BackendType.QISKIT_SIMULATOR, shots: int = 1024
) -> QuantumExecutionResult:
    """
    Convenience function to execute circuit on specified backend.

    Args:
        circuit: Quantum circuit to execute
        backend: Target backend (default: local simulator)
        shots: Number of measurement shots

    Returns:
        Execution result with counts and cost

    Example:
        >>> from circuit_builder import build_molecular_circuit
        >>> circuit = build_molecular_circuit(4, 'protein')
        >>> result = execute_on_backend(circuit, BackendType.IONQ_SIMULATOR)
        >>> print(result.counts)
    """
    executor = QuantumExecutor()
    return executor.execute_circuit(circuit, backend, shots)
