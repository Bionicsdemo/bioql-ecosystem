# QCEM — Quantum Compression-Enhanced Mitigation

A Qiskit-compatible function that combines **molecular Hamiltonian compression** with **composable error mitigation** for quantum chemistry calculations.

Unlike standalone error mitigation methods (ZNE, PEC, TEM), QCEM first compresses the Hamiltonian via Z₂ symmetry tapering — fewer qubits produce shallower circuits, which reduces the noise that mitigation must correct. **The best error mitigation is the error you never introduce.**

## Installation

```bash
pip install qcem

# With IBM Quantum Runtime support
pip install qcem[ibm]

# With PySCF for molecule input
pip install qcem[nature]
```

## Quick Start

```python
from qcem import QCEM
from qiskit.quantum_info import SparsePauliOp

# H₂ molecule Hamiltonian (4-qubit Jordan-Wigner)
H = SparsePauliOp.from_list([
    ("IIII", -0.81054798), ("IIIZ",  0.17218393),
    ("IIZI", -0.22575349), ("IZII",  0.17218393),
    ("ZIII", -0.22575349), ("IIZZ",  0.12091263),
    ("IZIZ",  0.16614543), ("IZZI",  0.16892754),
    ("ZIIZ",  0.16614543), ("ZIZI",  0.12091263),
    ("ZZII",  0.16892754), ("ZZZZ",  0.17464343),
    ("XXYY",  0.0452328),  ("YYXX",  0.0452328),
    ("XYYX", -0.0452328),  ("YXXY", -0.0452328),
])

qcem = QCEM()
result = qcem.run(H, n_electrons=2)
print(result.summary())
```

Output:
```
QCEM Result
========================================
Mitigated Energy:  -1.769634 Ha
Exact Energy:      -1.769634 Ha
Error:             0.00 mHa (0.00 kcal/mol)
Chemical Accuracy: Yes

Compression: 4 → 1 qubits (3 saved, 3 symmetries)
Mitigation:  statevector_exact
Runtime:     2.1s
```

## With IBM Quantum Hardware

```python
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService(channel="ibm_quantum_platform")
backend = service.backend("ibm_boston")

result = qcem.run(H, n_electrons=2, backend=backend)
```

## Compare Strategies

```python
comparison = qcem.compare(H, n_electrons=2)
# Returns results for: raw, mitigation_only, compression_only, qcem_full
```

## Mitigation Presets

| Preset | Techniques | Overhead | Use Case |
|--------|-----------|----------|----------|
| `maximum` | DD + Twirl + ZNE + PEC + TREX + Layer | 12× | Publication benchmarks |
| `balanced` | DD + Twirl + ZNE + TREX + Layer | 5× | Drug candidate evaluation |
| `fast` | DD + ZNE + TREX | 3× | Screening |
| `minimal` | DD + TREX | 2× | Quick estimates |
| `none` | — | 1× | Baseline comparison |

```python
from qcem import QCEM, QCEMConfig

qcem = QCEM(QCEMConfig(mitigation_preset="maximum"))
```

## From Molecular Geometry (requires PySCF)

```python
result = qcem.run_molecule("H 0 0 0; H 0 0 0.74", basis="sto-3g")
```

## How It Works

```
Hamiltonian → [Z₂ Symmetry Detection] → [Tapering] → Compressed Hamiltonian
                                                            ↓
                                                    [Build Ansatz]
                                                            ↓
                                                    [VQE Optimization]
                                                            ↓
Circuit → [DD] → [Twirling] → [ZNE/PEC] → [TREX] → [Layer Learning] → Energy
```

## By BioQL

QCEM is developed by the BioQL Quantum Team as part of the BioQL quantum drug discovery platform.

## License

Apache 2.0
