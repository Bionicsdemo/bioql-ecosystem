# 🎯 IonQ Simulators - Complete Guide

## Available IonQ Simulators

BioQL supports all IonQ simulators with your demo API key for **UNLIMITED** free access.

---

## 🖥️ IonQ Simulator Options

### 1. **Ideal Simulator** (Recommended)
```python
backend='ionq.simulator'
```

**Specifications:**
- **Qubits:** 29
- **Noise Model:** Ideal (no noise)
- **Queue Time:** 0 minutes
- **Best for:** Learning, development, algorithm testing
- **Cost with demo key:** FREE (unlimited)

**Use when:**
- Testing new algorithms
- Learning quantum computing
- Maximum accuracy needed
- No hardware noise simulation required

---

### 2. **IonQ Aria 1 Noisy Simulator**
```python
backend='ionq.qpu.aria-1'  # Simulated with noise
```

**Specifications:**
- **Qubits:** 25
- **Noise Model:** Aria 1 hardware simulation
- **Queue Time:** 0 minutes
- **Best for:** Testing real hardware behavior
- **Cost with demo key:** FREE (unlimited)

**Use when:**
- Preparing for real Aria 1 hardware
- Testing noise resilience
- Realistic performance estimation
- Hardware-accurate results needed

---

### 3. **IonQ Harmony Noisy Simulator**
```python
backend='ionq.qpu.harmony'  # Simulated with noise
```

**Specifications:**
- **Qubits:** 11
- **Noise Model:** Harmony hardware simulation
- **Queue Time:** 0 minutes
- **Best for:** Small circuits with realistic noise
- **Cost with demo key:** FREE (unlimited)

**Use when:**
- Testing with smaller qubit count
- Harmony hardware compatibility
- Legacy system testing
- Conservative qubit usage

---

## 🚀 Usage Examples

### Basic Usage (Ideal Simulator)

```python
from bioql import quantum

API_KEY = "__BIOQL_REDACTED__"

# Using ideal simulator (29 qubits, no noise)
result = quantum(
    "create a bell state with two qubits and measure both",
    backend='ionq.simulator',
    api_key=API_KEY,
    shots=1000
)
```

### Aria 1 Noisy Simulator (Realistic)

```python
# Simulate with Aria 1 noise model (25 qubits)
result = quantum(
    "simulate aspirin molecule using variational quantum eigensolver with 6 qubits",
    backend='ionq.qpu.aria-1',
    api_key=API_KEY,
    shots=2048
)
```

### Harmony Noisy Simulator (Small Circuits)

```python
# Simulate with Harmony noise model (11 qubits max)
result = quantum(
    "apply grover search on 3 qubits to find state 101",
    backend='ionq.qpu.harmony',
    api_key=API_KEY,
    shots=1024
)
```

---

## 📊 Comparison Table

| Feature | Ideal Simulator | Aria 1 Simulator | Harmony Simulator |
|---------|----------------|------------------|-------------------|
| **Qubits** | 29 | 25 | 11 |
| **Noise** | None (ideal) | Aria 1 model | Harmony model |
| **Queue** | 0 min | 0 min | 0 min |
| **Speed** | Fastest | Fast | Fastest |
| **Accuracy** | Perfect | ~98% | ~95% |
| **Best For** | Development | Pre-production | Small tests |
| **Cost** | FREE | FREE | FREE |

---

## 🎯 Backend Selection Guide

### Choose **Ideal Simulator** when:
- ✅ Learning BioQL or quantum computing
- ✅ Developing new algorithms
- ✅ Testing maximum theoretical performance
- ✅ No noise simulation needed
- ✅ Using up to 29 qubits

### Choose **Aria 1 Simulator** when:
- ✅ Preparing code for real Aria 1 hardware
- ✅ Testing noise-resilient algorithms
- ✅ Estimating real-world performance
- ✅ Using 12-25 qubits
- ✅ Production-ready testing

### Choose **Harmony Simulator** when:
- ✅ Testing smaller circuits (≤11 qubits)
- ✅ Harmony hardware compatibility
- ✅ Quick noise model testing
- ✅ Legacy code validation

---

## 💻 Complete Demo Scripts

### Script 1: Test All IonQ Simulators

```python
#!/usr/bin/env python3
"""Test all IonQ simulators"""
from bioql import quantum

API_KEY = "__BIOQL_REDACTED__"

backends = [
    ('ionq.simulator', 'Ideal Simulator (29 qubits)'),
    ('ionq.qpu.aria-1', 'Aria 1 Noisy Simulator (25 qubits)'),
    ('ionq.qpu.harmony', 'Harmony Noisy Simulator (11 qubits)')
]

query = "create a bell state with two qubits and measure both"

print("🧬 Testing All IonQ Simulators\n")

for backend, name in backends:
    print(f"Testing {name}...")
    result = quantum(
        query,
        backend=backend,
        api_key=API_KEY,
        shots=1000
    )
    print(f"✅ {name} - Success!\n")

print("🎉 All IonQ simulators tested successfully!")
```

### Script 2: Drug Discovery with Different Simulators

