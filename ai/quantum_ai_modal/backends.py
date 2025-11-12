# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

# Qiskit Bell-state helper
from qiskit import QuantumCircuit


def _maybe_bioql_client() -> Tuple[Optional[Any], Optional[str]]:
    try:
        import bioql  # type: ignore
    except Exception as exc:
        return None, f"bioql import error: {exc}"
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        return None, "BIOQL_API_KEY not set"
    client_cls = getattr(bioql, "Client", None)
    if client_cls is None:
        return None, "bioql.Client not available"
    try:
        client = client_cls(api_key=api_key)  # type: ignore[call-arg]
        return client, None
    except Exception as exc:
        return None, f"BioQL client init failed: {exc}"


def _maybe_qpharos_client() -> Tuple[Optional[Any], Optional[str]]:
    try:
        import qpharos  # type: ignore
    except Exception as exc:
        return None, f"qpharos import error: {exc}"
    api_key = os.getenv("QPHAROS_API_KEY")
    if not api_key:
        return None, "QPHAROS_API_KEY not set"
    client_cls = getattr(qpharos, "Client", None)
    if client_cls is None:
        return None, "qpharos.Client not available"
    try:
        client = client_cls(api_key=api_key)  # type: ignore[call-arg]
        return client, None
    except Exception as exc:
        return None, f"QPharos client init failed: {exc}"


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
            from qiskit import transpile
            from qiskit_aer import Aer

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
        return {
            "backend": backend_name,
            "distribution": {"00": 0.5, "11": 0.5},
            "note": "IBM_QUANTUM_API_KEY not set; returning mocked data",
        }
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Session
    except Exception as e:
        return {
            "backend": backend_name,
            "distribution": {"00": 0.5, "11": 0.5},
            "note": f"qiskit_ibm_runtime not available: {e}",
        }
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
        return {
            "backend": backend_name,
            "distribution": {"00": 0.5, "11": 0.5},
            "note": f"IBM Runtime unavailable: {e}",
        }


def quillow_demo(distance: int = 3, rounds: int = 5, p_error: float = 1e-3) -> Dict[str, Any]:
    """Small Quillow demo with safe fallbacks."""
    try:
        import quillow  # noqa
        from quillow import MWPMDecoder, SurfaceCodeSimulator
    except Exception as e:
        return {
            "demo": "quillow",
            "note": f"Quillow not importable; returning mocked data ({e})",
            "distance": distance,
            "rounds": rounds,
            "estimated_logical_error": 0.01,
        }
    try:
        # Some versions accept a noise model rather than p_error. Try the conservative subset.
        sim = SurfaceCodeSimulator(distance=distance, rounds=rounds)
        raw = sim.run(shots=128)
        dec = MWPMDecoder(distance=distance)
        est = getattr(dec, "estimate_logical_error", None)
        val = float(est(raw)) if callable(est) else 0.0
        return {"distance": distance, "rounds": rounds, "estimated_logical_error": val}
    except Exception as e:
        return {
            "demo": "quillow",
            "distance": distance,
            "rounds": rounds,
            "estimated_logical_error": 0.0123,
            "note": f"Quillow fallback due to API mismatch: {e}",
        }


def bioql_demo() -> Dict[str, Any]:
    """Minimal BioQL example. Replace with your real client calls."""
    try:
        import bioql
    except Exception as e:
        return {
            "bioql": {
                "status": "simulated",
                "note": f"bioql package not importable ({e}); returning mocked response",
            }
        }
    api_key = os.getenv("BIOQL_API_KEY")
    if not api_key:
        return {
            "bioql": {
                "status": "simulated",
                "note": "BIOQL_API_KEY not set; returning mocked response",
            }
        }
    try:
        if hasattr(bioql, "Client"):
            client = bioql.Client(api_key=api_key)  # type: ignore[attr-defined]
            _ = client  # placeholder so linting does not complain
            resp = {"status": "ok", "note": "Replace placeholder with real BioQL SDK call"}
            return {"bioql": resp}
        else:
            return {
                "bioql": {
                    "status": "simulated",
                    "note": "bioql.Client not found; returning mocked response",
                }
            }
    except Exception as e:
        return {
            "bioql": {
                "status": "simulated",
                "note": f"BioQL call failed; returning mocked response ({e})",
            }
        }


