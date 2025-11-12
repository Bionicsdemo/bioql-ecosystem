#!/bin/bash

# ============================================================================
# BioQL Assistant v7.0.0 - Instalación Rápida
# ============================================================================

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "🚀 BioQL Assistant v7.0.0 - Instalación Rápida"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Variables
VSIX_PATH="/Users/heinzjungbluth/Desktop/bioql-assistant-7.0.0.vsix"
WINDSURF_CLI="/Users/heinzjungbluth/.codeium/windsurf/bin/windsurf"
VSCODE_CLI="code"

# Verificar que el VSIX existe
if [ ! -f "$VSIX_PATH" ]; then
    echo "❌ Error: VSIX no encontrado en $VSIX_PATH"
    exit 1
fi

echo "✅ VSIX encontrado: bioql-assistant-7.0.0.vsix (2.4 MB)"
echo ""

# Detectar editor disponible
echo "🔍 Detectando editores disponibles..."
echo ""

HAS_WINDSURF=false
HAS_VSCODE=false

if [ -f "$WINDSURF_CLI" ]; then
    echo "✅ Windsurf CLI encontrado"
    HAS_WINDSURF=true
fi

if command -v code &> /dev/null; then
    echo "✅ VSCode CLI encontrado"
    HAS_VSCODE=true
fi

if [ "$HAS_WINDSURF" = false ] && [ "$HAS_VSCODE" = false ]; then
    echo "❌ Error: Ni Windsurf ni VSCode CLI encontrados"
    echo ""
    echo "📝 Instalación manual:"
    echo "   1. Abrir Windsurf o VSCode"
    echo "   2. View → Extensions"
    echo "   3. Click '...' → Install from VSIX"
    echo "   4. Seleccionar: $VSIX_PATH"
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo "Selecciona donde instalar:"
echo "─────────────────────────────────────────────────────────────────────"
echo ""

if [ "$HAS_WINDSURF" = true ]; then
    echo "[1] Windsurf (Recomendado)"
fi

if [ "$HAS_VSCODE" = true ]; then
    echo "[2] VSCode"
fi

echo "[3] Ambos"
echo "[0] Cancelar"
echo ""
read -p "Opción: " choice

echo ""

case $choice in
    1)
        if [ "$HAS_WINDSURF" = true ]; then
            echo "📦 Instalando en Windsurf..."
            "$WINDSURF_CLI" --install-extension "$VSIX_PATH"

            if [ $? -eq 0 ]; then
                echo ""
                echo "✅ ¡Instalación exitosa en Windsurf!"
                echo ""
                echo "🔄 Próximo paso: Reload Window en Windsurf"
                echo "   Cmd+Shift+P → 'Developer: Reload Window'"
            else
                echo ""
                echo "❌ Error durante la instalación"
            fi
        else
            echo "❌ Windsurf no está disponible"
        fi
        ;;
    2)
        if [ "$HAS_VSCODE" = true ]; then
            echo "📦 Instalando en VSCode..."
            code --install-extension "$VSIX_PATH"

            if [ $? -eq 0 ]; then
                echo ""
                echo "✅ ¡Instalación exitosa en VSCode!"
                echo ""
                echo "🔄 Próximo paso: Reload Window en VSCode"
                echo "   Cmd+Shift+P → 'Developer: Reload Window'"
            else
                echo ""
                echo "❌ Error durante la instalación"
            fi
        else
            echo "❌ VSCode no está disponible"
        fi
        ;;
    3)
        echo "📦 Instalando en ambos editores..."
        echo ""

        if [ "$HAS_WINDSURF" = true ]; then
            echo "→ Windsurf..."
            "$WINDSURF_CLI" --install-extension "$VSIX_PATH"
            echo ""
        fi

        if [ "$HAS_VSCODE" = true ]; then
            echo "→ VSCode..."
            code --install-extension "$VSIX_PATH"
            echo ""
        fi

        echo "✅ ¡Instalación completa!"
        echo ""
        echo "🔄 Próximo paso: Reload Window en cada editor"
        ;;
    0)
        echo "❌ Instalación cancelada"
        exit 0
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo "✅ Verificación"
echo "─────────────────────────────────────────────────────────────────────"
echo ""

if [ "$HAS_WINDSURF" = true ] && ([ "$choice" = "1" ] || [ "$choice" = "3" ]); then
    echo "📋 Extensiones instaladas en Windsurf:"
    "$WINDSURF_CLI" --list-extensions | grep -i bioql || echo "   (ejecuta después de reload)"
    echo ""
fi

if [ "$HAS_VSCODE" = true ] && ([ "$choice" = "2" ] || [ "$choice" = "3" ]); then
    echo "📋 Extensiones instaladas en VSCode:"
    code --list-extensions | grep -i bioql || echo "   (ejecuta después de reload)"
    echo ""
fi

echo "─────────────────────────────────────────────────────────────────────"
echo "📚 Próximos pasos"
echo "─────────────────────────────────────────────────────────────────────"
echo ""
echo "1. 🔄 Reload Window (Cmd+Shift+P → 'Developer: Reload Window')"
echo "2. ✅ Verificar instalación:"
echo "   - Extensions → Buscar 'BioQL'"
echo "   - Versión: 7.0.0"
echo ""
echo "3. 🧪 Probar funcionalidad:"
echo "   - Chat: @bioql run quillow surface code with distance 5"
echo "   - Snippet: bioql-quillow-basic [TAB]"
echo "   - Command: Cmd+Shift+P → 'BioQL: Run Quillow QEC Simulation'"
echo ""
echo "4. 📖 Leer documentación:"
echo "   - INSTALL_BIOQL_7.0.0.md (guía de instalación)"
echo "   - RELEASE_NOTES_v7.0.0.md (nuevas características)"
echo "   - BIOQL_QUILLOW_INTEGRATION_COMPLETE.md (documentación completa)"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "🎉 ¡Instalación de BioQL Assistant v7.0.0 completada!"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "🛡️  Nuevas características Quillow QEC disponibles:"
echo "   - Surface codes (d=3, 5, 7, 9)"
echo "   - Below-threshold operation"
echo "   - Real-time MWPM decoding"
echo "   - Multi-backend support (Stim, BioQL, IBM, IonQ)"
echo "   - 8 snippets nuevos"
echo "   - 4 comandos nuevos"
echo ""
echo "📞 Soporte:"
echo "   - GitHub: https://github.com/anthropics/claude-code/issues"
echo "   - Email: support@bioql.bio"
echo ""
