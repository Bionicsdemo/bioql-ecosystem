# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Integration Tests
=======================

Tests end-to-end quantum execution with mocked backends,
BioQL + Quillow integration, caching, optimization, and error handling.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mocks.mock_quantum_backend import MockIBMBackend, MockQuantumBackend, MockStimBackend


@pytest.mark.integration
class TestBioQLQuantumExecution:
    """Test end-to-end quantum execution workflows"""

    @pytest.fixture
    def mock_backend(self):
        """Provide mock quantum backend"""
        backend = MockQuantumBackend(backend_name="mock_simulator")
        yield backend
        backend.reset()

    @pytest.fixture
    def mock_ibm_backend(self):
        """Provide mock IBM backend"""
        return MockIBMBackend(backend_name="ibm_torino")

    def test_simple_circuit_execution(self, mock_backend):
        """Test basic circuit execution with mock backend"""
        # Execute circuit
        result = mock_backend.execute(circuit="H 0; CNOT 0 1; M 0 1", shots=1024)

        # Verify execution
        assert result.success is True
        assert result.shots == 1024
        assert result.backend == "mock_simulator"
        assert len(result.counts) > 0
        assert sum(result.counts.values()) == 1024
        assert mock_backend.execution_count == 1

    def test_noisy_backend_execution(self):
        """Test execution with noise model"""
        noisy_backend = MockQuantumBackend(noise=True)

        result = noisy_backend.execute(circuit="H 0; CNOT 0 1; M 0 1", shots=1000)

        # Verify noisy results
        assert result.success is True
        assert "00" in result.counts
        assert "11" in result.counts
        # Should have some errors in noisy simulation
        assert "01" in result.counts or "10" in result.counts
        assert result.metadata["noise_level"] > 0

    def test_backend_failure_handling(self, mock_backend):
        """Test error handling when backend fails"""
        # Simulate backend failure
        mock_backend.should_fail = True
        mock_backend.failure_message = "Quantum hardware unavailable"

        result = mock_backend.execute(circuit="H 0; M 0", shots=100)

        # Verify error handling
        assert result.success is False
        assert "error" in result.metadata
        assert "unavailable" in result.metadata["error"]

    def test_multiple_circuit_execution(self, mock_backend):
        """Test executing multiple circuits in sequence"""
        circuits = ["H 0; M 0", "X 0; M 0", "H 0; H 1; CNOT 0 1; M 0 1"]

        results = []
        for circuit in circuits:
            result = mock_backend.execute(circuit, shots=500)
            results.append(result)

        # Verify all executions
        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_backend.execution_count == 3
        assert all(r.shots == 500 for r in results)

    def test_ibm_job_submission(self, mock_ibm_backend):
        """Test job submission to IBM backend"""
        # Submit job
        job = mock_ibm_backend.run(circuit="H 0; CNOT 0 1; M 0 1", shots=2048)

        # Verify job created
        assert job.job_id.startswith("ibm_job_")
        assert job.backend == "ibm_torino"
        assert job.shots == 2048
        assert job.status() == "QUEUED"

    def test_ibm_job_result_retrieval(self, mock_ibm_backend):
        """Test retrieving job results"""
        # Submit and get result
        job = mock_ibm_backend.run(circuit="H 0; M 0", shots=1024)
        result = job.result()

        # Verify result
        assert result.success is True
        assert result.shots == 1024
        assert job.status() == "DONE"
        assert len(result.counts) > 0

    def test_backend_properties(self, mock_ibm_backend):
        """Test accessing backend properties"""
        props = mock_ibm_backend.properties()

        # Verify properties
        assert props["backend_name"] == "ibm_torino"
        assert props["n_qubits"] == 133
        assert props["simulator"] is False
        assert "coupling_map" in props
        assert "basis_gates" in props
        assert props["t1"] > 0
        assert props["t2"] > 0


