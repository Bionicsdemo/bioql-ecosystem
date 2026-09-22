"""
modal_lddm.py -- LDDM (Large Drug Discovery Model) on Modal GPU (BioQL).

What it adds to BioQL
---------------------
A pocket-conditioned 3D GENERATOR. Everything BioQL already runs on small
molecules -- MM-GBSA, FEP, SQD, ADMET, PBPK -- scores molecules somebody else
proposed. LDDM proposes them, in the pocket, with coordinates: de novo design,
fragment growing and linking, docking, partial docking (covalent warheads held
fixed), and synthesizable design over a reaction space.

It does NOT score binding. Its output is geometry; the affinity still comes
from BioQL's own stack. The honest split is: LDDM says "this molecule could sit
here", BioQL says "and this is what it would do".

Upstream: LPDI-EPFL, Igashov/Schneuing et al., bioRxiv 2026.09.15.751537.
Code MIT. Pinned to commit 309ab66 -- the repo is days old and still moving.

CHECKPOINT LICENSING -- read before changing DEFAULT_CKPT
---------------------------------------------------------
Two checkpoints exist and they are NOT interchangeable for us:

  lddm_CDBB.ckpt  MIT         trained without BindingNet   <- BioQL default
  lddm.ckpt       CC-BY-NC-4.0  the paper's model          <- non-commercial only

The NC one is the stronger model and the one every number in the preprint came
from, which makes it exactly the tempting mistake. Every result carries
`checkpoint_license` so a downstream gate can refuse to ship an NC-derived
molecule in a commercial deliverable. Do not default this to the NC model.

Deploy:   modal deploy modal_lddm.py
Warm:     modal run modal_lddm.py::warm   (one-time; see the cache note below)
Test:     modal run modal_lddm.py

MOLEVERA / BIOQL
"""
import modal

app = modal.App("bioql-lddm")

LDDM_COMMIT = "309ab66e49d374f72dfc66442e53ace5947dd10c"
ZENODO = "https://zenodo.org/records/22754501/files"

# Checkpoint -> (filename, license). MIT first, and it is the default.
CHECKPOINTS = {
    "CD+BB": ("lddm_CDBB.ckpt", "MIT"),
    "CD+BB+BN": ("lddm.ckpt", "CC-BY-NC-4.0"),
}
DEFAULT_CKPT = "CD+BB"

# Their own image already carries uv, Gnina and Reduce -- Gnina and Reduce are
# required by the programmable-design workflow and are a nuisance to build.
# Reproducing this from a bare CUDA image means rebuilding a torch 2.6.0+cu124
# + compiled torch-scatter stack by hand; don't.
image = (
    modal.Image.from_registry("schneuing/lddm:0.1.0", add_python="3.11")
    .apt_install("git", "wget")
    .run_commands(
        "git clone https://github.com/LPDI-EPFL/lddm /opt/lddm",
        f"cd /opt/lddm && git checkout {LDDM_COMMIT}",
        "cd /opt/lddm && uv sync",
    )
)

PY = "/opt/lddm/.venv/bin/python"
REPO = "/opt/lddm"

ckpt_vol = modal.Volume.from_name("lddm-checkpoints", create_if_missing=True)
# The geometry reference compiles its distributions on FIRST USE and the
# upstream README warns it "can take substantial time". Without a volume that
# cost is paid on every cold start, so the cache lives beside the SDF here.
geom_vol = modal.Volume.from_name("lddm-geometry", create_if_missing=True)

CKPT_DIR = "/ckpt"
GEOM_DIR = f"{REPO}/data/validity3d"

VOLUMES = {CKPT_DIR: ckpt_vol, GEOM_DIR: geom_vol}
# Project rule: every long-running endpoint gets the 12h timeout. A generative
# batch is minutes, but --n_samples is unbounded and a truncated run wastes the
# whole GPU spend.
TIMEOUT = 43200


def _ensure_checkpoint(model_key: str) -> tuple:
    """Fetch the checkpoint into the volume if absent. Returns (path, license, sha256)."""
    import hashlib
    import os
    import subprocess

    if model_key not in CHECKPOINTS:
        raise ValueError(f"unknown checkpoint {model_key!r}; known: {sorted(CHECKPOINTS)}")
    fname, lic = CHECKPOINTS[model_key]
    path = os.path.join(CKPT_DIR, fname)
    if not os.path.exists(path):
        os.makedirs(CKPT_DIR, exist_ok=True)
        subprocess.run(["wget", "-q", "-O", path, f"{ZENODO}/{fname}"], check=True)
        ckpt_vol.commit()
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return path, lic, h.hexdigest()


def _ensure_geometry() -> bool:
    """Reference geometry for 3D validity / programmable design. False if absent."""
    import os
    import subprocess

    sdf = os.path.join(GEOM_DIR, "ligands.sdf")
    if not os.path.exists(sdf):
        os.makedirs(GEOM_DIR, exist_ok=True)
        try:
            subprocess.run(["wget", "-q", "-O", sdf, f"{ZENODO}/ligands.sdf"], check=True)
            geom_vol.commit()
        except Exception:
            return False
    return os.path.exists(sdf)


