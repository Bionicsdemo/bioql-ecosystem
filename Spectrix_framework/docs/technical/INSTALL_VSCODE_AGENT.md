# Instalar BioQL VSCode Extension con Agent

## 📦 VSIX Generado

```
/Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.3.1.vsix
```

## 🚀 Instalación Manual

### Opción 1: Desde VSCode (Recomendado)

1. **Abre VSCode**

2. **Ve a Extensions:**
   - `Cmd+Shift+X` o click en el ícono de extensiones

3. **Instala desde VSIX:**
   - Click en `...` (tres puntos) arriba a la derecha
   - Selecciona "Install from VSIX..."
   - Navega a: `/Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.3.1.vsix`
   - Click "Install"

4. **Reload VSCode:**
   - `Cmd+Shift+P` → "Developer: Reload Window"

### Opción 2: Línea de comandos

Si tienes el comando `code` en tu PATH:

```bash
# Desinstalar versión anterior
code --uninstall-extension SpectrixRD.bioql-assistant

# Instalar nueva versión
code --install-extension /Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.3.1.vsix

# Verificar
code --list-extensions | grep bioql
```

## ⚙️ Configuración

1. **Abre Settings en VSCode:**
   - `Cmd+,` o `Code > Settings > Settings`

2. **Busca "bioql"**

3. **Configura:**
   ```json
   {
     "bioql.mode": "modal",
     "bioql.apiKey": "bioql_test_870ce7ae",
     "bioql.enableChat": true
   }
   ```

## 🧪 Probar el Agent

1. **Abre el Chat:**
   - `Cmd+Shift+P` → "Chat: Open"
   - O usa el ícono de chat en la barra lateral

2. **Usa @bioql:**

   ```
   @bioql create a Bell state
   ```

   ```
   @bioql run Python code that prints hello
   ```

   ```
   @bioql what is a quantum superposition?
   ```

## 🤖 Cómo Funciona el Agent

El agent ahora **siempre** se usa para todos los requests:

1. **Analiza tu request** usando keywords
2. **Decide qué hacer:**
   - `create`, `generate` → genera código
   - `run`, `execute` → genera y ejecuta
   - `list`, `files` → lista archivos
   - `read`, `file` → lee archivo
   - Otros → responde con el modelo

3. **Usa el modelo** DeepSeek fine-tuned para código
4. **Ejecuta actions** en Modal si es necesario
5. **Muestra resultado** en el chat

## 📊 Response Format

### Generar Código

```
@bioql create a Bell state
```

**Response:**
```markdown
### Code

​```python
from bioql import quantum
result = quantum("Create Bell state", backend="simulator")
print(result)
​```

[📋 Insert Code]
```

### Ejecutar Código

```
@bioql run code that prints hello
```

**Response:**
```markdown
### Action

✅ **execute_code**

​```
Hello from BioQL!
​```
```

### Listar Archivos

```
@bioql list files
```

**Response:**
```markdown
### Action

✅ **list_files**

​```
bioql/
  __init__.py
  compiler.py
  parser.py
...
​```
```

## 🔗 Endpoints Usados

- **Agent:** `https://spectrix--bioql-agent-simple-simple-agent.modal.run`
- **Model:** DeepSeek-Coder-1.3B fine-tuned on BioQL

## 🐛 Troubleshooting

### "Error: request is required"
- Asegúrate de tener la versión 3.3.1 instalada
- Verifica que el API key esté configurado
- Reloaded VSCode después de instalar

### Agent no responde
- Verifica conexión a internet
- Chequea que Modal esté corriendo: https://modal.com/apps/spectrix
- Revisa el Output Channel: `View > Output > BioQL Assistant`

### No veo @bioql en el chat
- Asegúrate de tener VSCode 1.90+
- Verifica que `bioql.enableChat` esté `true`
- Reload window: `Cmd+Shift+P` → "Developer: Reload Window"

## ✅ Verificación

Después de instalar, deberías ver:

1. En Extensions: "BioQL Code Assistant v3.3.1" instalado
2. En Output: "🚀 BioQL Code Assistant activated!"
3. En Chat: Puedes escribir `@bioql`

## 🎉 Listo!

Ahora puedes usar el agent inteligente directamente en VSCode.

Ejemplos:
```
@bioql create a Bell state
@bioql optimize this quantum circuit
@bioql run a Grover search with 3 qubits
@bioql explain this code: [selecciona código]
```
