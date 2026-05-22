"""
Tests for Probabilistic Error Cancellation (PEC) module.
"""
import sys
import os
import pytest
import numpy as np
from pathlib import Path

# Add agents directory to path
_agents_dir = str(Path(__file__).resolve().parent.parent.parent / "src" / "backend" / "BioQL_MCP" / "src" / "agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import EfficientSU2

from probabilistic_error_cancellation import (
    ProbabilisticErrorCancellation,
    PECConfig,
    PECResult,
    H2_HAMILTONIAN,
    H2_EXACT_ENERGY,
)


@pytest.fixture
def pec():
    """PEC instance in simulator mode."""
    return ProbabilisticErrorCancellation(use_hardware=False)


@pytest.fixture
def h2_hamiltonian():
    return SparsePauliOp.from_list(H2_HAMILTONIAN)


@pytest.fixture
def h2_circuit(h2_hamiltonian):
    """Optimized H2 ansatz circuit."""
    n_qubits = h2_hamiltonian.num_qubits
    ansatz = EfficientSU2(n_qubits, su2_gates=["ry", "rz"], entanglement="full", reps=2)
    # Use fixed parameters for deterministic tests
    params = np.array([0.1, -0.2, 0.3, -0.1, 0.2, -0.3, 0.15, -0.15,
                       0.05, -0.05, 0.25, -0.25][:ansatz.num_parameters])
    return ansatz.assign_parameters(dict(zip(ansatz.parameters, params)))


@pytest.mark.timeout(60)
def test_pec_config():
    """Test PECConfig defaults and serialization."""
    config = PECConfig()
    assert config.num_pec_samples == 500
    assert config.noise_model_type == "sparse_pauli_lindblad"
    assert config.default_shots == 4096


@pytest.mark.timeout(60)
def test_pec_simulator_h2(pec, h2_circuit, h2_hamiltonian):
    """Test PEC execution on H2 with simulator."""
    result = pec.run_pec(h2_circuit, h2_hamiltonian, num_samples=50, seed=42)

    assert isinstance(result, dict)
    assert "pec_energy" in result
    assert "raw_energy" in result
    assert "overhead_factor" in result
    assert "variance" in result
    assert "num_samples" in result
    assert result["num_samples"] == 50
    # Energy should be finite
    assert np.isfinite(result["pec_energy"])
    assert np.isfinite(result["raw_energy"])


@pytest.mark.timeout(60)
def test_pec_noise_learning(pec, h2_circuit):
    """Test noise model learning produces valid structure."""
    noise_model = pec.learn_noise_model(h2_circuit)

    assert isinstance(noise_model, dict)
    assert "n_qubits" in noise_model
    assert "gamma" in noise_model
    assert "overhead_factor" in noise_model
    assert "channels" in noise_model
    assert noise_model["gamma"] >= 1.0  # Gamma is always >= 1
    assert noise_model["overhead_factor"] >= 1.0


@pytest.mark.timeout(60)
def test_pec_qpd(pec, h2_circuit, h2_hamiltonian):
    """Test quasi-probability decomposition."""
    noise_model = pec.learn_noise_model(h2_circuit)
    qpd = pec.build_quasi_probability_decomposition(noise_model, h2_circuit)

    assert isinstance(qpd, dict)
    assert "decompositions" in qpd
    assert "gamma" in qpd
    assert "sign_ratio" in qpd
    assert 0.0 <= qpd["sign_ratio"] <= 1.0


@pytest.mark.timeout(120)
def test_pec_vs_zne(pec, h2_circuit, h2_hamiltonian):
    """Test PEC vs ZNE comparison."""
    comparison = pec.compare_with_zne(h2_circuit, h2_hamiltonian, num_samples=30, seed=42)

    assert "pec" in comparison
    assert "zne" in comparison
    assert "raw" in comparison
    assert "exact_energy" in comparison
    # Both should produce finite energies
    assert np.isfinite(comparison["pec"]["energy"])
    assert np.isfinite(comparison["zne"]["energy"])


@pytest.mark.timeout(120)
def test_pec_h2_benchmark(pec):
    """Test complete H2 benchmark."""
    result = pec.run_h2_benchmark(use_4qubit=False, seed=42)

    assert "molecule" in result
    assert result["molecule"] == "H2"
    assert "pec" in result
    assert "zne" in result
    assert result["n_qubits"] == 2


@pytest.mark.timeout(60)
def test_pec_returns_correct_format(pec, h2_circuit, h2_hamiltonian):
    """Validate PEC result dict has all expected fields."""
    result = pec.run_pec(h2_circuit, h2_hamiltonian, num_samples=20, seed=42)

    expected_keys = [
        "raw_energy", "pec_energy", "exact_energy",
        "raw_error_ha", "pec_error_ha",
        "raw_error_kcal_mol", "pec_error_kcal_mol",
        "improvement_ratio", "overhead_factor",
        "sign_problem_ratio", "num_samples",
        "variance", "chemical_accuracy",
        "runtime_seconds", "config",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"


@pytest.mark.timeout(60)
def test_pec_reproducibility(pec, h2_circuit, h2_hamiltonian):
    """Test that same seed produces same results."""
    r1 = pec.run_pec(h2_circuit, h2_hamiltonian, num_samples=20, seed=123)
    r2 = pec.run_pec(h2_circuit, h2_hamiltonian, num_samples=20, seed=123)

    assert r1["pec_energy"] == r2["pec_energy"]
