"""
modal_quantum_bridge.py — Flask dispatcher: HEAVY quantum -> NVIDIA GPUs (Modal or Brev).

This blueprint routes quantum workloads the local Mac cannot handle to the app
"bioql-quantum-gpu" (see modal_quantum_gpu.py), on Modal or on the Brev job
server that runs the same app bodies -- modal_compute_layer picks per call
(BIOQL_COMPUTE_PREFER, default by health) and every result says where it ran.
It never imports cudaq / pennylane locally; those live exclusively inside the
GPU images.

Routing policy (advertised at GET /api/quantum/gpu/health):
  * tensornet MPS  (≤ thousands of qubits, bounded entanglement) -> local first
    via /api/quantum/mps, else this GPU /api/quantum/gpu/tensornet
  * statevector    ≤ 29 qubits -> run locally (Aer); ≥ 30 qubits -> GPU
  * VQE / 30-40 qubit exact     -> GPU

Every remote call is wrapped so that a missing, unauthenticated, or otherwise
unavailable backend never crashes the server — failures degrade to a JSON error
with a deploy hint. GET /api/compute/backends shows both backends at a glance.

Register from the main app with:  register_modal_quantum_routes(app)

Copyright (c) 2026 MOLEVERA / BIOQL. All rights reserved.
"""

from __future__ import annotations

import logging
import os

from flask import Blueprint, jsonify, request
from modal_retry import call_modal_with_retry

log = logging.getLogger("modal_quantum_bridge")
modal_quantum_bp = Blueprint("bioql_modal_quantum", __name__)

_CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:3000")

MODAL_APP_NAME = "bioql-quantum-gpu"
DEPLOY_HINT = "deploy with: modal deploy src/backend/modal_quantum_gpu.py"
# Local statevector ceiling — above this we must offload to GPU.
LOCAL_STATEVECTOR_MAX_QUBITS = 29


def attach_cudaq_recovery_request(result, workload: str, request_payload: dict):
    """Make a failed CUDA-Q result automatically rerunnable by the supervisor."""
    if isinstance(result, dict) and result.get("success") is False:
        result["cudaq_recovery_request"] = {
            "workload": str(workload),
            **dict(request_payload or {}),
        }
    return result


