"""
QCEM Core — Quantum Compression-Enhanced Mitigation
=====================================================
The main user-facing class that combines compression + mitigation
in a single call. This is the Qiskit Function entry point.

Usage:
    from qcem import QCEM

    # With a pre-built Hamiltonian
    qcem = QCEM()
    result = qcem.run(hamiltonian, ansatz, backend=backend)

    # With a molecule (requires PySCF)
    result = qcem.run_molecule("H 0 0 0; H 0 0 0.74", basis="sto-3g")

    # Compare compression strategies
    comparison = qcem.compare(hamiltonian, n_electrons=2)
"""

import time
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import EfficientSU2
from scipy.optimize import minimize

try:
    from qiskit.primitives import StatevectorEstimator
except ImportError:
    from qiskit.primitives import Estimator as StatevectorEstimator

from .compression import compress_hamiltonian, CompressionResult
from .mitigation import mitigate, MitigationStack, get_preset, PRESETS


@dataclass
class QCEMConfig:
    """Configuration for QCEM function."""
    compress: bool = True
    taper: bool = True
    mitigation_preset: str = "balanced"
    mitigation_stack: Optional[MitigationStack] = None
    optimization_maxiter: int = 300
    optimization_restarts: int = 5
    seed: int = 42


@dataclass
class QCEMResult:
    """Result from QCEM execution."""
    # Energies
    raw_energy: float
    mitigated_energy: float
    exact_energy: Optional[float]

    # Errors
    error_ha: Optional[float]
    error_mha: Optional[float]
    error_kcal_mol: Optional[float]
    chemical_accuracy: Optional[bool]

    # Compression
    compression: Dict[str, Any]

    # Mitigation
    mitigation: Dict[str, Any]

    # Meta
    total_runtime_s: float
    config: Dict[str, Any]

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            "QCEM Result",
            "=" * 40,
            f"Mitigated Energy:  {self.mitigated_energy:.6f} Ha",
        ]
        if self.exact_energy is not None:
            lines.append(f"Exact Energy:      {self.exact_energy:.6f} Ha")
            lines.append(f"Error:             {self.error_mha:.2f} mHa ({self.error_kcal_mol:.2f} kcal/mol)")
            lines.append(f"Chemical Accuracy: {'Yes' if self.chemical_accuracy else 'No'}")

        c = self.compression
        lines.append(f"\nCompression: {c.get('original_qubits', '?')} → {c.get('compressed_qubits', '?')} qubits "
                     f"({c.get('qubits_saved', 0)} saved, {c.get('symmetries_found', 0)} symmetries)")

        m = self.mitigation
        lines.append(f"Mitigation:  {', '.join(m.get('techniques_applied', []))}")
        lines.append(f"Runtime:     {self.total_runtime_s:.1f}s")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return asdict(self)


