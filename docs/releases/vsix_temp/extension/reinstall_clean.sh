#!/bin/bash

# BioQL v4.0.0 - Clean Reinstall Script
# =======================================

echo "🚀 BioQL v4.0.0 - Reinstalación Limpia"
echo "======================================"
echo ""

# Step 1: Check if Cursor is running
echo "1️⃣  Verificando si Cursor está cerrado..."
if pgrep -x "Cursor" > /dev/null; then
    echo "❌ ERROR: Cursor está corriendo"
    echo ""
    echo "Por favor:"
    echo "  1. Cierra Cursor completamente (Cmd + Q)"
    echo "  2. Ejecuta este script nuevamente"
    echo ""
    exit 1
fi

echo "✅ Cursor está cerrado"
echo ""

# Step 2: Clean cache
echo "2️⃣  Limpiando caché..."
rm -rf "$HOME/Library/Application Support/Cursor/Cache"
rm -rf "$HOME/Library/Application Support/Cursor/CachedData"
rm -rf "$HOME/Library/Application Support/Cursor/CachedExtensionVSIXs"
rm -rf "$HOME/Library/Application Support/Cursor/Code Cache"
echo "✅ Caché eliminado"
echo ""

# Step 3: Remove old extension
echo "3️⃣  Eliminando extensión anterior..."
rm -rf "$HOME/.cursor/extensions/spectrixrd.bioql-assistant"*
echo "✅ Extensión anterior eliminada"
echo ""

# Step 4: Install new extension
echo "4️⃣  Instalando BioQL v4.0.0..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
/Applications/Cursor.app/Contents/Resources/app/bin/code --install-extension "$SCRIPT_DIR/bioql-assistant-4.0.0.vsix" --force

if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════"
    echo "✅ INSTALACIÓN EXITOSA"
    echo "════════════════════════════════════════"
    echo ""
    echo "📋 Próximos pasos:"
    echo ""
    echo "1. Abre Cursor/VS Code"
    echo "2. Configura tu API key:"
    echo "   - Cmd+, (Abrir Settings)"
    echo "   - Buscar: 'bioql.apiKey'"
    echo "   - Pegar tu API key"
    echo ""
    echo "3. Prueba la extensión:"
    echo "   - Abre el Chat"
    echo "   - Escribe: @bioql dock metformin to AMPK"
    echo ""
    echo "4. El agente te hará preguntas interactivas:"
    echo "   - ¿Qué backend? (aws/ibm/ionq/simulator)"
    echo "   - ¿QEC? (surface_code/steane/shor/none)"
    echo "   - ¿Cuántos shots? (1000 recomendado)"
    echo "   - ¿Hardware o simulador?"
    echo ""
    echo "5. Responde naturalmente, por ejemplo:"
    echo "   'AWS Braket simulator con 1000 shots y surface code QEC'"
    echo ""
    echo "════════════════════════════════════════"
    echo ""
else
    echo ""
    echo "❌ ERROR en la instalación"
    echo ""
    echo "Por favor intenta instalación manual:"
    echo "1. Abre Cursor/VS Code"
    echo "2. Cmd+Shift+P"
    echo "3. 'Extensions: Install from VSIX'"
    echo "4. Selecciona: bioql-assistant-4.0.0.vsix"
    echo ""
    exit 1
fi
