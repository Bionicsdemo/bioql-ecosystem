# BioQL VS Code Assistant - Complete Guide

## 🎯 What You Get

**Intelligent code assistant for BioQL in VS Code** que puede:

✅ **Generar código** desde lenguaje natural
✅ **Completar código** automáticamente mientras escribes
✅ **Corregir errores** en tu código BioQL
✅ **Explicar código** cuántico
✅ **Optimizar circuitos** cuánticos
✅ **Ejecutar en computadoras cuánticas** directamente desde VS Code

## 📋 Requisitos

- VS Code instalado
- Python 3.11+
- BioQL instalado (`pip install bioql`)

## 🚀 Opción 1: Modo Template (MÁS FÁCIL - Funciona en cualquier Mac)

Sin GPU, sin modelo pesado. Usa templates inteligentes.

### Instalación

```bash
cd /Users/heinzjungbluth/Desktop/bioql/vscode-extension

# Instalar dependencias
npm install

# Instalar extensión en VS Code
code --install-extension .
```

### Configuración

1. Abre VS Code
2. Ve a Settings (Cmd+,)
3. Busca "BioQL"
4. Configura:
   - **Mode**: `template`
   - **API Key**: Tu API key de BioQL
   - **Default Backend**: `simulator`

### Uso

```python
# En un archivo .py en VS Code

# Opción 1: Comando
# Cmd+Shift+G → "Create a Bell state"

# Opción 2: Escribir y autocompletar
from bioql import quantum
# Escribe "quantum(" y presiona Tab para autocompletar

# Opción 3: Fix código
# Selecciona código con error
# Cmd+Shift+F para corregir

# Opción 4: Ejecutar en quantum computer
# Cmd+Shift+P → "BioQL: Run on Quantum Computer"
```

## 🔥 Opción 2: Modo Modal (RECOMENDADO - Usa GPU en la nube)

Usa tu modelo entrenado corriendo en Modal con GPU.

### Setup Modal API

1. **Despliega tu modelo en Modal:**

```bash
cd /Users/heinzjungbluth/Desktop/bioql
modal deploy modal_serve.py
```

Obtendrás una URL como: `https://spectrix--bioql-model-api-api-generate.modal.run`

2. **Configura VS Code:**

Settings → BioQL:
- **Mode**: `modal`
- **Modal URL**: `https://tu-url.modal.run`

### Ventajas

✅ Usa tu modelo entrenado en GPU A100
✅ Inferencia rápida (~100-200ms)
✅ Sin carga en tu Mac
✅ Calidad máxima

### Costo

~$0.20/hora de GPU T4 en Modal (muy económico)

## ⚡ Opción 3: Modo Ollama (LOCAL OPTIMIZADO - Mac M1/M2/M3)

Convierte tu modelo a formato Ollama para ejecución local optimizada.

### Setup

1. **Instala Ollama:**

```bash
brew install ollama
```

2. **Convierte tu modelo a Ollama:**

```bash
# Crear Modelfile
cat > Modelfile <<EOF
FROM /Users/heinzjungbluth/Desktop/bioql/bioql/llm/trained_model
PARAMETER temperature 0.7
PARAMETER top_p 0.9
EOF

# Crear modelo Ollama
ollama create bioql -f Modelfile
```

3. **Configura VS Code:**

Settings → BioQL:
- **Mode**: `ollama`

4. **Inicia Ollama:**

```bash
ollama serve
```

### Ventajas

✅ 100% local (privacidad total)
✅ Optimizado para Mac Silicon
✅ Inferencia rápida
✅ Sin costos

### Desventajas

❌ Requiere Mac M1/M2/M3
❌ Consume memoria (~8-10GB)

## 🎨 Comandos Disponibles

| Comando | Atajo | Descripción |
|---------|-------|-------------|
| `BioQL: Generate Code` | Cmd+Shift+G | Genera código desde descripción |
| `BioQL: Fix Code` | Cmd+Shift+F | Corrige código seleccionado |
| `BioQL: Explain Code` | - | Explica código seleccionado |
| `BioQL: Optimize Circuit` | - | Optimiza circuito cuántico |
| `BioQL: Run on Quantum Computer` | - | Ejecuta en computadora cuántica |

