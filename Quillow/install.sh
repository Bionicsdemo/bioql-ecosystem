#!/bin/bash
# Quillow Installation Script
# ===========================

set -e

echo "=================================="
echo "Quillow Installation"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo -e "${GREEN}✓ Python version OK${NC}"
else
    echo "❌ Python 3.9+ required"
    exit 1
fi

# Install dependencies
echo ""
echo -e "${BLUE}Installing dependencies...${NC}"
pip3 install -r requirements.txt

# Install Quillow
echo ""
echo -e "${BLUE}Installing Quillow...${NC}"
pip3 install -e .

# Verify installation
echo ""
echo -e "${BLUE}Verifying installation...${NC}"
if quillow info > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Quillow installed successfully${NC}"
else
    echo "❌ Installation verification failed"
    exit 1
fi

# Check for BioQL API key
echo ""
echo -e "${BLUE}Checking BioQL configuration...${NC}"
if [ -z "$BIOQL_API_KEY" ]; then
    echo "⚠️  BIOQL_API_KEY not set"
    echo "To use BioQL integration, set:"
    echo "  export BIOQL_API_KEY='your_key_here'"
else
    echo -e "${GREEN}✓ BioQL API key found${NC}"
fi

# Summary
echo ""
echo "=================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=================================="
echo ""
echo "Quick Start:"
echo "  quillow simulate -d 5 -s 10000"
echo "  quillow info"
echo ""
echo "BioQL Integration:"
echo "  export BIOQL_API_KEY='your_key'"
echo "  quillow protect-bioql --query 'test' --backend simulator"
echo ""
echo "Documentation:"
echo "  cat README.md"
echo "  cat FINAL_DEPLOYMENT_GUIDE.md"
echo ""
