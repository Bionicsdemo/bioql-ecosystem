"""
Variational Quantum Eigensolver (VQE) Circuit Implementation

This module provides a pre-built implementation of the VQE algorithm for
finding ground state energies of quantum systems, with applications in
molecular chemistry and materials science.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library import TwoLocal, RealAmplitudes, EfficientSU2
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from scipy.optimize import minimize

from ..templates.base import CircuitTemplate, CircuitBackend


@dataclass
class VQEResult:
    """Result from VQE optimization."""

    success: bool
    optimal_energy: float
    optimal_parameters: List[float]
    iterations: int
    function_evaluations: int
    convergence_history: List[float]
    final_counts: Dict[str, int]
    metadata: Optional[Dict] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'optimal_energy': self.optimal_energy,
            'optimal_parameters': self.optimal_parameters,
            'iterations': self.iterations,
            'function_evaluations': self.function_evaluations,
            'convergence_history': self.convergence_history,
            'final_counts': self.final_counts,
            'metadata': self.metadata,
            'error_message': self.error_message
        }


class VQECircuit(CircuitTemplate):
    """
    Variational Quantum Eigensolver (VQE) Circuit.

    Implements the VQE algorithm for finding ground state energies of
    quantum Hamiltonians. VQE is a hybrid quantum-classical algorithm
    that uses a parameterized quantum circuit (ansatz) and classical
    optimization to minimize the expectation value of a Hamiltonian.

    Applications:
    - Molecular chemistry: Finding ground state energies
    - Materials science: Electronic structure calculations
    - Quantum simulation: Many-body systems

    Attributes:
        hamiltonian: Quantum Hamiltonian as SparsePauliOp or string
        ansatz: Variational ansatz circuit type
        optimizer: Classical optimizer for parameter optimization
        num_qubits: Number of qubits (inferred from Hamiltonian)

    Example:
        >>> # Simple 2-qubit Hamiltonian: H = Z0 + Z1 + 0.5*Z0Z1
        >>> hamiltonian = SparsePauliOp(['ZI', 'IZ', 'ZZ'], coeffs=[1.0, 1.0, 0.5])
        >>> vqe = VQECircuit(hamiltonian=hamiltonian, ansatz='RealAmplitudes')
        >>> result = vqe.optimize(shots=1024)
        >>> print(f"Ground state energy: {result.optimal_energy}")
        Ground state energy: -2.5
        >>>
        >>> # H2 molecule example
        >>> h2_hamiltonian = SparsePauliOp.from_list([
        ...     ('II', -1.0523),
        ...     ('ZI', 0.3979),
        ...     ('IZ', -0.3979),
        ...     ('ZZ', -0.0112),
        ...     ('XX', 0.1809)
        ... ])
        >>> vqe = VQECircuit(hamiltonian=h2_hamiltonian)
        >>> result = vqe.optimize()
    """

    def __init__(
        self,
        hamiltonian: Union[SparsePauliOp, str, List[Tuple[str, float]]],
        ansatz: str = 'RealAmplitudes',
        optimizer: str = 'COBYLA',
        num_layers: int = 2,
        backend: CircuitBackend = CircuitBackend.SIMULATOR
    ):
        """
        Initialize VQE circuit.

        Args:
            hamiltonian: Quantum Hamiltonian (SparsePauliOp, Pauli string, or list)
            ansatz: Ansatz type ('RealAmplitudes', 'EfficientSU2', 'TwoLocal')
            optimizer: Classical optimizer ('COBYLA', 'SLSQP', 'Powell', 'Nelder-Mead')
            num_layers: Number of ansatz layers (depth)
            backend: Quantum backend

        Raises:
            ValueError: If invalid parameters provided

        Example:
            >>> hamiltonian = SparsePauliOp(['ZZ', 'XX'], coeffs=[1.0, 0.5])
            >>> vqe = VQECircuit(hamiltonian, ansatz='EfficientSU2', num_layers=3)
        """
        # Parse Hamiltonian
        self.hamiltonian = self._parse_hamiltonian(hamiltonian)
        self.num_qubits = self.hamiltonian.num_qubits

        if self.num_qubits < 1:
            raise ValueError("Hamiltonian must have at least 1 qubit")

        self.ansatz_type = ansatz
        self.optimizer_type = optimizer
        self.num_layers = num_layers

        # Optimization tracking
        self._energy_history: List[float] = []
        self._iteration_count = 0
        self._function_evals = 0

        super().__init__(
            name=f"VQE ({self.num_qubits} qubits, {ansatz})",
            description=f"VQE with {ansatz} ansatz for {self.num_qubits}-qubit Hamiltonian",
            num_qubits=self.num_qubits,
            backend=backend
        )

        logger.info(
            f"Initialized VQE: {self.num_qubits} qubits, "
            f"{ansatz} ansatz, {num_layers} layers"
        )

    def _parse_hamiltonian(
        self,
        hamiltonian: Union[SparsePauliOp, str, List[Tuple[str, float]]]
    ) -> SparsePauliOp:
        """Parse various Hamiltonian formats to SparsePauliOp."""
        if isinstance(hamiltonian, SparsePauliOp):
            return hamiltonian
        elif isinstance(hamiltonian, str):
            # Single Pauli string
            return SparsePauliOp([hamiltonian], coeffs=[1.0])
        elif isinstance(hamiltonian, list):
            # List of (pauli_string, coefficient) tuples
            paulis = [p[0] for p in hamiltonian]
            coeffs = [p[1] for p in hamiltonian]
            return SparsePauliOp(paulis, coeffs=coeffs)
        else:
            raise ValueError(f"Unsupported Hamiltonian type: {type(hamiltonian)}")

    def build_circuit(self) -> QuantumCircuit:
        """
        Build the VQE circuit with current parameters.

        Note: For VQE, we build a parameterized circuit.
        Use build_ansatz() to get the circuit with specific parameters.

        Returns:
            QuantumCircuit: Parameterized ansatz circuit
        """
        return self.build_ansatz()

    def build_ansatz(
        self,
        parameters: Optional[List[float]] = None
    ) -> QuantumCircuit:
        """
        Build the variational ansatz circuit.

        Creates a parameterized quantum circuit based on the specified
        ansatz type (RealAmplitudes, EfficientSU2, or TwoLocal).

        Args:
            parameters: Parameter values (uses symbolic parameters if None)

        Returns:
            QuantumCircuit: Ansatz circuit

        Example:
            >>> vqe = VQECircuit(hamiltonian='ZZ', ansatz='RealAmplitudes')
            >>> circuit = vqe.build_ansatz([0.5, 1.0, 0.3, 0.7])
            >>> print(circuit)
        """
        if self.ansatz_type == 'RealAmplitudes':
            ansatz = RealAmplitudes(
                num_qubits=self.num_qubits,
                reps=self.num_layers,
                insert_barriers=False
            )
        elif self.ansatz_type == 'EfficientSU2':
            ansatz = EfficientSU2(
                num_qubits=self.num_qubits,
                reps=self.num_layers,
                insert_barriers=False
            )
        elif self.ansatz_type == 'TwoLocal':
            ansatz = TwoLocal(
                num_qubits=self.num_qubits,
                rotation_blocks=['ry', 'rz'],
                entanglement_blocks='cx',
                entanglement='linear',
                reps=self.num_layers,
                insert_barriers=False
            )
        else:
            raise ValueError(f"Unknown ansatz type: {self.ansatz_type}")

        # Bind parameters if provided
        if parameters is not None:
            if len(parameters) != ansatz.num_parameters:
                raise ValueError(
                    f"Expected {ansatz.num_parameters} parameters, "
                    f"got {len(parameters)}"
                )
            param_dict = dict(zip(ansatz.parameters, parameters))
            ansatz = ansatz.bind_parameters(param_dict)

        return ansatz

    def measure_energy(
        self,
        parameters: List[float],
        shots: int = 1024
    ) -> float:
        """
        Measure the expectation value of the Hamiltonian.

        Executes the parameterized circuit and computes ⟨ψ(θ)|H|ψ(θ)⟩
        where θ are the variational parameters.

        Args:
            parameters: Variational parameters
            shots: Number of measurement shots

        Returns:
            float: Energy expectation value

        Example:
            >>> vqe = VQECircuit(hamiltonian='ZZ')
            >>> energy = vqe.measure_energy([0.5, 1.0, 0.3, 0.7], shots=2048)
            >>> print(f"Energy: {energy}")
        """
        self._function_evals += 1

        try:
            # Build circuit with parameters
            circuit = self.build_ansatz(parameters)

            # Compute expectation value for each Pauli term
            total_energy = 0.0

            for pauli_string, coeff in zip(
                self.hamiltonian.paulis,
                self.hamiltonian.coeffs
            ):
                # Create measurement circuit for this Pauli term
                meas_circuit = circuit.copy()
                meas_circuit = self._add_pauli_measurement(meas_circuit, str(pauli_string))

                # Execute circuit
                simulator = AerSimulator()
                pass_manager = generate_preset_pass_manager(1, simulator)
                transpiled = pass_manager.run(meas_circuit)
                job = simulator.run(transpiled, shots=shots)
                result = job.result()
                counts = result.get_counts()

                # Calculate expectation value
                expectation = self._calculate_expectation(counts, shots)
                total_energy += float(coeff) * expectation

            # Track energy history
            self._energy_history.append(total_energy)

            logger.debug(f"Energy evaluation {self._function_evals}: {total_energy:.6f}")

            return total_energy

        except Exception as e:
            logger.error(f"Energy measurement failed: {e}")
            return float('inf')

    def _add_pauli_measurement(
        self,
        circuit: QuantumCircuit,
        pauli_string: str
    ) -> QuantumCircuit:
        """Add measurement basis rotation for Pauli string."""
        meas_circuit = circuit.copy()

        # Add basis rotation and measurement
        for i, pauli in enumerate(reversed(pauli_string)):
            if pauli == 'X':
                meas_circuit.h(i)
            elif pauli == 'Y':
                meas_circuit.sdg(i)
                meas_circuit.h(i)
            # Z basis is computational basis (no rotation needed)

        meas_circuit.measure_all()
        return meas_circuit

    def _calculate_expectation(
        self,
        counts: Dict[str, int],
        shots: int
    ) -> float:
        """Calculate expectation value from measurement counts."""
        expectation = 0.0

        for bitstring, count in counts.items():
            # Calculate parity (number of 1s)
            parity = bitstring.count('1') % 2
            sign = 1 if parity == 0 else -1
            expectation += sign * count / shots

        return expectation

    def optimize(
        self,
        initial_parameters: Optional[List[float]] = None,
        shots: int = 1024,
        maxiter: int = 100
    ) -> VQEResult:
        """
        Run VQE optimization to find ground state energy.

        Uses classical optimization to minimize the energy expectation
        value by adjusting variational parameters.

        Args:
            initial_parameters: Starting parameters (random if None)
            shots: Shots per energy evaluation
            maxiter: Maximum optimization iterations

        Returns:
            VQEResult: Optimization results

        Example:
            >>> vqe = VQECircuit(hamiltonian='ZZ')
            >>> result = vqe.optimize(shots=2048, maxiter=50)
            >>> print(f"Ground state: {result.optimal_energy:.6f}")
            >>> print(f"Converged in {result.iterations} iterations")
        """
        import time
        start_time = time.time()

        # Reset tracking
        self._energy_history = []
        self._iteration_count = 0
        self._function_evals = 0

        try:
            # Get number of parameters
            temp_circuit = self.build_ansatz()
            num_params = temp_circuit.num_parameters

            # Initialize parameters
            if initial_parameters is None:
                initial_parameters = np.random.uniform(
                    0, 2 * np.pi, num_params
                ).tolist()
            elif len(initial_parameters) != num_params:
                raise ValueError(
                    f"Expected {num_params} parameters, "
                    f"got {len(initial_parameters)}"
                )

            logger.info(f"Starting VQE optimization with {num_params} parameters")

            # Define objective function
            def objective(params):
                self._iteration_count += 1
                energy = self.measure_energy(params.tolist(), shots=shots)
                logger.info(
                    f"Iteration {self._iteration_count}: "
                    f"Energy = {energy:.6f}"
                )
                return energy

            # Run optimization
            result = minimize(
                objective,
                x0=np.array(initial_parameters),
                method=self.optimizer_type,
                options={'maxiter': maxiter}
            )

            # Get final counts for analysis
            final_circuit = self.build_ansatz(result.x.tolist())
            final_circuit.measure_all()

            simulator = AerSimulator()
            pass_manager = generate_preset_pass_manager(1, simulator)
            transpiled = pass_manager.run(final_circuit)
            job = simulator.run(transpiled, shots=shots)
            final_counts = job.result().get_counts()

            execution_time = time.time() - start_time

            logger.success(
                f"VQE optimization complete: "
                f"Energy = {result.fun:.6f}, "
                f"Iterations = {self._iteration_count}, "
                f"Time = {execution_time:.2f}s"
            )

            return VQEResult(
                success=result.success,
                optimal_energy=float(result.fun),
                optimal_parameters=result.x.tolist(),
                iterations=self._iteration_count,
                function_evaluations=self._function_evals,
                convergence_history=self._energy_history,
                final_counts=final_counts,
                metadata={
                    'ansatz': self.ansatz_type,
                    'optimizer': self.optimizer_type,
                    'num_layers': self.num_layers,
                    'num_parameters': num_params,
                    'execution_time_s': execution_time,
                    'shots_per_eval': shots
                }
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"VQE optimization failed: {e}")

            return VQEResult(
                success=False,
                optimal_energy=float('inf'),
                optimal_parameters=[],
                iterations=self._iteration_count,
                function_evaluations=self._function_evals,
                convergence_history=self._energy_history,
                final_counts={},
                metadata={'execution_time_s': execution_time},
                error_message=str(e)
            )

    def get_exact_ground_state_energy(self) -> float:
        """
        Calculate exact ground state energy (for comparison).

        Uses classical eigenvalue decomposition. Only practical for
        small systems (≤12 qubits).

        Returns:
            float: Exact ground state energy

        Example:
            >>> vqe = VQECircuit(hamiltonian='ZZ')
            >>> exact = vqe.get_exact_ground_state_energy()
            >>> vqe_result = vqe.optimize()
            >>> error = abs(vqe_result.optimal_energy - exact)
            >>> print(f"VQE error: {error:.6f}")
        """
        if self.num_qubits > 12:
            logger.warning(
                f"Computing exact ground state for {self.num_qubits} "
                f"qubits may be slow"
            )

        # Convert to matrix and find minimum eigenvalue
        matrix = self.hamiltonian.to_matrix()
        eigenvalues = np.linalg.eigvalsh(matrix)
        return float(min(eigenvalues))


__all__ = ['VQECircuit', 'VQEResult']
