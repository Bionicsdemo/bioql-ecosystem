"""
esmfold2_backend.py — REAL ESMFold2 (Biohub, MIT, 2026-05-27) structure backend.

This is the PREFERRED complex / antibody-antigen / peptide folder for BioQL.
It returns GENUINE ATOM coordinates (CIF + biopython-converted PDB) plus
iptm/ptm/plddt, mirroring the Modal/HTTP transport pattern already used by
bionics_bridge.predict_structure_chai1.

Transport priority (first that works wins):
  1. modal.Function.from_name("bioql-esmfold2-service", "predict").remote({...})
     (dodges Modal's 8-web-function workspace cap, same as Chai-1)
  2. HTTP POST to  f"{ESMFOLD2_URL}/predict/complex"  (or /predict/structure for
     a single chain) when env ESMFOLD2_URL is set.
  3. GRACEFUL FALLBACK to pipeline_enhancements.predict_structure_real (Chai-1),
     the only other REAL-coordinate folder on this machine.

HONESTY: the returned dict ALWAYS reports which backend/model actually produced
the structure (`backend` ∈ {"modal","http","fallback"}, `model` ∈
{"esmfold2","esmfold2-fast","chai-1(fallback)"}). Never fabricates coordinates
or scores; on total failure returns success=False with an honest error. Never
raises.

The 6B ESMC backbone behind ESMFold2 needs an A100-40GB (NOT an L4), so the
heavy lifting is a Modal A100 app (see src/modal/esmfold2_modal.py). This module
is the in-process client + fallback; it runs in the main backend venv with no
GPU and no ESM install.

Copyright (c) 2026 MOLEVERA / BIOQL. All rights reserved.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Union

log = logging.getLogger("bioql.esmfold2_backend")

# No hardcoded default — an empty value disables the HTTP transport so we never
# blindly POST to a stale URL. Set ESMFOLD2_URL to the deployed app base.
ESMFOLD2_URL = os.environ.get("ESMFOLD2_URL", "").rstrip("/")

# Modal app/function names (mirror predict_structure_chai1: from_name + remote).
# `predict` vive en el servicio de src/modal/esmfold2_modal.py, cuya app se llama
# "bioql-esmfold2-service"; "bioql-esmfold2" es otra app (fold_structure/fold_complex).
_MODAL_APP = os.environ.get("ESMFOLD2_MODAL_APP", "bioql-esmfold2-service")
_MODAL_FN = os.environ.get("ESMFOLD2_MODAL_FN", "predict")

_REMOTE_TIMEOUT_S = int(os.environ.get("ESMFOLD2_TIMEOUT_S", "900"))

# In-process result cache (input hash -> normalized result).
_cache: Dict[str, dict] = {}


def _cache_key(sequences: List[str], complex_flag: bool) -> str:
    raw = json.dumps({"seqs": sequences, "complex": complex_flag}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cif_to_pdb(cif: str) -> tuple[str, int]:
    """Convert mmCIF text -> PDB text (ATOM records). Returns (pdb_text, n_res).

    Tries biotite FIRST: ESMFold2 emits a minimal `data_pred` mmCIF with a
    non-standard _atom_site column order that biopython's MMCIFParser cannot
    parse (returns 0 atoms), whereas biotite handles it. Falls back to biopython
    for other CIFs. Never raises; ("", 0) on total failure.
    """
    if not cif or not isinstance(cif, str):
        return "", 0
    # 1) biotite — robust for ESMFold2's CIF
    try:
        import io as _io

        import biotite.structure as _struc
        import biotite.structure.io.pdb as _pdb
        import biotite.structure.io.pdbx as _pdbx

        f = _pdbx.CIFFile.read(_io.StringIO(cif))
        arr = _pdbx.get_structure(f, model=1)
        if arr is not None and arr.array_length() > 0:
            try:
                n_res = int(_struc.get_residue_count(arr))
            except Exception:
                n_res = 0
            pf = _pdb.PDBFile()
            pf.set_structure(arr)
            buf = _io.StringIO()
            pf.write(buf)
            ptxt = buf.getvalue()
            if "ATOM" in ptxt:
                return ptxt, n_res
    except Exception as be:
        log.warning("ESMFold2 CIF->PDB (biotite) failed: %s", be)
    # 2) biopython fallback (standard CIFs)
    pdb_text, n_res = "", 0
    cifp = pdbp = None
    try:
        from Bio.PDB import PDBIO, MMCIFParser

        fd, cifp = tempfile.mkstemp(suffix=".cif")
        with os.fdopen(fd, "w") as fh:
            fh.write(cif)
        st = MMCIFParser(QUIET=True).get_structure("s", cifp)
        n_res = sum(1 for _ in st.get_residues())
        io = PDBIO()
        io.set_structure(st)
        fd2, pdbp = tempfile.mkstemp(suffix=".pdb")
        os.close(fd2)
        io.save(pdbp)
        with open(pdbp) as fh:
            pdb_text = fh.read()
    except Exception as ce:
        log.warning("ESMFold2 CIF->PDB (biopython) failed: %s", ce)
    finally:
        for p in (cifp, pdbp):
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass
    return pdb_text, n_res


def _as_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _plddt_0_100(v) -> Optional[float]:
    """Normalize ESMFold2's fractional pLDDT to BioQL's explicit 0-100 contract."""
    value = _as_float(v)
    if value is None:
        return None
    return value * 100.0 if 0.0 <= value <= 1.0 else value


def _normalize_remote(raw: dict, *, backend: str) -> dict:
    """Map a remote ESMFold2 response onto this module's contract. Never raises."""
    cif = raw.get("cif") or raw.get("structure_cif") or ""
    pdb = raw.get("pdb") or ""
    n_res = raw.get("n_residues") or 0
    if not pdb and cif:
        pdb, n_res = _cif_to_pdb(cif)
    has_coords = bool("ATOM" in (pdb or "") or "_atom_site" in (cif or ""))
    if not has_coords:
        return {
            "success": False,
            "error": raw.get("error", "ESMFold2 returned no atomic coordinates"),
            "backend": backend,
            "model": raw.get("model", "esmfold2"),
        }
    return {
        "success": True,
        "pdb": pdb,
        "cif": cif,
        "iptm": _as_float(raw.get("iptm")),
        "plddt": _plddt_0_100(
            raw.get("plddt") if raw.get("plddt") is not None else raw.get("plddt_mean")
        ),
        "ptm": _as_float(raw.get("ptm")),
        "n_residues": int(n_res) if n_res else 0,
        "model": raw.get("model", "esmfold2"),
        "backend": backend,
        "error": None,
    }


