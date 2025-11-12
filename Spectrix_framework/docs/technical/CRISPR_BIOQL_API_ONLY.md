# 🧬 CRISPR-QAI: Solo necesitas tu BioQL API Key

## ✅ CORRECCIÓN IMPORTANTE

**ANTES (INCORRECTO):**
```python
# ❌ WRONG - Pidiendo credenciales de IBM/AWS directamente
import os
from bioql.crispr_qai import estimate_energy_collapse_qiskit

result = estimate_energy_collapse_qiskit(
    guide_seq="ATCGAAGTCGCTAGCTA",
    backend_name="ibm_torino",
    shots=1000,
    ibm_token=os.getenv("IBM_QUANTUM_TOKEN")  # ❌ NO!
)
```

**AHORA (CORRECTO):**
```python
# ✅ CORRECT - Solo BioQL API Key
import os
from bioql import quantum

BIOQL_API_KEY = os.getenv("BIOQL_API_KEY")

result = quantum(
    "Score CRISPR guide ATCGAAGTCGCTAGCTA for binding energy",
    backend="ibm_torino",  # BioQL maneja IBM internamente!
    shots=1000,
    api_key=BIOQL_API_KEY,  # ✅ Solo esto!
    mode="crispr"
)
```

---

## 🎯 Por qué es mejor

### Antes (complicado y malo)
- ❌ Necesitas token de IBM Quantum
- ❌ Necesitas credenciales de AWS
- ❌ Necesitas configurar S3 buckets
- ❌ Necesitas manejar múltiples APIs
- ❌ Código diferente para cada backend
- ❌ Exposición de credenciales sensibles

### Ahora (simple y correcto)
- ✅ Solo tu BioQL API key
- ✅ BioQL maneja IBM internamente
- ✅ BioQL maneja AWS internamente
- ✅ Mismo código para todos los backends
- ✅ Sin exposición de credenciales
- ✅ Billing unificado

---

## 📋 Ejemplo Completo CORRECTO

```python
#!/usr/bin/env python3
"""
CRISPR-QAI con BioQL API
Solo necesitas tu BioQL API Key!
"""

import os
from bioql import quantum

# ==============================================================================
# TU BIOQL API KEY (único requisito)
# ==============================================================================

BIOQL_API_KEY = os.getenv("BIOQL_API_KEY")
if not BIOQL_API_KEY:
    raise RuntimeError("BIOQL_API_KEY not set. Get it at https://bioql.com/signup")

# ==============================================================================
# EJEMPLO 1: Simulador Local (gratis, rápido)
# ==============================================================================

print("1️⃣  Testing with local simulator...")
result = quantum(
    "Score CRISPR guide ATCGAAGTCGCTAGCTA for binding energy",
    backend="simulator",
    shots=1000,
    api_key=BIOQL_API_KEY,
    mode="crispr"
)

print(f"✅ Energy: {result.energy_estimate:.4f}")
print(f"✅ Confidence: {result.confidence:.4f}")
print()

# ==============================================================================
# EJEMPLO 2: IBM Torino 133q (hardware cuántico REAL)
# ==============================================================================

print("2️⃣  Running on IBM Torino 133-qubit quantum computer...")
result = quantum(
    "Score CRISPR guide ATCGAAGTCGCTAGCTA for binding energy",
    backend="ibm_torino",  # BioQL handles IBM credentials!
    shots=1000,
    api_key=BIOQL_API_KEY,  # Only this needed!
    mode="crispr"
)

print(f"✅ Energy: {result.energy_estimate:.4f}")
print(f"✅ Backend: IBM Torino 133q")
print()

# ==============================================================================
# EJEMPLO 3: AWS Braket (cloud quantum)
# ==============================================================================

print("3️⃣  Running on AWS Braket...")
result = quantum(
    "Score CRISPR guide ATCGAAGTCGCTAGCTA for binding energy",
    backend="SV1",  # BioQL handles AWS credentials!
    shots=1000,
    api_key=BIOQL_API_KEY,  # Only this needed!
    mode="crispr"
)

print(f"✅ Energy: {result.energy_estimate:.4f}")
print(f"✅ Backend: AWS Braket SV1")
print()

# ==============================================================================
# RANKING DE MÚLTIPLES GUIDES
# ==============================================================================

print("4️⃣  Ranking multiple guides...")
guides = [
    "ATCGAAGTCGCTAGCTA",
    "GCTAGCTACGATCCGA",
    "TTAACCGGTTAACCGG"
]

results = []
for guide in guides:
    result = quantum(
        f"Score CRISPR guide {guide} for binding energy",
        backend="ibm_torino",
        shots=1000,
        api_key=BIOQL_API_KEY,
        mode="crispr"
    )
    results.append({'guide': guide, 'energy': result.energy_estimate})

# Sort by energy (lower = better)
results.sort(key=lambda x: x['energy'])

print("✅ Top guides:")
for i, r in enumerate(results, 1):
    print(f"   {i}. {r['guide']}: {r['energy']:.4f}")

print("\n🎉 Todo con SOLO tu BioQL API key!")
```

---

## 🚀 Setup (3 pasos)

