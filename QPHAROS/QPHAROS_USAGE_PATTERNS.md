# 🔶 QPHAROS Usage Patterns
## Multiple Schemas for Different User Types

QPHAROS ofrece **5 esquemas diferentes** de uso, desde principiante hasta experto:

---

## 📊 Esquema 1: **Simple API** (Principiantes)
### Para: Químicos, biólogos, investigadores sin experiencia en quantum

**Nivel de abstracción: MUY ALTO**

```python
from qpharos import dock

# Una línea - máxima simplicidad
result = dock('COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2', '6B3J')

print(f"Affinity: {result.binding_affinity} kcal/mol")
```

**Características:**
- ✅ Defaults inteligentes (backend, shots, QEC)
- ✅ API key desde environment variable
- ✅ Sin configuración
- ❌ Menos control sobre parámetros cuánticos

---

## 📊 Esquema 2: **Functional API** (Usuarios Normales)
### Para: Computational chemists, drug discovery scientists

**Nivel de abstracción: ALTO**

```python
from qpharos import dock, predict_admet, design_drug

# Docking con parámetros
result = dock(
    ligand='COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2',
    receptor='6B3J',
    binding_site='Active site',
    backend='ibm_torino',
    shots=2000,
    qec=True,
    api_key='bioql_xxx'
)

# ADMET prediction
admet = predict_admet(result.ligand_smiles)

# Drug design si el docking no es bueno
if result.binding_affinity > -7.0:  # Débil
    better = design_drug(
        target_protein='6B3J',
        scaffold=result.ligand_smiles,
        iterations=5
    )
```

**Características:**
- ✅ Funciones de alto nivel
- ✅ Control de parámetros importantes
- ✅ Flujo de trabajo completo
- ❌ No acceso a layers individuales

---

## 📊 Esquema 3: **Object-Oriented API** (Programadores)
### Para: Bioinformáticos, pipeline developers

**Nivel de abstracción: MEDIO**

```python
from qpharos import QPHAROSAnalyzer, QPHAROSConfig

# Configuración explícita
config = QPHAROSConfig(
    backend='ibm_torino',
    shots=2000,
    qec_enabled=True,
    qec_type='surface_code',
    logical_qubits=4,
    convergence_threshold=1e-6,
    max_iterations=100,
    api_key='bioql_xxx'
)

# Analyzer object
analyzer = QPHAROSAnalyzer(config)

# Múltiples análisis con misma config
for ligand in ligand_library:
    result = analyzer.dock(ligand, '6B3J')
    if result.binding_affinity < -8.0:
        admet = analyzer.predict_admet(ligand)
        if admet.lipinski_pass:
            hits.append(result)

# Reportes
analyzer.generate_report(hits, 'best_hits.pdf')
```

**Características:**
- ✅ Configuración reutilizable
- ✅ Métodos orientados a objetos
- ✅ Batch processing
- ✅ Reportes automáticos

---

## 📊 Esquema 4: **Layer-by-Layer API** (Expertos Quantum)
### Para: Quantum algorithm developers, researchers

**Nivel de abstracción: BAJO**

```python
from qpharos.layers import (
    QuantumFeatureEncoder,
    QuantumEntanglementMapper,
    QuantumConformationalSearch,
    QuantumScoringFunction,
    QuantumErrorCorrection
)
from qpharos.core import QuantumBackend

backend = QuantumBackend(backend='ibm_torino', shots=2000)

# Layer 1: Feature Encoding
encoder = QuantumFeatureEncoder(backend)
encoded_ligand = encoder.encode_molecule('CCO', method='amplitude')
encoded_protein = encoder.encode_protein('6B3J', method='basis')

# Layer 2: Entanglement Mapping
mapper = QuantumEntanglementMapper(backend)
interaction_circuit = mapper.create_entanglement(
    encoded_ligand,
    encoded_protein,
    coupling_strength=0.8
)

# Layer 3: Conformational Search (QAOA)
search = QuantumConformationalSearch(backend)
optimal_pose = search.qaoa_optimize(
    interaction_circuit,
    p_layers=3,
    optimizer='cobyla'
)

# Layer 4: Scoring (VQE)
scorer = QuantumScoringFunction(backend)
binding_energy = scorer.vqe_score(
    optimal_pose,
    ansatz='hardware_efficient',
    optimizer='spsa'
)

# Layer 5: QEC
qec = QuantumErrorCorrection(backend)
validated_energy = qec.apply_surface_code(binding_energy, distance=3)

print(f"Binding affinity: {validated_energy} Ha")
```

**Características:**
- ✅ Control total de cada layer
- ✅ Acceso a circuitos cuánticos
- ✅ Custom algorithms
- ✅ Experimentación
- ❌ Requiere conocimiento profundo de quantum

---

## 📊 Esquema 5: **BioQL Direct** (Usuarios Avanzados de BioQL)
### Para: Usuarios que ya conocen BioQL y quieren usar QPHAROS como templates

**Nivel de abstracción: MUY BAJO (prompt engineering)**

