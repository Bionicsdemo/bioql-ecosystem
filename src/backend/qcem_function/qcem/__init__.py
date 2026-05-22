"""
QCEM — Quantum Compression-Enhanced Mitigation
================================================
A Qiskit-compatible function that combines molecular Hamiltonian compression
with composable error mitigation for quantum chemistry calculations.

Unlike standalone error mitigation (ZNE, PEC, TEM), QCEM first compresses
the Hamiltonian via Bravyi-Kitaev encoding and Z₂ symmetry tapering,
then applies a composable mitigation stack. Fewer qubits → less noise →
better mitigation → lower cost.

Usage:
    from qcem import QCEM

    qcem = QCEM()
    result = qcem.run(hamiltonian, ansatz, backend="ibm_boston")

    # Or with molecular SMILES
    result = qcem.run_molecule("O", basis="sto-3g", backend="ibm_boston")

By BioQL — Quantum Drug Discovery Platform
https://github.com/bioql
"""

__version__ = "0.1.0"

from .core import QCEM, QCEMResult, QCEMConfig
from .compression import compress_hamiltonian, CompressionResult
from .mitigation import mitigate, MitigationStack
from .benchmark import QCEMBenchmark

__all__ = [
    "QCEM",
    "QCEMResult",
    "QCEMConfig",
    "compress_hamiltonian",
    "CompressionResult",
    "mitigate",
    "MitigationStack",
    "QCEMBenchmark",
]
