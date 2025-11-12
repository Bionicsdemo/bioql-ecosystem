"""
Quantum energy collapse estimation for gRNA-DNA interactions

Estimates binding affinity between guide RNA and target DNA using:
- Quantum Ising model
- Multiple backend support (simulator, Braket, Qiskit)
- Energy-based scoring
- Classical baseline calibration
- Statistical uncertainty quantification
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from .featurization import encode_guide_sequence
from .adapters.base import QuantumEngine
from .adapters.simulator import LocalSimulatorEngine


def compute_classical_baseline(
    guide_seq: str,
    coupling_strength: float = 1.0
) -> float:
    """
    Compute classical Ising energy baseline (no quantum effects)

    Uses mean-field approximation: all spins aligned to minimize energy

    Args:
        guide_seq: Guide RNA sequence
        coupling_strength: Base-pair coupling strength

    Returns:
        Classical baseline energy (lower bound)

    Example:
        >>> baseline = compute_classical_baseline("ATCGAAGTC")
        >>> print(f"Classical baseline: {baseline:.3f}")
    """
    angles = encode_guide_sequence(guide_seq)
    n = len(angles)

    # Classical ground state: all spins aligned
    # H = Σ h_i Z_i + Σ J_ij Z_i Z_j
    # For aligned spins (all +1 or all -1), minimize:
    h_fields = np.cos(angles)

    # Energy if all spins = +1
    energy_plus = np.sum(h_fields) + coupling_strength * (n - 1)

    # Energy if all spins = -1
    energy_minus = -np.sum(h_fields) + coupling_strength * (n - 1)

    # Return minimum (classical ground state)
    return min(energy_plus, energy_minus)


def generate_decoy_sequences(
    guide_seq: str,
    num_decoys: int = 10,
    mutation_rate: float = 0.3,
    seed: Optional[int] = None
) -> List[str]:
    """
    Generate decoy guide sequences with random mutations

    Used as negative controls for z-score calibration

    Args:
        guide_seq: Reference guide sequence
        num_decoys: Number of decoys to generate
        mutation_rate: Fraction of positions to mutate (0-1)
        seed: Random seed

    Returns:
        List of decoy sequences

    Example:
        >>> decoys = generate_decoy_sequences("ATCGAAGTC", num_decoys=5)
        >>> print(decoys[0])
        ATGGAACTC
    """
    if seed is not None:
        np.random.seed(seed)

    bases = ['A', 'T', 'C', 'G']
    decoys = []

    for _ in range(num_decoys):
        decoy = list(guide_seq)
        num_mutations = max(1, int(len(guide_seq) * mutation_rate))
        positions = np.random.choice(len(guide_seq), num_mutations, replace=False)

        for pos in positions:
            # Mutate to different base
            current_base = decoy[pos]
            new_base = np.random.choice([b for b in bases if b != current_base])
            decoy[pos] = new_base

        decoys.append(''.join(decoy))

    return decoys


def compute_normalized_energy(
    energy: float,
    classical_baseline: float,
    decoy_energies: List[float]
) -> Dict[str, float]:
    """
    Compute normalized energy metrics vs classical baseline and decoys

    Args:
        energy: Quantum energy estimate
        classical_baseline: Classical Ising baseline
        decoy_energies: Energies from decoy sequences

    Returns:
        {
            'delta_E_classical': Energy - classical_baseline,
            'z_score': (Energy - mean(decoys)) / std(decoys),
            'percentile': Percentile rank vs decoys (0-100)
        }

    Example:
        >>> metrics = compute_normalized_energy(-5.2, -8.0, [-3.1, -2.8, -3.5])
        >>> print(f"ΔE vs classical: {metrics['delta_E_classical']:.2f}")
        >>> print(f"Z-score: {metrics['z_score']:.2f}")
    """
    # ΔE vs classical baseline
    delta_E = energy - classical_baseline

    # Z-score vs decoys
    if len(decoy_energies) > 0:
        decoy_mean = np.mean(decoy_energies)
        decoy_std = np.std(decoy_energies)

        if decoy_std > 1e-6:
            z_score = (energy - decoy_mean) / decoy_std
        else:
            z_score = 0.0

        # Percentile: what % of decoys have higher energy
        percentile = 100 * np.mean([e >= energy for e in decoy_energies])
    else:
        z_score = 0.0
        percentile = 50.0

    return {
        'delta_E_classical': float(delta_E),
        'z_score': float(z_score),
        'percentile_vs_decoys': float(percentile)
    }


def estimate_with_uncertainty(
    guide_seq: str,
    engine: QuantumEngine,
    coupling_strength: float = 1.0,
    num_repeats: int = 5
) -> Dict[str, Any]:
    """
    Estimate energy with statistical uncertainty (multiple runs)

    Args:
        guide_seq: Guide RNA sequence
        engine: Quantum engine
        coupling_strength: Base-pair coupling strength
        num_repeats: Number of independent runs

    Returns:
        {
            'energy_mean': Mean energy,
            'energy_std': Standard deviation,
            'energy_sem': Standard error of mean,
            'confidence_mean': Mean confidence,
            'all_energies': List of individual energies,
            'backend': Backend name
        }

    Example:
        >>> from bioql.crispr_qai.adapters import LocalSimulatorEngine
        >>> engine = LocalSimulatorEngine(shots=1000)
        >>> result = estimate_with_uncertainty("ATCGAAGTC", engine, num_repeats=5)
        >>> print(f"Energy: {result['energy_mean']:.3f} ± {result['energy_std']:.3f}")
    """
    angles = encode_guide_sequence(guide_seq)

    energies = []
    confidences = []

    for _ in range(num_repeats):
        result = engine.run_energy_estimation(
            angles=angles,
            coupling_strength=coupling_strength
        )
        energies.append(result['energy_estimate'])
        confidences.append(result['confidence'])

    energies = np.array(energies)
    confidences = np.array(confidences)

    return {
        'energy_mean': float(np.mean(energies)),
        'energy_std': float(np.std(energies, ddof=1)),
        'energy_sem': float(np.std(energies, ddof=1) / np.sqrt(num_repeats)),
        'confidence_mean': float(np.mean(confidences)),
        'confidence_std': float(np.std(confidences, ddof=1)),
        'all_energies': energies.tolist(),
        'all_confidences': confidences.tolist(),
        'num_repeats': num_repeats,
        'backend': engine.backend_name,
        'guide_sequence': guide_seq
    }


def estimate_energy_collapse_simulator(
    guide_seq: str,
    coupling_strength: float = 1.0,
    shots: int = 1000,
    seed: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Estimate gRNA-DNA binding energy using local simulator

    Args:
        guide_seq: Guide RNA sequence (e.g., "ATCGAAGTC")
        coupling_strength: Base-pair coupling strength (default: 1.0)
        shots: Number of quantum measurements
        seed: Random seed for reproducibility
        metadata: Optional metadata (guide_id, target, etc.)

    Returns:
        {
            'energy_estimate': float,     # Estimated binding energy
            'confidence': float,          # Measurement confidence (0-1)
            'runtime_seconds': float,     # Execution time
            'backend': str,               # 'local_simulator'
            'guide_sequence': str,        # Original sequence
            'num_qubits': int,            # Circuit size
            'metadata': dict              # Original metadata
        }

    Example:
        >>> result = estimate_energy_collapse_simulator("ATCGAAGTC", shots=1000)
        >>> print(f"Energy: {result['energy_estimate']:.3f}")
        Energy: -2.456
    """
    # Encode sequence to angles
    angles = encode_guide_sequence(guide_seq)

    # Create simulator engine
    engine = LocalSimulatorEngine(shots=shots, seed=seed)

    # Run energy estimation
    result = engine.run_energy_estimation(
        angles=angles,
        coupling_strength=coupling_strength,
        metadata=metadata
    )

    # Add sequence info
    result['guide_sequence'] = guide_seq
    result['num_qubits'] = len(angles)

    return result


