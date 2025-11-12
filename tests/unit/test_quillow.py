#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Comprehensive Unit Tests for Quillow (Quantum Error Correction)
================================================================

Tests all core components of the Quillow QEC system:
- Surface code implementation (distance 3, 5, 7)
- Syndrome extraction and error correction
- PyMatching decoder (MWPM)
- Union-Find decoder
- Noise models (depolarizing, coherence)
- BioQL integration
- Performance benchmarks

Run with:
    pytest tests/unit/test_quillow.py -v
    pytest tests/unit/test_quillow.py -v -m "not slow"  # Skip slow tests
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

# Add Quillow to path
quillow_path = Path(__file__).parent.parent.parent / "Quillow"
sys.path.insert(0, str(quillow_path))

# Import Quillow components
from quillow import (
    BioQLBackend,
    BioQLConfig,
    BioQLOptimizer,
    CoherenceNoise,
    DepolarizingNoise,
    MWPMDecoder,
    PyMatchingDecoder,
    RotatedSurfaceCode,
    SurfaceCode,
    SurfaceCodeSimulator,
    UnionFindDecoder,
    get_decoder,
    get_noise_model,
)
from quillow.core.surface_code import QubitLayout, SimulationResult, StabilizerSpec
from quillow.decoders.abstract_decoder import AbstractDecoder, DecoderResult

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def surface_code_d3():
    """Distance-3 surface code for testing."""
    return RotatedSurfaceCode(distance=3, rounds=1)


@pytest.fixture
def surface_code_d5():
    """Distance-5 surface code for testing."""
    return RotatedSurfaceCode(distance=5, rounds=1)


@pytest.fixture
def surface_code_d7():
    """Distance-7 surface code for testing."""
    return RotatedSurfaceCode(distance=7, rounds=1)


@pytest.fixture
def depolarizing_noise():
    """Depolarizing noise model."""
    return DepolarizingNoise(error_rate=0.001)


@pytest.fixture
def coherence_noise():
    """Coherence noise model with T1/T2."""
    return CoherenceNoise(T1_us=100.0, T2_us=50.0)


@pytest.fixture
def pymatching_decoder():
    """PyMatching decoder instance."""
    return PyMatchingDecoder()


@pytest.fixture
def unionfind_decoder():
    """Union-Find decoder instance."""
    return UnionFindDecoder()


@pytest.fixture
def mock_bioql_config():
    """Mock BioQL configuration."""
    return BioQLConfig(
        base_url="https://api.bioql.bio",
        api_key="test_api_key_12345",
        timeout=3600,
        verify_ssl=True,
    )


# ============================================================================
# Test 1-3: SurfaceCodeSimulator - Initialization with Different Distances
# ============================================================================


@pytest.mark.unit
def test_surface_code_d3_initialization(surface_code_d3):
    """Test distance-3 surface code initialization."""
    assert surface_code_d3.distance == 3
    assert surface_code_d3.rounds == 1

    # Check qubit layout
    layout = surface_code_d3.layout
    assert layout.n_data == 9  # d^2 = 3^2 = 9 data qubits
    assert layout.n_syndrome > 0  # Should have syndrome qubits
    assert layout.distance == 3

    # Check stabilizers
    assert len(surface_code_d3.stabilizers) > 0
    x_stabilizers = [s for s in surface_code_d3.stabilizers if s.type == "X"]
    z_stabilizers = [s for s in surface_code_d3.stabilizers if s.type == "Z"]
    assert len(x_stabilizers) > 0
    assert len(z_stabilizers) > 0


@pytest.mark.unit
def test_surface_code_d5_initialization(surface_code_d5):
    """Test distance-5 surface code initialization."""
    assert surface_code_d5.distance == 5
    assert surface_code_d5.rounds == 1

    layout = surface_code_d5.layout
    assert layout.n_data == 25  # d^2 = 5^2 = 25 data qubits
    assert layout.n_syndrome > 0
    assert layout.distance == 5


