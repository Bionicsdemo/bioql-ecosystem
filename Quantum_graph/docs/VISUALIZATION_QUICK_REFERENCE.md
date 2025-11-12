# Quantum Visualization Quick Reference

## Molecule Types and Their Visualizations

### Small Molecule (`small_molecule`, `molecule`)

**Use for:** Organic compounds, drug molecules, simple inorganics

**Visualizations Generated:**
1. Molecular Orbitals - HOMO/LUMO diagram
2. Electron Density - 2D/3D density maps
3. Bond Energy - Dissociation curve + energy decomposition

**Key Metrics:**
- HOMO-LUMO gap (eV)
- Ground state energy (Hartree)
- Bond equilibrium distance (Å)
- Energy decomposition components

---

### Protein (`protein`, `antibody`, `protein_complex`)

**Use for:** Enzymes, antibodies, protein structures

**Visualizations Generated:**
1. Secondary Structure - Helix/sheet/coil prediction
2. Protein Folding - Energy landscape + pathway
3. Ramachandran Plot - Backbone dihedral angles

**Key Metrics:**
- Secondary structure composition (%)
- Phi/psi angle distributions
- Folding energy (kcal/mol)
- Structure validation scores

---

### DNA/RNA (`dna`, `rna`)

**Use for:** Genetic material, nucleic acids, aptamers

**Visualizations Generated:**
1. Double Helix - 3D structure with base pairs
2. Base Pair Analysis - Stacking energies + H-bonds
3. Groove Width - Major/minor groove measurements

**Key Metrics:**
- GC content (%)
- Base stacking energies (kcal/mol)
- Hydrogen bond counts
- Groove widths (Å)

---

### Metabolite (`metabolite`)

**Use for:** Metabolic intermediates, small bioactive molecules

**Visualizations Generated:**
1. Metabolic Pathway - Network graph
2. Reactivity Analysis - Electrophilic/nucleophilic sites + energy profile

**Key Metrics:**
- Partial charges
- HOMO-LUMO gap (eV)
- Activation energy (kcal/mol)
- Pathway connectivity

---

## Common Visualizations (All Types)

Generated for every molecule type:

1. **Energy Histogram** - VQE energy distribution
2. **State Distribution** - Quantum measurement probabilities
3. **Interactive Plot** - Plotly-based exploration
4. **Energy Landscape** - Potential energy surface (if VQE available)
5. **Hamiltonian Viz** - Operator decomposition (if available)
6. **VQE Convergence** - Optimization history (if available)

---

## Code Examples

### Basic Usage

```python
from quantum_core.backends.visualization_generator import VisualizationGenerator

viz_gen = VisualizationGenerator(output_dir="/tmp/viz")

files = viz_gen.generate_from_quantum_results(
    job_id="job_123",
    counts={"0000": 500, "1111": 300},
    num_qubits=4,
    molecule_type="protein",  # Choose: small_molecule, protein, dna, rna, metabolite
    viz_type="energy_landscape",
    vqe_energies={"0000": -5.2, "1111": -3.4},
    ground_state_energy=-5.2
)
```

### With Full VQE Data

```python
files = viz_gen.generate_from_quantum_results(
    job_id="job_456",
    counts=quantum_results['counts'],
    num_qubits=6,
    molecule_type="small_molecule",
    viz_type="structure_3d",
    vqe_energies=vqe_results['energies'],  # Dict[str, float]
    ground_state_energy=vqe_results['ground_state'],
    energy_landscape=vqe_results['landscape'],  # List[float]
    hamiltonian_terms=25,
    convergence_history=[...],  # List[float]
)
```

---

## Output File Naming Convention

Format: `{job_id}_{visualization_type}.{extension}`

Examples:
- `job_123_energy_histogram.png`
- `job_123_molecular_orbitals.png`
- `job_123_protein_folding.png`
- `job_123_double_helix.png`
- `job_123_interactive.html`
- `job_123_report.txt`
- `job_123_report.json`

---

## Visualization Summary Table

| Molecule Type | File Count | Generation Time | Memory Usage |
|--------------|-----------|----------------|--------------|
| Small Molecule | 9 files | ~2-3 sec | <500 MB |
| Protein | 9 files | ~3-4 sec | <500 MB |
| DNA/RNA | 9 files | ~2-3 sec | <500 MB |
| Metabolite | 8 files | ~1-2 sec | <300 MB |

---

## Energy Unit Conversions

Quick reference for unit conversions:

```
1 Hartree (Ha) = 27.2114 eV = 627.509 kcal/mol
1 eV = 0.036749 Ha = 23.061 kcal/mol
1 kcal/mol = 0.001594 Ha = 0.04336 eV

1 Bohr = 0.529177 Angstrom (Å)
1 Angstrom = 1.889726 Bohr
```

---

## Common Molecule Types in Practice

**Small Molecules:**
- Benzene, aspirin, caffeine
- Drug candidates (MW < 900 Da)
- Simple inorganics (H2, H2O, CO2)

**Proteins:**
- Enzymes (lysozyme, trypsin)
- Antibodies (IgG, scFv)
- Structural proteins (collagen fragments)

**DNA/RNA:**
- Short oligos (10-30 bp)
- siRNA, miRNA
- DNA aptamers

**Metabolites:**
- Glucose, ATP, pyruvate
- Amino acids, nucleotides
- Lipids, cofactors

---

## Troubleshooting

**No visualizations generated:**
- Check `molecule_type` spelling
- Verify `counts` dictionary is not empty
- Ensure output directory has write permissions

**Missing specialized visualizations:**
- Provide `vqe_energies` parameter for full feature set
- Check molecule type matches expected categories
- Review logs for error messages

**Poor quality structures:**
- Increase `num_qubits` for better resolution
- Use real quantum hardware instead of simulator
- Provide experimental energy data when available

---

## Best Practices

1. **Always provide VQE data** when available for maximum scientific value
2. **Use descriptive job IDs** for easier file management
3. **Store visualizations** for reproducibility
4. **Include metadata** in filenames or separate JSON
5. **Validate outputs** using generated quality scores

---

## API Integration

```python
# REST API example
POST /api/v1/visualize

{
  "job_id": "job_789",
  "molecule_type": "protein",
  "quantum_results": {
    "counts": {...},
    "vqe_energies": {...},
    "ground_state_energy": -5.234
  },
  "output_format": ["png", "html", "json"]
}

# Response
{
  "status": "success",
  "files": {
    "energy_histogram": "https://s3.../job_789_energy_histogram.png",
    "protein_folding": "https://s3.../job_789_protein_folding.png",
    ...
  },
  "metadata": {
    "generation_time": 3.2,
    "quality_score": 87.5
  }
}
```

---

## Performance Tips

- **Batch processing:** Generate multiple visualizations in parallel
- **Caching:** Reuse VQE data for multiple visualization sets
- **Compression:** Use PNG for static images, HTML for interactive
- **Async:** Run visualization generation asynchronously in production

---

## Support and Documentation

- Full docs: `/docs/SPECIALIZED_VISUALIZATIONS_IMPLEMENTATION.md`
- Code: `/quantum_core/backends/visualization_generator.py`
- Examples: `/examples/visualization_examples.py`
- API docs: `/docs/API_REFERENCE.md`

---

**Last Updated:** 2025-10-26
**Version:** 2.0
