#!/usr/bin/env bash

# Bootstrap script for quantum_ai_modal project

set -e

PROJECT_DIR="quantum_ai_modal"

echo "[info] Bootstrapping ${PROJECT_DIR}/ structure"

if [ -d "${PROJECT_DIR}" ]; then
  echo "[info] Removing existing ${PROJECT_DIR}/"
  rm -rf "${PROJECT_DIR}"
fi

echo "[info] Creating directories"
mkdir -p "${PROJECT_DIR}"

write_file() {
  local path="$1"
  local content="$2"
  mkdir -p "$(dirname "${path}")"
  cat > "${path}" <<'EOF'
EOF
}

echo "[info] Writing README.md"
cat > "${PROJECT_DIR}/README.md" <<'EOF'
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
EOF

echo "[info] Writing requirements.txt"
cat > "${PROJECT_DIR}/requirements.txt" <<'EOF'
# Core runtime
modal>=0.62.0
python-dotenv>=1.0.1

# DL / GPU
torch>=2.3.0
numpy>=1.26.0

# Qiskit stack
qiskit>=1.1.0
qiskit-ibm-runtime>=0.25.0
qiskit-aer>=0.14.0

# Domain libs (pinned for safety)
bioql>=5.3
quillow==1.0.0
qpharos==1.1.0
EOF

echo "[info] Writing .env.example"
cat > "${PROJECT_DIR}/.env.example" <<'EOF'
# Copy to .env and fill with your secrets for local testing
BIOQL_API_KEY=
IBM_QUANTUM_API_KEY=
QPHAROS_API_KEY=
EOF

echo "[info] Writing backends.py"
cat > "${PROJECT_DIR}/backends.py" <<'EOF'
from __future__ import annotations

import os
from typing import Any, Dict

# Qiskit Bell-state helper
from qiskit import QuantumCircuit


def _build_bell_circuit() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def run_qiskit_local() -> Dict[str, Any]:
    """Run a Bell-state circuit locally with Aer if available."""
    qc = _build_bell_circuit()
    try:
        from qiskit_aer.primitives import Sampler as AerSampler

        sampler = AerSampler()
        job = sampler.run(qc, shots=2048)
        result = job.result()
        if hasattr(result, "quasi_dists"):
            dist = result.quasi_dists[0]
            return {"backend": "aer_sampler", "distribution": dict(dist)}
        return {"backend": "aer_sampler", "result": str(result)}
    except Exception as e_sampler:
        try:
            from qiskit_aer import Aer
            from qiskit import transpile

            backend = Aer.get_backend("qasm_simulator")
            tqc = transpile(qc, backend)
            result = backend.run(tqc, shots=2048).result()
            counts = result.get_counts()
            return {"backend": "aer_qasm", "counts": counts}
        except Exception as e_legacy:
            return {"error": f"Aer not available: {e_sampler} / {e_legacy}"}


def run_qiskit_ibm(backend_name: str = "ibm_brisbane") -> Dict[str, Any]:
    """Run on IBM Qiskit Runtime using IBM_QUANTUM_API_KEY."""
    token = os.getenv("IBM_QUANTUM_API_KEY")
    if not token:
        return {"error": "IBM_QUANTUM_API_KEY not set"}
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler
    except Exception as e:
        return {"error": f"qiskit_ibm_runtime not available: {e}"}
    qc = _build_bell_circuit()
    try:
        service = QiskitRuntimeService(channel="ibm_cloud", token=token)
        with Session(service=service, backend=backend_name) as session:
            sampler = Sampler(session=session)
            job = sampler.run([qc], shots=2048)
            result = job.result()
        if hasattr(result, "quasi_dists"):
            qd = result.quasi_dists[0]
            return {"backend": backend_name, "distribution": dict(qd)}
        return {"backend": backend_name, "result": str(result)}
    except Exception as e:
        return {"error": f"IBM Runtime error: {e}"}


def quillow_demo(distance: int = 3, rounds: int = 5, p_error: float = 1e-3) -> Dict[str, Any]:
    """Small Quillow demo with safe fallbacks."""
    try:
        import quillow  # noqa
        from quillow import SurfaceCodeSimulator, MWPMDecoder
    except Exception as e:
        return {"error": f"Quillow not importable: {e}"}
    try:
        sim = SurfaceCodeSimulator(distance=distance, rounds=rounds, p_error=p_error)  # placeholder
        raw = sim.run(shots=128)  # placeholder API
        dec = MWPMDecoder(distance=distance)
        est = getattr(dec, "estimate_logical_error", None)
        val = float(est(raw)) if callable(est) else 0.0
        return {"distance": distance, "rounds": rounds, "estimated_logical_error": val}
    except Exception as e:
        return {"warning": f"Quillow demo path failed (API mismatch?). Detail: {e}"}


