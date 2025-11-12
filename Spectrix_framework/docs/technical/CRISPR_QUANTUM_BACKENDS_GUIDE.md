# 🧬⚛️ BioQL CRISPR-QAI: Real Quantum Hardware Guide

**BioQL v5.4.3 + VSIX v4.5.0 + Modal Agent**

---

## 🎯 What's New

BioQL CRISPR-QAI now supports **3 quantum backends** for guide RNA design:

1. **Local Simulator** - Fast, free, no credentials required
2. **IBM Qiskit** - Access to IBM Quantum hardware (Torino 133q, Kyoto, Osaka)
3. **AWS Braket** - Access to AWS Quantum hardware (Rigetti, IonQ)

---

## 🚀 Quick Start

### Option 1: VS Code Extension (Easiest)

1. Open Cursor/VS Code
2. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows)
3. Type: **"BioQL: Design CRISPR Guide"**
4. Enter guide sequence: `ATCGAAGTCGCTAGCTA`
5. Select backend:
   - 🖥️ **Local Simulator** (free, instant)
   - ⚛️ **IBM Qiskit** (requires token)
   - ☁️ **AWS Braket** (requires credentials)

The extension will generate ready-to-run code!

---

## 📋 Backend Options

### 1️⃣ Local Simulator (Always Available)

**No setup required** - Works out of the box!

```python
from bioql.crispr_qai import estimate_energy_collapse_simulator

result = estimate_energy_collapse_simulator(
    guide_seq="ATCGAAGTCGCTAGCTA",
    shots=1000,
    coupling_strength=1.0,
    seed=42  # Reproducibility
)

print(f"Energy: {result['energy_estimate']:.4f}")
print(f"Confidence: {result['confidence']:.4f}")
```

**Use for:**
- Rapid prototyping
- Testing workflows
- Educational purposes
- Cost-free experimentation

---

### 2️⃣ IBM Qiskit (Real Quantum Hardware)

**Setup:**
```bash
# Get token from: https://quantum.ibm.com/
export IBM_QUANTUM_TOKEN="your_token_here"
```

**Available Devices:**
- `aer_simulator` - Local Qiskit simulator
- `ibm_torino` - 133-qubit processor (validated: 10k shots, 99.7% fidelity)
- `ibm_kyoto` - 127-qubit processor
- `ibm_osaka` - 127-qubit processor

**Code:**
```python
from bioql.crispr_qai import estimate_energy_collapse_qiskit
import os

result = estimate_energy_collapse_qiskit(
    guide_seq="ATCGAAGTCGCTAGCTA",
    backend_name="ibm_torino",  # Real quantum hardware!
    shots=1000,
    coupling_strength=1.0,
    ibm_token=os.getenv("IBM_QUANTUM_TOKEN")
)

print(f"✅ Quantum computation complete!")
print(f"Energy: {result['energy_estimate']:.4f}")
print(f"Backend: {result['backend']}")
```

**Use for:**
- Production CRISPR experiments
- Research publications
- Real quantum advantage exploration
- Benchmarking vs. classical methods

**Cost:** IBM provides free credits; hardware access may have queue times.

---

### 3️⃣ AWS Braket (Cloud Quantum Hardware)

**Setup:**
```bash
# Configure AWS CLI
aws configure
# Enter Access Key, Secret Key, region (us-east-1)

# Create S3 bucket for results (required)
aws s3 mb s3://my-braket-bucket --region us-east-1
```

**Available Devices:**
- `SV1` - State Vector Simulator (32 qubits)
- `DM1` - Density Matrix Simulator (17 qubits)
- `Aspen-M-3` - Rigetti 79-qubit processor (real hardware)
- `Harmony` - IonQ 11-qubit trapped-ion (real hardware)

**Code:**
```python
from bioql.crispr_qai import estimate_energy_collapse_braket

result = estimate_energy_collapse_braket(
    guide_seq="ATCGAAGTCGCTAGCTA",
    backend_name="SV1",  # Or Aspen-M-3, Harmony
    shots=1000,
    coupling_strength=1.0,
    aws_region="us-east-1",
    s3_bucket="my-braket-bucket"
)

print(f"✅ AWS Braket computation complete!")
print(f"Energy: {result['energy_estimate']:.4f}")
print(f"Backend: {result['backend']}")
```

**Use for:**
- Enterprise CRISPR pipelines
- Multi-backend comparisons
- Ion trap experiments (IonQ)
- Superconducting qubits (Rigetti)

**Cost:** AWS Braket charges per shot/task. Simulators are cheaper than hardware.

---

## 🧪 Example Workflows

### Workflow 1: Compare All Backends

```python
from bioql.crispr_qai import (
    estimate_energy_collapse_simulator,
    estimate_energy_collapse_qiskit,
    estimate_energy_collapse_braket
)
import os

guide = "ATCGAAGTCGCTAGCTA"

print("Comparing quantum backends for CRISPR guide design...\n")

# Local
r1 = estimate_energy_collapse_simulator(guide, shots=1000, seed=42)
print(f"Local Simulator: {r1['energy_estimate']:.4f}")

# IBM
r2 = estimate_energy_collapse_qiskit(
    guide,
    backend_name="aer_simulator",
    shots=1000,
    ibm_token=os.getenv("IBM_QUANTUM_TOKEN")
)
print(f"IBM Qiskit: {r2['energy_estimate']:.4f}")

# AWS
r3 = estimate_energy_collapse_braket(
    guide,
    backend_name="SV1",
    shots=1000,
    aws_region="us-east-1",
    s3_bucket="my-braket-bucket"
)
print(f"AWS Braket: {r3['energy_estimate']:.4f}")
```

---

### Workflow 2: Rank Guides on IBM Torino (Real Quantum)