def _run_sample(payload: dict, mode: str) -> dict:
    """Shared body of design() and dock(). Writes inputs, shells out to the
    upstream CLI, reads the SDF back. Driving the CLI rather than importing
    `lddm` keeps its pinned torch stack isolated in its own venv."""
    import os
    import subprocess
    import tempfile
    import time
    import traceback
    from pathlib import Path

    t0 = time.time()
    payload = payload or {}
    protein_pdb = payload.get("protein_pdb") or ""
    ref_ligand_sdf = payload.get("ref_ligand_sdf") or ""
    ligand_sdf = payload.get("ligand_sdf") or ""
    model_key = payload.get("checkpoint", DEFAULT_CKPT)

    if not protein_pdb:
        return {"success": False, "error": "protein_pdb (PDB text) is required"}
    if not ref_ligand_sdf:
        return {"success": False, "error":
                "ref_ligand_sdf (SDF text) is required -- it defines the pocket"}
    if mode == "dock" and not ligand_sdf:
        return {"success": False, "error": "ligand_sdf is required in dock mode"}

    try:
        ckpt, lic, sha = _ensure_checkpoint(model_key)
    except Exception as e:
        return {"success": False, "error": f"checkpoint: {type(e).__name__}: {str(e)[:200]}"}

    try:
        work = Path(tempfile.mkdtemp())
        (work / "protein.pdb").write_text(protein_pdb)
        (work / "ref.sdf").write_text(ref_ligand_sdf)
        out = work / "samples.sdf"

        cmd = [PY, "scripts/sample.py", mode,
               "--protein", str(work / "protein.pdb"),
               "--ref_ligand", str(work / "ref.sdf"),
               "--checkpoint", ckpt,
               "--output", str(out),
               "--n_samples", str(int(payload.get("n_samples", 10))),
               "--n_steps", str(int(payload.get("n_steps", 100))),
               "--sampler", str(payload.get("sampler", "ForwardEuler")),
               "--sampling_noise", str(float(payload.get("sampling_noise", 5.0)))]
        if ligand_sdf:
            (work / "ligand.sdf").write_text(ligand_sdf)
            cmd += ["--ligand", str(work / "ligand.sdf")]
        if payload.get("batch_size"):
            cmd += ["--batch_size", str(int(payload["batch_size"]))]
        if mode == "design" and payload.get("molecule_size"):
            cmd += ["--molecule_size", str(payload["molecule_size"])]
        if mode == "dock" and payload.get("atoms_to_dock"):
            cmd += ["--atoms_to_dock"] + [str(int(a)) for a in payload["atoms_to_dock"]]
        # A seed is not optional for us: an unseeded generative run cannot be
        # reproduced from the manifest, and an irreproducible molecule is not
        # evidence of anything.
        seed = int(payload.get("seed", 42))
        cmd += ["--seed", str(seed)]

        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                              timeout=TIMEOUT - 120,
                              env={**os.environ, "PYTHONUNBUFFERED": "1"})
        if not out.exists():
            return {"success": False,
                    "error": "LDDM produced no SDF",
                    "returncode": proc.returncode,
                    "stderr": (proc.stderr or "")[-1500:],
                    "stdout": (proc.stdout or "")[-500:]}

        sdf_text = out.read_text()
        n_mols = sdf_text.count("$$$$")
        return {
            "success": n_mols > 0,
            "model": "LDDM",
            "mode": mode,
            "sdf": sdf_text,
            "n_molecules": n_mols,
            "checkpoint": model_key,
            "checkpoint_file": os.path.basename(ckpt),
            "checkpoint_license": lic,
            "checkpoint_sha256": sha,
            "commit": LDDM_COMMIT,
            "seed": seed,
            "n_steps": int(payload.get("n_steps", 100)),
            "sampler": str(payload.get("sampler", "ForwardEuler")),
            "sampling_noise": float(payload.get("sampling_noise", 5.0)),
            "elapsed_s": round(time.time() - t0, 1),
            "engine": f"LDDM {model_key} (Modal A100)",
            "honest_note": (
                "Generated 3D geometry only. LDDM predicts no binding affinity; "
                "these poses are unscored candidates until BioQL's own scoring "
                "stack runs on them. Validate with ligand_pose_gate first."
            ),
            "commercial_use_ok": (lic == "MIT"),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "LDDM sampling timed out"}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {str(e)[:400]}",
                "trace": traceback.format_exc()[-800:]}


@app.function(image=image, gpu="A100", timeout=TIMEOUT, volumes=VOLUMES)
def design(payload: dict):
    """De novo design, fragment growing, or fragment linking.

    Growing/linking is the same call with `ligand_sdf` set to the fragment(s);
    with no fragment it is unconstrained de novo design in the pocket.
    """
    return _run_sample(payload, "design")


@app.function(image=image, gpu="A100", timeout=TIMEOUT, volumes=VOLUMES)
def dock(payload: dict):
    """Docking, or partial docking when `atoms_to_dock` is given.

    Partial docking is the covalent case: the atoms NOT listed keep their input
    coordinates, so a warhead stays anchored while the rest is posed.
    """
    return _run_sample(payload, "dock")


