# QPHAROS Usage Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Configuration](#configuration)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Installation

```bash
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/QPHAROS
pip install -r requirements.txt
export BIOQL_API_KEY="your_api_key_here"
```

### 2. Run Quick Demo

```bash
python quick_start.py
```

This will run a quick demonstration using berberine as a test molecule.

## Basic Usage

### Example 1: Binding Prediction

```python
from QPHAROS import QuantumBindingPredictor, QuantumBackend, QPHAROSConfig

# Configuration
config = QPHAROSConfig(backend="ibm_torino")
backend = QuantumBackend(config)
predictor = QuantumBindingPredictor(backend, config)

# Predict binding
result = predictor.predict_binding(
    ligand_smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
    protein_pdb="6B3J"  # GLP-1R
)

print(f"Binding Affinity: {result['binding_affinity']:.2f} kcal/mol")
print(f"Ki: {result['ki']:.2f} nM")
```

### Example 2: ADMET Analysis

```python
from QPHAROS import QuantumADMETOptimizer, QuantumBackend, QPHAROSConfig

config = QPHAROSConfig()
backend = QuantumBackend(config)
optimizer = QuantumADMETOptimizer(backend, config)

# Analyze ADMET properties
admet = optimizer.predict_admet("CC(=O)Oc1ccccc1C(=O)O")  # Aspirin

# Check Lipinski's Rule
lipinski = optimizer.check_lipinski("CC(=O)Oc1ccccc1C(=O)O")
print(f"Lipinski Pass: {lipinski['all_pass']}")

# Calculate drug-likeness
score = optimizer.calculate_drug_likeness_score("CC(=O)Oc1ccccc1C(=O)O")
print(f"Drug-likeness: {score:.3f}")
```

### Example 3: Complete Pipeline

```python
from QPHAROS import QuantumDrugDesignPipeline, QPHAROSConfig

# Initialize pipeline
pipeline = QuantumDrugDesignPipeline(
    target_protein="6B3J",
    disease_profile="type 2 diabetes",
    backend="ibm_torino"
)

# Run complete drug design
results = pipeline.design_drug(
    iterations=50,
    save_results=True
)

print(f"Best Molecule: {results['molecule']}")
print(f"Score: {results['score']:.4f}")
```

## Advanced Features

### Batch Ligand Screening

```python
# Screen multiple ligands
ligands = [
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
    "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
    "CN(C)C(=N)NC(=N)N",  # Metformin
]

results = predictor.predict_binding_batch(ligands, "6B3J")

# Rank by affinity
ranked = predictor.rank_ligands(ligands, "6B3J")
for smiles, affinity in ranked:
    print(f"{smiles}: {affinity:.2f} kcal/mol")
```

### Molecular Generation

```python
from QPHAROS import QuantumMolecularGAN, QuantumBackend, QPHAROSConfig

config = QPHAROSConfig()
backend = QuantumBackend(config)
qgan = QuantumMolecularGAN(backend, config)

# Generate novel molecules
training_molecules = [
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "CC(=O)Oc1ccccc1C(=O)O",
]

generated = qgan.generate_molecules(
    training_molecules=training_molecules,
    n_generate=20,
    target_properties={'drug_like': True}
)

print(f"Generated {len(generated)} molecules")
```

### Analog Generation

```python
# Generate analogs of a reference molecule
reference = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"  # Caffeine

analogs = qgan.generate_analogs(
    reference_molecule=reference,
    n_analogs=10
)

for analog in analogs:
    print(analog)
```

### Scaffold Hopping

```python
# Generate molecules with different scaffolds
scaffold_hops = qgan.scaffold_hopping(
    reference_molecule=reference,
    n_candidates=10
)
```

### Molecular Dynamics Simulation

```python
from QPHAROS import QuantumMolecularDynamics, QuantumBackend, QPHAROSConfig

config = QPHAROSConfig()
backend = QuantumBackend(config)
md_sim = QuantumMolecularDynamics(backend, config)

# Run MD simulation
trajectory = md_sim.simulate_binding_dynamics(
    ligand_smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    protein_pdb="6B3J",
    simulation_time=1.0  # ps
)

# Calculate stability
stability = md_sim.calculate_stability(
    ligand_smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    protein_pdb="6B3J"
)
print(f"Stability: {stability:.3f}")

# Predict residence time
residence_time = md_sim.predict_residence_time(
    ligand_smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    protein_pdb="6B3J"
)
print(f"Residence Time: {residence_time:.2e} seconds")
```

## Configuration

### Full Configuration Options

