# Quantum-AI Modal Template (BioQL + Quillow + QPharos + Qiskit)

This template gives you:
- A GPU sanity-check training job on Modal (PyTorch).
- A Bell-state demo with Qiskit (local Aer or IBM Runtime).
- Safe stubs for BioQL, Quillow and QPharos with graceful fallbacks.
- A small adapter layer for quantum backends to keep app code clean.

## 1) Prerequisites
- Python 3.10+
- Modal CLI (`pip install modal`) and login: `modal token new`
- GPU quota on Modal (e.g., A10G / A100)
- Optional secrets:
  - `BIOQL_API_KEY`
  - `IBM_QUANTUM_API_KEY`
  - `QPHAROS_API_KEY`

## 2) Quickstart

Local optional test:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import torch; print(torch.cuda.is_available())"
```

Run on Modal:
```bash
# Full smoke test (GPU + Qiskit + stubs)
modal run modal_app.py::main

# Individually:
modal run modal_app.py::train_model
modal run modal_app.py::qiskit_hello_world --backend local
modal run modal_app.py::qiskit_hello_world --backend ibm --ibm_backend ibm_brisbane
modal run modal_app.py::bioql_demo
modal run modal_app.py::quillow_demo
modal run modal_app.py::qpharos_demo
```

Deploy (optional):
```bash
modal deploy modal_app.py
```

## 3) Secrets (optional)
Local:
```bash
export BIOQL_API_KEY="bioql_..."
export IBM_QUANTUM_API_KEY="ibm-..."
export QPHAROS_API_KEY="qp_..."
```
On Modal:
```bash
modal secret create bioql-secrets BIOQL_API_KEY=bioql_...
modal secret create ibm-quantum-secrets IBM_QUANTUM_API_KEY=ibm-...
modal secret create qpharos-secrets QPHAROS_API_KEY=qp_...
```

## 4) Next steps
- Replace placeholder calls in `backends.py` for BioQL/Quillow/QPharos with real client APIs.
- Add your research tasks (VQE, QAOA, chemistry) and wire Quillow QEC to them.
- Log results to W&B/MLflow and store artifacts on Modal volumes.
