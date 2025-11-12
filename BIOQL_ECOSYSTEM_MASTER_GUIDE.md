# BioQL Ecosystem - Master User Guide

**Version:** 1.0

**Last Updated:** November 2025

**Target Audience:** Enterprise Clients, Research Institutions, Pharmaceutical Companies

---

## Table of Contents

1. [Overview](#overview)
2. [Core Components](#core-components)
3. [Getting Started](#getting-started)
4. [Component Installation](#component-installation)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [Integration Guide](#integration-guide)
8. [VS Code Extension](#vs-code-extension)
9. [Web Interfaces](#web-interfaces)
10. [Best Practices](#best-practices)
11. [Support](#support)

---

## Overview

The **BioQL Ecosystem** is a comprehensive quantum computing platform for drug discovery, bioinformatics, and pharmaceutical research. It combines quantum algorithms, error correction, AI-guided design, and enterprise-grade tools to accelerate computational biology workflows.

### Key Benefits

- Real Quantum Hardware - Execute on IBM Quantum (156+ qubits)
- Quantum Error Correction - Surface code, Steane, Shor codes
- Drug Discovery Pipeline - Docking, ADME, toxicity, design
- Natural Language Interface - Write quantum programs in plain English
- Multi-Omics Support - Genomics, proteomics, metabolomics
- Enterprise Ready - API authentication, audit logs, compliance

---

## Core Components

### 1. BioQL Framework (v6.0.1)

Core quantum computing library for bioinformatics.

**PyPI:** `pip install bioql`

**Key Features:**

- Natural language quantum programming
- 12+ quantum backends (IBM, IonQ, Simulator)
- Molecular docking and binding affinity
- ADME/Tox prediction
- Protein folding (QAOA)
- CRISPR guide design
- Remote execution via API

**Use Cases:**

- Molecular docking calculations
- Quantum chemistry simulations
- Drug candidate screening
- Genomic analysis

---

### 2. Quillow (v1.0.0)

Willow-style quantum error correction system.

**PyPI:** `pip install quillow`

**Key Features:**

- Surface code QEC (distance 3, 5, 7)
- MWPM syndrome decoding
- GPU acceleration (CUDA)
- Real-time error correction
- Sub-100μs latency per shot
- BioQL integration layer

**Use Cases:**

- High-fidelity quantum computations
- Error-corrected molecular simulations
- Production quantum workflows
- Quantum algorithm benchmarking

---

### 3. QPHAROS (v1.1.0)

5-layer quantum pharmaceutical optimization system.

**PyPI:** `pip install qpharos`

**Key Features:**

- Quantum molecular docking
- AI-guided drug design (Quantum GANs)
- ADMET prediction
- Multi-target screening
- Binding site analysis
- Pharmacophore modeling

**Use Cases:**

- Lead optimization
- Virtual screening
- De novo drug design
- Target identification

---

### 4. BioQL VS Code Extension (v7.0.4)

AI-powered code generation for quantum drug discovery.

**Installation:** Via `.vsix` file

**Key Features:**

- Natural language to BioQL code
- Context-aware suggestions
- Docking workflow templates
- CRISPR design templates
- Multi-omics pipelines
- Automatic QEC configuration

**Use Cases:**

- Rapid prototyping
- Learning BioQL syntax
- Template-based workflows
- Educational purposes

---

### 5. BioQL Workflow Studio

Web-based visual workflow builder.

**Access:** `http://your-server:8080/workflows.html`

**Key Features:**

- Drag-and-drop node interface
- Real-time quantum job monitoring
- Global settings propagation
- JSON workflow export/import
- Multi-backend execution
- Queue position tracking

**Use Cases:**

- Non-programmers building workflows
- Visual pipeline design
- Job monitoring dashboards
- Team collaboration

---

## Getting Started

### Step 1: Get Your API Key

Sign up at the BioQL platform to obtain your API key:

```bash
# API keys are provided after registration
# Format: __BIOQL_REDACTED__
```

**Important:** Keep your API key secure and never commit it to version control.

### Step 2: Set Environment Variables

```bash
# Linux/macOS
export BIOQL_API_KEY="your_api_key_here"

# Windows (PowerShell)
$env:BIOQL_API_KEY="your_api_key_here"

# Or use a .env file
echo "BIOQL_API_KEY=your_api_key_here" > .env
```

### Step 3: Install Core Framework

```bash
pip install bioql
```

### Step 4: Verify Installation

```python
from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY')

result = quantum(
    "Create a Bell state",
    backend='simulator',
    shots=1000,
    api_key=api_key
)

print(f"Success: {result.success}")
print(f"Counts: {result.counts}")
```

---

## Component Installation

### Install BioQL Framework

```bash
# Basic installation
pip install bioql

# With visualization support
pip install bioql[viz]

# With AutoDock Vina support
pip install bioql[vina]

# With quantum chemistry
pip install bioql[quantum_chemistry]

# Everything
pip install bioql[viz,vina,quantum_chemistry]
```

### Install Quillow (QEC)

```bash
# Basic installation
pip install quillow

# With GPU acceleration
pip install quillow[gpu]

# With cloud support
pip install quillow[cloud]
```

### Install QPHAROS

```bash
# QPHAROS automatically installs BioQL
pip install qpharos
```

### Install VS Code Extension

1. Download `bioql-assistant-7.0.4.vsix` from your provider
2. Open VS Code
3. Go to Extensions (Ctrl+Shift+X)
4. Click `...` menu → "Install from VSIX..."
5. Select the downloaded `.vsix` file
6. Reload VS Code

### Deploy Workflow Studio

Contact your BioQL provider for deployment instructions or access credentials.

---

## Configuration

### BioQL Configuration

Create a configuration file `~/.bioql/config.yaml`:

```yaml
# API Settings
api:
  key: ${BIOQL_API_KEY}  # Uses environment variable
  url: https://api.bioql.bio
  timeout: 300

# Default Backend
backend:
  default: simulator
  preferred_hardware: ibm_fez  # 156 qubits, Online

# Quantum Error Correction
qec:
  enabled: true
  type: surface_code
  correction_level: low
  num_logical_qubits: 2

# Execution Settings
execution:
  default_shots: 2000
  max_retries: 3
  cache_results: true
  cache_dir: ~/.bioql/cache

# Logging
logging:
  level: INFO
  file: ~/.bioql/logs/bioql.log
```

### Quillow Configuration

Create `~/.quillow/config.yaml`:

```yaml
# QEC Settings
qec:
  code_distance: 7  # 3, 5, or 7
  decoder: pymatching  # pymatching, fusion_blossom
  noise_model: depolarizing
  physical_error_rate: 0.001

# Performance
performance:
  use_gpu: true
  batch_size: 10000
  num_workers: 4

# Backend
backend:
  type: stim  # stim, modal, custom
  simulator_seed: 42
```

### QPHAROS Configuration

```python
from qpharos import set_config

set_config({
    'api_key': 'your_bioql_api_key',
    'backend': 'ibm_fez',
    'shots': 2000,
    'qec': {
        'enabled': True,
        'type': 'surface_code',
        'level': 'low'
    },
    'docking': {
        'exhaustiveness': 8,
        'num_poses': 9
    }
})
```

---

## Usage Examples

### Example 1: Basic Molecular Docking (BioQL)

```python
from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY')

# Dock aspirin to COX-2 enzyme
ligand_smiles = "CC(=O)Oc1ccccc1C(=O)O"
receptor_pdb = "5KIR"

result = quantum(
    f"Analyze ligand with SMILES {ligand_smiles} docking to receptor PDB {receptor_pdb}. "
    "Calculate binding affinity using VQE quantum computation. "
    "Identify key molecular interactions from quantum states. "
    "Calculate Ki and IC50 from quantum binding energies.",
    backend='ibm_fez',
    shots=2000,
    api_key=api_key,
    error_correction='surface_code',
    correction_level='low',
    num_logical_qubits=2,
)

print(f"\n✅ Docking Complete!")
print(f"Success: {result.success}")

if result.success:
    bio = getattr(result, 'bio_interpretation', {})

    if bio.get('binding_affinity'):
        print(f"\n⚛️  Binding Affinity: {bio['binding_affinity']:.2f} kcal/mol")
    if bio.get('ki'):
        print(f"   Ki: {bio['ki']:.2f} nM")
    if bio.get('ic50'):
        print(f"   IC50: {bio['ic50']:.2f} nM")

    if bio.get('h_bonds'):
        print(f"\n🔗 H-bonds: {bio['h_bonds']}")
```

### Example 2: Error-Corrected Computation (Quillow)

```python
from quillow import SurfaceCodeSimulator
from quillow.decoders import PyMatchingDecoder
import numpy as np

# Initialize QEC system
simulator = SurfaceCodeSimulator(
    code_distance=5,
    physical_error_rate=0.001,
    decoder=PyMatchingDecoder()
)

# Run error-corrected computation
result = simulator.run_logical_circuit(
    shots=10000,
    num_cycles=10
)

print(f"Logical Error Rate: {result.logical_error_rate:.4f}")
print(f"Physical Error Rate: {result.physical_error_rate:.4f}")
print(f"QEC Overhead: {result.qec_overhead:.2f}x")
```

### Example 3: Drug Design (QPHAROS)

```python
from qpharos import design_drug
import os

api_key = os.getenv('BIOQL_API_KEY')

# Design molecules targeting EGFR for lung cancer
result = design_drug(
    target='EGFR',
    pdb_id='1M17',
    disease='lung cancer',
    num_candidates=5,
    api_key=api_key,
    backend='ibm_fez',
    shots=2000
)

print(f"\n🧪 Generated {len(result.candidates)} candidates:\n")

for i, candidate in enumerate(result.candidates, 1):
    print(f"{i}. SMILES: {candidate.smiles}")
    print(f"   Binding Affinity: {candidate.binding_affinity:.2f} kcal/mol")
    print(f"   QED Score: {candidate.qed_score:.2f}")
    print(f"   Lipinski Pass: {candidate.lipinski_pass}")
    print()
```

### Example 4: ADME Prediction

```python
from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY')

smiles = "CC(C)Cc1ccc(cc1)C(C)C(=O)O"  # Ibuprofen

result = quantum(
    f"Predict ADME properties for molecule SMILES {smiles}. "
    "Use QNN to predict Absorption, Distribution, Metabolism, Excretion scores (0-1). "
    "Calculate bioavailability percentage and half-life in hours. "
    "Check Lipinski Rule of Five.",
    backend='simulator',
    shots=2000,
    api_key=api_key,
    error_correction='surface_code',
    correction_level='low',
    num_logical_qubits=2,
)

if hasattr(result, 'absorption'):
    print(f"\n💊 ADME Prediction:")
    print(f"   Absorption: {result.absorption:.2f}")
    print(f"   Distribution: {result.distribution:.2f}")
    print(f"   Metabolism: {result.metabolism:.2f}")
    print(f"   Excretion: {result.excretion:.2f}")
    print(f"   Bioavailability: {result.bioavailability:.1f}%")
    print(f"   Half-life: {result.half_life:.1f} hours")
```

### Example 5: CRISPR Guide Design

```python
from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY')

target_gene = "BRCA1"
pam_sequence = "NGG"  # SpCas9 PAM

result = quantum(
    f"Design CRISPR guide RNA for gene {target_gene} with PAM {pam_sequence}. "
    "Search for guide sequences with high on-target efficiency (>70%). "
    "Minimize off-target effects. Return top 5 guides with scores.",
    backend='simulator',
    shots=1000,
    api_key=api_key
)

print(f"\n✂️ CRISPR Guides for {target_gene}:")
if hasattr(result, 'guides'):
    for i, guide in enumerate(result.guides[:5], 1):
        print(f"{i}. {guide.sequence}")
        print(f"   On-target: {guide.on_target_score:.2f}")
        print(f"   Off-target: {guide.off_target_score:.2f}")
```

### Example 6: Multi-Omics Integration

```python
from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY')

# Integrate genomics, proteomics, metabolomics data
result = quantum(
    "Perform quantum multi-omics integration. "
    "Analyze genomic variants from VCF, protein expression from proteomics, "
    "and metabolite concentrations. Use quantum kernel for feature fusion. "
    "Identify disease biomarkers and pathway dysregulation.",
    backend='simulator',
    shots=2000,
    api_key=api_key,
    error_correction='surface_code',
    correction_level='low',
    num_logical_qubits=2,
)

print(f"\n🧬 Multi-Omics Analysis:")
print(f"Success: {result.success}")
```

---

## Integration Guide

### Integrate BioQL with Quillow (QEC)

```python
from bioql import quantum
from quillow import enable_qec_for_bioql

# Enable Quillow QEC for all BioQL calls
enable_qec_for_bioql(
    code_distance=5,
    decoder='pymatching'
)

# Now all quantum() calls automatically use QEC
result = quantum(
    "Run VQE for H2 molecule",
    backend='ibm_fez',
    shots=2000,
    api_key=api_key
)
# Quillow handles error correction transparently
```

### Use QPHAROS with Custom BioQL Workflows

```python
from qpharos import dock
from bioql import quantum

# Step 1: Dock with QPHAROS
docking_result = dock(
    ligand='CC(=O)Oc1ccccc1C(=O)O',
    receptor='5KIR',
    api_key=api_key
)

# Step 2: Further analyze with BioQL
if docking_result.binding_affinity < -7.0:
    adme_result = quantum(
        f"Predict ADME for SMILES {docking_result.ligand_smiles}",
        backend='simulator',
        shots=1000,
        api_key=api_key
    )

    print(f"Promising candidate!")
    print(f"Binding: {docking_result.binding_affinity} kcal/mol")
    print(f"Bioavailability: {adme_result.bioavailability}%")
```

### Call BioQL from Python Scripts

```python
#!/usr/bin/env python3
import sys
from bioql import quantum
import os

def main():
    api_key = os.getenv('BIOQL_API_KEY')

    if not api_key:
        print("ERROR: BIOQL_API_KEY not set")
        sys.exit(1)

    # Your quantum computation
    result = quantum(
        "Create a 3-qubit GHZ state",
        backend='simulator',
        shots=1000,
        api_key=api_key,
        error_correction='surface_code',
        correction_level='low',
        num_logical_qubits=2,
    )

    if result.success:
        print("✅ Success!")
        print(f"Counts: {result.counts}")
    else:
        print(f"❌ Failed: {result.error_message}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Call BioQL via REST API

Using curl:

```bash
curl -X POST https://api.bioql.bio/api/quantum/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "program": "Create a Bell state",
    "backend": "simulator",
    "shots": 1000,
    "qec": {
      "enabled": true,
      "type": "surface_code",
      "correction_level": "low",
      "num_logical_qubits": 2
    }
  }'
```

Using Python requests:

```python
import requests

response = requests.post(
    'https://api.bioql.bio/api/quantum/execute',
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    },
    json={
        'program': 'Create a Bell state',
        'backend': 'simulator',
        'shots': 1000,
        'qec': {
            'enabled': True,
            'type': 'surface_code',
            'correction_level': 'low',
            'num_logical_qubits': 2
        }
    },
    timeout=300
)

result = response.json()
print(f"Success: {result['success']}")
```

---

## VS Code Extension

### Installation

1. Download `bioql-assistant-7.0.4.vsix`
2. In VS Code: Extensions → `...` → "Install from VSIX..."
3. Select the file and reload VS Code

### Usage

#### Generate Docking Code

1. Create a new Python file: `my_docking.py`
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Type: "BioQL: Generate Docking Code"
4. Enter:
   - Ligand SMILES: `CC(=O)Oc1ccccc1C(=O)O`
   - Receptor PDB: `5KIR`
   - Backend: `ibm_fez`
5. Code is automatically generated with QEC parameters

#### Generate CRISPR Design Code

1. Press `Ctrl+Shift+P`
2. Type: "BioQL: Generate CRISPR Code"
3. Enter:
   - Gene: `BRCA1`
   - PAM: `NGG`
4. Complete CRISPR workflow generated

#### IntelliSense Support

The extension provides:

- Auto-completion for BioQL functions
- Parameter hints for `quantum()`
- SMILES validation
- PDB ID suggestions
- Backend options

### Features

- Automatic QEC parameter injection
- Template-based code generation
- Context-aware suggestions
- SMILES/PDB validation
- Multi-omics templates
- Error handling templates

---

## Web Interfaces

### BioQL Workflow Studio

**Access:** `http://your-server:8080/workflows.html`

#### Create a Workflow

1. **Login** with your API key
2. **Drag nodes** from the left panel:
   - Input (SMILES, PDB)
   - Docking
   - ADME Prediction
   - Toxicity Prediction
   - Export (JSON, CSV)
3. **Connect nodes** by dragging from output to input
4. **Configure global settings**:
   - Backend: `ibm_fez`
   - Shots: `2000`
   - QEC: Enabled
5. **Run workflow**
6. **Monitor** real-time job status
7. **Download** results as JSON

#### Node Types

**Input Nodes:** SMILES Input, PDB Input, Sequence Input

**Computation Nodes:** Docking, ADME, Toxicity, CRISPR, Folding

**Analysis Nodes:** Virtual Screening, Binding Site Analysis

**Output Nodes:** JSON Export, CSV Export, Visualization

#### Queue Monitoring

- See your position in IBM Quantum queue
- Estimated wait time
- Live status updates
- Browser notifications when complete

---

## Best Practices

### 1. Always Use QEC Parameters

Good example - Includes QEC:

```python
result = quantum(
    "Create Bell state",
    backend='ibm_fez',
    shots=2000,
    api_key=api_key,
    error_correction='surface_code',
    correction_level='low',
    num_logical_qubits=2,
)
```

Bad example - Missing QEC (job may not execute):

```python
result = quantum(
    "Create Bell state",
    backend='ibm_fez',
    shots=2000,
    api_key=api_key
)
```

### 2. Check Backend Status

```python
from bioql import get_backend_status

status = get_backend_status(api_key=api_key)

for backend in status:
    print(f"{backend.name}: {backend.status} ({backend.qubits} qubits)")

# Use online backends only
online_backends = [b.name for b in status if b.status == 'Online']
```

### 3. Handle Errors Gracefully

```python
result = quantum(
    "Your program here",
    backend='ibm_fez',
    shots=2000,
    api_key=api_key,
    error_correction='surface_code',
    correction_level='low',
    num_logical_qubits=2,
)

if not result.success:
    print(f"❌ ERROR: {result.error_message}")
    print(f"Metadata: {result.metadata}")
    # Retry with simulator if hardware fails
    result = quantum(
        "Your program here",
        backend='simulator',
        shots=2000,
        api_key=api_key
    )
```

### 4. Use Appropriate Shots

```python
# Quick testing
result = quantum(..., shots=1000)  # Fast, less accurate

# Production docking
result = quantum(..., shots=2000)  # Balanced

# High-precision calculations
result = quantum(..., shots=5000)  # Slower, more accurate
```

### 5. Validate SMILES Before Docking

```python
from bioql.utils import validate_smiles, neutralize_smiles

smiles = "CC(=O)Oc1ccccc1C(=O)O"

# Validate
is_valid, message = validate_smiles(smiles)
if not is_valid:
    print(f"Invalid SMILES: {message}")
    exit(1)

# Neutralize charged groups
smiles_neutral = neutralize_smiles(smiles)
print(f"Neutralized: {smiles_neutral}")
```

### 6. Cache Results for Expensive Computations

```python
import pickle
import hashlib

def get_cache_key(program, backend, shots):
    return hashlib.md5(f"{program}{backend}{shots}".encode()).hexdigest()

def cached_quantum(program, **kwargs):
    cache_key = get_cache_key(program, kwargs['backend'], kwargs['shots'])
    cache_file = f"cache/{cache_key}.pkl"

    # Check cache
    try:
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        pass

    # Execute
    result = quantum(program, **kwargs)

    # Save to cache
    with open(cache_file, 'wb') as f:
        pickle.dump(result, f)

    return result
```

### 7. Use Environment Variables for Secrets

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

api_key = os.getenv('BIOQL_API_KEY')
if not api_key:
    raise ValueError("BIOQL_API_KEY not set")
```

---

## Support

### Documentation

- BioQL Framework: `https://bioql.readthedocs.io`
- Quillow: `https://quillow.readthedocs.io`
- QPHAROS: `https://qpharos.readthedocs.io`

### Getting Help

For technical support, contact your BioQL provider or use the support channels provided with your license.

### Common Issues

#### Issue: "Success: False" with no error message

**Solution:** Add QEC parameters to your quantum() call:

```python
error_correction='surface_code',
correction_level='low',
num_logical_qubits=2,
```

#### Issue: "Backend ibm_torino is Paused"

**Solution:** Check backend status and use an online backend:

```python
backend='ibm_fez'  # 156 qubits, Online
# or
backend='ibm_marrakesh'  # 156 qubits, Online
```

#### Issue: "Connection timeout"

**Solution:** Increase timeout or retry:

```python
from bioql import quantum
import time

max_retries = 3
for attempt in range(max_retries):
    try:
        result = quantum(..., timeout=600)  # 10 minutes
        break
    except TimeoutError:
        if attempt < max_retries - 1:
            print(f"Retry {attempt + 1}/{max_retries}")
            time.sleep(5)
        else:
            raise
```

#### Issue: "Invalid SMILES"

**Solution:** Use RDKit to validate and canonicalize:

```python
from rdkit import Chem

mol = Chem.MolFromSmiles(smiles)
if mol is None:
    print("Invalid SMILES")
else:
    canonical_smiles = Chem.MolToSmiles(mol)
    print(f"Canonical: {canonical_smiles}")
```

---

## Appendix: Available Quantum Backends

| Backend | Qubits | Status | Topology | Best For |
|---------|--------|--------|----------|----------|
| simulator | Unlimited | Always Online | N/A | Testing, development |
| ibm_fez | 156 | Online | Heron r2 | Production docking |
| ibm_marrakesh | 156 | Online | Heron r2 | Production workloads |
| ibm_torino | 133 | Paused | Eagle r3 | (Currently unavailable) |

**Note:** Backend availability changes. Check status before execution.

---

## Appendix: QEC Parameters

### Error Correction Types

**surface_code** - Most robust, highest overhead (recommended)

**steane** - 7-qubit code, medium overhead

**shor** - 9-qubit code, lower overhead

### Correction Levels

**low** - 2 logical qubits, fast execution (recommended for most tasks)

**medium** - 4 logical qubits, better fidelity

**high** - 8+ logical qubits, maximum fidelity (very slow)

### Choosing QEC Settings

Quick testing - use low:

```python
error_correction='surface_code',
correction_level='low',
num_logical_qubits=2,
```

Production drug discovery - use low or medium:

```python
error_correction='surface_code',
correction_level='medium',
num_logical_qubits=4,
```

High-precision quantum chemistry - use medium or high:

```python
error_correction='surface_code',
correction_level='high',
num_logical_qubits=8,
```

---

**End of Master Guide**

**Version 1.0** | November 2025

© SpectrixRD. All rights reserved.
