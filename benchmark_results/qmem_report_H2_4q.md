# QMEM Benchmark Report

Generated: 2026-05-22T16:30:36.402010+00:00
Molecule: H2_4q
Seeds: 10
Best technique: **trex**

## Per-Technique Results

| Technique | Mean Error (mHa) | Mean Error (kcal/mol) | 95% CI (mHa) | Chem. Accuracy Rate |
|-----------|------------------|-----------------------|---------------|---------------------|
| raw | 547.65 | 343.65 | [507.02, 585.00] | 0% |
| zne | 550.18 | 345.24 | [515.88, 581.15] | 0% |
| pec | 549.77 | 344.99 | [517.71, 582.02] | 0% |
| dd | 545.49 | 342.30 | [507.88, 578.09] | 0% |
| trex | 540.96 | 339.46 | [507.50, 577.55] | 0% |
| combined | 544.52 | 341.69 | [514.70, 573.95] | 0% |

## Pairwise Statistical Tests (Wilcoxon)

| Comparison | p-value | Significant (p<0.05) |
|------------|---------|----------------------|
| raw_vs_zne | 0.8457 | No |
| raw_vs_pec | 1.0000 | No |
| raw_vs_dd | 0.7695 | No |
| raw_vs_trex | 0.3750 | No |
| raw_vs_combined | 0.8457 | No |
| zne_vs_pec | 1.0000 | No |
| zne_vs_dd | 0.6953 | No |
| zne_vs_trex | 0.2754 | No |
| zne_vs_combined | 0.2324 | No |
| pec_vs_dd | 0.6953 | No |
| pec_vs_trex | 0.7695 | No |
| pec_vs_combined | 0.1602 | No |
| dd_vs_trex | 0.6953 | No |
| dd_vs_combined | 1.0000 | No |
| trex_vs_combined | 0.7695 | No |