## 💡 Ejemplos de Uso

### 1. Generar código desde cero

```
1. Cmd+Shift+G
2. Escribe: "Create a Bell state and measure it"
3. Enter
4. ✨ Código generado automáticamente
```

### 2. Autocompletar mientras escribes

```python
from bioql import quantum

# Empieza a escribir...
result = quantum(
    # Presiona Tab → autocompleta con sugerencias inteligentes
```

### 3. Corregir errores

```python
# Código con error
result = quantum("bell sate")  # Typo: "sate" → "state"

# Selecciona la línea
# Cmd+Shift+F
# ✨ Auto-corregido a "bell state"
```

### 4. Ejecutar en quantum computer

```python
from bioql import quantum

result = quantum(
    "Create a Bell state",
    api_key="your_key",
    backend="ibm_quantum",  # Real quantum computer!
    shots=1000
)

print(result.counts)

# Cmd+Shift+P → "BioQL: Run on Quantum Computer"
# ⚛️ Se ejecuta en IBM Quantum y muestra resultados
```

## 🔧 Troubleshooting

### "Python execution failed"

```bash
# Verifica que BioQL esté instalado
pip install bioql

# Verifica Python path en VS Code
# Settings → Python: Python Path → /opt/homebrew/bin/python3
```

### "Modal URL not configured"

```bash
# Despliega el modelo primero
modal deploy modal_serve.py

# Copia la URL y ponla en Settings → BioQL → Modal URL
```

### "Ollama not running"

```bash
# Inicia Ollama
ollama serve

# Verifica que funciona
ollama list  # Debe mostrar "bioql"
```

## 📊 Comparación de Modos

| Característica | Template | Modal | Ollama | Local |
|----------------|----------|-------|--------|-------|
| Setup | ⭐⭐⭐ Fácil | ⭐⭐ Medio | ⭐⭐ Medio | ⭐ Difícil |
| Velocidad | ⚡ Instantáneo | ⚡⚡ Rápido | ⚡⚡⚡ Muy rápido | ⚡ Lento |
| Calidad | ⭐⭐ Básica | ⭐⭐⭐ Alta | ⭐⭐⭐ Alta | ⭐⭐⭐ Alta |
| Costo | 💰 Gratis | 💰💰 ~$0.20/h | 💰 Gratis | 💰 Gratis |
| Requiere | Nada | Internet | Mac M1+ | GPU NVIDIA |
| Privacidad | ✅ | ❌ | ✅ | ✅ |

## 🎯 Recomendación

1. **Empezar**: Modo `template` (funciona en cualquier Mac)
2. **Producción**: Modo `modal` (mejor calidad, corre en GPU)
3. **Privacidad**: Modo `ollama` (si tienes Mac M1/M2/M3)

## 🚀 Quick Start (30 segundos)

```bash
# 1. Instala extensión
cd /Users/heinzjungbluth/Desktop/bioql/vscode-extension
npm install
code --install-extension .

# 2. Abre VS Code
code test.py

# 3. Presiona Cmd+Shift+G
# 4. Escribe: "Create a Bell state"
# 5. ✨ ¡Código generado!
```

## 📚 Ejemplos Avanzados

### Protein Folding

```
Cmd+Shift+G → "Simulate protein folding for insulin using VQE"
```

### Drug Discovery

```
Cmd+Shift+G → "Simulate drug binding to GLP1R receptor for diabetes"
```

### Custom Circuit

```
Cmd+Shift+G → "Create a 5-qubit QFT circuit with measurement"
```

## 🔗 Integración con BioQL

La extensión se integra perfectamente con tu librería BioQL:

```python
from bioql import quantum

# El asistente entiende el contexto de BioQL
# y genera código compatible con todos los backends:
# - simulator
# - ibm_quantum
# - ionq

# También entiende bio-specific operations:
# - protein folding
# - drug docking
# - DNA analysis
```

## 🎉 ¡Listo!

Ahora tienes un **asistente AI especializado en BioQL** corriendo en VS Code que puede:
- Generar código cuántico
- Ejecutar en computadoras cuánticas reales
- Optimizar circuitos
- Todo mientras escribes código

---

**Built with 🧬 by SpectrixRD**
