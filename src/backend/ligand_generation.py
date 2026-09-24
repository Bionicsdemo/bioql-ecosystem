"""One door for generative ligand design: GPU generation, then the pose gate.

BioQL scores molecules; until now something else had to propose them. This is
the proposing step -- LDDM on Modal GPU -- wired so the monolith needs one call
and gets back only poses that survived a geometry check, plus the record of
what was generated, under which licence, and what was thrown away.

The order matters. Generation is GPU-minutes; the gate is CPU-seconds. Running
the gate first, locally, means MM-GBSA / FEP / SQD never spend a GPU on a
molecule whose rings are flat or whose atoms sit inside the protein.

What this does NOT do: predict binding. LDDM outputs geometry. Affinity comes
from BioQL's own stack, downstream of here, and nothing in this module writes a
number that could be mistaken for one.

    import ligand_generation as LG
    r = LG.design(protein_pdb=pdb_text, ref_ligand_sdf=ref_sdf, n_samples=32)
    r["sdf"]          -> only the poses that passed
    r["pose_gate"]    -> what was checked, what failed, what was dropped
    r["provenance"]   -> checkpoint, sha256, licence, seed, commit

MOLEVERA / BIOQL
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_JOB = {"design": "ligand_design", "dock": "ligand_dock"}


def _record(mode: str, why: str, **extra) -> Dict[str, Any]:
    out = {
        "success": False,
        "mode": mode,
        "where_it_ran": "unavailable",
        "why": why,
        "sdf": None,
        "n_generated": None,
        "n_passed": None,
        "no_local_equivalent": True,
        "note": (
            "Pocket-conditioned 3D generation has no honest CPU "
            "stand-in, so nothing was substituted."
        ),
    }
    out.update(extra)
    return out


def _generate(mode: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    try:
        import modal_compute_layer as MC
    except Exception as e:
        return _record(mode, f"modal_compute_layer unimportable: {str(e)[:140]}")
    r = MC.run(_JOB[mode], payload, local_fn=None, timeout=timeout)
    if not MC.ran_remotely(r):
        return _record(
            mode,
            r.get("why", "remote GPU path (Modal / Brev) unavailable"),
            would_fallback_to=r.get("would_fallback_to"),
        )
    return {
        "where_it_ran": r["where_it_ran"],
        "result": r.get("result") or {},
        "compute_provenance": r.get("provenance"),
        "elapsed_s": r.get("elapsed_s"),
    }


def _run(
    mode: str,
    protein_pdb: str,
    ref_ligand_sdf: str,
    ligand_sdf: Optional[str] = None,
    *,
    n_samples: int = 10,
    n_steps: int = 100,
    seed: int = 42,
    checkpoint: str = "CD+BB",
    atoms_to_dock: Optional[List[int]] = None,
    molecule_size: Optional[Any] = None,
    gate: bool = True,
    timeout: int = 43200,
    **kwargs,
) -> Dict[str, Any]:
    t0 = time.time()
    payload: Dict[str, Any] = {
        "protein_pdb": protein_pdb,
        "ref_ligand_sdf": ref_ligand_sdf,
        "n_samples": n_samples,
        "n_steps": n_steps,
        "seed": seed,
        "checkpoint": checkpoint,
    }
    if ligand_sdf:
        payload["ligand_sdf"] = ligand_sdf
    if atoms_to_dock:
        payload["atoms_to_dock"] = list(atoms_to_dock)
    if molecule_size is not None:
        payload["molecule_size"] = molecule_size
    payload.update(kwargs)

    gen = _generate(mode, payload, timeout)
    if gen.get("where_it_ran") == "unavailable":
        return gen
    res = gen["result"]
    if not res.get("success"):
        return _record(
            mode,
            res.get("error", "LDDM reported failure"),
            where_it_ran=gen["where_it_ran"],
            stderr=res.get("stderr"),
        )

    provenance = {
        k: res.get(k)
        for k in (
            "checkpoint",
            "checkpoint_file",
            "checkpoint_license",
            "checkpoint_sha256",
            "commit",
            "seed",
            "n_steps",
            "sampler",
            "sampling_noise",
            "commercial_use_ok",
        )
    }
    provenance["model"] = "LDDM"
    provenance["source"] = "LPDI-EPFL/lddm"

    out: Dict[str, Any] = {
        "success": True,
        "mode": mode,
        "where_it_ran": gen["where_it_ran"],
        "compute_provenance": gen.get("compute_provenance"),
        "engine": res.get("engine"),
        "sdf": res.get("sdf"),
        "n_generated": res.get("n_molecules"),
        "n_passed": None,
        "provenance": provenance,
        "generation_s": res.get("elapsed_s"),
        "honest_note": (
            "Unscored 3D candidates. LDDM predicts no affinity; "
            "binding numbers must come from BioQL's scoring stack."
        ),
    }
    # A CC-BY-NC checkpoint taints everything downstream of it, so say so here
    # rather than leaving a licence field for somebody to notice later.
    if provenance.get("checkpoint_license") != "MIT":
        out["licence_warning"] = (
            f"Generated with a {provenance.get('checkpoint_license')} checkpoint: "
            "these molecules may not be used in a commercial deliverable."
        )

    if gate:
        try:
            import ligand_pose_gate as PG

            g = PG.filter_sdf(
                res["sdf"], protein_pdb, source=f"LDDM {provenance.get('checkpoint')}"
            )
            out["pose_gate"] = {k: v for k, v in g.items() if k != "poses"}
            out["poses"] = g.get("poses", [])
            if g.get("checked") and not g.get("passthrough"):
                path = g.get("output_path")
                if path:
                    with open(path) as fh:
                        out["sdf"] = fh.read()
                out["n_passed"] = g.get("n_written")
                out["n_dropped"] = g.get("n_dropped")
            else:
                out["gate_warning"] = "pose gate did not run; the SDF is " "UNFILTERED " + str(
                    g.get("gate_error")
                )
        except Exception as e:
            out["gate_warning"] = f"pose gate unavailable: {type(e).__name__}: {str(e)[:140]}"
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def design(
    protein_pdb: str, ref_ligand_sdf: str, ligand_sdf: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """De novo design in the pocket; with `ligand_sdf`, fragment growing/linking."""
    return _run("design", protein_pdb, ref_ligand_sdf, ligand_sdf, **kwargs)


def dock(
    protein_pdb: str,
    ref_ligand_sdf: str,
    ligand_sdf: str,
    atoms_to_dock: Optional[List[int]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Generative docking. `atoms_to_dock` poses only those atoms -- the
    covalent case, where the warhead stays where the chemistry puts it."""
    return _run(
        "dock", protein_pdb, ref_ligand_sdf, ligand_sdf, atoms_to_dock=atoms_to_dock, **kwargs
    )


def status() -> Dict[str, Any]:
    """Can this run at all right now? Cheap: no GPU, no generation."""
    out: Dict[str, Any] = {}
    try:
        import modal_compute_layer as MC

        st = MC.app_status()
        out["modal"] = {k: v for k, v in (st.get("apps") or {}).items() if k in _JOB.values()}
        out["modal_enabled"] = st.get("enabled")
    except Exception as e:
        out["modal_error"] = f"{type(e).__name__}: {str(e)[:140]}"
    try:
        import ligand_pose_gate as PG

        out["pose_gate"] = PG.available()
    except Exception as e:
        out["pose_gate_error"] = f"{type(e).__name__}: {str(e)[:140]}"
    return out


if __name__ == "__main__":
    import json

    print(json.dumps(status(), indent=2))

# MOLEVERA / BIOQL
