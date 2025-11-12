# BioQL - AWS Braket Examples

This directory contains complete examples and setup scripts for using BioQL with Amazon Braket quantum computing service.

## 📁 Files

### Setup & Configuration
- **`setup_braket.sh`** - Complete automated setup script for AWS Braket
- **`braket_instructions.md`** - Detailed instructions and troubleshooting guide
- **`QUICK_START.md`** - Quick reference guide

### Documentation
- **`bioql_braket_integration.md`** - Complete integration guide with BioQL 5.0.0
- **`AWS_BRAKET_SUCCESS.md`** - Verified results and success metrics

### Example Circuits
- **`bell.qasm`** - Bell state circuit (quantum entanglement demonstration)

## 🚀 Quick Start

### 1. Install BioQL
```bash
pip install bioql
```

### 2. Copy Examples to Your Home Directory
```python
import bioql
import shutil
from pathlib import Path

# Get examples directory
examples_dir = Path(bioql.__file__).parent / 'examples' / 'aws_braket'

# Copy to home
import os
home = Path.home()
shutil.copytree(examples_dir, home / 'bioql-braket-examples')

print(f"Examples copied to: {home / 'bioql-braket-examples'}")
```

### 3. Run Setup Script
```bash
~/bioql-braket-examples/setup_braket.sh
```

## 📋 Prerequisites

- **AWS Account** with Braket access
- **AWS CLI** installed (`brew install awscli` or `pip install awscli`)
- **AWS Credentials** (Access Key + Secret Key)
- **Python 3.9+** with BioQL installed

## 🔬 What's Included

### Automated Setup Script
The `setup_braket.sh` script will:
1. ✅ Configure AWS CLI profile (`braket-dev`)
2. ✅ Verify AWS credentials
3. ✅ Create S3 bucket for results
4. ✅ List available Braket devices
5. ✅ Create and execute Bell state circuit
6. ✅ Download and analyze results
7. ✅ Verify quantum entanglement (100%)

### Expected Results
- **|00⟩**: ~50% probability
- **|11⟩**: ~50% probability
- **|01⟩**: 0% (forbidden by entanglement)
- **|10⟩**: 0% (forbidden by entanglement)
- **Entanglement**: 100% confirmed ✅

## 💰 Cost

- **SV1 Simulator**: Free (AWS Free Tier - 1 hour/month)
- **S3 Storage**: ~$0.00001 per task
- **Total for examples**: < $0.01 USD

## 📚 Learn More

- **AWS Braket Docs**: https://docs.aws.amazon.com/braket/
- **BioQL Docs**: https://pypi.org/project/bioql/
- **OpenQASM 3.0**: https://openqasm.com/

## 🎯 Next Steps

After running the setup script, try:

1. **GHZ State (3 qubits)** - See `braket_instructions.md`
2. **Quantum Teleportation** - Advanced entanglement
3. **VQE for H2** - Quantum chemistry with BioQL
4. **Grover Search** - Quantum database search
5. **Real QPU** - IonQ Harmony or Rigetti devices

## ⚠️ Important Notes

- S3 bucket name **must** start with `amazon-braket-` (AWS requirement)
- Ensure your AWS user has `AmazonBraketFullAccess` permissions
- SV1 tasks complete in 1-3 seconds
- QPU tasks may take several minutes and cost ~$0.30-10 per task

## 🆘 Troubleshooting

See `braket_instructions.md` for complete troubleshooting guide.

Common issues:
- **"bucket does not start with 'amazon-braket-'"** → Use correct prefix
- **"AccessDeniedException"** → Add Braket permissions to IAM user
- **"Credentials invalid"** → Run `aws configure --profile braket-dev`

---

**✅ Ready to explore quantum computing with AWS Braket + BioQL!**

For questions or issues, visit: https://github.com/bioql/bioql/issues
