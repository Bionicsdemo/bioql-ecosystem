"""
Assemble the interactive report for one pipeline run.

The result JSON goes in; what comes out is a single self-contained payload: the
chapters, the scenes the page animates, the sentences with their numbers already
resolved, the PyMOL meshes, the arithmetic this module re-derived and checked,
and a coverage table proving every value of the run is shown somewhere -- the
rest lands in the data annex rather than disappearing.

No text is invented here: a sentence exists only if its values are in the run
(narrate.py), and every sentence carries the paths it quotes, so the page can
show the reader where each number came from.

MOLEVERA / BIOQL
"""

import hashlib
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

from . import facts as F
from . import narrate

ANNEX = "annex"
_REQUIRED = ("PIPELINE", "TITLE", "matches", "unwrap", "subject", "chapters", "mesh_targets")


def discover() -> List[Any]:
    """Every model module under models/, in a stable order.

    A pipeline model is one file that declares the contract; dropping it in is all
    that adding a pipeline takes. A file that does not declare the contract, or does
    not import, is skipped with a note rather than breaking every other report.
    """
    import importlib
    import pkgutil

    from . import models as _pkg

    found, skipped = [], []
    for info in sorted(pkgutil.iter_modules(_pkg.__path__), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{_pkg.__name__}.{info.name}")
        except Exception as e:  # noqa: BLE001
            skipped.append((info.name, f"{type(e).__name__}: {str(e)[:120]}"))
            continue
        missing = [a for a in _REQUIRED if not hasattr(mod, a)]
        if missing:
            skipped.append((info.name, f"missing {', '.join(missing)}"))
            continue
        found.append(mod)
    discover.skipped = skipped  # type: ignore[attr-defined]
    return found


MODELS = discover()


def pick_model(result: Dict[str, Any]):
    for m in MODELS:
        try:
            if m.matches(result):
                return m
        except Exception:
            continue
    return None


def _poster_for(targets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """A ray-traced still of the run's main structure, when PyMOL can make one.

    Optional in every sense: if the module is absent or PyMOL fails, the report is
    built without it rather than not at all.
    """
    if not targets or os.environ.get("BIOQL_REPORT_POSTER", "1") != "1":
        return None
    try:
        from . import poster as _poster
    except Exception:
        return None
    try:
        img = _poster.poster(targets[0]["pdb"])
    except Exception:  # noqa: BLE001 -- a poster may never cost the report
        return None
    if img:
        img["of"] = targets[0]["label"]
    return img


def _verify(
    beats: List[Dict[str, Any]],
    result: Dict[str, Any],
    checks: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Ask Jev whether each sentence is supported by the values it quotes.

    Off unless BIOQL_REPORT_VERIFY is set, because it costs an API call per sentence.
    "strict" also removes any sentence Jev does not support -- the page would rather
    say less than say something the data does not carry.
    """
    mode = os.environ.get("BIOQL_REPORT_VERIFY", "")
    if mode not in ("1", "strict"):
        return None
    try:
        from . import verify as _verify_mod
    except Exception as e:  # noqa: BLE001
        return {"available": False, "why": f"verifier not importable: {type(e).__name__}: {e}"}
    try:
        v = _verify_mod.verify(beats, result, checks=checks)
    except Exception as e:  # noqa: BLE001
        return {"available": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
    v["mode"] = mode
    return v


def build(
    result: Dict[str, Any],
    mesh_fn: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
    session_id: str = "",
    want_meshes: bool = True,
) -> Dict[str, Any]:
    t0 = time.time()
    model = pick_model(result)
    if model is None:
        raise ValueError("no artifact model matches this result (pipeline not recognised)")
    r = model.unwrap(result)

    meshes: Dict[str, Any] = {}
    mesh_keys: Dict[str, str] = {}
    mesh_notes: List[Dict[str, Any]] = []
    if want_meshes and mesh_fn:
        for tgt in model.mesh_targets(r):
            m = mesh_fn(tgt["pdb"])
            if m:
                meshes[tgt["key"]] = m
                mesh_keys[tgt["key"]] = tgt["key"]
            else:
                from . import mesh as _mesh

                mesh_notes.append(
                    {"key": tgt["key"], "label": tgt["label"], "reason": _mesh.last_error}
                )

    checks = model.checks(r) if hasattr(model, "checks") else []
    passed = {c["id"]: bool(c.get("ok")) for c in checks}

    chapters_out: List[Dict[str, Any]] = []
    claims: Dict[str, List[str]] = {}
    for ch in model.chapters(r, meshes, mesh_keys):
        beats, used = narrate.build_beats(
            r, ch["beats"], getattr(model, "ALIASES", None), checks=passed, meshes=meshes.keys()
        )
        claims[ch["id"]] = list(ch.get("claims") or [])
        chapters_out.append(
            {
                "id": ch["id"],
                "title": ch["title"],
                "scene": ch["scene"],
                "beats": beats,
                "claims": claims[ch["id"]],
                "quoted": used,
                "status": "gap" if beats and all(b["kind"] == "gap" for b in beats) else "ok",
            }
        )

    # every sentence of the report, in the order a reader meets them
    all_beats = [b for ch in chapters_out for b in ch["beats"]]
    verification = _verify(all_beats, r, checks)
    if verification and verification.get("available") and verification.get("mode") == "strict":
        unsupported = {v["i"] for v in verification.get("verdicts", []) if not v.get("ok")}
        if unsupported:
            keep = [b for i, b in enumerate(all_beats) if i not in unsupported]
            kept = {id(b) for b in keep}
            for ch in chapters_out:
                ch["beats"] = [b for b in ch["beats"] if id(b) in kept]
            verification["removed"] = len(unsupported)

    cov = F.coverage(r, claims, annex=ANNEX)
    annex = [{"path": p, "value": F.get(r, p)} for p in cov["annex_paths"]]

    payload = {
        "artifact": "bioql_interactive_report_v1",
        "pipeline": r.get("pipeline") or getattr(model, "PIPELINE", ""),
        "title": getattr(model, "TITLE", {"es": "Informe", "en": "Report"}),
        "subject": model.subject(r) if hasattr(model, "subject") else "",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_timestamp": r.get("timestamp"),
        "session_id": session_id,
        "chapters": chapters_out,
        "meshes": meshes,
        "mesh_notes": mesh_notes,
        "poster": _poster_for(model.mesh_targets(r) if want_meshes else []),
        "verification": verification,
        "checks": checks,
        "coverage": {
            "leaves": cov["leaves"],
            "per_chapter": cov["per_chapter"],
            "annex": len(annex),
        },
        "annex": annex,
        "result": r,
        "build_s": round(time.time() - t0, 2),
    }
    payload["digest"] = hashlib.sha256(
        json.dumps(r, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return payload


def summary(payload: Dict[str, Any]) -> str:
    c = payload["coverage"]
    chs = ", ".join(f"{k} {v}" for k, v in c["per_chapter"].items())
    return (
        f"{payload['pipeline']} · {len(payload['chapters'])} capítulos · "
        f"{sum(len(ch['beats']) for ch in payload['chapters'])} frases · "
        f"{c['leaves']} valores ({chs}; anexo {c['annex']}) · "
        f"{len(payload['meshes'])} mallas · {payload['build_s']} s"
    )


# MOLEVERA / BIOQL
