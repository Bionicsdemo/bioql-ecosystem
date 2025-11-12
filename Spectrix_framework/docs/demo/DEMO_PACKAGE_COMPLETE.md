# 🧬 BioQL Complete Demo Package

## 📦 What's Included

This package contains everything needed to demonstrate **BioQL** - the world's first **100% Natural Language Quantum Computing platform** for drug discovery.

---

## 🔑 DEMO CREDENTIALS (UNLIMITED SIMULATOR ACCESS)

```
API Key: __BIOQL_REDACTED__
Email: demo@bioql.com
Plan: Enterprise (Unlimited)
Backend: IonQ Simulator
Quota: UNLIMITED
Cost: $0.00 (FREE)
```

**⚠️ Important:** This key works ONLY with `ionq_simulator` backend. Real quantum hardware requires a production API key.

---

## 🚀 Quick Start (30 Seconds)

### Option 1: Quick Test (3 examples)
```bash
pip install bioql
python examples/quick_test.py
```

### Option 2: Full Demo (10 examples)
```bash
pip install bioql
python examples/demo_unlimited_simulator.py
```

### Option 3: Your Own Code
```python
from bioql import quantum

API_KEY = "__BIOQL_REDACTED__"

result = quantum(
    "create a bell state with two qubits and measure both",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=1000
)

print(result)
```

---

## 📁 Files Included

| File | Description | Lines |
|------|-------------|-------|
| `DEMO_CREDENTIALS.md` | Complete guide with credentials & examples | 400+ |
| `DEMO_README.txt` | Quick reference (plain text) | 150+ |
| `examples/quick_test.py` | 30-second demo (3 examples) | 60 |
| `examples/demo_unlimited_simulator.py` | Full demo (10 examples) | 250+ |

---

## 💻 Natural Language Examples (100% English)

### 1. Drug Discovery - Aspirin Simulation
```python
quantum(
    "simulate the molecular structure of aspirin using variational quantum eigensolver "
    "with 4 qubits to find ground state energy for drug optimization",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=2048
)
```

### 2. Protein Folding
```python
quantum(
    "simulate small protein fragment folding using quantum annealing approach "
    "with 6 qubits representing different conformational states",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=3000
)
```

### 3. Drug-Receptor Binding Energy
```python
quantum(
    "compute the binding energy between semaglutide drug molecule and glp1 receptor "
    "using variational quantum eigensolver on 6 qubits with hardware efficient ansatz",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=5000
)
```

### 4. Quantum Chemistry - Water Molecule
```python
quantum(
    "calculate the dipole moment and bond angles of water molecule H2O "
    "using quantum circuit with 4 qubits for electron orbital simulation",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=2048
)
```

### 5. Quantum Machine Learning - Toxicity Prediction
```python
quantum(
    "train a variational quantum classifier on 4 qubits to predict drug toxicity "
    "based on molecular features using quantum neural network",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=4096
)
```

### 6. Grover's Search Algorithm
```python
quantum(
    "apply grover search algorithm on 3 qubits to find the target state "
    "marked as 101 in the quantum database",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=1024
)
```

### 7. Quantum Fourier Transform
```python
quantum(
    "perform quantum fourier transform on 4 qubits initialized in equal superposition "
    "and measure the frequency spectrum",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=2048
)
```

### 8. QAOA Optimization
```python
quantum(
    "use quantum approximate optimization algorithm qaoa with 4 qubits "
    "to find optimal combination of three drugs minimizing side effects",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=3000
)
```

### 9. GHZ State (Multi-Qubit Entanglement)
```python
quantum(
    "create greenberger horne zeilinger state using 5 qubits "
    "where all qubits are maximally entangled and measure correlation",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=2048
)
```

### 10. Bell State (Basic Entanglement)
```python
quantum(
    "create a bell state with two qubits and measure both",
    backend='ionq_simulator',
    api_key=API_KEY,
    shots=1000
)
```

---

## 📊 Demo Script Details

### Quick Test (`examples/quick_test.py`)
- **Duration:** 30 seconds
- **Examples:** 3 (Bell State, Aspirin, Grover)
- **Total Shots:** 4,072
- **Perfect for:** Quick demos, initial validation

### Full Demo (`examples/demo_unlimited_simulator.py`)
- **Duration:** 2-3 minutes
- **Examples:** 10 (all algorithms)
- **Total Shots:** 27,360
- **Perfect for:** Complete product demonstration

**Both scripts include:**
- ✅ Progress indicators
- ✅ Success confirmations
- ✅ Summary statistics
- ✅ Zero configuration needed

---

## 🎯 What This Demo Shows

### ✨ Key Features
1. **100% Natural Language** - No quantum gates knowledge required
2. **164 Billion Patterns** - Understands complex scientific queries
3. **Drug Discovery Ready** - Molecular simulations, binding energy, toxicity
4. **All Quantum Algorithms** - VQE, QAOA, Grover, QFT, GHZ
5. **Instant Results** - Sub-minute execution on simulator
6. **Production Ready** - Enterprise-grade code quality

