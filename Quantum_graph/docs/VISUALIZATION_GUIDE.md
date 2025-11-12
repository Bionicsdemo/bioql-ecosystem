# Visualization Guide

Complete guide to interpreting Quantum Graphs visualizations and scientific results.

## Table of Contents

- [Output Files](#output-files)
- [Visualization Types](#visualization-types)
- [Scientific Metrics](#scientific-metrics)
- [Interactive Features](#interactive-features)
- [Interpretation Examples](#interpretation-examples)

---

## Output Files

Every quantum job generates multiple files for analysis:

### 1. Energy Landscape (`energy_landscape.png`)

**Shows**: Conformational energy distribution
**Format**: PNG (high-resolution, 300 DPI)
**Dimensions**: 1600×800 pixels

**Elements**:
- X-axis: Conformation index or reaction coordinate
- Y-axis: Energy (kcal/mol or Hartree)
- Bars: Individual conformer energies
- Colors: Energy gradient (blue=low, red=high)
- Labels: Ground state marker, energy values

**Interpretation**:
- **Lowest bar**: Ground state (most stable)
- **Energy gaps**: Activation barriers
- **Multiple minima**: Alternative conformations
- **Broad distribution**: Flexible molecule

**Example Reading**:
```
If you see:
- Ground state at -1075.3 Hartree
- First excited state at -1075.1 Hartree
→ Energy gap = 0.2 Hartree = 125 kcal/mol (stable)
```

---

### 2. Probability Distribution (`probability_distribution.png`)

**Shows**: Boltzmann probabilities of conformations
**Format**: PNG (300 DPI)

**Calculation**:
```
P(i) = exp(-E_i / kT) / Z
where Z = Σ exp(-E_j / kT)
```

**Elements**:
- X-axis: Conformation index
- Y-axis: Probability (0-1)
- Bars: Population of each state at 300K

**Interpretation**:
- **High probability**: Thermally accessible states
- **Low probability**: Rare conformations
- **Multiple peaks**: Ensemble behavior
- **Single peak**: Rigid molecule

**Use Cases**:
- Predicting experimental observables
- Understanding conformational flexibility
- Computing ensemble-averaged properties

---

### 3. Quantum Counts Histogram (`counts_histogram.png`)

**Shows**: Raw quantum measurement results
**Format**: PNG (300 DPI)

**Elements**:
- X-axis: Bitstring outcomes (e.g., "0000", "0001")
- Y-axis: Count (number of measurements)
- Bars: Frequency of each quantum state

**Interpretation**:
- **Dominant peaks**: Most probable quantum states
- **Distribution width**: Quantum fluctuations
- **Background noise**: Hardware errors
- **Symmetry**: Conservation laws

**Quality Indicators**:
- ✅ **Good**: Clear peaks, >50% in top 10 states
- ⚠️ **Medium**: Broader distribution, 30-50% in top states
- ❌ **Poor**: Flat distribution, <30% in top states

---

### 4. Statevector Visualization (`statevector.png`)

**Shows**: Quantum state amplitudes
**Format**: PNG (300 DPI)

**Elements**:
- X-axis: Basis states |00...0⟩ to |11...1⟩
- Y-axis: Probability amplitude |ψ|²
- Bars: Population of each computational basis state
- Phase colors: Complex phase (if shown)

**Interpretation**:
- **Localized**: State in definite configuration
- **Delocalized**: Quantum superposition
- **Entanglement**: Correlations between qubits

---

### 5. 3D Structure (`structure_3d.png`)

**Shows**: Molecular 3D geometry
**Format**: PNG (300 DPI) and interactive HTML

**Rendering Styles**:
- **Ball-and-stick**: Default, shows atoms as spheres
- **Space-filling**: Van der Waals surfaces
- **Ribbon**: For proteins, shows secondary structure

**Color Coding**:
- C (carbon): Gray
- N (nitrogen): Blue
- O (oxygen): Red
- H (hydrogen): White
- S (sulfur): Yellow
- P (phosphorus): Orange

**Interpretation**:
- **Bond lengths**: Normal ~1.5 Å
- **Bond angles**: Tetrahedral ~109°, planar ~120°
- **Steric clashes**: Atoms closer than VdW radii
- **Hydrogen bonds**: O-H...O distances ~2.8 Å

---

### 6. Interactive HTML (`structure_interactive.html`)

**Features**:
- Rotate: Click and drag
- Zoom: Mouse wheel
- Pan: Right-click and drag
- Select atoms: Click
- Measurements: Distance/angle tools

**Powered by**: Plotly.js or py3Dmol

---

### 7. Report File (`report.txt`)

**Contains**:
```
═══════════════════════════════════
QUANTUM VISUALIZATION REPORT
═══════════════════════════════════

Job ID: a7f2b3c4-d5e6-47f8-a9b0-c1d2e3f4g5h6
Molecule: Aspirin
Type: Small Molecule
Visualization: Conformational Sampling

-----------------------------------
QUANTUM CONFIGURATION
-----------------------------------
Backend:         IBM Torino
Logical Qubits:  12
Physical Qubits: 576
Shots:           4096
Circuit Depth:   240
QEC Code:        Surface-5

-----------------------------------
MOLECULAR COMPLEXITY
-----------------------------------
Atoms:              21
Heavy Atoms:        17
Electrons:          126
Molecular Weight:   180.16 Da
Rotatable Bonds:    4
Conformations:      ~10^8.7

-----------------------------------
RESULTS
-----------------------------------
Ground State Energy:  -1075.287 Hartree
                      -674,892 kcal/mol

Energy Landscape:
  State 0:  -1075.287 Ha  (0.0 kcal/mol)   P=0.68
  State 1:  -1075.285 Ha  (+1.3 kcal/mol)  P=0.18
  State 2:  -1075.280 Ha  (+4.4 kcal/mol)  P=0.08
  ...

-----------------------------------
EXECUTION METRICS
-----------------------------------
Total Time:       923.4 seconds
Quantum Time:     0.098 seconds
Queue Time:       920.0 seconds
Cost:             $12.29 USD
Accuracy:         95.2%

-----------------------------------
QUANTUM METRICS
-----------------------------------
Fidelity:         0.982
Gate Errors:      34 (expected: 30)
Readout Errors:   12 (expected: 10)
T1 (avg):         98.3 μs
T2 (avg):         142.7 μs

═══════════════════════════════════
```

---

## Visualization Types

### Energy Landscapes

**1. Single Minimum (Rigid Molecule)**
```
Energy
  │
  │        ●
  │       ╱ ╲
  │      ╱   ╲
  │_____╱_____╲_____
      Coordinate
```
**Example**: Benzene (planar, rigid aromatic)

---

**2. Double Well (Two Conformers)**
```
Energy
  │
  │   ●         ●
  │  ╱╲       ╱╲
  │ ╱  ╲_____╱  ╲
  │╱            ╲
  └──────────────
     Coordinate
```
**Example**: Butane (gauche/anti conformers)

---

**3. Multiple Minima (Flexible)**
```
Energy
  │
  │ ●  ●   ●  ●
  │╱╲╱╲___╱╲╱╲
  │         ╲
  └──────────────
     Coordinate
```
**Example**: Peptides (many conformations)

---

### Binding Affinity Plots

**Elements**:
- **Binding pose**: 3D protein-ligand complex
- **Energy decomposition**: Van der Waals, electrostatic, hydrophobic
- **Interaction map**: H-bonds, π-π stacking, salt bridges
- **Binding pocket**: Solvent-accessible surface

**Interpretation**:
```
Binding Energy = -8.5 kcal/mol
  Van der Waals:    -6.2 kcal/mol
  Electrostatic:    -3.8 kcal/mol
  Hydrophobic:      -2.1 kcal/mol
  Entropy penalty:  +3.6 kcal/mol
  ────────────────────────────────
  Total:            -8.5 kcal/mol

Predicted Kd ≈ 580 nM (strong binder)
```

---

### Molecular Orbitals

**Shows**: HOMO, LUMO, and other molecular orbitals

**Color Coding**:
- **Blue**: Positive phase (+)
- **Red**: Negative phase (-)
- **Opacity**: Orbital density

**Key Orbitals**:
- **HOMO**: Highest Occupied Molecular Orbital (electron donor)
- **LUMO**: Lowest Unoccupied Molecular Orbital (electron acceptor)
- **HOMO-LUMO gap**: Electronic excitation energy

**Interpretation**:
```
HOMO energy:        -5.2 eV
LUMO energy:        -2.1 eV
HOMO-LUMO gap:       3.1 eV  (UV absorption ~400 nm)
```

---

### Electron Density

**Shows**: 3D probability distribution of electrons

**Isosurfaces**:
- 0.001 e/Å³: Outer boundary
- 0.01 e/Å³: Bonding regions
- 0.1 e/Å³: Core electrons

**Features to Look For**:
- **Bond paths**: Density ridges between atoms
- **Lone pairs**: Density lobes on heteroatoms
- **π-systems**: Delocalized density above/below plane
- **Charge transfer**: Asymmetric density distribution

---

## Scientific Metrics

### Energy Metrics

#### 1. Absolute Energy (Hartree)

```
E_total = E_electronic + E_nuclear
```

**Typical values**:
- H₂: -1.13 Hartree
- H₂O: -76.0 Hartree
- Protein: -10,000 to -100,000 Hartree

#### 2. Relative Energy (kcal/mol)

```
ΔE = (E_conformer - E_ground) × 627.5
```

**Interpretation**:
- 0-2 kcal/mol: Easily accessible at room temperature
- 2-5 kcal/mol: Moderately accessible
- 5-10 kcal/mol: Rarely populated
- >10 kcal/mol: Effectively not populated

#### 3. Binding Energy (kcal/mol)

```
ΔE_bind = E_complex - (E_protein + E_ligand)
```

**Drug discovery guidelines**:
- -12 kcal/mol: Very strong binder (Kd ~ 1 nM)
- -10 kcal/mol: Strong binder (Kd ~ 10 nM)
- -8 kcal/mol: Good binder (Kd ~ 500 nM)
- -6 kcal/mol: Weak binder (Kd ~ 10 μM)

---

### Quantum Metrics

#### 1. Fidelity

Measure of quantum state quality:

```
F = |⟨ψ_ideal|ψ_measured⟩|²
```

**Quality scale**:
- F > 0.99: Excellent
- F = 0.95-0.99: Good
- F = 0.90-0.95: Acceptable
- F < 0.90: Poor (retry recommended)

#### 2. Purity

Measure of quantum vs classical mixture:

```
Tr(ρ²) where ρ is density matrix
```

**Values**:
- Purity = 1: Pure quantum state
- Purity < 1: Mixed state (decoherence)

#### 3. Entanglement

Two-qubit correlations:

```
C(i,j) = ⟨Z_i Z_j⟩ - ⟨Z_i⟩⟨Z_j⟩
```

**Interpretation**:
- |C| > 0.5: Strong correlation
- |C| = 0.1-0.5: Moderate correlation
- |C| < 0.1: Weakly correlated

---

### Statistical Metrics

#### 1. Standard Deviation

Energy uncertainty from sampling:

```
σ_E = √(⟨E²⟩ - ⟨E⟩²)
```

**Target**: σ_E < 0.001 Hartree (chemical accuracy)

#### 2. Confidence Interval

95% confidence for energy:

```
E_true ∈ [E_measured - 1.96σ, E_measured + 1.96σ]
```

#### 3. Convergence

Optimization convergence:

```
|E_n - E_{n-1}| / |E_n| < 10^-6
```

---

## Interactive Features

### HTML Visualizations

All jobs include interactive HTML files with:

1. **3D Structure Viewer**
   - Rotate, zoom, pan
   - Select atoms/residues
   - Measure distances/angles
   - Toggle representations

2. **Energy Plots (Plotly)**
   - Hover for exact values
   - Zoom to region
   - Download as PNG
   - Export data to CSV

3. **Molecular Orbitals**
   - Rotate orbital isosurfaces
   - Adjust isovalue threshold
   - Toggle phases
   - Overlay density

### Jupyter Notebook Integration

```python
from quantum_graphs import load_result

# Load results
result = load_result('job_id.json')

# Interactive 3D viewer
result.view_structure()

# Interactive energy plot
result.plot_energy_landscape()

# Export to common formats
result.export_pdb('structure.pdb')
result.export_xyz('structure.xyz')
```

---

## Interpretation Examples

### Example 1: Aspirin Conformational Analysis

**Input**: Aspirin molecule (21 atoms)
**Visualization**: Conformational sampling
**Backend**: IBM Brisbane (1.25$/shot)

**Results**:
```
Ground state energy: -1075.287 Hartree

Top 5 conformations:
1. -1075.287 Ha  (0.0 kcal/mol)   68% population
2. -1075.285 Ha  (+1.3 kcal/mol)  18% population
3. -1075.280 Ha  (+4.4 kcal/mol)   8% population
4. -1075.277 Ha  (+6.3 kcal/mol)   4% population
5. -1075.273 Ha  (+8.8 kcal/mol)   2% population
```

**Interpretation**:
- ✅ Aspirin is relatively rigid (68% in ground state)
- ✅ Dominant conformation clearly identified
- ✅ Alternative conformers present but rare (<10 kcal/mol barrier)
- 💡 For docking, use conformer #1 (dominant)

---

### Example 2: Antibody-Antigen Binding

**Input**: IgG Fab + peptide antigen
**Visualization**: Binding affinity
**Backend**: IBM Torino (3.00$/shot)

**Results**:
```
Binding energy: -12.3 kcal/mol
Predicted Kd: 1.2 nM (very strong)

Energy decomposition:
  H-bonds (6):        -8.4 kcal/mol
  Hydrophobic:        -5.2 kcal/mol
  Salt bridges (2):   -4.1 kcal/mol
  Van der Waals:      -3.8 kcal/mol
  Entropy penalty:    +9.2 kcal/mol
  ────────────────────────────────
  Total:             -12.3 kcal/mol

Key interactions:
  CDR-H1 Tyr32 - Antigen Glu5 (H-bond, 2.7 Å)
  CDR-L3 Arg95 - Antigen Asp8 (salt bridge, 2.9 Å)
  CDR-H2 Trp50 - Antigen Phe7 (π-π stacking, 3.8 Å)
```

**Interpretation**:
- ✅ Very strong binding (nanomolar affinity)
- ✅ Multiple interaction types (robust binding)
- ⚠️ High entropy penalty (loss of flexibility)
- 💡 Optimize CDR-H2 to reduce entropy cost

---

### Example 3: Drug Discovery Screening

**Input**: 100 drug candidates
**Visualization**: Structure 3D + binding affinity
**Backend**: Qiskit Simulator (FREE) → IBM Brisbane (top 10)

**Workflow**:
```
Step 1: Screen 100 compounds (simulator, FREE, 30 min)
  → Filter: predicted binding < -8 kcal/mol
  → Result: 15 hits

Step 2: Validate top 15 (IBM Brisbane, $37.50, 2 hours)
  → Quantum-accurate binding energies
  → Result: 8 confirmed hits

Step 3: Detailed analysis of top 3 (IBM Torino, $36, 3 hours)
  → Full conformational analysis
  → Binding mode optimization
  → Result: 2 lead compounds

Total cost: $73.50
Total time: 6 hours
Success rate: 2/100 = 2% (typical for virtual screening)
```

---

## Best Practices

### 1. Always Check Fidelity

Before interpreting results:
```python
if result['fidelity'] < 0.90:
    print("⚠️ Low fidelity - retry with more shots or error mitigation")
```

### 2. Validate Against Benchmarks

Compare to known systems:
```python
# Compare to DFT for validation
E_vqe = -1075.287
E_dft = -1075.291
error = abs(E_vqe - E_dft)  # 0.004 Ha = 2.5 kcal/mol ✅
```

### 3. Use Ensemble Averages

For flexible molecules:
```python
# Weighted average property
property_avg = sum(P_i * property_i for all conformers)
```

### 4. Check Convergence

Ensure optimization converged:
```python
if result['optimization_converged']:
    print("✅ Optimization successful")
else:
    print("⚠️ May need more iterations")
```

---

## Troubleshooting

### "Energy too high / unphysical"

**Causes**:
- Poor ansatz choice
- Insufficient optimization
- Hardware errors

**Solutions**:
- Increase circuit depth
- Try different ansatz (UCCSD)
- Use error mitigation
- Increase shots

---

### "Flat energy landscape"

**Causes**:
- Barren plateau (vanishing gradients)
- Too many parameters
- Poor initialization

**Solutions**:
- Reduce circuit depth
- Use layer-by-layer training
- Initialize near Hartree-Fock

---

### "Low fidelity / noisy results"

**Causes**:
- Hardware errors
- Deep circuit
- Insufficient shots

**Solutions**:
- Increase shots (2x or 4x)
- Use error mitigation
- Switch to better backend
- Enable QEC

---

## Next Steps

- [API Reference](API_REFERENCE.md) - Accessing visualizations programmatically
- [Configuration Guide](CONFIGURATION_GUIDE.md) - Optimizing visual quality
- [VQE Algorithm](VQE_ALGORITHM.md) - Understanding the science
- [IBM Integration](IBM_QUANTUM_INTEGRATION.md) - Running on hardware

---

## Support

For visualization questions:
- Email: support@quantum-graphs.bio
- Discord: [#viz-help](https://discord.gg/bioql)
- Examples: [GitHub Repo](https://github.com/bioql/quantum-graphs)