### 1. Obtén tu BioQL API Key
```bash
# Regístrate en https://bioql.com/signup
# Obtienes tu API key inmediatamente
```

### 2. Configura la variable de entorno
```bash
export BIOQL_API_KEY="bioql_tu_key_aqui"
```

### 3. ¡Úsalo!
```python
from bioql import quantum

result = quantum(
    "Score CRISPR guide ATCGAAGTCGCTAGCTA",
    backend="ibm_torino",  # O "SV1", "simulator"
    api_key=os.getenv("BIOQL_API_KEY"),
    mode="crispr"
)
```

---

## 🎛️ Backends Disponibles

| Backend | Descripción | BioQL maneja |
|---------|-------------|--------------|
| `simulator` | Simulador local | ✅ Nada que configurar |
| `aer_simulator` | IBM Qiskit simulator | ✅ Token IBM |
| `ibm_torino` | IBM 133 qubits | ✅ Token IBM |
| `ibm_kyoto` | IBM 127 qubits | ✅ Token IBM |
| `ibm_osaka` | IBM 127 qubits | ✅ Token IBM |
| `SV1` | AWS State Vector | ✅ Credenciales AWS |
| `DM1` | AWS Density Matrix | ✅ Credenciales AWS |
| `Aspen-M-3` | Rigetti 79 qubits | ✅ Credenciales AWS |
| `Harmony` | IonQ 11 qubits | ✅ Credenciales AWS |

**¡BioQL maneja TODAS las credenciales por ti!**

---

## 💡 Por qué funciona así

### Arquitectura BioQL

```
Usuario
  ↓ (BIOQL_API_KEY)
BioQL API Server
  ↓ (maneja credenciales internamente)
  ├─→ IBM Quantum (token manejado por BioQL)
  ├─→ AWS Braket (credenciales manejadas por BioQL)
  └─→ Local Simulator
```

**Beneficios:**
1. **Seguridad**: Las credenciales de IBM/AWS nunca salen del servidor BioQL
2. **Simplicidad**: Un solo API key para todo
3. **Billing**: Cobros unificados en tu cuenta BioQL
4. **Updates**: Nuevos backends sin cambiar código

---

## 🔒 Seguridad

### ✅ Correcto (BioQL API)
```python
# Credentials nunca expuestas
result = quantum(
    "Score guide...",
    backend="ibm_torino",
    api_key=BIOQL_API_KEY  # Solo esta key
)
```

### ❌ Incorrecto (Direct API - evitar)
```python
# ❌ Exponiendo token de IBM
result = estimate_energy_collapse_qiskit(
    guide_seq="...",
    ibm_token="eyJraWQ..."  # ❌ Expuesto en código!
)
```

---

## 📊 Pricing

**Con BioQL:**
- ✅ Un solo billing account
- ✅ Precios transparentes
- ✅ Créditos incluidos
- ✅ Sin sorpresas de AWS/IBM

**Sin BioQL:**
- ❌ Múltiples cuentas (IBM + AWS)
- ❌ Pricing complejo
- ❌ Sin unificación
- ❌ Facturas separadas

---

## 🎓 Ejemplos de Uso

### VS Code Extension
```
Cmd+Shift+P → "BioQL: Design CRISPR Guide"
→ Enter guide: ATCGAAGTCGCTAGCTA
→ Select: IBM Torino
→ Solo pide BIOQL_API_KEY ✅
```

### Python API
```python
from bioql import quantum

result = quantum(
    "Design CRISPR guide for BRCA1 knockout",
    backend="ibm_torino",
    shots=1000,
    api_key=BIOQL_API_KEY
)
```

### CLI
```bash
export BIOQL_API_KEY="tu_key"

bioql-crispr score \
  --guide ATCGAAGTCGCTAGCTA \
  --backend ibm_torino \
  --shots 1000
```

**¡Todo con la misma API key!**

---

## 🐛 Troubleshooting

### "BIOQL_API_KEY not set"
```bash
# Solución:
export BIOQL_API_KEY="bioql_tu_key_aqui"
```

### "Invalid API key"
```bash
# Verifica tu key en https://bioql.com/dashboard
# O regenera una nueva
```

### "Backend not available"
```bash
# Algunos backends requieren plan Pro
# Verifica en https://bioql.com/pricing
```

---

## ✅ Resumen

**Lo que cambió:**
- ❌ ANTES: Necesitabas IBM_QUANTUM_TOKEN
- ❌ ANTES: Necesitabas AWS credentials
- ❌ ANTES: Código diferente por backend
- ✅ AHORA: Solo BIOQL_API_KEY
- ✅ AHORA: BioQL maneja todo internamente
- ✅ AHORA: Mismo código para todos los backends

**Código correcto:**
```python
from bioql import quantum

result = quantum(
    "Score CRISPR guide ATCGAAGTCGCTAGCTA",
    backend="ibm_torino",  # O cualquier otro backend
    api_key=os.getenv("BIOQL_API_KEY"),  # Solo esto!
    mode="crispr"
)
```

**¡Así de simple! 🎉**

---

*Actualizado: 2025-10-08*
*BioQL v5.4.3 + Modal Agent + VSIX v4.5.0*
