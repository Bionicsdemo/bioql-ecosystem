# Comandos Rápidos para BioQL Ecosystem

**Fecha:** 27 de Enero, 2025

---

## ⚠️ Importante: Comillas en zsh

En zsh, los operadores de comparación (`>=`) necesitan comillas:

### ❌ Incorrecto
```bash
pip install stim>=1.12.0
# Error: zsh: 1.12.0 not found
```

### ✅ Correcto
```bash
pip install 'stim>=1.12.0'
# O también:
pip3 install 'stim>=1.12.0' 'networkx>=2.8.0' 'scipy>=1.9.0'
```

---

## 🔧 Instalación de Dependencias

### 1. Quillow QEC Framework
```bash
cd ~/Desktop/Spectrix_BioQL/Quillow
pip3 install 'stim>=1.12.0' 'networkx>=2.8.0' 'scipy>=1.9.0'
pip3 install -e .
```

### 2. BioQL Quillow Docking
```bash
cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking
pip3 install -r requirements.txt
```

### 3. Verificar Instalaciones
```bash
# BioQL
python3 -c "import bioql; print(f'BioQL {bioql.__version__ if hasattr(bioql, \"__version__\") else \"OK\"}')"

# Quillow
python3 -c "import quillow; print('Quillow OK')"

# Test completo
cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking
python3 test_installation.py
```

---

## 🚀 Uso Rápido - bioql_quillow_docking

### Comando Básico (Sin QEC)
```bash
cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking

python3 src/cli.py \
  --smiles "CCO" \
  --pdb 6B3J \
  --shots 1000
```

### Con QEC (Distance 5)
```bash
python3 src/cli.py \
  --smiles "CC(=O)Oc1ccccc1C(=O)O" \
  --pdb 6B3J \
  --shots 2000 \
  --qec on \
  --qec-distance 5
```

### Usando Archivo de Configuración
```bash
python3 src/cli.py --config examples/aspirin_6B3J.json
```

### Ver Ayuda
```bash
python3 src/cli.py --help
python3 src/cli.py example
python3 src/cli.py version
```

---

## 🔑 Configurar API Key

### Opción 1: Variable de entorno (recomendado)
```bash
export BIOQL_API_KEY="tu_api_key_aqui"

# Para hacerlo permanente, agregar a ~/.zshrc:
echo 'export BIOQL_API_KEY="tu_api_key"' >> ~/.zshrc
source ~/.zshrc
```

### Opción 2: En el comando
```bash
python3 src/cli.py \
  --smiles "CCO" \
  --pdb 6B3J \
  --api-key "tu_api_key_aqui"
```

### Opción 3: Archivo .env
```bash
cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking
echo "BIOQL_API_KEY=tu_api_key" > .env
```

---

## 📁 Git - Quantum_graph

### Inicializar repositorio
```bash
cd ~/Desktop/Spectrix_BioQL/Quantum_graph
git init
git add .
git commit -m "Initial commit: Quantum_graph quantum computing service"
```

### Conectar a remoto (opcional)
```bash
git remote add origin https://github.com/tu_usuario/quantum_graph.git
git branch -M main
git push -u origin main
```

---

## 🧪 Tests Rápidos

### Test de instalación completo
```bash
cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking
python3 test_installation.py
```

### Test individual de módulos
```bash
# Config
python3 -c "from src.config import create_default_config; print(create_default_config('CCO', '6B3J'))"

# QEC
python3 -c "from src.qec import QECManager, QECConfig; print(QECManager(QECConfig()).resources)"

# QuantumResult
python3 -c "from src.docking import QuantumResult; print('QuantumResult OK')"
```

---

## 📊 Ver Resultados

### Listar experimentos
```bash
cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking
ls -lh docking_output/
```

### Ver última figura generada
```bash
open docking_output/*.png
```

### Ver último resultado JSON
```bash
cat docking_output/*_data.json | python3 -m json.tool
```