```python
from QPHAROS import QPHAROSConfig

config = QPHAROSConfig(
    # Backend settings
    backend="ibm_torino",
    shots=4096,
    qec_enabled=True,
    qec_type="surface_code",  # or "steane", "shor"
    logical_qubits=2,

    # Molecular encoding
    qubits_per_atom=3,
    max_molecular_weight=500.0,

    # Binding prediction
    binding_layers=6,
    binding_qubits=20,

    # ADMET constraints
    max_molecular_weight_admet=500.0,
    logP_range=(-0.4, 5.6),
    max_h_bond_donors=5,
    max_h_bond_acceptors=10,

    # Molecular generation
    generator_qubits=15,
    generator_layers=8,

    # Molecular dynamics
    md_time_steps=100,
    md_timestep=0.01,
    trotter_order=4,

    # Optimization
    max_iterations=100,
    convergence_threshold=1e-4,

    # Scoring weights
    binding_weight=0.4,
    admet_weight=0.3,
    stability_weight=0.3
)
```

### Backend Selection

```python
# Use simulator for testing
config = QPHAROSConfig(backend="simulator")

# Use IBM Torino (133 qubits)
config = QPHAROSConfig(backend="ibm_torino")

# Use IonQ
config = QPHAROSConfig(backend="ionq")

# Use AWS Braket
config = QPHAROSConfig(backend="aws_braket")
```

### QEC Configuration

```python
# Surface code (best for large circuits)
config = QPHAROSConfig(
    qec_enabled=True,
    qec_type="surface_code",
    logical_qubits=2
)

# Steane code (7:1 overhead)
config = QPHAROSConfig(
    qec_enabled=True,
    qec_type="steane",
    logical_qubits=3
)

# No QEC (for simulators)
config = QPHAROSConfig(qec_enabled=False)
```

## Best Practices

### 1. Start with Small Molecules

```python
# Test with simple molecules first
test_molecules = [
    "C",      # Methane
    "CC",     # Ethane
    "CCO",    # Ethanol
]
```

### 2. Use Simulator for Development

```python
# Develop with simulator
config_dev = QPHAROSConfig(backend="simulator", shots=1000)

# Deploy to real hardware
config_prod = QPHAROSConfig(backend="ibm_torino", shots=4096)
```

### 3. Incremental Complexity

```python
# Start with binding only
binding_result = predictor.predict_binding(ligand, protein)

# Add ADMET
admet_result = optimizer.predict_admet(ligand)

# Finally add MD
md_result = md_sim.simulate_binding_dynamics(ligand, protein)
```

### 4. Batch Processing

```python
# Process multiple ligands efficiently
results = []
for ligand in ligand_library:
    result = predictor.predict_binding(ligand, protein)
    results.append(result)
```

### 5. Save Results

```python
import json
from datetime import datetime

# Save results with timestamp
results = pipeline.design_drug(iterations=100, save_results=True)

# Results automatically saved to: qpharos_results/drug_design_YYYYMMDD_HHMMSS.json
```

## Troubleshooting

### Error: BioQL not installed

```bash
pip install bioql
```

### Error: API key not set

```bash
export BIOQL_API_KEY="your_key_here"
```

Or in Python:
```python
import os
os.environ['BIOQL_API_KEY'] = 'your_key_here'
```

### Error: Backend not available

Check backend status:
```python
backend_info = backend.get_backend_info()
print(backend_info)
```

Try simulator first:
```python
config = QPHAROSConfig(backend="simulator")
```

### Error: Too many qubits required

Reduce molecular size or complexity:
```python
config = QPHAROSConfig(
    binding_qubits=15,  # Reduced from 20
    generator_qubits=12  # Reduced from 15
)
```

### Slow Performance

1. Reduce shots:
```python
config = QPHAROSConfig(shots=1000)  # Instead of 4096
```

2. Use shallower circuits:
```python
config = QPHAROSConfig(
    binding_layers=4,  # Instead of 6
    generator_layers=6  # Instead of 8
)
```

3. Disable QEC for testing:
```python
config = QPHAROSConfig(qec_enabled=False)
```

### Memory Issues

Process in smaller batches:
```python
batch_size = 10
for i in range(0, len(ligands), batch_size):
    batch = ligands[i:i+batch_size]
    results = predictor.predict_binding_batch(batch, protein)
```

## Resource Estimation

```python
# Estimate quantum resources
resources = backend.estimate_resources(
    n_qubits=20,
    circuit_depth=6
)

print(f"Physical qubits: {resources['physical_qubits']}")
print(f"Estimated time: {resources['estimated_time_ms']} ms")
```

## Getting Help

- **Documentation:** See README.md and ARCHITECTURE.md
- **Examples:** Check examples/ directory
- **Issues:** https://github.com/spectrixrd/bioql/issues
- **Email:** support@bioql.bio

## Next Steps

1. Try the examples in `examples/`
2. Read ARCHITECTURE.md for system details
3. Explore individual layers in `layers/`
4. Customize configuration in `core/config.py`
5. Build your own drug discovery workflow!

Happy quantum drug discovery! 🧬⚛️
