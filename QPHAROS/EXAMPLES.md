# 🔶 QPHAROS Usage Examples
## 4 Schemas for Different User Types

**QPHAROS Version:** 1.1.0
**Published:** https://pypi.org/project/qpharos/1.1.0/
**Installation:** `pip install qpharos`

---

## 📋 Overview of 4 Schemas

QPHAROS provides **4 different ways to use the same quantum drug discovery platform**, designed for users with varying levels of expertise:

| Schema | Target User | Complexity | Use Case |
|--------|------------|------------|----------|
| **Schema 1** | Beginners, chemists | Ultra-simple | Quick calculations, learning |
| **Schema 2** | Researchers, developers | Moderate | Research projects, flexibility |
| **Schema 3** | Bioinformaticians, engineers | Advanced | Production pipelines, batch processing |
| **Schema 4** | Quantum experts, researchers | Expert | Custom quantum algorithms, research |

---

## 🟢 Schema 1: Simple API (Beginners)

**Perfect for:** Scientists who want results without coding complexity.

### Installation & Setup

```bash
pip install qpharos
export BIOQL_API_KEY='your_bioql_api_key_here'
```

Get your API key at: https://bioql.bio/signup

### Example 1: Quick Docking

```python
from qpharos.simple import quick_dock

# Calculate binding affinity (one line!)
affinity = quick_dock('CCO', '6B3J')

print(f"Binding Affinity: {affinity} kcal/mol")
# Output: Binding Affinity: -6.2 kcal/mol
```

### Example 2: Check Drug-Likeness

```python
from qpharos.simple import is_drug_like

# Check if molecule passes Lipinski Rule of 5
drug_like = is_drug_like('CCO')

print(f"Drug-like: {drug_like}")
# Output: Drug-like: True
```

### Example 3: Complete Test (Docking + ADMET)

```python
from qpharos.simple import test_molecule

# Full analysis in one call
result = test_molecule('CCO', '6B3J')

print(result)
# Output:
# {
#   'affinity': -6.2,
#   'ki_nM': 28.5,
#   'drug_like': True,
#   'qed_score': 0.72,
#   'recommendation': 'Good candidate - proceed to optimization',
#   'job_id': 'd41r0b8lqprs73fkeetg'
# }
```

### Example 4: Berberina vs GLP1R (Real Pharma Case)

```python
from qpharos.simple import test_molecule

# Berberina (anti-diabetic natural product)
berberina_smiles = 'COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2'

# GLP-1 Receptor (diabetes target)
result = test_molecule(berberina_smiles, '6B3J')

print(f"🧬 Berberina → GLP1R Analysis:")
print(f"   Affinity: {result['affinity']} kcal/mol")
print(f"   Ki: {result['ki_nM']} nM")
print(f"   Drug-like: {result['drug_like']}")
print(f"   QED Score: {result['qed_score']}")
print(f"   ✅ {result['recommendation']}")
print(f"   IBM Job: https://quantum.ibm.com/jobs/{result['job_id']}")
```

**Schema 1 Summary:**
- ✅ Minimal code (1-2 lines)
- ✅ Returns simple values (float, bool, dict)
- ✅ Automatic API key from environment
- ✅ Uses best practices (IBM Torino, 2000 shots, QEC enabled)
- ❌ No customization of parameters

---

## 🔵 Schema 2: Functional API (Normal Users)

**Perfect for:** Researchers who need more control over parameters.

### Example 1: Custom Docking Parameters

```python
from qpharos import dock

result = dock(
    ligand='CCO',
    receptor='6B3J',
    api_key='bioql_xxx',
    backend='ibm_torino',  # Choose backend
    shots=5000,            # Custom shot count
    qec=True               # Quantum error correction
)

print(f"Affinity: {result.binding_affinity} kcal/mol")
print(f"Ki: {result.ki} nM")
print(f"Interactions: {result.interactions}")
print(f"Job ID: {result.job_id}")
```

### Example 2: ADMET Prediction