def qpharos_demo() -> Dict[str, Any]:
    """Minimal QPharos example. Replace with your real client calls."""
    try:
        import qpharos
    except Exception as e:
        return {
            "qpharos": {
                "status": "simulated",
                "note": f"qpharos not importable ({e}); returning mocked response",
            }
        }
    api_key = os.getenv("QPHAROS_API_KEY")
    if not api_key:
        return {
            "qpharos": {
                "status": "simulated",
                "note": "QPHAROS_API_KEY not set; returning mocked response",
            }
        }
    try:
        Client = getattr(qpharos, "Client", None)
        if Client:
            client = Client(api_key=api_key)  # type: ignore[attr-defined]
            _ = client
            return {
                "qpharos": {
                    "status": "ok",
                    "note": "Replace placeholder with real QPharos SDK call",
                }
            }
        else:
            return {
                "qpharos": {
                    "status": "simulated",
                    "note": "qpharos.Client not found; returning mocked response",
                }
            }
    except Exception as e:
        return {
            "qpharos": {
                "status": "simulated",
                "note": f"QPharos call failed; returning mocked response ({e})",
            }
        }


def bioql_configure_backend(
    backend: Optional[str],
    shots: Optional[int],
    post_check: Optional[str] = None,
) -> Dict[str, Any]:
    backend_name = backend or "ibm_toronto"
    shots_val = int(shots or 4096)
    client, note = _maybe_bioql_client()
    response: Dict[str, Any] = {
        "action": "bioql.configure_backend",
        "backend": backend_name,
        "shots": shots_val,
        "post_check": post_check,
        "status": "simulated",
    }
    if client is None:
        response["note"] = note or "BioQL unavailable; returning stub response."
        return response
    configure_fn = getattr(client, "configure_backend", None)
    if callable(configure_fn):
        try:
            result = configure_fn(backend=backend_name, shots=shots_val)  # type: ignore[call-arg]
            response["status"] = "ok"
            response["details"] = result
        except Exception as exc:
            response["note"] = f"BioQL configure failed: {exc}"
    else:
        response["note"] = "bioql.Client.configure_backend not implemented; stub."
    if post_check:
        status_fn = getattr(client, "status", None)
        if callable(status_fn):
            try:
                response["post_check_result"] = status_fn(post_check)
            except Exception as exc:
                response["post_check_result"] = {
                    "status": "simulated",
                    "note": f"Post-check failed: {exc}",
                    "check": post_check,
                }
    return response


def bioql_status_readiness() -> Dict[str, Any]:
    client, note = _maybe_bioql_client()
    action = "bioql.status.readiness"
    if client is None:
        return {
            "action": action,
            "status": "simulated",
            "note": note or "BioQL unavailable; returning stub readiness data.",
            "checks": {"health": "unknown", "queue_depth": None},
        }
    status_fn = getattr(client, "status", None)
    if callable(status_fn):
        try:
            readiness = status_fn("readiness")
            return {"action": action, "status": "ok", "details": readiness}
        except Exception as exc:
            return {
                "action": action,
                "status": "simulated",
                "note": f"BioQL readiness check failed: {exc}",
            }
    return {
        "action": action,
        "status": "simulated",
        "note": "bioql.Client.status unavailable; provide implementation.",
    }


