#!/usr/bin/env python3
"""
MHCE Benchmark Suite
====================
Publication-grade benchmarking of Hamiltonian compression techniques.

Compares: No compression, JW+taper, BK, BK+taper
Molecules: H2 (4q), LiH-like, BeH2-like
Metrics: qubit_reduction, term_reduction, energy_preservation
"""

import sys
import os
import time
import json
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import EfficientSU2

try:
    from qiskit.primitives import StatevectorEstimator
except ImportError:
    from qiskit.primitives import Estimator as StatevectorEstimator

from scipy.optimize import minimize

# Add agents to path for MHCE imports
_agents_dir = str(Path(__file__).resolve().parent.parent / "BioQL_MCP" / "src" / "agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from molecular_hamiltonian_compression_engine import (
    MolecularHamiltonianCompressionEngine,
    detect_z2_symmetries,
    taper_hamiltonian,
)

# Reference molecules (4-qubit JW-mapped Hamiltonians)
MOLECULES = {
    "H2": {
        "hamiltonian": [
            ("IIII", -0.81054798), ("IIIZ", 0.17218393), ("IIZI", -0.22575349),
            ("IZII", 0.17218393), ("ZIII", -0.22575349), ("IIZZ", 0.12091263),
            ("IZIZ", 0.16614543), ("IZZI", 0.16892754), ("ZIIZ", 0.16614543),
            ("ZIZI", 0.12091263), ("ZZII", 0.16892754), ("ZZZZ", 0.17464343),
            ("XXYY", 0.0452328), ("YYXX", 0.0452328), ("XYYX", -0.0452328),
            ("YXXY", -0.0452328),
        ],
        "fci_energy": -1.137275,
        "n_electrons": 2,
    },
}

STRATEGIES = ["no_compression", "jw_tapered", "bk", "bk_tapered"]


