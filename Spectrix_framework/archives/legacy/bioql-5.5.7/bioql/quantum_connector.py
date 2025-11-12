#!/usr/bin/env python3
"""
BioQL Quantum Connector Module

This module provides the core quantum computing functionality for BioQL,
including the quantum() function and QuantumResult class.
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Callable
import numpy as np
from dataclasses import dataclass, field
import warnings
import logging
import time
import hashlib
import json
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from datetime import datetime, timedelta

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    from qiskit.quantum_info import Statevector
    from qiskit.result import Result
    # Try new primitives API first, fallback to old
    try:
        from qiskit.primitives import StatevectorSampler as Sampler
    except ImportError:
        try:
            from qiskit.primitives import BackendSamplerV2 as Sampler
        except ImportError:
            # For older versions
            Sampler = None
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    # Create dummy classes when qiskit is not available
    class QuantumCircuit:
        pass
    warnings.warn(
        "Qiskit not available. Install with: pip install qiskit qiskit-aer",
        ImportWarning
    )

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler as RuntimeSampler
    from qiskit_ibm_runtime.exceptions import IBMRuntimeError, IBMAccountError
    IBM_QUANTUM_AVAILABLE = True
except ImportError:
    IBM_QUANTUM_AVAILABLE = False
    warnings.warn(
        "IBM Quantum libraries not available. Install with: pip install qiskit-ibm-runtime",
        ImportWarning
    )

try:
    from qiskit_ionq import IonQProvider
    IONQ_AVAILABLE = True
except ImportError:
    IONQ_AVAILABLE = False
    warnings.warn(
        "IonQ libraries not available. Install with: pip install qiskit-ionq",
        ImportWarning
    )

# Configure logging
logger = logging.getLogger(__name__)

# Suppress stevedore warnings about deprecated IBM plugins
logging.getLogger('stevedore.extension').setLevel(logging.CRITICAL)

# Billing integration imports (optional)
try:
    from .billing_integration import (
        BillingIntegration,
        create_billing_quantum_function,
        get_billing_status,
        BILLING_ENABLED
    )
    BILLING_INTEGRATION_AVAILABLE = True
except ImportError:
    BILLING_INTEGRATION_AVAILABLE = False
    BILLING_ENABLED = False
    logger.debug("Billing integration not available")


class BioQLError(Exception):
    """Base exception for BioQL-related errors."""
    pass


class QuantumBackendError(BioQLError):
    """Exception raised for quantum backend-related errors."""
    pass


class ProgramParsingError(BioQLError):
    """Exception raised for program parsing errors."""
    pass


class IBMQuantumError(BioQLError):
    """Exception raised for IBM Quantum-related errors."""
    pass


class JobTimeoutError(IBMQuantumError):
    """Exception raised when a quantum job times out."""
    pass


class AuthenticationError(IBMQuantumError):
    """Exception raised for authentication errors."""
    pass


class BackendNotAvailableError(IBMQuantumError):
    """Exception raised when a requested backend is not available."""
    pass


class CircuitTooLargeError(IBMQuantumError):
    """Exception raised when circuit exceeds backend capabilities."""
    pass


# Circuit caching utility
class CircuitCache:
    """Simple in-memory cache for quantum circuits and results."""

    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, Tuple[QuantumResult, datetime]] = {}
        self._max_size = max_size

    def _hash_circuit(self, circuit: QuantumCircuit, shots: int, backend: str) -> str:
        """Generate a hash for circuit identification."""
        circuit_str = str(circuit)
        data = f"{circuit_str}_{shots}_{backend}"
        return hashlib.md5(data.encode()).hexdigest()

    def get(self, circuit: QuantumCircuit, shots: int, backend: str,
            max_age_hours: int = 24) -> Optional['QuantumResult']:
        """Get cached result if available and not expired."""
        cache_key = self._hash_circuit(circuit, shots, backend)

        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            age = datetime.now() - timestamp

            if age < timedelta(hours=max_age_hours):
                logger.info(f"Cache hit for circuit {cache_key[:8]}...")
                return result
            else:
                # Remove expired entry
                del self._cache[cache_key]

        return None

    def put(self, circuit: QuantumCircuit, shots: int, backend: str,
            result: 'QuantumResult') -> None:
        """Store result in cache."""
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(),
                           key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        cache_key = self._hash_circuit(circuit, shots, backend)
        self._cache[cache_key] = (result, datetime.now())
        logger.info(f"Cached result for circuit {cache_key[:8]}...")


# Global circuit cache instance
_circuit_cache = CircuitCache()


# Retry decorator for IBM Quantum operations
def retry_on_failure(max_retries: int = 3, delay: float = 1.0,
                    backoff: float = 2.0):
    """Decorator to retry operations with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (IBMRuntimeError,
                       ConnectionError, TimeoutError) as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed. "
                            f"Last error: {str(e)}"
                        )

            raise IBMQuantumError(
                f"Operation failed after {max_retries + 1} attempts: "
                f"{str(last_exception)}"
            )

        return wrapper
    return decorator


