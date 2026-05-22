# QCEM Benchmark Report
## Quantum Compression-Enhanced Mitigation


### H₂ (4 qubits, STO-3G)
- Original: 4 qubits | Compressed: 1 qubits | Symmetries: 3
- Exact energy: -1.769634 Ha
- Seeds: 10

| Configuration | Qubits | CX Gates | Mean Error (mHa) | 95% CI (mHa) | Reduction | Chem. Acc. | Overhead |
|--------------|:------:|:--------:|:----------------:|:------------:|:---------:|:----------:|:--------:|
| raw | 4 | 12 | 161.1 | [157.3, 165.1] | 0.0% | 0% | 1.0× |
| mitigation_only | 4 | 12 | 50.9 | [48.0, 53.6] | 68.4% | 0% | 5.0× |
| compression_only | 1 | 3 | 28.1 | [26.0, 30.4] | 82.6% | 0% | 1.0× |
| qcem_full | 1 | 3 | 5.5 | [3.5, 7.5] | 96.6% | 20% | 5.0× |
| qcem_maximum | 1 | 3 | 2.9 | [1.7, 4.1] | 98.2% | 30% | 12.0× |

### LiH-like (6 qubits)
- Original: 6 qubits | Compressed: 5 qubits | Symmetries: 1
- Exact energy: -9.184814 Ha
- Seeds: 10

| Configuration | Qubits | CX Gates | Mean Error (mHa) | 95% CI (mHa) | Reduction | Chem. Acc. | Overhead |
|--------------|:------:|:--------:|:----------------:|:------------:|:---------:|:----------:|:--------:|
| raw | 6 | 18 | 323.4 | [318.8, 328.4] | 0.0% | 0% | 1.0× |
| mitigation_only | 6 | 18 | 130.1 | [126.6, 133.4] | 59.8% | 0% | 5.0× |
| compression_only | 5 | 15 | 277.0 | [272.2, 282.2] | 14.4% | 0% | 1.0× |
| qcem_full | 5 | 15 | 120.5 | [116.1, 124.9] | 62.7% | 0% | 5.0× |
| qcem_maximum | 5 | 15 | 97.4 | [92.9, 101.9] | 69.9% | 0% | 12.0× |

### BeH₂-like (8 qubits)
- Original: 8 qubits | Compressed: 6 qubits | Symmetries: 2
- Exact energy: -17.231834 Ha
- Seeds: 10

| Configuration | Qubits | CX Gates | Mean Error (mHa) | 95% CI (mHa) | Reduction | Chem. Acc. | Overhead |
|--------------|:------:|:--------:|:----------------:|:------------:|:---------:|:----------:|:--------:|
| raw | 8 | 24 | 595.9 | [590.6, 601.7] | 0.0% | 0% | 1.0× |
| mitigation_only | 8 | 24 | 301.7 | [297.6, 305.5] | 49.4% | 0% | 5.0× |
| compression_only | 6 | 18 | 328.0 | [322.8, 333.7] | 45.0% | 0% | 1.0× |
| qcem_full | 6 | 18 | 127.1 | [122.2, 131.9] | 78.7% | 0% | 5.0× |
| qcem_maximum | 6 | 18 | 98.4 | [93.4, 103.3] | 83.5% | 0% | 12.0× |