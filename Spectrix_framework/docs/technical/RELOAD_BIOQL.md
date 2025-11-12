# 🔄 RECARGAR BIOQL ASSISTANT v4.9.8

## ✅ PASOS PARA ACTIVAR:

### 1️⃣ **Cerrar Cursor COMPLETAMENTE**
```bash
# Matar todos los procesos de Cursor
pkill -9 Cursor
sleep 2
```

### 2️⃣ **Abrir Cursor de nuevo**
```bash
open -a Cursor
```

### 3️⃣ **Verificar extensión cargada**
En Cursor, presiona:
- `Cmd+Shift+P` → "Developer: Show Running Extensions"
- Busca "bioql-assistant" en la lista
- Debe aparecer como **ACTIVADA** ✅

### 4️⃣ **Probar @bioql en chat**
En el panel de chat de Cursor:
```
@bioql Design a drug for diabetes targeting GLP1R
```

---

## 🔍 SI NO FUNCIONA:

### Verificar logs de extensión:
1. `Cmd+Shift+P` → "Developer: Toggle Developer Tools"
2. Ve a la pestaña "Console"
3. Busca errores relacionados con "bioql"

### Reinstalar extensión:
```bash
cd /Users/heinzjungbluth/Desktop/Server_bioql/vscode_extension/bioql-assistant
/Applications/Cursor.app/Contents/Resources/app/bin/code --uninstall-extension SpectrixRD.bioql-assistant
/Applications/Cursor.app/Contents/Resources/app/bin/code --install-extension bioql-assistant-4.9.8.vsix --force
```

### Verificar configuración:
En Cursor Settings (Cmd+,):
- Busca "BioQL"
- Verifica que `bioql.enableChat` = ✅ true
- Verifica que `bioql.mode` = "modal"
- Verifica que `bioql.modalUrl` = "https://spectrix--bioql-agent-create-fastapi-app.modal.run"

---

## 📊 FEATURES DISPONIBLES EN v4.9.8:

✅ **Pharmaceutical Scoring**
- Lipinski Rule of 5
- QED Score (drug-likeness)
- SA Score (synthetic accessibility)  
- PAINS detection

✅ **Auto SMILES Neutralization**
- Detecta átomos cargados (N+, O-)
- Neutraliza automáticamente

✅ **Production Drug Design**
- Binding affinity (Ki/IC50)
- Provenance tracking
- Artifact management

✅ **CRISPR-QAI**
- Guide design
- Off-target analysis
- Clinical therapy design

---

## 🚀 QUICK TEST:

```python
from bioql import quantum

result = quantum(
    "Dock aspirin to COX2 receptor with pharmaceutical scoring",
    backend='simulator',
    shots=100
)

print(f"Binding Affinity: {result.binding_affinity} kcal/mol")
print(f"Lipinski: {result.lipinski_compliant}")
print(f"QED Score: {result.qed_score}")
```
