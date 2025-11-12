#!/bin/bash
# BioQL Ecosystem - Solución Completa
# Fecha: 27 de Enero, 2025
# Descripción: Script para resolver todos los issues pendientes

echo "========================================"
echo "BioQL Ecosystem - Instalación Completa"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Instalar Quillow dependencies
echo -e "${YELLOW}[1/4] Instalando dependencias de Quillow...${NC}"
cd ~/Desktop/Spectrix_BioQL/Quillow
pip3 install -r requirements.txt --user

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencias de Quillow instaladas${NC}"
else
    echo -e "${RED}❌ Error instalando dependencias de Quillow${NC}"
fi
echo ""

# 2. Instalar Quillow en modo editable
echo -e "${YELLOW}[2/4] Instalando Quillow (modo editable)...${NC}"
pip3 install -e . --user

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Quillow instalado${NC}"
else
    echo -e "${RED}❌ Error instalando Quillow${NC}"
fi
echo ""

# 3. Verificar Quillow
echo -e "${YELLOW}[3/4] Verificando Quillow...${NC}"
python3 -c "import quillow; print('✅ Quillow OK')" 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Quillow funciona correctamente${NC}"
else
    echo -e "${RED}❌ Quillow tiene problemas de importación${NC}"
fi
echo ""

# 4. Inicializar Git en Quantum_graph
echo -e "${YELLOW}[4/4] Inicializando Git en Quantum_graph...${NC}"
cd ~/Desktop/Spectrix_BioQL/Quantum_graph

if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit: Quantum_graph quantum computing service"
    echo -e "${GREEN}✅ Git inicializado en Quantum_graph${NC}"
else
    echo -e "${YELLOW}⚠️  Git ya estaba inicializado${NC}"
fi
echo ""

# 5. Verificar instalación de bioql_quillow_docking
echo -e "${YELLOW}[5/5] Verificando bioql_quillow_docking...${NC}"
cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking
python3 test_installation.py

echo ""
echo "========================================"
echo "Resumen de Instalación"
echo "========================================"
echo ""
echo "Verificando todos los componentes:"
echo ""

# BioQL
python3 -c "import bioql; print('✅ BioQL OK')" 2>&1 | grep -q "✅" && echo -e "${GREEN}✅ BioQL Framework${NC}" || echo -e "${RED}❌ BioQL Framework${NC}"

# Quillow
python3 -c "import quillow; print('✅ Quillow OK')" 2>&1 | grep -q "✅" && echo -e "${GREEN}✅ Quillow QEC${NC}" || echo -e "${RED}❌ Quillow QEC${NC}"

# Stim
python3 -c "import stim; print('✅ Stim OK')" 2>&1 | grep -q "✅" && echo -e "${GREEN}✅ Stim Backend${NC}" || echo -e "${RED}❌ Stim Backend${NC}"

# Git Quantum_graph
cd ~/Desktop/Spectrix_BioQL/Quantum_graph
if [ -d .git ]; then
    echo -e "${GREEN}✅ Quantum_graph (Git)${NC}"
else
    echo -e "${RED}❌ Quantum_graph (Git)${NC}"
fi

echo ""
echo "========================================"
echo "Instalación completa!"
echo "========================================"
echo ""
echo "Próximos pasos:"
echo "1. Configurar API key: export BIOQL_API_KEY='tu_key'"
echo "2. Ejecutar ejemplo: cd ~/Desktop/Spectrix_BioQL/bioql_quillow_docking"
echo "3. Ejecutar: python3 src/cli.py --smiles 'CCO' --pdb 6B3J --shots 1000"
echo ""