def estimate_energy_collapse_braket(
    guide_seq: str,
    backend_name: str = "SV1",
    coupling_strength: float = 1.0,
    shots: int = 1000,
    aws_region: str = "us-east-1",
    s3_bucket: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Estimate gRNA-DNA binding energy using AWS Braket

    Args:
        guide_seq: Guide RNA sequence
        backend_name: Braket device ('SV1', 'DM1', 'Aspen-M', 'Harmony')
        coupling_strength: Base-pair coupling strength
        shots: Number of measurements
        aws_region: AWS region
        s3_bucket: S3 bucket (required for hardware)
        metadata: Optional metadata

    Returns:
        Energy estimation results (same format as simulator)

    Example:
        >>> result = estimate_energy_collapse_braket(
        ...     "ATCGAAGTC",
        ...     backend_name="SV1",
        ...     shots=1000
        ... )
    """
    from .adapters.braket_adapter import BraketEngine

    # Encode sequence
    angles = encode_guide_sequence(guide_seq)

    # Create Braket engine
    engine = BraketEngine(
        backend_name=backend_name,
        shots=shots,
        aws_region=aws_region,
        s3_bucket=s3_bucket
    )

    # Validate backend
    if not engine.validate_backend():
        raise RuntimeError(f"Braket backend {backend_name} not available")

    # Run energy estimation
    result = engine.run_energy_estimation(
        angles=angles,
        coupling_strength=coupling_strength,
        metadata=metadata
    )

    # Add sequence info
    result['guide_sequence'] = guide_seq
    result['num_qubits'] = len(angles)

    return result


def estimate_energy_collapse_qiskit(
    guide_seq: str,
    backend_name: str = "aer_simulator",
    coupling_strength: float = 1.0,
    shots: int = 1000,
    ibm_token: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Estimate gRNA-DNA binding energy using IBM Qiskit

    Args:
        guide_seq: Guide RNA sequence
        backend_name: Qiskit backend ('aer_simulator', 'ibm_torino', etc.)
        coupling_strength: Base-pair coupling strength
        shots: Number of measurements
        ibm_token: IBM Quantum token (required for hardware)
        metadata: Optional metadata

    Returns:
        Energy estimation results (same format as simulator)

    Example:
        >>> result = estimate_energy_collapse_qiskit(
        ...     "ATCGAAGTC",
        ...     backend_name="aer_simulator",
        ...     shots=1000
        ... )
    """
    from .adapters.qiskit_adapter import QiskitEngine

    # Encode sequence
    angles = encode_guide_sequence(guide_seq)

    # Create Qiskit engine
    engine = QiskitEngine(
        backend_name=backend_name,
        shots=shots,
        ibm_token=ibm_token
    )

    # Validate backend
    if not engine.validate_backend():
        raise RuntimeError(f"Qiskit backend {backend_name} not available")

    # Run energy estimation
    result = engine.run_energy_estimation(
        angles=angles,
        coupling_strength=coupling_strength,
        metadata=metadata
    )

    # Add sequence info
    result['guide_sequence'] = guide_seq
    result['num_qubits'] = len(angles)

    return result


def estimate_energy_custom(
    guide_seq: str,
    engine: QuantumEngine,
    coupling_strength: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Estimate energy using custom quantum engine

    Args:
        guide_seq: Guide RNA sequence
        engine: Custom QuantumEngine instance
        coupling_strength: Base-pair coupling strength
        metadata: Optional metadata

    Returns:
        Energy estimation results

    Example:
        >>> from bioql.crispr_qai.adapters import LocalSimulatorEngine
        >>> engine = LocalSimulatorEngine(shots=5000, seed=42)
        >>> result = estimate_energy_custom("ATCGAAGTC", engine)
    """
    # Encode sequence
    angles = encode_guide_sequence(guide_seq)

    # Validate backend
    if not engine.validated and not engine.validate_backend():
        raise RuntimeError(f"Engine {engine.backend_name} not available")

    # Run energy estimation
    result = engine.run_energy_estimation(
        angles=angles,
        coupling_strength=coupling_strength,
        metadata=metadata
    )

    # Add sequence info
    result['guide_sequence'] = guide_seq
    result['num_qubits'] = len(angles)

    return result


def batch_energy_estimation(
    guide_sequences: List[str],
    engine: Optional[QuantumEngine] = None,
    coupling_strength: float = 1.0,
    shots: int = 1000
) -> List[Dict[str, Any]]:
    """
    Estimate energies for multiple guide sequences

    Args:
        guide_sequences: List of guide RNA sequences
        engine: Quantum engine (defaults to LocalSimulatorEngine)
        coupling_strength: Base-pair coupling strength
        shots: Number of measurements per guide

    Returns:
        List of energy estimation results

    Example:
        >>> guides = ["ATCGAAGTC", "GCTAGCTA", "TTAACCGG"]
        >>> results = batch_energy_estimation(guides, shots=1000)
        >>> for r in results:
        ...     print(f"{r['guide_sequence']}: {r['energy_estimate']:.3f}")
    """
    if engine is None:
        engine = LocalSimulatorEngine(shots=shots)

    results = []

    for guide_seq in guide_sequences:
        result = estimate_energy_custom(
            guide_seq=guide_seq,
            engine=engine,
            coupling_strength=coupling_strength
        )
        results.append(result)

    return results
