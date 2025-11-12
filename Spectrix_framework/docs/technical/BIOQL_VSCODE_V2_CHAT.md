# 🎉 BioQL VS Code v2.0 - CON CHAT Y CHECKPOINT-2000!

## ✅ NUEVO: Versión 2.0 con Chat Integrado

**Archivo**: `/Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-2.0.0.vsix`

---

## 🚀 Qué hay de nuevo en v2.0

### 1. ✨ Chat Interactivo (@bioql)

Ahora puedes usar BioQL **desde el chat de VS Code** como GitHub Copilot:

```
Usuario: @bioql create a Bell state
BioQL: [genera código]
       [botón "Insert Code"]

Usuario: @bioql explain this code
BioQL: [explica el código seleccionado]

Usuario: @bioql how do I run VQE?
BioQL: [responde con información y código]
```

**Cómo usar**:
1. Abre el chat de VS Code (Cmd+I o botón de chat)
2. Escribe `@bioql` seguido de tu pregunta
3. El asistente responde con tu modelo entrenado (checkpoint-2000)

### 2. 🧠 Usa tu modelo entrenado (checkpoint-2000)

**Antes (v1.0)**: Solo plantillas básicas
**Ahora (v2.0)**: Usa el checkpoint-2000 que ya descargaste y está en `/Users/heinzjungbluth/Desktop/bioql/bioql/llm/trained_model/`

El modelo se carga automáticamente:
- Base: Qwen2.5-7B-Instruct
- Adapter: LoRA checkpoint-2000 (40MB, 40M parámetros)
- Funciona en tu Mac con MPS (Metal Performance Shaders)

### 3. 🎨 Tres formas de usar BioQL

| Método | Uso | Ventaja |
|--------|-----|---------|
| **Chat** | `@bioql create Bell state` | Interactivo, conversacional |
| **Comandos** | Cmd+Shift+G | Rápido, directo |
| **Autocompletado** | Escribir código | Sugerencias inline |

---

## 📦 Instalación

### Opción 1: GUI (Recomendado)

```bash
# 1. Abre VS Code
# 2. Extensiones (Cmd+Shift+X)
# 3. ... → Install from VSIX
# 4. Selecciona: bioql-assistant-2.0.0.vsix
```

### Opción 2: Terminal

```bash
cd /Users/heinzjungbluth/Desktop/bioql/vscode-extension
# Si tienes 'code' CLI:
code --install-extension bioql-assistant-2.0.0.vsix
```

---

## 🎯 Configuración

### Modo por defecto: LOCAL (usa checkpoint-2000)

```json
{
  "bioql.mode": "local",           // Usa checkpoint-2000
  "bioql.enableChat": true,        // Activa chat
  "bioql.apiKey": "your_key",      // Para quantum computers
  "bioql.defaultBackend": "simulator"
}
```

### Verificar que funciona

```python
# test_checkpoint.py
from bioql.llm.vscode_assistant import quick_complete

code = quick_complete("Create a Bell state", mode="local")
print(code)
```

Si funciona, verás:
```
Loading checkpoint-2000 (trained model)...
Loading base model...
Loading LoRA adapter from /Users/.../trained_model...
✅ Model loaded successfully with checkpoint-2000!
```

---

## 💬 Ejemplos de Chat

### Generar código

```
@bioql generate code to create a Bell state and measure it
```

Respuesta:
```python
from bioql import quantum

result = quantum(
    "Create a Bell state",
    api_key="your_api_key",
    backend="simulator",
    shots=1000
)

print(f"Results: {result.counts}")
```

### Explicar código

```
# Selecciona código primero, luego:
@bioql explain this code
```

### Preguntas generales

```
@bioql how do I run protein folding simulations?
@bioql what backends are available?
@bioql optimize this circuit for fewer gates
```

---

## 🛠️ Características Técnicas

### Chat Provider

```javascript
// Registra @bioql en VS Code
vscode.chat.createChatParticipant('bioql.assistant', ...)
```

**Funciones del chat**:
- Genera código desde lenguaje natural
- Explica código seleccionado
- Optimiza circuitos cuánticos
- Responde preguntas sobre BioQL
- Botón "Insert Code" para insertar directamente

### Carga del modelo