def _fallback_chai1(sequences: List[str], ligand_smiles: str = "") -> dict:
    """Graceful fallback to Chai-1 (the other REAL-coordinate folder). Honest:
    reports model='chai-1(fallback)', backend='fallback'."""
    try:
        from pipeline_enhancements import predict_structure_real
    except Exception as e:
        return {
            "success": False,
            "error": f"fallback unavailable: {e}",
            "backend": "fallback",
            "model": "chai-1(fallback)",
        }
    try:
        r = predict_structure_real(sequences, ligand_smiles=ligand_smiles)
        if not r or not r.get("success"):
            return {
                "success": False,
                "error": (r or {}).get("error", "Chai-1 fallback failed"),
                "backend": "fallback",
                "model": "chai-1(fallback)",
            }
        cif = r.get("cif") or ""
        pdb = r.get("pdb") or ""
        agg = _as_float(r.get("aggregate_score"))
        return {
            "success": True,
            "pdb": pdb,
            "cif": cif,
            # Chai-1's aggregate_score is the closest honest proxy; expose as ptm.
            "iptm": None,
            "plddt": None,
            "ptm": agg,
            "aggregate_score": agg,
            "n_residues": r.get("n_residues", 0),
            "model": "chai-1(fallback)",
            "backend": "fallback",
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
            "backend": "fallback",
            "model": "chai-1(fallback)",
        }


