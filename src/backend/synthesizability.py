"""
synthesizability.py — synthetic-accessibility assessment for generated / proposed
molecules.

WHAT THIS COMPUTES (all real, no fabrication):
  • SA_Score  — Ertl & Schuffenhauer (2009) Synthetic Accessibility score, the
    RDKit-contrib reference implementation (`Contrib/SA_Score/sascorer.py`). Range
    1 (easy to make) … 10 (very hard). Combines a fragment-contribution score
    (learned from 1M PubChem molecules) with a complexity penalty (rings, stereo,
    macrocycles, size). This is the field-standard heuristic for synthesizability.
  • SCScore  — Coley et al. (2018) Synthetic Complexity Score (1…5), IF the
    `scscore` package is importable. Optional; absent by default.
  • NP_Score — Ertl natural-product-likeness (RDKit `Contrib/NP_Score`), a useful
    orthogonal complexity signal (high NP-likeness ⇒ usually harder to make).
  • AiZynthFinder route-exists — IF `aizynthfinder` + a trained policy are
    installed, an honest retrosynthetic "is there a route to buyable building
    blocks?" check. Optional; absent by default (returns pending, never faked).

HONESTY: SA_Score is a *heuristic*, not a synthesis planner. It correlates with
chemists' ease-of-synthesis ratings (the original paper) and cleanly separates
easy drug-like molecules from hard complex natural products (see
validate_synthesizability.py), but it does NOT prove a route exists. We surface
its MEASURED separation power from the validation registry; we never claim a
route was found unless AiZynthFinder actually found one this run.

ADDITIVE: pure new module. Surfaces a `validation` field via validation_registry.

Pythons with rdkit: ~/.pyenv/versions/3.12.7/bin/python3 and
~/miniforge3/envs/docking_clean/bin/python.
"""

from __future__ import annotations

import math
import os
import sys
import threading
from typing import Any, Dict, List, Optional

# ── RDKit (required) ─────────────────────────────────────────────────────────
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, RDConfig

    _RDKIT = True
except Exception:  # pragma: no cover
    _RDKIT = False
    RDConfig = None

# ── SA_Score (RDKit contrib) — import once, thread-safe ──────────────────────
_SASCORER = None
_SASCORER_LOCK = threading.Lock()


def _load_sascorer():
    """Import the RDKit-contrib sascorer module (Ertl & Schuffenhauer 2009)."""
    global _SASCORER
    if _SASCORER is not None or not _RDKIT:
        return _SASCORER
    with _SASCORER_LOCK:
        if _SASCORER is not None:
            return _SASCORER
        try:
            sa_dir = os.path.join(RDConfig.RDContribDir, "SA_Score")
            if sa_dir not in sys.path:
                sys.path.append(sa_dir)
            import sascorer

            _SASCORER = sascorer
        except Exception:
            _SASCORER = None
    return _SASCORER


# ── NP_Score (RDKit contrib) — optional complexity signal ────────────────────
_NPSCORER = None
_NP_FSCORE = None
_NP_LOCK = threading.Lock()


def _load_npscorer():
    global _NPSCORER, _NP_FSCORE
    if _NPSCORER is not None or not _RDKIT:
        return _NPSCORER
    with _NP_LOCK:
        if _NPSCORER is not None:
            return _NPSCORER
        try:
            np_dir = os.path.join(RDConfig.RDContribDir, "NP_Score")
            if np_dir not in sys.path:
                sys.path.append(np_dir)
            import npscorer

            _NP_FSCORE = npscorer.readNPModel()
            _NPSCORER = npscorer
        except Exception:
            _NPSCORER = None
    return _NPSCORER


# ── SCScore (optional pip package) ───────────────────────────────────────────
_SCSCORER = None
_SC_TRIED = False