@dataclass
class QuantumResult:
    """
    Result object containing the output of a quantum computation.

    Attributes:
        counts: Dictionary mapping measurement outcomes to their frequencies
        statevector: Complex amplitudes of the quantum state (if available)
        bio_interpretation: Biological interpretation of the quantum results
        metadata: Additional metadata about the computation
        success: Whether the computation completed successfully
        error_message: Error message if computation failed
        job_id: Job ID from quantum backend (if available)
        backend_name: Name of the backend used
        execution_time: Total execution time in seconds
        queue_time: Time spent in queue (if available)
        cost_estimate: Estimated cost of the computation
        billing_metadata: Billing and usage tracking information (if enabled)
        qec_metrics: Quantum Error Correction metrics (if QEC was applied)
        visualization_path: Path to generated QEC visualizations (if enabled)
        resource_estimation: Resource estimation for QEC (if calculated)
    """
    counts: Dict[str, int] = field(default_factory=dict)
    statevector: Optional[np.ndarray] = None
    bio_interpretation: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    job_id: Optional[str] = None
    backend_name: Optional[str] = None
    execution_time: Optional[float] = None
    queue_time: Optional[float] = None
    cost_estimate: Optional[float] = None
    # Billing integration fields
    billing_metadata: Dict[str, Any] = field(default_factory=dict)
    # QEC integration fields (NEW in v5.0.0)
    qec_metrics: Optional[Dict[str, Any]] = None
    visualization_path: Optional[str] = None
    resource_estimation: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate the result after initialization."""
        if not self.success and not self.error_message:
            raise ValueError("Failed results must include an error message")

    @property
    def total_shots(self) -> int:
        """Total number of shots executed."""
        return sum(self.counts.values()) if self.counts else 0

    @property
    def most_likely_outcome(self) -> Optional[str]:
        """The measurement outcome with the highest probability."""
        if not self.counts:
            return None
        return max(self.counts.keys(), key=lambda k: self.counts[k])

    def probabilities(self) -> Dict[str, float]:
        """Convert counts to probabilities."""
        if not self.counts:
            return {}
        total = self.total_shots
        return {outcome: count / total for outcome, count in self.counts.items()}


class QuantumSimulator:
    """
    Quantum simulator backend using Qiskit.

    This class provides a simple interface to quantum simulation
    functionality for BioQL programs.
    """

    def __init__(self, backend_name: str = 'aer_simulator'):
        """
        Initialize the quantum simulator.

        Args:
            backend_name: Name of the Qiskit backend to use
        """
        if not QISKIT_AVAILABLE:
            raise QuantumBackendError(
                "Qiskit not available. Please install qiskit and qiskit-aer"
            )

        self.backend_name = backend_name
        self.backend = AerSimulator()
        logger.info(f"Initialized quantum simulator with backend: {backend_name}")

    def execute_circuit(
        self,
        circuit: QuantumCircuit,
        shots: int = 1024,
        get_statevector: bool = False
    ) -> QuantumResult:
        """
        Execute a quantum circuit on the simulator.

        Args:
            circuit: The quantum circuit to execute
            shots: Number of measurement shots
            get_statevector: Whether to compute the final statevector

        Returns:
            QuantumResult containing the computation results
        """
        try:
            # Transpile circuit for the backend
            transpiled_circuit = transpile(circuit, self.backend)

            # Execute the circuit
            job = self.backend.run(transpiled_circuit, shots=shots)
            result = job.result()

            # Extract counts
            counts = result.get_counts()

            # Get statevector if requested
            statevector = None
            if get_statevector:
                try:
                    # For statevector, we need to run without measurements
                    statevector_circuit = circuit.copy()
                    # Remove measurements for statevector calculation
                    for instruction in statevector_circuit.data[:]:
                        if instruction.operation.name == 'measure':
                            statevector_circuit.data.remove(instruction)

                    # Use statevector simulator
                    sv_backend = AerSimulator(method='statevector')
                    sv_job = sv_backend.run(statevector_circuit, shots=1)
                    sv_result = sv_job.result()
                    statevector = sv_result.get_statevector().data
                except Exception as e:
                    logger.warning(f"Could not compute statevector: {str(e)}")
                    statevector = None

            # Create metadata
            metadata = {
                'backend': self.backend_name,
                'shots': shots,
                'circuit_depth': circuit.depth(),
                'num_qubits': circuit.num_qubits,
                'num_clbits': circuit.num_clbits,
                'execution_time': getattr(job.result(), 'time_taken', None)
            }

            return QuantumResult(
                counts=counts,
                statevector=statevector,
                bio_interpretation={},  # Will be filled by bio interpreter
                metadata=metadata,
                success=True
            )

        except Exception as e:
            logger.error(f"Circuit execution failed: {str(e)}")
            return QuantumResult(
                success=False,
                error_message=f"Circuit execution failed: {str(e)}"
            )


class IBMQuantumBackend:
    """
    IBM Quantum backend for executing circuits on real quantum hardware.

    This class provides comprehensive integration with IBM Quantum services,
    including authentication, job management, queue monitoring, and error handling.
    """

    # Known IBM backends with their capabilities
    KNOWN_BACKENDS = {
        'ibm_eagle': {'qubits': 127, 'basis_gates': ['id', 'rz', 'sx', 'x', 'cx'], 'coupling_map': True},
        'ibm_condor': {'qubits': 1121, 'basis_gates': ['id', 'rz', 'sx', 'x', 'cx'], 'coupling_map': True},
        'ibm_sherbrooke': {'qubits': 127, 'basis_gates': ['id', 'rz', 'sx', 'x', 'cx'], 'coupling_map': True},
        'ibm_brisbane': {'qubits': 127, 'basis_gates': ['id', 'rz', 'sx', 'x', 'cx'], 'coupling_map': True},
        'ibm_torino': {'qubits': 133, 'basis_gates': ['id', 'rz', 'sx', 'x', 'cx', 'ecr'], 'coupling_map': True},
        'ibm_kyoto': {'qubits': 127, 'basis_gates': ['id', 'rz', 'sx', 'x', 'cx'], 'coupling_map': True},
        'ibm_osaka': {'qubits': 127, 'basis_gates': ['id', 'rz', 'sx', 'x', 'cx'], 'coupling_map': True},
        'simulator_statevector': {'qubits': 32, 'basis_gates': None, 'coupling_map': False},
        'simulator_mps': {'qubits': 100, 'basis_gates': None, 'coupling_map': False},
    }

    # BioQL pricing per shot (USD) - PRECIO FINAL PARA CLIENTE
    # Incluye margen sobre costo del proveedor
    # NO EXPONER detalles de margen o costo del proveedor al cliente
    #
    # Hardware IBM: $0.50/shot → 1000 shots = $500 USD
    # Simuladores: $0.001/shot → 1000 shots = $1 USD
    COST_PER_SHOT = {
        'ibm_eagle': 0.50,          # 127 qubits - Heron
        'ibm_condor': 0.50,         # 1121 qubits - Condor
        'ibm_sherbrooke': 0.50,     # 127 qubits - Heron
        'ibm_brisbane': 0.50,       # 127 qubits - Heron
        'ibm_torino': 0.50,         # 133 qubits - Heron r1
        'ibm_kyoto': 0.50,          # 127 qubits - Heron
        'ibm_osaka': 0.50,          # 127 qubits - Heron
        'simulator_statevector': 0.001,   # Simulador IBM
        'simulator_mps': 0.001,     # Simulador IBM
    }

    def __init__(self, backend_name: str, token: Optional[str] = None,
                 instance: Optional[str] = None, channel: str = 'ibm_quantum_platform'):
        """
        Initialize IBM Quantum backend.

        Args:
            backend_name: Name of the IBM backend to use
            token: IBM Quantum API token (if not provided, looks for env var)
            instance: IBM Quantum instance (hub/group/project)
            channel: IBM Quantum channel ('ibm_quantum_platform' or 'ibm_cloud')
        """
        if not IBM_QUANTUM_AVAILABLE:
            raise IBMQuantumError(
                "IBM Quantum libraries not available. Install with: "
                "pip install qiskit-ibm-runtime qiskit-ibm-provider"
            )

        self.backend_name = backend_name
        self.channel = channel
        self.instance = instance
        self._service = None
        self._provider = None
        self._backend = None
        self._session = None

        # Get token from environment if not provided
        if token is None:
            token = os.getenv('IBM_QUANTUM_TOKEN')
            if token is None:
                raise AuthenticationError(
                    "IBM Quantum token not found. Provide token parameter or "
                    "set IBM_QUANTUM_TOKEN environment variable."
                )

        self.token = token
        self._initialize_connection()

    @retry_on_failure(max_retries=3)
    def _initialize_connection(self) -> None:
        """Initialize connection to IBM Quantum services."""
        try:
            # Initialize runtime service
            if self.instance:
                self._service = QiskitRuntimeService(
                    channel=self.channel,
                    token=self.token,
                    instance=self.instance
                )
            else:
                self._service = QiskitRuntimeService(
                    channel=self.channel,
                    token=self.token
                )

            # Get the backend
            self._backend = self._service.backend(self.backend_name)

            # Provider functionality is now handled by QiskitRuntimeService
            self._provider = self._service

            logger.info(f"Successfully connected to IBM backend: {self.backend_name}")
            self._log_backend_info()

        except (IBMRuntimeError, IBMAccountError) as e:
            raise AuthenticationError(f"Failed to authenticate with IBM Quantum: {str(e)}")
        except Exception as e:
            if "not found" in str(e).lower():
                available_backends = self.list_available_backends()
                raise BackendNotAvailableError(
                    f"Backend '{self.backend_name}' not found. "
                    f"Available backends: {available_backends}"
                )
            raise IBMQuantumError(f"Failed to initialize IBM Quantum connection: {str(e)}")

    def _log_backend_info(self) -> None:
        """Log information about the selected backend."""
        try:
            config = self._backend.configuration()
            status = self._backend.status()

            logger.info(f"Backend: {config.backend_name}")
            logger.info(f"Qubits: {config.n_qubits}")
            logger.info(f"Operational: {status.operational}")
            logger.info(f"Pending jobs: {status.pending_jobs}")

            if hasattr(status, 'queue_length'):
                logger.info(f"Queue length: {status.queue_length}")

        except Exception as e:
            logger.warning(f"Could not retrieve backend info: {str(e)}")

    def list_available_backends(self) -> List[str]:
        """List all available backends for the current account."""
        try:
            if self._service is None:
                return list(self.KNOWN_BACKENDS.keys())

            backends = self._service.backends()
            return [backend.name for backend in backends]

        except Exception as e:
            logger.warning(f"Could not list backends: {str(e)}")
            return list(self.KNOWN_BACKENDS.keys())

    def get_backend_info(self) -> Dict[str, Any]:
        """Get detailed information about the current backend."""
        try:
            config = self._backend.configuration()
            status = self._backend.status()

            # Get coupling map safely (can be list or CouplingMap object)
            coupling_map = None
            if hasattr(config, 'coupling_map') and config.coupling_map:
                if hasattr(config.coupling_map, 'get_edges'):
                    coupling_map = config.coupling_map.get_edges()
                elif isinstance(config.coupling_map, list):
                    coupling_map = config.coupling_map

            info = {
                'name': config.backend_name,
                'version': getattr(config, 'backend_version', 'unknown'),
                'qubits': config.n_qubits,
                'basis_gates': config.basis_gates,
                'coupling_map': coupling_map,
                'operational': status.operational,
                'pending_jobs': status.pending_jobs,
                'description': getattr(config, 'description', '')
            }

            if hasattr(status, 'queue_length'):
                info['queue_length'] = status.queue_length

            return info

        except Exception as e:
            logger.error(f"Failed to get backend info: {str(e)}")
            return {'name': self.backend_name, 'error': str(e)}

    def validate_circuit(self, circuit: QuantumCircuit) -> Tuple[bool, str]:
        """Validate if circuit can run on this backend."""
        try:
            config = self._backend.configuration()

            # Check qubit count
            if circuit.num_qubits > config.n_qubits:
                return False, f"Circuit requires {circuit.num_qubits} qubits but backend only has {config.n_qubits}"

            # Check circuit depth (basic check)
            if circuit.depth() > 1000:  # Arbitrary limit
                return False, f"Circuit depth ({circuit.depth()}) may be too large for reliable execution"

            return True, "Circuit validation passed"

        except Exception as e:
            return False, f"Validation failed: {str(e)}"

    def estimate_cost(self, shots: int) -> float:
        """Estimate the cost of running the circuit."""
        base_cost = self.COST_PER_SHOT.get(self.backend_name, 0.001)
        return base_cost * shots

    def estimate_queue_time(self) -> Tuple[Optional[int], str]:
        """
        Estimate queue waiting time in minutes.

        NOTE: This is a ROUGH ESTIMATE based on pending jobs count.
        Real queue times depend on job complexity, hardware status, and priority.
        """
        try:
            status = self._backend.status()

            if not status.operational:
                return None, "Backend is not operational"

            pending_jobs = status.pending_jobs

            # ESTIMATE ONLY: assume each job takes 2-5 minutes on average
            # This is NOT accurate - real times vary significantly
            if pending_jobs == 0:
                return 0, "No queue (estimate)"
            elif pending_jobs < 5:
                return pending_jobs * 3, f"Short queue (~{pending_jobs} jobs, estimate)"
            elif pending_jobs < 20:
                return pending_jobs * 4, f"Medium queue (~{pending_jobs} jobs, estimate)"
            else:
                return pending_jobs * 5, f"Long queue ({pending_jobs} jobs, estimate)"

        except Exception as e:
            logger.warning(f"Could not estimate queue time: {str(e)}")
            return None, "Queue time unknown"

    @retry_on_failure(max_retries=2)
    def execute_circuit(self, circuit: QuantumCircuit, shots: int = 1024,
                       timeout: int = 3600, max_circuits: int = 1) -> QuantumResult:
        """
        Execute a quantum circuit on IBM hardware.

        Args:
            circuit: The quantum circuit to execute
            shots: Number of measurement shots
            timeout: Maximum time to wait for job completion (seconds)
            max_circuits: Maximum number of circuits to run in batch

        Returns:
            QuantumResult containing the computation results
        """
        start_time = time.time()

        try:
            # Check cache first
            cached_result = _circuit_cache.get(circuit, shots, self.backend_name)
            if cached_result is not None:
                logger.info("Returning cached result")
                return cached_result

            # Validate circuit
            valid, message = self.validate_circuit(circuit)
            if not valid:
                raise CircuitTooLargeError(message)

            # Log cost and queue estimates
            cost = self.estimate_cost(shots)
            queue_time, queue_status = self.estimate_queue_time()

            logger.info(f"Estimated cost: ${cost:.4f}")
            logger.info(f"Queue status: {queue_status}")
            if queue_time is not None:
                logger.info(f"Estimated queue time: {queue_time} minutes")

            # Transpile circuit for the backend
            logger.info("Transpiling circuit for backend...")
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

            # Use preset pass manager for modern Qiskit
            pm = generate_preset_pass_manager(backend=self._backend, optimization_level=1)
            transpiled_circuit = pm.run(circuit)

            # For Open plan, use SamplerV2 primitive (correct modern API)
            logger.info(f"Submitting job to {self.backend_name} with {shots} shots...")

            # REAL IBM Quantum API - SamplerV2 with mode=backend (NOT backend=backend)
            from qiskit_ibm_runtime import SamplerV2
            sampler = SamplerV2(mode=self._backend)

            # Submit job - SamplerV2 uses run([circuit], shots=N) format
            job = sampler.run([transpiled_circuit], shots=shots)

            logger.info(f"Job submitted with ID: {job.job_id()}")
            logger.info("Waiting for job completion...")

            # Wait for job completion with status updates
            result = self._wait_for_job(job, timeout)

            # Calculate timing
            execution_time = time.time() - start_time

            # Extract counts from SamplerV2 result
            # In SamplerV2, result has data attribute with BitArray
            pub_result = result[0]

            # Get the measurement data - try different possible names
            try:
                # Try the classical register name from circuit
                creg_name = list(circuit.cregs)[0].name if circuit.cregs else 'meas'
                bit_array = getattr(pub_result.data, creg_name)
            except (AttributeError, IndexError):
                # Fallback: get first available attribute that's a BitArray
                for attr_name in dir(pub_result.data):
                    if not attr_name.startswith('_'):
                        try:
                            bit_array = getattr(pub_result.data, attr_name)
                            if hasattr(bit_array, 'get_counts'):
                                break
                        except:
                            continue

            counts = bit_array.get_counts()
            int_counts = counts

            # Create metadata
            backend_info = self.get_backend_info()
            metadata = {
                'backend': self.backend_name,
                'backend_info': backend_info,
                'shots': shots,
                'circuit_depth': circuit.depth(),
                'num_qubits': circuit.num_qubits,
                'num_clbits': circuit.num_clbits,
                'transpiled_depth': transpiled_circuit.depth(),
                'job_id': job.job_id(),
                'execution_time': execution_time,
                'cost_estimate': cost,
                'queue_estimate': queue_time
            }

            quantum_result = QuantumResult(
                counts=int_counts,
                statevector=None,  # Not available from real hardware
                bio_interpretation={},
                metadata=metadata,
                success=True,
                job_id=job.job_id(),
                backend_name=self.backend_name,
                execution_time=execution_time,
                cost_estimate=cost
            )

            # Cache the result
            _circuit_cache.put(circuit, shots, self.backend_name, quantum_result)

            logger.info(f"Job completed successfully in {execution_time:.1f}s")
            return quantum_result

        except (IBMRuntimeError) as e:
            error_msg = f"IBM Quantum execution failed: {str(e)}"
            logger.error(error_msg)
            return QuantumResult(
                success=False,
                error_message=error_msg,
                metadata={'backend': self.backend_name, 'execution_time': time.time() - start_time}
            )
        except Exception as e:
            error_msg = f"Circuit execution failed: {str(e)}"
            logger.error(error_msg)
            return QuantumResult(
                success=False,
                error_message=error_msg,
                metadata={'backend': self.backend_name, 'execution_time': time.time() - start_time}
            )

    def _wait_for_job(self, job, timeout: int):
        """Wait for job completion with periodic status updates."""
        start_time = time.time()
        last_status = None

        while True:
            try:
                # Check if job is done
                status = job.status()

                if status != last_status:
                    logger.info(f"Job status: {status}")
                    last_status = status

                if job.done():
                    return job.result()

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise JobTimeoutError(
                        f"Job {job.job_id()} timed out after {timeout}s"
                    )

                # Wait before next status check
                time.sleep(min(30, max(5, timeout // 100)))  # Adaptive polling

            except JobTimeoutError:
                raise
            except Exception as e:
                logger.warning(f"Error checking job status: {str(e)}")
                time.sleep(10)

    def close(self) -> None:
        """Close the IBM Quantum connection."""
        if self._session:
            self._session.close()
        logger.info("IBM Quantum connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class IonQBackend:
    """
    IonQ quantum backend interface using qiskit-ionq provider.

    Supports IonQ quantum computers and simulators through the IonQ Cloud API.
    """

    # Known IonQ backends with their capabilities
    KNOWN_BACKENDS = {
        'ionq_simulator': {'qubits': 29, 'basis_gates': ['rx', 'ry', 'rz', 'cnot'], 'coupling_map': False, 'type': 'simulator'},
        'ionq_ideal': {'qubits': 29, 'basis_gates': ['rx', 'ry', 'rz', 'cnot'], 'coupling_map': False, 'type': 'simulator'},
        'ionq_aria_simulator': {'qubits': 25, 'basis_gates': ['rx', 'ry', 'rz', 'cnot'], 'coupling_map': False, 'type': 'simulator'},
        'ionq_harmony_simulator': {'qubits': 11, 'basis_gates': ['rx', 'ry', 'rz', 'cnot'], 'coupling_map': False, 'type': 'simulator'},
        'ionq_qpu': {'qubits': 36, 'basis_gates': ['rx', 'ry', 'rz', 'cnot'], 'coupling_map': False, 'type': 'hardware'},
    }

    # BioQL pricing per shot (USD) - PRECIO FINAL PARA CLIENTE
    # Incluye margen sobre costo del proveedor
    # NO EXPONER detalles de margen o costo del proveedor al cliente
    #
    # Hardware IonQ: $0.50/shot → 1000 shots = $500 USD
    # Simuladores: $0.001/shot → 1000 shots = $1 USD
    COST_PER_SHOT = {
        'ionq_simulator': 0.001,       # Simulador IonQ
        'ionq_ideal': 0.001,           # Simulador ideal
        'ionq_aria_simulator': 0.001,  # Simulador Aria
        'ionq_harmony_simulator': 0.001, # Simulador Harmony
        'ionq_qpu': 0.50,              # Hardware real IonQ (11 qubits)
        'ionq_forte': 0.50,            # 36 qubits - Forte
    }

    def __init__(self, backend_name: str, token: Optional[str] = None):
        """
        Initialize IonQ backend.

        Args:
            backend_name: Name of the IonQ backend ('ionq_simulator' or 'ionq_qpu')
            token: IonQ API token
        """
        if not IONQ_AVAILABLE:
            raise QuantumBackendError(
                "IonQ libraries not available. Please install qiskit-ionq"
            )

        self.backend_name = backend_name
        self._provider = None
        self._backend = None
        self._token = token

        # Load token from config if not provided
        if not self._token:
            self._token = self._load_token_from_config()

        if not self._token:
            raise AuthenticationError(
                "IonQ token not provided. Use bioql setup-keys to configure or pass token parameter."
            )

        self._initialize_provider()

    def _load_token_from_config(self) -> Optional[str]:
        """Load IonQ token from configuration file."""
        try:
            import json
            from pathlib import Path

            config_file = Path.home() / '.bioql' / 'config.json'
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('ionq_token')
        except Exception as e:
            logger.warning(f"Could not load IonQ token from config: {e}")
        return None

    def _initialize_provider(self):
        """Initialize the IonQ provider."""
        try:
            self._provider = IonQProvider(self._token)

            # Map BioQL backend names to IonQ backend names
            backend_mapping = {
                'ionq_ideal': 'ionq_simulator',
                'ionq_simulator': 'ionq_simulator',
                'ionq_aria_simulator': 'ionq_simulator',  # Aria is just simulator
                'ionq_harmony_simulator': 'ionq_simulator',  # Harmony is just simulator
                'ionq_qpu': 'ionq_qpu',
                'ionq_forte': 'ionq_qpu',  # Forte is QPU hardware
            }

            ionq_backend_name = backend_mapping.get(self.backend_name, self.backend_name)
            self._backend = self._provider.get_backend(ionq_backend_name)
            logger.info(f"Initialized IonQ backend: {self.backend_name} -> {ionq_backend_name}")
        except Exception as e:
            raise QuantumBackendError(f"Failed to initialize IonQ backend: {str(e)}")

    def execute_circuit(self, circuit: QuantumCircuit, shots: int = 1024) -> QuantumResult:
        """
        Execute a quantum circuit on IonQ backend.

        Args:
            circuit: Quantum circuit to execute
            shots: Number of measurement shots

        Returns:
            QuantumResult object with execution results
        """
        if not self._backend:
            raise QuantumBackendError("IonQ backend not initialized")

        start_time = time.time()

        try:
            logger.info(f"Submitting job to {self.backend_name} with {shots} shots...")

            # Transpile circuit for IonQ backend (IonQ recommends optimization_level=1)
            transpiled_circuit = transpile(circuit, self._backend, optimization_level=1)

            # Submit job
            job = self._backend.run(transpiled_circuit, shots=shots)

            # Wait for completion
            logger.info(f"Job submitted. Job ID: {job.job_id()}")
            result = job.result()

            execution_time = time.time() - start_time

            # Get counts
            counts = result.get_counts()

            # Calculate cost estimate
            cost = self.COST_PER_SHOT.get(self.backend_name, 0.01) * shots

            # Create metadata
            metadata = {
                'backend': self.backend_name,
                'shots': shots,
                'circuit_depth': circuit.depth(),
                'num_qubits': circuit.num_qubits,
                'num_clbits': circuit.num_clbits,
                'execution_time': execution_time,
                'cost_estimate': cost,
                'job_id': job.job_id(),
                'provider': 'ionq'
            }

            logger.info(f"Job completed in {execution_time:.2f}s")

            return QuantumResult(
                counts=counts,
                success=True,
                metadata=metadata,
                cost_estimate=cost,
                job_id=job.job_id(),
                backend_name=self.backend_name,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"IonQ execution failed: {str(e)}"
            logger.error(error_msg)

            return QuantumResult(
                counts={},
                success=False,
                error_message=error_msg,
                execution_time=execution_time,
                backend_name=self.backend_name
            )

    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the IonQ backend."""
        backend_info = self.KNOWN_BACKENDS.get(self.backend_name, {})
        return {
            'name': self.backend_name,
            'provider': 'ionq',
            'qubits': backend_info.get('qubits', 32),
            'basis_gates': backend_info.get('basis_gates', ['rx', 'ry', 'rz', 'cnot']),
            'coupling_map': backend_info.get('coupling_map', False),
            'cost_per_shot': self.COST_PER_SHOT.get(self.backend_name, 0.01),
            'operational': True  # Assume operational
        }

    def list_available_backends(self) -> List[str]:
        """List available IonQ backends."""
        if self._provider:
            try:
                backends = self._provider.backends()
                return [backend.name() for backend in backends]
            except Exception as e:
                logger.warning(f"Could not query IonQ backends: {str(e)}")
                return list(self.KNOWN_BACKENDS.keys())
        else:
            return list(self.KNOWN_BACKENDS.keys())