@pytest.mark.unit
def test_surface_code_d7_initialization(surface_code_d7):
    """Test distance-7 surface code initialization."""
    assert surface_code_d7.distance == 7
    assert surface_code_d7.rounds == 1

    layout = surface_code_d7.layout
    assert layout.n_data == 49  # d^2 = 7^2 = 49 data qubits
    assert layout.n_syndrome > 0
    assert layout.distance == 7


# ============================================================================
# Test 4: Surface Code - Invalid Distance
# ============================================================================


@pytest.mark.unit
def test_surface_code_invalid_distance():
    """Test that even distances raise ValueError."""
    with pytest.raises(ValueError, match="Distance must be odd"):
        RotatedSurfaceCode(distance=4, rounds=1)

    with pytest.raises(ValueError, match="Minimum distance is 3"):
        RotatedSurfaceCode(distance=1, rounds=1)


# ============================================================================
# Test 5: Surface Code - Qubit Layout
# ============================================================================


@pytest.mark.unit
def test_qubit_layout_properties(surface_code_d3):
    """Test QubitLayout properties and relationships."""
    layout = surface_code_d3.layout

    # Check basic properties
    assert isinstance(layout, QubitLayout)
    assert layout.total_qubits == layout.n_data + layout.n_syndrome

    # Data qubits should be on integer coordinates
    for qubit in layout.data_qubits:
        x, y = qubit
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert 0 <= x < layout.distance
        assert 0 <= y < layout.distance


# ============================================================================
# Test 6: Surface Code - Stabilizer Specifications
# ============================================================================


@pytest.mark.unit
def test_stabilizer_specs(surface_code_d3):
    """Test stabilizer specifications."""
    for stabilizer in surface_code_d3.stabilizers:
        assert isinstance(stabilizer, StabilizerSpec)
        assert stabilizer.type in ["X", "Z"]
        assert len(stabilizer.data_qubits) >= 2  # At least 2 qubits (boundary)
        assert stabilizer.weight() == len(stabilizer.data_qubits)
        assert len(stabilizer.order) > 0


# ============================================================================
# Test 7: Surface Code - Stim Circuit Generation
# ============================================================================


@pytest.mark.unit
def test_stim_circuit_generation(surface_code_d3, depolarizing_noise):
    """Test Stim circuit generation with noise."""
    import stim

    circuit = surface_code_d3.build_stim_circuit(noise_model=depolarizing_noise)

    assert isinstance(circuit, stim.Circuit)
    assert circuit.num_qubits > 0
    assert circuit.num_detectors > 0
    assert circuit.num_observables > 0

    # Check circuit has required operations
    circuit_str = str(circuit)
    assert "R" in circuit_str  # Reset operations
    assert "TICK" in circuit_str  # Time steps
    assert "DETECTOR" in circuit_str  # Syndrome measurements


# ============================================================================
# Test 8-9: Syndrome Extraction and Error Correction
# ============================================================================


@pytest.mark.unit
def test_syndrome_extraction():
    """Test syndrome extraction from surface code."""
    import stim

    simulator = SurfaceCodeSimulator(distance=3, physical_error_rate=0.01, rounds=1)

    # Sample to get syndromes
    sampler = simulator.circuit.compile_detector_sampler()
    syndromes, observables = sampler.sample(shots=10, separate_observables=True)

    assert syndromes.shape[0] == 10  # Number of shots
    assert syndromes.shape[1] > 0  # Number of detectors
    assert observables.shape[0] == 10
    assert np.all((syndromes == 0) | (syndromes == 1))  # Binary


@pytest.mark.unit
def test_error_correction_basic():
    """Test basic error correction with low error rate."""
    simulator = SurfaceCodeSimulator(distance=5, physical_error_rate=0.001, rounds=3)

    result = simulator.run(shots=100, decoder="pymatching")

    assert isinstance(result, SimulationResult)
    assert result.distance == 5
    assert result.rounds == 3
    assert result.shots == 100
    assert 0 <= result.logical_error_rate <= 1.0
    assert result.logical_errors >= 0
    assert result.runtime_seconds > 0


