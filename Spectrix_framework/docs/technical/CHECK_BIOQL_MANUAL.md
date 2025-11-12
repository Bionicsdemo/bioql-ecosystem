# 🔍 VERIFICAR BIOQL EXTENSION - MANUAL

Ya que el comando `code` no está disponible, vamos a verificar todo manualmente en VSCode.

---

## ✅ PASO 1: VERIFICAR QUE LA EXTENSIÓN ESTÁ INSTALADA

### En VSCode:

1. Presiona `Cmd+Shift+X` (Panel de Extensions)
2. En el cuadro de búsqueda, escribe: **bioql**
3. **¿Aparece "BioQL Code Assistant"?**

   - ✅ **SI:** Continúa al PASO 2
   - ❌ **NO:** Instala la extensión primero:
     - Click en `...` (tres puntos arriba)
     - "Install from VSIX..."
     - Selecciona: `/Users/heinzjungbluth/Desktop/Server_bioql/vscode_extension/bioql-assistant/bioql-assistant-4.9.9.vsix`

---

## ✅ PASO 2: VERIFICAR QUE ESTÁ ACTIVADA

### En el panel de Extensions:

- Busca "BioQL Code Assistant"
- **¿Dice "Disable" o "Uninstall"?**
  - ✅ **SI:** La extensión está instalada y habilitada
  - ❌ **NO (dice "Enable"):** Click en "Enable" primero

---

## ✅ PASO 3: RECARGAR VSCODE

**IMPORTANTE:** Después de instalar/habilitar:

```
Cmd+Shift+P → Developer: Reload Window
```

O simplemente cierra y abre VSCode de nuevo.

---

## ✅ PASO 4: VER DEVELOPER CONSOLE

### Para ver errores de activación:

1. **Abrir Developer Tools:**
   ```
   Cmd+Shift+P → Developer: Toggle Developer Tools
   ```

2. **Ve a la pestaña "Console"**

3. **Busca errores relacionados con:**
   - "bioql"
   - "extension"
   - "activation failed"

4. **Copia cualquier error que veas aquí** ⬇️

---

## ✅ PASO 5: VER EXTENSIONES EN EJECUCIÓN

```
Cmd+Shift+P → Developer: Show Running Extensions
```

### Busca "bioql-assistant" en la lista:

- ✅ **Aparece con estado "Activated":** La extensión está corriendo
- ⚠️ **Aparece con estado "Activating...":** Está intentando activarse (espera 10 segundos)
- ❌ **No aparece:** La extensión no está instalada o no se está cargando

---

## ✅ PASO 6: VERIFICAR OUTPUT CHANNEL

1. **Abrir Output panel:**
   ```
   Cmd+Shift+U (o View → Output)
   ```

2. **En el dropdown de arriba, busca "BioQL Assistant"**

   - ✅ **Aparece en la lista:** La extensión está activa
   - ❌ **No aparece:** La extensión NO se activó

3. **Si aparece, selecciónalo y verifica que dice:**
   ```
   🚀 BioQL Code Assistant activated!
   ✅ BioQL Chat enabled! Use @bioql in chat
   ✅ Chat participant registered: bioql.assistant
   ✅ BioQL Assistant ready!
   ```

---

## 🔧 SI LA EXTENSIÓN NO APARECE EN OUTPUT:

Esto significa que la extensión **NO SE ACTIVÓ**. Posibles causas:

### A) Falta node_modules (dependencias)

La extensión empaquetada NO incluye node_modules por defecto. Necesitas:

**Opción 1: Reinstalar con dependencias**

```bash
cd /Users/heinzjungbluth/Desktop/Server_bioql/vscode_extension/bioql-assistant
rm -rf node_modules package-lock.json
npm install
npx @vscode/vsce package --allow-missing-repository
```

Luego instalar el nuevo VSIX generado.

**Opción 2: Usar modo desarrollo**

En lugar de VSIX, ejecuta la extensión en modo desarrollo:

1. Abre VSCode
2. File → Open Folder
3. Selecciona: `/Users/heinzjungbluth/Desktop/Server_bioql/vscode_extension/bioql-assistant/`
4. Presiona `F5` (o Run → Start Debugging)
5. Se abrirá una nueva ventana de VSCode con la extensión cargada

### B) Error en extension.js

Verifica en Developer Console (PASO 4) si hay errores de JavaScript.

### C) Versión de VSCode muy antigua

Verifica tu versión:
```
VSCode → About Visual Studio Code
```

**Requisito:** >= 1.90.0 para Chat API

---

## 📝 REPORTE DE DIAGNÓSTICO

**Por favor completa y envía:**

1. ¿La extensión aparece en Extensions panel? (SI/NO): _____
2. ¿Dice "Disable" o "Enable"? _____
3. ¿Aparece en "Running Extensions"? (SI/NO): _____
4. ¿Aparece "BioQL Assistant" en Output dropdown? (SI/NO): _____
5. Versión de VSCode: _____
6. Errores en Console (copiar aquí):
   ```

   ```

---

## 🆘 ÚLTIMO RECURSO - INSTALACIÓN EN MODO DESARROLLO

Si la extensión empaquetada no funciona, instálala en modo desarrollo:

```bash
cd /Users/heinzjungbluth/Desktop/Server_bioql/vscode_extension/bioql-assistant

# 1. Instalar dependencias
npm install

# 2. Abrir en VSCode
code .

# 3. Presionar F5 para ejecutar en modo debug
```

Esto cargará la extensión directamente sin empaquetar.

---

## 📦 ARCHIVOS ACTUALES:

```
VSIX: bioql-assistant-4.9.9.vsix (50.41 KB)
Location: /Users/heinzjungbluth/Desktop/Server_bioql/vscode_extension/bioql-assistant/
Modal Agent: https://spectrix--bioql-agent-create-fastapi-app.modal.run
BioQL Version: 5.5.7
```
