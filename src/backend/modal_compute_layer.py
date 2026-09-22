"""
Single routing point for every heavy computation: Modal first, local fallback.

Why this file exists
--------------------
Modal calls were scattered across modules, each with its own try/except, and
when the workspace ran out of budget every one of them degraded in a slightly
different way -- some silently. A pipeline that quietly swaps a GPU model for a
local approximation and keeps the same field name is lying by omission.

Here every heavy job goes through ONE door that always answers three things:

    where_it_ran     "modal" | "local" | "unavailable"
    why              if it did not run on Modal, the exact reason
    is_degraded      True when the local path is a weaker substitute

The card and the report read those fields, so a viewer always knows whether a
number came from the GPU model or from its local stand-in.

Deployed apps -- VERIFIED BY HYDRATION on 2026-09-19.

The previous note here said "verified -- the functions resolve". It did not
verify anything: `Function.from_name()` is LAZY in modal >=1.x, so it returns a
handle without contacting the server and never raises for an app that does not
exist. `app_status()` therefore reported every entry as deployed, including
`bioql-lddm` an hour before that app was written. `.hydrate()` is the call that
actually looks it up, and this module now uses it.

What the real lookup found (four of five registrations were wrong):

    bioql-boltz2::predict              FIXED -- was ::fold, which does not exist
    bioql-quantum-gpu::cudaq_statevector  FIXED -- was ::run, which does not exist
    bioql-mmgbsa-ens::ensemble_gpu_ligand OK
    bioql-esmfold2::fold_structure     FIXED by redeploy on 2026-09-21 -- the
                                       deployed app had predated the source
    bioql-admet-sota::ADMETSota.predict   it is a modal.Cls, not a Function, so
                                       a Function lookup could never work; the
                                       "cls" kind below handles it

Those four were failing at call time and silently taking the local fallback --
runtime stayed honest (`is_degraded: True`), the status table did not.

    bioql-lddm::design|dock|programmable    LDDM 3D ligand generation
                                       (modal_lddm.py, added 2026-09-19; NOT
                                       deployed -- the deploy needs an image
                                       build and the Modal workspace is over
                                       its spend limit as of 2026-09-21)

MOLEVERA / BIOQL
"""

import os
import time
from typing import Any, Callable, Dict, Optional

# key -> how to reach it. `kind` is "function" for @app.function and "cls" for
# a modal.Cls (the ADMET apps are classes; a Function lookup on them fails).
APPS = {
    "fold_complex": {"app": "bioql-boltz2", "fn": "predict", "kind": "function",
                     "does": "co-folded protein:ligand complex structure",
                     "fallback": "experimental PDB from RCSB (no prediction)"},
    "fold_protein": {"app": "bioql-esmfold2", "fn": "fold_structure", "kind": "function",
                     "does": "single-chain protein structure",
                     "fallback": "experimental PDB from RCSB (no prediction)"},
    "quantum_gpu": {"app": "bioql-quantum-gpu", "fn": "cudaq_statevector", "kind": "function",
                    "does": "CUDA-Q state-vector / MPS simulation",
                    "fallback": "local CPU state-vector (ffsim/pyscf) — same answer, fewer qubits"},
    "mmgbsa_ensemble": {"app": "bioql-mmgbsa-ens", "fn": "ensemble_gpu_ligand", "kind": "function",
                        "does": "ensemble MM-GBSA on GPU",
                        "fallback": "single-structure MM-GBSA in a local conda env"},
    "admet_sota": {"app": "bioql-admet-sota", "cls": "ADMETSota", "fn": "predict", "kind": "cls",
                   "does": "SOTA ADMET model suite",
                   "fallback": "local LightGBM ADMET — lower accuracy, still calibrated"},
    # LDDM (modal_lddm.py). No local fallback ON PURPOSE: there is no honest CPU
    # stand-in for a pocket-conditioned 3D generator, and substituting a fragment
    # enumeration under the same field name would be the exact lie this layer
    # exists to prevent. Unavailable says unavailable.
    "ligand_design": {"app": "bioql-lddm", "fn": "design", "kind": "function",
                      "does": "pocket-conditioned 3D ligand design / growing / linking (LDDM)",
                      "fallback": None},
    "ligand_dock": {"app": "bioql-lddm", "fn": "dock", "kind": "function",
                    "does": "generative (re)docking, incl. partial docking for covalents (LDDM)",
                    "fallback": None},
    "ligand_programmable": {"app": "bioql-lddm", "fn": "programmable", "kind": "function",
                            "does": "programmable / synthesizable ligand design (LDDM)",
                            "fallback": None},
}


def _handle(spec: Dict[str, Any]):
    """Resolve a spec to a callable handle AND hydrate it.

    Hydration is the point: without it `from_name` returns a handle for an app
    that may not exist, and every caller downstream believes it is there.
    """
    if spec.get("kind") == "cls":
        from modal import Cls
        cls = Cls.from_name(spec["app"], spec["cls"])
        cls.hydrate()
        return getattr(cls(), spec["fn"])
    from modal import Function
    f = Function.from_name(spec["app"], spec["fn"])
    f.hydrate()
    return f


_ENABLED = os.environ.get("BIOQL_MODAL_ENABLED", "1") == "1"