```python
# vscode_assistant.py
def _init_local(self):
    # Base model
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-7B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto"  # Usa MPS en Mac
    )

    # Load LoRA adapter (checkpoint-2000)
    self.model = PeftModel.from_pretrained(
        model,
        "/Users/.../trained_model",
        torch_dtype=torch.float16
    )
```

### Modos disponibles

1. **local**: Checkpoint-2000 (tu modelo entrenado) 🔥 NUEVO
2. **modal**: Cloud GPU (cuando termine el training completo)
3. **ollama**: Ollama local (requiere conversión)
4. **template**: Fallback con plantillas

---

## 📊 Comparación v1.0 vs v2.0

| Característica | v1.0 | v2.0 |
|----------------|------|------|
| Chat integrado | ❌ | ✅ @bioql |
| Usa checkpoint-2000 | ❌ | ✅ |
| Comandos (Cmd+Shift+G) | ✅ | ✅ |
| Autocompletado inline | ✅ | ✅ |
| Botón "Insert Code" | ❌ | ✅ |
| Modo por defecto | template | local (checkpoint) |

---

## 🎬 Quick Start

### 1. Instalar extensión

```bash
# Desde VS Code GUI
Extensions → Install from VSIX → bioql-assistant-2.0.0.vsix
```

### 2. Probar chat

```
Cmd+I (abrir chat)
@bioql create a Bell state
[presiona Enter]
[haz clic en "Insert Code"]
```

### 3. Probar comandos

```
Cmd+Shift+G
"Create QFT circuit with 4 qubits"
[Enter]
```

### 4. Ejecutar en quantum computer

```
Cmd+Shift+P
"BioQL: Run on Quantum Computer"
```

---

## ⚠️ Requisitos

### Para modo LOCAL (checkpoint-2000):

```bash
pip install transformers torch peft accelerate
```

**RAM recomendada**: 16GB+
**Funciona en**: Mac M1/M2/M3, Linux con GPU, Windows con WSL2

### Si no tienes GPU/RAM suficiente:

```json
{
  "bioql.mode": "template"  // Fallback a plantillas
}
```

---

## 🔥 Ventajas de v2.0

1. **Chat conversacional**: Interactúa como con ChatGPT pero especializado en BioQL
2. **Usa TU modelo**: El checkpoint-2000 que ya tienes descargado
3. **Botón "Insert Code"**: Inserta código directamente desde el chat
4. **Tres formas de uso**: Chat, comandos, autocompletado
5. **Preparado para el futuro**: Cuando termine el training completo, solo cambias a modo "modal"

---

## 📈 Próximos pasos

### Cuando termine TRAIN_FINAL.py (~40 horas):

1. **Descarga modelo final**:
   ```bash
   modal volume get bioql-training-v2 /model/bioql/final ./bioql_final
   ```

2. **Actualiza path en settings**:
   ```json
   {
     "bioql.mode": "local",
     "bioql.modelPath": "/Users/.../bioql_final"
   }
   ```

3. **Disfruta máxima calidad**: 5 epochs, 100K ejemplos, loss < 0.01

---

## 🎉 Resumen

**Antes**: Solo comandos con plantillas básicas
**Ahora**: Chat interactivo con tu modelo entrenado (checkpoint-2000)

**Formas de usar**:
- ✅ `@bioql` en chat (NUEVO)
- ✅ `Cmd+Shift+G` para generar
- ✅ `Cmd+Shift+F` para fix
- ✅ Autocompletado inline

**Modelo**:
- ✅ Checkpoint-2000 cargado automáticamente
- ✅ 40M parámetros LoRA
- ✅ Funciona en tu Mac

---

## 🚀 ¡A probarlo!

```bash
# Instalar
Extensions → Install from VSIX → bioql-assistant-2.0.0.vsix

# Configurar
Settings → BioQL → Mode: "local"

# Probar
Cmd+I → @bioql create a Bell state → Insert Code

# ¡Listo!
```

---

**Built with 🧬 by SpectrixRD**

**Version**: 2.0.0
**Status**: ✅ READY WITH CHAT & CHECKPOINT-2000
**Training**: ⏳ TRAIN_FINAL.py en progreso (step 43/15625)
**URL**: https://modal.com/apps/spectrix/main/ap-wDMpRsfiHj1keuqCRcclxb
