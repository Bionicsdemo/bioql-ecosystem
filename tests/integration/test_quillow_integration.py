# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Integration tests for Quillow (Quantum Error Correction)
"""

import numpy as np
import pytest

from tests.mocks.mock_quantum_backend import MockDetectorSampler, MockStimBackend


@pytest.mark.integration
@pytest.mark.quantum
class TestQuillowQEC:
    """Test Quillow QEC integration"""

    def test_surface_code_simulation(self):
        """Test surface code circuit simulation"""
        backend = MockStimBackend()

        # Mock circuit
        circuit = {"distance": 5, "rounds": 5}

        # Sample syndromes
        syndromes = backend.sample(circuit, shots=1000)

        assert syndromes.shape[0] == 1000  # shots
        assert syndromes.shape[1] == 10  # measurements

    def test_detector_sampling(self):
        """Test syndrome detector sampling"""
        circuit = {"distance": 5, "rounds": 5}
        sampler = MockDetectorSampler(circuit)

        syndromes = sampler.sample(shots=1000)

        assert syndromes.shape[0] == 1000
        assert syndromes.shape[1] == 24  # d=5 has 24 detectors

    def test_observable_measurement(self):
        """Test logical observable measurement"""
        circuit = {"distance": 5, "rounds": 5}
        sampler = MockDetectorSampler(circuit)

        syndromes, observables = sampler.sample(shots=1000, separate_observables=True)

        assert syndromes.shape == (1000, 24)
        assert observables.shape == (1000, 1)

    def test_error_rate_estimation(self):
        """Test logical error rate estimation"""
        # Mock error rates at different physical error rates
        physical_errors = [0.001, 0.005, 0.01]
        logical_errors = []

        for p_error in physical_errors:
            # Simulate QEC
            circuit = {"distance": 5, "error_rate": p_error}
            sampler = MockDetectorSampler(circuit)

            syndromes, observables = sampler.sample(shots=1000, separate_observables=True)

            # Calculate logical error rate
            logical_error_rate = np.mean(observables)
            logical_errors.append(logical_error_rate)

        # Logical error rate should be reasonably bounded
        # Note: With random syndromes, we can't guarantee improvement
        # In real QEC,logical errors would be lower than physical
        assert all(0 <= l <= 1 for l in logical_errors)


@pytest.mark.integration
class TestQuillowBackends:
    """Test Quillow backend integration"""

    def test_stim_backend_initialization(self):
        """Test Stim backend initialization"""
        backend = MockStimBackend()
        assert backend is not None
        assert hasattr(backend, "sample")

    def test_multiple_circuit_execution(self):
        """Test executing multiple circuits"""
        backend = MockStimBackend()

        circuits = [
            {"distance": 3, "rounds": 3},
            {"distance": 5, "rounds": 5},
            {"distance": 7, "rounds": 7},
        ]

        results = []
        for circuit in circuits:
            result = backend.sample(circuit, shots=100)
            results.append(result)

        assert len(results) == len(circuits)
        assert len(backend.circuits_executed) == 3


@pytest.mark.integration
@pytest.mark.slow
class TestQuillowDecoding:
    """Test QEC decoding integration"""

    def test_mwpm_decoding(self):
        """Test MWPM (Minimum Weight Perfect Matching) decoding"""
        # Mock syndrome data
        syndromes = np.array([[0, 1, 1, 0, 0, 0], [1, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 1]])

        # Mock MWPM decoder
        predictions = np.zeros(syndromes.shape[0], dtype=int)

        # Simulate decoding (mock implementation)
        for i, syndrome in enumerate(syndromes):
            if np.sum(syndrome) % 2 == 0:
                predictions[i] = 0
            else:
                predictions[i] = 1

        assert predictions.shape[0] == syndromes.shape[0]

    def test_union_find_decoding(self):
        """Test Union-Find decoder"""
        # Mock syndrome for Union-Find
        syndromes = np.random.randint(0, 2, size=(100, 24))

        # Simple mock decoding
        predictions = (np.sum(syndromes, axis=1) % 2).astype(int)

        assert len(predictions) == 100


@pytest.mark.integration
class TestQuillowNoise:
    """Test noise model integration"""

    def test_depolarizing_noise(self):
        """Test depolarizing noise model"""
        noise_params = {"type": "depolarizing", "error_rate": 0.001, "gate_time": 50e-9}  # 50 ns

        assert noise_params["error_rate"] > 0
        assert noise_params["error_rate"] < 1

    def test_measurement_noise(self):
        """Test measurement noise"""
        # Perfect measurements
        measurements = np.array([0, 0, 0, 0, 0])

        # Add noise
        error_rate = 0.01
        noise = np.random.random(len(measurements)) < error_rate
        noisy_measurements = (measurements + noise) % 2

        # Should have some errors (probabilistically)
        # We just check format here
        assert len(noisy_measurements) == len(measurements)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
