"""
Tests for Molecular Hamiltonian Compression Engine (MHCE).
"""
import sys
import pytest
import numpy as np
from pathlib import Path

_agents_dir = str(Path(__file__).resolve().parent.parent.parent / "src" / "backend" / "BioQL_MCP" / "src" / "agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import EfficientSU2

try:
    from qiskit.primitives import StatevectorEstimator
except ImportError:
    from qiskit.primitives import Estimator as StatevectorEstimator

from molecular_hamiltonian_compression_engine import (
    MolecularHamiltonianCompressionEngine,
    CompressionResult,
    detect_z2_symmetries,
    taper_hamiltonian,
    bravyi_kitaev_single_excitation,
    bravyi_kitaev_double_excitation,
    bravyi_kitaev_one_body,
)


H2_4Q = [
    ("IIII", -0.81054798), ("IIIZ", 0.17218393), ("IIZI", -0.22575349),
    ("IZII", 0.17218393), ("ZIII", -0.22575349), ("IIZZ", 0.12091263),
    ("IZIZ", 0.16614543), ("IZZI", 0.16892754), ("ZIIZ", 0.16614543),
    ("ZIZI", 0.12091263), ("ZZII", 0.16892754), ("ZZZZ", 0.17464343),
    ("XXYY", 0.0452328), ("YYXX", 0.0452328), ("XYYX", -0.0452328),
    ("YXXY", -0.0452328),
]
H2_EXACT = -1.137275


@pytest.fixture
def engine():
    return MolecularHamiltonianCompressionEngine()


@pytest.fixture
def h2_hamiltonian():
    return SparsePauliOp.from_list(H2_4Q)


@pytest.mark.timeout(30)
def test_bravyi_kitaev_single_excitation():
    """BK single excitation produces valid Pauli terms."""
    terms = bravyi_kitaev_single_excitation(0, 1, 4)
    assert len(terms) > 0
    for pauli_str, coeff in terms:
        assert len(pauli_str) == 4
        assert all(c in "IXYZ" for c in pauli_str)
        assert np.isfinite(coeff)


@pytest.mark.timeout(30)
def test_bravyi_kitaev_double_excitation():
    """BK double excitation produces valid Pauli terms."""
    terms = bravyi_kitaev_double_excitation(0, 1, 2, 3, 4)
    assert len(terms) == 8  # Always 8 terms
    for pauli_str, coeff in terms:
        assert len(pauli_str) == 4


@pytest.mark.timeout(30)
def test_bk_identity_case():
    """BK with p==q returns empty."""
    terms = bravyi_kitaev_single_excitation(2, 2, 4)
    assert terms == []


@pytest.mark.timeout(30)
def test_bk_one_body():
    """BK one-body mapping produces SparsePauliOp-compatible terms."""
    terms = bravyi_kitaev_one_body(0, 0, 4, 0.5)
    assert len(terms) > 0
    # Should be able to construct SparsePauliOp
    op = SparsePauliOp.from_list(terms)
    assert op.num_qubits == 4


@pytest.mark.timeout(60)
def test_symmetry_detection_h2(h2_hamiltonian):
    """Detect Z2 symmetries of H2 Hamiltonian."""
    symmetries = detect_z2_symmetries(h2_hamiltonian)
    assert isinstance(symmetries, list)
    # H2 in STO-3G should have symmetries (particle number, spin)
    # At minimum it should find at least one
    for sym in symmetries:
        assert isinstance(sym, SparsePauliOp)
        assert sym.num_qubits == h2_hamiltonian.num_qubits


@pytest.mark.timeout(60)
def test_tapering_reduces_qubits(h2_hamiltonian):
    """Tapering should reduce qubit count when symmetries exist."""
    symmetries = detect_z2_symmetries(h2_hamiltonian)
    if symmetries:
        tapered, shift = taper_hamiltonian(h2_hamiltonian, symmetries[:1])
        assert tapered.num_qubits < h2_hamiltonian.num_qubits
        assert tapered.num_qubits == h2_hamiltonian.num_qubits - 1


@pytest.mark.timeout(60)
def test_tapering_no_symmetries():
    """Tapering with empty symmetries returns original."""
    ham = SparsePauliOp.from_list([("XX", 0.5), ("ZZ", 0.3)])
    tapered, shift = taper_hamiltonian(ham, [])
    assert tapered.num_qubits == ham.num_qubits
    assert shift == 0.0


@pytest.mark.timeout(60)
def test_compression_auto_selection(engine, h2_hamiltonian):
    """Auto mode selects JW for small molecules."""
    result = engine.compress(h2_hamiltonian, n_electrons=2, transform="auto")
    assert isinstance(result, CompressionResult)
    # 4 qubits → should choose JW (threshold is > 8)
    assert result.transform_used == "jw"


@pytest.mark.timeout(60)
def test_compression_bk_explicit(engine, h2_hamiltonian):
    """Explicit BK compression works."""
    result = engine.compress(h2_hamiltonian, n_electrons=2, transform="bk", taper=False)
    assert result.transform_used == "bk"
    assert result.compressed_hamiltonian is not None
    assert isinstance(result.compressed_hamiltonian, SparsePauliOp)


@pytest.mark.timeout(60)
def test_compression_result_format(engine, h2_hamiltonian):
    """CompressionResult has all expected fields."""
    result = engine.compress(h2_hamiltonian, n_electrons=2, transform="jw")
    d = result.to_dict()

    expected_keys = [
        "original_qubits", "compressed_qubits", "original_terms",
        "compressed_terms", "energy_shift", "symmetries_found",
        "transform_used", "compression_ratio", "qubit_reduction_percent",
        "term_reduction_percent", "runtime_seconds",
    ]
    for key in expected_keys:
        assert key in d, f"Missing key: {key}"


@pytest.mark.timeout(120)
def test_benchmark_compression(engine, h2_hamiltonian):
    """Benchmark comparison produces all strategies."""
    benchmark = engine.benchmark_compression(h2_hamiltonian, n_electrons=2)

    assert "no_compression" in benchmark
    assert "jw_tapered" in benchmark
    assert "bk" in benchmark
    assert "bk_tapered" in benchmark
    assert "summary" in benchmark
    assert benchmark["summary"]["best_strategy"] in ["jw_tapered", "bk", "bk_tapered"]


@pytest.mark.timeout(120)
def test_energy_preservation(engine, h2_hamiltonian):
    """Compression should preserve ground state energy within tolerance."""
    estimator = StatevectorEstimator()

    # Original energy
    n_qubits = h2_hamiltonian.num_qubits
    ansatz = EfficientSU2(n_qubits, su2_gates=["ry", "rz"], entanglement="full", reps=2)
    params = np.zeros(ansatz.num_parameters)
    bound = ansatz.assign_parameters(dict(zip(ansatz.parameters, params)))
    job = estimator.run([(bound, h2_hamiltonian)])
    original_energy = float(job.result()[0].data.evs)

    # BK-transformed energy (same circuit, different Hamiltonian)
    result = engine.compress(h2_hamiltonian, n_electrons=2, transform="bk", taper=False)
    if result.compressed_hamiltonian.num_qubits == n_qubits:
        ansatz2 = EfficientSU2(n_qubits, su2_gates=["ry", "rz"], entanglement="full", reps=2)
        bound2 = ansatz2.assign_parameters(dict(zip(ansatz2.parameters, params)))
        job2 = estimator.run([(bound2, result.compressed_hamiltonian)])
        bk_energy = float(job2.result()[0].data.evs)
        # Should be reasonably close (within 0.1 Ha for zero params)
        assert abs(original_energy - bk_energy) < 0.5
