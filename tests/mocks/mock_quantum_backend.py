# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Mock Quantum Backends for testing
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class MockQuantumResult:
    """Mock quantum execution result"""

    counts: Dict[str, int]
    shots: int
    backend: str
    metadata: Dict[str, Any]
    success: bool = True
    job_id: Optional[str] = None


class MockQuantumBackend:
    """Mock quantum backend for testing"""

    def __init__(self, backend_name: str = "mock_simulator", noise: bool = False):
        self.backend_name = backend_name
        self.noise = noise
        self.execution_count = 0
        self.last_circuit = None
        self.should_fail = False
        self.failure_message = "Simulated backend failure"

    def execute(self, circuit: Any, shots: int = 1024, **kwargs) -> MockQuantumResult:
        """Mock execute quantum circuit"""
        self.execution_count += 1
        self.last_circuit = circuit

        if self.should_fail:
            return MockQuantumResult(
                counts={},
                shots=shots,
                backend=self.backend_name,
                metadata={"error": self.failure_message},
                success=False,
            )

        # Generate mock results
        if self.noise:
            # Noisy results
            counts = self._generate_noisy_counts(shots)
        else:
            # Perfect results
            counts = {"00": shots // 2, "11": shots // 2}

        return MockQuantumResult(
            counts=counts,
            shots=shots,
            backend=self.backend_name,
            metadata={
                "execution_time": 0.1,
                "qubits_used": 2,
                "noise_level": 0.01 if self.noise else 0.0,
            },
            job_id=f"job_{self.execution_count}",
        )

    def _generate_noisy_counts(self, shots: int) -> Dict[str, int]:
        """Generate realistic noisy measurement counts"""
        # Bell state with noise
        probabilities = {"00": 0.48, "01": 0.02, "10": 0.02, "11": 0.48}

        counts = {}
        remaining = shots

        for state, prob in probabilities.items():
            count = int(shots * prob)
            if count > 0:
                counts[state] = count
                remaining -= count

        # Distribute remaining shots
        if remaining > 0:
            counts["00"] = counts.get("00", 0) + remaining

        return counts

    def reset(self):
        """Reset mock state"""
        self.execution_count = 0
        self.last_circuit = None
        self.should_fail = False


class MockIBMBackend:
    """Mock IBM Quantum backend"""

    def __init__(self, backend_name: str = "ibm_torino"):
        self.backend_name = backend_name
        self.jobs = {}
        self.job_counter = 0
        self.queue_depth = 5

    def run(self, circuit: Any, shots: int = 1024) -> "MockJob":
        """Submit job to queue"""
        self.job_counter += 1
        job_id = f"ibm_job_{self.job_counter}"

        job = MockJob(
            job_id=job_id,
            backend=self.backend_name,
            shots=shots,
            circuit=circuit,
            queue_position=self.queue_depth,
        )

        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> "MockJob":
        """Get job by ID"""
        return self.jobs.get(job_id)

    def properties(self) -> Dict[str, Any]:
        """Get backend properties"""
        return {
            "backend_name": self.backend_name,
            "backend_version": "1.0.0",
            "n_qubits": 133,
            "simulator": False,
            "local": False,
            "coupling_map": [[0, 1], [1, 2], [2, 3]],
            "basis_gates": ["id", "rz", "sx", "x", "cx"],
            "t1": 100e-6,
            "t2": 80e-6,
            "readout_error": 0.01,
        }


class MockJob:
    """Mock quantum job"""

    def __init__(
        self, job_id: str, backend: str, shots: int, circuit: Any, queue_position: int = 0
    ):
        self.job_id = job_id
        self.backend = backend
        self.shots = shots
        self.circuit = circuit
        self.queue_position = queue_position
        self._status = "QUEUED"
        self._result = None

    def status(self) -> str:
        """Get job status"""
        return self._status

    def result(self) -> MockQuantumResult:
        """Get job result (blocks until complete)"""
        # Simulate completion
        if self._status == "QUEUED":
            self._status = "RUNNING"
        if self._status == "RUNNING":
            self._status = "DONE"

        if self._result is None:
            # Generate result
            counts = {"00": self.shots // 2 + 10, "11": self.shots // 2 - 10}
            self._result = MockQuantumResult(
                counts=counts,
                shots=self.shots,
                backend=self.backend,
                metadata={"job_id": self.job_id, "execution_time": 2.5},
                job_id=self.job_id,
            )

        return self._result

    def cancel(self):
        """Cancel job"""
        self._status = "CANCELLED"


class MockStimBackend:
    """Mock Stim backend for QEC testing"""

    def __init__(self):
        self.circuits_executed = []

    def sample(self, circuit: Any, shots: int = 1000) -> np.ndarray:
        """Sample from circuit"""
        self.circuits_executed.append(circuit)

        # Return mock measurement results
        num_measurements = 10  # Mock circuit has 10 measurements
        results = np.random.randint(0, 2, size=(shots, num_measurements))
        return results

    def compile_detector_sampler(self, circuit: Any):
        """Create detector sampler"""
        return MockDetectorSampler(circuit)


class MockDetectorSampler:
    """Mock detector sampler for syndrome extraction"""

    def __init__(self, circuit: Any):
        self.circuit = circuit

    def sample(self, shots: int = 1000, separate_observables: bool = False):
        """Sample syndromes and observables"""
        # Mock syndrome data (detectors)
        num_detectors = 24  # d=5 surface code has 24 detectors
        syndromes = np.random.randint(0, 2, size=(shots, num_detectors))

        if separate_observables:
            # Mock observable data (logical qubits)
            num_observables = 1
            observables = np.random.randint(0, 2, size=(shots, num_observables))
            return syndromes, observables

        return syndromes