# =============================================================================
# PUERTA DE CONFIANZA Y ESCALADO A MSA
# =============================================================================
# MEDIDO 2026-08-30 contra una estructura cristalografica publicada del mismo
# barril beta (225 Ca emparejados, Kabsch + TM-score):
#
#   plegador                      RMSD Ca    TM-score   Ca < 2 A   pLDDT
#   ---------------------------   --------   --------   --------   -----
#   ESMFold2 (secuencia unica)     20.43 A     0.161        0 %      33.8
#   Boltz-2 SIN MSA                17.59 A     0.172        0 %      35.5
#   Boltz-2 CON MSA                 1.15 A     0.971       92 %      94.6
#
# Un TM-score de 0.16 es lo que puntuan dos proteinas SIN RELACION. O sea: no
# era una prediccion insegura, era una prediccion equivocada, y salia con
# success=True. Cualquiera de los modulos que llama aqui la estaba tomando por
# buena.
#
# Aumentar el muestreo NO lo arregla: 200 pasos de difusion y 5 muestras dan el
# mismo pLDDT (44.7 en GFP) que 50 pasos y 1 muestra. El determinante es el
# ALINEAMIENTO. ESMFold2 es de secuencia unica; funciona en plegamientos
# faciles (ubiquitina, pLDDT 81) y se hunde donde hace falta informacion
# evolutiva.
#
# Por eso, desde aqui:
#   1. TODO resultado sale etiquetado con `trustworthy`. Nunca mas un
#      success=True sin decir si es defendible.
#   2. Si cae por debajo del suelo, se reintenta con Boltz-2 CON MSA, que es la
#      unica via medida que reproduce el cristal. Solo se escala cuando hace
#      falta, asi que un plegado bueno no cuesta GPU extra.
#   3. Se acepta el escalado solo si de verdad mejora.
FOLD_PLDDT_FLOOR = 70.0

FOLD_BENCHMARK = {
    "reference": "cristal publicado del mismo barril beta, 225 Ca emparejados",
    "date": "2026-08-30",
    "measured": [
        {
            "folder": "ESMFold2 (secuencia unica)",
            "rmsd_ca_a": 20.43,
            "tm_score": 0.161,
            "ca_within_2a_pct": 0,
            "plddt": 33.8,
        },
        {
            "folder": "Boltz-2 sin MSA",
            "rmsd_ca_a": 17.59,
            "tm_score": 0.172,
            "ca_within_2a_pct": 0,
            "plddt": 35.5,
        },
        {
            "folder": "Boltz-2 con MSA",
            "rmsd_ca_a": 1.15,
            "tm_score": 0.971,
            "ca_within_2a_pct": 92,
            "plddt": 94.6,
        },
    ],
    "sampling_control": (
        "mas muestreo no compensa la falta de MSA: 200 pasos y "
        "5 muestras dan el mismo pLDDT que 50 pasos y 1 muestra"
    ),
    "easy_case_control": (
        "ESMFold2 no esta roto: ubiquitina sale a pLDDT 81. "
        "Falla donde hace falta informacion evolutiva"
    ),
}


def _escalation_allowed() -> tuple:
    """Si se puede pedir el MSA, y por que no cuando no se puede.

    Pedir el MSA envia la secuencia a un servicio externo. Hay trabajo en esta
    plataforma que no puede salir de aqui, asi que existe una forma explicita
    de prohibirlo sin tener que tocar codigo.
    """
    if os.environ.get("BIOQL_FOLD_NO_EXTERNAL_MSA", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "si",
    ):
        return False, (
            "prohibido por BIOQL_FOLD_NO_EXTERNAL_MSA: pedir el MSA "
            "enviaria la secuencia a un servicio externo"
        )
    if os.environ.get("BIOQL_FOLD_ESCALATE_MSA", "1").strip().lower() in ("0", "false", "no"):
        return False, "desactivado por BIOQL_FOLD_ESCALATE_MSA=0"
    return True, None


def _boltz2_with_msa(seqs: List[str], ligand_smiles: str = "") -> dict:
    """Boltz-2 CON MSA. Admite complejo: Boltz separa cadenas por ':'."""
    try:
        import modal_compute_layer

        import modal

        raw = modal_compute_layer.function("bioql-boltz2", "predict").remote(
            {
                "protein_sequence": ":".join(seqs),
                "ligand_smiles": ligand_smiles or "",
                "use_msa_server": True,
            }
        )
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"Boltz-2 no disponible: {type(e).__name__}: {e}"}
    if not isinstance(raw, dict) or not raw.get("success"):
        return {
            "success": False,
            "error": f"Boltz-2 no devolvio estructura: {(raw or {}).get('error')}",
        }
    pdb = raw.get("pdb") or ""
    cif = raw.get("cif") or ""
    if not pdb and cif:
        pdb, _ = _cif_to_pdb(cif)
    if not pdb:
        return {"success": False, "error": "Boltz-2 no devolvio coordenadas"}
    conf = raw.get("confidence") or {}
    return {
        "success": True,
        "pdb": pdb,
        "cif": cif,
        "plddt": _plddt_0_100(conf.get("plddt")),
        "ptm": _as_float(conf.get("ptm")),
        "iptm": _as_float(conf.get("iptm")),
        "n_residues": sum(len(x) for x in seqs),
        "model": "boltz-2 (con MSA)",
        "backend": raw.get("engine", "modal"),
        "external_transmission": (
            "la secuencia se envio al servidor de MSA para " "construir el alineamiento"
        ),
        "error": None,
    }


