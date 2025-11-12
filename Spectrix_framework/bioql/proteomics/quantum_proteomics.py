#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum Circuits for Proteomics - v6.0.0
"""

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import RealAmplitudes, ZZFeatureMap

    HAVE_QISKIT = True
except ImportError:
    HAVE_QISKIT = False


def secondary_structure_circuit(sequence: str) -> "QuantumCircuit":
    """Create quantum circuit for secondary structure prediction."""
    if not HAVE_QISKIT:
        raise ImportError("Qiskit required")

    num_qubits = 8
    qc = QuantumCircuit(num_qubits)
    feature_map = ZZFeatureMap(num_qubits, reps=2)
    qc.compose(feature_map, inplace=True)
    qc.measure_all()
    return qc


def ppi_affinity_circuit(protein_a: str, protein_b: str) -> "QuantumCircuit":
    """Create quantum circuit for PPI affinity calculation."""
    if not HAVE_QISKIT:
        raise ImportError("Qiskit required")

    num_qubits = 10
    qc = QuantumCircuit(num_qubits)
    ansatz = RealAmplitudes(num_qubits, reps=3)
    qc.compose(ansatz, inplace=True)
    qc.measure_all()
    return qc


def protein_feature_map(sequence: str, num_qubits: int = 8) -> "QuantumCircuit":
    """Create quantum feature map for protein sequence."""
    if not HAVE_QISKIT:
        raise ImportError("Qiskit required")

    qc = QuantumCircuit(num_qubits)
    feature_map = ZZFeatureMap(num_qubits, reps=2)
    qc.compose(feature_map, inplace=True)
    return qc