def select_best_backend(required_qubits: int, prefer_simulator: bool = False,
                       available_backends: Optional[List[str]] = None,
                       service: Optional[Any] = None) -> str:
    """
    Select the best IBM Quantum backend based on requirements.

    Args:
        required_qubits: Minimum number of qubits needed
        prefer_simulator: Whether to prefer simulator backends
        available_backends: List of available backend names (if known)
        service: QiskitRuntimeService instance to query real backends

    Returns:
        Name of the recommended backend

    Raises:
        BackendNotAvailableError: If no suitable backend is found
    """
    # Get available backends
    if available_backends is None and service is not None:
        try:
            backends = service.backends()
            available_backends = [backend.name for backend in backends if backend.operational]
        except Exception as e:
            logger.warning(f"Could not query available backends: {str(e)}")
            available_backends = list(IBMQuantumBackend.KNOWN_BACKENDS.keys())
    elif available_backends is None:
        available_backends = list(IBMQuantumBackend.KNOWN_BACKENDS.keys())

    # Filter by qubit requirements
    suitable_backends = []
    for backend_name in available_backends:
        backend_info = IBMQuantumBackend.KNOWN_BACKENDS.get(backend_name, {})
        backend_qubits = backend_info.get('qubits', 0)

        if backend_qubits >= required_qubits:
            suitable_backends.append((backend_name, backend_info))

    if not suitable_backends:
        raise BackendNotAvailableError(
            f"No backend found with at least {required_qubits} qubits. "
            f"Available backends: {available_backends}"
        )

    # Sort by preference
    def backend_priority(backend_tuple):
        name, info = backend_tuple
        qubits = info.get('qubits', 0)
        is_simulator = 'simulator' in name.lower()

        if prefer_simulator:
            # Prefer simulators, then by qubit count (ascending)
            return (0 if is_simulator else 1, qubits)
        else:
            # Prefer real hardware, then by qubit count (ascending to minimize cost)
            return (1 if is_simulator else 0, qubits)

    suitable_backends.sort(key=backend_priority)
    selected_backend = suitable_backends[0][0]

    logger.info(f"Selected backend: {selected_backend} for {required_qubits} qubits")
    return selected_backend


