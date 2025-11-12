# Changelog

All notable changes to BioQL will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-09-29

### Added - Drug Discovery Pack 🧬

#### Core Features
- **Molecular Docking System**
  - AutoDock Vina backend integration for classical docking
  - Quantum computing backend for novel docking calculations
  - Unified `dock()` API with automatic backend selection
  - Support for SMILES input and PDB/PDBQT file formats
  - Configurable search box and exhaustiveness parameters

- **Chemistry Module** (`bioql.chem`)
  - Ligand preparation from SMILES strings
  - 3D conformer generation and geometry optimization
  - Receptor preparation from PDB files
  - Format conversion (PDB, PDBQT, MOL2, SDF)
  - Support for RDKit, OpenBabel, and Meeko backends

- **Visualization Module** (`bioql.visualize`)
  - PyMOL integration for publication-quality rendering
  - py3Dmol fallback for web-based visualization
  - Protein-ligand complex visualization
  - Image export (PNG, TIFF) with ray tracing
  - PyMOL session file (.pse) export

- **Dynamic Library Bridge** (Meta-wrapper) 🔮
  - **Revolutionary feature**: Call any Python library via natural language!
  - Natural language → library function mapping
  - Pre-configured support for:
    - Chemistry: RDKit, OpenBabel
    - Scientific computing: NumPy, SciPy, Pandas
    - Bioinformatics: Biopython
    - Visualization: PyMOL, py3Dmol
  - Extensible registry for custom library integration
  - Automatic argument extraction from natural language

#### CLI Enhancements
- `bioql dock` - Molecular docking command
  - `--receptor` - Receptor PDB file
  - `--smiles` - Ligand SMILES string
  - `--backend` - Backend selection (auto, vina, quantum)
  - `--center` - Binding site center coordinates
  - `--box-size` - Search box dimensions

- `bioql visualize` - Molecular visualization command
  - `--structure` - Structure file to visualize
  - `--style` - Display style (cartoon, sticks, spheres, surface)
  - `--output` - Save image to file
  - `--session` - Save PyMOL session
  - `--ligand` - Additional ligand for complex visualization

- `bioql call` - Dynamic library call command
  - Natural language interface to any Python library
  - Examples:
    - `bioql call "Use RDKit to calculate molecular weight of SMILES ..."`
    - `bioql call "Use numpy to calculate mean of array [1, 2, 3]"`

#### Installation Extras
- `pip install bioql[vina]` - AutoDock Vina support
  - meeko >= 0.4.0
  - rdkit >= 2022.9.1
  - openbabel-wheel >= 3.1.1

- `pip install bioql[viz]` - Visualization support
  - py3Dmol >= 2.0.0
  - pillow >= 9.0.0

- `pip install bioql[openmm]` - Molecular dynamics support
  - openmm >= 8.0.0

### Changed
- Enhanced CLI help with new command examples
- Improved error messages with installation hints
- Optimized logging for drug discovery workflows

### Technical Details
- New submodules maintain full backward compatibility
- All new features available via optional extras
- Lazy imports prevent hard dependencies
- Graceful fallbacks when optional packages unavailable

### Examples
See `examples/drug_discovery_example.py` for comprehensive usage examples:
- Vina docking workflow
- Quantum docking workflow
- Ligand preparation
- Molecular visualization
- Dynamic library calls
- Complete end-to-end workflow

### Documentation
- New technical reference: `TECHNICAL_REFERENCE.md`
- Updated installation instructions
- API documentation for new modules
- CLI usage examples

### Notes
- Drug Discovery Pack requires Python 3.8+
- Recommended: Python 3.11 for best performance
- Some features require external tools (AutoDock Vina binary, PyMOL)
- Full quantum docking requires BioQL API key

---

## [2.0.0] - 2025-01-XX

### Added
- DevKit NL→IR→Quantum Pipeline
- Enhanced quantum execution with IR compilation
- API key authentication model
- SpectrixRD branding

### Changed
- Migration from open-source to authenticated model
- Enhanced natural language processing
- Improved quantum backend integration

---

## [1.0.2] - 2024-XX-XX

### Security
- Package structure cleanup
- Security audit and fixes

---

## [1.0.1] - 2024-XX-XX

### Changed
- SpectrixRD branding updates
- Documentation improvements

---

## [1.0.0] - 2024-XX-XX

### Added
- Initial release of BioQL
- Core quantum computing interface
- Qiskit integration
- Basic bioinformatics operations

---

## Upgrade Guide

### From 2.0.x to 2.1.0

**No breaking changes!** All existing code continues to work.

To use new features:

```python
# Install extras
pip install --upgrade bioql[vina,viz]

# Use molecular docking
from bioql.docking import dock

result = dock(
    receptor="protein.pdb",
    ligand_smiles="CCO",
    backend="vina"
)

# Use dynamic library calls
from bioql import dynamic_call

result = dynamic_call("Use RDKit to calculate molecular weight of SMILES CCO")
print(result.result)
```

### CLI Migration

New commands complement existing ones:

```bash
# Old (still works)
bioql quantum "analyze protein" --api-key KEY

# New additions
bioql dock --receptor protein.pdb --smiles "CCO"
bioql visualize --structure complex.pdb --output image.png
bioql call "Use RDKit to ..."
```

---

## Deprecation Notices

None for this release. Full backward compatibility maintained.

---

## Contributors

- BioQL Development Team
- Community contributors (see CONTRIBUTORS.md)

## License

MIT License - See LICENSE file for details

---

**Full Changelog**: https://github.com/bioql/bioql/compare/v2.0.0...v2.1.0