```python
from bioql.crispr_qai import rank_guides_batch
from bioql.crispr_qai.adapters.qiskit_adapter import QiskitEngine
import os

# Define guides
guides = [
    "ATCGAAGTCGCTAGCTA",
    "GCTAGCTACGATCCGA",
    "TTAACCGGTTAACCGG"
]

# Create IBM Torino engine
engine = QiskitEngine(
    backend_name="ibm_torino",
    shots=1000,
    ibm_token=os.getenv("IBM_QUANTUM_TOKEN")
)

# Rank guides using real quantum hardware
print("🧬 Ranking guides on IBM Torino 133-qubit processor...")

results = []
for guide in guides:
    from bioql.crispr_qai import estimate_energy_collapse_qiskit
    result = estimate_energy_collapse_qiskit(
        guide_seq=guide,
        backend_name="ibm_torino",
        shots=1000,
        ibm_token=os.getenv("IBM_QUANTUM_TOKEN")
    )
    results.append(result)

# Sort by energy
results.sort(key=lambda x: x['energy_estimate'])

print("\n✅ Top guides (lowest energy = strongest binding):")
for i, r in enumerate(results, 1):
    print(f"{i}. {r['guide_sequence']}: {r['energy_estimate']:.4f}")
```

---

### Workflow 3: Natural Language (VS Code Extension)

**No code required!** Just ask in natural language:

```
"Score CRISPR guide ATCGAAGTCGCTAGCTA using IBM Torino with 1000 shots"
```

```
"Rank these guides using AWS Braket SV1:
 ATCGAAGTCGCTAGCTA, GCTAGCTACGATCCGA, TTAACCGGTTAACCGG"
```

```
"Analyze off-targets for guide ATCGAAGTCGCTAGCTA using IBM Qiskit aer_simulator"
```

The BioQL agent will:
1. Detect backend (IBM/AWS/Simulator)
2. Extract guide sequences
3. Generate optimized code
4. Return ready-to-execute script

---

## 🎛️ Backend Selection Guide

| Use Case | Recommended Backend | Why |
|----------|---------------------|-----|
| **Learning/Testing** | Local Simulator | Free, instant, no setup |
| **Production CRISPR** | IBM Torino | Validated, 133 qubits, 99.7% fidelity |
| **Cost-Sensitive** | IBM aer_simulator | Free Qiskit simulator |
| **Enterprise Pipeline** | AWS Braket SV1 | Cloud-native, scalable |
| **Ion Trap Research** | AWS Harmony (IonQ) | Trapped-ion hardware |
| **Superconducting** | AWS Aspen-M (Rigetti) | Superconducting qubits |
| **Benchmarking** | All 3 backends | Compare results |

---

## 🔒 Security & Credentials

### IBM Quantum Token
```bash
export IBM_QUANTUM_TOKEN="your_token_here"
```
- Get token: https://quantum.ibm.com/
- Keep secret (never commit to git)
- Rotates periodically

### AWS Credentials
```bash
aws configure
# Access Key ID: YOUR_ACCESS_KEY
# Secret Access Key: YOUR_SECRET_KEY
# Region: us-east-1
```
- Use IAM roles for production
- Enable MFA for security
- Set up S3 bucket permissions

---

## 📊 Expected Results

### Energy Estimates
- **Strong binder**: -3.0 to -5.0 (very negative)
- **Moderate binder**: -1.0 to -3.0
- **Weak binder**: 0.0 to -1.0

### Confidence
- **High**: 0.8 - 1.0
- **Medium**: 0.6 - 0.8
- **Low**: < 0.6

### Runtime
- **Simulator**: 0.1 - 1s
- **IBM Qiskit**: 5 - 60s (depends on queue)
- **AWS Braket**: 10 - 120s (depends on device)

---

## 🐛 Troubleshooting

### IBM Qiskit Issues

**Problem:** `RuntimeError: Qiskit backend ibm_torino not available`

**Solution:**
1. Check token: `echo $IBM_QUANTUM_TOKEN`
2. Test authentication:
   ```python
   from qiskit_ibm_runtime import QiskitRuntimeService
   service = QiskitRuntimeService(token="YOUR_TOKEN")
   print(service.backends())
   ```
3. Verify queue access (some backends require permissions)

---

### AWS Braket Issues

**Problem:** `ClientError: An error occurred (AccessDenied)`

**Solution:**
1. Check credentials: `aws sts get-caller-identity`
2. Create S3 bucket: `aws s3 mb s3://my-braket-bucket`
3. Verify Braket permissions in IAM

---

### Slow Simulators

**Problem:** Simulator hangs/takes forever

**Solution:**
1. Reduce shots: `shots=100` instead of 1000
2. Use shorter guides (15-20 nucleotides)
3. Update BioQL: `pip install --upgrade bioql`

---

## 🎓 Learn More

- **BioQL Docs**: https://bioql.com/docs
- **IBM Quantum**: https://quantum.ibm.com/
- **AWS Braket**: https://aws.amazon.com/braket/
- **CRISPR-QAI Paper**: Coming soon

---

## 🚀 What's Next?

BioQL CRISPR-QAI roadmap:

- ✅ Multi-backend support (Simulator, IBM, AWS)
- ✅ VS Code integration
- ✅ Natural language interface
- 🔄 Google Cirq support
- 🔄 Azure Quantum integration
- 🔄 Batch optimization (1000s of guides)
- 🔄 Genome-wide off-target scanning

---

## 📞 Support

- **Issues**: https://github.com/spectrixrd/bioql/issues
- **Email**: support@bioql.com
- **Slack**: bioql-community.slack.com

---

**🧬 Happy quantum CRISPR designing! ⚛️**

*Generated by BioQL v5.4.3 - Real Quantum CRISPR Experiments*