def _enqueue_failed_cudaq(result, workload: str):
    """Start background recovery immediately for direct CUDA-Q endpoint failures."""
    if not isinstance(result, dict) or result.get("success") is not False:
        return
    try:
        import uuid

        from active_cudaq_supervisor import enqueue_pipeline_review

        result["active_cudaq_review"] = enqueue_pipeline_review(
            {
                "cudaq_result": result,
                "cudaq_recovery_request": result.get("cudaq_recovery_request"),
            },
            pipeline=f"cudaq_{workload}",
            session_id=f"cudaq-{workload}-{uuid.uuid4().hex[:12]}",
        )
    except Exception as exc:
        result["active_cudaq_review"] = {
            "enqueued": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _cors(resp):
    resp.headers.add("Access-Control-Allow-Origin", _CORS_ORIGIN)
    resp.headers.add("Access-Control-Allow-Headers", "*")
    resp.headers.add("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    return resp


def _modal_available():
    """Return (modal_module_or_None, error_message_or_None). Never raises."""
    try:
        import modal  # noqa: F401

        return modal, None
    except Exception as e:  # pragma: no cover - import guard
        return None, f"modal SDK not importable: {type(e).__name__}: {e}"


def _call_modal_function(fn_name: str, *args, **kwargs):
    """Look up a deployed Modal function and call .remote(...) with
    retry/backoff (modal_retry.call_modal_with_retry). Never raises.

    Returns the function result on success, or a JSON-safe error dict
    {"success": False, "error": ..., "hint": ...} on any failure (missing SDK,
    unauthenticated, app not deployed, runtime error, or retries exhausted).
    """
    modal, err = _modal_available()
    if modal is None:
        return {"success": False, "error": err, "hint": DEPLOY_HINT}

    retry_result = call_modal_with_retry(MODAL_APP_NAME, fn_name, *args, **kwargs)
    if not retry_result.get("success"):
        return {
            "success": False,
            "error": retry_result.get("error"),
            "attempts": retry_result.get("attempts"),
            "transient": retry_result.get("transient"),
            "hint": DEPLOY_HINT,
        }

    result = retry_result["result"]
    if isinstance(result, dict):
        result.setdefault("success", True)
        result.setdefault("attempts", retry_result.get("attempts"))
        result.setdefault("where_it_ran", retry_result.get("backend"))
        return result
    return {
        "success": True,
        "result": result,
        "attempts": retry_result.get("attempts"),
        "where_it_ran": retry_result.get("backend"),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@modal_quantum_bp.route("/api/quantum/gpu/statevector", methods=["POST", "OPTIONS"])
def api_gpu_statevector():
    """Dispatch exact statevector (30-40 qubit) to Modal cudaq_statevector.

    Body: {"spec": {...} | "qasm": "...", "shots": 1000}
    """
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    data = request.get_json(silent=True) or {}
    payload = data.get("spec", data.get("qasm"))
    if payload is None:
        return (
            _cors(
                jsonify(
                    {
                        "success": False,
                        "error": "provide 'spec' (circuit dict) or 'qasm' (string)",
                    }
                )
            ),
            400,
        )
    shots = int(data.get("shots", 1000))
    result = _call_modal_function("cudaq_statevector", payload, shots)
    attach_cudaq_recovery_request(result, "statevector", {"spec": payload, "shots": shots})
    _enqueue_failed_cudaq(result, "statevector")
    return _cors(jsonify(result))


@modal_quantum_bp.route("/api/quantum/gpu/tensornet", methods=["POST", "OPTIONS"])
def api_gpu_tensornet():
    """Dispatch MPS tensor-network sim (thousands of qubits) to cudaq_tensornet_mps.

    Body: {"n_qubits": 1000 | "spec": {...}, "shots": 100, "max_bond": 64}
    """
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    data = request.get_json(silent=True) or {}
    spec = data.get("spec", data.get("n_qubits", 1000))
    shots = int(data.get("shots", 100))
    max_bond = int(data.get("max_bond", 64))
    result = _call_modal_function("cudaq_tensornet_mps", spec, shots, max_bond)
    attach_cudaq_recovery_request(
        result,
        "tensornet",
        {"spec": spec, "shots": shots, "max_bond": max_bond},
    )
    _enqueue_failed_cudaq(result, "tensornet")
    return _cors(jsonify(result))


@modal_quantum_bp.route("/api/quantum/gpu/vqe", methods=["POST", "OPTIONS"])
def api_gpu_vqe():
    """Dispatch VQE ground-state energy to Modal cudaq_vqe.

    Body: {"hamiltonian_terms": [...], "ansatz_params": {...}}
    Empty body runs the default H2 Hamiltonian.
    """
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    data = request.get_json(silent=True) or {}
    hamiltonian_terms = data.get("hamiltonian_terms")
    ansatz_params = data.get("ansatz_params")
    result = _call_modal_function("cudaq_vqe", hamiltonian_terms, ansatz_params)
    attach_cudaq_recovery_request(
        result,
        "vqe",
        {"hamiltonian_terms": hamiltonian_terms, "ansatz_params": ansatz_params},
    )
    _enqueue_failed_cudaq(result, "vqe")
    return _cors(jsonify(result))


@modal_quantum_bp.route("/api/quantum/gpu/molecular-vqe-rdm", methods=["POST", "OPTIONS"])
def api_gpu_molecular_vqe_rdm():
    """Dispatch a typed molecular Hamiltonian/1-RDM/force contract to Modal."""
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    contract = request.get_json(silent=True) or {}
    result = _call_modal_function("cudaq_molecular_vqe_rdm", contract)
    return _cors(jsonify(result))


@modal_quantum_bp.route("/api/quantum/gpu/pennylane", methods=["POST", "OPTIONS"])
def api_gpu_pennylane():
    """Dispatch large variational circuit to Modal pennylane_gpu_circuit.

    Body: {"n_qubits": 24, "params": [...]}
    """
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    data = request.get_json(silent=True) or {}
    n_qubits = int(data.get("n_qubits", 24))
    params = data.get("params")
    result = _call_modal_function("pennylane_gpu_circuit", n_qubits, params)
    return _cors(jsonify(result))


@modal_quantum_bp.route("/api/quantum/gpu/health", methods=["GET", "OPTIONS"])
def api_gpu_health():
    """Report where the quantum GPU app can run (Modal, Brev) and the routing policy.

    `deployed` used to come from a bare `Function.from_name`, which is lazy in
    modal >=1.x and never fails -- it reported True for anything. It is now a
    real hydrate on Modal, and Brev is judged by its job server's own list.
    """
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    import brev_client
    import modal_compute_layer as mcl

    modal, err = _modal_available()
    sdk_importable = modal is not None
    modal_version = None
    deployed = False
    deploy_check = "sdk_unavailable"

    if sdk_importable and not mcl.modal_enabled():
        deploy_check = "disabled by BIOQL_MODAL_ENABLED=0"
    elif sdk_importable:
        modal_version = getattr(modal, "__version__", "unknown")
        try:
            mcl._modal_target(MODAL_APP_NAME, "cudaq_statevector")
            deployed = True
            deploy_check = "function_hydrated"
        except Exception as e:
            deployed = False
            deploy_check = f"lookup_failed: {type(e).__name__}: {e}"
    brev_serves = brev_client.serves(MODAL_APP_NAME, "cudaq_statevector")

    return _cors(
        jsonify(
            {
                "success": True,
                "modal_sdk_importable": sdk_importable,
                "modal_sdk_error": err,
                "modal_version": modal_version,
                "app_name": MODAL_APP_NAME,
                "deployed": deployed,
                "deploy_check": deploy_check,
                "brev_serves": brev_serves,
                "compute": mcl.status(),
                "deploy_command": "modal deploy src/backend/modal_quantum_gpu.py",
                # The @app.function names in modal_quantum_gpu.py (checked 2026-09-24).
                "functions": [
                    "cudaq_statevector",
                    "cudaq_tensornet_mps",
                    "cudaq_tensornet_mps_max",
                    "cudaq_vqe",
                    "cudaq_molecular_vqe_rdm",
                    "pennylane_gpu_circuit",
                    "cudaq_algorithms",
                    "cudaq_qubo_qaoa",
                    "cudaq_nmr_spectrum",
                    "cudaq_grover_argmax",
                ],
                "endpoints": {
                    "statevector": "/api/quantum/gpu/statevector",
                    "tensornet": "/api/quantum/gpu/tensornet",
                    "vqe": "/api/quantum/gpu/vqe",
                    "pennylane": "/api/quantum/gpu/pennylane",
                },
                "routing_policy": {
                    "tensornet_mps": "local first via /api/quantum/mps (≤ thousands of "
                    "qubits, bounded entanglement); else GPU /api/quantum/gpu/tensornet",
                    "statevector": f"≤ {LOCAL_STATEVECTOR_MAX_QUBITS} qubits run locally "
                    "(Aer); ≥ 30 qubits dispatch to GPU /api/quantum/gpu/statevector",
                    "vqe": "30-40 qubit / heavy VQE -> GPU /api/quantum/gpu/vqe",
                    "pennylane": "large variational circuits (24+ qubits) -> GPU",
                },
                "local_statevector_max_qubits": LOCAL_STATEVECTOR_MAX_QUBITS,
            }
        )
    )


@modal_quantum_bp.route("/api/compute/backends", methods=["GET", "OPTIONS"])
def api_compute_backends():
    """Both remote backends at a glance: policy, Modal flags, Brev job-server
    health (GPU, loaded functions, free slots) and any backend cooling down."""
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    import modal_compute_layer as mcl

    return _cors(jsonify({"success": True, **mcl.status()}))


def register_modal_quantum_routes(app):
    """Register the Modal quantum-GPU dispatcher blueprint on a Flask app."""
    app.register_blueprint(modal_quantum_bp)
    log.info("Modal quantum-GPU dispatcher routes registered (/api/quantum/gpu/*)")