def _load_scscorer():
    global _SCSCORER, _SC_TRIED
    if _SC_TRIED:
        return _SCSCORER
    _SC_TRIED = True
    try:
        from scscore.standalone_model_numpy import SCScorer

        model = SCScorer()
        # try the packaged default weights; if unavailable, give up gracefully
        model.restore()
        _SCSCORER = model
    except Exception:
        _SCSCORER = None
    return _SCSCORER


# ── validation registry (additive surfacing) ────────────────────────────────
_vr: Any = None
try:
    import validation_registry as _vr
except Exception:  # pragma: no cover
    # El respaldo que había aquí era `from . import validation_registry`, y
    # src/backend no es un paquete: un import relativo no puede resolver nunca
    # desde aquí, así que esa rama solo podía acabar en `_vr = None`, que es lo
    # que este `except` ya hace. Se quita porque además detenía a mypy en seco.
    _vr = None

REGISTRY_KEY = "synthesizability"

# SA_Score threshold: molecules with SA <= this are treated as "readily
# synthesizable". 6.0 is the widely-used cutoff in generative-chemistry papers
# (Gao & Coley 2020; many de-novo design works flag SA>6 as a red flag). This is
# a convention, surfaced honestly — not a learned decision boundary.
SA_SYNTH_THRESHOLD = 6.0


# ─────────────────────────────────────────────────────────────────────────────
def available() -> Dict[str, bool]:
    """Which back-ends are live this process."""
    return {
        "rdkit": _RDKIT,
        "sa_score": _load_sascorer() is not None,
        "np_score": _load_npscorer() is not None,
        "scscore": _load_scscorer() is not None,
        "aizynthfinder": _aizynth_available(),
        "aizynth_configured": _aizynth_available() and _resolve_aizynth_config() is not None,
    }


def _aizynth_available() -> bool:
    try:
        import aizynthfinder  # noqa: F401

        return True
    except Exception:
        return False


def sa_score(smiles: str) -> Optional[float]:
    """Ertl & Schuffenhauer Synthetic Accessibility score (1 easy … 10 hard).
    None if RDKit/sascorer unavailable or SMILES invalid."""
    sas = _load_sascorer()
    if sas is None:
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return float(sas.calculateScore(mol))
    except Exception:
        return None


def np_score(smiles: str) -> Optional[float]:
    """Natural-product-likeness (Ertl); higher ⇒ more NP-like ⇒ usually harder.
    None if unavailable / invalid."""
    nps = _load_npscorer()
    if nps is None:
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return float(nps.scoreMol(mol, _NP_FSCORE))
    except Exception:
        return None


def sc_score(smiles: str) -> Optional[float]:
    """Coley SCScore (1 simple … 5 complex), only if the scscore pkg is present."""
    sc = _load_scscorer()
    if sc is None:
        return None
    try:
        _, score = sc.get_score_from_smi(smiles)
        return float(score)
    except Exception:
        return None


# ── AiZynthFinder — cached finder (loading the ZINC stock is ~5s/663MB) ──────
_AIZYNTH_FINDER = None
_AIZYNTH_CFG = None
_AIZYNTH_LOCK = threading.Lock()