def _judge(result: dict) -> dict:
    """Etiqueta el resultado. No cambia coordenadas, solo dice que valen."""
    if not isinstance(result, dict):
        return result
    result["confidence_floor"] = FOLD_PLDDT_FLOOR
    result["benchmark"] = FOLD_BENCHMARK
    if not result.get("success"):
        result["trustworthy"] = False
        result["trust_reason"] = result.get("error") or "el plegado no produjo estructura"
        return result
    plddt = _as_float(result.get("plddt"))
    modelo = str(result.get("model") or "")
    if plddt is None:
        # Chai-1 no devuelve pLDDT; su aggregate_score no es comparable con este
        # suelo, asi que no se inventa un veredicto que no se puede sostener.
        result["trustworthy"] = None
        result["trust_reason"] = (
            f"{modelo} no devuelve pLDDT comparable; sin esa medida no se puede "
            f"afirmar ni negar que la estructura sea correcta"
        )
        return result
    ok = plddt >= FOLD_PLDDT_FLOOR
    result["trustworthy"] = bool(ok)
    result["trust_reason"] = (
        f"pLDDT {plddt:.1f} >= suelo {FOLD_PLDDT_FLOOR}"
        if ok
        else f"pLDDT {plddt:.1f} por debajo del suelo {FOLD_PLDDT_FLOOR}. MEDIDO: a "
        f"este nivel el plegado de secuencia unica dio TM-score 0.16 contra el "
        f"cristal, que es lo que puntuan dos proteinas sin relacion"
    )
    return result


