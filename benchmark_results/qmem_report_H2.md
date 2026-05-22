# QMEM Benchmark Report

Generated: 2026-05-22T16:33:26.378977+00:00
Molecule: H2
Seeds: 10
Best technique: **raw**

## Per-Technique Results

| Technique | Mean Error (mHa) | Mean Error (kcal/mol) | 95% CI (mHa) | Chem. Accuracy Rate |
|-----------|------------------|-----------------------|---------------|---------------------|
| raw | 266.54 | 167.26 | [263.95, 268.94] | 0% |
| zne | 288.92 | 181.30 | [285.56, 292.66] | 0% |
| pec | 300.49 | 188.56 | [297.27, 303.75] | 0% |
| dd | 274.57 | 172.30 | [272.33, 277.23] | 0% |
| trex | 284.18 | 178.33 | [280.70, 287.49] | 0% |
| combined | 315.13 | 197.75 | [312.46, 317.60] | 0% |

## Pairwise Statistical Tests (Wilcoxon)

| Comparison | p-value | Significant (p<0.05) |
|------------|---------|----------------------|
| raw_vs_zne | 0.0020 | Yes |
| raw_vs_pec | 0.0020 | Yes |
| raw_vs_dd | 0.0020 | Yes |
| raw_vs_trex | 0.0020 | Yes |
| raw_vs_combined | 0.0020 | Yes |
| zne_vs_pec | 0.0059 | Yes |
| zne_vs_dd | 0.0020 | Yes |
| zne_vs_trex | 0.1602 | No |
| zne_vs_combined | 0.0020 | Yes |
| pec_vs_dd | 0.0020 | Yes |
| pec_vs_trex | 0.0020 | Yes |
| pec_vs_combined | 0.0039 | Yes |
| dd_vs_trex | 0.0059 | Yes |
| dd_vs_combined | 0.0020 | Yes |
| trex_vs_combined | 0.0020 | Yes |