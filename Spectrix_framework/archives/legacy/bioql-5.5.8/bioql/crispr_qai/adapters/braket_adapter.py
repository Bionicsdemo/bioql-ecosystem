"""
AWS Braket adapter for CRISPR-QAI energy estimation

Supports:
- SV1 (State Vector Simulator, 34 qubits)
- DM1 (Density Matrix Simulator, 17 qubits, noise)
- Rigetti Aspen-M (real quantum hardware)
- IonQ Harmony (real quantum hardware)

Requires:
- AWS account with Braket access
- boto3 and amazon-braket-sdk
"""

import time
from typing import Dict, List, Any, Optional
import numpy as np

from .base import QuantumEngine

try:
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
    import boto3
    HAVE_BRAKET = True
except ImportError:
    HAVE_BRAKET = False


class BraketEngine(QuantumEngine):
    """
    AWS Braket quantum backend for CRISPR energy estimation
    """

    def __init__(
        self,
        backend_name: str = "SV1",
        shots: int = 1000,
        aws_region: str = "us-east-1",
        s3_bucket: Optional[str] = None
    ):
        """
        Initialize Braket backend

        Args:
            backend_name: Braket device ('SV1', 'DM1', 'Aspen-M', 'Harmony')
            shots: Number of measurements
            aws_region: AWS region
            s3_bucket: S3 bucket for results (required for hardware)
        """
        if not HAVE_BRAKET:
            raise ImportError(
                "AWS Braket not installed. "
                "Install with: pip install amazon-braket-sdk boto3"
            )

        super().__init__(backend_name=backend_name, shots=shots)
        self.aws_region = aws_region
        self.s3_bucket = s3_bucket
        self.device = None

    def run_energy_estimation(
        self,
        angles: List[float],
        coupling_strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run energy estimation on AWS Braket

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

        # Execute on Braket
        task = self.device.run(circuit, shots=self.shots)
        result = task.result()

        # Parse results
        counts = result.measurement_counts

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
            'task_arn': task.id,
            'metadata': metadata or {}
        }

    def validate_backend(self) -> bool:
        """
        Validate AWS Braket backend

        Returns:
            True if backend is available
        """
        try:
            if self.backend_name in ["SV1", "DM1"]:
                # Local simulators
                self.device = LocalSimulator(self.backend_name)
            else:
                # Real quantum hardware (requires S3)
                if not self.s3_bucket:
                    raise ValueError(
                        f"s3_bucket required for hardware backend {self.backend_name}"
                    )

                from braket.aws import AwsDevice
                device_arn = self._get_device_arn(self.backend_name)
                self.device = AwsDevice(device_arn)

            self.validated = True
            return True

        except Exception as e:
            print(f"Braket validation failed: {e}")
            self.validated = False
            return False

    def _build_circuit(
        self,
        angles: List[float],
        coupling_strength: float
    ) -> "Circuit":
        """
        Build Braket quantum circuit for energy estimation

        Args:
            angles: Rotation angles
            coupling_strength: Coupling strength

        Returns:
            Braket Circuit
        """
        num_qubits = len(angles)
        circuit = Circuit()

        # Apply rotations encoding gRNA sequence
        for i, angle in enumerate(angles):
            circuit.ry(i, angle)

        # Apply ZZ couplings for base-pair interactions
        for i in range(num_qubits - 1):
            # ZZ(θ) = exp(-i θ/2 Z_i Z_{i+1})
            theta = coupling_strength * np.pi / 4
            circuit.zz(i, i+1, theta)

        # Measure all qubits
        circuit.measure(range(num_qubits))

        return circuit

    def _calculate_energy_from_counts(
        self,
        counts: Dict[str, int],
        angles: List[float],
        coupling_strength: float
    ) -> float:
        """
        Calculate energy expectation from Braket measurement counts

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
            spins = np.array([1 if b == '1' else -1 for b in bitstring])

            # H = Σ h_i Z_i + Σ J_ij Z_i Z_j
            config_energy = np.dot(h_fields, spins)

            for i in range(len(spins) - 1):
                config_energy += coupling_strength * spins[i] * spins[i+1]

            energy += (count / total_shots) * config_energy

        return energy

    def _get_device_arn(self, device_name: str) -> str:
        """
        Get AWS device ARN from device name

        Args:
            device_name: Device name (e.g., 'Aspen-M', 'Harmony')

        Returns:
            Device ARN
        """
        device_map = {
            'Aspen-M': 'arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3',
            'Harmony': 'arn:aws:braket:us-east-1::device/qpu/ionq/Harmony',
        }

        if device_name not in device_map:
            raise ValueError(
                f"Unknown device: {device_name}. "
                f"Available: {list(device_map.keys())}"
            )

        return device_map[device_name]