```python
from qpharos import predict_admet

result = predict_admet(
    smiles='CCO',
    api_key='bioql_xxx',
    backend='ibm_torino',
    shots=1500
)

print(f"Lipinski Pass: {result.lipinski_pass}")
print(f"QED Score: {result.qed_score}")
print(f"LogP: {result.logp}")
print(f"Solubility: {result.solubility}")
print(f"BBB Permeability: {result.bbb_permeability}")
```

### Example 3: Drug Design (De Novo Generation)

```python
from qpharos import design_drug

result = design_drug(
    target_protein='6B3J',
    n_molecules=5,
    api_key='bioql_xxx',
    backend='ibm_torino',
    shots=3000
)

for i, mol in enumerate(result.molecules, 1):
    print(f"Molecule {i}:")
    print(f"  SMILES: {mol.smiles}")
    print(f"  Predicted Affinity: {mol.predicted_affinity} kcal/mol")
    print(f"  QED: {mol.qed_score}")
    print()
```

### Example 4: High-Throughput Screening

```python
from qpharos import screen_library

# Screen 1000 compounds
library = [
    'CCO',
    'CC(C)O',
    'CCCO',
    # ... 997 more compounds
]

results = screen_library(
    ligands=library,
    receptor='6B3J',
    api_key='bioql_xxx',
    shots_per_ligand=1000,  # Fewer shots for HTS
    affinity_threshold=-7.0  # Only return hits
)

print(f"Total compounds: {len(library)}")
print(f"Hits found: {len(results)}")

for hit in results:
    print(f"  {hit.ligand_smiles}: {hit.binding_affinity} kcal/mol")
```

### Example 5: Lead Optimization

```python
from qpharos import optimize_lead

# Optimize lead compound
result = optimize_lead(
    lead_smiles='CCO',
    receptor='6B3J',
    optimization_cycles=3,
    api_key='bioql_xxx'
)

print("Original Compound:")
print(f"  SMILES: {result.original_smiles}")
print(f"  Affinity: {result.original_affinity} kcal/mol")
print()

print("Optimized Compound:")
print(f"  SMILES: {result.optimized_smiles}")
print(f"  Affinity: {result.optimized_affinity} kcal/mol")
print(f"  Improvement: {result.improvement_percent}%")
```

**Schema 2 Summary:**
- ✅ Full parameter control
- ✅ Returns rich result objects (DockingResult, ADMETResult, etc.)
- ✅ All QPHAROS functions available
- ✅ Flexible backend selection
- ❌ No session management

---

## 🟣 Schema 3: OOP API (Programmers)

**Perfect for:** Integrating into production pipelines with session tracking.

### Example 1: Basic OOP Usage

```python
from qpharos import QPHAROSAnalyzer, QPHAROSConfig

# Configure analyzer
config = QPHAROSConfig(
    backend='ibm_torino',
    shots=2000,
    api_key='bioql_xxx',
    qec_enabled=True
)

# Create analyzer instance
analyzer = QPHAROSAnalyzer(config)

# Run docking
result = analyzer.dock('CCO', '6B3J')

print(f"Affinity: {result.binding_affinity} kcal/mol")
print(f"Session ID: {analyzer.session.session_id}")
```

### Example 2: Batch Screening with Session

```python
from qpharos import QPHAROSAnalyzer, QPHAROSConfig

config = QPHAROSConfig(
    backend='ibm_torino',
    shots=2000,
    api_key='bioql_xxx'
)

analyzer = QPHAROSAnalyzer(config)

# Screen multiple ligands
ligands = ['CCO', 'CC(C)O', 'CCCO', 'CC(C)(C)O']

hits = analyzer.screen(
    ligands=ligands,
    receptor='6B3J',
    affinity_threshold=-7.0  # Strong binders only
)

print(f"Screened {len(ligands)} compounds")
print(f"Found {len(hits)} hits")

# Get session summary
summary = analyzer.get_session_summary()
print(f"Session ID: {summary['session_id']}")
print(f"Total analyses: {summary['total_analyses']}")
print(f"Hits: {summary['hits']}")
```

### Example 3: Full Drug Discovery Pipeline

