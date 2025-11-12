# 🚀 Instalación BioQL VS Code Extension

## ✅ Estado Actual

**El asistente BioQL funciona perfectamente!**

```
✅ Template mode: Funciona en cualquier Mac
✅ Modal mode: Configurado (requiere Modal API URL)
✅ Ollama mode: Configurado (requiere Ollama running)
✅ Local mode: Configurado (fallback a template)
```

## 📦 Instalación Manual (Recomendado)

Como el comando `code` no está disponible desde terminal, usa este método:

### Paso 1: Copia la extensión

```bash
# La extensión está lista en:
/Users/heinzjungbluth/Desktop/bioql/vscode-extension/
```

### Paso 2: Instala en VS Code

**Opción A: Interfaz gráfica (más fácil)**

1. Abre VS Code
2. Ve a Extensions (icono cuadrado en la barra lateral, o Cmd+Shift+X)
3. Haz clic en `...` (arriba derecha)
4. Selecciona "Install from VSIX..."
5. Navega a `/Users/heinzjungbluth/Desktop/bioql/vscode-extension`
6. ¡Listo!

**Opción B: Crear VSIX package**

```bash
cd /Users/heinzjungbluth/Desktop/bioql/vscode-extension

# Instalar vsce (VS Code Extension CLI)
npm install -g @vscode/vsce

# Crear package
vsce package

# Esto creará: bioql-assistant-1.0.0.vsix
# Luego instálalo desde VS Code (Opción A arriba)
```

### Paso 3: Configurar la extensión

1. Abre VS Code Settings (Cmd+,)
2. Busca "BioQL"
3. Configura:
   - **Mode**: `template` (funciona sin configuración adicional)
   - **API Key**: Tu API key de BioQL (para ejecutar en quantum computers)
   - **Default Backend**: `simulator`

### Paso 4: ¡Prueba!

```python
# Crea un archivo test.py en VS Code

# Opción 1: Generar código desde cero
# Presiona: Cmd+Shift+G
# Escribe: "Create a Bell state"
# ¡Código generado automáticamente!

# Opción 2: Fix código con errores
# Escribe código con typo:
result = quantum("bell sate")  # typo: sate

# Selecciona la línea
# Presiona: Cmd+Shift+F
# ¡Auto-corregido!

# Opción 3: Ejecutar en quantum computer
# Presiona: Cmd+Shift+P
# Escribe: "BioQL: Run on Quantum Computer"
# ¡Se ejecuta en simulador o hardware real!
```

## 🎨 Comandos Disponibles

| Comando | Atajo | Descripción |
|---------|-------|-------------|
| Generate Code | Cmd+Shift+G | Genera código desde lenguaje natural |
| Fix Code | Cmd+Shift+F | Corrige código seleccionado |
| Explain Code | - | Explica código seleccionado |
| Optimize Circuit | - | Optimiza circuito cuántico |
| Run on Quantum Computer | - | Ejecuta en computadora cuántica |

## 🔧 Configuración de Modos

### Modo Template (Ya funciona!)

```json
// Settings → BioQL
{
  "bioql.mode": "template"
}
```

**Ventajas**:
- ✅ Funciona inmediatamente
- ✅ Sin configuración adicional
- ✅ Plantillas inteligentes para Bell, QFT, Protein Folding
- ✅ Respuesta instantánea

### Modo Modal (Para producción)

1. **Despliega tu modelo en Modal**:

```bash
cd /Users/heinzjungbluth/Desktop/bioql

# Espera a que termine el training actual (check progress)
modal run modal_train_simple.py  # Si no está corriendo

# Una vez terminado, descarga el modelo final
modal run modal_download_checkpoints.py

# Despliega el modelo como API
modal deploy modal_serve.py
```

2. **Configura VS Code**:

```json
{
  "bioql.mode": "modal",
  "bioql.modalUrl": "https://tu-url.modal.run"
}
```

