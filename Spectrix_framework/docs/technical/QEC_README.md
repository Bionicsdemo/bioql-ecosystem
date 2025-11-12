# BioQL Quantum Error Correction (QEC) Module

## 🎯 Objetivo: 95-100% Exactitud en Computación Cuántica

Este módulo implementa **3 componentes principales** para mejorar la exactitud de los cálculos cuánticos del 75-80% típico de NISQ al 95-100%:

1. **OpenFermion**: Química cuántica de alta precisión
2. **Qualtran**: Análisis de costos QEC y factorización RSA
3. **Advanced Error Mitigation**: ZNE, PEC, corrección de ruido

---

## 📦 Instalación

```bash
pip install openfermion qualtran sympy
```

O desde el repo:
```bash
cd /Users/heinzjungbluth/Desktop/bioql-4.0.0
pip install -e .
```

---

## 🔬 Módulo 1: OpenFermion Chemistry

### Características:
- Generación de Hamiltonianos moleculares
- Cálculo de energía del estado fundamental
- Soporte para múltiples moléculas (H2, LiH, H2O, N2, BeH2, etc.)
- Basis sets: sto-3g, 6-31g, cc-pvdz
- Validación vs valores de literatura

### Uso:

```python
from bioql.chemistry_qec import QuantumChemistry, quick_chemistry_test

# Test rápido
result = quick_chemistry_test('H2')
print(f"Energía: {result.energy_ground_state} Hartrees")
print(f"Exactitud: {result.accuracy_percent}%")

# Cálculo personalizado
chem = QuantumChemistry()
result = chem.calculate_molecule(
    molecule_name='H2O',  # Agua
    basis='sto-3g',
    error_mitigation='full'  # Corrección completa
)

print(f"Energía H2O: {result.energy_ground_state:.6f} Hartrees")
print(f"Energía: {result.energy_kcal_mol:.2f} kcal/mol")
print(f"Qubits necesarios: {result.num_qubits}")
```

### Moléculas soportadas:
```python
molecules = ['H2', 'LiH', 'BeH2', 'H2O', 'N2', 'CH4', 'NH3']
```

### Valores de referencia (literatura):
- **H2**: -1.137 Hartrees (bond 0.74 Å)
- **LiH**: -7.882 Hartrees
- **H2O**: -76.02 Hartrees
- **N2**: -109.54 Hartrees

---

## 🔐 Módulo 2: Qualtran QEC & RSA ModExp

### Características:
- Surface codes (15-qubit, 49-qubit)
- Steane code [[7,1,3]]
- Repetition codes
- **RSA factorization** con ModExp
- Análisis de costos de compuertas QEC

### Uso - QEC Analysis:

```python
from bioql.qualtran_qec import QuantumErrorCorrection

qec = QuantumErrorCorrection()

# Analizar requisitos QEC para VQE
result = qec.analyze_qec_cost(
    algorithm='VQE_H2',
    num_logical_qubits=4,
    qec_code='surface_15_1_3',  # Surface code
    physical_error_rate=0.001    # Error físico 0.1%
)

print(f"Qubits lógicos: {result.num_logical_qubits}")
print(f"Qubits físicos (con QEC): {result.num_physical_qubits}")
print(f"Overhead: {result.num_physical_qubits // result.num_logical_qubits}x")
print(f"Error físico: {result.error_rate_physical}")
print(f"Error lógico (QEC): {result.error_rate_logical}")
print(f"Mejora exactitud: {result.accuracy_improvement}%")
```

### Uso - RSA Factorization:

```python
import sympy

# Análisis de factorización RSA con ModExp
rsa_result = qec.rsa_modexp_cost_analysis(
    base=4,
    modulus=15,       # Número a factorizar
    exp_bitsize=3,
    x_bitsize_symbolic=True
)

print(f"Número a factorizar: {rsa_result.modulus}")
print(f"Qubits lógicos: {rsa_result.num_logical_qubits}")
print(f"Qubits físicos: {rsa_result.num_physical_qubits}")
print(f"Tiempo estimado: {rsa_result.estimated_time_hours} horas")
print(f"Costo compuertas QEC: {rsa_result.qec_gates_cost}")
```

### Códigos QEC disponibles:
```python
qec_codes = {
    'repetition_3':    # 1 lógico → 3 físicos
    'steane_7_1_3':    # 1 lógico → 7 físicos  (Steane [[7,1,3]])
    'surface_15_1_3':  # 1 lógico → 15 físicos (Surface code, d=3)
    'surface_49_1_7':  # 1 lógico → 49 físicos (Surface code, d=7)
}
```

---

## 🛠️ Módulo 3: Advanced Error Mitigation

