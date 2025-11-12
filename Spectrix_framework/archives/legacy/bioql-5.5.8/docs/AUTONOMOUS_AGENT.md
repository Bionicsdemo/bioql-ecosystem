# 🤖 BioQL Autonomous Agent - Code Fixer/Improver/Refactorer

## ¡Nuevo! v3.4.0

El agente BioQL ahora **NO SOLO REVISA** - **ACTÚA SOBRE TU CÓDIGO**:

- ✅ **Fix and Apply** - Encuentra bugs y los corrige automáticamente
- 🎨 **Improve Code** - Mejora calidad, estructura, documentación
- ♻️  **Refactor** - Refactoriza para performance, legibilidad, seguridad

## Arquitectura

```
VSCode Editor
     ↓
  [Tu código con problemas]
     ↓
User: "@bioql fix and apply"
     ↓
Agente Autónomo en Modal
     ↓
1. Analiza código (encuentra issues)
2. Genera fixes
3. Calcula diff
4. Retorna código corregido
     ↓
VSCode muestra:
- Issues encontrados
- Diff de cambios
- Código fixed
- Botón "✅ Apply Changes"
     ↓
Click Apply → Código se reemplaza automáticamente
```

## Actions Disponibles

### 1. 🔧 Fix and Apply

**Qué hace:**
- Analiza código
- Encuentra bugs, syntax errors, security issues
- Genera código corregido
- Retorna diff para aplicar

**Keywords:**
```
@bioql fix and apply
@bioql fix this code automatically
@bioql apply fixes
```

**Ejemplo:**

```python
# Código con problemas:
API_KEY = "hardcoded_secret"  # ❌ Security risk
for i in range(1000):         # ❌ Performance issue
    result = quantum("test")
    print result              # ❌ Python 2 syntax
```

**User en VSCode:**
```
@bioql fix and apply
```

**Agente Response:**
```markdown
### 🔧 FIX_AND_APPLY Complete

**Changes:** 3 lines modified

**Issues Found:**
1. Security: API key is hardcoded
2. Performance: 1000 sequential API calls
3. Syntax: Python 2 print statement

**Diff:**
- API_KEY = "hardcoded_secret"
+ API_KEY = os.getenv('BIOQL_API_KEY')

- print result
+ print(result)

[✅ Apply Changes]
```

Click "✅ Apply Changes" → Código se actualiza automáticamente

---

### 2. 🎨 Improve Code

**Qué hace:**
- Mejora nombres de variables
- Agrega docstrings
- Añade type hints
- Mejora estructura
- Agrega error handling

**Keywords:**
```
@bioql improve code
@bioql improve this code quality
```

**Ejemplo:**

```python
# Código funcional pero mejorable:
def f(x):
    r = quantum(x, backend="simulator")
    return r
```

**User:**
```
@bioql improve code
```

**Improved:**
```python
def run_quantum_simulation(circuit_description: str) -> dict:
    """
    Executes a quantum simulation.

    Args:
        circuit_description: Natural language description of the circuit

    Returns:
        Simulation results with counts
    """
    try:
        result = quantum(
            circuit_description,
            backend="simulator",
            shots=1000
        )
        return result
    except Exception as e:
        raise RuntimeError(f"Quantum simulation failed: {e}")
```

---

### 3. ♻️  Refactor

**Qué hace:**
- Refactoriza para performance
- Optimiza estructura
- Mejora legibilidad
- Aumenta seguridad

**Keywords:**
```
@bioql refactor
@bioql refactor for performance
@bioql refactor this code
```

**Tipos de refactor:**
- `performance` - Optimiza velocidad
- `structure` - Mejora organización
- `readability` - Simplifica lógica
- `security` - Aumenta seguridad

**Ejemplo:**

```python
# Código con 100 llamadas secuenciales:
for i in range(100):
    result = quantum(f"test {i}", backend="simulator")
    print(result)
```

**User:**
```
@bioql refactor for performance
```

**Refactored:**
```python
# Batch quantum calls
test_circuits = [f"test {i}" for i in range(100)]

# Use batch API if available, or parallelize
results = quantum_batch(
    test_circuits,
    backend="simulator",
    shots=1000
)

for i, result in enumerate(results):
    print(f"Test {i}: {result}")
```

---

## Cómo Usar

### Paso 1: Instala Extension v3.4.0

```
/Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.4.0.vsix
```

**Instalación:**
1. VSCode → Extensions (`Cmd+Shift+X`)
2. `...` → "Install from VSIX..."
3. Selecciona `bioql-assistant-3.4.0.vsix`
4. **Reload Window** (`Cmd+Shift+P` → "Developer: Reload Window")

### Paso 2: Abre tu Código

Abre cualquier archivo Python en VSCode que quieras mejorar.

Ejemplo:
```bash
code /Users/heinzjungbluth/Test/clinical_study.py
```

### Paso 3: Usa el Agente Autónomo

En el chat de VSCode:

```
@bioql fix and apply
```

O:

```
@bioql improve code
```

O:

```
@bioql refactor for performance
```

### Paso 4: Revisa Cambios

El agente mostrará:
- ✅ Issues encontrados
- 📝 Diff de cambios
- 🔨 Código corregido
- **[✅ Apply Changes]** button

### Paso 5: Aplica los Cambios

Click en **"✅ Apply Changes"**

→ VSCode preguntará confirmación
→ Click "Apply"
→ ✅ Código reemplazado automáticamente
→ ✅ Archivo guardado

