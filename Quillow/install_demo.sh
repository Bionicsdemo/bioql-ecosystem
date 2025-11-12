#!/bin/bash
# Script de instalación rápida para demos de Quillow

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║           🔬 INSTALANDO DEPENDENCIAS PARA QUILLOW                ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

echo "📦 Instalando dependencias necesarias..."
echo ""

# Instalar dependencias core
pip install stim pymatching numpy scipy matplotlib networkx loguru pydantic requests rich

echo ""
echo "✅ Instalación completa!"
echo ""
echo "🚀 Ahora puedes ejecutar:"
echo "   python demo_bioql.py"
echo "   python demo_script.py"
echo ""
