# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum validation benchmark for BioQL.

This module provides quantum circuit execution and validation using IBM Quantum services.
It creates toy quantum circuits, executes them on real quantum hardware, and analyzes
the results to compute entropy and correlations.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_quantum_validation(target_name: str) -> Dict[str, Any]:
    """
    Run quantum validation benchmark on IBM Quantum hardware.

    Args:
        target_name: Name of the target (used for artifact naming)

    Returns:
        Dictionary containing:
        - quantum_skipped: bool indicating if quantum execution was skipped
        - backend_name: Name of the quantum backend used (if executed)
        - job_id: IBM Quantum job ID (if executed)
        - runtime_seconds: Execution time in seconds (if executed)
        - shannon_entropy: Shannon entropy of measurement results (if executed)
        - bit_correlations: Correlation metrics between qubits (if executed)
        - error: Error message (if failed)
    """
    # Check for IBM Quantum token
    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        logger.warning("IBM_QUANTUM_TOKEN not found in environment. Skipping quantum validation.")
        return {"quantum_skipped": True, "reason": "Missing IBM_QUANTUM_TOKEN"}

    try:
        # Import quantum libraries (after token check to fail fast)
        from qiskit import QuantumCircuit
        from qiskit_ibm_runtime import Options, QiskitRuntimeService, Sampler

        logger.info(f"Starting quantum validation for target: {target_name}")
        start_time = time.time()

        # Initialize runtime service
        logger.info("Connecting to IBM Quantum services...")
        service = QiskitRuntimeService(channel="ibm_quantum", token=token)

        # Select backend (prefer ibm_torino, else least busy)
        backend_name = _select_backend(service)
        logger.info(f"Selected backend: {backend_name}")
        backend = service.backend(backend_name)

        # Create toy quantum circuit
        num_qubits = 4  # Using 4 qubits for good balance
        circuit = _create_toy_circuit(num_qubits)
        logger.info(f"Created quantum circuit with {num_qubits} qubits")

        # Execute circuit with Sampler
        logger.info("Submitting job to quantum backend...")
        options = Options()
        options.execution.shots = 5000

        sampler = Sampler(backend=backend, options=options)
        job = sampler.run(circuit)
        job_id = job.job_id()
        logger.info(f"Job submitted with ID: {job_id}")

        # Wait for results
        logger.info("Waiting for job to complete...")
        result = job.result()

        # Extract measurement counts
        quasi_dists = result.quasi_dists[0]
        counts = _quasi_dist_to_counts(quasi_dists, shots=5000)

        runtime_seconds = time.time() - start_time
        logger.info(f"Job completed in {runtime_seconds:.2f} seconds")

        # Calculate metrics
        shannon_entropy = _calculate_shannon_entropy(counts)
        bit_correlations = _calculate_bit_correlations(counts, num_qubits)

        logger.info(f"Shannon entropy: {shannon_entropy:.4f}")
        logger.info(f"Bit correlations computed: {len(bit_correlations)} pairs")

        # Save artifacts
        _save_artifacts(target_name, counts, backend_name, job_id, runtime_seconds)
        logger.info("Artifacts saved successfully")

        return {
            "quantum_skipped": False,
            "backend_name": backend_name,
            "job_id": job_id,
            "runtime_seconds": runtime_seconds,
            "shannon_entropy": shannon_entropy,
            "bit_correlations": bit_correlations,
            "num_qubits": num_qubits,
            "total_shots": 5000,
        }

    except ImportError as e:
        logger.error(f"Failed to import quantum libraries: {e}")
        return {"quantum_skipped": True, "reason": "Missing quantum dependencies", "error": str(e)}
    except Exception as e:
        logger.error(f"Quantum validation failed: {e}", exc_info=True)
        return {"quantum_skipped": True, "reason": "Execution error", "error": str(e)}


def _select_backend(service: Any) -> str:
    """
    Select the best available backend.

    Prefers ibm_torino if available and operational, otherwise selects
    the least busy operational backend.

    Args:
        service: QiskitRuntimeService instance

    Returns:
        Name of selected backend
    """
    try:
        # Try to get ibm_torino first
        try:
            backend = service.backend("ibm_torino")
            if backend.status().operational:
                logger.info("ibm_torino is available and operational")
                return "ibm_torino"
        except Exception:
            logger.info("ibm_torino not available")

        # Fall back to least busy operational backend
        logger.info("Finding least busy operational backend...")
        backends = service.backends(
            filters=lambda x: x.configuration().n_qubits >= 4
            and not x.configuration().simulator
            and x.status().operational
        )

        if not backends:
            raise RuntimeError("No operational backends available")

        # Sort by pending jobs to find least busy
        least_busy = min(backends, key=lambda b: b.status().pending_jobs)
        return least_busy.name

    except Exception as e:
        logger.warning(f"Error selecting backend: {e}. Using fallback.")
        # Fallback to any operational backend
        backends = service.backends(operational=True, simulator=False)
        if backends:
            return backends[0].name
        raise RuntimeError("No operational quantum backends available")


