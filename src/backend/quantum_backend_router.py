"""quantum_backend_router.py — walk the substrate chain and label the result honestly.

WHY THIS FILE DID NOT EXIST, AND WHY THAT MATTERED
    `quantum_fallback_runners` builds an ordered dict of substrate runners and
    hands it to `execute_with_fallback` from this module. This module was
    missing. Four call sites imported it and every one of them failed:

        quantum_fallback_runners.py:488, :715
        antibody_discovery_engine.py:316, :340

    The ImportError was caught, and each caller fell through to its own legacy
    path — which, in every case, went straight to IBM. So the modern chain
    (CUDA-Q GPU -> MPS -> Aer) was never walked at all, and a platform that had
    moved off IBM kept opening connections to it.

    MEASURED 2026-09-17, one PBPK dose derivation:
        'Shared QPU-first sampler failed (No module named quantum_backend_router);
         trying legacy IBM'
        'Unable to retrieve instances. Please check that you are using a valid
         API token.'
    Three stages, three dead handshakes, 68 seconds for a calculation that takes
    6 seconds on the classical path.

THE HONESTY INVARIANT THIS ENFORCES
    `is_real_hardware` is True ONLY when a real provider job id came back AND
    the mode that produced it is a hardware mode. A simulator result is never
    labelled as hardware, no matter which substrate it fell through from. That
    invariant is the reason this router exists rather than each engine labelling
    its own results.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Modes that represent execution on a real device. Everything else is a
# simulator, however faithful.
HARDWARE_MODES = frozenset({"ibm_hardware", "openquantum_hardware",
                            "rigetti_hardware", "qpu"})

# What each mode actually is, for the provenance block. A reader should never
# have to guess whether "mps" was a device.
SUBSTRATE_LABELS: Dict[str, str] = {
    "ibm_hardware": "IBM Quantum hardware",
    "openquantum_hardware": "OpenQuantum hardware",
    "cudaq_gpu": "CUDA-Q GPU statevector (simulation)",
    "mps": "Matrix-product-state simulator (simulation)",
    "aer": "Qiskit Aer statevector (simulation, local CPU)",
}

_JOB_ID_KEYS = ("ibm_job_id", "job_id", "provider_job_id", "task_id")


def _first_job_id(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for k in _JOB_ID_KEYS:
        v = payload.get(k)
        if isinstance(v, str) and v.strip() and not v.strip().lower().startswith("sim"):
            return v.strip()
    return None


def resolve_quantum_backend(prefer: str = "aer", **_: Any) -> Dict[str, Any]:
    """Describe the backend a caller should expect, before anything has run.

    Deliberately conservative: it reports a simulator unless hardware has been
    explicitly enabled. A pre-run guess that claims hardware and then falls back
    is how a simulated result acquires a hardware label.
    """
    want = (prefer or "aer").strip().lower()
    ibm_on = os.environ.get("BIOQL_ENABLE_IBM", "0").lower() in {"1", "true", "on"}
    if want.startswith("ibm") and ibm_on:
        mode = "ibm_hardware"
    elif want.startswith("openquantum"):
        mode = "openquantum_hardware"
    else:
        mode = "aer"
    return {
        "mode": mode,
        "backend_name": "aer_simulator" if mode == "aer" else mode,
        # Never True before execution: nothing has produced a job id yet.
        "is_real_hardware": False,
        "ibm_available": ibm_on,
        "substrate": SUBSTRATE_LABELS.get(mode, mode),
        "reason": ("pre-run resolution; the executed backend is whatever "
                   "execute_with_fallback actually reaches"),
    }


def stamp_quantum_provenance(result: Dict[str, Any],
                             backend_info: Dict[str, Any],
                             job_id: Optional[str] = None) -> Dict[str, Any]:
    """Attach the honest provenance block to a result. Never raises."""
    info = backend_info if isinstance(backend_info, dict) else {}
    mode = str(info.get("mode") or "aer")
    jid = job_id or _first_job_id(result) or _first_job_id(info)
    real = bool(jid) and mode in HARDWARE_MODES

    prov = {
        "mode": mode,
        "backend": info.get("backend_name") or info.get("backend") or mode,
        "substrate": info.get("substrate") or SUBSTRATE_LABELS.get(mode, mode),
        "is_real_hardware": real,
        "job_id": jid if real else None,
        "ibm_job_id": jid if (real and mode == "ibm_hardware") else None,
        "honesty_note": (
            "is_real_hardware is True only when a provider job id came back AND "
            "the mode that produced it is a hardware mode."
        ),
    }
    if not real and jid:
        prov["unverified_job_id"] = jid
        prov["unverified_reason"] = (
            "A job id was present but mode %r is a simulator; the result is not "
            "labelled as hardware." % mode
        )
    if isinstance(result, dict):
        result["quantum_provenance"] = prov
    return prov


def execute_with_fallback(runners: Dict[str, Callable[[], Dict[str, Any]]],
                          *,
                          n_qubits: int = 0,
                          kind: str = "sampling",
                          est_qpu_seconds: float = 2.0,
                          shots: int = 1024,
                          ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Try each runner in order; return the first success with honest provenance.

    `runners` is an ORDERED mapping {mode: callable}. A runner raises on
    failure; this walks past it. Returns (result, provenance). `result` is None
    only when every substrate failed — real-or-null, never a fabricated result.
    Never raises.
    """
    attempts = []
    for mode, run in (runners or {}).items():
        t0 = time.time()
        try:
            payload = run()
        except Exception as exc:  # noqa: BLE001 — walking the chain is the point
            attempts.append({"mode": mode, "ok": False,
                             "error": "%s: %s" % (type(exc).__name__, str(exc)[:160]),
                             "seconds": round(time.time() - t0, 3)})
            logger.info("[router] %s failed (%s); trying next substrate", mode, exc)
            continue

        if not isinstance(payload, dict):
            attempts.append({"mode": mode, "ok": False,
                             "error": "runner returned %s, not a dict" % type(payload).__name__,
                             "seconds": round(time.time() - t0, 3)})
            continue

        attempts.append({"mode": mode, "ok": True,
                         "seconds": round(time.time() - t0, 3)})
        info = {
            "mode": mode,
            "backend_name": payload.get("backend") or mode,
            "substrate": SUBSTRATE_LABELS.get(mode, mode),
        }
        prov = stamp_quantum_provenance(payload, info)
        prov.update({
            "kind": kind,
            "n_qubits": int(n_qubits or 0),
            "shots": int(shots or 0),
            "attempts": attempts,
            "substrates_tried": [a["mode"] for a in attempts],
        })
        payload["quantum_provenance"] = prov
        return payload, prov

    # Everything failed. Say so; do not invent counts.
    prov = {
        "mode": None,
        "backend": None,
        "is_real_hardware": False,
        "job_id": None,
        "kind": kind,
        "n_qubits": int(n_qubits or 0),
        "shots": int(shots or 0),
        "attempts": attempts,
        "substrates_tried": [a["mode"] for a in attempts],
        "error": "every substrate failed",
        "honesty_note": ("No result is returned rather than a simulated one "
                         "labelled as something else."),
    }
    logger.warning("[router] every substrate failed: %s",
                   [a.get("error") for a in attempts])
    return None, prov


def resolve_with_fallback(*_: Any, **__: Any) -> Dict[str, Any]:
    """Compatibility shim for callers that ask which backend to try first."""
    return resolve_quantum_backend(prefer=os.environ.get("BIOQL_PREFER_BACKEND", "aer"))