```python
from qpharos import QPHAROSAnalyzer, QPHAROSConfig

config = QPHAROSConfig(
    backend='ibm_torino',
    shots=2000,
    api_key='bioql_xxx'
)

analyzer = QPHAROSAnalyzer(config)

# Run complete pipeline
result = analyzer.full_pipeline(
    ligand='CCO',
    receptor='6B3J'
)

print("Pipeline Results:")
print(f"  Ligand: {result['ligand']}")
print(f"  Receptor: {result['receptor']}")
print(f"  Binding Affinity: {result['docking'].binding_affinity} kcal/mol")

if result['admet']:
    print(f"  Drug-like: {result['admet'].lipinski_pass}")
    print(f"  QED Score: {result['admet'].qed_score}")

print(f"  ✅ {result['recommendation']}")
```

### Example 4: Report Generation

```python
from qpharos import QPHAROSAnalyzer, QPHAROSConfig

config = QPHAROSConfig(api_key='bioql_xxx')
analyzer = QPHAROSAnalyzer(config)

# Run multiple analyses
analyzer.dock('CCO', '6B3J')
analyzer.dock('CC(C)O', '6B3J')
analyzer.predict_admet('CCO')

# Save JSON report
analyzer.save_report('results.json', format='json')

# Save text report
analyzer.save_report('results.txt', format='text')

print("Reports saved!")
```

### Example 5: Enterprise Pipeline Integration

```python
from qpharos import QPHAROSAnalyzer, QPHAROSConfig

class DrugDiscoveryPipeline:
    """Production drug discovery pipeline"""

    def __init__(self, api_key: str):
        config = QPHAROSConfig(
            backend='ibm_torino',
            shots=2000,
            api_key=api_key,
            qec_enabled=True
        )
        self.analyzer = QPHAROSAnalyzer(config)

    def process_library(self, library_file: str, receptor: str):
        """Process compound library"""
        # Load library
        with open(library_file) as f:
            ligands = [line.strip() for line in f]

        # Screen
        hits = self.analyzer.screen(
            ligands=ligands,
            receptor=receptor,
            affinity_threshold=-7.0
        )

        # Validate hits with ADMET
        validated_hits = []
        for hit in hits:
            admet = self.analyzer.predict_admet(hit.ligand_smiles)
            if admet.lipinski_pass and admet.qed_score > 0.5:
                validated_hits.append({
                    'smiles': hit.ligand_smiles,
                    'affinity': hit.binding_affinity,
                    'qed': admet.qed_score
                })

        # Generate report
        self.analyzer.save_report(f'hits_{receptor}.json')

        return validated_hits

# Usage
pipeline = DrugDiscoveryPipeline(api_key='bioql_xxx')
hits = pipeline.process_library('library.smi', '6B3J')
print(f"Validated hits: {len(hits)}")
```

**Schema 3 Summary:**
- ✅ Object-oriented design
- ✅ Session management and tracking
- ✅ Batch processing capabilities
- ✅ Report generation
- ✅ Enterprise-ready
- ❌ More code than Schema 1/2

---

## 🟡 Schema 4: Layer-by-Layer API (Quantum Experts)

**Perfect for:** Quantum researchers who want control over each quantum layer.

### Example 1: Direct Layer Access

```python
from qpharos.layers import (
    QuantumFeatureEncoder,
    QuantumEntanglementMapper,
    QuantumConformationalSearch,
    QuantumScoringFunction,
    QuantumErrorCorrection
)

# Initialize backend
from qpharos.core import quantum_backend

backend = quantum_backend.QuantumBackend(
    backend_name='ibm_torino',
    shots=2000,
    api_key='bioql_xxx'
)

# Layer 1: Feature Encoding
encoder = QuantumFeatureEncoder(backend)
encoded_ligand = encoder.encode_molecule('CCO')
encoded_receptor = encoder.encode_protein('6B3J')

print(f"Ligand qubits: {encoded_ligand.n_qubits}")
print(f"Receptor qubits: {encoded_receptor.n_qubits}")

# Layer 2: Entanglement Mapping
mapper = QuantumEntanglementMapper(backend)
entangled_state = mapper.create_entanglement(
    encoded_ligand,
    encoded_receptor
)

print(f"Entanglement depth: {entangled_state.circuit_depth}")

# Layer 3: Conformational Search
search = QuantumConformationalSearch(backend)
conformers = search.find_conformers(entangled_state, n_conformers=10)

print(f"Conformers found: {len(conformers)}")

# Layer 4: Quantum Scoring
scorer = QuantumScoringFunction(backend)
affinity = scorer.calculate_binding_affinity(conformers[0])

print(f"Binding Affinity: {affinity} kcal/mol")

# Layer 5: Quantum Error Correction
qec = QuantumErrorCorrection(backend, code_type='surface_code')
corrected_affinity = qec.correct_measurement(affinity)

print(f"QEC Corrected Affinity: {corrected_affinity} kcal/mol")
```

