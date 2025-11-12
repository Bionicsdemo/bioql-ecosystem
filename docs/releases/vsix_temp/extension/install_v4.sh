#!/bin/bash

# BioQL Code Assistant v4.0.0 - Quick Install Script
# ===================================================

echo "🚀 BioQL Code Assistant v4.0.0 Installer"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if VS Code is installed
if ! command -v code &> /dev/null; then
    echo -e "${RED}❌ VS Code CLI not found${NC}"
    echo "Please install VS Code or add 'code' to your PATH"
    echo ""
    echo "To add 'code' to PATH:"
    echo "1. Open VS Code"
    echo "2. Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)"
    echo "3. Type 'Shell Command: Install code command in PATH'"
    exit 1
fi

echo -e "${GREEN}✅ VS Code CLI found${NC}"
echo ""

# Check if VSIX file exists
VSIX_FILE="bioql-assistant-4.0.0.vsix"

if [ ! -f "$VSIX_FILE" ]; then
    echo -e "${RED}❌ $VSIX_FILE not found${NC}"
    echo "Please run this script from the extension directory"
    exit 1
fi

echo -e "${GREEN}✅ Found $VSIX_FILE (860 KB)${NC}"
echo ""

# Uninstall previous version
echo -e "${BLUE}🔄 Checking for previous versions...${NC}"
EXISTING=$(code --list-extensions | grep -i bioql-assistant || true)

if [ ! -z "$EXISTING" ]; then
    echo -e "${YELLOW}⚠️  Found existing version: $EXISTING${NC}"
    read -p "Uninstall previous version? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🗑️  Uninstalling previous version...${NC}"
        code --uninstall-extension spectrixrd.bioql-assistant
        echo -e "${GREEN}✅ Previous version uninstalled${NC}"
    fi
else
    echo -e "${GREEN}✅ No previous version found${NC}"
fi
echo ""

# Install new version
echo -e "${BLUE}📦 Installing BioQL Code Assistant v4.0.0...${NC}"
code --install-extension "$VSIX_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Installation successful!${NC}"
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo -e "${GREEN}🎉 BioQL Code Assistant v4.0.0 Installed!${NC}"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "📋 Next Steps:"
    echo ""
    echo "1. 🔑 Set your API key:"
    echo "   - Open VS Code Settings (Cmd+,)"
    echo "   - Search for 'BioQL'"
    echo "   - Set 'bioql.apiKey' to your API key"
    echo ""
    echo "2. 🎯 Try it out:"
    echo "   - Press Cmd+Shift+G (Mac) or Ctrl+Shift+G (Windows)"
    echo "   - Type: 'create a bell state'"
    echo "   - Agent will ask for parameters interactively!"
    echo ""
    echo "3. 💬 Use Chat:"
    echo "   - Open VS Code Chat"
    echo "   - Type: '@bioql create a ghz state with 3 qubits'"
    echo ""
    echo "📊 New in v4.0.0:"
    echo "  ✅ Interactive parameter collection"
    echo "  ✅ Automatic Qualtran visualizations"
    echo "  ✅ QEC support (Surface, Steane, Shor)"
    echo "  ✅ Multi-backend (AWS, IBM, IonQ)"
    echo ""
    echo "📚 Resources:"
    echo "  - README: readme.md"
    echo "  - Release Notes: RELEASE_NOTES_v4.0.0.md"
    echo "  - Documentation: https://docs.bioql.com"
    echo ""
    echo -e "${YELLOW}💡 Tip: Reload VS Code window to activate all features${NC}"
    echo "   (Cmd+Shift+P → 'Reload Window')"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Installation failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Close VS Code completely"
    echo "2. Try manual installation:"
    echo "   - Open VS Code"
    echo "   - Cmd+Shift+P → 'Extensions: Install from VSIX'"
    echo "   - Select bioql-assistant-4.0.0.vsix"
    echo ""
    exit 1
fi

echo "═══════════════════════════════════════════════════════"
echo ""