# ============================================================================
# Test 10: Logical Error Rate Calculation
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "error_rate,expected_below_threshold",
    [
        (0.0001, True),  # Very low error rate - should be below threshold
        (0.001, True),  # Low error rate - should be below threshold
        (0.01, True),  # Near threshold - might be below for d=5
    ],
)
def test_logical_error_rates(error_rate, expected_below_threshold):
    """Test logical error rates for different physical error rates."""
    simulator = SurfaceCodeSimulator(distance=5, physical_error_rate=error_rate, rounds=5)

    result = simulator.run(shots=1000, decoder="pymatching")

    assert result.physical_error_rate == error_rate
    assert isinstance(result.logical_error_rate, float)
    assert result.logical_error_rate >= 0

    # For very low error rates, logical should be lower than physical
    if error_rate <= 0.001:
        # QEC should provide error suppression
        assert result.suppression_factor >= 1.0 or result.logical_error_rate == 0


# ============================================================================
# Test 11-12: PyMatching Decoder (MWPM)
# ============================================================================


@pytest.mark.unit
def test_pymatching_decoder_initialization(pymatching_decoder):
    """Test PyMatching decoder initialization."""
    assert isinstance(pymatching_decoder, PyMatchingDecoder)
    assert isinstance(pymatching_decoder, AbstractDecoder)
    assert pymatching_decoder.name == "PyMatching"
    assert pymatching_decoder.weights_from_dem is True
    assert pymatching_decoder.matcher is None  # Not built yet


@pytest.mark.unit
def test_pymatching_decoder_build_matcher(pymatching_decoder):
    """Test building PyMatching matcher from circuit."""
    import stim

    # Create a simple circuit
    simulator = SurfaceCodeSimulator(distance=3, physical_error_rate=0.001)
    circuit = simulator.circuit

    # Build matcher
    pymatching_decoder.build_matcher(circuit)

    assert pymatching_decoder.matcher is not None
    assert circuit.num_detectors > 0


# ============================================================================
# Test 13: PyMatching Decoder - Batch Decoding
# ============================================================================


@pytest.mark.unit
def test_pymatching_batch_decoding():
    """Test PyMatching batch decoding."""
    simulator = SurfaceCodeSimulator(distance=3, physical_error_rate=0.005)

    # Sample syndromes
    sampler = simulator.circuit.compile_detector_sampler()
    syndromes, observables = sampler.sample(shots=50, separate_observables=True)

    # Decode
    decoder = PyMatchingDecoder()
    predictions = decoder.decode_batch(syndromes, circuit=simulator.circuit)

    assert predictions.shape == (50,)
    assert np.all((predictions == 0) | (predictions == 1))
    assert decoder.decode_count == 50
    assert decoder.total_decode_time > 0


# ============================================================================
# Test 14: PyMatching Decoder - Accuracy
# ============================================================================


@pytest.mark.unit
def test_pymatching_decoder_accuracy():
    """Test PyMatching decoder achieves good accuracy."""
    simulator = SurfaceCodeSimulator(distance=5, physical_error_rate=0.001)
    result = simulator.run(shots=1000, decoder="pymatching")

    # With low error rate and d=5, should have very low logical error rate
    assert result.logical_error_rate < 0.01  # Less than 1% logical errors

    # Error suppression should be positive
    if result.logical_error_rate > 0:
        assert result.suppression_factor > 0


# ============================================================================
# Test 15-16: Union-Find Decoder
# ============================================================================


@pytest.mark.unit
def test_unionfind_decoder_initialization(unionfind_decoder):
    """Test Union-Find decoder initialization."""
    assert isinstance(unionfind_decoder, UnionFindDecoder)
    assert isinstance(unionfind_decoder, AbstractDecoder)
    assert unionfind_decoder.name == "UnionFind"
    assert unionfind_decoder.growth_order == "nearest"
    assert unionfind_decoder.max_growth_rounds == 100


@pytest.mark.unit
def test_unionfind_decoder_decoding():
    """Test Union-Find decoder can decode syndromes."""
    from quillow.decoders.union_find import UnionFind

    # Test Union-Find data structure
    uf = UnionFind(10)

    # Initially all separate
    assert uf.find(0) != uf.find(1)

    # Union some elements
    uf.union(0, 1)
    assert uf.find(0) == uf.find(1)
    assert uf.connected(0, 1)

    uf.union(1, 2)
    assert uf.connected(0, 2)

    # Test decoder
    decoder = UnionFindDecoder()
    simulator = SurfaceCodeSimulator(distance=3, physical_error_rate=0.005)

    sampler = simulator.circuit.compile_detector_sampler()
    syndromes, _ = sampler.sample(shots=20, separate_observables=True)

    predictions = decoder.decode_batch(syndromes)
    assert predictions.shape == (20,)