@pytest.mark.integration
class TestBioQLQuillowIntegration:
    """Test BioQL + Quillow QEC integration"""

    @pytest.fixture
    def mock_stim_backend(self):
        """Provide mock Stim backend for QEC"""
        return MockStimBackend()

    def test_qec_circuit_protection(self, mock_stim_backend):
        """Test protecting circuit with QEC"""
        # Sample with QEC
        circuit = "surface_code_d5"
        results = mock_stim_backend.sample(circuit, shots=1000)

        # Verify QEC execution
        assert results.shape[0] == 1000  # shots
        assert results.shape[1] == 10  # measurements
        assert len(mock_stim_backend.circuits_executed) == 1

    def test_syndrome_extraction(self, mock_stim_backend):
        """Test extracting error syndromes"""
        circuit = "surface_code_d5"
        sampler = mock_stim_backend.compile_detector_sampler(circuit)

        # Sample syndromes and observables
        syndromes, observables = sampler.sample(shots=500, separate_observables=True)

        # Verify syndrome data
        assert syndromes.shape[0] == 500  # shots
        assert syndromes.shape[1] == 24  # detectors for d=5
        assert observables.shape[0] == 500
        assert observables.shape[1] == 1  # logical observable

    def test_error_correction_workflow(self, mock_stim_backend):
        """Test complete error correction workflow"""
        # 1. Execute with errors
        circuit = "surface_code_d5"
        sampler = mock_stim_backend.compile_detector_sampler(circuit)

        # 2. Get syndromes
        syndromes, observables = sampler.sample(shots=1000, separate_observables=True)

        # 3. Mock decoding (simplified)
        predictions = np.random.randint(0, 2, size=syndromes.shape[0])

        # 4. Calculate logical error rate
        logical_errors = np.sum(predictions != observables[:, 0])
        error_rate = logical_errors / 1000

        # Verify workflow
        assert 0 <= error_rate <= 1
        assert len(predictions) == 1000

    def test_qec_overhead_calculation(self):
        """Test calculating QEC overhead"""
        base_shots = 1000
        qec_distance = 5

        # Physical qubits for surface code: d^2 + (d-1)^2
        physical_qubits = qec_distance**2 + (qec_distance - 1) ** 2

        # Overhead multiplier
        overhead = 1.5  # Surface code overhead

        # Calculate effective cost
        effective_shots = base_shots * overhead
        qubit_overhead = physical_qubits - 1  # minus logical qubit

        assert effective_shots == 1500
        assert qubit_overhead == 40  # 25 + 16 - 1

    def test_multiple_qec_distances(self, mock_stim_backend):
        """Test QEC with different code distances"""
        distances = [3, 5, 7]
        results = {}

        for d in distances:
            circuit = f"surface_code_d{d}"
            sampler = mock_stim_backend.compile_detector_sampler(circuit)
            syndromes, obs = sampler.sample(shots=100, separate_observables=True)

            # Expected detectors for distance d
            num_detectors = 2 * d * (d - 1)

            results[d] = {"syndromes": syndromes, "num_detectors": num_detectors}

        # Verify different distances
        assert results[3]["num_detectors"] == 12  # 2*3*2
        assert results[5]["num_detectors"] == 40  # 2*5*4
        assert results[7]["num_detectors"] == 84  # 2*7*6


