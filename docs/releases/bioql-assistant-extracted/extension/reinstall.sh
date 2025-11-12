#!/bin/bash
# Reinstall BioQL VSCode Extension
# ==================================

echo "🔄 Reinstalling BioQL VSCode Extension..."
echo ""

# 1. Uninstall old version
echo "1. Uninstalling old version..."
code --uninstall-extension SpectrixRD.bioql-assistant 2>/dev/null || true

# 2. Build new VSIX
echo ""
echo "2. Building new VSIX..."
npx vsce package --no-dependencies

# 3. Get latest VSIX file
VSIX_FILE=$(ls -t *.vsix | head -1)

if [ -z "$VSIX_FILE" ]; then
    echo "❌ No VSIX file found!"
    exit 1
fi

echo "   📦 Built: $VSIX_FILE"

# 4. Install
echo ""
echo "3. Installing extension..."
code --install-extension "$VSIX_FILE" --force

# 5. Verify
echo ""
echo "4. Verifying installation..."
if code --list-extensions | grep -q "spectrixrd.bioql-assistant"; then
    echo "✅ Extension installed successfully!"
    echo ""
    echo "📝 Please reload VSCode to activate:"
    echo "   Cmd+Shift+P → 'Developer: Reload Window'"
else
    echo "❌ Installation verification failed"
    exit 1
fi

echo ""
echo "🎉 Done! Extension ready to use with @bioql in chat"