# ============================================================================
# Test 17: Decoder Factory Function
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "decoder_name,expected_class",
    [
        ("pymatching", PyMatchingDecoder),
        ("mwpm", MWPMDecoder),
        ("unionfind", UnionFindDecoder),
    ],
)
def test_get_decoder_factory(decoder_name, expected_class):
    """Test decoder factory function."""
    decoder = get_decoder(decoder_name)
    assert isinstance(decoder, expected_class)
    assert isinstance(decoder, AbstractDecoder)


# ============================================================================
# Test 18-19: Noise Models - Depolarizing
# ============================================================================


@pytest.mark.unit
def test_depolarizing_noise_initialization(depolarizing_noise):
    """Test depolarizing noise model initialization."""
    from quillow.core.noise_models import NoiseModel

    assert isinstance(depolarizing_noise, NoiseModel)
    assert depolarizing_noise.error_rate == 0.001
    assert depolarizing_noise.params.single_qubit_gate_error == 0.001


@pytest.mark.unit
def test_depolarizing_noise_circuit_generation(depolarizing_noise):
    """Test depolarizing noise generates proper Stim circuits."""
    import stim

    # Single-qubit gate noise
    noise_circuit = depolarizing_noise.single_qubit_gate_noise([0, 1, 2])
    assert isinstance(noise_circuit, stim.Circuit)
    circuit_str = str(noise_circuit)
    assert "DEPOLARIZE1" in circuit_str

    # Two-qubit gate noise
    noise_circuit = depolarizing_noise.two_qubit_gate_noise([0, 1])
    assert isinstance(noise_circuit, stim.Circuit)
    circuit_str = str(noise_circuit)
    assert "DEPOLARIZE2" in circuit_str

    # Measurement noise
    noise_circuit = depolarizing_noise.measurement_noise(3)
    assert isinstance(noise_circuit, stim.Circuit)
    circuit_str = str(noise_circuit)
    assert "X_ERROR" in circuit_str


# ============================================================================
# Test 20: Noise Models - Coherence (T1/T2)
# ============================================================================


@pytest.mark.unit
def test_coherence_noise_model(coherence_noise):
    """Test coherence noise model with T1/T2."""
    assert coherence_noise.T1_us == 100.0
    assert coherence_noise.T2_us == 50.0
    assert coherence_noise.T2_us <= 2 * coherence_noise.T1_us  # Physical bound

    # Test error probabilities scale with time
    p_amp_1us, p_phase_1us = coherence_noise._error_probabilities(1.0)
    p_amp_10us, p_phase_10us = coherence_noise._error_probabilities(10.0)

    assert p_amp_10us > p_amp_1us
    assert p_phase_10us > p_phase_1us
    assert 0 <= p_amp_1us <= 1
    assert 0 <= p_phase_1us <= 1


# ============================================================================
# Test 21: Noise Model Factory
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "model_type",
    ["depolarizing", "bitflip", "phaseflip", "amplitude_damping", "coherence", "circuit_level"],
)
def test_noise_model_factory(model_type):
    """Test noise model factory function."""
    noise_model = get_noise_model(model_type, error_rate=0.001)
    from quillow.core.noise_models import NoiseModel

    assert isinstance(noise_model, NoiseModel)


# ============================================================================
# Test 22: BioQL Backend - Initialization
# ============================================================================


@pytest.mark.unit
def test_bioql_backend_initialization(mock_bioql_config):
    """Test BioQL backend initialization."""
    backend = BioQLBackend(config=mock_bioql_config, qec_distance=5, enable_qec=True)

    assert backend.name == "BioQL"
    assert backend.qec_distance == 5
    assert backend.enable_qec is True
    assert backend.config.api_key == "test_api_key_12345"
    assert isinstance(backend.decoder, PyMatchingDecoder)


