# 🛠️ QEC Parameter Fix - BioQL Quantum Error Correction

**Fecha:** Octubre 28, 2025
**Issue:** `quantum()` got an unexpected keyword argument 'qec_config'
**Status:** ✅ RESUELTO

---

## 🐛 Problema

El código generado por el agente estaba usando un diccionario `qec_config` que NO es un parámetro válido de `quantum()`:

### ❌ INCORRECTO (genera error)

```python
result = quantum(
    "Analyze ligand...",
    backend='ibm_torino',
    shots=2000,
    api_key=api_key,
    qec_config={                    # ❌ ERROR: No existe este parámetro
        'enabled': True,
        'type': 'surface_code',
        'distance': 3,
        'logical_qubits': 2,
        'decoder': 'mwpm',
        'physical_qubits': 50
    }
)
```

**Error:**
```
❌ Error: quantum() got an unexpected keyword argument 'qec_config'
```

---

## ✅ Solución

La función `quantum()` de BioQL acepta los parámetros QEC como **parámetros individuales separados**, NO como un diccionario:

### ✅ CORRECTO

```python
result = quantum(
    "Analyze ligand with SMILES ... docking to receptor PDB 6B3J using surface_code error correction with 2 logical qubits",
    backend='ibm_torino',
    shots=2000,
    api_key=api_key,
    qec_enabled=True,              # ✅ Parámetro individual
    qec_type='surface_code',       # ✅ Parámetro individual
    logical_qubits=2               # ✅ Parámetro individual
)
```

---

## 📝 Parámetros QEC Válidos

### Signature de `quantum()` con QEC:

```python
def quantum(
    prompt: str,
    backend: str = 'simulator',
    shots: int = 1000,
    api_key: str = None,
    qec_enabled: bool = False,              # ✅ Boolean
    qec_type: str = 'surface_code',         # ✅ String: 'surface_code', 'steane', 'shor'
    logical_qubits: int = 2,                # ✅ Integer
    **kwargs
) -> QuantumResult:
    ...
```

### Opciones de `qec_type`:

| Tipo | Physical Qubits per Logical | Descripción |
|------|----------------------------|-------------|
| `surface_code` | (2d-1)² <br> d=3: 25 <br> d=5: 81 <br> d=7: 169 | Google Willow-style surface codes |
| `steane` | 7 | Steane [[7,1,3]] code |
| `shor` | 9 | Shor [[9,1,3]] code |

---

## 🔧 Cómo Arreglar Scripts Existentes

### Paso 1: Identificar el patrón incorrecto

Buscar en tu código:
```python
qec_config={
    'enabled': True,
    'type': '...',
    ...
}
```

### Paso 2: Reemplazar con parámetros individuales

```python
# Antes (❌)
qec_config={'enabled': True, 'type': 'surface_code', 'logical_qubits': 2}

# Después (✅)
qec_enabled=True,
qec_type='surface_code',
logical_qubits=2
```

---

## 📚 Ejemplos Completos

### Ejemplo 1: Molecular Docking con QEC

```python
from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY')

result = quantum(
    "Analyze ligand with SMILES CCO docking to receptor PDB 6B3J. "
    "Calculate binding affinity using surface code error correction with 2 logical qubits",
    backend='ibm_torino',
    shots=2000,
    api_key=api_key,
    qec_enabled=True,
    qec_type='surface_code',
    logical_qubits=2
)

print(f"Binding Affinity: {result.binding_affinity:.2f} kcal/mol")
print(f"Ki: {result.ki:.2f} nM")
```

### Ejemplo 2: Bell State con QEC

```python
result = quantum(
    "Create a Bell state and measure 1000 times using Steane code",
    backend='aws_braket',
    shots=1000,
    api_key=api_key,
    qec_enabled=True,
    qec_type='steane',      # 7 physical qubits per logical
    logical_qubits=2
)

print(f"Counts: {result.counts}")
```

### Ejemplo 3: Drug Design con QEC