### 🧬 Use Cases Demonstrated
- Drug discovery (aspirin, semaglutide)
- Protein folding simulations
- Quantum chemistry (water molecule)
- Quantum machine learning (toxicity prediction)
- Quantum search (Grover's algorithm)
- Signal processing (QFT)
- Optimization (QAOA)
- Quantum entanglement (Bell, GHZ)

---

## 💰 Demo vs Production

| Feature | Demo Key (FREE) | Production Key |
|---------|----------------|----------------|
| **IonQ Simulator** | ✅ UNLIMITED | ✅ Included |
| **IBM Quantum** | ❌ | ✅ (Academic+) |
| **IonQ QPU** | ❌ | ✅ (Biotech+) |
| **Shots/Month** | Unlimited | Plan-based |
| **Cost** | $0 | From $49/month |
| **Support** | Community | Email/Discord |
| **SLA** | None | 99.9%+ |

**Get production access:** https://bioql.com/signup

---

## 🔧 Installation Requirements

### Minimum
```bash
pip install bioql
```

### With Visualization
```bash
pip install bioql[viz]
```

### Complete (All Features)
```bash
pip install bioql[cloud,visualization,vina,viz,openmm]
```

### System Requirements
- **Python:** 3.8 - 3.12
- **OS:** Linux, macOS, Windows
- **RAM:** 4GB minimum, 8GB recommended
- **Internet:** Required for API authentication

---

## 📖 Documentation

### Quick Links
- **Installation:** `docs/INSTALLATION.md`
- **API Reference:** `docs/BIOQL_V3_README.md`
- **Pricing:** `docs/BIOQL_PRICING.md`
- **Technical Details:** `docs/TECHNICAL_REFERENCE.md`

### Online Resources
- **Website:** https://bioql.com
- **Docs:** https://docs.bioql.com
- **GitHub:** https://github.com/bioql/bioql
- **Discord:** https://discord.gg/bioql

---

## 🐛 Troubleshooting

### "Invalid API Key"
**Problem:** Wrong key or typo
**Solution:** Use exact key: `__BIOQL_REDACTED__`

### "Backend not available"
**Problem:** Trying to use real hardware
**Solution:** Use `backend='ionq_simulator'` (not `ionq_qpu`)

### "Module not found: bioql"
**Problem:** BioQL not installed
**Solution:** `pip install bioql`

### "Connection timeout"
**Problem:** Network issue or firewall
**Solution:** Check internet connection, try again

### Performance Issues
**Problem:** Slow execution
**Solution:** Reduce shots (1024 is usually enough for demos)

---

## 📞 Support

### Community Support (FREE)
- **Discord:** https://discord.gg/bioql
- **GitHub Issues:** https://github.com/bioql/bioql/issues
- **Stack Overflow:** Tag `bioql`

### Enterprise Support
- **Email:** support@bioql.com
- **Response Time:** 24 hours
- **Dedicated Slack Channel:** Available for Enterprise plan

---

## 🎬 Video Demos

1. **Installation & Quick Start** (2 min)
   - Install BioQL
   - Run first quantum circuit
   - Understand results

2. **Drug Discovery Workflow** (5 min)
   - Molecular simulation
   - Binding energy calculation
   - Toxicity prediction

3. **Natural Language Deep Dive** (10 min)
   - How the parser works
   - 164 billion patterns explained
   - Advanced query optimization

**Watch all videos:** https://bioql.com/videos

---

## 📚 Citation

If you use BioQL in your research:

```bibtex
@software{bioql2025,
  title = {BioQL: Natural Language Quantum Computing for Bioinformatics},
  author = {BioQL Development Team},
  year = {2025},
  version = {3.0.2},
  url = {https://bioql.com},
  doi = {10.5281/zenodo.XXXXXXX}
}
```

---

## 🚀 Next Steps

### 1. Run the Demo
```bash
pip install bioql
python examples/quick_test.py
```

### 2. Explore Examples
```bash
python examples/demo_unlimited_simulator.py
```

### 3. Build Your Application
```python
from bioql import quantum

API_KEY = "__BIOQL_REDACTED__"

# Your quantum drug discovery code here!
result = quantum(
    "your natural language query",
    backend='ionq_simulator',
    api_key=API_KEY
)
```

### 4. Get Production Access
Visit: https://bioql.com/signup

---

## 💎 Why BioQL?

### Traditional Approach (Qiskit)
```python
from qiskit import QuantumCircuit, execute, Aer
from qiskit.algorithms import VQE
from qiskit.circuit.library import TwoLocal
from qiskit.opflow import PauliSumOp

# 50+ lines of complex quantum code...
```

### BioQL Approach
```python
from bioql import quantum

result = quantum(
    "simulate aspirin molecule using VQE with 4 qubits",
    backend='ionq_simulator',
    api_key=API_KEY
)
```

**Result:** 50x less code, 100x easier to use! 🚀

---

## ✅ Checklist for Demo

- [ ] Install BioQL: `pip install bioql`
- [ ] Copy API key: `__BIOQL_REDACTED__`
- [ ] Run quick test: `python examples/quick_test.py`
- [ ] Run full demo: `python examples/demo_unlimited_simulator.py`
- [ ] Review results and documentation
- [ ] Share with your team!

---

## 🎉 You're Ready!

**Demo API Key:** `__BIOQL_REDACTED__`

**Quick Command:**
```bash
pip install bioql && python examples/quick_test.py
```

**Welcome to the future of quantum computing!** 🧬⚛️

---

*Last Updated: October 2, 2025*
*Version: 3.0.2*
*License: MIT*