---

## Keywords Completas

### Fix and Apply
```
@bioql fix and apply
@bioql fix this code automatically
@bioql apply fixes to this code
@bioql fix bugs and apply changes
```

### Improve
```
@bioql improve code
@bioql improve this code quality
@bioql improve code structure
```

### Refactor
```
@bioql refactor
@bioql refactor this code
@bioql refactor for performance
@bioql refactor for security
@bioql refactor for readability
```

---

## Ejemplo Completo: clinical_study.py

**Problema Original:**
```python
# /Users/heinzjungbluth/Test/clinical_study.py
API_KEY = "bioql_test_8a3f9d2c..."  # Hardcoded!

for i in range(1000):  # 1000 API calls!
    genetic_variation = quantum(...)
    # No error handling
```

**User en VSCode:**
```
1. Abre clinical_study.py
2. Chat: @bioql fix and apply focusing on security and performance
```

**Agent Response:**
```markdown
### 🔧 FIX_AND_APPLY Complete

**Changes:** 15 lines modified

**Issues Found:**
1. Security: Hardcoded API key (line 11)
2. Performance: 1000 sequential API calls (lines 74-81)
3. Error Handling: No try/except blocks
4. Directory: docking_results/ may not exist

**Fixed Code:**
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('BIOQL_API_KEY')

# Create output directory
os.makedirs('docking_results', exist_ok=True)

# Batch quantum calls (reduce from 1000 to 10)
try:
    for i in range(10):
        genetic_variation = quantum(...)
except Exception as e:
    print(f"Error: {e}")

[✅ Apply Changes]
```

**User clicks:** "✅ Apply Changes"

→ ✅ clinical_study.py actualizado automáticamente!

---

## Configuración

### API Key (Requerido)

```json
{
  "bioql.apiKey": "bioql_test_870ce7ae"
}
```

### Optional Settings

```json
{
  "bioql.mode": "modal",
  "bioql.enableChat": true
}
```

---

## Costos

| Action | Tiempo Promedio | Costo Estimado |
|--------|----------------|----------------|
| Fix and Apply | 15-60s | $0.01-0.03 |
| Improve Code | 10-30s | $0.005-0.015 |
| Refactor | 15-45s | $0.01-0.025 |

**Nota:** Costos incluyen 40% markup sobre GPU A10G de Modal.

---

## Output Channel

Para ver logs detallados:

```
View → Output → "BioQL Assistant"
```

Verás:
```
🤖 Calling Autonomous Agent...
   Action: fix_and_apply
   File: /Users/.../clinical_study.py

💰 Autonomous Agent Cost:
   User Cost: $0.019838
   Time: 46.373s
   Changes: 3 lines

✅ Autonomous agent fixes applied to: clinical_study.py
```

---

## Endpoints

### Autónomo (Principal)
```
https://spectrix--bioql-agent-autonomous-agent-act.modal.run
```

**Actions:**
- `fix_and_apply` - Fix bugs and apply
- `improve` - Improve quality
- `refactor` - Refactor code

### Simple Agent (Review only)
```
https://spectrix--bioql-agent-simple-simple-agent.modal.run
```

Solo revisa, no modifica.

---

## Troubleshooting

### "No file open"
- Abre el archivo que quieres modificar primero
- El agente actúa sobre el archivo actualmente abierto

### "API key required"
- Configura `bioql.apiKey` en settings
- Reload window después de configurar

### "Changes count: 0"
- El código ya está bien
- O el modelo no detectó cambios significativos
- Intenta ser más específico: `@bioql fix security issues`

### Cambios no son buenos
- No apliques los cambios
- El modelo fine-tuned es bueno para código BioQL
- Para código general, puede no ser óptimo

---

## Comparación con Review Simple

| Feature | Review Simple | Autonomous Agent |
|---------|--------------|------------------|
| Analiza código | ✅ | ✅ |
| Encuentra issues | ✅ | ✅ |
| Genera fixes | ❌ | ✅ |
| Muestra diff | ❌ | ✅ |
| Aplica cambios | ❌ | ✅ (con botón) |
| Multi-step analysis | ❌ | ✅ |

### Cuándo usar cada uno

**Review Simple:**
- Solo quieres analizar
- Quieres entender el código
- No necesitas modificar

**Autonomous Agent:**
- Quieres fixes automáticos
- Necesitas mejorar calidad
- Quieres refactorizar
- Quieres ahorrar tiempo

---

## Próximas Mejoras

- [ ] Multi-file refactor
- [ ] Custom refactor rules
- [ ] Pre-commit hook integration
- [ ] Continuous code improvement
- [ ] Team code style enforcement
- [ ] Automatic PR creation

---

## Estado

✅ **Production Ready - v3.4.0**

- Agent autónomo desplegado en Modal
- VSCode extension integrada
- Fix and Apply funcionando
- Improve code funcionando
- Refactor funcionando
- Apply changes con confirmación
- Billing integrado
- Docs completas

---

## Conclusión

El **Agente Autónomo BioQL** ya no es solo un reviewer - es un **verdadero agente** que:

✅ Analiza tu código
✅ Encuentra problemas
✅ **Genera fixes**
✅ **Aplica cambios automáticamente**
✅ Mejora calidad
✅ Refactoriza código

Todo desde VSCode, con un simple:
```
@bioql fix and apply
```

🎉 **¡El agente que realmente ACTÚA sobre tu código!**