def _resolve_aizynth_config(config_path: Optional[str] = None) -> Optional[str]:
    """Find a usable AiZynthFinder config.yml: explicit arg → AIZYNTH_CONFIG env
    → the default download location (~/aizynth_data/config.yml)."""
    candidates = [
        config_path,
        os.environ.get("AIZYNTH_CONFIG"),
        os.path.expanduser("~/aizynth_data/config.yml"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


# ── Isolated-env bridge ──────────────────────────────────────────────────────
# aizynthfinder 4.x HARD-pins numpy<2 / networkx<3 / rdkit<2024 / pandas<3, which
# are mutually exclusive with the live product env (numpy>=2, networkx 3, rdkit
# 2026, pandas 3 — required by qiskit-machine-learning, the modern rdkit pipeline,
# etc.). It therefore cannot be installed into the live interpreter without
# downgrading and breaking those engines. Instead, when the local interpreter
# cannot import aizynthfinder, we delegate the REAL route search to a sibling
# interpreter that can (default: pyenv 3.12.7, or $AIZYNTH_PYTHON), run a genuine
# AiZynthFinder MCTS there, and parse the real JSON back. Nothing is fabricated —
# an actual retrosynthesis runs; it just runs in a sibling process/env. This is a
# no-op when aizynthfinder is importable locally (the natural path is taken).
_AIZYNTH_PY_CANDIDATES = [
    os.environ.get("AIZYNTH_PYTHON"),
    os.path.expanduser("~/.pyenv/versions/3.12.7/bin/python3"),
    os.path.expanduser("~/miniforge3/envs/docking_clean/bin/python"),
]
_AIZYNTH_PY_CACHE: Any = "__unset__"
_AIZYNTH_PY_LOCK = threading.Lock()


def _resolve_aizynth_python() -> Optional[str]:
    """Find a sibling interpreter (not this one) that can import aizynthfinder."""
    global _AIZYNTH_PY_CACHE
    if _AIZYNTH_PY_CACHE != "__unset__":
        return str(_AIZYNTH_PY_CACHE) if _AIZYNTH_PY_CACHE else None
    import subprocess

    with _AIZYNTH_PY_LOCK:
        if _AIZYNTH_PY_CACHE != "__unset__":
            return str(_AIZYNTH_PY_CACHE) if _AIZYNTH_PY_CACHE else None
        found = None
        for py in _AIZYNTH_PY_CANDIDATES:
            if not py or not os.path.exists(py):
                continue
            try:
                if os.path.realpath(py) == os.path.realpath(sys.executable):
                    continue  # that's us; if we could import it we wouldn't be here
            except Exception:
                pass
            try:
                cp = subprocess.run(
                    [py, "-c", "import aizynthfinder"], capture_output=True, timeout=120
                )
                if cp.returncode == 0:
                    found = py
                    break
            except Exception:
                continue
        _AIZYNTH_PY_CACHE = found
        return found


def _delegate(
    func_name: str, smiles: str, config_path: Optional[str], extra: Dict[str, Any], timeout_s: int
) -> Optional[Dict[str, Any]]:
    """Run synthesizability.<func_name>(smiles, …) in the isolated aizynth env and
    return its real JSON result. Returns None if no sibling interpreter exists."""
    import json
    import subprocess

    py = _resolve_aizynth_python()
    if not py:
        return None
    here = os.path.dirname(os.path.abspath(__file__))
    payload = {"func": func_name, "smiles": smiles, "config_path": config_path, "extra": extra}
    code = (
        "import sys, json, os\n"
        "sys.path.insert(0, os.environ['BIOQL_BACKEND_DIR'])\n"
        "p = json.load(sys.stdin)\n"
        "import synthesizability as s\n"
        "fn = getattr(s, p['func'])\n"
        "res = fn(p['smiles'], config_path=p['config_path'], **p['extra'])\n"
        "sys.stdout.write('<<<AIZJSON>>>' + json.dumps(res))\n"
    )
    env = dict(os.environ, BIOQL_BACKEND_DIR=here, AIZYNTH_DELEGATED="1")
    try:
        cp = subprocess.run(
            [py, "-c", code],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
    except Exception as e:
        return {"available": False, "note": f"aizynth delegation error: {e}"}
    marker = "<<<AIZJSON>>>"
    idx = (cp.stdout or "").rfind(marker)
    if idx < 0:
        return {
            "available": False,
            "note": "aizynth delegation produced no result",
            "stderr_tail": (cp.stderr or "")[-400:],
        }
    try:
        out: Dict[str, Any] = json.loads(cp.stdout[idx + len(marker) :].strip())
        out["delegated_to"] = py
        return out
    except Exception as e:
        return {"available": False, "note": f"aizynth delegation parse error: {e}"}


def _can_delegate() -> bool:
    """True when this process can't run aizynth itself but a sibling env can."""
    if os.environ.get("AIZYNTH_DELEGATED") == "1":
        return False  # already inside the isolated worker — never recurse
    return (not _aizynth_available()) and (_resolve_aizynth_python() is not None)


def _get_finder(config_path: Optional[str] = None):
    """Return a cached AiZynthFinder configured with the USPTO policy + ZINC
    stock. Loads once per process (thread-safe). Returns None if unavailable."""
    global _AIZYNTH_FINDER, _AIZYNTH_CFG
    if not _aizynth_available():
        return None
    cfg = _resolve_aizynth_config(config_path)
    if not cfg:
        return None
    with _AIZYNTH_LOCK:
        if _AIZYNTH_FINDER is not None and _AIZYNTH_CFG == cfg:
            return _AIZYNTH_FINDER
        try:
            from aizynthfinder.aizynthfinder import AiZynthFinder

            finder = AiZynthFinder(configfile=cfg)
            # select an expansion policy (prefer the USPTO single-step model) and a stock
            pols = list(finder.expansion_policy.items)
            pol = "uspto" if "uspto" in pols else (pols[0] if pols else None)
            stocks = list(finder.stock.items)
            stk = "zinc" if "zinc" in stocks else (stocks[0] if stocks else None)
            if pol is None or stk is None:
                return None
            finder.expansion_policy.select(pol)
            finder.stock.select(stk)
            _AIZYNTH_FINDER = finder
            _AIZYNTH_CFG = cfg
            return finder
        except Exception:
            return None


def aizynth_route(
    smiles: str, config_path: Optional[str] = None, time_limit_s: int = 60
) -> Dict[str, Any]:
    """Real retrosynthetic route-exists check via AiZynthFinder, IF installed and
    configured (needs a trained expansion policy + stock). Returns
    {available, solved, n_routes, ...} or an honest pending dict — never faked.

    `solved` = AiZynthFinder found a complete tree from `smiles` down to
    purchasable building blocks (the ZINC in-stock set). This is a genuine
    retrosynthetic route, not a heuristic guess."""
    if _can_delegate():
        out = _delegate(
            "aizynth_route",
            smiles,
            config_path,
            {"time_limit_s": time_limit_s},
            timeout_s=max(time_limit_s + 180, 240),
        )
        if out is not None:
            return out
    if not _aizynth_available():
        return {
            "available": False,
            "note": "aizynthfinder not installed; route-exists check skipped",
        }
    cfg = _resolve_aizynth_config(config_path)
    if not cfg:
        return {
            "available": False,
            "note": "aizynthfinder installed but no config; set AIZYNTH_CONFIG "
            "to a config.yml (USPTO policy+stock) or place it at "
            "~/aizynth_data/config.yml",
        }
    finder = _get_finder(cfg)
    if finder is None:
        return {
            "available": False,
            "note": "aizynthfinder config present but finder failed to load "
            "(missing policy/stock models?)",
        }
    try:
        with _AIZYNTH_LOCK:
            finder.config.search.time_limit = time_limit_s
            finder.target_smiles = smiles
            finder.tree_search()
            finder.build_routes()
            solved = (
                bool(finder.tree.search_tree_solved())
                if hasattr(finder.tree, "search_tree_solved")
                else bool(finder.routes)
            )
            n_routes = len(finder.routes) if finder.routes else 0
            # cheapest (best) route score, if available
            top_score = None
            try:
                if finder.routes and getattr(finder.routes, "scores", None):
                    top_score = (
                        float(min(finder.routes.scores))
                        if isinstance(finder.routes.scores, (list, tuple))
                        else None
                    )
            except Exception:
                top_score = None
        return {
            "available": True,
            "solved": solved,
            "n_routes": n_routes,
            "top_route_score": top_score,
            "time_limit_s": time_limit_s,
            "stock": _AIZYNTH_CFG and "zinc",
            "policy": "uspto",
            "method": "AiZynthFinder MCTS, USPTO expansion policy + ZINC stock",
        }
    except Exception as e:  # pragma: no cover
        return {"available": False, "note": f"aizynthfinder error: {e}"}


def _route_detail(reaction_tree, score: Optional[float]) -> Dict[str, Any]:
    """Turn one AiZynthFinder ReactionTree into an actionable synthesis recipe:
    ordered retrosynthetic steps (product <- reactants), the leaf building blocks
    and whether each is purchasable, the step count and the longest linear
    sequence. All extracted from the REAL tree — nothing invented."""
    rt = reaction_tree
    # ── reactions, ordered shallow→deep (target disconnection first) ──────────
    rxns = list(rt.reactions())
    steps: List[Dict[str, Any]] = []
    for rx in rxns:
        rsmi = rx.reaction_smiles()
        product, _, reactants = rsmi.partition(">>")
        depth = None
        try:
            # depth of the product molecule node (edges from root); //2 = step #
            depth = int(rt.depth(rx.mol)) // 2 + 1
        except Exception:
            depth = None
        steps.append(
            {
                "product": product,
                "reactants": [r for r in reactants.split(".") if r],
                "reaction_smiles": rsmi,
                "retro_step": depth,
            }
        )
    # order steps by retro depth (target first) when available
    try:
        steps.sort(key=lambda s: (s["retro_step"] is None, s["retro_step"]))
    except Exception:
        pass

    # ── leaf building blocks + purchasability ────────────────────────────────
    blocks: List[Dict[str, Any]] = []
    leaf_depths: List[int] = []
    for m in rt.leafs():
        in_stock = False
        try:
            in_stock = bool(rt.in_stock(m))
        except Exception:
            in_stock = False
        blocks.append({"smiles": m.smiles, "in_stock": in_stock})
        try:
            leaf_depths.append(int(rt.depth(m)))
        except Exception:
            pass
    longest_linear = (max(leaf_depths) // 2) if leaf_depths else None

    n_blocks = len(blocks)
    n_purchasable = sum(1 for b in blocks if b["in_stock"])
    return {
        "n_steps": len(rxns),
        "longest_linear_sequence": longest_linear,
        "n_building_blocks": n_blocks,
        "n_purchasable_building_blocks": n_purchasable,
        "all_building_blocks_purchasable": (n_blocks > 0 and n_purchasable == n_blocks),
        "building_blocks": blocks,
        "steps": steps,
        "route_score": score,
    }


def route_plan(
    smiles: str, config_path: Optional[str] = None, time_limit_s: int = 120, max_routes: int = 3
) -> Dict[str, Any]:
    """Actionable synthetic-route PLAN for `smiles` via AiZynthFinder (real
    retrosynthesis, USPTO expansion policy + ZINC purchasable stock, MCTS).

    Unlike SA_Score (which rates HOW HARD a molecule is to make on a 1..10 scale),
    this returns HOW TO MAKE IT: the number of reaction steps, the ordered
    retrosynthetic step list (product <- reactants), the leaf building blocks and
    whether each is purchasable, plus AiZynthFinder's route score. The two are
    complementary — SA_Score = difficulty, route_plan = a concrete recipe.

    Returns the best route plus up to `max_routes` alternatives, or an honest
    pending/unavailable dict (never fabricated). `solved=True` means a complete
    tree down to buyable building blocks was found this run."""
    if _can_delegate():
        out = _delegate(
            "route_plan",
            smiles,
            config_path,
            {"time_limit_s": time_limit_s, "max_routes": max_routes},
            timeout_s=max(time_limit_s + 180, 300),
        )
        if out is not None:
            return out
    if not _aizynth_available():
        return {
            "available": False,
            "solved": None,
            "note": "aizynthfinder not installed; route planning skipped",
        }
    cfg = _resolve_aizynth_config(config_path)
    if not cfg:
        return {
            "available": False,
            "solved": None,
            "note": "aizynthfinder installed but no config; set AIZYNTH_CONFIG "
            "or place a config.yml at ~/aizynth_data/config.yml",
        }
    finder = _get_finder(cfg)
    if finder is None:
        return {
            "available": False,
            "solved": None,
            "note": "aizynthfinder config present but finder failed to load "
            "(missing policy/stock models?)",
        }
    if not smiles or (_RDKIT and Chem.MolFromSmiles(smiles) is None):
        return {"available": True, "solved": None, "note": "invalid SMILES"}
    try:
        with _AIZYNTH_LOCK:
            finder.config.search.time_limit = time_limit_s
            finder.target_smiles = smiles
            finder.tree_search()
            finder.build_routes()
            routes = finder.routes
            n_routes = len(routes) if routes else 0
            solved = (
                bool(finder.tree.search_tree_solved())
                if hasattr(finder.tree, "search_tree_solved")
                else bool(n_routes)
            )
            if not n_routes:
                return {
                    "available": True,
                    "solved": solved,
                    "n_routes": 0,
                    "smiles": smiles,
                    "best_route": None,
                    "alternatives": [],
                    "time_limit_s": time_limit_s,
                    "stock": "zinc",
                    "policy": "uspto",
                    "method": "AiZynthFinder MCTS, USPTO expansion policy + " "ZINC stock",
                    "note": "no complete route to purchasable stock found in "
                    "the time/coverage budget (can be a search miss, "
                    "not a proof of non-synthesizability)",
                }
            # extract per-route detail
            scores_raw = getattr(routes, "all_scores", None) or []
            details: List[Dict[str, Any]] = []
            for i in range(min(n_routes, max_routes)):
                try:
                    rt = routes[i]["reaction_tree"]
                except Exception:
                    rt = routes.reaction_trees[i]
                sc = None
                try:
                    sc = routes[i].get("score")
                    if isinstance(sc, dict):
                        sc = next(iter(sc.values()), None)
                except Exception:
                    sc = None
                if sc is None and i < len(scores_raw):
                    sv = scores_raw[i]
                    sc = next(iter(sv.values()), None) if isinstance(sv, dict) else sv
                details.append(_route_detail(rt, float(sc) if sc is not None else None))
        best = details[0] if details else None
        return {
            "available": True,
            "solved": solved,
            "smiles": smiles,
            "n_routes": n_routes,
            "best_route": best,
            "alternatives": details[1:],
            "time_limit_s": time_limit_s,
            "stock": "zinc",
            "policy": "uspto",
            "method": "AiZynthFinder MCTS, USPTO expansion policy + ZINC stock",
            "interpretation": (
                "SA_Score rates difficulty (1 easy..10 hard); this route_plan is "
                "the concrete recipe. n_steps reaction steps from purchasable "
                "building blocks."
                if best
                else None
            ),
        }
    except Exception as e:  # pragma: no cover
        return {"available": False, "solved": None, "note": f"aizynthfinder error: {e}"}


def route_exists(
    smiles: str, config_path: Optional[str] = None, time_limit_s: int = 60
) -> Optional[bool]:
    """ROUTE-VALIDATED synthesizability: True iff AiZynthFinder finds a complete
    retrosynthetic route from `smiles` to purchasable building blocks. Returns
    None (not False) if AiZynthFinder is unavailable/unconfigured — so callers can
    distinguish 'no route found' from 'could not check'. Never fabricated."""
    res = aizynth_route(smiles, config_path=config_path, time_limit_s=time_limit_s)
    if not res.get("available"):
        return None
    return bool(res.get("solved"))


def _validation_field() -> Dict[str, Any]:
    """Surface the MEASURED separation power of SA_Score from the registry."""
    if _vr is None:
        return {"validated": False, "note": "validation_registry unavailable"}
    try:
        return dict(_vr.summary(REGISTRY_KEY))
    except Exception:
        return {"validated": False, "note": "validation_registry error"}


def assess(smiles: str, run_aizynth: bool = False) -> Dict[str, Any]:
    """Full synthesizability assessment for one molecule.

    Returns a dict with the real computed scores plus a `validation` field
    carrying the registry-recorded separation power (never a fabricated number).
    Keys: smiles, valid, sa_score, sa_synthesizable, synth_score (0..1, higher=
    easier), np_score, sc_score, aizynth, scores_available, validation.
    """
    out: Dict[str, Any] = {
        "smiles": smiles,
        "valid": False,
        "sa_score": None,
        "sa_synthesizable": None,
        "synth_score": None,
        "np_score": None,
        "sc_score": None,
        "aizynth": None,
        "scores_available": available(),
        "validation": _validation_field(),
    }
    if not _RDKIT:
        out["note"] = "rdkit unavailable"
        return out
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        out["note"] = "invalid SMILES"
        return out
    out["valid"] = True

    sa = sa_score(smiles)
    if sa is not None:
        out["sa_score"] = round(sa, 3)
        out["sa_synthesizable"] = bool(sa <= SA_SYNTH_THRESHOLD)
        # synth_score: map SA[1..10] -> [1..0] linearly, clamp. Higher = easier.
        out["synth_score"] = round(max(0.0, min(1.0, (10.0 - sa) / 9.0)), 3)
        out["sa_threshold"] = SA_SYNTH_THRESHOLD

    nps = np_score(smiles)
    if nps is not None:
        out["np_score"] = round(nps, 3)
    scs = sc_score(smiles)
    if scs is not None:
        out["sc_score"] = round(scs, 3)

    if run_aizynth:
        az = aizynth_route(smiles)
        out["aizynth"] = az
        # route_validated: the honest, planner-backed synthesizability verdict.
        # True/False only when AiZynthFinder actually ran; None otherwise.
        out["route_validated"] = bool(az.get("solved")) if az.get("available") else None

    return out


def assess_batch(smiles_list: List[str]) -> List[Dict[str, Any]]:
    """Vectorised assess() over a list of SMILES."""
    return [assess(s) for s in (smiles_list or [])]


def synth_score_only(smiles: str) -> Optional[float]:
    """Convenience: the 0..1 synth_score (higher=easier) or None. For additive
    wiring into generative output with minimal surface area."""
    r = assess(smiles)
    return r.get("synth_score")


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Synthesizability assessment (SA_Score etc.)")
    ap.add_argument("smiles", nargs="*", help="SMILES to assess")
    ap.add_argument(
        "--aizynth", action="store_true", help="run AiZynthFinder route check if configured"
    )
    ap.add_argument(
        "--route",
        action="store_true",
        help="print a full route_plan (steps + building blocks) per molecule",
    )
    args = ap.parse_args()
    print("backends:", json.dumps(available()))
    demo = args.smiles or [
        "CC(=O)Oc1ccccc1C(=O)O",  # aspirin (easy)
        "CC(C)Cc1ccc(C(C)C(=O)O)cc1",  # ibuprofen (easy)
        "CC(=O)Nc1ccc(O)cc1",  # paracetamol (easy)
    ]
    for s in demo:
        r = assess(s, run_aizynth=args.aizynth)
        print(
            json.dumps(
                {
                    k: r[k]
                    for k in (
                        "smiles",
                        "valid",
                        "sa_score",
                        "sa_synthesizable",
                        "synth_score",
                        "np_score",
                    )
                },
                default=str,
            )
        )
        if args.route:
            plan = route_plan(s)
            if plan.get("best_route"):
                br = plan["best_route"]
                print(
                    f"  route_plan: solved={plan.get('solved')} "
                    f"n_steps={br['n_steps']} "
                    f"longest_linear={br['longest_linear_sequence']} "
                    f"score={br['route_score']}"
                )
                for st in br["steps"]:
                    print(
                        f"    step {st['retro_step']}: {st['product']} "
                        f"<- {'.'.join(st['reactants'])}"
                    )
                print(
                    "    building blocks: "
                    + ", ".join(
                        f"{b['smiles']}{'(buy)' if b['in_stock'] else '(?)'}"
                        for b in br["building_blocks"]
                    )
                )
            else:
                print(f"  route_plan: {plan.get('note') or plan}")