```python
from bioql import quantum

# QPHAROS como template de prompt
result = quantum(
    """QPHAROS 5-Layer Drug Discovery:

    Ligand: Aspirin
    SMILES: CC(=O)Oc1ccccc1C(=O)O
    Receptor: COX-2 (PDB: 1EQG)

    Custom Parameters:
    - Layer 3 QAOA: p=5 (más profundo que default)
    - Layer 4 VQE: RY ansatz instead of hardware-efficient
    - Layer 5 QEC: Steane code (7 qubits) instead of Surface

    Calculate binding affinity with custom workflow.""",
    backend='ibm_torino',
    shots=3000,
    api_key='bioql_xxx'
)

# O completamente custom
custom_circuit = quantum(
    """Build quantum circuit for molecular docking:
    1. Encode ligand 'CCO' using Pauli encoding
    2. Encode protein '1ABC' using phase encoding
    3. Apply controlled rotations for H-bond detection
    4. Use VQE with custom cost function: H = -1*⟨ψ|H_binding|ψ⟩
    5. No QEC (raw noisy results wanted)""",
    backend='ibm_torino',
    shots=2000,
    api_key='bioql_xxx'
)
```

**Características:**
- ✅ Control absoluto via prompts
- ✅ Puede usar QPHAROS templates o crear propios
- ✅ Experimentación libre
- ✅ Acceso directo a BioQL compiler
- ❌ Sin validación de QPHAROS
- ❌ Resultados sin bio_interpretation automática

---

## 📊 Comparación de Esquemas

| Esquema | Usuario Típico | Complejidad | Control | Velocidad Desarrollo |
|---------|---------------|-------------|---------|---------------------|
| **1. Simple API** | Químico sin coding | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| **2. Functional API** | Computational chemist | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **3. OOP API** | Bioinformático | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **4. Layer-by-Layer** | Quantum researcher | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **5. BioQL Direct** | Power user | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |

---

## 🎯 Casos de Uso por Esquema

### Esquema 1: Simple API
```python
# "Solo quiero saber si mi molécula se une bien"
from qpharos import dock
result = dock('CCO', '1ABC')
print(result.binding_affinity)  # -6.2 kcal/mol
```

### Esquema 2: Functional API
```python
# "Quiero evaluar 100 moléculas y elegir las mejores"
from qpharos import screen_library
results = screen_library(my_ligands, '6B3J')
top10 = results[:10]
```

### Esquema 3: OOP API
```python
# "Quiero integrar QPHAROS en mi pipeline de drug discovery"
analyzer = QPHAROSAnalyzer(config)
for compound in database:
    if analyzer.dock(compound, target).is_hit():
        analyzer.optimize_lead(compound)
```

### Esquema 4: Layer-by-Layer
```python
# "Quiero investigar cómo cada layer afecta los resultados"
encoder = QuantumFeatureEncoder()
for method in ['amplitude', 'basis', 'angle']:
    encoded = encoder.encode_molecule('CCO', method=method)
    score = scorer.vqe_score(encoded)
    print(f"{method}: {score}")
```

### Esquema 5: BioQL Direct
```python
# "Quiero experimentar con nuevos algoritmos cuánticos"
result = quantum("Use quantum walks for conformational search...")
```

---

## 💡 Recomendaciones

### Para Pharma Companies (Producción):
- ✅ Usar **Esquema 2 (Functional API)** o **Esquema 3 (OOP API)**
- ✅ Predecible, estable, documentado
- ✅ Fácil integración en pipelines

### Para Researchers (Investigación):
- ✅ Usar **Esquema 4 (Layer-by-Layer)** o **Esquema 5 (BioQL Direct)**
- ✅ Máximo control para experimentación
- ✅ Publicaciones científicas

### Para Startups (Rapid Prototyping):
- ✅ Empezar con **Esquema 1 (Simple API)**
- ✅ Migrar a **Esquema 2** cuando escalen
- ✅ Velocidad de desarrollo

### Para Academics (Teaching):
- ✅ Enseñar con **Esquema 1** (introducción)
- ✅ Luego **Esquema 4** (quantum mechanics details)
- ✅ Curva de aprendizaje gradual

---

## 🚀 Roadmap: Nuevos Esquemas

### Esquema 6: **CLI** (Terminal users)
```bash
qpharos dock --ligand "CCO" --receptor "6B3J" --output results.json
qpharos screen --library ligands.smi --receptor "6B3J" --top 10
qpharos report --results results.json --format pdf
```

### Esquema 7: **REST API** (Web services)
```bash
curl -X POST https://api.qpharos.com/v1/dock \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"ligand": "CCO", "receptor": "6B3J"}'
```

### Esquema 8: **GUI** (No-code users)
- Web dashboard
- Drag-and-drop molecules
- Visual result explorer
- One-click reports

---

## 📝 Conclusión

QPHAROS debe ofrecer **múltiples esquemas** para maximizar adopción:

1. **Principiantes** → Esquema 1 (Simple API)
2. **Usuarios Normales** → Esquema 2 (Functional API)
3. **Programadores** → Esquema 3 (OOP API)
4. **Expertos Quantum** → Esquema 4 (Layer-by-Layer)
5. **Power Users** → Esquema 5 (BioQL Direct)

**Todos usando el mismo backend de BioQL** pero con diferentes niveles de abstracción.