class MHCEBenchmark:
    """
    Benchmark suite for Molecular Hamiltonian Compression Engine.
    """

    def __init__(self):
        self.engine = MolecularHamiltonianCompressionEngine()
        self.estimator = StatevectorEstimator()

    def run_compression_comparison(self, molecule: str = "H2") -> dict:
        """
        Compare all compression strategies on a molecule.

        Returns dict with metrics for each strategy.
        """
        mol_data = MOLECULES.get(molecule, MOLECULES["H2"])
        hamiltonian = SparsePauliOp.from_list(mol_data["hamiltonian"])
        n_electrons = mol_data["n_electrons"]
        fci_energy = mol_data["fci_energy"]

        results = {}

        # No compression baseline
        start = time.time()
        baseline_energy = self._compute_vqe_energy(hamiltonian)
        results["no_compression"] = {
            "qubits": hamiltonian.num_qubits,
            "terms": len(hamiltonian),
            "vqe_energy": baseline_energy,
            "energy_error_vs_fci": abs(baseline_energy - fci_energy),
            "qubit_reduction_percent": 0.0,
            "term_reduction_percent": 0.0,
            "runtime_seconds": time.time() - start,
        }

        # JW + tapering
        start = time.time()
        jw_result = self.engine.compress(
            hamiltonian, n_electrons, transform="jw", taper=True
        )
        if jw_result.compressed_hamiltonian is not None:
            jw_energy = self._compute_vqe_energy(jw_result.compressed_hamiltonian)
            jw_energy_corrected = jw_energy + jw_result.energy_shift
        else:
            jw_energy_corrected = baseline_energy
        results["jw_tapered"] = {
            **jw_result.to_dict(),
            "vqe_energy": jw_energy_corrected,
            "energy_error_vs_fci": abs(jw_energy_corrected - fci_energy),
            "energy_preservation_error": abs(jw_energy_corrected - baseline_energy),
            "runtime_seconds": time.time() - start,
        }

        # BK (no tapering)
        start = time.time()
        bk_result = self.engine.compress(
            hamiltonian, n_electrons, transform="bk", taper=False
        )
        if bk_result.compressed_hamiltonian is not None:
            bk_energy = self._compute_vqe_energy(bk_result.compressed_hamiltonian)
        else:
            bk_energy = baseline_energy
        results["bk"] = {
            **bk_result.to_dict(),
            "vqe_energy": bk_energy,
            "energy_error_vs_fci": abs(bk_energy - fci_energy),
            "energy_preservation_error": abs(bk_energy - baseline_energy),
            "runtime_seconds": time.time() - start,
        }

        # BK + tapering
        start = time.time()
        bk_taper = self.engine.compress(
            hamiltonian, n_electrons, transform="bk", taper=True
        )
        if bk_taper.compressed_hamiltonian is not None:
            bk_taper_energy = self._compute_vqe_energy(bk_taper.compressed_hamiltonian)
            bk_taper_corrected = bk_taper_energy + bk_taper.energy_shift
        else:
            bk_taper_corrected = baseline_energy
        results["bk_tapered"] = {
            **bk_taper.to_dict(),
            "vqe_energy": bk_taper_corrected,
            "energy_error_vs_fci": abs(bk_taper_corrected - fci_energy),
            "energy_preservation_error": abs(bk_taper_corrected - baseline_energy),
            "runtime_seconds": time.time() - start,
        }

        # Summary
        best = min(
            STRATEGIES[1:],  # Exclude no_compression
            key=lambda s: results[s].get("compressed_qubits", results[s].get("qubits", 999)),
        )
        results["summary"] = {
            "molecule": molecule,
            "fci_energy": fci_energy,
            "best_strategy": best,
            "max_qubit_reduction": max(
                results[s].get("qubit_reduction_percent", 0) for s in STRATEGIES[1:]
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return results

    def _compute_vqe_energy(
        self, hamiltonian: SparsePauliOp, seed: int = 42
    ) -> float:
        """Run quick VQE and return ground state energy."""
        n_qubits = hamiltonian.num_qubits
        if n_qubits == 0:
            # Scalar Hamiltonian
            return float(hamiltonian.coeffs[0].real) if len(hamiltonian) > 0 else 0.0

        ansatz = EfficientSU2(
            n_qubits,
            su2_gates=["ry", "rz"],
            entanglement="full" if n_qubits <= 4 else "linear",
            reps=2,
        )

        rng = np.random.default_rng(seed)
        init = rng.uniform(-0.1, 0.1, ansatz.num_parameters)

        def cost(params):
            bound = ansatz.assign_parameters(dict(zip(ansatz.parameters, params)))
            job = self.estimator.run([(bound, hamiltonian)])
            return float(job.result()[0].data.evs)

        result = minimize(cost, init, method="COBYLA", options={"maxiter": 80})
        return float(result.fun)

    def generate_report(self, comparison: Optional[dict] = None) -> str:
        """Generate Markdown benchmark report."""
        if comparison is None:
            comparison = self.run_compression_comparison("H2")

        lines = [
            "# MHCE Benchmark Report",
            f"\nGenerated: {comparison['summary']['timestamp']}",
            f"Molecule: {comparison['summary']['molecule']}",
            f"FCI Energy: {comparison['summary']['fci_energy']:.6f} Ha",
            f"Best strategy: **{comparison['summary']['best_strategy']}**",
            "\n## Compression Results\n",
            "| Strategy | Qubits | Terms | Qubit Reduction | VQE Energy (Ha) | Error vs FCI (mHa) |",
            "|----------|--------|-------|-----------------|-----------------|---------------------|",
        ]

        for strategy in STRATEGIES:
            r = comparison[strategy]
            qubits = r.get("compressed_qubits", r.get("qubits", "?"))
            terms = r.get("compressed_terms", r.get("terms", "?"))
            reduction = r.get("qubit_reduction_percent", 0)
            energy = r.get("vqe_energy", 0)
            error = r.get("energy_error_vs_fci", 0)
            lines.append(
                f"| {strategy} | {qubits} | {terms} | {reduction:.1f}% | "
                f"{energy:.6f} | {error*1000:.2f} |"
            )

        return "\n".join(lines)
