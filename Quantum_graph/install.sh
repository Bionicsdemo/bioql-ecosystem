#!/bin/bash
# Quantum_graph Installation Script
# ==================================

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║         QUANTUM_GRAPH INSTALLATION                               ║"
echo "║         Quantum-Enhanced Scientific Visualization               ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python3 --version || { echo "❌ Python 3.9+ required"; exit 1; }

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install core dependencies
echo ""
echo "📥 Installing core dependencies..."
pip install numpy scipy matplotlib

# Install quantum computing libraries
echo ""
echo "⚛️  Installing quantum computing libraries..."
pip install qiskit qiskit-nature qiskit-aer cirq pennylane

# Install visualization libraries
echo ""
echo "🎨 Installing visualization libraries..."
pip install rdkit biopython networkx

# Install web framework
echo ""
echo "🌐 Installing FastAPI server..."
pip install fastapi uvicorn pydantic python-multipart

# Install from requirements.txt
echo ""
echo "📋 Installing remaining dependencies from requirements.txt..."
pip install -r requirements.txt

# Install BioQL from Spectrix framework (if available)
echo ""
echo "🔗 Checking for BioQL installation..."
if [ -d "../Spectrix_framework" ]; then
    echo "✅ Found Spectrix framework, installing BioQL..."
    pip install -e ../Spectrix_framework
else
    echo "⚠️  Spectrix framework not found at ../Spectrix_framework"
    echo "   BioQL integration will use mock mode"
fi

# Install Quantum_graph in development mode
echo ""
echo "🔧 Installing Quantum_graph..."
pip install -e .

# Create necessary directories
echo ""
echo "📁 Creating working directories..."
mkdir -p data/proteins
mkdir -p data/metabolites
mkdir -p data/outputs
mkdir -p logs
mkdir -p temp

# Set up configuration
echo ""
echo "⚙️  Setting up configuration..."
if [ ! -f "config.yaml" ]; then
    cat > config.yaml << 'EOF'
# Quantum_graph Configuration
# ===========================

quantum:
  default_backend: "auto"
  max_budget_usd: 1000.0
  max_time_hours: 48.0
  accuracy_target: 0.95

backends:
  ibm_quantum:
    api_token: ""  # Add your IBM Quantum token
    hub: "ibm-q"
    group: "open"
    project: "main"

  azure_quantum:
    subscription_id: ""  # Add your Azure subscription
    resource_group: "quantum-rg"
    workspace: "quantum-workspace"

  aws_braket:
    aws_access_key_id: ""  # Add your AWS credentials
    aws_secret_access_key: ""
    region: "us-east-1"

visualization:
  dpi: 300
  format: "png"
  colorscheme: "publication"
  output_dir: "data/outputs"

server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  log_level: "info"

cache:
  enabled: true
  max_size_gb: 10
  ttl_hours: 24
EOF
    echo "✅ Created default config.yaml"
else
    echo "ℹ️  config.yaml already exists, skipping"
fi

# Run tests
echo ""
echo "🧪 Running installation tests..."
python3 -c "
import sys
try:
    from quantum_core.optimizers.adaptive_quantum_optimizer import AdaptiveQuantumOptimizer
    from visualization.quantum_viz_engine import QuantumVizEngine
    print('✅ Core modules imported successfully')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

# Print success message
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║         ✅ INSTALLATION COMPLETE!                                ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📚 Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Configure quantum backends in config.yaml"
echo "   (Add API tokens for IBM Quantum, Azure, AWS Braket)"
echo ""
echo "3. Run example workflow:"
echo "   python examples/complete_workflow_example.py"
echo ""
echo "4. Start API server:"
echo "   python backend/api/quantum_viz_api.py"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "5. Run tests:"
echo "   pytest tests/"
echo ""
echo "📖 Documentation: README.md"
echo "🆘 Support: support@spectrixrd.com"
echo ""
echo "Happy Quantum Visualizing! 🎨⚛️"
