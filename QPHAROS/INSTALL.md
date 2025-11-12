# QPHAROS Installation Guide

## Prerequisites

- Python 3.8 or higher
- BioQL API key (get from https://bioql.bio)
- 4GB+ RAM recommended
- Access to IBM Quantum (optional, for real hardware)

## Installation Steps

### 1. Clone or Download QPHAROS

```bash
cd /path/to/Spectrix_BioQL
# QPHAROS is already in the repository
```

### 2. Install Dependencies

```bash
cd QPHAROS
pip install -r requirements.txt
```

### 3. Install BioQL

```bash
pip install bioql
```

### 4. Set API Key

Set your BioQL API key as an environment variable:

**MacOS/Linux:**
```bash
export BIOQL_API_KEY="your_api_key_here"
```

**Windows:**
```cmd
set BIOQL_API_KEY=your_api_key_here
```

Or add to your Python code:
```python
import os
os.environ['BIOQL_API_KEY'] = 'your_api_key_here'
```

### 5. Verify Installation

```bash
cd examples
python example_binding_prediction.py
```

## Optional Dependencies

### OpenBabel (GPL-2.0)

**Important:** OpenBabel is licensed under GPL-2.0, which is incompatible with BioQL's Apache 2.0 license. Therefore, it is NOT included in the default installation.

If you need OpenBabel functionality:
```bash
pip install openbabel-wheel
```

**Note:** By installing OpenBabel, you accept the GPL-2.0 license terms.

**Alternative:** BioQL uses RDKit as the default chemistry toolkit, which provides similar functionality under a BSD license.

### RDKit (for advanced chemistry)

```bash
conda install -c conda-forge rdkit
# or
pip install rdkit
```

### Qiskit (for direct quantum circuit access)

```bash
pip install qiskit qiskit-nature
```

### PennyLane (for variational circuits)

```bash
pip install pennylane pennylane-qiskit
```

## IBM Quantum Setup (Optional)

To use real IBM Quantum hardware:

1. Create account at https://quantum-computing.ibm.com/
2. Get your API token
3. Configure BioQL with IBM credentials

```python
config = QPHAROSConfig(
    backend="ibm_torino",
    api_key="your_bioql_key"
)
```

## Docker Installation (Alternative)

```bash
# Build Docker image
docker build -t qpharos .

# Run container
docker run -it -e BIOQL_API_KEY=your_key qpharos
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`, ensure QPHAROS is in your Python path:

```python
import sys
sys.path.insert(0, '/path/to/Spectrix_BioQL/QPHAROS')
```

### BioQL Connection Issues

- Verify API key is set correctly
- Check internet connection
- Ensure firewall allows HTTPS traffic

### Quantum Backend Errors

- Start with `backend="simulator"` for testing
- IBM Torino requires valid IBM Quantum credentials
- Check backend availability on IBM Quantum dashboard

## Getting Help

- Documentation: See README.md
- Examples: Check examples/ directory
- Issues: Report at https://github.com/spectrixrd/bioql
- Email: support@bioql.bio

## Next Steps

After installation, try the examples:

1. `example_binding_prediction.py` - Basic binding prediction
2. `example_admet_optimization.py` - ADMET analysis
3. `example_molecular_generation.py` - Generate new molecules
4. `example_complete_pipeline.py` - Full drug design workflow

Enjoy using QPHAROS! 🧬⚛️
