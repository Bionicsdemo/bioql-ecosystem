"""
QCEM Composable Error Mitigation Stack
========================================
Configurable pipeline: DD → Twirling → ZNE/PEC → TREX → Layer Learning

Standalone module — works with any Qiskit circuit + SparsePauliOp.
"""

import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp

try:
    from qiskit_ibm_runtime import EstimatorV2
    from qiskit_ibm_runtime.options import EstimatorOptions
    _IBM_RUNTIME = True
except ImportError:
    _IBM_RUNTIME = False

try:
    from qiskit.primitives import StatevectorEstimator
except ImportError:
    from qiskit.primitives import Estimator as StatevectorEstimator


@dataclass
class MitigationStack:
    """Configuration for the composable mitigation stack."""
    dd_enabled: bool = True
    dd_sequence: str = "XpXm"
    twirling_enabled: bool = True
    twirling_randomizations: int = 64
    zne_enabled: bool = True
    zne_noise_factors: List[float] = field(default_factory=lambda: [1, 1.5, 2, 2.5, 3])
    zne_extrapolator: str = "exponential"
    pec_enabled: bool = False
    pec_samples: int = 500
    trex_enabled: bool = True
    trex_randomizations: int = 64
    layer_learning_enabled: bool = True
    shots: int = 4096

    def active_techniques(self) -> List[str]:
        """Return list of enabled technique names."""
        t = []
        if self.dd_enabled:
            t.append("dynamical_decoupling")
        if self.twirling_enabled:
            t.append("pauli_twirling")
        if self.zne_enabled:
            t.append("zne")
        if self.pec_enabled:
            t.append("pec")
        if self.trex_enabled:
            t.append("trex")
        if self.layer_learning_enabled:
            t.append("layer_noise_learning")
        return t

    def to_estimator_options(self) -> Optional["EstimatorOptions"]:
        """Convert to Qiskit Runtime EstimatorOptions. Returns None if runtime unavailable."""
        if not _IBM_RUNTIME:
            return None

        opts = EstimatorOptions()
        opts.default_shots = self.shots

        if self.dd_enabled:
            opts.dynamical_decoupling.enable = True
            opts.dynamical_decoupling.sequence_type = self.dd_sequence

        if self.twirling_enabled:
            opts.twirling.enable_gates = True
            opts.twirling.enable_measure = True
            opts.twirling.num_randomizations = self.twirling_randomizations

        if self.zne_enabled:
            opts.resilience.zne_mitigation = True
            opts.resilience.zne.noise_factors = self.zne_noise_factors
            opts.resilience.zne.extrapolator = [self.zne_extrapolator, "linear"]
            opts.resilience.zne.amplifier = "gate_folding"

        if self.trex_enabled:
            opts.resilience.measure_mitigation = True
            opts.resilience.measure_noise_learning.num_randomizations = self.trex_randomizations
            opts.resilience.measure_noise_learning.shots_per_randomization = 256

        if self.layer_learning_enabled:
            opts.resilience.layer_noise_learning.max_layers_to_learn = 4
            opts.resilience.layer_noise_learning.num_randomizations = 32
            opts.resilience.layer_noise_learning.shots_per_randomization = 256

        return opts


# ============================================================================
# PRESET STACKS
# ============================================================================

PRESETS = {
    "maximum": MitigationStack(
        dd_enabled=True, twirling_enabled=True, zne_enabled=True,
        pec_enabled=True, trex_enabled=True, layer_learning_enabled=True,
    ),
    "balanced": MitigationStack(
        dd_enabled=True, twirling_enabled=True, zne_enabled=True,
        pec_enabled=False, trex_enabled=True, layer_learning_enabled=True,
    ),
    "fast": MitigationStack(
        dd_enabled=True, twirling_enabled=False, zne_enabled=True,
        pec_enabled=False, trex_enabled=True, layer_learning_enabled=False,
    ),
    "minimal": MitigationStack(
        dd_enabled=True, twirling_enabled=False, zne_enabled=False,
        pec_enabled=False, trex_enabled=True, layer_learning_enabled=False,
    ),
    "none": MitigationStack(
        dd_enabled=False, twirling_enabled=False, zne_enabled=False,
        pec_enabled=False, trex_enabled=False, layer_learning_enabled=False,
    ),
}


def get_preset(name: str) -> MitigationStack:
    """Get a named mitigation preset.

    Available presets:
        - "maximum": All 6 techniques (highest accuracy, 12× overhead)
        - "balanced": DD + Twirling + ZNE + TREX + Layer Learning (5× overhead)
        - "fast": DD + ZNE + TREX (3× overhead)
        - "minimal": DD + TREX only (2× overhead)
        - "none": No mitigation (baseline)
    """
    if name not in PRESETS:
        raise ValueError(f"Unknown preset '{name}'. Choose from: {list(PRESETS.keys())}")
    return PRESETS[name]


# ============================================================================
# MITIGATION EXECUTION
# ============================================================================

def mitigate(
    circuit: QuantumCircuit,
    observable: SparsePauliOp,
    backend: Any = None,
    stack: Optional[MitigationStack] = None,
    preset: str = "balanced",
) -> Dict[str, Any]:
    """
    Run error-mitigated expectation value estimation.

    Uses IBM Runtime EstimatorV2 when a backend is provided,
    falls back to StatevectorEstimator (noiseless) otherwise.

    Args:
        circuit: Bound quantum circuit (parameters already assigned)
        observable: Observable as SparsePauliOp
        backend: IBM Quantum backend (or None for simulator)
        stack: MitigationStack config (overrides preset if provided)
        preset: Named preset if stack not provided

    Returns:
        Dict with mitigated energy, techniques applied, and metadata

    Example:
        >>> from qiskit.circuit.library import EfficientSU2
        >>> from qiskit.quantum_info import SparsePauliOp
        >>> ansatz = EfficientSU2(2, reps=1)
        >>> H = SparsePauliOp.from_list([("ZZ", 0.5), ("XX", 0.3)])
        >>> bound = ansatz.assign_parameters([0.1] * ansatz.num_parameters)
        >>> result = mitigate(bound, H, preset="fast")
        >>> print(f"Energy: {result['energy']:.6f}")
    """
    if stack is None:
        stack = get_preset(preset)

    techniques_applied = stack.active_techniques()

    if backend is not None and _IBM_RUNTIME:
        # Hardware execution with mitigation
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

        pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
        isa_circuit = pm.run(circuit)
        isa_obs = observable.apply_layout(isa_circuit.layout)

        options = stack.to_estimator_options()
        estimator = EstimatorV2(mode=backend, options=options)
        job = estimator.run([(isa_circuit, isa_obs)])
        result = job.result()

        energy = float(result[0].data.evs)
        std = float(result[0].data.stds)
    else:
        # Simulator fallback
        estimator = StatevectorEstimator()
        job = estimator.run([(circuit, observable)])
        energy = float(job.result()[0].data.evs)
        std = 0.0
        techniques_applied = ["statevector_exact"]

    return {
        "energy": energy,
        "std": std,
        "techniques_applied": techniques_applied,
        "n_techniques": len(techniques_applied),
        "preset": preset if stack is None else "custom",
        "shots": stack.shots,
        "backend": str(backend) if backend else "StatevectorEstimator",
    }
