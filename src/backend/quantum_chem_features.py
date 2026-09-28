"""quantum_chem_features.py — REAL quantum-chemistry observables as ML features.

This is the honest lever for molecular quantum advantage (see Reports/quantum_pqk_ab):
a projected-quantum-KERNEL on RDKit descriptors is REDUNDANT with what a GBDT already
extracts, so it never lifts. What classical descriptors genuinely LACK is the
electronic structure — so here we feed the pipeline REAL wavefunction observables
computed by HF + SQD (the validated quantum spine, quantum_core/quantum_descriptor):

  E_hf, HOMO, LUMO, gap, electrophilicity ω (Parr), SQD correlation energy,
  multireference character (1 - HF weight).

These are non-redundant with 2D/constitutional descriptors and are the numbers that
matter exactly where classical single-reference scoring is unreliable (high MR).
SQD here reproduces CASCI/FCI to ~1e-7 kcal (validated 6/6 vs FCI, beats CCSD(T) 4/6).

Expensive (HF+SQD per molecule) → results are cached by (smiles, basis, cas). Opt-in
via BIOQL_QCHEM_FEATURES=1. Fail-open: returns None if the quantum env / PySCF is
unavailable, so no pipeline ever breaks.

Runs in the miniforge `quantum` env (pyscf). MOLEVERA / BIOQL
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional

# Ordered feature names — the vector these map to is what gets appended to a model.
FEATURE_NAMES: List[str] = [
    "E_hf_Ha",
    "homo_eV",
    "lumo_eV",
    "gap_eV",
    "electrophilicity_omega_eV",
    "correlation_energy_eV",
    "multireference_character",
    "hf_weight",
]

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "qchem_cache")


def _flag_on() -> bool:
    return os.getenv("BIOQL_QCHEM_FEATURES", "0") == "1"


def _cache_path(smiles: str, basis: str, cas) -> str:
    key = hashlib.md5(f"{smiles}|{basis}|{cas}".encode()).hexdigest()
    return os.path.join(_CACHE_DIR, f"{key}.json")


def _resolve_quantum_core() -> Optional[str]:
    """Localiza el directorio `quantum_core` de forma robusta.

    OJO — bug real corregido el 2026-08-27: la versión anterior hacía
    `dirname(dirname(dirname(__file__)))` + "quantum_core". Eso funciona desde
    src/backend/, pero este módulo TAMBIÉN se carga desde /opt/bioql (que va
    primero en sys.path del servidor), y allí los tres dirname dan "/", con lo
    que buscaba "/quantum_core" — inexistente. El resultado era que
    `_quantum_descriptor` devolvía None SIEMPRE en el backend en ejecución, y
    toda la capa de observables cuánticos quedaba en silencio sin error visible.

    Orden: variable de entorno -> relativo a este archivo -> rutas conocidas.
    """
    env = os.environ.get("BIOQL_QUANTUM_CORE")
    if env and os.path.isdir(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(os.path.dirname(os.path.dirname(here)), "quantum_core"),
        os.path.join(os.path.dirname(here), "quantum_core"),
        os.path.join(here, "quantum_core"),
        os.path.expanduser("~/Documents/Proyectos/Spectrix_BioQL/quantum_core"),
        "/opt/bioql/quantum_core",
    ]
    for c in cands:
        if os.path.isdir(c):
            return c
    return None


def _quantum_descriptor(smiles: str, basis: str, cas) -> Optional[Dict[str, Any]]:
    """Call quantum_core/quantum_descriptor. Returns the raw observable dict or None."""
    try:
        import sys

        qc_dir = _resolve_quantum_core()
        if qc_dir is None:
            return None
        if qc_dir not in sys.path:
            sys.path.insert(0, qc_dir)
        from quantum_descriptor import quantum_descriptor

        _, n_o = cas if isinstance(cas, (tuple, list)) else (6, 6)
        out = quantum_descriptor(smiles=smiles, basis=basis, n_act_orb=int(n_o))
        return dict(out) if out is not None else None
    except Exception:
        return None


def compute_one(
    smiles: str, basis: str = "sto-3g", cas=(6, 6), use_cache: bool = True
) -> Optional[Dict[str, Any]]:
    """Compute the quantum-chemistry observables for ONE molecule. Cached, fail-open."""
    if not smiles:
        return None
    cp = _cache_path(smiles, basis, cas)
    if use_cache and os.path.exists(cp):
        try:
            cached: Dict[str, Any] = json.load(open(cp))
            return cached
        except Exception:
            pass
    d = _quantum_descriptor(smiles, basis, cas)
    if d is None:
        return None
    sqd = d.get("sqd_active_space") or {}
    out = {
        "E_hf_Ha": d.get("E_hf_Ha"),
        "homo_eV": d.get("homo_eV"),
        "lumo_eV": d.get("lumo_eV"),
        "gap_eV": d.get("gap_eV"),
        "electrophilicity_omega_eV": d.get("electrophilicity_omega_eV"),
        "correlation_energy_eV": d.get("correlation_energy_eV"),
        "multireference_character": d.get("multireference_character"),
        "hf_weight": d.get("hf_weight"),
        "E_sqd_Ha": sqd.get("E_sqd_Ha"),
        "decision": d.get("decision"),
    }
    # La ETIQUETA tiene que reflejar lo que CORRIO. Se detecto el 2026-09-08:
    # jax 0.10.1 exige numpy>=2 y el venv tiene 1.26.4; ffsim.linalg importa jax,
    # asi que `sqd_active_space` reventaba al importar y el SQD no corria. El
    # error quedaba en `sqd_error` dentro de quantum_descriptor, pero ESTA
    # funcion no lo copiaba al dict de salida ni al cache -- y el fichero seguia
    # declarando "HF+SQD (validated spine)". 16 de 39 entradas cacheadas tenian
    # MR=None con esa etiqueta puesta. Una etiqueta cuantica que sobrevive al
    # fallo del calculo cuantico es exactamente lo que este proyecto persigue
    # eliminar, asi que ahora: el error se propaga y la etiqueta dice la verdad.
    sqd_ran = out.get("multireference_character") is not None
    out["sqd_ran"] = bool(sqd_ran)
    if d.get("sqd_error"):
        out["sqd_error"] = d["sqd_error"]
    out["backend"] = (
        "HF+SQD (pyscf, quantum_core validated spine)"
        if sqd_ran
        else "HF only (SQD NO corrio; ver sqd_error)"
    )
    if use_cache:
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            json.dump(out, open(cp, "w"))
        except Exception:
            pass
    return out


def feature_vector(smiles: str, basis: str = "sto-3g", cas=(6, 6)) -> Optional[List[float]]:
    """Return the ordered numeric quantum-observable vector (FEATURE_NAMES) or None."""
    d = compute_one(smiles, basis=basis, cas=cas)
    if d is None:
        return None
    try:
        # Un valor de la caché puede no ser escalar (una lista, por ejemplo);
        # antes `float()` reventaba sobre él y el except devolvía None para TODO
        # el vector. Lo no numérico vale 0.0 y el resto del vector sobrevive.
        vec: List[float] = []
        for k in FEATURE_NAMES:
            v = d.get(k)
            vec.append(float(v) if isinstance(v, (int, float)) else 0.0)
        return vec
    except Exception:
        return None


def batch_features(smiles_list: List[str], basis: str = "sto-3g", cas=(6, 6)):
    """Compute the observable matrix for a list of SMILES. Returns (X, keep_idx, meta).
    Rows that fail SQD are skipped (indices in keep_idx). Import numpy lazily."""
    import numpy as np

    rows, keep = [], []
    for i, s in enumerate(smiles_list):
        v = feature_vector(s, basis=basis, cas=cas)
        if v is not None:
            rows.append(v)
            keep.append(i)
    if not rows:
        return None, [], {"names": FEATURE_NAMES}
    return np.asarray(rows, dtype=float), np.asarray(keep, dtype=int), {"names": FEATURE_NAMES}


def is_available() -> bool:
    try:
        import pyscf  # noqa: F401

        return True
    except Exception:
        return False


if __name__ == "__main__":
    for smi in ["C=CC(=O)N", "c1ccccc1", "O=C(C)Nc1ccc(O)cc1"]:
        v = feature_vector(smi)
        print(smi, "->", None if v is None else [round(x, 3) for x in v])