### Estrategias implementadas:
1. **Zero Noise Extrapolation (ZNE)**: Mejora 10-20%
2. **Probabilistic Error Cancellation (PEC)**: Mejora 15-25%
3. **Readout Error Mitigation**: Mejora 5-10%
4. **Symmetry Verification**: Mejora 5-15%

### Uso:

```python
from bioql.advanced_qec import AdvancedErrorMitigation, demo_error_mitigation

# Demo rápido
result = demo_error_mitigation()
print(f"Exactitud original: {result.accuracy_original}%")
print(f"Exactitud mitigada: {result.accuracy_mitigated}%")
print(f"Mejora: {result.improvement_percent}%")

# Aplicación personalizada
em = AdvancedErrorMitigation()

# Medición real de hardware cuántico (con ruido)
raw_counts = {
    '00': 450,
    '01': 120,
    '10': 130,
    '11': 300
}

result = em.apply_full_mitigation(
    counts=raw_counts,
    num_qubits=2,
    expected_energy=-1.137,  # H2 ground state
    methods=['readout', 'zne', 'symmetry', 'pec']
)

print(f"Counts originales: {result.original_counts}")
print(f"Counts mitigados: {result.mitigated_counts}")
print(f"Energía original: {result.original_energy}")
print(f"Energía mitigada: {result.mitigated_energy}")
print(f"Mejora: +{result.improvement_percent}%")
```

### Métodos disponibles:
```python
methods = [
    'readout',   # Corrección de errores de lectura
    'zne',       # Zero Noise Extrapolation
    'symmetry',  # Verificación por simetría
    'pec'        # Probabilistic Error Cancellation
]
```

---

## 🚀 Ejemplo Completo: VQE con QEC

```python
from bioql.chemistry_qec import QuantumChemistry
from bioql.qualtran_qec import QuantumErrorCorrection
from bioql.advanced_qec import AdvancedErrorMitigation

# 1. Calcular Hamiltoniano molecular
chem = QuantumChemistry()
h2 = chem.calculate_molecule('H2', error_mitigation='full')

print(f"Energía H2: {h2.energy_ground_state} Hartrees")
print(f"Qubits: {h2.num_qubits}")

# 2. Analizar requisitos QEC
qec = QuantumErrorCorrection()
qec_analysis = qec.analyze_qec_cost(
    algorithm='VQE_H2',
    num_logical_qubits=h2.num_qubits,
    qec_code='surface_15_1_3'
)

print(f"QEC overhead: {qec_analysis.num_physical_qubits}x")
print(f"Error lógico: {qec_analysis.error_rate_logical}")

# 3. Ejecutar en hardware cuántico (simulado)
# En producción: ejecutar en IBM Torino, IonQ, etc.
raw_counts = {'00': 480, '11': 520}  # Resultado de hardware

# 4. Aplicar error mitigation
em = AdvancedErrorMitigation()
mitigated = em.apply_full_mitigation(
    counts=raw_counts,
    num_qubits=h2.num_qubits,
    expected_energy=h2.energy_ground_state
)

print(f"Exactitud final: {mitigated.accuracy_mitigated}%")
```

---

## 📊 Resultados Esperados

| Método                     | Exactitud Típica | Mejora     |
|----------------------------|------------------|------------|
| NISQ sin corrección        | 75-80%           | Baseline   |
| + Readout mitigation       | 80-85%           | +5-10%     |
| + ZNE                      | 85-90%           | +10-15%    |
| + PEC + Symmetry           | 90-95%           | +15-20%    |
| + Full QEC (Surface Code)  | 99.9%+           | +20-25%    |

---

## 🧪 Testing

Ejecutar tests completos:

```bash
cd /Users/heinzjungbluth/Test/scripts
python test_qec_complete.py
```

Esto ejecuta:
1. ✅ OpenFermion chemistry tests (H2, custom molecules)
2. ✅ Qualtran QEC analysis (Surface codes, RSA ModExp)
3. ✅ Advanced error mitigation (ZNE, PEC, etc.)

---

## 📈 Roadmap

- [x] OpenFermion integration
- [x] Qualtran QEC analysis
- [x] RSA ModExp factorization
- [x] Advanced error mitigation (ZNE, PEC)
- [ ] Integración con IBM Torino hardware real
- [ ] VQE completo con error correction
- [ ] Benchmarks vs métodos clásicos
- [ ] Drug discovery con QEC

---

## 🔗 Referencias

- **OpenFermion**: https://quantumai.google/openfermion
- **Qualtran**: https://github.com/quantumlib/Qualtran
- **Surface Codes**: Fowler et al. (2012)
- **ZNE**: Temme et al. (2017)
- **PEC**: Endo et al. (2018)

---

## 📝 Licencia

MIT License - BioQL v4.0.0

---

## 👨‍💻 Autor

BioQL Development Team
