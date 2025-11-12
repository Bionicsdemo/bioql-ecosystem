# BioQL Agent Integration - Model + Tools

## Arquitectura

```
┌─────────────┐
│   VSCode    │  @bioql create a Bell state
│  Extension  │
└──────┬──────┘
       │ HTTP POST
       ↓
┌──────────────────────────────────────┐
│    Modal App (GPU A10G)              │
│                                      │
│  ┌────────────────────────────────┐ │
│  │  SimpleBioQLAgent              │ │
│  │                                │ │
│  │  1. Analiza request            │ │
│  │  2. Decide acción (keyword)    │ │
│  │  3. Usa modelo para código     │ │
│  │  4. Ejecuta tool si necesario  │ │
│  └────────────────────────────────┘ │
│                                      │
│  ┌────────────────────────────────┐ │
│  │  DeepSeek-Coder Fine-tuned     │ │
│  │  (solo genera código)          │ │
│  └────────────────────────────────┘ │
│                                      │
└──────────────────────────────────────┘
       │
       ↓ JSON Response
┌─────────────┐
│   VSCode    │  Shows code + result
│     UI      │
└─────────────┘
```

## ¿Por qué este diseño?

### Problema Inicial
- El modelo no fue entrenado para usar tools
- Intentar que el modelo decida tools generaba outputs malformados
- Parsing de tools desde el modelo no funcionaba

### Solución: Agent Simple
- **Agent decide actions** basándose en keywords del request
- **Model solo genera código** (su trabajo original)
- **Agent ejecuta tools** cuando sea necesario

## Endpoints Disponibles

### 1. Inferencia Normal (solo código)
```
https://spectrix--bioql-inference-deepseek-generate-code.modal.run
```

**Input:**
```json
{
  "api_key": "bioql_test_...",
  "prompt": "Create a Bell state",
  "max_length": 300,
  "temperature": 0.7,
  "include_reasoning": true
}
```

**Output:**
```json
{
  "code": "from bioql import quantum...",
  "reasoning": "...",
  "cost": {...},
  "timing": {...}
}
```

### 2. Agent Simple (con tools)
```
https://spectrix--bioql-agent-simple-simple-agent.modal.run
```

**Input:**
```json
{
  "api_key": "bioql_test_...",
  "request": "Create a Bell state using BioQL",
  "workspace_context": {
    "workspace": "/path/to/workspace",
    "current_file": "test.py",
    "selected_text": ""
  }
}
```

**Output:**
```json
{
  "success": true,
  "action": "generate_code",
  "code": "from bioql import quantum...",
  "reasoning": "Generated code for...",
  "model": "bioql-simple-agent",
  "cost": {...},
  "timing": {...}
}
```

## Actions Soportadas

El agente detecta automáticamente qué hacer basándose en keywords:

### 1. Generate Code
**Keywords:** `create`, `generate`, `write code`, `bell state`, `quantum`

**Request:**
```
"Create a Bell state using BioQL"
```

**Action:** Llama al modelo para generar código

### 2. Execute Code
**Keywords:** `run`, `execute`

**Request:**
```
"Run Python code that prints Hello from BioQL"
```

**Action:** Genera código con el modelo y lo ejecuta

### 3. List Files
**Keywords:** `list`, `file`

**Request:**
```
"List all Python files"
```

**Action:** Lista archivos en workspace

### 4. Read File
**Keywords:** `read`, `file`

**Request:**
```
"Read file bioql/compiler.py"
```

**Action:** Lee contenido del archivo

### 5. Answer (default)
**Fallback para preguntas generales**

**Request:**
```
"What is a Bell state?"
```

**Action:** Usa el modelo para responder

## Uso en VSCode

### Automático
El agente se activa automáticamente cuando usas keywords específicas en el chat:

```
@bioql create a Bell state
@bioql run code that prints hello
@bioql list files in bioql/llm
@bioql read file test.py
```

### Detección
La función `detectToolRequirement()` detecta si necesitas tools:

```javascript
const toolKeywords = [
  'read file', 'write file', 'edit file', 'create file',
  'run', 'execute', 'test',
  'search', 'find in', 'grep',
  'list files', 'show files',
  'fix code in', 'update file'
];
```

### Response Format
El chat muestra:

```markdown
### Actions Taken

1. ✅ **generate_code**
   ```python
   from bioql import quantum
   result = quantum("Create Bell state", ...)
   ```

### Result

Generated code for: Create a Bell state using BioQL
```

## Costos

- **Inferencia normal:** ~$0.001-0.005 por request (1-5 segundos)
- **Agent:** ~$0.005-0.015 por request (5-15 segundos)
- Incluye 40% markup sobre costos de Modal
- Se factura por segundo de GPU usado

## Testing

### Test Local
```bash
python3 test_agent_modal.py
```

### Test API
```bash
curl -X POST https://spectrix--bioql-agent-simple-simple-agent.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "bioql_test_870ce7ae",
    "request": "Create a Bell state"
  }'
```

### Test VSCode
1. Abre VSCode con extensión BioQL instalada
2. Abre chat: `Cmd+Shift+P` → "Chat: Open"
3. Escribe: `@bioql create a Bell state`
4. El agente detectará el request y usará el modelo

## Archivos Clave

### Modal
- `modal/bioql_inference_deepseek.py` - Inferencia + Agent complejo (deprecated)
- `modal/bioql_agent_simple.py` - **Simple Agent (ACTUAL)** ✅

### VSCode
- `vscode-extension/extension.js` - Integración con agent
- `vscode-extension/package.json` - Configuración

### Python
- `bioql/llm/agent_wrapper.py` - Wrapper Python base
- `bioql/llm/enhanced_agent.py` - Agent Python extendido
- `test_agent_modal.py` - Tests

## Próximos Pasos

### Mejoras Posibles
1. **Multi-turn conversations** - Agent recuerda contexto
2. **More tools** - git, npm, docker integration
3. **Streaming responses** - Show code as it generates
4. **Tool chaining** - Multiple tools in sequence
5. **User approval** - Ask before executing dangerous ops

### Entrenamiento del Modelo
Para que el modelo aprenda tools nativamente:

```python
# Training data format
{
  "instruction": "Create a Bell state",
  "reasoning": "I need to generate BioQL code",
  "tools": [
    {"name": "generate_code", "params": "bell_state"}
  ],
  "code": "from bioql import quantum..."
}
```

Esto requeriría re-entrenar con ejemplos de tool usage.

## Troubleshooting

**Agent no activa:**
- Verifica que uses keywords correctas
- Chequea API key en settings
- Revisa Output Channel para errores

**Código no se genera:**
- Modelo puede estar frío (primer request)
- Aumenta timeout en settings
- Verifica balance de usuario

**Tools fallan:**
- Workspace context no se está enviando
- Archivos no existen en workspace
- Permisos de archivos

## Conclusión

El **Simple Agent** es la solución óptima:

✅ Usa el modelo para lo que sabe hacer (generar código)
✅ Agent decide acciones de manera determinística
✅ No requiere re-entrenar el modelo
✅ Funciona con el modelo fine-tuned actual
✅ Se integra perfectamente con VSCode

**Estado:** ✅ Production Ready
