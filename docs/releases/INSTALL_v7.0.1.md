# 📦 Instalación de BioQL Assistant v7.0.1 - QEC Fix

**Fecha:** Octubre 28, 2025
**Versión:** 7.0.1
**Archivo:** `bioql-assistant-7.0.1.vsix`
**Status:** ✅ LISTO PARA INSTALAR

---

## 🚀 Instalación Rápida

### Método 1: VS Code UI (Recomendado)

1. **Desinstalar versión anterior (si existe):**
   - Abrir VS Code
   - Ir a Extensions (⌘+Shift+X en Mac, Ctrl+Shift+X en Windows/Linux)
   - Buscar "BioQL"
   - Click en el engranaje ⚙️ → "Uninstall"
   - **Restart VS Code**

2. **Instalar v7.0.1:**
   - Ir a Extensions (⌘+Shift+X)
   - Click en el menú "..." (arriba a la derecha)
   - Seleccionar "Install from VSIX..."
   - Navegar a:
     ```
     /Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/releases/bioql-assistant-7.0.1.vsix
     ```
   - Click "Install"
   - **Restart VS Code** cuando se solicite

3. **Verificar instalación:**
   - Abrir Extensions
   - Buscar "BioQL"
   - Debe mostrar: **"BioQL Code Assistant v7.0.1"**
   - Status: Enabled ✅

---

### Método 2: Terminal (Si `code` está en PATH)

```bash
# Desinstalar versión anterior
code --uninstall-extension SpectrixRD.bioql-assistant

# Instalar v7.0.1
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/releases
code --install-extension bioql-assistant-7.0.1.vsix

# Restart VS Code
# No hay comando para esto, hay que hacerlo manualmente
```

---

### Método 3: Agregar `code` al PATH (macOS)

Si el comando `code` no funciona:

```bash
# Abrir VS Code
# Cmd+Shift+P → Type "Shell Command: Install 'code' command in PATH"
# Después reiniciar la terminal

# Ahora puedes usar:
code --install-extension /path/to/bioql-assistant-7.0.1.vsix
```

---

## ✅ Verificación Post-Instalación

### 1. Verificar Versión

```bash
# En terminal
code --list-extensions --show-versions | grep bioql

# Debería mostrar:
# spectrixrd.bioql-assistant@7.0.1
```

### 2. Verificar Chat Agent

1. Abrir VS Code
2. Abrir Chat Panel (Cmd+Shift+I o View → Open View → Chat)
3. Escribir: `@bioql`
4. Debería aparecer el agente con autocompletado

### 3. Test de Generación de Código QEC

1. En el chat, escribir:
   ```
   @bioql dock aspirin to GLP-1 receptor 6B3J using surface code QEC with 2 logical qubits on IBM Torino
   ```

2. El código generado **DEBE** usar:
   ```python
   result = quantum(
       "...",
       backend='ibm_torino',
       shots=2000,
       api_key=api_key,
       qec_enabled=True,           # ✅ CORRECTO
       qec_type='surface_code',    # ✅ CORRECTO
       logical_qubits=2            # ✅ CORRECTO
   )
   ```

3. **NO debe** usar:
   ```python
   qec_config={...}  # ❌ INCORRECTO (versión 7.0.0)
   ```

---

## 🔧 Configuración Recomendada

### Settings en VS Code

Abrir Settings (Cmd+,) y buscar "bioql":

```json
{
  "bioql.apiKey": "tu_api_key_aqui",
  "bioql.mode": "modal",
  "bioql.defaultBackend": "ibm_torino",
  "bioql.enableQEC": true,
  "bioql.qecType": "surface_code",
  "bioql.defaultShots": 2000,
  "bioql.enableVisualizations": true
}
```

---

## 🧪 Testing Completo

### Test 1: Bell State sin QEC

```
@bioql create a Bell state with 1000 shots on simulator
```

Código esperado:
```python
result = quantum(
    "Create a Bell state and measure 1000 times",
    backend='simulator',
    shots=1000,
    api_key=api_key
    # Sin parámetros QEC - OK
)
```

### Test 2: Docking con QEC (Surface Code)

```
@bioql dock metformin to AMPK 2Y8L using surface code QEC distance 5
```

Código esperado:
```python
result = quantum(
    "Analyze ligand with SMILES ... docking to receptor PDB 2Y8L using surface_code error correction",
    backend='ibm_torino',
    shots=2000,
    api_key=api_key,
    qec_enabled=True,
    qec_type='surface_code',
    logical_qubits=2
)
```

### Test 3: Drug Design con QEC (Steane Code)

```
@bioql design drug for Alzheimer's targeting BACE1 with steane QEC
```

Código esperado:
```python
result = quantum(
    "Design a new drug for Alzheimer's targeting BACE1 receptor using steane error correction",
    backend='ibm_brisbane',
    shots=4000,
    api_key=api_key,
    qec_enabled=True,
    qec_type='steane',
    logical_qubits=3
)
```

