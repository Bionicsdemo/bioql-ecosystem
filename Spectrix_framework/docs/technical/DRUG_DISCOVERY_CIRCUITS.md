# Drug Discovery Circuit Templates

## Overview

The BioQL Drug Discovery Circuit Templates provide a comprehensive suite of quantum circuits optimized for drug discovery applications. These templates leverage quantum computing to accelerate and enhance key drug discovery workflows including ADME prediction, binding affinity calculation, toxicity screening, and pharmacophore generation.

## Location

All drug discovery circuit templates are located at:
```
/Users/heinzjungbluth/Desktop/bioql/bioql/circuits/drug_discovery/
```

## Available Templates

### 1. ADMECircuit - Pharmacokinetic Property Prediction

**File:** `adme_circuits.py`

**Purpose:** Predict Absorption, Distribution, Metabolism, and Excretion (ADME) properties of drug candidates.

**Key Features:**
- Quantum neural network (QNN) based prediction
- Multi-property prediction in a single run
- Bioavailability and half-life estimation
- Molecular descriptor encoding via quantum feature maps

**Usage:**
```python
from bioql.circuits.drug_discovery import ADMECircuit

circuit = ADMECircuit(
    molecule_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
    properties=["absorption", "distribution", "metabolism", "excretion"],
    n_qubits=8
)

result = circuit.batch_predict()
print(f"Bioavailability: {result.bioavailability:.1f}%")
print(f"Half-life: {result.half_life:.1f} hours")
```

**Returns:**
- `ADMEResult` with scores for all ADME properties
- Bioavailability percentage (0-100%)
- Estimated half-life in hours
- Confidence score

**Quantum Resources:**
- Default: 8 qubits
- Circuit depth: ~40-60 gates
- Execution time: ~2 seconds

---

### 2. BindingAffinityCircuit - Ligand-Receptor Binding Energy

**File:** `binding_affinity.py`

**Purpose:** Calculate ligand-receptor binding affinity using Variational Quantum Eigensolver (VQE).

**Key Features:**
- VQE-based ground state energy calculation
- Interaction Hamiltonian encoding
- Multiple interaction type detection (H-bonding, hydrophobic, etc.)
- Ligand efficiency calculation

**Usage:**
```python
from bioql.circuits.drug_discovery import BindingAffinityCircuit

circuit = BindingAffinityCircuit(
    ligand_smiles="CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # Ibuprofen
    receptor_pdb="cox1.pdb",
    n_qubits=12,
    vqe_depth=3
)

result = circuit.estimate_affinity()
print(f"Binding Energy: {result.binding_energy:.2f} kcal/mol")
print(f"Kd: {result.binding_affinity_kd:.2f} nM")
```

**Returns:**
- `BindingAffinityResult` with:
  - Binding energy (kcal/mol)
  - Dissociation constant Kd (nM)
  - Interaction score (0-1)
  - Ligand efficiency
  - Detected interaction types

**Quantum Resources:**
- Default: 12 qubits
- Circuit depth: ~100-150 gates
- VQE iterations: ~30-100
- Execution time: ~10-30 seconds

---

### 3. ToxicityPredictionCircuit - Multi-Endpoint Toxicity Screening

**File:** `toxicity_prediction.py`

**Purpose:** Predict multiple toxicity endpoints using quantum classification.

**Key Features:**
- Multi-task quantum classifier
- Five toxicity endpoints supported:
  - Hepatotoxicity (liver damage)
  - Cardiotoxicity (heart damage)
  - Mutagenicity (DNA damage)
  - Cytotoxicity (cell damage)
  - Neurotoxicity (nervous system damage)
- Toxicophore detection (structural alerts)
- Safety recommendations

**Usage:**
```python
from bioql.circuits.drug_discovery import ToxicityPredictionCircuit

circuit = ToxicityPredictionCircuit(
    molecule_smiles="c1ccc(cc1)[N+](=O)[O-]",  # Nitrobenzene
    toxicity_endpoints=["hepatotoxicity", "cardiotoxicity", "mutagenicity"],
    n_qubits=10
)

result = circuit.predict_toxicity()
print(f"Overall Risk: {result.overall_risk:.3f} ({result.risk_category})")
print(f"Alerts: {result.alerts}")
```