def predict_structure_esmfold2(
    sequences: Union[str, List[str]],
    complex: bool = False,
    ligand_smiles: str = "",
    tracker: Optional[Any] = None,
) -> dict:
    """Fold a protein (or multi-chain complex) with ESMFold2; fall back to Chai-1.

    Args:
        sequences:     a single sequence str OR a list of chain sequences.
                       len>1 (or complex=True) -> multi-chain complex fold.
        complex:       force complex/multi-chain folding.
        ligand_smiles: optional ligand (passed through to the fallback folder).

    Returns (NEVER raises):
        {
          "success": bool,
          "pdb": str,            # biopython-converted ATOM records ("" on failure)
          "cif": str,            # raw mmCIF
          "iptm": float|None,    # meaningful for complexes
          "plddt": float|None,   # mean per-residue
          "ptm": float|None,
          "n_residues": int,
          "model": "esmfold2"|"esmfold2-fast"|"chai-1(fallback)",
          "backend": "modal"|"http"|"fallback",
          "error": str|None,
        }
    """
    # Normalize the sequence input.
    if isinstance(sequences, str):
        seqs = [sequences.strip()] if sequences.strip() else []
    else:
        seqs = [s.strip() for s in (sequences or []) if isinstance(s, str) and s.strip()]
    if not seqs:
        return {
            "success": False,
            "error": "no protein sequence(s) provided",
            "backend": "fallback",
            "model": "esmfold2",
            "pdb": "",
            "cif": "",
        }

    is_complex = bool(complex or len(seqs) > 1)

    ck = _cache_key(seqs, is_complex)
    if ck in _cache:
        return _cache[ck]

    payload = {"sequences": seqs, "complex": is_complex}
    if ligand_smiles:
        payload["ligand_smiles"] = ligand_smiles

    result: Optional[dict] = None

    # 1) Preferred: Modal Function.from_name (no web-fn cap).
    try:
        import modal_compute_layer

        import modal as _modal

        fn = modal_compute_layer.function(_MODAL_APP, _MODAL_FN)
        raw = fn.remote(payload)
        if isinstance(raw, dict):
            norm = _normalize_remote(raw, backend="modal")
            if norm.get("success"):
                result = norm
            else:
                log.warning("ESMFold2 modal returned no coords: %s", norm.get("error"))
    except Exception as exc:
        log.warning("ESMFold2 generic Modal function failed (%s); trying deployed API", exc)

    # 1b) The production deployment predates the generic payload wrapper and
    # exposes fold_structure/fold_complex directly. Keep this compatibility
    # path before any non-ESMFold fallback. For NMR, use the production sampler
    # (100 diffusion steps, 3 samples) because structural precision matters.
    if result is None and not is_complex and len(seqs) == 1:
        try:
            import modal_compute_layer

            import modal as _modal

            fn = modal_compute_layer.function(_MODAL_APP, "fold_structure")
            raw = fn.remote(seqs[0], 0, "production")
            if isinstance(raw, dict) and raw.get("success"):
                norm = _normalize_remote(raw, backend="modal")
                if norm.get("success"):
                    norm["sampling_quality"] = raw.get("quality", "production")
                    norm["sampler_config"] = raw.get("sampler_config")
                    result = norm
        except Exception as exc:
            log.warning("ESMFold2 deployed fold_structure failed (%s); trying HTTP/fallback", exc)

    # 2) HTTP transport (only if ESMFOLD2_URL is configured).
    if result is None and ESMFOLD2_URL:
        try:
            import requests

            path = "/predict/complex" if is_complex else "/predict/structure"
            resp = requests.post(
                f"{ESMFOLD2_URL}{path}", json=payload, timeout=_REMOTE_TIMEOUT_S, verify=True
            )
            if resp.status_code == 200:
                raw = resp.json()
                if isinstance(raw, dict):
                    norm = _normalize_remote(raw, backend="http")
                    if norm.get("success"):
                        result = norm
                    else:
                        log.warning("ESMFold2 http returned no coords: %s", norm.get("error"))
            else:
                log.warning("ESMFold2 HTTP -> %s", resp.status_code)
        except Exception as exc:
            log.warning("ESMFold2 HTTP call failed (%s); falling back to Chai-1", exc)

    # 3) Graceful fallback -> Chai-1 (real coords) for the complex / first chain.
    if result is None:
        result = _fallback_chai1(seqs if is_complex else seqs[:1], ligand_smiles=ligand_smiles)

    # 4) Puerta de confianza. Ver FOLD_BENCHMARK: un plegado de secuencia unica
    #    por debajo del suelo no es "poco seguro", es probablemente erroneo.
    result = _judge(result)
    result["escalation"] = {"attempted": False, "reason": "el plegado inicial pasa el suelo"}

    if result.get("trustworthy") is not True:
        permitido, motivo = _escalation_allowed()
        if not permitido:
            result["escalation"] = {"attempted": False, "reason": motivo}
        else:
            log.warning(
                "Fold por debajo del suelo (%s); escalando a Boltz-2 con MSA",
                result.get("trust_reason"),
            )
            alt = _judge(_boltz2_with_msa(seqs, ligand_smiles=ligand_smiles))
            antes = _as_float(result.get("plddt"))
            despues = _as_float(alt.get("plddt"))
            # Solo se acepta si de verdad mejora. Cambiar un plegado malo por
            # otro igual de malo no es un arreglo, es esconder el problema.
            mejora = (
                alt.get("success") and despues is not None and (antes is None or despues > antes)
            )
            if mejora:
                registro = {
                    "attempted": True,
                    "accepted": True,
                    "from_model": result.get("model"),
                    "from_plddt": antes,
                    "to_model": alt.get("model"),
                    "to_plddt": despues,
                    "reason": ("el plegado de secuencia unica no llegaba " "al suelo; con MSA si"),
                }
                result = alt
                result["escalation"] = registro
            else:
                result["escalation"] = {
                    "attempted": True,
                    "accepted": False,
                    "to_plddt": despues,
                    "reason": (
                        alt.get("error")
                        or "el escalado no mejoro el pLDDT; se conserva el "
                        "resultado original, que sigue marcado como no "
                        "defendible"
                    ),
                }

    try:
        _cache[ck] = result
    except Exception:
        pass

    if result and result.get("success") and tracker is not None:
        try:
            tracker.stamp_dag_node(
                node_id=f"esmfold2-{hashlib.sha256(str(sequences).encode()).hexdigest()[:8]}",
                node_type="esmfold_prediction",
                input_data={
                    "sequences": sequences,
                    "complex": is_complex,
                    "ligand_smiles": ligand_smiles,
                },
                output_data={
                    "iptm": result.get("iptm"),
                    "plddt": result.get("plddt"),
                    "ptm": result.get("ptm"),
                    "backend": result.get("backend"),
                },
                metadata={"model": result.get("model")},
            )
        except Exception as e:
            log.warning("Failed to stamp ESMFold2 DAG node: %s", e)

    return result