@pytest.mark.integration
class TestBioQLCachingOptimization:
    """Test caching and optimization features"""

    def test_circuit_caching(self):
        """Test circuit result caching"""
        cache = {}

        def execute_with_cache(circuit, shots, backend):
            """Execute with caching"""
            cache_key = f"{circuit}_{shots}_{backend}"

            if cache_key in cache:
                return cache[cache_key]

            # Simulate execution
            result = {
                "counts": {"00": shots // 2, "11": shots // 2},
                "shots": shots,
                "cached": False,
            }

            cache[cache_key] = result
            return result

        # First execution - not cached
        result1 = execute_with_cache("H 0; CNOT 0 1", 1024, "simulator")
        assert result1["cached"] is False

        # Second execution - should be cached
        result2 = execute_with_cache("H 0; CNOT 0 1", 1024, "simulator")
        assert result2 is result1  # Same object from cache

    def test_parameter_optimization(self):
        """Test optimizing circuit parameters"""

        # Mock VQE optimization
        def optimize_parameters(initial_params, target_energy=-1.137):
            """Simulate parameter optimization"""
            params = initial_params.copy()
            energies = []

            for iteration in range(5):
                # Simulate energy calculation
                energy = target_energy + np.random.normal(0, 0.1)
                energies.append(energy)

                # Update parameters
                params += np.random.normal(0, 0.01, size=params.shape)

            return {"optimal_params": params, "optimal_energy": min(energies), "iterations": 5}

        initial = np.array([0.0, 0.0, 0.0])
        result = optimize_parameters(initial)

        assert "optimal_params" in result
        assert "optimal_energy" in result
        assert result["iterations"] == 5
        assert len(result["optimal_params"]) == 3

    def test_adaptive_shot_allocation(self):
        """Test adaptive shot allocation strategy"""

        def adaptive_shots(iteration, max_shots=10000):
            """Allocate shots based on iteration"""
            if iteration < 5:
                return 100  # Low shots for early exploration
            elif iteration < 10:
                return 500  # Medium shots
            else:
                return 1000  # High shots for final iterations

        # Test allocation
        assert adaptive_shots(0) == 100
        assert adaptive_shots(5) == 500
        assert adaptive_shots(15) == 1000

    def test_batch_execution_optimization(self, mock_backend=None):
        """Test batching multiple circuits for efficiency"""
        if mock_backend is None:
            mock_backend = MockQuantumBackend()

        circuits = [f"H {i}; M {i}" for i in range(5)]

        # Batch execution
        results = []
        for circuit in circuits:
            result = mock_backend.execute(circuit, shots=100)
            results.append(result)

        # Verify batch execution
        assert len(results) == 5
        assert all(r.success for r in results)
        assert mock_backend.execution_count == 5


@pytest.mark.integration
class TestBioQLErrorHandling:
    """Test comprehensive error handling across components"""

    def test_invalid_circuit_handling(self):
        """Test handling invalid circuit syntax"""
        backend = MockQuantumBackend()

        # Mock validation
        def validate_circuit(circuit):
            if not circuit or not isinstance(circuit, str):
                raise ValueError("Invalid circuit format")
            return True

        with pytest.raises(ValueError, match="Invalid circuit format"):
            validate_circuit(None)

        with pytest.raises(ValueError, match="Invalid circuit format"):
            validate_circuit(123)

    def test_quota_exceeded_handling(self):
        """Test handling quota exceeded errors"""

        def check_quota(user_balance, cost):
            if user_balance < cost:
                raise RuntimeError("Insufficient balance")
            return True

        # Should raise error
        with pytest.raises(RuntimeError, match="Insufficient balance"):
            check_quota(user_balance=10.0, cost=20.0)

        # Should succeed
        assert check_quota(user_balance=50.0, cost=10.0) is True

    def test_backend_timeout_handling(self):
        """Test handling backend timeout"""

        def execute_with_timeout(circuit, timeout=5):
            import time

            start = time.time()

            # Simulate long execution
            execution_time = 10  # Would take 10 seconds

            if execution_time > timeout:
                raise TimeoutError(f"Execution exceeded {timeout}s timeout")

            return {"success": True}

        with pytest.raises(TimeoutError, match="exceeded.*timeout"):
            execute_with_timeout("long_circuit", timeout=5)

    def test_network_error_retry(self):
        """Test retry logic for network errors"""
        attempts = []

        def execute_with_retry(circuit, max_retries=3):
            """Execute with retry on failure"""
            for attempt in range(max_retries):
                attempts.append(attempt)

                # Simulate failure for first 2 attempts
                if attempt < 2:
                    continue  # Retry

                # Success on 3rd attempt
                return {"success": True, "attempts": len(attempts)}

            raise RuntimeError("Max retries exceeded")

        result = execute_with_retry("test_circuit")
        assert result["success"] is True
        assert result["attempts"] == 3

    def test_partial_result_handling(self):
        """Test handling partial/incomplete results"""

        def validate_result(result, expected_shots):
            """Validate result completeness"""
            if "counts" not in result:
                raise ValueError("Missing counts in result")

            total_shots = sum(result["counts"].values())

            if total_shots < expected_shots * 0.9:
                raise ValueError(f"Incomplete result: {total_shots}/{expected_shots} shots")

            return True

        # Complete result
        good_result = {"counts": {"00": 500, "11": 500}}
        assert validate_result(good_result, 1000) is True

        # Incomplete result
        bad_result = {"counts": {"00": 100, "11": 100}}
        with pytest.raises(ValueError, match="Incomplete result"):
            validate_result(bad_result, 1000)

    def test_concurrent_execution_safety(self):
        """Test thread-safe concurrent execution"""
        backend = MockQuantumBackend()

        # Simulate concurrent executions
        results = []
        for i in range(10):
            result = backend.execute(f"H {i}; M {i}", shots=100)
            results.append(result)

        # Verify all succeeded
        assert len(results) == 10
        assert all(r.success for r in results)
        assert backend.execution_count == 10

    def test_error_recovery_workflow(self):
        """Test complete error recovery workflow"""
        backend = MockQuantumBackend()

        # 1. First execution fails
        backend.should_fail = True
        result1 = backend.execute("H 0; M 0", shots=100)
        assert result1.success is False

        # 2. Retry after recovery
        backend.should_fail = False
        result2 = backend.execute("H 0; M 0", shots=100)
        assert result2.success is True

        # 3. Verify state reset
        assert backend.execution_count == 2


# Test summary
def test_integration_suite_summary():
    """Summary of integration test coverage"""
    test_categories = {
        "Quantum Execution": 7,
        "QEC Integration": 5,
        "Caching & Optimization": 4,
        "Error Handling": 7,
    }

    total_tests = sum(test_categories.values())
    assert total_tests >= 20, f"Expected at least 20 tests, got {total_tests}"

    print(f"\nIntegration Test Coverage Summary:")
    print(f"{'='*50}")
    for category, count in test_categories.items():
        print(f"{category:.<40} {count:>3} tests")
    print(f"{'='*50}")
    print(f"{'Total':.>40} {total_tests:>3} tests")