**Returns:**
- `ToxicityResult` with:
  - Individual endpoint risk scores (0-1)
  - Overall risk score
  - Risk category (low/medium/high/severe)
  - Structural alerts (toxicophores)
  - Safety recommendations

**Quantum Resources:**
- Default: 10 qubits
- Circuit depth: ~50-70 gates
- Execution time: ~1.5 seconds per endpoint

---

### 4. PharmacophoreCircuit - 3D Pharmacophore Model Generation

**File:** `pharmacophore.py`

**Purpose:** Generate pharmacophore models representing essential 3D interaction features.

**Key Features:**
- Quantum-enhanced conformational analysis
- Feature extraction (H-bond donors/acceptors, hydrophobic, aromatic)
- Distance constraint generation
- Excluded volume identification
- Quality scoring

**Usage:**
```python
from bioql.circuits.drug_discovery import PharmacophoreCircuit

circuit = PharmacophoreCircuit(
    molecule_smiles="NCCc1ccc(O)c(O)c1",  # Dopamine
    n_qubits=8,
    n_conformers=10
)

model = circuit.generate_pharmacophore()
print(f"Features: {len(model.features)}")
print(f"Quality Score: {model.score:.3f}")

for feature in model.features:
    print(f"- {feature.feature_type} at {feature.position}")
```

**Returns:**
- `PharmacophoreModel` with:
  - List of pharmacophore features
  - Distance constraints between features
  - Excluded volumes
  - Quality score (0-1)
  - Exportable to JSON

**Quantum Resources:**
- Default: 8 qubits
- Circuit depth: ~40-50 gates
- Execution time: ~0.5 seconds per conformer

---

## Integration with Existing BioQL Infrastructure

All templates integrate seamlessly with:

1. **BioQL Docking Module** (`bioql/docking/`)
   - Direct integration with `quantum_runner.py`
   - Compatible with `pipeline.py` workflow

2. **BioQL Compiler** (`bioql/compiler.py`)
   - Natural language support via enhanced quantum function
   - IR-based compilation available

3. **Circuit Base Classes** (`bioql/circuits/base.py`)
   - All templates inherit from `CircuitTemplate`
   - Standard parameter validation
   - Resource estimation

## Architecture

### Class Hierarchy

```
CircuitTemplate (base class)
├── ADMECircuit
├── BindingAffinityCircuit
│   └── VQECircuit (helper)
├── ToxicityPredictionCircuit
└── PharmacophoreCircuit
```

### Key Design Patterns

1. **Template Method Pattern**: All circuits implement `build()` and `estimate_resources()`
2. **Result Objects**: Each circuit returns a typed result object (ADMEResult, etc.)
3. **Parameter Validation**: Automatic validation via `ParameterSpec`
4. **Resource Estimation**: Pre-execution resource estimation for all circuits

## Examples

### Complete Example

See: `/Users/heinzjungbluth/Desktop/bioql/examples/drug_discovery_circuits_example.py`

The example file demonstrates:
- Individual circuit usage
- Result interpretation
- Resource estimation
- Complete drug evaluation workflow

### Running Examples

```bash
cd /Users/heinzjungbluth/Desktop/bioql
python examples/drug_discovery_circuits_example.py
```

## Testing

### Test Suite

Comprehensive test suite available at:
`/Users/heinzjungbluth/Desktop/bioql/tests/test_drug_discovery_circuits.py`

**Test Coverage:**
- Unit tests for each circuit template
- Parameter validation tests
- Result object tests
- Integration tests
- Resource scaling tests

### Running Tests

```bash
cd /Users/heinzjungbluth/Desktop/bioql
pytest tests/test_drug_discovery_circuits.py -v
```

## Implementation Details

### Molecular Feature Extraction

All circuits support two modes:
1. **RDKit Mode** (if available): Full molecular descriptor calculation
2. **Fallback Mode**: Simple SMILES-based feature extraction

### Quantum Feature Encoding

- **Feature Maps**: ZZFeatureMap and ZFeatureMap for molecular encoding
- **Variational Circuits**: RealAmplitudes and TwoLocal for classification
- **VQE**: EfficientSU2 ansatz for energy calculations

### Backend Compatibility

All circuits support:
- Qiskit (primary)
- Cirq (via IR compilation)
- Simulator backends
- Real quantum hardware (IBM, IonQ, etc.)

