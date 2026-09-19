"""One import surface for the gates, so the monolith needs three lines, not surgery.

`script_executor_server.py` is ~35k lines. Every call site added to it is a
place a future edit can break, so the gates expose exactly four functions here
and keep their own logic in their own modules.

EVERY FUNCTION HERE FAILS OPEN BY DESIGN -- and says so.
    A gate that raises takes the pipeline down with it. These wrappers catch,
    record the failure in the returned record, and let the pipeline continue.
    That is the right trade for an audit layer, but it means a caller must read
    the record: `verdict == "pass"` with `gate_error` set means UNCHECKED, not
    checked-and-clean. `audited()` never claims a check that did not run.

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

_LOG_PREFIX = "[bioql_gates]"


def _err(name: str, exc: Exception) -> Dict[str, Any]:
    return {"verdict": "pass", "findings": [], "withheld": [],
            "gate_error": "%s: %s" % (type(exc).__name__, exc),
            "checked": False,
            "note": "%s did not run. Unchecked is not the same as passed." % name}


# ───────────────────────────── stage audit ────────────────────────────────

def audit(stage: str,
          output: Dict[str, Any],
          candidate: Optional[Dict[str, Any]] = None,
          prior: Optional[Dict[str, Any]] = None,
          cohort: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Audit one stage's output at the boundary. Never raises."""
    try:
        import stage_audit
        r = stage_audit.audit_stage(stage, output, candidate, prior,
                                    cohort=cohort,
                                    consult_model=_consult_model())
        r["checked"] = True
        return r
    except Exception as exc:
        print("%s audit(%s) failed: %s" % (_LOG_PREFIX, stage, exc))
        return _err("stage audit", exc)


def audited(stage: str,
            output: Dict[str, Any],
            candidate: Optional[Dict[str, Any]] = None,
            prior: Optional[Dict[str, Any]] = None,
            cohort: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Audit and return the output to pass downstream, with the audit attached.

    In `enforce` mode quarantined fields are absent from the returned copy. In
    `shadow` (the default) nothing is withheld and the verdict is recorded only.
    """
    a = audit(stage, output, candidate, prior, cohort)
    try:
        import stage_audit
        out = stage_audit.apply_quarantine(output, a)
    except Exception as exc:
        print("%s apply_quarantine(%s) failed: %s" % (_LOG_PREFIX, stage, exc))
        out = output
    if isinstance(out, dict):
        out = dict(out)
        out["_stage_audit"] = a
        rc = composite_beside(out)
        if rc is not None:
            out["_composite_evidenced"] = rc
    return out


def composite_beside(candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The composite over evidenced components only, placed BESIDE the published one.

    Never replaces the published score. Returns None when the record has no
    score_breakdown to weigh, so nothing is attached to records it cannot speak
    to. Without a cohort no value is presumed to be a default -- stated in the
    result -- which is the honest behaviour for a single candidate read alone.
    """
    try:
        import composite_recompute as CR
        if not CR.breakdown_of(candidate):
            return None
        return CR.recompute(candidate)
    except Exception as exc:
        print("%s composite_beside failed: %s" % (_LOG_PREFIX, exc))
        return {"available": False, "checked": False,
                "reason": "Recompute did not run (%s). Unchecked is not the same "
                          "as agreeing with the published score." % exc}


def _consult_model() -> bool:
    """The model half of the audit is off unless asked for: it costs a call."""
    return (os.environ.get("BIOQL_STAGE_AUDIT_MODEL") or "0").strip() in ("1", "true", "yes")


# ─────────────────────────── literature potency ───────────────────────────

def potency_from_text(candidate: Dict[str, Any], text: str,
                      measure: str = "IC50") -> Dict[str, Any]:
    """Read a stated potency out of supplied text. Never raises."""
    try:
        import literature_value_extraction as LX
        return LX.potency_for_candidate(candidate, text, measure=measure)
    except Exception as exc:
        print("%s potency_from_text failed: %s" % (_LOG_PREFIX, exc))
        return {"available": False, "value_nm": None,
                "reason": "Extraction did not run (%s)." % exc}


# ───────────────────────────── intent routing ─────────────────────────────

def route_request(request: str, registry: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Choose one registered tool, or decline. Never raises, never dispatches."""
    try:
        import intent_router
        return intent_router.route(request, registry)
    except Exception as exc:
        print("%s route_request failed: %s" % (_LOG_PREFIX, exc))
        return {"available": False, "tool": None, "ready_to_dispatch": False,
                "reason": "Routing did not run (%s)." % exc,
                "next_step": "Name the tool directly. Nothing was run."}


# ──────────────────────────────── status ──────────────────────────────────

def status() -> Dict[str, Any]:
    """What is wired, what mode it is in, and what is actually reachable."""
    out: Dict[str, Any] = {"modules": {}, "modes": {}}
    for name in ("stage_audit", "intent_router", "literature_value_extraction",
                 "efficacious_dose", "stage_solver", "typesafe_client"):
        try:
            mod = __import__(name)
            out["modules"][name] = {"loaded": True, "path": getattr(mod, "__file__", None)}
        except Exception as exc:
            out["modules"][name] = {"loaded": False, "error": str(exc)}
    try:
        import stage_audit
        out["modes"]["stage_audit"] = stage_audit.mode()
    except Exception:
        out["modes"]["stage_audit"] = "unavailable"
    try:
        import stage_solver
        out["modes"]["stage_solver"] = stage_solver.mode()
    except Exception:
        out["modes"]["stage_solver"] = "unavailable"
    try:
        import typesafe_client
        out["typesafe_configured"] = typesafe_client.is_configured()
    except Exception:
        out["typesafe_configured"] = False
    out["modes"]["stage_audit_consults_model"] = _consult_model()
    return out