def get_backend_recommendations(circuit: QuantumCircuit,
                               service: Optional[Any] = None) -> Dict[str, Any]:
    """
    Get backend recommendations for a specific circuit.

    Args:
        circuit: The quantum circuit to analyze
        service: QiskitRuntimeService instance to query real backends

    Returns:
        Dictionary with backend recommendations and analysis
    """
    required_qubits = circuit.num_qubits
    circuit_depth = circuit.depth()

    # Get available backends
    available_backends = []
    if service is not None:
        try:
            backends = service.backends()
            for backend in backends:
                if backend.operational:
                    available_backends.append({
                        'name': backend.name,
                        'qubits': backend.configuration().n_qubits,
                        'pending_jobs': backend.status().pending_jobs,
                        'operational': backend.status().operational
                    })
        except Exception as e:
            logger.warning(f"Could not query backends: {str(e)}")

    # Analyze circuit requirements
    recommendations = {
        'circuit_analysis': {
            'qubits_required': required_qubits,
            'circuit_depth': circuit_depth,
            'complexity': 'low' if circuit_depth < 50 else 'medium' if circuit_depth < 200 else 'high'
        },
        'recommended_backends': {},
        'cost_estimates': {},
        'warnings': []
    }

    # Add recommendations for different categories
    try:
        # Best simulator
        sim_backend = select_best_backend(required_qubits, prefer_simulator=True)
        recommendations['recommended_backends']['best_simulator'] = sim_backend
        recommendations['cost_estimates'][sim_backend] = 0.0

        # Best real hardware
        hw_backend = select_best_backend(required_qubits, prefer_simulator=False)
        recommendations['recommended_backends']['best_hardware'] = hw_backend
        cost = IBMQuantumBackend.COST_PER_SHOT.get(hw_backend, 0.001) * 1024  # Default 1024 shots
        recommendations['cost_estimates'][hw_backend] = cost

        # Add warnings
        if circuit_depth > 100:
            recommendations['warnings'].append(
                f"Circuit depth ({circuit_depth}) is high. Consider circuit optimization."
            )

        if required_qubits > 50:
            recommendations['warnings'].append(
                f"Large circuit ({required_qubits} qubits) will be expensive on real hardware."
            )

    except BackendNotAvailableError as e:
        recommendations['warnings'].append(str(e))

    return recommendations


def parse_bioql_program(program: str) -> QuantumCircuit:
    """
    Parse a BioQL natural language program into a quantum circuit.

    Uses the real BioQL compiler to convert natural language descriptions
    into optimized quantum circuits for biological applications.

    Args:
        program: Natural language description of the quantum program

    Returns:
        Quantum circuit representing the program

    Raises:
        ProgramParsingError: If the program cannot be parsed
    """
    # Real BioQL compiler implementation
    logger.info("Parsing natural language using BioQL compiler")

    try:
        # Use the real BioQL compiler to parse natural language
        from .compiler import BioQLCompiler

        compiler = BioQLCompiler()
        circuit = compiler.parse_to_circuit(program)

        if circuit is None:
            raise ProgramParsingError("Compiler returned None - this should never happen with real BioQL compiler")

        logger.info(f"Parsed program into circuit with {circuit.num_qubits} qubits, {len(circuit.data)} operations")
        return circuit

    except Exception as e:
        logger.error(f"BioQL compiler failed: {e}")
        raise ProgramParsingError(f"Real BioQL compiler failed to parse program: {str(e)}")


def _load_ionq_token_from_config() -> Optional[str]:
    """
    Load IonQ token from provider configuration (SERVER SIDE).

    IMPORTANTE: Este token es del PROVEEDOR (SpectrixRD), no del cliente.
    """
    import json
    from pathlib import Path

    # 1. Intentar cargar desde SERVER
    server_config_paths = [
        Path.home() / "Desktop" / "Server_bioql" / "config_providers" / "quantum_providers.json",
        Path("/Users/heinzjungbluth/Desktop/Server_bioql/config_providers/quantum_providers.json"),
    ]

    for config_path in server_config_paths:
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    token = config.get('providers', {}).get('ionq', {}).get('token')
                    if token:
                        logger.debug(f"Loaded IonQ token from server config: {config_path}")
                        return token
        except Exception as e:
            logger.debug(f"Could not load IonQ token from {config_path}: {e}")

    # 2. Environment variable
    import os
    env_token = os.getenv('IONQ_API_KEY')
    if env_token:
        logger.debug("Loaded IonQ token from environment variable")
        return env_token

    logger.warning("IonQ token not found in any configuration")
    return None