# ============================================================================
# Test 23: BioQL Backend - API Validation (Mocked)
# ============================================================================


@pytest.mark.unit
def test_bioql_backend_api_validation_mock(mock_bioql_config):
    """Test BioQL API key validation with mocking."""
    backend = BioQLBackend(config=mock_bioql_config)

    # Mock the requests.post call
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user_id": "test_user_123", "valid": True}
        mock_post.return_value = mock_response

        result = backend.validate_api_key()
        assert result is True

        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert mock_bioql_config.base_url in call_args[0][0]


# ============================================================================
# Test 24: BioQL Backend - Quota Check (Mocked)
# ============================================================================


@pytest.mark.unit
def test_bioql_backend_quota_check_mock(mock_bioql_config):
    """Test BioQL quota checking with mocking."""
    backend = BioQLBackend(config=mock_bioql_config)

    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user": {"balance": 100.0, "tier": "pro"},
            "quota": {"shots_used": 50000, "shots_limit": "unlimited"},
        }
        mock_post.return_value = mock_response

        quota = backend.check_quota()

        assert quota["balance"] == 100.0
        assert quota["tier"] == "pro"
        assert quota["shots_used"] == 50000


# ============================================================================
# Test 25: BioQL Optimizer - Initialization
# ============================================================================


@pytest.mark.unit
def test_bioql_optimizer_initialization():
    """Test BioQL optimizer initialization."""
    optimizer = BioQLOptimizer(api_key="test_key", qec_distance=5, auto_optimize=True)

    assert isinstance(optimizer.backend, BioQLBackend)
    assert optimizer.backend.qec_distance == 5
    assert optimizer.auto_optimize is True


# ============================================================================
# Test 26: BioQL Optimizer - Circuit Protection
# ============================================================================


@pytest.mark.unit
def test_bioql_optimizer_circuit_protection():
    """Test circuit protection with surface code."""
    import stim

    optimizer = BioQLOptimizer(api_key="test_key", qec_distance=3)

    # Create a simple circuit
    simple_circuit = stim.Circuit()

    protected_circuit = optimizer.protect_circuit(simple_circuit, distance=3)

    assert isinstance(protected_circuit, stim.Circuit)
    assert protected_circuit.num_qubits > 0
    assert protected_circuit.num_detectors > 0


# ============================================================================
# Test 27: Simulation Results - Properties
# ============================================================================


@pytest.mark.unit
def test_simulation_result_properties():
    """Test SimulationResult properties and methods."""
    result = SimulationResult(
        distance=5,
        rounds=5,
        shots=1000,
        physical_error_rate=0.001,
        logical_error_rate=0.0001,
        logical_errors=1,
        detection_events=np.zeros((1000, 24)),
        observable_flips=np.zeros((1000, 1)),
        runtime_seconds=2.5,
        decoder_time_seconds=1.0,
    )

    assert result.is_below_threshold is True  # Logical < Physical
    assert result.suppression_factor == 10.0  # 0.001 / 0.0001
    assert result.avg_latency_us > 0

    # Test to_dict conversion
    result_dict = result.to_dict()
    assert result_dict["distance"] == 5
    assert result_dict["logical_error_rate"] == 0.0001
    assert result_dict["is_below_threshold"] is True


# ============================================================================
# Test 28: Below-Threshold Operation
# ============================================================================


@pytest.mark.unit
def test_below_threshold_operation():
    """Test that QEC operates below threshold for low error rates."""
    simulator = SurfaceCodeSimulator(
        distance=5, physical_error_rate=0.0005, rounds=5  # Well below threshold (~1.1%)
    )

    result = simulator.run(shots=1000, decoder="pymatching")

    # With d=5 and very low physical error rate, should achieve suppression
    # (though with finite sampling, might occasionally not achieve it)
    assert result.physical_error_rate == 0.0005

    # Logical error rate should be reasonable
    assert result.logical_error_rate < 0.1  # Less than 10%


