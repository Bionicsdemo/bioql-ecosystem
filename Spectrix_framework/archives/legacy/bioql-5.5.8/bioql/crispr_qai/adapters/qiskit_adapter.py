"""
IBM Qiskit adapter for CRISPR-QAI energy estimation

Supports:
- Qiskit Aer (local simulator)
- IBM Quantum hardware (via IBM Runtime)
- Custom noise models

Requires:
- qiskit >= 1.0
- qiskit-ibm-runtime (for real hardware)
"""

import time
from typing import Dict, List, Any, Optional
import numpy as np

from .base import QuantumEngine

try:
    from qiskit import QuantumCircuit
    from qiskit_aer import Aer
    HAVE_QISKIT = True
except ImportError:
    HAVE_QISKIT = False

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
    HAVE_IBM_RUNTIME = True
except ImportError:
    HAVE_IBM_RUNTIME = False


class QiskitEngine(QuantumEngine):
    """
    IBM Qiskit quantum backend for CRISPR energy estimation
    """

    def __init__(
        self,
        backend_name: str = "aer_simulator",
        shots: int = 1000,
        ibm_token: Optional[str] = None
    ):
        """
        Initialize Qiskit backend

        Args:
            backend_name: Qiskit backend ('aer_simulator', 'ibm_torino', etc.)
            shots: Number of measurements
            ibm_token: IBM Quantum token (required for hardware)
        """
        if not HAVE_QISKIT:
            raise ImportError(
                "Qiskit not installed. "
                "Install with: pip install qiskit qiskit-aer"
            )

        super().__init__(backend_name=backend_name, shots=shots)
        self.ibm_token = ibm_token
        self.backend = None
        self.service = None

    def run_energy_estimation(
        self,
        angles: List[float],
        coupling_strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run energy estimation on Qiskit backend

        Args:
            angles: Rotation angles encoding gRNA
            coupling_strength: Qubit coupling strength
            metadata: Guide metadata

        Returns:
            Energy estimation results
        """
        start_time = time.time()

        # Validate
        self._validate_angles(angles)
        if not self.validated:
            self.validate_backend()

        num_qubits = len(angles)

        # Build quantum circuit
        circuit = self._build_circuit(angles, coupling_strength)

        # Execute
        if self.backend_name == "aer_simulator":
            counts = self._run_aer(circuit)
        else:
            counts = self._run_ibm_runtime(circuit)

        # Calculate energy
        energy_estimate = self._calculate_energy_from_counts(
            counts, angles, coupling_strength
        )

        confidence = self._calculate_confidence(counts)

        runtime = time.time() - start_time

        return {
            'energy_estimate': float(energy_estimate),
            'confidence': float(confidence),
            'runtime_seconds': runtime,
            'backend': self.backend_name,
            'shots': self.shots,
            'num_qubits': num_qubits,
            'metadata': metadata or {}
        }

    def validate_backend(self) -> bool:
        """
        Validate Qiskit backend

        Returns:
            True if backend is available
        """
        try:
            if self.backend_name == "aer_simulator":
                # Local simulator
                self.backend = Aer.get_backend('aer_simulator')
                self.validated = True
                return True

            else:
                # IBM Quantum hardware
                if not HAVE_IBM_RUNTIME:
                    raise ImportError(
                        "IBM Runtime not installed. "
                        "Install with: pip install qiskit-ibm-runtime"
                    )

                # Load IBM token from BioQL's internal config (SERVER SIDE)
                if not self.ibm_token:
                    from ...quantum_connector import _load_ibm_token_from_config
                    self.ibm_token = _load_ibm_token_from_config()

                if not self.ibm_token:
                    raise ValueError(
                        "IBM Quantum token not found. BioQL needs IBM credentials configured. "
                        "Contact BioQL support or configure with: bioql config"
                    )

                self.service = QiskitRuntimeService(
                    channel="ibm_quantum_platform",
                    token=self.ibm_token
                )
                self.backend = self.service.backend(self.backend_name)
                self.validated = True
                return True

        except Exception as e:
            print(f"Qiskit validation failed: {e}")
            self.validated = False
            return False

    def _build_circuit(
        self,
        angles: List[float],
        coupling_strength: float
    ) -> QuantumCircuit:
        """
        Build Qiskit quantum circuit for energy estimation

        Args:
            angles: Rotation angles
            coupling_strength: Coupling strength

        Returns:
            QuantumCircuit
        """
        num_qubits = len(angles)
        circuit = QuantumCircuit(num_qubits)

        # Apply rotations encoding gRNA sequence
        for i, angle in enumerate(angles):
            circuit.ry(angle, i)

        # Apply ZZ couplings for base-pair interactions
        for i in range(num_qubits - 1):
            theta = coupling_strength * np.pi / 4
            circuit.rzz(2 * theta, i, i+1)

        # Measure all qubits (creates 'meas' classical register automatically)
        circuit.measure_all()

        return circuit

    def _run_aer(self, circuit: QuantumCircuit) -> Dict[str, int]:
        """
        Run circuit on Aer simulator

        Args:
            circuit: Quantum circuit

        Returns:
            Measurement counts
        """
        from qiskit import transpile

        transpiled = transpile(circuit, self.backend)
        job = self.backend.run(transpiled, shots=self.shots)
        result = job.result()
        counts = result.get_counts()

        return counts

    def _run_ibm_runtime(self, circuit: QuantumCircuit) -> Dict[str, int]:
        """
        Run circuit on IBM Quantum hardware via Runtime

        Args:
            circuit: Quantum circuit

        Returns:
            Measurement counts
        """
        # ✅ qiskit-ibm-runtime 0.42.0: Use mode= instead of backend=
        from qiskit import transpile

        # Transpile circuit to backend's basis gates (REQUIRED for real hardware)
        transpiled_circuit = transpile(circuit, backend=self.backend, optimization_level=3)

        sampler = Sampler(mode=self.backend)
        job = sampler.run([transpiled_circuit], shots=self.shots)
        result = job.result()

        # Extract counts from runtime result (qiskit-ibm-runtime 0.42.0 API)
        # Result format: PrimitiveResult with pub_results[0].data containing BitArray
        pub_result = result[0]  # First pub_result

        # Access the classical register data (measure_all() creates 'meas' register)
        # The data is a BitArray object
        bit_array = pub_result.data.meas  # Classical register 'meas'

        # Convert BitArray to counts dictionary
        counts_dict = bit_array.get_counts()

        # Ensure proper formatting
        counts = {}
        for bitstring, count in counts_dict.items():
            # bitstring might be int or string, normalize to binary string
            if isinstance(bitstring, int):
                counts[format(bitstring, f'0{circuit.num_qubits}b')] = count
            else:
                counts[bitstring] = count

        return counts

    def _calculate_energy_from_counts(
        self,
        counts: Dict[str, int],
        angles: List[float],
        coupling_strength: float
    ) -> float:
        """
        Calculate energy expectation from Qiskit measurement counts

        Args:
            counts: Measurement results
            angles: Original rotation angles
            coupling_strength: Coupling strength

        Returns:
            Expected energy
        """
        total_shots = sum(counts.values())
        h_fields = np.cos(angles)
        energy = 0.0

        for bitstring, count in counts.items():
            # Qiskit uses reversed bit order
            spins = np.array([1 if b == '1' else -1 for b in bitstring[::-1]])

            # H = Σ h_i Z_i + Σ J_ij Z_i Z_j
            config_energy = np.dot(h_fields, spins)

            for i in range(len(spins) - 1):
                config_energy += coupling_strength * spins[i] * spins[i+1]

            energy += (count / total_shots) * config_energy

        return energy
