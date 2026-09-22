"""Pose-validity gate for generated ligands -- the cheap filter before the dear one.

Why this exists
---------------
Every generative ligand source BioQL uses (LDDM, DiffDock, Boltz-2 co-folding,
the de-novo designers) emits 3D poses that LOOK like molecules and are not:
broken valences, disconnected fragments, flattened rings that should pucker,
atoms inside the protein. Sending those downstream is the expensive mistake --
MM-GBSA, FEP and SQD each cost GPU-minutes to tell you what a sub-second
geometry check already knew.

So this runs first, locally, on CPU, and only the survivors reach the scoring
stack. It is a FILTER, not a score: it never ranks binders, it removes
non-molecules.

Engine: PoseBusters (Buttenschoen, Morris & Deane 2024, BSD-3), the standard
the docking field already reports against. With a receptor it runs the full
`dock` battery (21 checks incl. protein clashes and pocket containment);
without one, the `mol` battery (intramolecular only) and the record SAYS which.

Honest contract, same as the rest of the gates
----------------------------------------------
NEVER RAISES. If PoseBusters is missing or the input is unreadable, the record
comes back `checked: False` with `gate_error` set, and `verdict: "unchecked"`.
Unchecked is NOT the same as passed, and no caller may read it as such --
`n_valid` is None in that case, never 0 and never n_poses.

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

_PB_CONFIG_WITH_RECEPTOR = "dock"
_PB_CONFIG_LIGAND_ONLY = "mol"

# Checks that are bookkeeping, not chemistry -- their failure means "we could
# not read the input", which the loader already reports.
_NON_CHECK_COLUMNS = {"file", "molecule", "mol_pred_loaded", "mol_cond_loaded",
                      "mol_true_loaded"}


def available() -> Dict[str, Any]:
    """Can the gate actually run? Does not check any pose, so it costs nothing."""
    out: Dict[str, Any] = {"posebusters": False, "rdkit": False, "sa_score": False}
    try:
        import posebusters  # noqa: F401
        out["posebusters"] = True
        out["posebusters_version"] = getattr(posebusters, "__version__", "?")
    except Exception as e:
        out["posebusters_reason"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    try:
        import rdkit  # noqa: F401
        out["rdkit"] = True
    except Exception:
        pass
    try:
        import synthesizability
        out["sa_score"] = bool(synthesizability.available().get("sa_score"))
    except Exception:
        pass
    out["ready"] = out["posebusters"] and out["rdkit"]
    return out


def _materialize(data: Optional[str], suffix: str) -> Optional[str]:
    """Accept either a path on disk or raw file text; return a path either way."""
    if not data:
        return None
    if len(data) < 4096 and os.path.exists(data):
        return data
    fh = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False)
    fh.write(data)
    fh.close()
    return fh.name


def _sa_score(smiles: Optional[str]) -> Optional[float]:
    if not smiles:
        return None
    try:
        import synthesizability
        return synthesizability.sa_score(smiles)
    except Exception:
        return None


def check_poses(ligand_sdf: str,
                receptor_pdb: Optional[str] = None,
                *,
                source: Optional[str] = None,
                with_sa_score: bool = True,
                max_poses: Optional[int] = None) -> Dict[str, Any]:
    """Validate generated ligand poses. Never raises.

    ligand_sdf / receptor_pdb may each be a path or the file's raw text.
    `source` is free text recorded in the result (e.g. "LDDM CD+BB") so the
    provenance manifest can say which generator produced the poses.
    """
    rec: Dict[str, Any] = {
        "gate": "ligand_pose_validity",
        "checked": False,
        "verdict": "unchecked",
        "source": source,
        "receptor_aware": bool(receptor_pdb),
        "n_poses": None,
        "n_valid": None,
        "pass_rate": None,
        "poses": [],
    }

    lig_path = None
    rcp_path = None
    try:
        from rdkit import Chem, RDLogger
        RDLogger.DisableLog("rdApp.*")
        from posebusters import PoseBusters

        lig_path = _materialize(ligand_sdf, ".sdf")
        if not lig_path or not os.path.exists(lig_path):
            rec["gate_error"] = "ligand SDF not readable"
            rec["note"] = "Gate did not run. Unchecked is not the same as passed."
            return rec
        rcp_path = _materialize(receptor_pdb, ".pdb") if receptor_pdb else None
        rec["receptor_aware"] = bool(rcp_path)

        config = _PB_CONFIG_WITH_RECEPTOR if rcp_path else _PB_CONFIG_LIGAND_ONLY
        rec["engine"] = "PoseBusters (%s battery)" % config
        rec["battery"] = config
        if not rcp_path:
            rec["battery_note"] = ("No receptor given, so protein clashes and "
                                   "pocket containment were NOT checked.")

        # SMILES per pose, read independently of PoseBusters so a pose that
        # fails sanitization still gets an identity in the record.
        supplier = Chem.SDMolSupplier(lig_path, sanitize=False, removeHs=False)
        smiles: List[Optional[str]] = []
        for mol in supplier:
            if mol is None:
                smiles.append(None)
                continue
            try:
                smiles.append(Chem.MolToSmiles(mol))
            except Exception:
                smiles.append(None)
        rec["n_poses"] = len(smiles)
        if not smiles:
            rec["gate_error"] = "SDF contained no molecules"
            rec["note"] = "Gate did not run. Unchecked is not the same as passed."
            return rec

        buster = PoseBusters(config=config)
        df = buster.bust([lig_path], None, rcp_path)

        check_cols = [c for c in df.columns if c not in _NON_CHECK_COLUMNS]

        def _passed(value: Any) -> bool:
            """PoseBusters returns numpy booleans, and NaN where a check could
            not be evaluated. `value is True` would reject numpy.True_, and
            `bool(nan)` is True -- so neither shortcut is safe here."""
            try:
                import pandas as _pd
                if value is None or _pd.isna(value):
                    return False
            except Exception:
                if value is None:
                    return False
            return bool(value)
        poses: List[Dict[str, Any]] = []
        for i, (_, row) in enumerate(df.iterrows()):
            if max_poses is not None and i >= max_poses:
                break
            failed = [c for c in check_cols if not _passed(row.get(c))]
            smi = smiles[i] if i < len(smiles) else None
            entry: Dict[str, Any] = {
                "index": i,
                "smiles": smi,
                "valid": not failed,
                "failed_checks": failed,
                "n_checks": len(check_cols),
            }
            if with_sa_score:
                entry["sa_score"] = _sa_score(smi)
            poses.append(entry)

        n_valid = sum(1 for p in poses if p["valid"])
        rec.update({
            "checked": True,
            "poses": poses,
            "n_poses": len(poses),
            "n_valid": n_valid,
            "pass_rate": round(n_valid / len(poses), 4) if poses else None,
            "checks_applied": check_cols,
            "verdict": "pass" if n_valid else "fail",
            "note": ("Geometric validity only. A valid pose is not a predicted "
                     "binder -- affinity comes from the scoring stack."),
        })
        return rec
    except Exception as e:
        rec["gate_error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        rec["note"] = "Gate did not run. Unchecked is not the same as passed."
        return rec
    finally:
        for p, given in ((lig_path, ligand_sdf), (rcp_path, receptor_pdb)):
            if p and given and p != given:
                try:
                    os.unlink(p)
                except Exception:
                    pass


def filter_sdf(ligand_sdf: str,
               receptor_pdb: Optional[str] = None,
               output_path: Optional[str] = None,
               *,
               source: Optional[str] = None,
               max_sa_score: Optional[float] = None) -> Dict[str, Any]:
    """Keep only the poses that pass, write them out, report what was dropped.

    This is the call that saves GPU time: run it between a generator and
    MM-GBSA / FEP / SQD. On a gate error NOTHING is dropped -- the original set
    passes through with `checked: False`, because silently discarding molecules
    on a failed check is worse than scoring a few bad ones.

    `max_sa_score` additionally drops poses the SA scorer rates harder to make
    than the threshold (Ertl scale 1-10, higher = harder). Off by default.
    """
    result = check_poses(ligand_sdf, receptor_pdb, source=source)
    out: Dict[str, Any] = dict(result)
    out["output_path"] = None
    out["n_written"] = None
    out["n_dropped"] = None

    if not result.get("checked"):
        out["passthrough"] = True
        out["passthrough_reason"] = ("gate did not run, so no pose was dropped; "
                                     "downstream input is UNFILTERED")
        return out

    keep = {p["index"] for p in result["poses"] if p["valid"]}
    if max_sa_score is not None:
        keep = {p["index"] for p in result["poses"]
                if p["valid"] and (p.get("sa_score") is None
                                   or p["sa_score"] <= max_sa_score)}
        out["max_sa_score"] = max_sa_score

    lig_path = None
    try:
        from rdkit import Chem
        lig_path = _materialize(ligand_sdf, ".sdf")
        dest = output_path or tempfile.NamedTemporaryFile(
            suffix="_filtered.sdf", delete=False).name
        supplier = Chem.SDMolSupplier(lig_path, sanitize=False, removeHs=False)
        writer = Chem.SDWriter(dest)
        written = 0
        for i, mol in enumerate(supplier):
            if mol is None or i not in keep:
                continue
            writer.write(mol)
            written += 1
        writer.close()
        out["output_path"] = dest
        out["n_written"] = written
        out["n_dropped"] = (result.get("n_poses") or 0) - written
        out["passthrough"] = False
        return out
    except Exception as e:
        out["gate_error"] = "write failed: %s: %s" % (type(e).__name__, str(e)[:160])
        out["passthrough"] = True
        out["passthrough_reason"] = "could not write filtered SDF; nothing dropped"
        return out
    finally:
        if lig_path and lig_path != ligand_sdf:
            try:
                os.unlink(lig_path)
            except Exception:
                pass


if __name__ == "__main__":
    import json
    import sys
    av = available()
    print("available:", json.dumps(av))
    if len(sys.argv) >= 2:
        r = check_poses(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
                        source="cli")
        print(json.dumps({k: v for k, v in r.items() if k != "poses"}, indent=2))
        for p in r.get("poses", [])[:10]:
            print("  pose %d valid=%s sa=%s failed=%s"
                  % (p["index"], p["valid"], p.get("sa_score"), p["failed_checks"]))

# MOLEVERA / BIOQL
