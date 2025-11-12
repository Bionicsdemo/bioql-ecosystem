# BioQL Agent - File Review/Fix Feature ✅

## El Problema Anterior

Cuando preguntabas:
```
@bioql review and fix the code in bioql from /Users/heinzjungbluth/Test/clinical_study.py
```

El agente respondía con **código incorrecto** porque:

1. **Agent corre en Modal (cloud)** - No tiene acceso a tu filesystem local
2. **No podía leer el archivo** - `/Users/heinzjungbluth/Test/clinical_study.py` no existe en Modal
3. **Generaba código genérico** - Sin contexto real del archivo

## La Solución

Ahora **VSCode envía el contenido del archivo** al agente automáticamente:

```
Tu VSCode (Mac local)
   ↓
Lee clinical_study.py
   ↓
Envía contenido al agente
   ↓
Modal Agent (cloud)
   ↓
Analiza el código REAL
   ↓
Retorna review/fixes
   ↓
VSCode muestra resultado
```

## Cómo Usar Correctamente

### Paso 1: Abre el archivo en VSCode

```
File → Open → /Users/heinzjungbluth/Test/clinical_study.py
```

El archivo debe estar **abierto y visible** en el editor.

### Paso 2: Usa el chat CON el archivo abierto

```
@bioql review and fix the code
```

O también:
```
@bioql analyze this code and suggest improvements
@bioql debug this file
@bioql fix the errors in this code
```

### Keywords que activan File Review:
- `review`
- `fix`
- `analyze`
- `debug`

## Lo que hace el Agent

1. **VSCode detecta keywords** (`review`, `fix`, etc.)
2. **VSCode lee el archivo abierto** (hasta 2000 caracteres)
3. **VSCode envía:**
   ```json
   {
     "request": "review and fix the code",
     "workspace_context": {
       "current_file": "/Users/.../clinical_study.py",
       "file_content": "from bioql import quantum\n..."
     }
   }
   ```
4. **Agent recibe el contenido** y lo analiza con el modelo
5. **Agent genera review** específico para ESE código
6. **VSCode muestra el resultado**

## Ejemplo Real

### Input:
```
@bioql review and fix the code
```

Con `clinical_study.py` abierto:
```python
from bioql import quantum
API_KEY = "__BIOQL_REDACTED__"  # Hardcoded!

for i in range(1000):  # 1000 API calls!
    genetic_variation = quantum(...)
```

### Output del Agent:
```markdown
### Code Review

Issues found:
1. **Security Risk**: API key is hardcoded (line 11)
   - Fix: Use environment variables

2. **Performance**: 1000 sequential API calls (line 76-81)
   - Fix: Batch quantum calls or use vectorization

3. **Error Handling**: No try/except blocks
   - Fix: Add error handling for API failures

4. **Missing Directory**: docking_results/ may not exist
   - Fix: Add os.makedirs() before saving

Suggested fixes:
```python
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('BIOQL_API_KEY')

# Create output directory
os.makedirs('docking_results', exist_ok=True)

# Batch quantum calls
try:
    results = quantum_batch([...], api_key=API_KEY)
except Exception as e:
    print(f"Error: {e}")
```
```

## Limitaciones

1. **2000 caracteres max** - Solo envía los primeros 2000 chars del archivo
2. **Archivo debe estar abierto** - No puede leer archivos cerrados
3. **Un archivo a la vez** - Solo revisa el archivo activo
4. **Modelo limitado** - El modelo fue entrenado en código BioQL, no es un code reviewer general

## Actualización Necesaria

### Reinstala la Extension v3.3.1

```bash
# Opción 1: Manual en VSCode
Extensions → ... → Install from VSIX
→ Selecciona: /Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.3.1.vsix

# Opción 2: CLI (si tienes `code` en PATH)
code --uninstall-extension SpectrixRD.bioql-assistant
code --install-extension /Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.3.1.vsix
```

**Después:** Reload Window (`Cmd+Shift+P` → "Developer: Reload Window")

## Verificación

Para verificar que funciona:

1. **Abre cualquier archivo Python** en VSCode
2. **Abre el chat** (`Cmd+Shift+P` → "Chat: Open")
3. **Escribe:** `@bioql review this code`
4. **Espera ~10 segundos**
5. **Deberías ver:** Un análisis específico de TU código

Si ves código genérico o ejemplos de DFT:
- ❌ La extension NO está actualizada
- ❌ El archivo NO está abierto
- ❌ No usaste keywords `review`/`fix`

## Comparación

### ❌ Antes (INCORRECTO):
```
User: @bioql review /Users/.../clinical_study.py
Agent: [Genera código genérico de DFT calculator]
```

### ✅ Ahora (CORRECTO):
```
User: [Abre clinical_study.py]
User: @bioql review this code
Agent: [Analiza el código real y sugiere fixes específicos]
```

## Archivos Modificados

### VSCode Extension
- ✅ `vscode-extension/extension.js:354-368` - Lee contenido del archivo
- ✅ `vscode-extension/bioql-assistant-3.3.1.vsix` - Rebuilt

### Modal Agent
- ✅ `modal/bioql_agent_simple.py:82-124` - Review/fix con file_content
- ✅ Deployed a Modal

## Próximas Mejoras

1. **Incrementar límite** - De 2000 a 5000+ caracteres
2. **Multi-file review** - Revisar múltiples archivos
3. **Apply fixes automatically** - Botón para aplicar fixes
4. **Diff view** - Mostrar antes/después
5. **Stream response** - Mostrar review mientras se genera

## Troubleshooting

**"Código genérico, no revisa mi archivo"**
- Asegúrate de que el archivo esté **abierto** en VSCode
- Usa keyword `review` o `fix` en tu request
- Reinstala extension v3.3.1

**"Error: file_content not found"**
- Extension no está actualizada
- Reload window después de instalar

**"Review muy corto o incompleto"**
- Archivo es >2000 chars (solo analiza primeros 2000)
- Modelo tiene timeout (max 500 tokens de respuesta)

## Conclusión

✅ **Ahora el agente SÍ puede revisar tu código real**

Solo asegúrate de:
1. Tener el archivo abierto en VSCode
2. Usar `@bioql review this code` (con keywords)
3. Tener extension v3.3.1 instalada

El agente analizará el contenido REAL y dará sugerencias específicas.