def app_status() -> Dict[str, Any]:
    """Which apps are really deployed. Hydrates each handle -- one cheap lookup
    per app, no GPU started, no billable work. It does NOT prove the workspace
    has budget to run them; that only shows at call time."""
    out: Dict[str, Any] = {"enabled": _ENABLED, "apps": {},
                           "verified_by": "modal hydrate (real server lookup)"}
    if not _ENABLED:
        out["reason"] = "disabled by BIOQL_MODAL_ENABLED=0"
        return out
    try:
        import modal  # noqa: F401
    except Exception as e:
        out["reason"] = f"modal not importable: {str(e)[:120]}"
        return out
    for key, spec in APPS.items():
        entry = {"app": spec["app"], "function": spec["fn"],
                 "kind": spec.get("kind", "function"),
                 "does": spec["does"], "local_fallback": spec.get("fallback")}
        if spec.get("note"):
            entry["note"] = spec["note"]
        try:
            _handle(spec)
            entry["deployed"] = True
        except Exception as e:
            entry["deployed"] = False
            entry["reason"] = f"{type(e).__name__}: {str(e)[:160]}"
        out["apps"][key] = entry
    out["n_deployed"] = sum(1 for a in out["apps"].values() if a["deployed"])
    out["n_registered"] = len(APPS)
    return out


def run(key: str, *args, local_fn: Optional[Callable] = None,
        timeout: int = 1800, **kwargs) -> Dict[str, Any]:
    """Run a heavy job. Modal first; on any failure, the local path.

    The return ALWAYS carries where it ran and why -- a caller cannot use the
    result without seeing which engine produced it.
    """
    t0 = time.time()
    spec = APPS.get(key)
    if not spec:
        return {"available": False, "where_it_ran": "unavailable",
                "why": f"unknown job {key!r}", "known": sorted(APPS)}
    app, fn, does = spec["app"], spec["fn"], spec["does"]
    fallback = spec.get("fallback")

    if _ENABLED:
        try:
            f = _handle(spec)
            res = f.remote(*args, **kwargs)
            return {"available": True, "where_it_ran": "modal",
                    "app": app, "function": fn, "does": does,
                    "is_degraded": False, "result": res,
                    "elapsed_s": round(time.time() - t0, 1)}
        except Exception as e:
            why = f"{type(e).__name__}: {str(e)[:180]}"
    else:
        why = "Modal disabled by BIOQL_MODAL_ENABLED=0"

    if local_fn is None:
        return {"available": False, "where_it_ran": "unavailable",
                "why": why, "does": does, "would_fallback_to": fallback,
                "no_local_equivalent": fallback is None,
                "elapsed_s": round(time.time() - t0, 1)}
    try:
        res = local_fn(*args, **kwargs)
        return {"available": True, "where_it_ran": "local",
                "is_degraded": True, "why": why,
                "does": does, "local_engine": fallback, "result": res,
                "degradation_note": (f"Modal path unavailable, so this value "
                                     f"comes from: {fallback}"),
                "elapsed_s": round(time.time() - t0, 1)}
    except Exception as e:
        return {"available": False, "where_it_ran": "unavailable",
                "why": why,
                "local_error": f"{type(e).__name__}: {str(e)[:150]}",
                "does": does, "elapsed_s": round(time.time() - t0, 1)}


def receptor_structure(pdb_id: str) -> Dict[str, Any]:
    """Receptor coordinates for the 3D viewer.

    Experimental structure first: a measured crystal beats a prediction, and
    the pipeline already picked this PDB precisely because it has a real
    ligand-bound pocket. Modal's folding models are for the case where NO
    experimental structure exists.
    """
    try:
        from docking_screening_engine import _download_pdb
        txt = _download_pdb(pdb_id)
        if not txt or len(txt) < 500:
            raise ValueError("empty PDB text")
        atoms = sum(1 for l in txt.splitlines() if l.startswith("ATOM"))
        het = sum(1 for l in txt.splitlines() if l.startswith("HETATM"))
        return {"available": True, "source": "RCSB (experimental)",
                "pdb_id": pdb_id, "n_atoms": atoms, "n_hetatm": het,
                "pdb_text": txt, "size_kb": round(len(txt) / 1024, 1),
                "why_not_predicted": ("an experimental structure exists; a "
                                      "predicted model would be a step down")}
    except Exception as e:
        return {"available": False, "pdb_id": pdb_id,
                "reason": f"{type(e).__name__}: {str(e)[:140]}",
                "next_option": ("fold it on Modal (bioql-boltz2 / "
                                "bioql-esmfold2) when no crystal exists")}


if __name__ == "__main__":
    import json
    st = app_status()
    print(f"Modal enabled: {st['enabled']}  deployed: {st.get('n_deployed')}/{len(APPS)}"
          f"  ({st.get('verified_by')})")
    for k, a in (st.get("apps") or {}).items():
        print(f"  [{'OK' if a['deployed'] else '--'}] {k:20} {a['app']}::{a['function']}")
        print(f"       does     : {a['does']}")
        print(f"       fallback : {a['local_fallback'] or 'NONE — no honest local equivalent'}")
        if a.get("reason"):
            print(f"       reason   : {a['reason']}")
    print("\nreceptor fetch test (6OJF):")
    r = receptor_structure("6OJF")
    print(f"  available={r['available']} atoms={r.get('n_atoms')} "
          f"het={r.get('n_hetatm')} size={r.get('size_kb')} KB")

# MOLEVERA / BIOQL
