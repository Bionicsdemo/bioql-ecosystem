# Quantum Graphs Configuration Guide

Complete guide to configuring Quantum Graphs for optimal scientific visualization.

## Table of Contents

- [Molecule Types](#molecule-types)
- [Visualization Types](#visualization-types)
- [Quantum Backends](#quantum-backends)
- [Compatibility Matrix](#compatibility-matrix)
- [Cost Optimization](#cost-optimization)
- [Performance Tuning](#performance-tuning)
- [Use Case Examples](#use-case-examples)

---

## Molecule Types

Quantum Graphs supports 7 types of molecular systems with automatic parameter optimization.

### 1. Protein (`protein`)

**Description**: Single protein structures (< 5000 atoms)

**Use Cases**:
- Protein structure visualization
- Secondary structure analysis
- Active site identification
- Conformational dynamics

**Typical Properties**:
- Atoms: 1,000 - 5,000
- Residues: 100 - 500
- Molecular Weight: 10-50 kDa

**Recommended Backends**:
- Quick tests: `qiskit_simulator`
- Production: `ibm_brisbane` or `ionq_forte`

**Example**:
```json
{
  "molecule_type": "protein",
  "molecule_data": {
    "num_atoms": 2500,
    "num_residues": 250,
    "molecular_weight": 28000
  }
}
```

**Best Visualizations**:
- `structure_3d`
- `protein_folding`
- `conformational_sampling`

---

### 2. DNA (`dna`)

**Description**: DNA sequences and structures

**Use Cases**:
- DNA structure visualization
- Base pair analysis
- Conformational flexibility
- DNA-protein interactions

**Typical Properties**:
- Atoms: 500 - 10,000
- Base Pairs: 20 - 500
- Molecular Weight: 6-150 kDa

**Recommended Backends**:
- Quick tests: `qiskit_simulator`
- Production: `ibm_torino`

**Example**:
```json
{
  "molecule_type": "dna",
  "molecule_data": {
    "num_atoms": 3000,
    "num_base_pairs": 100,
    "sequence": "ATCGATCG..."
  }
}
```

---

### 3. RNA (`rna`)

**Description**: RNA sequences and structures

**Use Cases**:
- RNA folding
- Secondary structure prediction
- Ribozyme analysis
- RNA-ligand binding

**Typical Properties**:
- Atoms: 300 - 5,000
- Nucleotides: 20 - 500
- Molecular Weight: 6-150 kDa

**Recommended Backends**:
- Quick tests: `qiskit_simulator`
- Production: `ibm_brisbane`

---

### 4. Small Molecule (`small_molecule`)

**Description**: Drug-like molecules and organic compounds (< 100 atoms)

**Use Cases**:
- Drug design
- ADME prediction
- Chemical reaction pathways
- Molecular docking

**Typical Properties**:
- Atoms: 10 - 100
- Molecular Weight: 100-800 Da
- Rotatable Bonds: 0-15

**Recommended Backends**:
- Quick tests: `qiskit_simulator` (FREE)
- Production: `ibm_brisbane` or `ionq_forte`

**Example**:
```json
{
  "molecule_type": "small_molecule",
  "molecule_data": {
    "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "num_atoms": 21,
    "molecular_weight": 180.16,
    "rotatable_bonds": 4
  }
}
```

**Best Visualizations**:
- `structure_3d`
- `conformational_sampling`
- `molecular_orbitals`
- `docking_simulation`

---

### 5. Antibody (`antibody`)

**Description**: Antibody structures (IgG, Fab, scFv)

**Use Cases**:
- Antibody-antigen binding
- CDR loop analysis
- Humanization studies
- Epitope mapping

**Typical Properties**:
- Atoms: 10,000 - 25,000
- Residues: 1,300 - 2,500
- Molecular Weight: 150-180 kDa

**Recommended Backends**:
- Quick tests: `ionq_simulator`
- Production: `ibm_torino` or `ionq_forte`

**Example**:
```json
{
  "molecule_type": "antibody",
  "molecule_data": {
    "num_atoms": 20000,
    "num_residues": 1300,
    "molecular_weight": 150000,
    "antibody_type": "IgG"
  }
}
```

**Best Visualizations**:
- `structure_3d`
- `binding_affinity`
- `conformational_sampling`

---

### 6. Protein Complex (`protein_complex`)

**Description**: Multi-protein assemblies (> 5000 atoms)

**Use Cases**:
- Protein-protein interactions
- Quaternary structure
- Allosteric regulation
- Molecular machines

**Typical Properties**:
- Atoms: 5,000 - 50,000
- Subunits: 2 - 20
- Molecular Weight: 50-500 kDa

**Recommended Backends**:
- Quick tests: `aws_sv1`
- Production: `ibm_torino` (high qubit count)

---

### 7. Metabolite (`metabolite`)

**Description**: Metabolic compounds and biochemical intermediates

**Use Cases**:
- Metabolic pathway analysis
- Enzyme-substrate interactions
- Metabolomics visualization
- Reaction mechanisms

**Typical Properties**:
- Atoms: 5 - 50
- Molecular Weight: 50-500 Da

**Recommended Backends**:
- Quick tests: `qiskit_simulator`
- Production: `ibm_brisbane`

---

## Visualization Types

Quantum Graphs supports 9 types of scientific visualizations, each optimized for specific applications.

### 1. Structure 3D (`structure_3d`)

**Description**: 3D molecular structure rendering with ball-and-stick or space-filling models

**Best For**:
- Visual inspection
- Publication figures
- Teaching materials

**Quantum Requirements**:
- Qubits: Low (4-8)
- Shots: 1,024
- Time: < 1 minute

**Output Files**:
- PNG image (high-resolution)
- Interactive HTML (rotatable)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $1.25 - $3.00

---

### 2. Energy Landscape (`energy_landscape`)

**Description**: Conformational energy surface visualization

**Best For**:
- Understanding molecular stability
- Finding energy minima
- Transition state analysis

**Quantum Requirements**:
- Qubits: Medium (8-15)
- Shots: 2,048 - 4,096
- Time: 5-30 minutes

**Quantum Algorithm**: Variational Quantum Eigensolver (VQE)

**Output Files**:
- Energy curve plot (PNG)
- 3D energy surface (HTML)
- Energy data (JSON)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $2.50 - $12.00

---

### 3. Binding Affinity (`binding_affinity`)

**Description**: Drug-target binding energy calculation

**Best For**:
- Drug discovery
- Lead optimization
- Structure-activity relationships

**Quantum Requirements**:
- Qubits: Medium-High (12-20)
- Shots: 4,096 - 8,192
- Time: 15-60 minutes

**Quantum Algorithm**: Quantum Annealing / VQE

**Output Files**:
- Binding pose visualization (PNG)
- Energy decomposition (JSON)
- Interaction map (HTML)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $5.00 - $24.00

**Example Configuration**:
```json
{
  "viz_type": "binding_affinity",
  "molecule_data": {
    "receptor": "protein.pdb",
    "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"
  },
  "backend_preference": "ibm_brisbane",
  "shots": 4096
}
```

---

### 4. Conformational Sampling (`conformational_sampling`)

**Description**: Quantum-enhanced sampling of molecular conformations

**Best For**:
- Flexible molecule analysis
- Ensemble properties
- Entropy calculations

**Quantum Requirements**:
- Qubits: Medium (10-16)
- Shots: 2,048 - 8,192
- Time: 10-45 minutes

**Quantum Algorithm**: Quantum Approximate Optimization Algorithm (QAOA)

**Output Files**:
- Conformation ensemble (PDB)
- Boltzmann distribution (PNG)
- RMSD matrix (HTML)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $2.50 - $24.00

---

### 5. Electron Density (`electron_density`)

**Description**: Quantum-accurate electron density maps

**Best For**:
- Chemical bonding analysis
- Charge distribution
- Reactive site identification

**Quantum Requirements**:
- Qubits: High (15-30)
- Shots: 8,192 - 16,384
- Time: 30-120 minutes

**Quantum Algorithm**: Variational Quantum Eigensolver (VQE)

**Output Files**:
- Density isosurface (PNG)
- Volumetric data (CUBE)
- Interactive viewer (HTML)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $10.00 - $48.00

---

### 6. Molecular Orbitals (`molecular_orbitals`)

**Description**: HOMO, LUMO, and molecular orbital visualization

**Best For**:
- Reaction mechanism studies
- Spectroscopy prediction
- Electronic properties

**Quantum Requirements**:
- Qubits: High (15-25)
- Shots: 8,192 - 16,384
- Time: 30-120 minutes

**Quantum Algorithm**: VQE with orbital optimization

**Output Files**:
- Orbital isosurfaces (PNG)
- Energy level diagram (PNG)
- Orbital coefficients (JSON)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $10.00 - $48.00

---

### 7. Reaction Pathway (`reaction_pathway`)

**Description**: Quantum-computed reaction coordinates

**Best For**:
- Transition state theory
- Reaction kinetics
- Catalysis studies

**Quantum Requirements**:
- Qubits: High (20-40)
- Shots: 8,192 - 16,384
- Time: 60-240 minutes

**Quantum Algorithm**: Variational Quantum Deflation (VQD)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $10.00 - $48.00

---

### 8. Protein Folding (`protein_folding`)

**Description**: Quantum simulation of protein folding dynamics

**Best For**:
- Misfolding diseases
- Protein design
- Folding kinetics

**Quantum Requirements**:
- Qubits: High (20-50)
- Shots: 8,192 - 32,768
- Time: 60-480 minutes

**Quantum Algorithm**: Quantum Molecular Dynamics (QMD)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $10.00 - $96.00

---

### 9. Docking Simulation (`docking_simulation`)

**Description**: Quantum-enhanced molecular docking

**Best For**:
- Virtual screening
- Binding mode prediction
- Drug design

**Quantum Requirements**:
- Qubits: Medium-High (12-25)
- Shots: 4,096 - 8,192
- Time: 20-90 minutes

**Quantum Algorithm**: Quantum Annealing

**Output Files**:
- Docking poses (PDB)
- Scoring histogram (PNG)
- Interaction fingerprint (JSON)

**Cost Estimate**:
- Simulator: FREE
- IBM Hardware: $5.00 - $24.00

---

## Quantum Backends

### Simulators (Free / Low Cost)

#### 1. Qiskit Simulator (`qiskit_simulator`)

- **Type**: Classical simulator
- **Cost**: FREE
- **Max Qubits**: 30
- **Speed**: Fast (local)
- **Best For**: Development, testing, small molecules
- **Authentication**: None required

**Example**:
```json
{
  "backend_preference": "qiskit_simulator",
  "shots": 1024
}
```

---

#### 2. IonQ Simulator (`ionq_simulator`)

- **Type**: Cloud simulator
- **Cost**: $0.01/shot
- **Max Qubits**: 29
- **Speed**: Fast
- **Best For**: Testing IonQ compatibility
- **Authentication**: API key required

---

#### 3. AWS SV1 (`aws_sv1`)

- **Type**: State vector simulator
- **Cost**: $0.01/shot
- **Max Qubits**: 34
- **Speed**: Medium
- **Best For**: Large qubit simulations
- **Authentication**: AWS credentials required

---

### Quantum Hardware (Premium)

#### 4. IBM Torino (`ibm_torino`)

- **Type**: Superconducting quantum computer
- **Cost**: $3.00/shot
- **Qubits**: 133
- **Fidelity**: 99.95%
- **Queue Time**: ~35 hours (free tier), < 1 hour (paid)
- **Best For**: Large proteins, complexes
- **Authentication**: IBM Quantum token required

**Specifications**:
- Topology: Heavy-hex lattice
- T1: ~100 μs
- T2: ~150 μs
- Gate Time: ~100 ns
- Error Rate: 0.05%

**Example**:
```json
{
  "backend_preference": "ibm_torino",
  "shots": 4096,
  "budget_usd": 50.0
}
```

---

#### 5. IBM Brisbane (`ibm_brisbane`)

- **Type**: Superconducting quantum computer
- **Cost**: $1.25/shot
- **Qubits**: 127
- **Fidelity**: 99.95%
- **Queue Time**: ~20 hours (free tier)
- **Best For**: Standard protein work
- **Authentication**: IBM Quantum token required

---

#### 6. IonQ Forte (`ionq_forte`)

- **Type**: Trapped ion quantum computer
- **Cost**: $3.00/shot
- **Qubits**: 36
- **Fidelity**: 99.98%
- **Queue Time**: Variable
- **Best For**: High-fidelity calculations
- **Authentication**: IonQ API key required

**Specifications**:
- Technology: Trapped Ytterbium ions
- All-to-all connectivity
- Gate fidelity: 99.98%
- Measurement fidelity: 99.9%

---

#### 7. IonQ QPU (`ionq_qpu`)

- **Type**: Trapped ion quantum computer
- **Cost**: $2.00/shot
- **Qubits**: 36
- **Fidelity**: 99.90%
- **Queue Time**: Variable
- **Best For**: Cost-effective production
- **Authentication**: IonQ API key required

---

## Compatibility Matrix

### Molecule Type × Backend

| Molecule Type | Qiskit Sim | IonQ Sim | IBM Torino | IBM Brisbane | IonQ Forte |
|---------------|-----------|----------|------------|--------------|------------|
| Protein | ✅ | ✅ | ✅ | ✅ | ⚠️ Limited |
| DNA | ✅ | ✅ | ✅ | ✅ | ⚠️ Limited |
| RNA | ✅ | ✅ | ✅ | ✅ | ✅ |
| Small Molecule | ✅ | ✅ | ✅ | ✅ | ✅ |
| Antibody | ⚠️ Limited | ⚠️ Limited | ✅ | ✅ | ❌ |
| Protein Complex | ❌ | ❌ | ✅ | ⚠️ Limited | ❌ |
| Metabolite | ✅ | ✅ | ✅ | ✅ | ✅ |

**Legend**:
- ✅ Fully supported
- ⚠️ Limited (small systems only)
- ❌ Not recommended

---

### Visualization Type × Complexity

| Viz Type | Qubits | Shots | Time | Cost (IBM) | Best Backend |
|----------|--------|-------|------|------------|--------------|
| structure_3d | 4-8 | 1K | < 1 min | $1.25 | qiskit_sim |
| energy_landscape | 8-15 | 2K-4K | 5-30 min | $2.50-$12 | ibm_brisbane |
| binding_affinity | 12-20 | 4K-8K | 15-60 min | $5-$24 | ibm_brisbane |
| conformational_sampling | 10-16 | 2K-8K | 10-45 min | $2.50-$24 | ionq_forte |
| electron_density | 15-30 | 8K-16K | 30-120 min | $10-$48 | ibm_torino |
| molecular_orbitals | 15-25 | 8K-16K | 30-120 min | $10-$48 | ibm_torino |
| reaction_pathway | 20-40 | 8K-16K | 60-240 min | $10-$48 | ibm_torino |
| protein_folding | 20-50 | 8K-32K | 60-480 min | $10-$96 | ibm_torino |
| docking_simulation | 12-25 | 4K-8K | 20-90 min | $5-$24 | ionq_forte |

---

## Cost Optimization

### Strategy 1: Start with Simulators

Always test with free simulators before using hardware:

```json
{
  "backend_preference": "qiskit_simulator",
  "shots": 1024
}
```

**Savings**: 100% (FREE vs $3,000+)

---

### Strategy 2: Reduce Shot Count

Use minimum shots for your accuracy requirement:

```python
# Development
"shots": 1024  # $1.25 - $3.00

# Production
"shots": 2048  # $2.50 - $6.00

# High accuracy
"shots": 4096  # $5.00 - $12.00
```

**Savings**: 50-75%

---

### Strategy 3: Use Budget Constraints

Set automatic budget limits:

```json
{
  "budget_usd": 10.0,
  "max_time_hours": 2.0,
  "accuracy_target": 0.90
}
```

The optimizer will automatically:
- Reduce shots if needed
- Select cheaper backend
- Adjust QEC code

**Savings**: 30-60%

---

### Strategy 4: Batch Similar Jobs

Submit multiple similar jobs together to amortize queue time:

```python
jobs = []
for molecule in molecule_library:
    job = submit_job({
        "molecule_data": molecule,
        "backend_preference": "ibm_brisbane",
        "shots": 2048
    })
    jobs.append(job)
```

**Savings**: 20-40% in wall-clock time

---

### Strategy 5: Choose Right Backend

| Use Case | Recommended Backend | Cost Savings |
|----------|-------------------|--------------|
| Quick prototyping | qiskit_simulator | 100% (FREE) |
| Small molecules | ibm_brisbane | 58% vs ibm_torino |
| High fidelity needed | ionq_forte | Worth premium |
| Bulk production | ionq_qpu | 33% vs ionq_forte |

---

## Performance Tuning

### Qubit Optimization

**Automatic**: Quantum Graphs automatically determines optimal qubit count based on molecular complexity.

**Manual Override**:
```python
# If you know your system better
"molecule_data": {
    "num_atoms": 50,
    "force_qubits": 12  # Override automatic calculation
}
```

---

### Shot Optimization

**Rule of Thumb**:
```
shots = 1 / (1 - accuracy)²
```

**Examples**:
- 90% accuracy: 100 shots
- 95% accuracy: 400 shots
- 99% accuracy: 10,000 shots

**Recommendation**: Use 2,048-4,096 for most applications.

---

### Circuit Depth Reduction

The optimizer automatically minimizes circuit depth by:
- Using efficient gate decompositions
- Applying circuit optimization passes
- Removing redundant gates

**Manual Control**:
```json
{
  "optimization_level": 3,  // 0-3, higher = more optimization
  "transpile_options": {
    "approximation_degree": 1.0
  }
}
```

---

## Use Case Examples

### Example 1: Drug Discovery (Small Molecule)

**Goal**: Screen 100 drug candidates for binding affinity

**Configuration**:
```json
{
  "molecule_type": "small_molecule",
  "viz_type": "binding_affinity",
  "backend_preference": "ibm_brisbane",
  "shots": 2048,
  "budget_usd": 500.0
}
```

**Expected Results**:
- Time: 5-10 minutes per molecule
- Cost: $2.50 per molecule
- Total: $250 for 100 molecules
- Accuracy: 95%

---

### Example 2: Antibody Engineering

**Goal**: Optimize antibody-antigen interface

**Configuration**:
```json
{
  "molecule_type": "antibody",
  "viz_type": "conformational_sampling",
  "backend_preference": "ibm_torino",
  "shots": 4096,
  "budget_usd": 50.0,
  "accuracy_target": 0.98
}
```

**Expected Results**:
- Time: 45-60 minutes
- Cost: $12-$15
- Conformations: 20-50 sampled
- Accuracy: 98%

---

### Example 3: Protein Folding Simulation

**Goal**: Understand misfolding pathways

**Configuration**:
```json
{
  "molecule_type": "protein",
  "viz_type": "protein_folding",
  "backend_preference": "ibm_torino",
  "shots": 8192,
  "max_time_hours": 4.0,
  "accuracy_target": 0.95
}
```

**Expected Results**:
- Time: 2-4 hours
- Cost: $25-$50
- Folding intermediates: 10-20 states
- Accuracy: 95%

---

### Example 4: High-Throughput Screening

**Goal**: Screen 1000 compounds (budget: $1000)

**Optimized Configuration**:
```json
{
  "molecule_type": "small_molecule",
  "viz_type": "structure_3d",
  "backend_preference": "qiskit_simulator",  // FREE!
  "shots": 1024
}
```

**Results**:
- Time: 1-2 seconds per molecule
- Cost: $0 (FREE simulator)
- Total time: 30 minutes for 1000 molecules
- Then use hardware for top 20 hits

---

## Configuration Best Practices

### 1. Development Workflow

```
1. Test with qiskit_simulator (FREE)
2. Validate with ionq_simulator ($0.01/shot)
3. Production run on ibm_brisbane or ibm_torino
```

### 2. Cost-Performance Tradeoff

```
Budget < $10:      Use simulators
Budget $10-$50:    Use ibm_brisbane
Budget $50-$200:   Use ibm_torino or ionq_forte
Budget > $200:     Contact for enterprise pricing
```

### 3. Accuracy Requirements

```
Quick tests:       accuracy_target = 0.85
Standard:          accuracy_target = 0.95
Publications:      accuracy_target = 0.98
```

### 4. Time Constraints

```
Interactive (<5 min):  qiskit_simulator
Same day (<1 hour):    ibm_brisbane (paid tier)
Production (1-24h):    ibm_torino (free tier OK)
```

---

## Troubleshooting

### "Backend not available"

**Solution**: Check backend status at [IBM Quantum Status](https://quantum.ibm.com/services/resources)

### "Quota exceeded"

**Solution**: Upgrade tier at [BioQL Pricing](https://api.bioql.bio/pricing)

### "Circuit too large"

**Solution**: Reduce complexity or increase backend qubit limit

### "Cost exceeds budget"

**Solution**: Reduce shots, use cheaper backend, or increase budget_usd

---

## Next Steps

- [API Reference](API_REFERENCE.md) - Complete API documentation
- [VQE Algorithm](VQE_ALGORITHM.md) - Understanding the quantum algorithms
- [Visualization Guide](VISUALIZATION_GUIDE.md) - Interpreting results
- [IBM Integration](IBM_QUANTUM_INTEGRATION.md) - IBM Quantum setup

---

## Support

For configuration questions:
- Email: support@quantum-graphs.bio
- Discord: [https://discord.gg/bioql](https://discord.gg/bioql)
- Documentation: [https://docs.quantum-graphs.bio](https://docs.quantum-graphs.bio)