def _load_ibm_config_from_server() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Load IBM Quantum token, instance AND channel from provider configuration (SERVER SIDE).

    IMPORTANTE: Estos datos son del PROVEEDOR (SpectrixRD), no del cliente.
    El cliente solo necesita su BioQL API key.

    Returns:
        tuple: (token, instance, channel)
    """
    import json
    from pathlib import Path

    # 1. Intentar cargar desde SERVER (Desktop/Server_bioql)
    server_config_paths = [
        Path.home() / "Desktop" / "Server_bioql" / "config_providers" / "quantum_providers.json",
        Path("/Users/heinzjungbluth/Desktop/Server_bioql/config_providers/quantum_providers.json"),
    ]

    for config_path in server_config_paths:
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    ibm_config = config.get('providers', {}).get('ibm_quantum', {})
                    token = ibm_config.get('token')
                    instance = ibm_config.get('instance')
                    channel = ibm_config.get('channel', 'ibm_quantum_platform')
                    if token:
                        logger.debug(f"Loaded IBM config from server: {config_path}")
                        logger.debug(f"Instance: {instance}, Channel: {channel}")
                        return token, instance, channel
        except Exception as e:
            logger.debug(f"Could not load from {config_path}: {e}")

    return None, None, 'ibm_quantum_platform'


def _load_ibm_token_from_config() -> Optional[str]:
    """
    Load IBM Quantum token from provider configuration (SERVER SIDE).

    IMPORTANTE: Este token es del PROVEEDOR (SpectrixRD), no del cliente.
    El cliente solo necesita su BioQL API key.

    Busca en este orden:
    1. Server_bioql/config_providers/quantum_providers.json (SERVIDOR)
    2. ~/.bioql/config.json (fallback legacy)
    3. Environment variable IBM_QUANTUM_TOKEN (desarrollo)
    """
    # Usar la nueva función que devuelve token, instance y channel
    token, _, _ = _load_ibm_config_from_server()
    if token:
        return token

    # 2. Fallback: config antiguo
    try:
        config_file = Path.home() / '.bioql' / 'config.json'
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                token = config.get('ibm_token')
                if token:
                    logger.debug("Loaded IBM token from legacy config")
                    return token
    except Exception as e:
        logger.debug(f"Could not load from legacy config: {e}")

    # 3. Fallback: environment variable (desarrollo)
    import os
    env_token = os.getenv('IBM_QUANTUM_TOKEN')
    if env_token:
        logger.debug("Loaded IBM token from environment variable")
        return env_token

    logger.warning("IBM Quantum token not found in any configuration")
    return None


def quantum(
    program: str,
    api_key: str,  # BioQL API key (REQUIRED) - cliente solo necesita esto
    backend: str = 'simulator',
    shots: int = 1024,
    debug: bool = False,
    instance: Optional[str] = None,
    timeout: int = 3600,
    auto_select: bool = False,
    # QEC parameters (NEW in v5.0.0)
    num_qubits: Optional[int] = None,  # Physical qubits
    num_logical_qubits: Optional[int] = None,  # Logical qubits after QEC
    topology: str = 'linear',  # 'linear', 'grid', 'all-to-all'
    error_correction: Optional[str] = None,  # 'surface_code', 'steane', 'shor'
    correction_level: str = 'medium',  # 'low' (d=3), 'medium' (d=5), 'high' (d=7)
    error_threshold: float = 0.001,
    mitigation: Optional[List[str]] = None,
    mitigation_strength: float = 0.8,
    qec: Optional[Any] = None,  # QEC config object
    target_fidelity: float = 0.95,
    visualize: bool = False,  # Generate Qualtran visualizations
    mode: Optional[str] = None  # NEW in v5.4.3: 'crispr' for CRISPR-QAI mode
) -> QuantumResult:
    """
    Execute a BioQL quantum program.

    This is the main entry point for BioQL quantum computations. It accepts
    natural language descriptions of quantum programs and executes them on
    the specified backend, including real IBM Quantum hardware.

    IMPORTANTE: El cliente SOLO necesita su BioQL API key. BioQL maneja
    internamente las credenciales de IBM Quantum, IonQ, etc.

    Args:
        program: Natural language description of the quantum program
        api_key: BioQL API key (REQUIRED) - obtén tu clave en https://bioql.com
        backend: Quantum backend to use. Options include:
                - 'simulator', 'sim', 'aer': Local simulator
                - 'ibm_torino', 'ibm_brisbane', etc.: IBM Quantum hardware
                - 'ionq_ideal', 'ionq_aria_simulator': IonQ simulators (gratis)
                - 'ionq_qpu': IonQ hardware
                - 'auto': Automatically select best backend
        shots: Number of measurement shots to perform
        debug: Whether to enable debug mode with additional logging
        instance: IBM Quantum instance (hub/group/project format) - opcional
        timeout: Maximum time to wait for job completion (seconds)
        auto_select: Whether to automatically select the best backend for the circuit

        QEC Parameters (NEW in v5.0.0):
        num_qubits: Total number of physical qubits to use
        num_logical_qubits: Number of logical qubits (before QEC overhead)
        topology: Qubit topology - 'linear', 'grid', or 'all-to-all'
        error_correction: QEC code to use - 'surface_code', 'steane', 'shor', or None
        correction_level: QEC strength - 'low' (d=3), 'medium' (d=5), 'high' (d=7)
        error_threshold: Physical error rate threshold (default: 0.001)
        mitigation: List of error mitigation methods to apply - ['readout', 'zne', 'pec', 'symmetry']
        mitigation_strength: Strength of error mitigation (0.0-1.0, default: 0.8)
        qec: Pre-configured QEC object (advanced usage)
        target_fidelity: Target fidelity after QEC/mitigation (default: 0.95)
        visualize: Generate Qualtran visualization graphs (default: False)

    Returns:
        QuantumResult object containing the computation results

    Raises:
        QuantumBackendError: If the backend is not available
        ProgramParsingError: If the program cannot be parsed
        AuthenticationError: If BioQL API key authentication fails
        JobTimeoutError: If the job times out

    Examples:
        >>> # Run on local simulator (BioQL API key required)
        >>> result = quantum("Create a Bell state and measure both qubits",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx")
        >>> print(result.counts)
        {'00': 512, '11': 512}

        >>> # Run on IBM Torino (133 qubits, hardware real)
        >>> result = quantum("Put qubit in superposition",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx",
        ...                  backend='ibm_torino')
        >>> print(result.cost_estimate)
        3.20  # Precio con 60% margen

        >>> # Run on IonQ Ideal Simulator (GRATIS)
        >>> result = quantum("Generate 3-qubit GHZ state",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx",
        ...                  backend='ionq_ideal')
        >>> print(result.cost_estimate)
        0.10  # Minimal fee

        >>> # Automatically select best backend
        >>> result = quantum("Random circuit",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx",
        ...                  backend='auto',
        ...                  auto_select=True)
        >>> print(result.backend_name)
        'ibm_torino'

        >>> # Get cost and queue estimates
        >>> result = quantum("Random circuit",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx",
        ...                  backend='ibm_brisbane',
        ...                  shots=2048,
        ...                  debug=True)
        >>> print(f"Cost: ${result.cost_estimate:.4f}")  # Precio BioQL (con margen)
        >>> print(f"Queue time: {result.metadata.get('queue_estimate')} min")

        >>> # NEW in v5.0.0: QEC with Surface Code (medium level)
        >>> result = quantum("Create Bell state",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx",
        ...                  backend='ibm_torino',
        ...                  error_correction='surface_code',
        ...                  correction_level='medium',
        ...                  num_logical_qubits=2)
        >>> print(result.qec_metrics)
        {'enabled': True, 'logical_qubits': 2, 'physical_qubits': 98, 'code_distance': 7, ...}

        >>> # QEC with error mitigation
        >>> result = quantum("VQE simulation",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx",
        ...                  backend='ibm_brisbane',
        ...                  error_correction='steane',
        ...                  mitigation=['readout', 'zne', 'pec'],
        ...                  target_fidelity=0.99)
        >>> print(f"Expected fidelity: {result.qec_metrics['expected_fidelity']:.4f}")
        >>> print(f"Accuracy improvement: {result.qec_metrics['accuracy_improvement']:.1f}%")

        >>> # Generate QEC visualizations
        >>> result = quantum("Quantum chemistry",
        ...                  api_key="bioql_sk_xxxxxxxxxxxxx",
        ...                  error_correction='surface_code',
        ...                  correction_level='high',
        ...                  visualize=True)
        >>> print(f"Visualization saved to: {result.visualization_path}")
    """
    # Configure logging for debug mode
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug(f"Debug mode enabled for program: {program}")

    try:
        # NEW in v5.4.3: CRISPR-QAI mode
        if mode == 'crispr':
            logger.info("CRISPR-QAI mode detected, routing to CRISPR module")
            try:
                from .crispr_qai import estimate_energy_collapse_simulator, estimate_energy_collapse_qiskit, estimate_energy_collapse_braket

                # Extract guide sequence from program
                import re
                guide_match = re.search(r'guide\s+([ATCG]{15,25})', program, re.IGNORECASE)
                if not guide_match:
                    raise ValueError("No valid guide sequence found in program. Use format: 'Score CRISPR guide ATCGAAGTCGCTAGCTA'")

                guide_seq = guide_match.group(1)
                logger.info(f"Extracted guide sequence: {guide_seq}")

                # Route to appropriate backend
                if backend == 'simulator' or backend == 'sim' or backend == 'aer':
                    crispr_result = estimate_energy_collapse_simulator(
                        guide_seq=guide_seq,
                        shots=shots,
                        coupling_strength=1.0,
                        seed=42
                    )
                elif 'ibm' in backend.lower() or 'qiskit' in backend.lower():
                    crispr_result = estimate_energy_collapse_qiskit(
                        guide_seq=guide_seq,
                        backend_name=backend,
                        shots=shots,
                        coupling_strength=1.0,
                        ibm_token=None  # BioQL handles this internally
                    )
                elif 'braket' in backend.lower() or 'aws' in backend.lower() or backend in ['SV1', 'DM1', 'Aspen-M-3', 'Harmony']:
                    crispr_result = estimate_energy_collapse_braket(
                        guide_seq=guide_seq,
                        backend_name=backend,
                        shots=shots,
                        coupling_strength=1.0,
                        aws_region='us-east-1',
                        s3_bucket='bioql-braket-results'
                    )
                else:
                    # Default to simulator
                    crispr_result = estimate_energy_collapse_simulator(
                        guide_seq=guide_seq,
                        shots=shots,
                        coupling_strength=1.0,
                        seed=42
                    )

                # Convert CRISPR result to QuantumResult format
                quantum_result = QuantumResult(
                    counts={},  # CRISPR doesn't use counts
                    backend_name=crispr_result.get('backend', backend),
                    job_id=None,
                    execution_time=crispr_result.get('runtime_seconds', 0.0),
                    metadata={
                        'mode': 'crispr',
                        'guide_sequence': guide_seq,
                        'energy_estimate': crispr_result.get('energy_estimate'),
                        'confidence': crispr_result.get('confidence'),
                        'num_qubits': crispr_result.get('num_qubits'),
                        'coupling_strength': 1.0,
                        **crispr_result
                    }
                )

                # Add CRISPR-specific attributes to result dynamically
                quantum_result.energy_estimate = crispr_result.get('energy_estimate')
                quantum_result.confidence = crispr_result.get('confidence')
                quantum_result.guide_sequence = guide_seq

                logger.info(f"CRISPR computation complete: Energy={quantum_result.energy_estimate:.4f}")
                return quantum_result

            except ImportError:
                logger.error("CRISPR-QAI module not available. Install with: pip install bioql[qec]")
                raise BioQLError("CRISPR-QAI module not installed")

        # Validate inputs
        if not isinstance(program, str) or not program.strip():
            raise ProgramParsingError("Program must be a non-empty string")

        if shots <= 0:
            raise ValueError("Shots must be a positive integer")

        # MANDATORY API KEY AUTHENTICATION
        # Import cloud authentication module
        from .cloud_auth import authenticate_api_key, check_usage_limits, record_usage

        # Step 1: Authenticate API key (REQUIRED)
        try:
            user_info = authenticate_api_key(api_key)
            logger.debug(f"Authentication successful for user: {user_info.get('email')}")
        except Exception as auth_error:
            raise AuthenticationError(
                f"BioQL API key authentication failed: {auth_error}\n\n"
                f"🔑 Get your API key at: https://bioql.com/signup\n"
                f"📧 Already have an account? Login at: https://bioql.com/login\n"
                f"💡 Need help? Contact: support@bioql.com"
            )

        # Step 2: Check usage limits (REQUIRED)
        try:
            limits_check = check_usage_limits(api_key, shots, backend)
            if not limits_check.get('allowed', False):
                raise ValueError(
                    f"Usage limit exceeded: {limits_check.get('reason')}\n\n"
                    f"💰 Upgrade your plan at: https://bioql.com/pricing\n"
                    f"📊 Check usage at: https://bioql.com/dashboard"
                )

            estimated_cost = limits_check.get('cost', 0.0)
            logger.debug(f"Usage check passed. Estimated cost: ${estimated_cost:.4f}")

        except Exception as limit_error:
            raise ValueError(f"Usage validation failed: {limit_error}")

        # Extract user info for billing
        user_id = user_info.get('user_id')
        api_key_id = user_info.get('api_key_id')

        # Authentication successful - extract user info for tracking
        user_email = user_info.get('email', 'unknown')
        user_plan = user_info.get('plan', 'free')
        logger.info(f"✅ Authenticated user: {user_email} ({user_plan})")

        # Load provider tokens from config (cliente NO proporciona estos tokens)
        provider_ibm_token = None
        provider_ionq_token = None
        provider_ibm_instance = None
        provider_ibm_channel = 'ibm_quantum_platform'

        if backend.startswith('ibm_'):
            # Cargar token, instance y channel de IBM del proveedor (SpectrixRD)
            provider_ibm_token, provider_ibm_instance, provider_ibm_channel = _load_ibm_config_from_server()
            if not provider_ibm_token:
                logger.warning("IBM Quantum token not found in provider config")

            # Usar la instance del servidor si no se especificó una
            if not instance and provider_ibm_instance:
                instance = provider_ibm_instance
                logger.debug(f"Using IBM instance from server config: {instance}")

            logger.debug(f"Using IBM channel: {provider_ibm_channel}")

        elif backend.startswith('ionq_'):
            # Cargar token de IonQ del proveedor (SpectrixRD) desde SERVIDOR
            provider_ionq_token = _load_ionq_token_from_config()
            if not provider_ionq_token:
                logger.warning("IonQ token not found in provider config")

        # Parse the natural language program
        logger.info(f"Parsing BioQL program: {program[:50]}...")
        circuit = parse_bioql_program(program)

        # ===== QEC PROCESSING (NEW in v5.0.0) =====
        qec_config = None
        qec_result = None
        visualization_output = None
        resource_estimates = None

        # Auto-create QEC config if error_correction is specified
        if error_correction is not None or qec is not None:
            try:
                logger.info("QEC enabled - initializing error correction")

                # Import QEC modules
                from .qualtran_qec import QuantumErrorCorrection
                from .advanced_qec import AdvancedErrorMitigation

                # Determine number of logical qubits
                circuit_logical_qubits = num_logical_qubits if num_logical_qubits else circuit.num_qubits

                # Map correction_level to QEC code
                qec_code_map = {
                    'low': 'surface_15_1_3',      # d=3, 15 physical per logical
                    'medium': 'surface_49_1_7',   # d=7, 49 physical per logical
                    'high': 'surface_49_1_7'      # d=7, 49 physical per logical
                }

                # Map error_correction to QEC code
                if error_correction:
                    if error_correction.lower() in ['surface_code', 'surface']:
                        qec_code = qec_code_map.get(correction_level, 'surface_15_1_3')
                    elif error_correction.lower() == 'steane':
                        qec_code = 'steane_7_1_3'
                    elif error_correction.lower() == 'shor':
                        qec_code = 'surface_15_1_3'  # Use surface code for now
                    else:
                        qec_code = qec_code_map.get(correction_level, 'surface_15_1_3')
                else:
                    qec_code = qec_code_map.get(correction_level, 'surface_15_1_3')

                # Initialize QEC engine
                qec_engine = QuantumErrorCorrection()

                # Analyze QEC requirements
                qec_result = qec_engine.analyze_qec_cost(
                    algorithm=program[:50],
                    num_logical_qubits=circuit_logical_qubits,
                    qec_code=qec_code,
                    physical_error_rate=error_threshold
                )

                if qec_result.success:
                    logger.info(f"QEC Analysis Complete:")
                    logger.info(f"  Logical qubits: {qec_result.num_logical_qubits}")
                    logger.info(f"  Physical qubits: {qec_result.num_physical_qubits}")
                    logger.info(f"  Code distance: {qec_result.code_distance}")
                    logger.info(f"  Physical error rate: {qec_result.error_rate_physical:.6f}")
                    logger.info(f"  Logical error rate: {qec_result.error_rate_logical:.6f}")
                    logger.info(f"  Accuracy improvement: {qec_result.accuracy_improvement:.2f}%")

                    # Validate against backend limits
                    if num_qubits and qec_result.num_physical_qubits > num_qubits:
                        logger.warning(f"QEC requires {qec_result.num_physical_qubits} physical qubits, but only {num_qubits} requested")
                        logger.warning("Circuit may not fit on requested hardware")

                    # Store resource estimation
                    resource_estimates = {
                        'logical_qubits': qec_result.num_logical_qubits,
                        'physical_qubits': qec_result.num_physical_qubits,
                        'overhead_factor': qec_result.num_physical_qubits / qec_result.num_logical_qubits,
                        'code_distance': qec_result.code_distance,
                        'qec_code': qec_code,
                        'topology': topology,
                        'error_rate_physical': qec_result.error_rate_physical,
                        'error_rate_logical': qec_result.error_rate_logical,
                        'target_fidelity': target_fidelity,
                        'expected_fidelity': 1.0 - qec_result.error_rate_logical
                    }

                    # Generate visualizations if requested
                    if visualize:
                        try:
                            import os
                            import tempfile
                            from pathlib import Path

                            # Create visualization directory
                            viz_dir = Path(tempfile.gettempdir()) / 'bioql_qec_viz'
                            viz_dir.mkdir(exist_ok=True)

                            # Generate visualization filename
                            import datetime
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            viz_path = viz_dir / f'qec_analysis_{timestamp}.png'

                            logger.info(f"QEC visualization would be saved to: {viz_path}")
                            visualization_output = str(viz_path)

                        except Exception as viz_error:
                            logger.warning(f"Could not generate QEC visualization: {viz_error}")

                else:
                    logger.warning(f"QEC analysis failed: {qec_result.error_message}")

            except ImportError as e:
                logger.warning(f"QEC modules not available: {e}")
                logger.warning("Continuing without QEC - install qualtran for QEC support")
            except Exception as e:
                logger.warning(f"QEC initialization failed: {e}")
                logger.warning("Continuing without QEC")

        # Determine the actual backend to use
        actual_backend = backend.lower()

        # Handle auto-selection
        if actual_backend == 'auto' or auto_select:
            if IBM_QUANTUM_AVAILABLE and provider_ibm_token:
                try:
                    # Try to connect to IBM Quantum for backend selection
                    temp_service = QiskitRuntimeService(token=provider_ibm_token, instance=instance) if instance else QiskitRuntimeService(token=provider_ibm_token)
                    actual_backend = select_best_backend(
                        circuit.num_qubits,
                        prefer_simulator=False,
                        service=temp_service
                    )
                    logger.info(f"Auto-selected backend: {actual_backend}")
                except Exception as e:
                    logger.warning(f"Auto-selection failed, falling back to simulator: {str(e)}")
                    actual_backend = 'simulator'
            else:
                actual_backend = 'simulator'

        # Show circuit recommendations in debug mode
        if debug:
            try:
                if IBM_QUANTUM_AVAILABLE and provider_ibm_token:
                    temp_service = QiskitRuntimeService(token=provider_ibm_token, instance=instance) if instance else QiskitRuntimeService(token=provider_ibm_token)
                    recommendations = get_backend_recommendations(circuit, temp_service)
                    logger.debug(f"Backend recommendations: {recommendations}")
            except Exception as e:
                logger.debug(f"Could not get recommendations: {str(e)}")

        # Initialize quantum backend
        quantum_backend = None
        if actual_backend in ['simulator', 'sim', 'aer']:
            quantum_backend = QuantumSimulator('aer_simulator')
            logger.info(f"Using local simulator")
        elif actual_backend.startswith('ionq_'):
            # IonQ backend
            if not IONQ_AVAILABLE:
                raise QuantumBackendError(
                    "IonQ not available. Install with: pip install qiskit-ionq"
                )

            logger.info(f"Initializing IonQ backend: {actual_backend}")
            quantum_backend = IonQBackend(
                backend_name=actual_backend,
                token=provider_ionq_token  # Usa token del proveedor, no del cliente
            )

            # Log cost estimate
            cost = IonQBackend.COST_PER_SHOT.get(actual_backend, 0.01) * shots
            logger.info(f"Estimated cost: ${cost:.3f}")

        elif actual_backend.startswith('ibm_') or actual_backend.startswith('simulator_'):
            # IBM Quantum backend
            if not IBM_QUANTUM_AVAILABLE:
                raise QuantumBackendError(
                    "IBM Quantum not available. Install with: pip install qiskit-ibm-runtime qiskit-ibm-provider"
                )

            logger.info(f"Initializing IBM backend: {actual_backend}")
            quantum_backend = IBMQuantumBackend(
                backend_name=actual_backend,
                token=provider_ibm_token,  # Usa token del proveedor, no del cliente
                instance=instance,
                channel=provider_ibm_channel  # Usar channel del config
            )

            # Log cost and queue estimates
            cost = quantum_backend.estimate_cost(shots)
            queue_time, queue_status = quantum_backend.estimate_queue_time()
            logger.info(f"Estimated cost: ${cost:.4f}")
            logger.info(f"Queue status: {queue_status}")
            if queue_time is not None:
                logger.info(f"Estimated queue time: {queue_time} minutes")

        else:
            raise QuantumBackendError(f"Unknown backend '{actual_backend}'. Supported: simulator, ionq_simulator, ionq_qpu, ibm_eagle, ibm_condor, etc.")

        # Execute the circuit
        logger.info(f"Executing circuit on {actual_backend} with {shots} shots")

        if isinstance(quantum_backend, QuantumSimulator):
            result = quantum_backend.execute_circuit(
                circuit,
                shots=shots,
                get_statevector=debug
            )
        elif isinstance(quantum_backend, IonQBackend):
            result = quantum_backend.execute_circuit(
                circuit,
                shots=shots
            )
        else:  # IBM backend
            result = quantum_backend.execute_circuit(
                circuit,
                shots=shots,
                timeout=timeout
            )

        # Add program information to metadata
        result.metadata['original_program'] = program
        result.metadata['backend_requested'] = backend
        result.metadata['backend_used'] = actual_backend

        # ===== ERROR MITIGATION (NEW in v5.0.0) =====
        mitigation_result = None
        if mitigation is not None and len(mitigation) > 0:
            try:
                logger.info(f"Applying error mitigation: {mitigation}")
                from .advanced_qec import AdvancedErrorMitigation

                # Initialize error mitigation engine
                em_engine = AdvancedErrorMitigation()

                # Apply mitigation to counts
                mitigation_result = em_engine.apply_full_mitigation(
                    counts=result.counts,
                    num_qubits=circuit.num_qubits,
                    methods=mitigation
                )

                if mitigation_result.success:
                    logger.info(f"Error mitigation applied successfully")
                    logger.info(f"  Original accuracy: {mitigation_result.accuracy_original:.1f}%")
                    logger.info(f"  Mitigated accuracy: {mitigation_result.accuracy_mitigated:.1f}%")
                    logger.info(f"  Improvement: {mitigation_result.improvement_percent:.1f}%")

                    # Replace counts with mitigated counts
                    result.counts = mitigation_result.mitigated_counts

                    # Add mitigation info to metadata
                    result.metadata['error_mitigation'] = {
                        'methods': mitigation,
                        'strength': mitigation_strength,
                        'accuracy_original': mitigation_result.accuracy_original,
                        'accuracy_mitigated': mitigation_result.accuracy_mitigated,
                        'improvement_percent': mitigation_result.improvement_percent
                    }
                else:
                    logger.warning("Error mitigation failed, using original counts")

            except ImportError:
                logger.warning("Error mitigation module not available")
            except Exception as e:
                logger.warning(f"Error mitigation failed: {e}")

        # ===== ADD QEC METRICS TO RESULT =====
        if qec_result is not None and qec_result.success:
            result.qec_metrics = {
                'enabled': True,
                'qec_code': resource_estimates.get('qec_code') if resource_estimates else None,
                'logical_qubits': qec_result.num_logical_qubits,
                'physical_qubits': qec_result.num_physical_qubits,
                'overhead_factor': qec_result.num_physical_qubits / qec_result.num_logical_qubits,
                'code_distance': qec_result.code_distance,
                'error_rate_physical': qec_result.error_rate_physical,
                'error_rate_logical': qec_result.error_rate_logical,
                'accuracy_improvement': qec_result.accuracy_improvement,
                'target_fidelity': target_fidelity,
                'expected_fidelity': 1.0 - qec_result.error_rate_logical
            }

            if mitigation_result and mitigation_result.success:
                result.qec_metrics['error_mitigation'] = {
                    'applied': True,
                    'methods': mitigation,
                    'accuracy_improvement': mitigation_result.improvement_percent
                }

        else:
            result.qec_metrics = {'enabled': False}

        # Add resource estimation
        if resource_estimates:
            result.resource_estimation = resource_estimates

        # Add visualization path
        if visualization_output:
            result.visualization_path = visualization_output

        # Real biological interpretation using bio_interpreter module
        try:
            from .bio_interpreter import interpret_bio_results
            import re

            # Build context dictionary with extracted parameters
            context = {}
            program_lower = program.lower()

            # Detect application type
            # IMPORTANT: Check DRUG_DESIGN before DRUG_DOCKING
            if ("design" in program_lower or "generate" in program_lower or "create" in program_lower) and \
               ("drug" in program_lower or "molecule" in program_lower):
                context['application'] = "drug_design"

                # Extract disease/target for drug design
                diseases = {
                    'obesity': 'obesity',
                    'diabetes': 'diabetes',
                    'cancer': 'cancer',
                    'alzheimer': 'alzheimers',
                    'parkinson': 'parkinsons',
                    'hypertension': 'hypertension',
                    'depression': 'depression',
                    'pain': 'pain'
                }
                for keyword, disease in diseases.items():
                    if keyword in program_lower:
                        context['disease'] = disease
                        break

                # Extract target
                if 'glp-1' in program_lower or 'glp1' in program_lower:
                    context['target'] = 'GLP1R'
                elif 'gip' in program_lower:
                    context['target'] = 'GIP'

            elif "protein" in program_lower or "folding" in program_lower:
                context['application'] = "protein_folding"
            elif "drug" in program_lower or "binding" in program_lower or "docking" in program_lower:
                context['application'] = "molecular_docking"
            elif "dna" in program_lower or "sequence" in program_lower:
                context['application'] = "dna_analysis"
            else:
                context['application'] = "general"

            # Extract SMILES from program text
            # Pattern: "SMILES <smiles_string>" or "with SMILES <smiles_string>"
            smiles_match = re.search(r'smiles\s+([A-Za-z0-9@+\-\[\]\(\)=#$]+)', program, re.IGNORECASE)
            if smiles_match:
                context['smiles'] = smiles_match.group(1)

            # Extract PDB ID from program text
            # Pattern: "PDB <pdb_id>", "pdb=<pdb_id>", "PDB:<pdb_id>", "receptor PDB <pdb_id>"
            # PDB IDs are exactly 4 characters: 1 digit + 3 alphanumeric (e.g., 6B3J, 1ABC, 7DTY)
            pdb_match = re.search(r'pdb[\s=:_]+(\d[A-Za-z0-9]{3})(?:\s|$|[,;.])', program, re.IGNORECASE)
            if pdb_match:
                context['pdb_id'] = pdb_match.group(1).upper()

            # Extract molecule/ligand names
            ligand_match = re.search(r'ligand\s+(?:with\s+smiles\s+)?([A-Za-z0-9@+\-\[\]\(\)=#$]+)', program, re.IGNORECASE)
            if ligand_match and 'smiles' not in context:
                # This might be a molecule name, not SMILES
                context['ligand'] = ligand_match.group(1)

            receptor_match = re.search(r'(?:receptor|protein|target)\s+(?:pdb\s+)?([A-Za-z0-9]+)', program, re.IGNORECASE)
            if receptor_match and 'pdb_id' not in context:
                context['receptor'] = receptor_match.group(1)

                # Automatic PDB lookup for known receptors
                try:
                    from bioql.drug_discovery_templates import RECEPTOR_PDB
                    receptor_lower = context['receptor'].lower().replace('-', '').replace('_', '')
                    if receptor_lower in RECEPTOR_PDB:
                        context['pdb_id'] = RECEPTOR_PDB[receptor_lower]
                        logger.info(f"Automatic PDB lookup: {context['receptor']} → {context['pdb_id']}")
                except (ImportError, KeyError):
                    pass  # No automatic lookup available

            result.bio_interpretation = interpret_bio_results(result.counts, context)

            # Copy bio_interpretation values as direct attributes for easier access
            if isinstance(result.bio_interpretation, dict) and 'status' not in result.bio_interpretation:
                # For drug design (de novo generation)
                if result.bio_interpretation.get('designed_molecules'):
                    result.designed_molecules = result.bio_interpretation.get('designed_molecules')
                    result.best_molecule = result.bio_interpretation.get('best_molecule')
                    result.binding_affinity = result.bio_interpretation.get('binding_affinity')
                    result.ki = result.bio_interpretation.get('ki')
                    result.ic50 = result.bio_interpretation.get('ic50')
                    result.all_candidates = result.bio_interpretation.get('all_candidates')

                # For drug docking
                elif result.bio_interpretation.get('application') == 'drug_docking':
                    result.binding_affinity = result.bio_interpretation.get('binding_affinity_kcal_mol')
                    result.ki = result.bio_interpretation.get('ki_nanomolar')
                    result.ic50 = result.bio_interpretation.get('ic50_nanomolar')
                    result.num_poses = result.bio_interpretation.get('poses_explored')
                    result.interactions = []

                    # Extract interaction details
                    mol_int = result.bio_interpretation.get('molecular_interactions', {})
                    if mol_int.get('hydrogen_bonds', 0) > 0:
                        result.interactions.append(f"H-bonds: {mol_int['hydrogen_bonds']}")
                    if mol_int.get('hydrophobic_contacts', 0) > 0:
                        result.interactions.append(f"Hydrophobic: {mol_int['hydrophobic_contacts']}")
                    if mol_int.get('pi_stacking', 0) > 0:
                        result.interactions.append(f"π-stacking: {mol_int['pi_stacking']}")
                    if mol_int.get('salt_bridges', 0) > 0:
                        result.interactions.append(f"Salt bridges: {mol_int['salt_bridges']}")

                    # Pharmaceutical scores
                    pharma = result.bio_interpretation.get('pharmaceutical_scores')
                    if pharma:
                        result.lipinski_compliant = pharma.get('lipinski_compliant')
                        result.lipinski_violations = pharma.get('lipinski_violations')
                        result.qed_score = pharma.get('qed_score')
                        result.qed_rating = pharma.get('qed_rating')
                        result.sa_score = pharma.get('sa_score')
                        result.sa_rating = pharma.get('sa_rating')
                        result.pains_alerts = pharma.get('pains_alerts')
                        result.pharmaceutical_viability = pharma.get('pharmaceutical_viability')

        except ImportError as e:
            import traceback
            tb_str = traceback.format_exc()
            logger.error(f"Bio interpreter import failed: {e}")
            logger.error(f"Traceback: {tb_str}")
            result.bio_interpretation = {
                'status': 'error',
                'message': f'Bio interpreter import failed: {str(e)}',
                'traceback': tb_str
            }
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            logger.error(f"❌ Bio interpretation failed: {e}")
            logger.error(f"Traceback:\n{tb_str}")
            result.bio_interpretation = {
                'status': 'error',
                'message': f'Bio interpretation failed: {str(e)}',
                'traceback': tb_str
            }
            # Re-raise in development to see full error
            if logger.level <= 10:  # DEBUG level
                raise

        if debug:
            logger.debug(f"Execution completed successfully")
            logger.debug(f"Results: {result.counts}")
            logger.debug(f"Metadata: {result.metadata}")

        # Log usage for billing if enabled
        # MANDATORY: Record usage for billing (always enabled)
        try:
            execution_time = result.metadata.get('execution_time', 0) if result.metadata else 0
            actual_shots = getattr(result, 'total_shots', shots)

            # Record usage with cloud service
            record_usage(
                api_key=api_key,
                shots_executed=actual_shots,
                backend=actual_backend,
                cost=estimated_cost,
                success=getattr(result, 'success', True)
            )

            # Add cost info to result
            if hasattr(result, 'metadata'):
                result.metadata['cost_estimate'] = estimated_cost
                result.metadata['billing_status'] = 'recorded'
            else:
                result.metadata = {
                    'cost_estimate': estimated_cost,
                    'billing_status': 'recorded'
                }

            result.cost_estimate = estimated_cost
            logger.info(f"💰 Usage recorded: {actual_shots} shots, ${estimated_cost:.4f}")

        except Exception as e:
            logger.warning(f"⚠️  Usage recording failed: {e}")
            # Don't fail the execution, but warn user
            if hasattr(result, 'metadata'):
                result.metadata['billing_status'] = 'failed'

        # Clean up IBM backend connection
        if isinstance(quantum_backend, IBMQuantumBackend):
            quantum_backend.close()

        return result

    except Exception as e:
        logger.error(f"Quantum execution failed: {str(e)}")

        # Record failed usage (only if we got past authentication)
        if 'api_key' in locals() and api_key:
            try:
                record_usage(
                    api_key=api_key,
                    shots_executed=0,  # No shots executed on failure
                    backend=backend,
                    cost=0.0,  # No cost for failed executions
                    success=False
                )
                logger.info(f"🚫 Failed execution recorded for billing")
            except Exception as billing_error:
                logger.warning(f"⚠️  Failed to record failed usage: {billing_error}")

        return QuantumResult(
            success=False,
            error_message=str(e),
            metadata={
                'original_program': program,
                'backend_requested': backend,
                'backend_used': actual_backend if 'actual_backend' in locals() else backend
            }
        )


def list_available_backends(token: Optional[str] = None,
                           instance: Optional[str] = None) -> Dict[str, Any]:
    """
    List all available quantum backends and their status.

    Args:
        token: IBM Quantum API token
        instance: IBM Quantum instance

    Returns:
        Dictionary with backend information
    """
    backends_info = {
        'simulators': {},
        'ibm_hardware': {},
        'ionq_hardware': {},
        'status': 'success',
        'error': None
    }

    # Add simulator backends
    backends_info['simulators']['aer_simulator'] = {
        'qubits': 'unlimited',
        'cost_per_shot': 0.0,
        'queue_length': 0,
        'operational': True,
        'description': 'Local Qiskit Aer simulator'
    }

    # Add known IonQ backends
    for backend_name, info in IonQBackend.KNOWN_BACKENDS.items():
        if 'simulator' in backend_name:
            backends_info['simulators'][backend_name] = {
                'qubits': info['qubits'],
                'cost_per_shot': IonQBackend.COST_PER_SHOT.get(backend_name, 0.0),
                'queue_length': 0,
                'operational': True,
                'description': 'IonQ cloud simulator'
            }
        else:
            backends_info['ionq_hardware'][backend_name] = {
                'qubits': info['qubits'],
                'cost_per_shot': IonQBackend.COST_PER_SHOT.get(backend_name, 0.01),
                'queue_length': 'N/A',
                'operational': 'N/A',
                'description': 'IonQ quantum computer'
            }

    # Add known IBM backends
    for backend_name, info in IBMQuantumBackend.KNOWN_BACKENDS.items():
        if 'simulator' in backend_name:
            backends_info['simulators'][backend_name] = {
                'qubits': info['qubits'],
                'cost_per_shot': IBMQuantumBackend.COST_PER_SHOT.get(backend_name, 0.0),
                'queue_length': 'N/A',
                'operational': 'N/A',
                'description': 'IBM Quantum simulator'
            }
        else:
            backends_info['ibm_hardware'][backend_name] = {
                'qubits': info['qubits'],
                'cost_per_shot': IBMQuantumBackend.COST_PER_SHOT.get(backend_name, 0.001),
                'queue_length': 'Unknown',
                'operational': 'Unknown',
                'description': 'IBM Quantum hardware'
            }

    # Try to get real-time status if token is provided
    if token and IBM_QUANTUM_AVAILABLE:
        try:
            service = QiskitRuntimeService(
                token=token,
                instance=instance
            ) if instance else QiskitRuntimeService(token=token)

            live_backends = service.backends()
            for backend in live_backends:
                config = backend.configuration()
                status = backend.status()

                backend_info = {
                    'qubits': config.n_qubits,
                    'cost_per_shot': IBMQuantumBackend.COST_PER_SHOT.get(backend.name, 0.001),
                    'queue_length': status.pending_jobs,
                    'operational': status.operational,
                    'description': getattr(config, 'description', 'IBM Quantum hardware')
                }

                if 'simulator' in backend.name:
                    backends_info['simulators'][backend.name] = backend_info
                else:
                    backends_info['ibm_hardware'][backend.name] = backend_info

        except Exception as e:
            backends_info['error'] = f"Could not get live backend status: {str(e)}"
            backends_info['status'] = 'partial'

    return backends_info


def estimate_job_cost(circuit: QuantumCircuit, backend: str, shots: int = 1024) -> Dict[str, Any]:
    """
    Estimate the cost and time for running a circuit.

    Args:
        circuit: The quantum circuit to analyze
        backend: Target backend name
        shots: Number of shots

    Returns:
        Dictionary with cost and time estimates
    """
    cost_info = {
        'backend': backend,
        'shots': shots,
        'cost_usd': 0.0,
        'time_estimate_minutes': 0,
        'warnings': [],
        'recommendations': []
    }

    # Calculate cost
    if backend in IBMQuantumBackend.COST_PER_SHOT:
        cost_info['cost_usd'] = IBMQuantumBackend.COST_PER_SHOT[backend] * shots
    elif backend.startswith('ibm_'):
        cost_info['cost_usd'] = 0.001 * shots  # Default estimate
    else:
        cost_info['cost_usd'] = 0.0  # Simulators are free

    # Estimate time
    if 'simulator' in backend.lower():
        cost_info['time_estimate_minutes'] = max(1, circuit.depth() // 100)  # Very rough estimate
    else:
        # For real hardware, factor in queue time
        cost_info['time_estimate_minutes'] = 5 + (circuit.depth() // 50)  # Basic estimate

    # Add warnings and recommendations
    if circuit.num_qubits > 50:
        cost_info['warnings'].append(f"Large circuit ({circuit.num_qubits} qubits) will be expensive")

    if circuit.depth() > 200:
        cost_info['warnings'].append(f"Deep circuit ({circuit.depth()} depth) may have low fidelity on hardware")
        cost_info['recommendations'].append("Consider circuit optimization or use simulator for testing")

    if cost_info['cost_usd'] > 10.0:
        cost_info['warnings'].append(f"High cost estimate: ${cost_info['cost_usd']:.2f}")
        cost_info['recommendations'].append("Consider reducing shots or using a simulator")

    return cost_info


def main():
    """Command-line interface for the quantum connector."""
    import argparse

    parser = argparse.ArgumentParser(
        description='BioQL Quantum Connector with IBM Quantum Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on local simulator
  bioql-quantum "Create Bell state" --backend simulator

  # Run on IBM Eagle hardware
  bioql-quantum "Create Bell state" --backend ibm_eagle --token YOUR_TOKEN

  # Auto-select best backend
  bioql-quantum "3-qubit GHZ state" --backend auto --token YOUR_TOKEN

  # List available backends
  bioql-quantum --list-backends --token YOUR_TOKEN

  # Estimate cost
  bioql-quantum "Random circuit" --estimate-cost --backend ibm_brisbane
        """
    )

    # Main arguments
    parser.add_argument('program', nargs='?', help='BioQL program to execute')
    parser.add_argument('--backend', default='simulator',
                       help='Quantum backend (simulator, ibm_eagle, auto, etc.)')
    parser.add_argument('--shots', type=int, default=1024, help='Number of shots')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    # IBM Quantum arguments
    parser.add_argument('--token', help='IBM Quantum API token')
    parser.add_argument('--instance', help='IBM Quantum instance (hub/group/project)')
    parser.add_argument('--timeout', type=int, default=3600,
                       help='Job timeout in seconds')
    parser.add_argument('--auto-select', action='store_true',
                       help='Automatically select best backend')

    # Utility arguments
    parser.add_argument('--list-backends', action='store_true',
                       help='List available backends and exit')
    parser.add_argument('--estimate-cost', action='store_true',
                       help='Estimate cost without running')

    args = parser.parse_args()

    # Handle utility commands
    if args.list_backends:
        backends = list_available_backends(args.token, args.instance)
        print("\n=== Available Quantum Backends ===")

        print("\n--- Simulators ---")
        for name, info in backends['simulators'].items():
            status = "✓" if info['operational'] else "✗"
            print(f"{status} {name:20} | {info['qubits']:>6} qubits | ${info['cost_per_shot']:.4f}/shot")

        print("\n--- IBM Hardware ---")
        for name, info in backends['ibm_hardware'].items():
            status = "✓" if info['operational'] else "?"
            queue = f"{info['queue_length']} jobs" if isinstance(info['queue_length'], int) else info['queue_length']
            print(f"{status} {name:20} | {info['qubits']:>6} qubits | ${info['cost_per_shot']:.4f}/shot | Queue: {queue}")

        if backends['error']:
            print(f"\nNote: {backends['error']}")

        return

    # Require program for other operations
    if not args.program:
        parser.error("Program is required unless using --list-backends")

    if args.estimate_cost:
        # Parse program and estimate cost
        circuit = parse_bioql_program(args.program)
        estimate = estimate_job_cost(circuit, args.backend, args.shots)

        print(f"\n=== Cost Estimate ===")
        print(f"Backend: {estimate['backend']}")
        print(f"Circuit: {circuit.num_qubits} qubits, {circuit.depth()} depth")
        print(f"Shots: {estimate['shots']}")
        print(f"Estimated cost: ${estimate['cost_usd']:.4f}")
        print(f"Estimated time: {estimate['time_estimate_minutes']} minutes")

        if estimate['warnings']:
            print("\nWarnings:")
            for warning in estimate['warnings']:
                print(f"  ⚠ {warning}")

        if estimate['recommendations']:
            print("\nRecommendations:")
            for rec in estimate['recommendations']:
                print(f"  💡 {rec}")

        return

    # Execute the quantum program
    result = quantum(
        args.program,
        backend=args.backend,
        shots=args.shots,
        debug=args.debug,
        token=args.token,
        instance=args.instance,
        timeout=args.timeout,
        auto_select=args.auto_select
    )

    # Display results
    print(f"\n=== Quantum Execution Results ===")
    if result.success:
        print(f"✓ Execution successful!")
        print(f"Backend: {result.metadata.get('backend_used', args.backend)}")

        if result.job_id:
            print(f"Job ID: {result.job_id}")

        if result.execution_time:
            print(f"Execution time: {result.execution_time:.1f}s")

        if result.cost_estimate:
            print(f"Cost: ${result.cost_estimate:.4f}")

        print(f"\nResults:")
        print(f"Total shots: {result.total_shots}")
        print(f"Most likely outcome: {result.most_likely_outcome}")

        print(f"\nCounts:")
        for outcome, count in sorted(result.counts.items()):
            probability = count / result.total_shots
            print(f"  {outcome}: {count:4d} ({probability:.3f})")

        if args.debug and result.metadata:
            print(f"\nMetadata: {result.metadata}")

    else:
        print(f"✗ Execution failed: {result.error_message}")

        if result.metadata.get('backend_used'):
            print(f"Backend: {result.metadata['backend_used']}")

        return 1

    return 0