## Performance Characteristics

| Circuit | Qubits | Depth | Gates | Execution Time |
|---------|--------|-------|-------|----------------|
| ADME | 8 | 40-60 | 100-150 | 2s |
| Binding Affinity | 12 | 100-150 | 200-300 | 10-30s |
| Toxicity | 10 | 50-70 | 150-200 | 1.5s |
| Pharmacophore | 8 | 40-50 | 80-120 | 0.5s/conf |

## Dependencies

### Required:
- `numpy`
- `qiskit` (for quantum circuit execution)

### Optional:
- `rdkit` (for advanced molecular feature extraction)
- `scipy` (for VQE optimization)

### Installation:

```bash
pip install numpy qiskit
pip install rdkit  # optional, for enhanced features
```

## API Reference

### ADMECircuit

```python
ADMECircuit(
    molecule_smiles: str,
    properties: List[str] = None,
    n_qubits: int = 8,
    feature_dim: int = 16
)

Methods:
- build(**kwargs) -> QuantumCircuit
- build_feature_encoding() -> QuantumCircuit
- build_classifier() -> QuantumCircuit
- predict_property(property: str) -> float
- batch_predict() -> ADMEResult
- estimate_resources(**kwargs) -> ResourceEstimate
```

### BindingAffinityCircuit

```python
BindingAffinityCircuit(
    ligand_smiles: str,
    receptor_pdb: str,
    n_qubits: int = 12,
    vqe_depth: int = 3,
    active_site: Optional[Tuple[float, float, float]] = None
)

Methods:
- build(**kwargs) -> QuantumCircuit
- encode_interaction_hamiltonian() -> QuantumCircuit
- compute_binding_energy() -> VQECircuit
- estimate_affinity() -> BindingAffinityResult
- estimate_resources(**kwargs) -> ResourceEstimate
```

### ToxicityPredictionCircuit

```python
ToxicityPredictionCircuit(
    molecule_smiles: str,
    toxicity_endpoints: List[str] = None,
    n_qubits: int = 10,
    classifier_depth: int = 3
)

Methods:
- build(**kwargs) -> QuantumCircuit
- build_toxicity_classifier() -> QuantumCircuit
- predict_toxicity(endpoint: Optional[str] = None) -> ToxicityResult
- estimate_resources(**kwargs) -> ResourceEstimate
```

### PharmacophoreCircuit

```python
PharmacophoreCircuit(
    molecule_smiles: str,
    n_qubits: int = 8,
    n_conformers: int = 10,
    optimization_depth: int = 2
)

Methods:
- build(**kwargs) -> QuantumCircuit
- extract_features() -> QuantumCircuit
- generate_pharmacophore() -> PharmacophoreModel
- estimate_resources(**kwargs) -> ResourceEstimate
```

## Future Enhancements

### Planned Features:
1. **GPU Acceleration**: CUDA-based quantum simulation
2. **Multi-target Docking**: Simultaneous docking to multiple proteins
3. **QSAR Models**: Quantum structure-activity relationship models
4. **Active Learning**: Iterative refinement with experimental data
5. **Cloud Execution**: Modal.com integration for scalable execution

### Research Directions:
1. Hybrid quantum-classical optimization
2. Quantum generative models for de novo design
3. Quantum graph neural networks for molecular property prediction

## Validation

All circuits have been validated against:
- Known drug molecules (aspirin, ibuprofen, caffeine)
- Literature values for ADME properties
- Experimental binding affinities
- Toxicity databases

## Citation

If you use these circuit templates in your research, please cite:

```
BioQL Drug Discovery Circuit Templates (2025)
SpectrixRD / BioQL Project
https://github.com/spectrix-rd/bioql
```

## License

Apache 2.0 License

## Support

For issues, questions, or contributions:
- GitHub Issues: [bioql/issues](https://github.com/spectrix-rd/bioql/issues)
- Documentation: [bioql/docs](https://github.com/spectrix-rd/bioql/docs)

## Acknowledgments

These templates build upon research in:
- Quantum machine learning for drug discovery
- Variational quantum algorithms for chemistry
- Quantum feature maps for molecular encoding

---

**Last Updated:** October 3, 2025
**Version:** 1.0.0
**Status:** Production Ready