---

## ❌ Troubleshooting

### Problema: Extension no aparece

**Solución:**
```bash
# Verificar que está instalada
code --list-extensions | grep bioql

# Si no aparece, reinstalar
code --install-extension /Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/releases/bioql-assistant-7.0.1.vsix

# Restart VS Code completamente (Cmd+Q, reabrir)
```

### Problema: Chat no funciona

**Solución:**
1. Verificar que API key esté configurada:
   - Settings → bioql.apiKey
2. Verificar que el modo esté en "modal":
   - Settings → bioql.mode = "modal"
3. Restart VS Code

### Problema: Genera código con `qec_config`

**Diagnóstico:**
Estás usando la versión 7.0.0, no 7.0.1

**Solución:**
```bash
# Ver versión instalada
code --list-extensions --show-versions | grep bioql

# Si muestra 7.0.0:
code --uninstall-extension SpectrixRD.bioql-assistant
code --install-extension bioql-assistant-7.0.1.vsix

# Restart VS Code
```

### Problema: Error "command not found: code"

**Solución macOS:**
1. Abrir VS Code
2. Cmd+Shift+P
3. Type: "Shell Command: Install 'code' command in PATH"
4. Reiniciar terminal

**Solución alternativa:**
Usar el método UI (Método 1) para instalar desde el menú de Extensions

---

## 📊 Comparación de Versiones

| Aspecto | v7.0.0 (Buggy) | v7.0.1 (Fixed) |
|---------|----------------|----------------|
| **QEC Parameters** | ❌ `qec_config={}` | ✅ `qec_enabled`, `qec_type`, `logical_qubits` |
| **Runtime Error** | ❌ `unexpected keyword argument` | ✅ Sin errores |
| **Code Generation** | ❌ Incorrect | ✅ Correct |
| **Release Date** | Oct 27, 2025 | Oct 28, 2025 |

---

## 📁 Archivos Relacionados

### En el Release

```
/Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/releases/
├── bioql-assistant-7.0.0-FIXED.vsix  # ❌ Versión anterior (buggy)
├── bioql-assistant-7.0.1.vsix        # ✅ Nueva versión (fixed)
├── INSTALL_v7.0.1.md                 # Este archivo
```

### En el Source

```
/Users/heinzjungbluth/Desktop/Spectrix_BioQL/Server_bioql/vscode_extension/bioql-assistant/
├── modal_serve_vscode.py             # ✅ Actualizado (líneas 401-429)
├── package.json                      # ✅ v7.0.1
├── RELEASE_NOTES_v7.0.1.md           # Documentación completa
```

### Documentación

```
/Users/heinzjungbluth/Desktop/Spectrix_BioQL/docs/
├── QEC_PARAMETER_FIX.md              # Guía técnica del fix
```

### Test Scripts

```
/Users/heinzjungbluth/Desktop/
├── test_docking_qec_FIXED.py         # Script corregido
```

---

## 🎯 Checklist de Instalación

- [ ] Desinstalar versión 7.0.0
- [ ] Restart VS Code
- [ ] Instalar versión 7.0.1 desde VSIX
- [ ] Restart VS Code nuevamente
- [ ] Verificar versión: v7.0.1 ✅
- [ ] Verificar Chat Agent funciona (@bioql)
- [ ] Test: Generar código con QEC
- [ ] Verificar: Usa `qec_enabled`, NO `qec_config`
- [ ] Configurar API key en Settings
- [ ] Ejecutar test script de ejemplo
- [ ] Confirmar: Sin errores ✅

---

## 🚀 Siguientes Pasos

Una vez instalado correctamente:

1. **Ejecutar test script:**
   ```bash
   cd /Users/heinzjungbluth/Desktop
   python test_docking_qec_FIXED.py
   ```

2. **Probar en VS Code Chat:**
   - Abrir chat
   - Pedir: `@bioql dock aspirin to 6B3J with QEC`
   - Verificar código generado

3. **Leer documentación:**
   - [RELEASE_NOTES_v7.0.1.md](../Server_bioql/vscode_extension/bioql-assistant/RELEASE_NOTES_v7.0.1.md)
   - [QEC_PARAMETER_FIX.md](QEC_PARAMETER_FIX.md)

---

## 📞 Soporte

### Issues Conocidos
✅ Ninguno - v7.0.1 es estable

### Reportar Problemas
- Email: support@bioql.bio
- GitHub: https://github.com/spectrixrd/bioql/issues

### Verificar Logs
```bash
# Ver logs de VS Code
# macOS: ~/Library/Application Support/Code/logs/
# Linux: ~/.config/Code/logs/
# Windows: %APPDATA%\Code\logs\
```

---

**🎉 Instalación Completa!**

Ya puedes usar BioQL Assistant v7.0.1 con QEC correctamente implementado.

---

🧬 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

---

**Versión:** 7.0.1
**Status:** ✅ STABLE
**Fecha:** Octubre 28, 2025
