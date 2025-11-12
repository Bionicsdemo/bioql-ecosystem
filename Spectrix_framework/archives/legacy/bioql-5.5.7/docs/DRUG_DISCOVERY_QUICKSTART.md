# BioQL Drug Discovery Pack - Quick Start Guide

Welcome to the BioQL Drug Discovery Pack! This guide will get you started with molecular docking, visualization, and dynamic library calls in minutes.

## Installation

```bash
# Basic installation
pip install bioql

# With drug discovery features
pip install bioql[vina,viz]

# Complete installation (all features)
pip install bioql[vina,viz,openmm,dev]
```

## Quick Examples

### 1. Molecular Docking (CLI)

```bash
# Using AutoDock Vina
bioql dock \
  --receptor protein.pdb \
  --smiles "CC(=O)OC1=CC=CC=C1C(=O)O" \
  --backend vina \
  --out results/

# Using Quantum Backend
bioql dock \
  --receptor protein.pdb \
  --smiles "CCO" \
  --backend quantum \
  --api-key YOUR_KEY
```

### 2. Molecular Docking (Python API)

```python
from bioql.docking import dock

# Dock aspirin to COX-2
result = dock(
    receptor="cox2.pdb",
    ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
    backend="vina",
    output_dir="results/cox2_aspirin"
)

print(f"Binding score: {result.score:.2f} kcal/mol")
print(f"Output: {result.output_complex}")
```

### 3. Ligand Preparation

```python
from bioql.chem import prepare_ligand

# Prepare caffeine from SMILES
result = prepare_ligand(
    smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    output_path="caffeine.pdb",
    add_hydrogens=True,
    optimize_geometry=True
)

print(f"Molecular weight: {result.molecular_weight:.2f} g/mol")
```

### 4. Visualization

```python
from bioql.visualize import visualize_complex

# Visualize protein-ligand complex
result = visualize_complex(
    receptor_path="protein.pdb",
    ligand_path="ligand.pdb",
    output_image="complex.png",
    output_session="complex.pse"  # PyMOL session
)
```

Or via CLI:

```bash
bioql visualize \
  --structure complex.pdb \
  --output complex.png \
  --style cartoon
```

### 5. Dynamic Library Calls (🔮 NEW!)

Call **any** Python library using natural language:

```python
from bioql import dynamic_call

# Calculate molecular properties with RDKit
result = dynamic_call(
    "Use RDKit to calculate molecular weight of aspirin SMILES CC(=O)OC1=CC=CC=C1C(=O)O"
)
print(f"MW: {result.result} g/mol")

# NumPy calculations
result = dynamic_call(
    "Use numpy to calculate mean of array [1, 2, 3, 4, 5]"
)
print(f"Mean: {result.result}")

# Pandas data analysis
result = dynamic_call(
    "Use pandas to read CSV file data.csv and show first 5 rows"
)
print(result.result)
```

Or via CLI:

```bash
bioql call "Use RDKit to calculate molecular weight of SMILES CCO"
bioql call "Use numpy to calculate mean of array [1, 2, 3, 4, 5]"
```

## Complete Workflow Example

```python
from bioql.chem import prepare_ligand, prepare_receptor
from bioql.docking import dock
from bioql.visualize import visualize_complex

# 1. Prepare receptor
receptor = prepare_receptor(
    "target.pdb",
    remove_waters=True,
    output_path="receptor_clean.pdb"
)

# 2. Prepare ligand from SMILES
ligand = prepare_ligand(
    "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
    output_path="ligand.pdb"
)

# 3. Perform docking
docking = dock(
    receptor=receptor.output_path,
    ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
    backend="auto",  # Auto-select best backend
    output_dir="docking_results/"
)

# 4. Visualize results
viz = visualize_complex(
    receptor_path=receptor.output_path,
    ligand_path=ligand.output_path,
    output_image="binding_site.png"
)

print(f"✅ Workflow complete!")
print(f"   Binding score: {docking.score:.2f} kcal/mol")
print(f"   Visualization: {viz.output_path}")
```

## Key Features

### Molecular Docking
- **Multiple backends**: AutoDock Vina (classical) + Quantum computing
- **Auto backend selection**: Intelligent fallback system
- **SMILES input**: Direct from chemical notation
- **Configurable search**: Custom binding site and box size

### Chemistry Tools
- **Ligand prep**: SMILES → 3D with optimization
- **Receptor prep**: PDB cleaning and preparation
- **Format conversion**: PDB, PDBQT, MOL2, SDF
- **Multiple engines**: RDKit, OpenBabel, Meeko

### Visualization
- **PyMOL integration**: Publication-quality rendering
- **Web fallback**: py3Dmol for Jupyter notebooks
- **Complex rendering**: Protein-ligand visualization
- **Export options**: PNG, TIFF, PyMOL sessions

### Dynamic Library Bridge (Meta-wrapper)
- **Natural language**: Call any library without coding
- **Pre-configured**: RDKit, NumPy, Pandas, Biopython, PyMOL
- **Extensible**: Register your own libraries
- **Automatic parsing**: Extracts arguments from text

## Configuration

### API Keys (for Quantum Backend)

```bash
# Set environment variable
export BIOQL_API_KEY=your_key_here

# Or pass directly
bioql dock --api-key YOUR_KEY ...
```

Get your API key at: https://bioql.com/signup

### External Tools

- **AutoDock Vina**: Download from http://vina.scripps.edu/
- **PyMOL**: Install via `conda install -c conda-forge pymol-open-source`

## Troubleshooting

### "Vina executable not found"
```bash
# Install AutoDock Vina
# Download from: http://vina.scripps.edu/download.html
# Add to PATH or specify path in code
```

### "PyMOL not available"
```bash
pip install bioql[viz]
# Or for PyMOL:
conda install -c conda-forge pymol-open-source
```

### "RDKit/Meeko required"
```bash
pip install bioql[vina]
```

## Examples Repository

See `examples/drug_discovery_example.py` for comprehensive demonstrations:
- Vina docking workflow
- Quantum docking
- Ligand preparation
- Visualization
- Dynamic library calls
- Complete end-to-end workflow

## Documentation

- **Full API Reference**: https://docs.bioql.com/api
- **Drug Discovery Guide**: https://docs.bioql.com/drug-discovery
- **Tutorials**: https://docs.bioql.com/tutorials
- **Technical Reference**: `TECHNICAL_REFERENCE.md`

## Support

- **Issues**: https://github.com/bioql/bioql/issues
- **Discussions**: https://github.com/bioql/bioql/discussions
- **Email**: support@bioql.com

## What's New in v2.1.0

✨ **Major Features:**
- Complete drug discovery toolkit
- AutoDock Vina integration
- Quantum docking backend
- Dynamic library bridge (meta-wrapper)
- Molecular visualization
- CLI commands for docking and visualization

🔧 **Technical:**
- Backward compatible with v2.0.x
- Optional dependencies via extras
- Graceful fallbacks
- Production-ready logging

📚 **Documentation:**
- Quick start guide
- Complete API reference
- Example scripts
- CHANGELOG

## License

MIT License - See LICENSE file for details

---

**Happy Docking!** 🧬🔬

Questions? Open an issue or check the docs at https://docs.bioql.com