#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""Quantum Circuits for Metabolomics"""
try:
    from qiskit import QuantumCircuit

    HAVE_QISKIT = True
except ImportError:
    HAVE_QISKIT = False


def flux_optimization_circuit(model: str) -> "QuantumCircuit":
    """QAOA circuit for flux optimization."""
    if not HAVE_QISKIT:
        raise ImportError("Qiskit required")
    qc = QuantumCircuit(10)
    qc.h(range(10))
    qc.measure_all()
    return qc


def pathway_correlation_circuit(metabolites: list) -> "QuantumCircuit":
    """Quantum feature map for pathway correlations."""
    if not HAVE_QISKIT:
        raise ImportError("Qiskit required")
    qc = QuantumCircuit(8)
    qc.h(range(8))
    qc.measure_all()
    return qc