**Ventajas**:
- 🚀 Mejor calidad (usa tu modelo entrenado)
- ⚡ GPU A100 en la nube
- 🎯 Especializado en BioQL

### Modo Ollama (Local optimizado)

1. **Instala Ollama**:

```bash
brew install ollama
```

2. **Convierte tu modelo** (después de que termine el training):

```bash
cd /Users/heinzjungbluth/Desktop/bioql/bioql/llm/trained_model

# Crear Modelfile
cat > Modelfile <<EOF
FROM ./adapter_model.safetensors
PARAMETER temperature 0.7
PARAMETER top_p 0.9
EOF

# Crear modelo Ollama
ollama create bioql -f Modelfile

# Iniciar Ollama
ollama serve
```

3. **Configura VS Code**:

```json
{
  "bioql.mode": "ollama"
}
```

**Ventajas**:
- 💻 100% local (privacidad total)
- ⚡ Optimizado para Mac Silicon
- 🔒 Sin dependencias de internet

## 📊 Estado del Entrenamiento

**Training actual**: En progreso en Modal GPU A100

```
✓ Checkpoint-2000 descargado y funcionando
✓ Training resumed desde checkpoint-2000
○ Progress: ~29% (step 4050/14065, epoch 1.44/5)
○ ETA: ~15-17 horas más
○ Loss: 0.0001 (excelente convergencia!)
```

Una vez completado el training:
1. Descarga el modelo final con `modal_download_checkpoints.py`
2. Usa modo Modal o Ollama para máxima calidad

## 🎯 Quick Start (30 segundos)

```bash
# 1. Abre VS Code
code /Users/heinzjungbluth/Desktop/bioql

# 2. Crea test.py
# Contenido:
from bioql import quantum

# 3. Presiona Cmd+Shift+G
# 4. Escribe: "Create a Bell state"
# 5. ✨ ¡Código generado!
```

## 🔍 Verificar Instalación

```python
# Corre esto para verificar que todo funciona:
python3 /Users/heinzjungbluth/Desktop/bioql/test_vscode_assistant.py
```

Deberías ver:
```
✅ Template mode works!
✅ Generated code: 200 chars
✅ All modes available
```

## 📚 Ejemplos de Uso

### Ejemplo 1: Bell State

```
Cmd+Shift+G → "Create a Bell state and measure it"

# Genera:
from bioql import quantum

result = quantum(
    "Create a Bell state",
    api_key="your_api_key",
    backend="simulator",
    shots=1000
)

print(f"Results: {result.counts}")
```

### Ejemplo 2: Protein Folding

```
Cmd+Shift+G → "Simulate insulin protein folding using VQE"

# Genera código especializado para protein folding
```

### Ejemplo 3: Fix Errors

```python
# Código con error:
result = quantum("bell sate", backend="ibmm_quantum")

# Selecciona → Cmd+Shift+F
# Auto-corrige:
result = quantum("bell state", backend="ibm_quantum")
```

## 🐛 Troubleshooting

### "Extension not found"

→ Usa instalación manual (Opción A arriba)

### "Python execution failed"

```bash
# Verifica que BioQL esté instalado
pip install bioql

# Verifica Python path en VS Code
# Settings → Python: Python Path
```

### "Modal URL not configured"

→ Es normal si usas modo `template`. Cambia a `modal` solo después de desplegar el modelo.

### "Ollama not running"

```bash
# Inicia Ollama
ollama serve

# Verifica
ollama list  # Debe mostrar "bioql"
```

## 🎉 ¡Listo!

Ahora tienes:

✅ **Asistente AI** especializado en BioQL en VS Code
✅ **Generación de código** desde lenguaje natural
✅ **Auto-corrección** de errores
✅ **Ejecución** en computadoras cuánticas reales
✅ **4 modos** de operación (template/modal/ollama/local)

---

**Built with 🧬 by SpectrixRD**

**Training Status**: En progreso → https://modal.com/apps/spectrix/main