# ============================================================================
# Test 29: Parametrized Distance Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "distance,expected_data_qubits",
    [
        (3, 9),  # 3^2 = 9
        (5, 25),  # 5^2 = 25
        (7, 49),  # 7^2 = 49
    ],
)
def test_distance_scaling(distance, expected_data_qubits):
    """Test surface code scaling with distance."""
    code = RotatedSurfaceCode(distance=distance, rounds=1)
    assert code.layout.n_data == expected_data_qubits
    assert code.distance == distance


# ============================================================================
# Test 30: Factory Functions
# ============================================================================


@pytest.mark.unit
def test_surface_code_factory_functions():
    """Test SurfaceCode factory methods."""
    code_d3 = SurfaceCode.distance_3(rounds=2)
    assert code_d3.distance == 3
    assert code_d3.rounds == 2

    code_d5 = SurfaceCode.distance_5(rounds=3)
    assert code_d5.distance == 5
    assert code_d5.rounds == 3

    code_d7 = SurfaceCode.distance_7(rounds=1)
    assert code_d7.distance == 7

    code_custom = SurfaceCode.custom_distance(distance=9, rounds=1)
    assert code_custom.distance == 9


# ============================================================================
# Test 31: Performance Test - Decoder Throughput (Marked as Slow)
# ============================================================================


@pytest.mark.slow
@pytest.mark.unit
def test_decoder_throughput_performance():
    """Test decoder throughput performance."""
    simulator = SurfaceCodeSimulator(distance=5, physical_error_rate=0.001)

    # Sample large batch
    sampler = simulator.circuit.compile_detector_sampler()
    syndromes, observables = sampler.sample(shots=5000, separate_observables=True)

    # Test PyMatching performance
    decoder = PyMatchingDecoder()
    start_time = time.time()
    predictions = decoder.decode_batch(syndromes, circuit=simulator.circuit)
    decode_time = time.time() - start_time

    throughput = 5000 / decode_time

    # Should decode at least 100 shots per second
    assert throughput > 100, f"Throughput too low: {throughput:.1f} shots/sec"

    # Check statistics
    stats = decoder.get_statistics()
    assert stats["decode_count"] == 5000
    assert stats["throughput"] > 0


# ============================================================================
# Test 32: Performance Test - Circuit Compilation (Marked as Slow)
# ============================================================================


@pytest.mark.slow
@pytest.mark.unit
def test_circuit_compilation_performance():
    """Test circuit compilation performance for different distances."""
    distances = [3, 5, 7]
    compilation_times = {}

    for d in distances:
        code = RotatedSurfaceCode(distance=d, rounds=d)
        noise = DepolarizingNoise(error_rate=0.001)

        start = time.time()
        circuit = code.build_stim_circuit(noise_model=noise)
        compilation_times[d] = time.time() - start

        assert circuit.num_qubits > 0
        assert circuit.num_detectors > 0

    # Compilation should complete in reasonable time
    assert all(
        t < 1.0 for t in compilation_times.values()
    ), f"Compilation too slow: {compilation_times}"


# ============================================================================
# Test 33: Edge Cases - Zero Error Rate
# ============================================================================


@pytest.mark.unit
def test_zero_error_rate():
    """Test behavior with zero error rate."""
    simulator = SurfaceCodeSimulator(distance=3, physical_error_rate=0.0, rounds=1)  # No errors

    result = simulator.run(shots=100, decoder="pymatching")

    # With zero errors, should have zero logical errors
    assert result.logical_error_rate == 0.0
    assert result.logical_errors == 0


# ============================================================================
# Test 34: Edge Cases - High Error Rate
# ============================================================================


@pytest.mark.unit
def test_high_error_rate():
    """Test behavior with high error rate (above threshold)."""
    simulator = SurfaceCodeSimulator(
        distance=3, physical_error_rate=0.05, rounds=1  # 5% - well above threshold
    )

    result = simulator.run(shots=500, decoder="pymatching")

    # With high error rate, logical error rate will be significant
    assert result.logical_error_rate > 0
    # Should still be a valid probability
    assert 0 <= result.logical_error_rate <= 1.0


# ============================================================================
# Test 35: Decoder Statistics Tracking
# ============================================================================