### Example 2: Custom VQE Parameters

```python
from qpharos.layers import QuantumScoringFunction
from qpharos.core import quantum_backend

backend = quantum_backend.QuantumBackend(
    backend_name='ibm_torino',
    shots=5000,
    api_key='bioql_xxx'
)

scorer = QuantumScoringFunction(backend)

# Customize VQE
result = scorer.run_vqe(
    hamiltonian=custom_hamiltonian,
    ansatz='hardware_efficient',
    optimizer='COBYLA',
    max_iterations=200,
    convergence_threshold=1e-6
)

print(f"VQE Energy: {result.energy}")
print(f"Iterations: {result.iterations}")
print(f"Fidelity: {result.fidelity}")
```

### Example 3: Custom QAOA for Conformational Search

```python
from qpharos.layers import QuantumConformationalSearch
from qpharos.core import quantum_backend

backend = quantum_backend.QuantumBackend(
    backend_name='ibm_torino',
    shots=3000,
    api_key='bioql_xxx'
)

search = QuantumConformationalSearch(backend)

# Custom QAOA parameters
conformers = search.run_qaoa(
    molecule=encoded_molecule,
    p_layers=4,  # QAOA depth
    mixer='X',
    penalty_strength=10.0,
    optimization_level=3
)

for i, conf in enumerate(conformers):
    print(f"Conformer {i+1}:")
    print(f"  Energy: {conf.energy}")
    print(f"  Probability: {conf.probability}")
```

### Example 4: Implement Custom QEC Code

```python
from qpharos.layers import QuantumErrorCorrection
from qpharos.core import quantum_backend

backend = quantum_backend.QuantumBackend(
    backend_name='ibm_torino',
    shots=2000,
    api_key='bioql_xxx'
)

# Use different QEC codes
qec_surface = QuantumErrorCorrection(backend, code_type='surface_code')
qec_steane = QuantumErrorCorrection(backend, code_type='steane_code')
qec_shor = QuantumErrorCorrection(backend, code_type='shor_code')

# Compare error correction methods
raw_result = 0.75
corrected_surface = qec_surface.correct_measurement(raw_result)
corrected_steane = qec_steane.correct_measurement(raw_result)
corrected_shor = qec_shor.correct_measurement(raw_result)

print(f"Raw: {raw_result}")
print(f"Surface Code: {corrected_surface}")
print(f"Steane Code: {corrected_steane}")
print(f"Shor Code: {corrected_shor}")
```

### Example 5: Research - Build Custom Quantum Algorithm

```python
from qpharos.layers import *
from qpharos.core import quantum_backend
from qiskit import QuantumCircuit

backend = quantum_backend.QuantumBackend(
    backend_name='ibm_torino',
    shots=10000,
    api_key='bioql_xxx'
)

# Build custom quantum circuit for docking
def custom_docking_circuit(ligand, receptor):
    """Custom quantum docking algorithm for research"""

    # Encode with custom mapping
    encoder = QuantumFeatureEncoder(backend)
    lig_qubits = encoder.encode_with_custom_mapping(ligand, mapping='gray_code')
    rec_qubits = encoder.encode_with_custom_mapping(receptor, mapping='binary')

    # Create circuit
    qc = QuantumCircuit(lig_qubits.n_qubits + rec_qubits.n_qubits)

    # Apply custom gates
    for i in range(lig_qubits.n_qubits):
        qc.h(i)  # Hadamard

    for i in range(lig_qubits.n_qubits):
        for j in range(rec_qubits.n_qubits):
            qc.cx(i, lig_qubits.n_qubits + j)  # Controlled-NOT

    # Add parametrized rotation (VQE-like)
    from qiskit.circuit import Parameter
    theta = Parameter('θ')
    for i in range(qc.num_qubits):
        qc.ry(theta, i)

    # Measure
    qc.measure_all()

    # Execute on IBM Torino
    result = backend.execute(qc, parameter_values=[0.5])

    return result

# Test custom algorithm
result = custom_docking_circuit('CCO', '6B3J')
print(f"Counts: {result.counts}")
```

