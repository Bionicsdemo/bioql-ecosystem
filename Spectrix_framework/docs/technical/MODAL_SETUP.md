# 🚀 BioQL VS Code Extension - Modal Setup

Tu modelo Qwen2.5-7B está desplegado en Modal y listo para usar desde VS Code!

## ✅ Servidor Activo

**URL:** `https://spectrix--bioql-vscode-fastapi-app.modal.run`

**Endpoints disponibles:**
- `GET /health` - Check server status
- `POST /generate` - Generate BioQL code from prompt

## 📝 Configurar VS Code

### Método 1: Settings UI (Recomendado)

1. Abre VS Code
2. Presiona `Cmd+,` (Settings)
3. Busca "BioQL"
4. Configura:
   - **BioQL: Mode** → `modal`
   - **BioQL: Modal Url** → `https://spectrix--bioql-vscode-fastapi-app.modal.run/generate`
   - **BioQL: Enable Chat** → ✅ (checked)
   - **BioQL: Default Backend** → `simulator`

### Método 2: settings.json

1. Presiona `Cmd+Shift+P`
2. Escribe: "Preferences: Open User Settings (JSON)"
3. Agrega:

```json
{
  "bioql.mode": "modal",
  "bioql.modalUrl": "https://spectrix--bioql-vscode-fastapi-app.modal.run/generate",
  "bioql.enableChat": true,
  "bioql.defaultBackend": "simulator"
}
```

## 🎯 Probar la Extensión

### Opción 1: Chat (@bioql)

1. Abre el chat: `Cmd+I`
2. Escribe: `@bioql create a Bell state`
3. Presiona Enter
4. ✨ El modelo en Modal generará el código

### Opción 2: Comando Generate

1. Abre un archivo `.py`
2. Presiona `Cmd+Shift+G`
3. Escribe: `create a 3-qubit GHZ state`
4. Enter
5. ✨ Código insertado

### Opción 3: Fix Code

1. Escribe código con un error
2. Selecciona el código
3. Presiona `Cmd+Shift+F`
4. ✨ Código corregido

## 🔍 Verificar que Funciona

### Test 1: Health Check

```bash
curl https://spectrix--bioql-vscode-fastapi-app.modal.run/health
```

Respuesta esperada:
```json
{"status":"healthy","model":"Qwen2.5-7B-Instruct"}
```

### Test 2: Generate Code

```bash
curl -X POST https://spectrix--bioql-vscode-fastapi-app.modal.run/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a Bell state","max_length":300,"temperature":0.7}'
```

Respuesta esperada:
```json
{
  "code": "from bioql import quantum\n\nresult = quantum(...)",
  "success": true
}
```

## 📊 Monitorear el Servidor

**Dashboard de Modal:**
https://modal.com/apps/spectrix/main/deployed/bioql-vscode

Aquí puedes ver:
- Requests activos
- Latencia
- Errores
- Logs en tiempo real
- Costos

## 💰 Costos

GPU A10G cuesta aprox:
- **$0.0004/segundo** mientras está activo
- **Scaledown** automático después de 5 minutos sin uso
- **Sin costo** cuando no está en uso

Ejemplo:
- 100 requests/día
- ~5 segundos/request
- ~500 segundos/día = ~$0.20/día

## 🛠️ Comandos Útiles

### Ver logs en tiempo real
```bash
modal app logs bioql-vscode --follow
```

### Actualizar el deployment
```bash
cd /Users/heinzjungbluth/Desktop/bioql/vscode-extension
modal deploy modal_serve_simple.py
```

### Detener el servidor
```bash
modal app stop bioql-vscode
```

## 🎨 Ejemplos de Uso

### Ejemplo 1: Generate Bell State
```
@bioql create a Bell state
```

### Ejemplo 2: Grover's Algorithm
```
@bioql implement Grover's algorithm for 3 qubits
```

### Ejemplo 3: Quantum Fourier Transform
```
@bioql create a QFT circuit for 4 qubits
```

### Ejemplo 4: Fix Code
Selecciona código con errores y presiona `Cmd+Shift+F`

## ⚙️ Troubleshooting

### Error: "Modal URL not configured"
- Verifica que `bioql.modalUrl` esté configurado correctamente
- URL debe terminar en `/generate`

### Error: "Connection refused"
- Verifica que el servidor esté activo en Modal dashboard
- Puede tomar ~30 segundos en arrancar la primera vez (cold start)

### Error: "Timeout"
- El modelo está cargándose (primera request)
- Espera ~2 minutos y vuelve a intentar
- Requests subsiguientes serán más rápidas (<5 seg)

### Código generado no es bueno
- Ajusta `temperature` (más bajo = más conservador)
- Sé más específico en tu prompt
- Ejemplo: "Create a Bell state using Hadamard and CNOT gates"

## 📚 Más Info

- Modal Docs: https://modal.com/docs
- BioQL Docs: /Users/heinzjungbluth/Desktop/bioql/docs/
- VS Code Extension Guide: INSTALL_VSCODE_EXTENSION.md

## 🎉 ¡Listo!

Tu extensión de VS Code ahora usa tu modelo Qwen2.5-7B desplegado en Modal con GPU A10G.

**No necesitas ninguna configuración adicional** - simplemente usa `@bioql` en el chat o `Cmd+Shift+G` para generar código.

¡Disfruta tu asistente de código cuántico powered by AI! 🚀