def _create_toy_circuit(num_qubits: int) -> Any:
    """
    Create a toy quantum circuit with H, CX, and Ry gates.

    The circuit creates entanglement and applies rotations to produce
    interesting quantum correlations.

    Args:
        num_qubits: Number of qubits (2-6)

    Returns:
        QuantumCircuit instance
    """
    from qiskit import QuantumCircuit

    if not 2 <= num_qubits <= 6:
        raise ValueError("num_qubits must be between 2 and 6")

    circuit = QuantumCircuit(num_qubits, num_qubits)

    # Apply Hadamard gates to create superposition
    for i in range(num_qubits):
        circuit.h(i)

    # Create entanglement with CX gates
    for i in range(num_qubits - 1):
        circuit.cx(i, i + 1)

    # Add some rotation gates for variety
    angles = [np.pi / 4, np.pi / 3, np.pi / 2, 2 * np.pi / 3, 3 * np.pi / 4, 5 * np.pi / 6]
    for i in range(num_qubits):
        circuit.ry(angles[i % len(angles)], i)

    # Add another layer of entanglement
    for i in range(num_qubits - 1, 0, -1):
        circuit.cx(i, i - 1)

    # Measure all qubits
    circuit.measure(range(num_qubits), range(num_qubits))

    return circuit


def _quasi_dist_to_counts(quasi_dist: Dict[int, float], shots: int) -> Dict[str, int]:
    """
    Convert quasi-probability distribution to counts dictionary.

    Args:
        quasi_dist: Quasi-probability distribution from Sampler
        shots: Total number of shots

    Returns:
        Dictionary mapping bitstrings to counts
    """
    counts = {}
    for outcome, probability in quasi_dist.items():
        # Convert integer outcome to bitstring
        bitstring = bin(outcome)[2:]  # Remove '0b' prefix
        # Estimate count from probability
        count = int(probability * shots)
        if count > 0:
            counts[bitstring] = count
    return counts


def _calculate_shannon_entropy(counts: Dict[str, int]) -> float:
    """
    Calculate Shannon entropy of measurement distribution.

    H = -Σ p(x) * log2(p(x))

    Args:
        counts: Dictionary mapping bitstrings to counts

    Returns:
        Shannon entropy in bits
    """
    total_shots = sum(counts.values())
    if total_shots == 0:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        if count > 0:
            probability = count / total_shots
            entropy -= probability * np.log2(probability)

    return float(entropy)


def _calculate_bit_correlations(counts: Dict[str, int], num_qubits: int) -> Dict[str, float]:
    """
    Calculate correlations between qubit pairs.

    For each pair of qubits, calculates the mutual information:
    I(X;Y) = H(X) + H(Y) - H(X,Y)

    Args:
        counts: Dictionary mapping bitstrings to counts
        num_qubits: Number of qubits in the circuit

    Returns:
        Dictionary mapping qubit pairs to correlation values
    """
    total_shots = sum(counts.values())
    if total_shots == 0:
        return {}

    correlations = {}

    # Normalize bitstrings to have consistent length
    normalized_counts = {}
    for bitstring, count in counts.items():
        # Pad with leading zeros if needed
        padded = bitstring.zfill(num_qubits)
        normalized_counts[padded] = count

    # Calculate correlation for each pair of qubits
    for i in range(num_qubits):
        for j in range(i + 1, num_qubits):
            # Calculate marginal distributions
            counts_i = {}
            counts_j = {}
            counts_ij = {}

            for bitstring, count in normalized_counts.items():
                # Extract bits (reversed because Qiskit uses little-endian)
                bit_i = bitstring[-(i + 1)]
                bit_j = bitstring[-(j + 1)]

                counts_i[bit_i] = counts_i.get(bit_i, 0) + count
                counts_j[bit_j] = counts_j.get(bit_j, 0) + count
                counts_ij[f"{bit_i}{bit_j}"] = counts_ij.get(f"{bit_i}{bit_j}", 0) + count

            # Calculate entropies
            h_i = _calculate_shannon_entropy(counts_i)
            h_j = _calculate_shannon_entropy(counts_j)
            h_ij = _calculate_shannon_entropy(counts_ij)

            # Mutual information
            mutual_info = h_i + h_j - h_ij
            correlations[f"q{i}_q{j}"] = float(mutual_info)

    return correlations


def _save_artifacts(
    target_name: str, counts: Dict[str, int], backend_name: str, job_id: str, runtime_seconds: float
) -> None:
    """
    Save quantum validation artifacts to disk.

    Args:
        target_name: Name of the target
        counts: Measurement counts
        backend_name: Name of quantum backend
        job_id: IBM Quantum job ID
        runtime_seconds: Execution time in seconds
    """
    # Create artifacts directory
    artifacts_dir = Path("/Users/heinzjungbluth/Desktop/artifacts/quantum")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Save counts
    counts_file = artifacts_dir / f"counts_{target_name}.json"
    with open(counts_file, "w") as f:
        json.dump(counts, f, indent=2)

    # Save metadata
    meta_file = artifacts_dir / "meta.json"
    metadata = {
        "target_name": target_name,
        "backend_name": backend_name,
        "job_id": job_id,
        "runtime_seconds": runtime_seconds,
        "timestamp": time.time(),
        "shots": 5000,
    }
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved counts to: {counts_file}")
    logger.info(f"Saved metadata to: {meta_file}")


if __name__ == "__main__":
    # Example usage
    result = run_quantum_validation("test_target")
    print(json.dumps(result, indent=2))
