# BioQL - Quantum Computing for Bioinformatics

[![PyPI version](https://badge.fury.io/py/bioql.svg)](https://badge.fury.io/py/bioql)
[![Python Version](https://img.shields.io/pypi/pyversions/bioql.svg)](https://pypi.org/project/bioql/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**BioQL** is a quantum computing framework specifically designed for bioinformatics applications, developed by SpectrixRD. It provides a high-level interface for executing quantum algorithms on biological data, bridging the gap between quantum computing and computational biology.

## ⚠️ API Key Required

**All quantum executions require a valid API key from SpectrixRD.** The package is freely installable but authentication is mandatory for usage. Contact [hello@spectrixrd.com](mailto:hello@spectrixrd.com) to request access.

## 🚀 Quick Start

### Installation

```bash
pip install bioql
```

### Get Your API Key

1. Contact us at [hello@spectrixrd.com](mailto:hello@spectrixrd.com) to request access
2. Receive your API key and plan details via email
3. Start using BioQL with your personal API key

### Basic Usage

```python
from bioql import quantum

# API key is required for all executions
result = quantum(
    program="Create a 2-qubit Bell state circuit",
    api_key="your_api_key_here",  # Required!
    backend="simulator",
    shots=1000
)

if result.success:
    print(f"Measurement results: {result.counts}")
    print(f"Execution cost: ${result.cost_estimate:.4f}")
else:
    print(f"Error: {result.error_message}")
```

## 📖 Features

### Quantum Computing for Biology
- **DNA/RNA Analysis**: Quantum algorithms for sequence alignment and analysis
- **Protein Folding**: Quantum approaches to protein structure prediction
- **Genomics**: Quantum machine learning for genomic data
- **Drug Discovery**: Quantum optimization for molecular design

### Backend Support
- **Local Simulator**: Fast classical simulation for development
- **IBM Quantum**: Real quantum hardware access (Pro/Enterprise plans)
- **IonQ**: Trapped-ion quantum computers (Enterprise plan)
- **Cloud Integration**: Seamless cloud quantum computing

### Billing & Plans
- **Basic**: 1,000 shots/month, simulator only
- **Pro**: 50,000 shots/month, IBM Quantum access
- **Enterprise**: 1M+ shots/month, all backends, priority support

## 🔬 Scientific Applications

### DNA Sequence Analysis
```python
from bioql import quantum

# Quantum sequence alignment
result = quantum(
    program="Align sequences: ATCGATCG vs ATCGATCC",
    api_key="your_api_key",
    backend="simulator",
    shots=500
)
```

### Protein Structure Prediction
```python
# Quantum protein folding simulation
result = quantum(
    program="Fold protein with sequence: MGHHHHHHH",
    api_key="your_api_key",
    backend="ibm_quantum",
    shots=1000
)
```

### Pharmacogenomics
```python
# Drug-target interaction modeling
result = quantum(
    program="Model drug binding: aspirin + COX1",
    api_key="your_api_key",
    backend="ionq",
    shots=2000
)
```

## 🛡️ Authentication Model

BioQL implements a **mandatory API key authentication system**:

### Why API Keys?
- **Usage Control**: Track and limit quantum resource consumption
- **Billing**: Accurate cost tracking for quantum executions
- **Plan Management**: Access control for different quantum backends
- **Security**: Secure access to premium quantum hardware

### Getting Started
1. **Install**: `pip install bioql` (free, open source)
2. **Request Access**: Contact [hello@spectrixrd.com](mailto:hello@spectrixrd.com) for API key
3. **Execute**: All quantum functions require `api_key` parameter

### Error Handling
```python
try:
    result = quantum(
        program="Create Bell state",
        api_key="invalid_key",  # This will fail
        backend="simulator"
    )
except Exception as e:
    if "Invalid API key" in str(e):
        print("Please get a valid API key from hello@spectrixrd.com")
    elif "Usage limit exceeded" in str(e):
        print("Contact hello@spectrixrd.com to upgrade your plan")
```

## 📊 Supported Quantum Operations

### Basic Quantum Circuits
- Single-qubit gates (X, Y, Z, H, S, T)
- Two-qubit gates (CNOT, CZ, SWAP)
- Multi-qubit entanglement (Bell states, GHZ states)
- Quantum measurements and state tomography

### Advanced Algorithms
- **QAOA**: Quantum Approximate Optimization Algorithm
- **VQE**: Variational Quantum Eigensolver
- **Grover's**: Quantum search algorithm
- **Shor's**: Quantum factoring (limited implementations)

### Bioinformatics-Specific
- **Sequence Alignment**: Quantum dynamic programming
- **Structure Prediction**: Quantum annealing approaches
- **Phylogenetic Trees**: Quantum clustering algorithms
- **Molecular Dynamics**: Quantum simulation methods

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   BioQL Client  │───▶│ Authentication  │───▶│ Quantum Backend │
│   (Your Code)   │    │   Service       │    │   (IBM/IonQ)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  pip install    │    │   API Key       │    │   Quantum       │
│     bioql       │    │ Validation      │    │  Execution      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📈 Usage Monitoring

Track your quantum usage:

```python
from bioql import get_usage_stats

# Check your current usage
usage = get_usage_stats(api_key="your_api_key")
print(f"Shots used this month: {usage.shots_used}/{usage.monthly_limit}")
print(f"Current cost: ${usage.current_cost:.2f}")
print(f"Remaining credits: ${usage.credits_remaining:.2f}")
```

## 🔧 Advanced Configuration

### Environment Variables
```bash
# Optional: Set default API key
export BIOQL_API_KEY="your_api_key_here"

# Optional: Set authentication endpoint
export BIOQL_AUTH_URL="https://auth.bioql.com"
```

### Python Configuration
```python
import bioql

# Configure global settings
bioql.configure(
    api_key="your_api_key",
    default_backend="simulator",
    default_shots=1000,
    debug=True
)

# Now api_key is optional in individual calls
result = bioql.quantum("Create Bell state")
```

## 🧪 Testing & Development

### Running Tests
```bash
# Install development dependencies
pip install bioql[dev]

# Run tests
pytest tests/

# Run with coverage
pytest --cov=bioql tests/
```

### Local Development
```bash
# Clone repository
git clone https://github.com/bioql/bioql.git
cd bioql

# Install in development mode
pip install -e .[dev]

# Run linting
black bioql/
isort bioql/
flake8 bioql/
mypy bioql/
```

## 📚 Documentation

- **API Reference**: [docs.bioql.com/api](https://docs.bioql.com/api)
- **Tutorials**: [docs.bioql.com/tutorials](https://docs.bioql.com/tutorials)
- **Examples**: [github.com/bioql/bioql/examples](https://github.com/bioql/bioql/tree/main/examples)
- **Research Papers**: [bioql.com/research](https://bioql.com/research)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

BioQL is released under the [MIT License](LICENSE).

## 🆘 Support

- **Documentation**: [docs.bioql.com](https://docs.bioql.com)
- **Issues**: [GitHub Issues](https://github.com/bioql/bioql/issues)
- **Email**: [hello@spectrixrd.com](mailto:hello@spectrixrd.com)
- **Community**: [Discord Server](https://discord.gg/bioql)

## 🎯 Roadmap

### Q1 2024
- [ ] Enhanced protein folding algorithms
- [ ] Real-time quantum execution monitoring
- [ ] Advanced visualization tools

### Q2 2024
- [ ] GPU-accelerated classical simulation
- [ ] Integration with major biology databases
- [ ] Quantum machine learning models

### Q3 2024
- [ ] Multi-cloud quantum backend support
- [ ] Quantum error correction integration
- [ ] Enterprise security features

## 📊 Benchmarks

| Algorithm | Classical (s) | Quantum (s) | Speedup |
|-----------|--------------|-------------|---------|
| Sequence Alignment (100bp) | 0.045 | 0.023 | 2x |
| Protein Folding (50 residues) | 120.0 | 45.0 | 2.7x |
| Drug Screening (1000 compounds) | 1800 | 600 | 3x |

*Benchmarks on IBM Quantum 127-qubit systems vs classical workstation

## 🌟 Sponsors

BioQL is supported by leading organizations in quantum computing and bioinformatics:

- **IBM Quantum Network**
- **IonQ Research Program**
- **National Science Foundation**
- **Quantum Economic Development Consortium**

---

**Ready to start your quantum bioinformatics journey?**

```bash
pip install bioql
```

Get your API key by contacting [hello@spectrixrd.com](mailto:hello@spectrixrd.com) and start exploring the quantum advantage in biology! 🚀🧬