# Billing-aware quantum function factory
def get_quantum_function(billing_enabled: bool = None) -> Callable:
    """
    Get quantum function with optional billing integration.

    This factory function returns either the original quantum() function
    or a billing-enabled version depending on configuration.

    Args:
        billing_enabled: Override billing configuration (optional)

    Returns:
        Quantum function (with or without billing)

    Examples:
        >>> # Get standard quantum function
        >>> quantum_func = get_quantum_function(billing_enabled=False)
        >>> result = quantum_func("Create Bell state")
        >>>
        >>> # Get billing-enabled quantum function
        >>> quantum_with_billing = get_quantum_function(billing_enabled=True)
        >>> result = quantum_with_billing("Create Bell state", api_key="your_key")
        >>> print(result.billing_metadata)
    """
    # Determine if billing should be enabled
    use_billing = billing_enabled
    if use_billing is None:
        use_billing = BILLING_ENABLED and BILLING_INTEGRATION_AVAILABLE

    if use_billing and BILLING_INTEGRATION_AVAILABLE:
        logger.info("Creating billing-enabled quantum function")
        return create_billing_quantum_function()
    else:
        logger.info("Using standard quantum function (billing disabled)")
        return quantum


# Convenience function that automatically detects billing availability
def quantum_auto(*args, **kwargs):
    """
    Quantum function that automatically uses billing if available.

    This function automatically detects if billing integration is available
    and uses it if configured. Falls back to standard quantum() if not.

    Usage is identical to quantum() but with optional billing parameters:
    - api_key: BioQL API key for user authentication
    - user_id: Direct user ID (for internal use)
    - session_id: Session ID for grouping operations
    """
    if BILLING_ENABLED and BILLING_INTEGRATION_AVAILABLE:
        # Extract billing parameters
        billing_params = {}
        for param in ['api_key', 'user_id', 'session_id', 'client_ip', 'user_agent']:
            if param in kwargs:
                billing_params[param] = kwargs.pop(param)

        # Use billing-enabled function
        billing_quantum = create_billing_quantum_function()
        return billing_quantum(*args, **kwargs, **billing_params)
    else:
        # Remove billing parameters and use standard function
        for param in ['api_key', 'user_id', 'session_id', 'client_ip', 'user_agent']:
            kwargs.pop(param, None)

        result = quantum(*args, **kwargs)

        # Add empty billing metadata for consistency
        if hasattr(result, 'billing_metadata'):
            result.billing_metadata = {
                'billing_enabled': False,
                'reason': 'Billing integration not available or disabled'
            }

        return result