```python
result = quantum(
    "Design a new drug for diabetes targeting GLP-1 receptor PDB 6B3J "
    "using surface code error correction distance 5",
    backend='ibm_brisbane',
    shots=4000,
    api_key=api_key,
    qec_enabled=True,
    qec_type='surface_code',
    logical_qubits=3
)

bio = result.bio_interpretation
print(f"Designed Molecule: {bio['designed_molecule']}")
print(f"Binding Affinity: {bio['binding_affinity']:.2f} kcal/mol")
```

---

## 🤖 Para el Agente VSIX

### Prompt Template Correcto

Cuando el usuario pide QEC, generar:

```python
from bioql import quantum
import os

api_key = os.getenv('BIOQL_API_KEY', 'your_key_here')

print("🧬 Quantum {task}")
print(f"Backend: {backend}")
print(f"QEC: {qec_type}")
print(f"Logical Qubits: {logical_qubits}")
print(f"Shots: {shots}")

result = quantum(
    "{prompt_description}",
    backend='{backend}',
    shots={shots},
    api_key=api_key,
    qec_enabled=True,              # ✅ Usar estos 3 parámetros
    qec_type='{qec_type}',         # ✅ NO usar qec_config
    logical_qubits={logical_qubits}  # ✅
)
```

### Reglas para el Agente:

1. **NUNCA** usar `qec_config` como diccionario
2. **SIEMPRE** usar parámetros individuales: `qec_enabled`, `qec_type`, `logical_qubits`
3. **INCLUIR** en el prompt la mención del tipo de QEC (e.g., "using surface_code error correction")
4. **VALIDAR** que `qec_type` sea uno de: `'surface_code'`, `'steane'`, `'shor'`

---

## 🧪 Testing

### Test Script Corregido

Ver archivo: `/Users/heinzjungbluth/Desktop/test_docking_qec_FIXED.py`

```bash
# Ejecutar
python /Users/heinzjungbluth/Desktop/test_docking_qec_FIXED.py

# Output esperado:
✅ Quillow QEC engine loaded
🧬 Molecular Docking Simulation with Quillow QEC
...
⚛️  Executing quantum docking with QEC protection...
✅ QEC Docking Complete!
```

---

## 📊 Cálculo de Recursos QEC

### Surface Code (d=3, 2 logical qubits):

```python
distance = 3
physical_per_logical = (2 * distance - 1) ** 2  # = 25
total_physical = logical_qubits * physical_per_logical  # = 50
```

### Tabla de Recursos:

| Distance | Physical/Logical | 2 Logical Qubits | 3 Logical Qubits |
|----------|------------------|------------------|------------------|
| d=3      | 25               | 50               | 75               |
| d=5      | 81               | 162              | 243              |
| d=7      | 169              | 338              | 507              |

---

## 🔗 Referencias

### Documentación Oficial:
- **BioQL API**: https://docs.bioql.bio
- **Quillow QEC**: `/Users/heinzjungbluth/Desktop/Spectrix_BioQL/Quillow/README.md`
- **VSIX Extension**: `/Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/releases/bioql-assistant-7.0.0-FIXED.vsix`
- **Release Notes**: `RELEASE_NOTES_v4.0.0.md` (líneas 148-157)

### Ejemplos en Producción:
- **Quantum Docking CLI**: `/Users/heinzjungbluth/Desktop/Spectrix_BioQL/bioql_quillow_docking/src/cli.py`
- **Web Interface**: https://api.bioql.bio/quantum-docking/

---

## ✅ Checklist de Corrección

- [ ] Remover `qec_config` del código
- [ ] Agregar `qec_enabled=True`
- [ ] Agregar `qec_type='surface_code'` (o 'steane', 'shor')
- [ ] Agregar `logical_qubits=2` (o el número deseado)
- [ ] Mencionar QEC en el prompt del `quantum()`
- [ ] Verificar que `BIOQL_API_KEY` esté configurada
- [ ] Testing con script corregido

---

## 📞 Soporte

Si encuentras más errores relacionados con QEC:

1. Verificar que estés usando parámetros individuales
2. Verificar la versión de BioQL: `pip show bioql`
3. Revisar logs: `/var/log/bioql/` (en servidor)
4. Contactar: support@bioql.bio

---

**Status:** ✅ RESUELTO
**Fecha de fix:** Octubre 28, 2025
**Versión BioQL:** 5.0.1+
**Versión Quillow:** 1.0.0+

---

🧬 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