def bioql_log_event(
    event: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    client, note = _maybe_bioql_client()
    response: Dict[str, Any] = {
        "action": "bioql.log_event",
        "event": event,
        "metadata": metadata,
        "status": "simulated",
    }
    if client is None:
        response["note"] = note or "BioQL unavailable; returning stub log result."
        return response
    log_fn = getattr(client, "log_event", None)
    if callable(log_fn):
        try:
            log_result = log_fn(event=event, metadata=metadata or {})  # type: ignore[call-arg]
            response["status"] = "ok"
            response["details"] = log_result
        except Exception as exc:
            response["note"] = f"BioQL log_event failed: {exc}"
    else:
        response["note"] = "bioql.Client.log_event not implemented; stub."
    return response


def bioql_set_mode(mode: Optional[str]) -> Dict[str, Any]:
    client, note = _maybe_bioql_client()
    response: Dict[str, Any] = {
        "action": "bioql.set_mode",
        "mode": mode,
        "status": "simulated",
    }
    if client is None:
        response["note"] = note or "BioQL unavailable; returning stub mode switch."
        return response
    mode_fn = getattr(client, "set_mode", None)
    if callable(mode_fn):
        try:
            result = mode_fn(mode=mode)  # type: ignore[call-arg]
            response["status"] = "ok"
            response["details"] = result
        except Exception as exc:
            response["note"] = f"BioQL set_mode failed: {exc}"
    else:
        response["note"] = "bioql.Client.set_mode not implemented; stub."
    return response


def bioql_execute_program(
    program: Optional[str],
    backend: Optional[str],
    shots: Optional[int],
    api_key: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    endpoint = "https://api.bioql.bio/api/quantum/execute"
    resolved_api_key = api_key or os.getenv("BIOQL_API_KEY")
    payload: Dict[str, Any] = {
        "program": program or "",
        "backend": backend or "simulator",
        "shots": int(shots or 1024),
    }
    if extra_payload:
        payload.update(extra_payload)
    response: Dict[str, Any] = {
        "action": "bioql.execute_program",
        "endpoint": endpoint,
        "backend": payload["backend"],
        "shots": payload["shots"],
        "program": payload["program"],
        "status": "simulated",
    }
    if not resolved_api_key:
        response["note"] = "BIOQL_API_KEY not set; request not sent."
        return response
    payload["api_key"] = resolved_api_key
    try:
        import httpx

        with httpx.Client(timeout=httpx.Timeout(45.0)) as client:
            http_response = client.post(endpoint, json=payload)
        response["http_status"] = http_response.status_code
        if http_response.headers.get("content-type", "").startswith("application/json"):
            try:
                response["result"] = http_response.json()
            except ValueError:
                response["result"] = http_response.text
        else:
            response["result"] = http_response.text
        response["status"] = "ok" if http_response.is_success else "error"
    except Exception as exc:
        response["note"] = f"BioQL execute request failed: {exc}"
    return response


def qpharos_list_calibrations(
    filters: Optional[Dict[str, Any]] = None,
    response_mode: Optional[str] = None,
) -> Dict[str, Any]:
    client, note = _maybe_qpharos_client()
    response: Dict[str, Any] = {
        "action": "qpharos.list_calibrations",
        "filters": filters,
        "response_mode": response_mode,
        "status": "simulated",
    }
    if client is None:
        response["note"] = note or "QPharos unavailable; returning stub calibrations."
        return response
    list_fn = getattr(client, "list_calibrations", None)
    if callable(list_fn):
        try:
            calibrations = list_fn(filters=filters or {})  # type: ignore[call-arg]
            response["status"] = "ok"
            response["calibrations"] = calibrations
        except Exception as exc:
            response["note"] = f"QPharos list_calibrations failed: {exc}"
    else:
        response["note"] = "qpharos.Client.list_calibrations not implemented; stub."
    return response


def qpharos_update_job(
    job_id: Optional[str],
    backend: Optional[str],
    note: Optional[str] = None,
) -> Dict[str, Any]:
    client, client_note = _maybe_qpharos_client()
    response: Dict[str, Any] = {
        "action": "qpharos.update_job",
        "job_id": job_id,
        "backend": backend,
        "note": note,
        "status": "simulated",
    }
    if client is None:
        response["reason"] = client_note or "QPharos unavailable."
        return response
    update_fn = getattr(client, "update_job", None)
    if callable(update_fn):
        try:
            result = update_fn(job_id=job_id, backend=backend, note=note)  # type: ignore[call-arg]
            response["status"] = "ok"
            response["details"] = result
        except Exception as exc:
            response["reason"] = f"QPharos update_job failed: {exc}"
    else:
        response["reason"] = "qpharos.Client.update_job not implemented; stub."
    return response


def qpharos_execute_calibration(script: Optional[str]) -> Dict[str, Any]:
    client, note = _maybe_qpharos_client()
    response: Dict[str, Any] = {
        "action": "qpharos.execute_calibration",
        "script": script,
        "status": "simulated",
    }
    if client is None:
        response["note"] = note or "QPharos unavailable; returning stub execution."
        return response
    exec_fn = getattr(client, "execute_calibration", None)
    if callable(exec_fn):
        try:
            result = exec_fn(script=script)  # type: ignore[call-arg]
            response["status"] = "ok"
            response["details"] = result
        except Exception as exc:
            response["note"] = f"QPharos execute_calibration failed: {exc}"
    else:
        response["note"] = "qpharos.Client.execute_calibration not implemented; stub."
    return response


def quillow_estimate_error(
    distance: Optional[int],
    p_error: Optional[float],
    rounds: Optional[int],
) -> Dict[str, Any]:
    distance_val = distance or 3
    rounds_val = rounds or 5
    p_val = p_error or 1e-3
    try:
        from quillow import MWPMDecoder, SurfaceCodeSimulator

        sim = SurfaceCodeSimulator(distance=distance_val, rounds=rounds_val)
        try:
            raw = sim.run(shots=128, error_probability=p_val)  # type: ignore[call-arg]
        except TypeError:
            raw = sim.run(shots=128)
        decoder = MWPMDecoder(distance=distance_val)
        est_fn = getattr(decoder, "estimate_logical_error", None)
        if callable(est_fn):
            estimated = float(est_fn(raw))
        else:
            estimated = 0.0
        return {
            "action": "quillow.estimate_error",
            "distance": distance_val,
            "rounds": rounds_val,
            "p_error": p_val,
            "estimated_logical_error": estimated,
        }
    except Exception as exc:
        return {
            "action": "quillow.estimate_error",
            "distance": distance_val,
            "rounds": rounds_val,
            "p_error": p_val,
            "estimated_logical_error": 0.012,
            "note": f"Quillow estimate fallback: {exc}",
        }


def quillow_benchmark_decoder(shots: Optional[int]) -> Dict[str, Any]:
    shots_val = int(shots or 512)
    try:
        from quillow import MWPMDecoder, SurfaceCodeSimulator

        sim = SurfaceCodeSimulator(distance=3, rounds=5)
        raw = sim.run(shots=shots_val)
        decoder = MWPMDecoder(distance=3)
        est_fn = getattr(decoder, "estimate_logical_error", None)
        estimated = float(est_fn(raw)) if callable(est_fn) else 0.0
        return {
            "action": "quillow.benchmark_decoder",
            "shots": shots_val,
            "estimated_logical_error": estimated,
        }
    except Exception as exc:
        return {
            "action": "quillow.benchmark_decoder",
            "shots": shots_val,
            "estimated_logical_error": 0.011,
            "note": f"Quillow benchmark fallback: {exc}",
        }


def send_notification(
    channel: Optional[str],
    condition: Optional[str],
) -> Dict[str, Any]:
    return {
        "action": "notify",
        "channel": channel or "alerts",
        "condition": condition,
        "status": "simulated",
        "note": "Hook this into your messaging or on-call system.",
    }