**Schema 4 Summary:**
- ✅ Full quantum circuit control
- ✅ Access to all 5 layers individually
- ✅ Custom VQE/QAOA parameters
- ✅ Research-grade flexibility
- ✅ Direct Qiskit integration
- ❌ Requires quantum computing expertise

---

## 🎯 Which Schema Should I Use?

### Decision Tree:

```
┌─────────────────────────────────────────┐
│ Do you have quantum computing expertise?│
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
       YES           NO
        │             │
        ▼             ▼
   Schema 4      ┌───────────────────────────┐
                 │ Do you need batch/session?│
                 └──────────┬────────────────┘
                            │
                     ┌──────┴──────┐
                     │             │
                    YES           NO
                     │             │
                     ▼             ▼
                Schema 3      ┌────────────────────┐
                              │ Need customization?│
                              └─────────┬──────────┘
                                        │
                                 ┌──────┴──────┐
                                 │             │
                                YES           NO
                                 │             │
                                 ▼             ▼
                            Schema 2      Schema 1
```

### Quick Guide:

| Your Role | Recommended Schema | Why |
|-----------|-------------------|-----|
| Medicinal chemist | Schema 1 | Simple, quick results |
| PhD student | Schema 2 | Flexible, research-friendly |
| Biotech engineer | Schema 3 | Production pipelines |
| CRO pipeline | Schema 3 | Batch processing, reports |
| Quantum researcher | Schema 4 | Algorithm development |
| Pharma company | Schema 2 or 3 | Depends on integration needs |

---

## 📚 Additional Resources

- **PyPI Package:** https://pypi.org/project/qpharos/
- **BioQL Platform:** https://bioql.bio
- **Get API Key:** https://bioql.bio/signup
- **Documentation:** https://docs.bioql.bio/qpharos
- **GitHub:** https://github.com/yourusername/qpharos
- **Support:** heinz@bionics-ai.biz

---

## 🔬 Real-World Example: Complete Drug Discovery

Let's compare all 4 schemas for the same task: **Docking Berberina to GLP1R**

### Schema 1 (Beginner):
```python
from qpharos.simple import test_molecule

result = test_molecule(
    'COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2',
    '6B3J'
)
print(result['recommendation'])
```

### Schema 2 (Researcher):
```python
from qpharos import dock

result = dock(
    ligand='COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2',
    receptor='6B3J',
    api_key='bioql_xxx',
    backend='ibm_torino',
    shots=2000
)
print(f"{result.binding_affinity} kcal/mol")
```

### Schema 3 (Engineer):
```python
from qpharos import QPHAROSAnalyzer, QPHAROSConfig

config = QPHAROSConfig(api_key='bioql_xxx')
analyzer = QPHAROSAnalyzer(config)

result = analyzer.full_pipeline(
    'COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2',
    '6B3J'
)
analyzer.save_report('berberina_report.json')
```

### Schema 4 (Quantum Expert):
```python
from qpharos.layers import *
from qpharos.core import quantum_backend

backend = quantum_backend.QuantumBackend(
    backend_name='ibm_torino',
    shots=2000,
    api_key='bioql_xxx'
)

encoder = QuantumFeatureEncoder(backend)
lig = encoder.encode_molecule('COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2')
rec = encoder.encode_protein('6B3J')

mapper = QuantumEntanglementMapper(backend)
state = mapper.create_entanglement(lig, rec)

scorer = QuantumScoringFunction(backend)
affinity = scorer.calculate_binding_affinity(state)

print(f"{affinity} kcal/mol")
```

**Same result, different approaches!**

---

**QPHAROS v1.1.0** - Quantum Pharmaceutical Optimization System
🧬 Built with BioQL | ⚛️ Powered by IBM Quantum | 🔬 Designed for Drug Discovery