# Module-level utilities
def enable_billing() -> Dict[str, Any]:
    """
    Enable billing integration for this module.

    Returns:
        Dictionary with enablement status
    """
    global BILLING_ENABLED

    if not BILLING_INTEGRATION_AVAILABLE:
        return {
            'success': False,
            'error': 'Billing integration not available. Check billing_integration module.'
        }

    BILLING_ENABLED = True
    return {
        'success': True,
        'message': 'Billing integration enabled for quantum_connector module'
    }


def disable_billing() -> Dict[str, Any]:
    """
    Disable billing integration for this module.

    Returns:
        Dictionary with disablement status
    """
    global BILLING_ENABLED
    BILLING_ENABLED = False
    return {
        'success': True,
        'message': 'Billing integration disabled for quantum_connector module'
    }


def get_integration_status() -> Dict[str, Any]:
    """
    Get status of billing integration.

    Returns:
        Dictionary with integration status information
    """
    status = {
        'billing_integration_available': BILLING_INTEGRATION_AVAILABLE,
        'billing_enabled': BILLING_ENABLED,
        'quantum_connector_version': '2.0.0-billing'
    }

    if BILLING_INTEGRATION_AVAILABLE:
        status['billing_system_status'] = get_billing_status()

    return status


if __name__ == '__main__':
    main()