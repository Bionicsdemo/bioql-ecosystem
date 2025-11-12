#!/bin/bash
# Build and verify Quillow package for PyPI distribution

set -e  # Exit on error

echo "🔨 Building Quillow Package for PyPI"
echo "======================================"
echo

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Check we're in the right directory
echo "📁 Checking directory..."
if [ ! -f "setup.py" ]; then
    echo -e "${RED}❌ Error: setup.py not found. Run from Quillow root directory.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ In Quillow directory${NC}"
echo

# 2. Check required files exist
echo "📋 Verifying required files..."
required_files=("setup.py" "pyproject.toml" "LICENSE" "README.md" "MANIFEST.in" "requirements.txt")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✅ $file${NC}"
    else
        echo -e "${RED}  ❌ Missing: $file${NC}"
        exit 1
    fi
done
echo

# 3. Check version consistency
echo "🔢 Checking version consistency..."
setup_version=$(grep "version=" setup.py | head -1 | sed "s/.*version='\(.*\)'.*/\1/")
pyproject_version=$(grep "^version = " pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ "$setup_version" = "$pyproject_version" ]; then
    echo -e "${GREEN}  ✅ Version: $setup_version${NC}"
else
    echo -e "${RED}  ❌ Version mismatch:${NC}"
    echo "     setup.py: $setup_version"
    echo "     pyproject.toml: $pyproject_version"
    exit 1
fi
VERSION=$setup_version
echo

# 4. Check no bioql dependency in install_requires
echo "🔍 Checking dependencies..."
if grep -A 20 "install_requires=" setup.py | grep -q "'bioql"; then
    echo -e "${RED}  ❌ Found 'bioql' in install_requires. Remove it!${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ No bioql in install_requires${NC}"
echo

# 5. Install build tools
echo "🛠️  Installing build tools..."
pip install --upgrade build twine wheel setuptools > /dev/null 2>&1
echo -e "${GREEN}  ✅ Build tools installed${NC}"
echo

# 6. Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info
echo -e "${GREEN}  ✅ Cleaned${NC}"
echo

# 7. Build the package
echo "📦 Building distribution..."
python -m build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ Build successful${NC}"
else
    echo -e "${RED}  ❌ Build failed${NC}"
    exit 1
fi
echo

# 8. Verify build outputs
echo "🔍 Verifying build outputs..."
if [ -f "dist/quillow-${VERSION}-py3-none-any.whl" ]; then
    echo -e "${GREEN}  ✅ Wheel: quillow-${VERSION}-py3-none-any.whl${NC}"
    whl_size=$(ls -lh "dist/quillow-${VERSION}-py3-none-any.whl" | awk '{print $5}')
    echo "     Size: $whl_size"
else
    echo -e "${RED}  ❌ Wheel not found${NC}"
    exit 1
fi

if [ -f "dist/quillow-${VERSION}.tar.gz" ]; then
    echo -e "${GREEN}  ✅ Source: quillow-${VERSION}.tar.gz${NC}"
    tar_size=$(ls -lh "dist/quillow-${VERSION}.tar.gz" | awk '{print $5}')
    echo "     Size: $tar_size"
else
    echo -e "${RED}  ❌ Source tarball not found${NC}"
    exit 1
fi
echo

# 9. Check package with twine
echo "✅ Running twine check..."
twine check dist/*
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ Twine check passed${NC}"
else
    echo -e "${RED}  ❌ Twine check failed${NC}"
    exit 1
fi
echo

# 10. Inspect package contents
echo "📋 Package contents:"
tar -tzf "dist/quillow-${VERSION}.tar.gz" | head -20
echo "     ... (showing first 20 files)"
echo

# 11. Summary
echo "════════════════════════════════════════════════"
echo -e "${GREEN}✅ Package built successfully!${NC}"
echo "════════════════════════════════════════════════"
echo
echo "📦 Distribution files:"
echo "   • dist/quillow-${VERSION}-py3-none-any.whl"
echo "   • dist/quillow-${VERSION}.tar.gz"
echo
echo "🚀 Next steps:"
echo
echo "   1️⃣  Test locally:"
echo "       pip install dist/quillow-${VERSION}-py3-none-any.whl"
echo
echo "   2️⃣  Upload to TestPyPI:"
echo "       twine upload --repository testpypi dist/*"
echo
echo "   3️⃣  Test from TestPyPI:"
echo "       pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ quillow"
echo
echo "   4️⃣  Upload to PyPI (production):"
echo "       twine upload dist/*"
echo
echo "   5️⃣  Install from PyPI:"
echo "       pip install quillow"
echo
echo "📖 For detailed instructions, see: PYPI_DEPLOYMENT.md"
echo