class QCEM:
    """
    Quantum Compression-Enhanced Mitigation (QCEM) Function.

    A Qiskit-compatible function that first compresses molecular Hamiltonians
    (Z₂ symmetry tapering → fewer qubits → shallower circuits) then applies
    composable error mitigation (DD + Twirling + ZNE/PEC + TREX + Layer Learning).

    The key insight: compression reduces the noise budget BEFORE mitigation,
    yielding compounding benefits unavailable to standalone mitigation methods.

    Args:
        config: QCEMConfig or None for defaults

    Example:
        >>> from qcem import QCEM
        >>> from qiskit.quantum_info import SparsePauliOp
        >>>
        >>> H = SparsePauliOp.from_list([
        ...     ("IIII", -0.81), ("IIIZ", 0.17), ("IIZI", -0.23),
        ...     ("IZII", 0.17), ("ZIII", -0.23), ("IIZZ", 0.12),
        ...     ("XXYY", 0.05), ("YYXX", 0.05),
        ... ])
        >>> qcem = QCEM()
        >>> result = qcem.run(H, n_electrons=2)
        >>> print(result.summary())
    """

    def __init__(self, config: Optional[QCEMConfig] = None):
        self.config = config or QCEMConfig()
        self._estimator = StatevectorEstimator()

    def run(
        self,
        hamiltonian: SparsePauliOp,
        n_electrons: int = 2,
        ansatz: Optional[QuantumCircuit] = None,
        backend: Any = None,
        exact_energy: Optional[float] = None,
    ) -> QCEMResult:
        """
        Run the full QCEM pipeline: compress → optimize → mitigate.

        Args:
            hamiltonian: Molecular Hamiltonian as SparsePauliOp
            n_electrons: Number of electrons in the molecule
            ansatz: Optional pre-built ansatz (auto-generated if None)
            backend: IBM Quantum backend (None for simulator)
            exact_energy: Known exact energy for error computation (auto-computed if None)

        Returns:
            QCEMResult with energies, errors, compression and mitigation details
        """
        start = time.time()

        # Step 1: Compute exact energy if not provided
        if exact_energy is None:
            exact_energy = float(np.linalg.eigvalsh(hamiltonian.to_matrix())[0])

        # Step 2: Compress
        if self.config.compress:
            comp_result = compress_hamiltonian(
                hamiltonian,
                n_electrons=n_electrons,
                taper=self.config.taper,
            )
            work_hamiltonian = comp_result.compressed_hamiltonian
            energy_shift = comp_result.energy_shift
            compression_info = comp_result.summary()
        else:
            work_hamiltonian = hamiltonian
            energy_shift = 0.0
            compression_info = {
                "original_qubits": hamiltonian.num_qubits,
                "compressed_qubits": hamiltonian.num_qubits,
                "qubits_saved": 0,
                "symmetries_found": 0,
                "energy_shift": 0.0,
                "encoding": "none",
            }

        n_qubits = work_hamiltonian.num_qubits

        # Step 3: Build ansatz if not provided
        if ansatz is None:
            if n_qubits == 0:
                # Fully compressed to scalar
                raw_energy = float(work_hamiltonian.coeffs[0].real) + energy_shift
                return QCEMResult(
                    raw_energy=raw_energy,
                    mitigated_energy=raw_energy,
                    exact_energy=exact_energy,
                    error_ha=abs(raw_energy - exact_energy),
                    error_mha=abs(raw_energy - exact_energy) * 1000,
                    error_kcal_mol=abs(raw_energy - exact_energy) * 627.509,
                    chemical_accuracy=abs(raw_energy - exact_energy) * 627.509 < 1.0,
                    compression=compression_info,
                    mitigation={"techniques_applied": ["none_needed"], "note": "fully_compressed"},
                    total_runtime_s=time.time() - start,
                    config=asdict(self.config) if hasattr(self.config, '__dataclass_fields__') else {},
                )

            ansatz = EfficientSU2(
                n_qubits,
                su2_gates=["ry", "rz"],
                entanglement="full" if n_qubits <= 6 else "linear",
                reps=2,
            )

        # Step 4: Optimize parameters (noiseless)
        optimal_params = self._optimize_vqe(ansatz, work_hamiltonian)
        bound_circuit = ansatz.assign_parameters(
            dict(zip(ansatz.parameters, optimal_params))
        )

        # Raw energy (no mitigation)
        job = self._estimator.run([(bound_circuit, work_hamiltonian)])
        raw_energy = float(job.result()[0].data.evs) + energy_shift

        # Step 5: Mitigate
        stack = self.config.mitigation_stack or get_preset(self.config.mitigation_preset)
        mit_result = mitigate(
            bound_circuit, work_hamiltonian,
            backend=backend,
            stack=stack,
        )
        mitigated_energy = mit_result["energy"] + energy_shift

        # Compute errors
        err = abs(mitigated_energy - exact_energy) if exact_energy else None

        return QCEMResult(
            raw_energy=raw_energy,
            mitigated_energy=mitigated_energy,
            exact_energy=exact_energy,
            error_ha=err,
            error_mha=err * 1000 if err else None,
            error_kcal_mol=err * 627.509 if err else None,
            chemical_accuracy=(err * 627.509 < 1.0) if err else None,
            compression=compression_info,
            mitigation=mit_result,
            total_runtime_s=time.time() - start,
            config=asdict(self.config) if hasattr(self.config, '__dataclass_fields__') else {},
        )

    def compare(
        self,
        hamiltonian: SparsePauliOp,
        n_electrons: int = 2,
        exact_energy: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compare QCEM (compress+mitigate) vs mitigate-only vs raw.

        Demonstrates the compounding benefit of compression × mitigation.

        Returns:
            Dict with results for each configuration
        """
        if exact_energy is None:
            exact_energy = float(np.linalg.eigvalsh(hamiltonian.to_matrix())[0])

        results = {}

        # Raw (no compression, no mitigation)
        cfg_raw = QCEMConfig(compress=False, mitigation_preset="none")
        qcem_raw = QCEM(cfg_raw)
        results["raw"] = qcem_raw.run(hamiltonian, n_electrons, exact_energy=exact_energy).to_dict()

        # Mitigation only (no compression)
        cfg_mit = QCEMConfig(compress=False, mitigation_preset="balanced")
        qcem_mit = QCEM(cfg_mit)
        results["mitigation_only"] = qcem_mit.run(hamiltonian, n_electrons, exact_energy=exact_energy).to_dict()

        # Compression only (no mitigation)
        cfg_comp = QCEMConfig(compress=True, mitigation_preset="none")
        qcem_comp = QCEM(cfg_comp)
        results["compression_only"] = qcem_comp.run(hamiltonian, n_electrons, exact_energy=exact_energy).to_dict()

        # QCEM full (compression + mitigation)
        cfg_full = QCEMConfig(compress=True, mitigation_preset="balanced")
        qcem_full = QCEM(cfg_full)
        results["qcem_full"] = qcem_full.run(hamiltonian, n_electrons, exact_energy=exact_energy).to_dict()

        # Summary
        results["summary"] = {
            "exact_energy": exact_energy,
            "raw_error_mha": results["raw"]["error_mha"],
            "mitigation_only_error_mha": results["mitigation_only"]["error_mha"],
            "compression_only_error_mha": results["compression_only"]["error_mha"],
            "qcem_full_error_mha": results["qcem_full"]["error_mha"],
        }

        return results

    def run_molecule(
        self,
        geometry: str,
        basis: str = "sto-3g",
        charge: int = 0,
        spin: int = 0,
        backend: Any = None,
    ) -> QCEMResult:
        """
        Run QCEM on a molecule specified by geometry string.

        Requires PySCF and qiskit-nature for Hamiltonian generation.

        Args:
            geometry: Molecular geometry ("H 0 0 0; H 0 0 0.74")
            basis: Basis set (default: sto-3g)
            charge: Molecular charge
            spin: Spin multiplicity - 1
            backend: IBM Quantum backend

        Returns:
            QCEMResult
        """
        try:
            from qiskit_nature.second_q.drivers import PySCFDriver
            from qiskit_nature.second_q.mappers import JordanWignerMapper
        except ImportError:
            raise ImportError(
                "qiskit-nature and PySCF are required for run_molecule(). "
                "Install with: pip install qiskit-nature pyscf"
            )

        driver = PySCFDriver(atom=geometry, basis=basis, charge=charge, spin=spin)
        problem = driver.run()
        fermionic_op = problem.hamiltonian.second_q_op()
        mapper = JordanWignerMapper()
        hamiltonian = mapper.map(fermionic_op)

        n_electrons = problem.num_particles[0] + problem.num_particles[1]
        return self.run(hamiltonian, n_electrons=n_electrons, backend=backend)

    def _optimize_vqe(
        self, ansatz: QuantumCircuit, hamiltonian: SparsePauliOp
    ) -> np.ndarray:
        """Optimize VQE parameters on noiseless simulator."""
        rng = np.random.default_rng(self.config.seed)
        exact = float(np.linalg.eigvalsh(hamiltonian.to_matrix())[0])
        best_energy = float("inf")
        best_params = None

        for _ in range(self.config.optimization_restarts):
            init = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)

            def cost(params):
                bound = ansatz.assign_parameters(dict(zip(ansatz.parameters, params)))
                job = self._estimator.run([(bound, hamiltonian)])
                return float(job.result()[0].data.evs)

            result = minimize(cost, init, method="COBYLA",
                            options={"maxiter": self.config.optimization_maxiter, "rhobeg": 1.0})
            if result.fun < best_energy:
                best_energy = result.fun
                best_params = result.x

            if abs(best_energy - exact) < 0.0016:
                break

        return best_params