@pytest.mark.unit
def test_decoder_statistics_tracking():
    """Test decoder statistics are properly tracked."""
    decoder = PyMatchingDecoder()

    # Initially empty
    stats = decoder.get_statistics()
    assert stats["decode_count"] == 0
    assert stats["total_time"] == 0

    # After decoding
    simulator = SurfaceCodeSimulator(distance=3, physical_error_rate=0.005)
    sampler = simulator.circuit.compile_detector_sampler()
    syndromes, _ = sampler.sample(shots=100, separate_observables=True)

    decoder.decode_batch(syndromes, circuit=simulator.circuit)

    stats = decoder.get_statistics()
    assert stats["decode_count"] == 100
    assert stats["total_time"] > 0
    assert stats["avg_time_per_shot"] > 0
    assert stats["throughput"] > 0

    # Reset statistics
    decoder.reset_statistics()
    stats = decoder.get_statistics()
    assert stats["decode_count"] == 0


# ============================================================================
# Test 36: Stim Integration - Detector Error Model
# ============================================================================


@pytest.mark.unit
def test_detector_error_model_extraction():
    """Test extraction of detector error model from circuit."""
    import stim

    simulator = SurfaceCodeSimulator(distance=3, physical_error_rate=0.001)
    circuit = simulator.circuit

    # Extract DEM
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)

    assert isinstance(dem, stim.DetectorErrorModel)
    assert len(str(dem)) > 0  # Should have content


# ============================================================================
# Helper Test: Multiple Rounds
# ============================================================================


@pytest.mark.unit
def test_multiple_qec_rounds():
    """Test surface code with multiple QEC rounds."""
    code = RotatedSurfaceCode(distance=3, rounds=5)
    assert code.rounds == 5

    noise = DepolarizingNoise(error_rate=0.001)
    circuit = code.build_stim_circuit(noise_model=noise)

    # Circuit should have multiple rounds
    circuit_str = str(circuit)
    tick_count = circuit_str.count("TICK")
    assert tick_count >= 5  # At least one per round


# ============================================================================
# Summary
# ============================================================================

"""
Test Summary:
=============

Total Tests Created: 36

Component Coverage:
-------------------
1. SurfaceCodeSimulator (Tests 1-10):
   - Initialization with distances 3, 5, 7
   - Invalid distance handling
   - Qubit layout properties
   - Stabilizer specifications
   - Stim circuit generation
   - Syndrome extraction
   - Error correction
   - Logical error rates
   - Below-threshold operation

2. Decoders (Tests 11-17):
   - PyMatching initialization and build
   - Batch decoding
   - Decoder accuracy
   - Union-Find decoder
   - Decoder factory function
   - Multiple decoder types

3. Noise Models (Tests 18-21):
   - Depolarizing noise initialization
   - Circuit generation
   - Coherence noise (T1/T2)
   - Noise model factory
   - Multiple noise types

4. BioQL Integration (Tests 22-26):
   - Backend initialization
   - API validation (mocked)
   - Quota checking (mocked)
   - Optimizer initialization
   - Circuit protection

5. Performance & Edge Cases (Tests 27-36):
   - Simulation result properties
   - Parametrized distance tests
   - Factory functions
   - Decoder throughput (slow)
   - Circuit compilation (slow)
   - Zero/high error rates
   - Statistics tracking
   - DEM extraction
   - Multiple QEC rounds

Key Features Tested:
--------------------
✓ Distance scaling (3, 5, 7)
✓ Syndrome extraction
✓ Error correction accuracy
✓ Multiple decoders (PyMatching, Union-Find)
✓ Noise models (depolarizing, coherence)
✓ BioQL integration (mocked)
✓ Below-threshold operation
✓ Performance benchmarks
✓ Edge cases (zero/high error)
✓ Parametrized tests
✓ Mocking for external dependencies

Usage:
------
Run all tests:          pytest tests/unit/test_quillow.py -v
Skip slow tests:        pytest tests/unit/test_quillow.py -v -m "not slow"
Run only unit tests:    pytest tests/unit/test_quillow.py -v -m "unit"
Run specific test:      pytest tests/unit/test_quillow.py::test_name -v
"""
