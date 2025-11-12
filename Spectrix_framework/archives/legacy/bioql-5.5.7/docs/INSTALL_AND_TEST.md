# 🚀 Instalar y Probar Agente Autónomo en VSCode

## ✅ Estado Actual

- 🤖 Agente en Modal: **ACTIVO** ✅
- 📦 Extension v3.4.0: **EMPAQUETADA** ✅
- 🔗 Endpoints: **FUNCIONANDO** ✅

**Lo que falta:** Instalar la extensión en tu VSCode

---

## 📦 Paso 1: Instalar Extension v3.4.0

### Opción A: Manual (Recomendado)

1. **Abre VSCode**

2. **Desinstala versión anterior** (si la tienes):
   ```
   - Extensions (Cmd+Shift+X)
   - Busca "BioQL"
   - Click engranaje ⚙️ → "Uninstall"
   ```

3. **Instala v3.4.0**:
   ```
   - Extensions (Cmd+Shift+X)
   - Click ... (tres puntos arriba derecha)
   - "Install from VSIX..."
   - Selecciona:
     /Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.4.0.vsix
   - Click "Install"
   ```

4. **Reload Window**:
   ```
   Cmd+Shift+P → "Developer: Reload Window"
   ```

5. **Verifica instalación**:
   ```
   - Extensions → Busca "BioQL"
   - Debe decir: "v3.4.0"
   - Status: Enabled
   ```

### Opción B: Command Line (si tienes `code` en PATH)

```bash
# Desinstalar anterior
code --uninstall-extension SpectrixRD.bioql-assistant

# Instalar v3.4.0
code --install-extension /Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.4.0.vsix

# Verificar
code --list-extensions | grep bioql
```

---

## ⚙️ Paso 2: Configurar

1. **Abre Settings** (`Cmd+,`)

2. **Busca "bioql"**

3. **Configura:**
   ```json
   {
     "bioql.mode": "modal",
     "bioql.apiKey": "bioql_test_870ce7ae",
     "bioql.enableChat": true
   }
   ```

4. **Verifica Output Channel**:
   ```
   View → Output → Selecciona "BioQL Assistant"
   ```

   Debe mostrar:
   ```
   🚀 BioQL Code Assistant activated!
   ✅ BioQL Assistant ready!
   ```

---

## 🧪 Paso 3: Probar Agente Autónomo

### Test 1: Fix and Apply (Básico)

1. **Crea archivo de prueba**:
   ```bash
   cat > /tmp/test_agent.py << 'EOF'
   from bioql import quantum

   # Código con problemas
   API_KEY = "hardcoded_secret"  # Security issue

   for i in range(1000):  # Performance issue
       result = quantum("test")
       print result  # Syntax error!
   EOF
   ```

2. **Abre el archivo en VSCode**:
   ```bash
   code /tmp/test_agent.py
   ```

3. **Abre Chat**:
   ```
   Cmd+Shift+P → "Chat: Focus on Chat View"
   ```

4. **Escribe en el chat**:
   ```
   @bioql fix and apply
   ```

5. **Espera respuesta** (~30-60 segundos):
   ```markdown
   ### 🔧 FIX_AND_APPLY Complete

   **Changes:** 3 lines modified

   **Issues Found:**
   1. Hardcoded API key
   2. 1000 sequential calls
   3. Python 2 syntax

   **Fixed Code:**
   [código corregido...]

   [✅ Apply Changes]
   ```

6. **Click "✅ Apply Changes"**
   - Confirma "Apply"
   - ✅ Código se actualiza automáticamente!

---

### Test 2: Improve Code

1. **Crea código mejorable**:
   ```bash
   cat > /tmp/improve_test.py << 'EOF'
   from bioql import quantum

   def f(x):
       r = quantum(x, backend="simulator")
       return r
   EOF
   ```

2. **Abre en VSCode**:
   ```bash
   code /tmp/improve_test.py
   ```

3. **En el chat**:
   ```
   @bioql improve code
   ```

4. **Espera resultado** con:
   - Docstrings
   - Type hints
   - Better names
   - Error handling

---

### Test 3: Refactor

1. **Crea código con performance issues**:
   ```bash
   cat > /tmp/refactor_test.py << 'EOF'
   from bioql import quantum

   for i in range(100):
       result = quantum(f"test {i}", backend="simulator")
       print(result)
   EOF
   ```

2. **Abre en VSCode**

3. **En el chat**:
   ```
   @bioql refactor for performance
   ```