def bioql_demo() -> Dict[str, Any]:
    """Minimal BioQL example. Replace with your real client calls."""
    try:
        import bioql
    except Exception as e:
        return {"error": f"bioql not importable: {e}"}
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        return {"error": "BIOQL_API_KEY not set"}
    try:
        if hasattr(bioql, "Client"):
            client = bioql.Client(api_key=api_key)  # placeholder
            resp = {"status": "ok", "note": "Replace placeholder with real BioQL SDK call"}
            return {"bioql": resp}
        else:
            return {"warning": "bioql.Client not found; update to real API"}
    except Exception as e:
        return {"error": f"BioQL call failed: {e}"}


def qpharos_demo() -> Dict[str, Any]:
    """Minimal QPharos example. Replace with your real client calls."""
    try:
        import qpharos
    except Exception as e:
        return {"error": f"qpharos not importable: {e}"}
    api_key = os.getenv("QPHAROS_API_KEY")
    if not api_key:
        return {"error": "QPHAROS_API_KEY not set"}
    try:
        Client = getattr(qpharos, "Client", None)
        if Client:
            client = Client(api_key=api_key)  # placeholder
            resp = {"status": "ok", "note": "Replace placeholder with real QPharos SDK call"}
            return {"qpharos": resp}
        else:
            return {"warning": "qpharos.Client not found; update to real API"}
    except Exception as e:
        return {"error": f"QPharos call failed: {e}"}
EOF

echo "[info] Writing modal_app.py"
cat > "${PROJECT_DIR}/modal_app.py" <<'EOF'
from __future__ import annotations

import json
from typing import Optional

import modal

# Build image with pinned deps
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.3.0",
        "numpy>=1.26.0",
        "qiskit>=1.1.0",
        "qiskit-ibm-runtime>=0.25.0",
        "qiskit-aer>=0.14.0",
        "bioql>=5.3",
        "quillow==1.0.0",
        "qpharos==1.1.0",
    )
)

stub = modal.Stub("quantum_ai_modal", image=image)

# Optional: mount Modal secrets if you created them
# bioql_secret = modal.Secret.from_name("bioql-secrets")
# ibm_secret = modal.Secret.from_name("ibm-quantum-secrets")
# qpharos_secret = modal.Secret.from_name("qpharos-secrets")


def _pp(x):
    print(json.dumps(x, indent=2, default=str))


@stub.function(gpu="A10G", timeout=900)
def train_model(steps: int = 2000, batch: int = 256):
    """Minimal PyTorch GPU sanity check: trains a tiny MLP on random data."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}  (CUDA={torch.cuda.is_available()})")

    class TinyNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(128, 256)
            self.fc2 = nn.Linear(256, 2)

        def forward(self, x):
            x = F.relu(self.fc1(x))
            return self.fc2(x)

    model = TinyNet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)

    for step in range(steps):
        x = torch.randn(batch, 128, device=device)
        y = (x.sum(dim=1) > 0).long()  # fake binary label
        logits = model(x)
        loss = F.cross_entropy(logits, y)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % 200 == 0:
            print(f"step {step:04d} | loss {loss.item():.4f}")

    total_norm = 0.0
    with torch.no_grad():
        for p in model.parameters():
            total_norm += p.norm().item()
    return {"status": "ok", "weights_l2_norm": total_norm}


@stub.function(timeout=600)
def qiskit_hello_world(backend: str = "local", ibm_backend: Optional[str] = None):
    """Run a Bell-state job on local Aer or IBM Runtime."""
    from backends import run_qiskit_local, run_qiskit_ibm

    if backend == "local":
        result = run_qiskit_local()
    elif backend == "ibm":
        name = ibm_backend or "ibm_brisbane"
        result = run_qiskit_ibm(name)
    else:
        result = {"error": f"Unknown backend '{backend}'"}

    _pp(result)
    return result


@stub.function(timeout=600)
def quillow_demo():
    from backends import quillow_demo as _demo

    res = _demo()
    _pp(res)
    return res


@stub.function(timeout=600)
def bioql_demo():
    from backends import bioql_demo as _demo

    res = _demo()
    _pp(res)
    return res


@stub.function(timeout=600)
def qpharos_demo():
    from backends import qpharos_demo as _demo

    res = _demo()
    _pp(res)
    return res


@stub.local_entrypoint()
def main():
    """Local orchestrator: calls remote functions for a full smoke test."""
    train_out = train_model.call(steps=400, batch=128)
    print("\n[train_model]")
    _pp(train_out)

    print("\n[qiskit_hello_world local]")
    _pp(qiskit_hello_world.call(backend="local"))

    print("\n[qiskit_hello_world ibm]")
    _pp(qiskit_hello_world.call(backend="ibm", ibm_backend="ibm_brisbane"))

    print("\n[quillow_demo]")
    _pp(quillow_demo.call())

    print("\n[bioql_demo]")
    _pp(bioql_demo.call())

    print("\n[qpharos_demo]")
    _pp(qpharos_demo.call())
EOF

echo ""
echo "NEXT STEPS"
echo "1) cd quantum_ai_modal"
echo "2) (optional) python -m venv .venv && source .venv/bin/activate"
echo "3) pip install -r requirements.txt"
echo "4) modal token new"
echo "5) modal run modal_app.py::main"
