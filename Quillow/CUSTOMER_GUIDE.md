# 🎉 Quillow - Customer Installation Guide

## Welcome to Quillow!

Quillow is now available on PyPI! This guide will help you get started with quantum error correction for your BioQL quantum chemistry calculations.

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Quillow

```bash
pip install quillow
```

That's it! Quillow is now installed on your system.

### Step 2: Get Your BioQL API Key

1. Sign up at [bioql.bio](https://bioql.bio)
2. Get your API key (format: `bioql_XXXXXXXX...`)
3. Set it as an environment variable:

```bash
export BIOQL_API_KEY="__BIOQL_REDACTED__"
```

**Or** create a config file:

```bash
mkdir -p ~/.quillow
cat > ~/.quillow/config.yaml << EOF
bioql:
  api_key: bioql_YOUR_API_KEY_HERE
  base_url: https://api.bioql.bio
qec:
  default_distance: 5
  enable_by_default: true
EOF
```

### Step 3: Verify Installation

```bash
# Check version
quillow --version

# View system info
quillow info

# Test BioQL connection
quillow check-bioql
```

---

## 💡 Usage Examples

### Example 1: Basic QEC Simulation

```python
from quillow.core import RotatedSurfaceCode
from quillow.decoders import PyMatchingDecoder

# Create d=5 surface code
surface_code = RotatedSurfaceCode(distance=5, rounds=5)
circuit = surface_code.build_stim_circuit()

# Sample with noise
sampler = circuit.compile_detector_sampler()
syndromes, observables = sampler.sample(shots=10000, separate_observables=True)

# Decode
decoder = PyMatchingDecoder()
predictions = decoder.decode_batch(syndromes, circuit)

# Check error rate
logical_errors = (predictions != observables[:, 0]).sum()
print(f"Logical error rate: {logical_errors / 10000:.6f}")
```

### Example 2: Protect BioQL Quantum Chemistry (CLI)

```bash
# Run quantum chemistry with QEC protection on real hardware
quillow protect-bioql \
  --query "optimize H2 molecule with VQE" \
  --backend ibm_torino \
  --shots 2048 \
  --qec-distance 5
```

### Example 3: Protect BioQL Quantum Chemistry (Python)

```python
from quillow.backends.bioql_backend import BioQLOptimizer

# Initialize (reads BIOQL_API_KEY from environment)
optimizer = BioQLOptimizer(qec_distance=5)

# Execute with QEC protection on real quantum hardware
result = optimizer.execute_with_qec(
    bioql_query="apply VQE to aspirin molecule",
    backend="ibm_torino",  # or "ionq_forte", "aws_sv1", "simulator"
    shots=2048
)

print(f"✅ Calculation complete!")
print(f"Energy: {result['energy']:.6f} Hartree")
print(f"Raw Energy (no QEC): {result['raw_energy']:.6f} Hartree")
print(f"QEC Improvement: {abs(result['raw_energy'] - result['energy']):.6f}")
print(f"Logical Error Rate: {result['logical_error_rate']:.6f}")
```

### Example 4: Direct Backend Control

```python
from quillow.backends.bioql_backend import BioQLBackend, BioQLConfig
import stim

# Configure
config = BioQLConfig(
    api_key="bioql_YOUR_KEY_HERE",
    base_url="https://api.bioql.bio"
)

backend = BioQLBackend(config, qec_distance=5)

# Validate connection
if backend.validate_api_key():
    print("✅ Connected to BioQL")

# Check quota
quota = backend.check_quota()
print(f"Remaining balance: ${quota['balance']:.2f}")
print(f"Tier: {quota['tier']}")

# Execute circuit with QEC
circuit = stim.Circuit("""
    H 0
    CNOT 0 1
    M 0 1
""")

result = backend.execute(circuit, shots=1024, backend="ibm_torino")
print(f"Logical error rate: {result.metadata['logical_error_rate']:.6f}")
```

---

## 💰 Pricing & Billing

Quillow automatically tracks QEC overhead and bills through your BioQL account:

| QEC Distance | Overhead | Example Cost (2048 shots) |
|--------------|----------|---------------------------|
| **d=3** | 1.2x | $2.46 (vs $2.05 without QEC) |
| **d=5** | 1.5x | $3.07 (vs $2.05 without QEC) |
| **d=7** | 2.0x | $4.10 (vs $2.05 without QEC) |

**Base cost**: $0.001 per shot on real hardware

**Why pay for QEC?**
- 📉 **Lower error rates**: 2-10x reduction in logical errors
- 🎯 **More accurate results**: Better energy estimates for quantum chemistry
- 🔬 **Scientific quality**: Publication-ready data with error correction

All usage is recorded automatically to your BioQL account via `api.bioql.bio/billing/record-usage`.

---

## 🎛️ CLI Commands

```bash
# Basic commands
quillow --version                  # Show version
quillow info                       # System information
quillow check-bioql               # Test BioQL API connection

# Simulations
quillow simulate -d 5 -s 10000 --decoder pymatching
quillow simulate -d 3,5,7 -s 5000  # Multiple distances

# BioQL integration
quillow protect-bioql \
  --query "optimize molecule" \
  --backend ibm_torino \
  --shots 2048 \
  --qec-distance 5

# Benchmarks
quillow benchmark threshold --distances 3,5,7
quillow benchmark decoder --shots 10000

# Account management
quillow quota                     # Check BioQL quota
quillow usage                     # View usage history
```

---

## 🔧 Advanced Configuration

### GPU Acceleration (Optional)

For high-throughput decoding:

```bash
pip install quillow[gpu]
```

Then use GPU decoders:

```python
from quillow.decoders.gpu_decoder_modal import decode_batch_gpu

# Achieves 100K+ shots/sec on A100
```

### Modal Cloud GPU (Optional)

For cloud GPU deployment:

```bash
pip install quillow[cloud]
modal deploy quillow/decoders/gpu_decoder_modal.py
```

---

## 📊 Supported Backends

Quillow integrates with BioQL to access these quantum backends:

| Backend | Type | Description |
|---------|------|-------------|
| `simulator` | Free | Fast local simulator (testing) |
| `ibm_torino` | Paid | IBM 127-qubit quantum processor |
| `ionq_forte` | Paid | IonQ trapped-ion system |
| `aws_sv1` | Paid | AWS Braket state vector |
| `aws_dm1` | Paid | AWS Braket density matrix |

*Pricing varies by backend. Check [bioql.bio/pricing](https://bioql.bio/pricing) for details.*

---

## 🆘 Troubleshooting

### "BIOQL_API_KEY not set"

```bash
export BIOQL_API_KEY="bioql_YOUR_KEY_HERE"
```

Or add to your `~/.bashrc` or `~/.zshrc`:

```bash
echo 'export BIOQL_API_KEY="bioql_YOUR_KEY_HERE"' >> ~/.bashrc
source ~/.bashrc
```

### "API key validation failed"

1. Check your API key is correct
2. Verify at [bioql.bio/account](https://bioql.bio/account)
3. Ensure account has sufficient balance

### "Package not found" errors

```bash
pip install --upgrade quillow
```

### ImportError: Missing dependencies

```bash
# Install all dependencies
pip install quillow[all]

# Or install specific features
pip install quillow[gpu]    # GPU support
pip install quillow[cloud]  # Modal cloud
```

---

## 📚 Documentation

- **GitHub**: https://github.com/spectrixrd/quillow
- **PyPI**: https://pypi.org/project/quillow/
- **BioQL Platform**: https://bioql.bio
- **Support**: support@bioql.bio

---

## 🤝 Community

- **Discord**: https://discord.gg/spectrixrd
- **Twitter**: @SpectrixRD
- **Issues**: https://github.com/spectrixrd/quillow/issues

---

## 📝 License

Quillow is MIT licensed. See [LICENSE](LICENSE) for details.

---

## 🎓 Examples

See the [examples/](examples/) directory for more usage examples:

- `basic_simulation.py` - Simple QEC simulation
- `bioql_protection.py` - BioQL integration examples
- `customer_usage_example.py` - Comprehensive walkthrough

---

## 🚀 Ready to Go!

You're all set! Start using quantum error correction for your quantum chemistry calculations:

```bash
pip install quillow
export BIOQL_API_KEY="bioql_YOUR_KEY_HERE"
quillow protect-bioql --query "your molecule" --backend ibm_torino
```

**Questions?** Contact support@bioql.bio

**Happy quantum computing!** 🔬⚛️