4. **Espera refactoring** optimizado

---

## 🐛 Troubleshooting

### "Extension not found"
```
1. Verifica instalación:
   Extensions → Search "BioQL"
2. Debe aparecer "BioQL Code Assistant v3.4.0"
3. Si no aparece, reinstala desde VSIX
```

### "No chat participant @bioql"
```
1. Verifica que VSCode es v1.90+
2. Reload window: Cmd+Shift+P → "Developer: Reload Window"
3. Verifica: bioql.enableChat = true
```

### "Agent responde pero no detecta autonomous actions"
```
1. Verifica keywords exactos:
   - "fix and apply" ✅
   - "fix" ❌ (no suficiente)
   - "improve code" ✅
   - "refactor" ✅

2. Verifica Output Channel:
   View → Output → "BioQL Assistant"
   Debe mostrar: "Calling Autonomous Agent..."
```

### "Error: API key required"
```
1. Settings → bioql.apiKey
2. Valor: "bioql_test_870ce7ae"
3. Reload window
```

### "Timeout or no response"
```
1. Verifica internet
2. Check Modal status:
   python3 verify_modal_deployment.py
3. Aumenta timeout en extension (default: 180s)
```

### "Changes no se aplican"
```
1. ¿Hiciste click en "✅ Apply Changes"?
2. ¿Confirmaste en el dialog?
3. Check Output Channel para errores
```

---

## 📊 Ver Logs Detallados

**Output Channel:**
```
View → Output → "BioQL Assistant"
```

**Verás:**
```
🤖 Calling Autonomous Agent...
   Action: fix_and_apply
   File: /tmp/test_agent.py

💰 Autonomous Agent Cost:
   User Cost: $0.027875
   Time: 65.162s
   Changes: 3 lines

✅ Autonomous agent fixes applied to: /tmp/test_agent.py
```

---

## ✅ Checklist de Verificación

Antes de usar, verifica que tienes:

- [ ] VSCode 1.90+
- [ ] Extension v3.4.0 instalada
- [ ] `bioql.apiKey` configurado
- [ ] `bioql.enableChat` = true
- [ ] Chat abierto en VSCode
- [ ] @bioql aparece como opción
- [ ] Internet funcionando
- [ ] Modal endpoints activos

---

## 🎯 Keywords Que Activan Autonomous Agent

### ✅ Fix and Apply
```
@bioql fix and apply
@bioql fix this code automatically
@bioql apply fixes
```

### ✅ Improve Code
```
@bioql improve code
@bioql improve this code quality
```

### ✅ Refactor
```
@bioql refactor
@bioql refactor for performance
@bioql refactor for security
```

### ❌ NO Activan Autonomous (usan Simple Agent)
```
@bioql review this code
@bioql create a Bell state
@bioql explain this code
```

---

## 🎉 Si Todo Funciona

Verás:
1. ✅ Chat responde con "🤖 Autonomous agent..."
2. ✅ Muestra issues encontrados
3. ✅ Muestra diff de cambios
4. ✅ Muestra código fixed
5. ✅ Botón "Apply Changes" aparece
6. ✅ Click → Código se actualiza
7. ✅ Archivo se guarda automáticamente

---

## 📞 Si Necesitas Ayuda

1. **Check logs**:
   ```bash
   View → Output → "BioQL Assistant"
   ```

2. **Verifica Modal**:
   ```bash
   python3 verify_modal_deployment.py
   ```

3. **Test endpoint directo**:
   ```bash
   python3 test_autonomous_agent.py
   ```

---

## 🚀 Quick Start (TL;DR)

```bash
# 1. Instalar
code --install-extension /Users/heinzjungbluth/Desktop/bioql/vscode-extension/bioql-assistant-3.4.0.vsix

# 2. Configurar (en VSCode settings)
# bioql.apiKey: "bioql_test_870ce7ae"

# 3. Crear test file
echo 'print "hello"' > /tmp/test.py

# 4. Abrir en VSCode
code /tmp/test.py

# 5. En chat de VSCode
@bioql fix and apply

# 6. Click "✅ Apply Changes"
# ✅ Done!
```

---

## 📚 Documentación

- **Uso:** `docs/AUTONOMOUS_AGENT.md`
- **Deploy:** `MODAL_DEPLOYMENT_STATUS.md`
- **Tests:** `test_autonomous_agent.py`
- **Verify:** `verify_modal_deployment.py`

🎉 ¡Listo para usar el agente autónomo!