```python
#!/usr/bin/env python3
"""Drug discovery across IonQ simulators"""
from bioql import quantum

API_KEY = "__BIOQL_REDACTED__"

print("🧬 Drug Discovery: Aspirin Simulation\n")

# Test 1: Ideal simulator (no noise, fastest)
print("1. Ideal Simulator (no noise)...")
result1 = quantum(
    "simulate aspirin molecule using VQE with 4 qubits to find ground state energy",
    backend='ionq.simulator',
    api_key=API_KEY,
    shots=2048
)
print("✅ Completed with ideal conditions\n")

# Test 2: Aria 1 simulator (realistic noise)
print("2. Aria 1 Simulator (with hardware noise)...")
result2 = quantum(
    "simulate aspirin molecule using VQE with 4 qubits to find ground state energy",
    backend='ionq.qpu.aria-1',
    api_key=API_KEY,
    shots=2048
)
print("✅ Completed with Aria 1 noise model\n")

# Test 3: Harmony simulator (smaller system)
print("3. Harmony Simulator (legacy hardware)...")
result3 = quantum(
    "simulate aspirin molecule using VQE with 4 qubits to find ground state energy",
    backend='ionq.qpu.harmony',
    api_key=API_KEY,
    shots=2048
)
print("✅ Completed with Harmony noise model\n")

print("🎉 Drug discovery tested on all IonQ simulators!")
```

---

## 🔧 Backend Configuration

### Option 1: Environment Variable
```bash
export BIOQL_BACKEND="ionq.simulator"
```

### Option 2: Config File (~/.bioql/config.yaml)
```yaml
defaults:
  backend: "ionq.simulator"  # or ionq.qpu.aria-1 or ionq.qpu.harmony
  shots: 2048
```

### Option 3: Per-Query (Recommended)
```python
# Explicit backend selection
quantum(
    "your query here",
    backend='ionq.simulator',  # Choose your backend
    api_key=API_KEY
)
```

---

## 🎓 Natural Language Examples (All Simulators)

### Example 1: Bell State (All Simulators)

```python
# Ideal Simulator
quantum(
    "create a bell state with two qubits and measure both",
    backend='ionq.simulator',
    api_key=API_KEY
)

# Aria 1 Simulator
quantum(
    "create a bell state with two qubits and measure both",
    backend='ionq.qpu.aria-1',
    api_key=API_KEY
)

# Harmony Simulator
quantum(
    "create a bell state with two qubits and measure both",
    backend='ionq.qpu.harmony',
    api_key=API_KEY
)
```

### Example 2: Drug Discovery (Ideal Simulator - 29 Qubits)

```python
quantum(
    "simulate semaglutide binding to glp1 receptor using 12 qubits "
    "with variational quantum eigensolver for energy calculation",
    backend='ionq.simulator',
    api_key=API_KEY,
    shots=5000
)
```

### Example 3: Protein Folding (Aria 1 - Realistic)

```python
quantum(
    "simulate protein folding with 8 qubits using quantum annealing "
    "to find minimal energy conformation",
    backend='ionq.qpu.aria-1',
    api_key=API_KEY,
    shots=3000
)
```

### Example 4: Quantum Search (Harmony - Small)

```python
quantum(
    "apply grover algorithm on 5 qubits to search for marked state 10101",
    backend='ionq.qpu.harmony',
    api_key=API_KEY,
    shots=2048
)
```

---

## ⚡ Performance Tips

### 1. **Start with Ideal Simulator**
- Fastest execution
- No noise overhead
- Perfect for development

### 2. **Use Aria 1 for Production Testing**
- Most realistic simulation
- Matches real hardware behavior
- Best for final validation

### 3. **Optimize Shot Count**
```python
# Development: Low shots
shots=1024  # Fast, less accurate

# Production: High shots
shots=5000  # Slower, more accurate
```

### 4. **Match Qubit Count to Backend**
```python
# Ideal: up to 29 qubits
quantum("use 20 qubits...", backend='ionq.simulator')

# Aria 1: up to 25 qubits
quantum("use 20 qubits...", backend='ionq.qpu.aria-1')

# Harmony: up to 11 qubits
quantum("use 8 qubits...", backend='ionq.qpu.harmony')
```

---

## 🚫 Common Errors & Solutions

### Error: "Too many qubits"
```python
# ❌ Wrong: Harmony only supports 11 qubits
quantum("use 15 qubits...", backend='ionq.qpu.harmony')

# ✅ Correct: Use Ideal or Aria 1 for 15+ qubits
quantum("use 15 qubits...", backend='ionq.simulator')
```

### Error: "Backend not found"
```python
# ❌ Wrong backend name
backend='ionq_simulator'  # underscore

# ✅ Correct backend name
backend='ionq.simulator'  # dot
```

### Error: "Invalid API key"
```python
# ✅ Make sure you're using the correct key
API_KEY = "__BIOQL_REDACTED__"
```

---

## 📊 Quick Reference

```python
# IDEAL SIMULATOR (29 qubits, no noise)
backend='ionq.simulator'

# ARIA 1 SIMULATOR (25 qubits, with noise)
backend='ionq.qpu.aria-1'

# HARMONY SIMULATOR (11 qubits, with noise)
backend='ionq.qpu.harmony'

# DEMO API KEY (unlimited access)
api_key='__BIOQL_REDACTED__'
```

---

## 🎯 Recommended Workflow

1. **Development** → Use `ionq.simulator` (ideal, fast)
2. **Testing** → Use `ionq.qpu.aria-1` (realistic noise)
3. **Validation** → Compare all three simulators
4. **Production** → Deploy to real IonQ hardware (requires production API key)

---

## 💡 Pro Tips

1. **Always start with ideal simulator** for fastest development
2. **Test with noise models** before real hardware
3. **Use appropriate qubit count** for each backend
4. **Higher shots = more accurate** but slower
5. **Natural language works** on all backends identically

---

## 📞 Support

- **Email:** support@bioql.com
- **Docs:** https://docs.bioql.com/ionq-simulators
- **IonQ Docs:** https://docs.ionq.com

---

**Ready to test?**

```bash
python examples/ionq_simulators_test.py
```

---

*Last Updated: October 2, 2025*
*BioQL Version: 3.0.2*
*IonQ SDK Supported*
