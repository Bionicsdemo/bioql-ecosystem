#!/bin/bash

# BioQL v4.0.0 - Instalación Manual Simple
# ==========================================

echo "🚀 BioQL v4.0.0 - Instalación Manual"
echo "===================================="
echo ""

VSIX_FILE="bioql-assistant-4.0.0.vsix"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -f "$SCRIPT_DIR/$VSIX_FILE" ]; then
    echo "❌ ERROR: $VSIX_FILE no encontrado"
    exit 1
fi

echo "📦 Archivo VSIX encontrado: $VSIX_FILE"
echo ""
echo "════════════════════════════════════════"
echo "📋 INSTRUCCIONES DE INSTALACIÓN MANUAL"
echo "════════════════════════════════════════"
echo ""
echo "Por favor sigue estos pasos:"
echo ""
echo "1️⃣  CIERRA completamente tu editor (VS Code/Cursor/Windsurf)"
echo "   - Presiona Cmd + Q (NO solo cerrar la ventana)"
echo "   - Espera 5 segundos"
echo ""
echo "2️⃣  ABRE tu editor nuevamente"
echo ""
echo "3️⃣  Instala la extensión desde la UI:"
echo "   - Presiona: Cmd + Shift + P"
echo "   - Escribe: 'Extensions: Install from VSIX'"
echo "   - Selecciona este archivo:"
echo "     $SCRIPT_DIR/$VSIX_FILE"
echo ""
echo "4️⃣  RECARGA la ventana:"
echo "   - Presiona: Cmd + Shift + P"
echo "   - Escribe: 'Reload Window'"
echo ""
echo "5️⃣  CONFIGURA tu API key:"
echo "   - Presiona: Cmd + ,"
echo "   - Busca: 'bioql.apiKey'"
echo "   - Pega: __BIOQL_REDACTED__"
echo ""
echo "6️⃣  PRUEBA la extensión:"
echo "   - Abre el Chat"
echo "   - Escribe: @bioql dock metformin to AMPK"
echo "   - El agente te hará preguntas interactivas ✅"
echo ""
echo "════════════════════════════════════════"
echo ""
echo "💡 TIP: Si ves 'context is not defined', recarga la ventana"
echo ""
echo "🔗 Ruta completa del VSIX:"
echo "   $SCRIPT_DIR/$VSIX_FILE"
echo ""