@app.function(image=image, gpu="H100", timeout=TIMEOUT, volumes=VOLUMES)
def programmable(payload: dict):
    """Programmable / synthesizable design, driven by an upstream YAML config.

    This is the mode the paper's prospective campaigns used: fine-grained
    objectives, and -- with a reaction space -- molecules that come with a
    synthesis route instead of a synthesizability score. Upstream timings on an
    H100: ~8 min programmable, ~21 min synthesizable.

    The bundled reaction space is the SynSpace demo (44,944 building blocks,
    3 reactions). Enamine REAL is licensed and cannot be redistributed, so real
    synthesizable design needs our own license and a prepared space.
    """
    import subprocess
    import tempfile
    import time
    import traceback
    from pathlib import Path

    t0 = time.time()
    payload = payload or {}
    config_yaml = payload.get("config_yaml")
    if not config_yaml:
        return {"success": False, "error":
                "config_yaml (text of a controlled_generation config) is required"}

    model_key = payload.get("checkpoint", DEFAULT_CKPT)
    try:
        ckpt, lic, sha = _ensure_checkpoint(model_key)
    except Exception as e:
        return {"success": False, "error": f"checkpoint: {type(e).__name__}: {str(e)[:200]}"}

    geometry_ok = _ensure_geometry()
    if not geometry_ok:
        return {"success": False, "error":
                "geometry reference (data/validity3d/ligands.sdf) unavailable; "
                "programmable design needs it. Run warm() first."}

    try:
        work = Path(tempfile.mkdtemp())
        for name, text in (payload.get("input_files") or {}).items():
            (work / Path(name).name).write_text(text)
        cfg = work / "config.yml"
        cfg.write_text(config_yaml.replace("{{WORKDIR}}", str(work))
                                  .replace("{{CHECKPOINT}}", ckpt))

        proc = subprocess.run([PY, "scripts/generate_programmable_design.py", str(cfg)],
                              cwd=REPO, capture_output=True, text=True,
                              timeout=TIMEOUT - 120)
        sdfs = sorted(work.rglob("*.sdf"))
        outputs = {p.name: p.read_text() for p in sdfs
                   if p.name not in {f for f in (payload.get("input_files") or {})}}
        return {
            "success": bool(outputs),
            "model": "LDDM",
            "mode": "programmable",
            "outputs": outputs,
            "n_files": len(outputs),
            "checkpoint": model_key,
            "checkpoint_license": lic,
            "checkpoint_sha256": sha,
            "commit": LDDM_COMMIT,
            "commercial_use_ok": (lic == "MIT"),
            "elapsed_s": round(time.time() - t0, 1),
            "engine": f"LDDM {model_key} programmable (Modal H100)",
            "returncode": proc.returncode,
            "stderr_tail": (proc.stderr or "")[-1200:] if not outputs else None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "programmable design timed out"}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {str(e)[:400]}",
                "trace": traceback.format_exc()[-800:]}


@app.function(image=image, gpu="A100", timeout=TIMEOUT, volumes=VOLUMES)
def warm(checkpoint: str = DEFAULT_CKPT):
    """One-time: pull the checkpoint and compile the geometry cache into the
    volumes, so the first real call is not paying for a download and a long
    distribution build on a GPU that is sitting idle."""
    import os
    import time

    t0 = time.time()
    out = {"checkpoint_requested": checkpoint}
    try:
        path, lic, sha = _ensure_checkpoint(checkpoint)
        out.update({"checkpoint_ok": True, "checkpoint_license": lic,
                    "checkpoint_sha256": sha,
                    "size_mb": round(os.path.getsize(path) / 1e6, 1)})
    except Exception as e:
        out.update({"checkpoint_ok": False,
                    "error": f"{type(e).__name__}: {str(e)[:200]}"})
    out["geometry_ok"] = _ensure_geometry()
    if out["geometry_ok"]:
        try:
            from subprocess import run
            run([PY, "-c",
                 "from lddm.sbdd_metrics.validity_3d.validity3d import *  # noqa"],
                cwd=REPO, capture_output=True, timeout=3600)
            geom_vol.commit()
            out["geometry_cache_built"] = True
        except Exception as e:
            out["geometry_cache_built"] = False
            out["geometry_note"] = f"{type(e).__name__}: {str(e)[:160]}"
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


@app.local_entrypoint()
def main():
    """GPU smoke test: design 4 ligands in the upstream KRAS pocket."""
    import json
    import urllib.request

    base = f"https://raw.githubusercontent.com/LPDI-EPFL/lddm/{LDDM_COMMIT}/examples"
    get = lambda n: urllib.request.urlopen(f"{base}/{n}").read().decode()
    r = design.remote({"protein_pdb": get("kras.pdb"),
                       "ref_ligand_sdf": get("kras_ref_ligand.sdf"),
                       "n_samples": 4, "n_steps": 100, "seed": 42})
    print(json.dumps({k: v for k, v in r.items() if k != "sdf"}, indent=2)[:1400])

# MOLEVERA / BIOQL