### Ver logs
```bash
tail -f docking_output/*.log
```

---

## 🔍 Diagnóstico

### Verificar estado de todos los componentes
```bash
cd ~/Desktop/Spectrix_BioQL

# BioQL
python3 -c "import bioql; print(f'✅ BioQL {bioql.__version__ if hasattr(bioql, \"__version__\") else \"OK\"}')" 2>&1 | grep -E "✅|Error"

# Quillow
python3 -c "import quillow; print('✅ Quillow OK')" 2>&1 | grep -E "✅|Error"

# Stim
python3 -c "import stim; print('✅ Stim OK')" 2>&1 | grep -E "✅|Error"

# NetworkX
python3 -c "import networkx; print('✅ NetworkX OK')" 2>&1 | grep -E "✅|Error"

# Scipy
python3 -c "import scipy; print('✅ Scipy OK')" 2>&1 | grep -E "✅|Error"
```

### Ver versiones instaladas
```bash
pip3 list | grep -E "bioql|quillow|stim|networkx|scipy|numpy|matplotlib"
```

---

## 📦 Instalación Completa desde Cero

### Script de instalación completa
```bash
#!/bin/bash
cd ~/Desktop/Spectrix_BioQL

# 1. Dependencias base
pip3 install 'numpy>=1.21.0' 'matplotlib>=3.5.0' 'scipy>=1.9.0'

# 2. QEC dependencies
pip3 install 'stim>=1.12.0' 'networkx>=2.8.0'

# 3. CLI dependencies
pip3 install 'typer>=0.9.0' 'rich>=13.0.0'

# 4. Química (opcional)
pip3 install 'rdkit>=2022.9.1'

# 5. BioQL Framework
cd Spectrix_framework
pip3 install -e .

# 6. Quillow
cd ../Quillow
pip3 install -e .

# 7. bioql_quillow_docking
cd ../bioql_quillow_docking
pip3 install -r requirements.txt

# 8. Verificar
python3 test_installation.py
```

---

## 🆘 Solución de Problemas Comunes

### Error: "zsh: not found"
**Causa:** Falta comillas en comando con `>=`
**Solución:** Usar comillas: `pip3 install 'stim>=1.12.0'`

### Error: "No module named 'bioql'"
**Solución:**
```bash
export PYTHONPATH="$HOME/Desktop/Spectrix_BioQL/Spectrix_framework:$PYTHONPATH"
```

### Error: "No module named 'quillow'"
**Solución:**
```bash
cd ~/Desktop/Spectrix_BioQL/Quillow
pip3 install -e .
```

### Error: "BIOQL_API_KEY required"
**Solución:**
```bash
export BIOQL_API_KEY="tu_api_key"
```

### Error: "No module named 'stim'"
**Solución:**
```bash
pip3 install 'stim>=1.12.0'
```

---

## 🔗 Recursos

- **Documentación completa:** `~/Desktop/Spectrix_BioQL/bioql_quillow_docking/README.md`
- **Quick Start:** `~/Desktop/Spectrix_BioQL/bioql_quillow_docking/QUICKSTART.md`
- **Status Report:** `~/Desktop/Spectrix_BioQL/SYSTEM_STATUS_REPORT.md`
- **Ejemplos:** `~/Desktop/Spectrix_BioQL/bioql_quillow_docking/examples/`

---

## 📝 Aliases Útiles (agregar a ~/.zshrc)

```bash
# Alias para BioQL
alias bioql-dock='cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking && python3 src/cli.py'
alias bioql-test='cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking && python3 test_installation.py'
alias bioql-results='open ~/Desktop/Spectrix_BioQL/bioql_quillow_docking/docking_output/'

# Aplicar cambios
source ~/.zshrc
```

**Uso:**
```bash
bioql-dock --smiles "CCO" --pdb 6B3J --shots 1000
bioql-test
bioql-results
```

---

**Última actualización:** 27 de Enero, 2025
**Sistema:** macOS con zsh
