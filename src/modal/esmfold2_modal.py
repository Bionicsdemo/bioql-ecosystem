#!/usr/bin/env python3
"""
BioQL ESMFold2 — Modal A100 deployment
======================================

REAL ESMFold2 (Biohub, MIT, released 2026-05-27) protein / complex structure
prediction. ESMFold2 runs on top of the 6.35B-parameter ESMC backbone, so it
needs an A100-40GB (an L4 24GB OOMs for non-trivial lengths) — this is why this
is a Modal A100 app, NOT a local-macbook capability.

Called from the backend via:
    modal.Function.from_name("bioql-esmfold2-service", "predict").remote(payload)
(the SDK Function path, NOT a web endpoint — this dodges Modal's 8-web-function
workspace cap, exactly like the Chai-1 app `bioql-chai1`).

Deploy:
    modal deploy src/modal/esmfold2_modal.py

Payload shape (matches src/backend/esmfold2_backend.py):
    {"sequences": ["SEQ_A", "SEQ_B", ...], "complex": bool, "ligand_smiles"?: str}

Returns:
    {"success": bool, "cif": str, "pdb": str, "iptm": float|None,
     "plddt": float|None, "ptm": float|None, "n_residues": int,
     "model": "esmfold2"|"esmfold2-fast", "error": str|None}

HONESTY: returns genuine model output only; on failure returns success=False
with an error (the backend then falls back to Chai-1). Never fabricates coords.

Copyright (c) 2026 MOLEVERA / BIOQL. All rights reserved.
"""

import modal

# Nombre propio: "bioql-esmfold2" ya es la app de src/backend/modal_esmfold2.py
# (fold_structure / fold_complex, redesplegada 2026-09-21). Con el mismo nombre,
# desplegar este archivo reemplazaba esa app y viceversa (2026-09-24).
app = modal.App("bioql-esmfold2-service")

# ESMFold2 needs the `esm` git package + a transformers build exposing
# transformers.models.esmfold2, plus torch + biopython for CIF->PDB.
esmfold2_image = (
    modal.Image.from_registry("nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04", add_python="3.12")
    .apt_install("git", "wget", "build-essential")
    .pip_install(
        [
            "torch>=2.1.0",
            "numpy",
            "scipy",
            "biopython",
            "huggingface_hub",
        ]
    )
    .run_commands(
        # The Biohub `esm` package + matching transformers (exposes esmfold2).
        "pip install 'esm @ git+https://github.com/Biohub/esm.git@c94ed8d'",
    )
    .env(
        {
            "HF_HOME": "/hf_cache",
            "HF_HUB_CACHE": "/hf_cache/hub",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        }
    )
)

results_vol = modal.Volume.from_name("bioql-gpu-results", create_if_missing=True)
hf_cache_vol = modal.Volume.from_name("bioql-hf-cache", create_if_missing=True)

VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _cif_to_pdb(cif: str):
    """mmCIF -> PDB (ATOM records) via biopython. Returns (pdb, n_res)."""
    import os
    import tempfile

    if not cif:
        return "", 0
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
    except Exception:
        pass
    finally:
        for p in (cifp, pdbp):
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass
    return pdb_text, n_res


# --- configuracion del muestreador -------------------------------------------
# MEDIDO 2026-08-30 con los valores fijos que habia aqui (50 pasos, 1 muestra):
#   ubiquitina (76 aa, plegamiento facil) ..... pLDDT 0.81
#   GFP (238 aa, barril beta) ................. pLDDT 0.45
#   KillerRed (225 aa, barril beta) ........... pLDDT 0.34, CERO residuos > 70
# Ubiquitina sale bien y los barriles beta se hunden. Un barril beta con
# estructura cristalografica publicada no puede puntuar 0.34: el limite estaba
# en el muestreo, no en la proteina. Por eso los parametros dejan de estar
# fijados en duro y viajan en el payload.
#
# Los valores por defecto son EXACTAMENTE los que habia antes, para que ningun
# llamador existente cambie de comportamiento sin pedirlo.
SAMPLER_DEFAULTS = {
    "num_loops": 3,
    "num_sampling_steps": 50,
    "num_diffusion_samples": 1,
    "seed": 0,
}

# Perfiles con nombre. "production" gasta mas GPU a cambio de mas pasos de
# difusion y un ensemble best-of-N, que es donde se juega un barril beta.
SAMPLER_PROFILES = {
    "fast": {"num_sampling_steps": 50, "num_diffusion_samples": 1, "num_loops": 3},
    "production": {"num_sampling_steps": 100, "num_diffusion_samples": 3, "num_loops": 3},
    "max": {"num_sampling_steps": 200, "num_diffusion_samples": 5, "num_loops": 4},
}


def _sampler_cfg(payload: dict) -> dict:
    """Resuelve el muestreador: perfil por nombre, y overrides explicitos encima."""
    cfg = dict(SAMPLER_DEFAULTS)
    perfil = str(payload.get("quality") or payload.get("profile") or "").lower()
    if perfil in SAMPLER_PROFILES:
        cfg.update(SAMPLER_PROFILES[perfil])
        cfg["profile"] = perfil
    for k in ("num_loops", "num_sampling_steps", "num_diffusion_samples", "seed"):
        if payload.get(k) is not None:
            try:
                cfg[k] = int(payload[k])
                cfg["profile"] = "custom"
            except (TypeError, ValueError):
                pass
    cfg.setdefault("profile", "default")
    return cfg


@app.cls(
    image=esmfold2_image,
    gpu="a100-80gb",
    timeout=3600,
    scaledown_window=300,
    volumes={"/results": results_vol, "/hf_cache": hf_cache_vol},
)
class ESMFold2Service:

    @modal.enter()
    def setup(self):
        import torch

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None
        self._fast_model = None

    def _load(self, fast: bool):
        from transformers.models.esmfold2.modeling_esmfold2 import ESMFold2Model

        if fast:
            if self._fast_model is None:
                self._fast_model = (
                    ESMFold2Model.from_pretrained("biohub/ESMFold2-Fast").to(self.device).eval()
                )
            try:
                hf_cache_vol.commit()
            except Exception:
                pass
            return self._fast_model
        if self._model is None:
            self._model = ESMFold2Model.from_pretrained("biohub/ESMFold2").to(self.device).eval()
        try:
            hf_cache_vol.commit()
        except Exception:
            pass
        return self._model

    @modal.method()
    def predict(self, payload: dict) -> dict:
        """Fold a protein (single chain) or complex (multi-chain). Never raises."""
        try:
            seqs = [
                s.strip()
                for s in (payload.get("sequences") or [])
                if isinstance(s, str) and s.strip()
            ]
            if not seqs:
                return {"success": False, "error": "no sequences provided"}
            is_complex = bool(payload.get("complex") or len(seqs) > 1)

            # Both single-chain and multi-chain use the DOCUMENTED builder path,
            # which is the only one that exports coordinates (result.complex.to_mmcif()).
            # infer_protein() returns only plddt/ptm tensors, no structure -> that was
            # the "no structure produced" bug.
            from esm.models.esmfold2 import (
                ESMFold2InputBuilder,
                ProteinInput,
                StructurePredictionInput,
            )

            model = self._load(fast=False)
            inputs = [ProteinInput(id=chr(65 + i), sequence=s) for i, s in enumerate(seqs)]
            spi = StructurePredictionInput(sequences=inputs)
            cfg = _sampler_cfg(payload)
            result = ESMFold2InputBuilder().fold(
                model,
                spi,
                num_loops=cfg["num_loops"],
                num_sampling_steps=cfg["num_sampling_steps"],
                num_diffusion_samples=cfg["num_diffusion_samples"],
                seed=cfg["seed"],
            )

            def _g(obj, name):
                v = getattr(obj, name, None)
                try:
                    return (
                        float(v.mean())
                        if hasattr(v, "mean")
                        else (float(v) if v is not None else None)
                    )
                except Exception:
                    return None

            # MEDIDO 2026-08-30: con num_diffusion_samples > 1 el constructor
            # devuelve una LISTA de muestras, no un objeto. El codigo anterior
            # hacia getattr(result, "complex") sobre la lista, no encontraba
            # to_mmcif y salia con "empty cif". Por eso el perfil de mas calidad
            # nunca llego a ejecutarse: no es que diera peor resultado, es que
            # no devolvia estructura. Aqui se elige la mejor muestra por pLDDT,
            # que es justamente para lo que sirve un ensemble best-of-N.
            muestras = list(result) if isinstance(result, (list, tuple)) else [result]
            elegido, cif, mejor = None, "", None
            fallos = []
            for i, cand in enumerate(muestras):
                try:
                    comp = getattr(cand, "complex", None) or cand
                    c = comp.to_mmcif() if hasattr(comp, "to_mmcif") else ""
                except Exception as _ce:  # noqa: BLE001
                    fallos.append(f"muestra {i}: {type(_ce).__name__}: {_ce}")
                    continue
                if not c:
                    fallos.append(f"muestra {i}: mmcif vacio")
                    continue
                score = _g(cand, "plddt")
                if mejor is None or (score is not None and score > mejor):
                    elegido, cif, mejor = cand, c, score
            if not cif:
                _attrs = ",".join(a for a in dir(muestras[0]) if not a.startswith("_"))[:300]
                return {
                    "success": False,
                    "model": "esmfold2",
                    "sampler_config": cfg,
                    "error": (
                        f"ninguna de las {len(muestras)} muestras produjo "
                        f"estructura: {'; '.join(fallos)[:300]}; "
                        f"attrs=[{_attrs}]"
                    ),
                }
            result = elegido
            seleccion = {
                "n_samples": len(muestras),
                "selected_plddt": mejor,
                "all_plddt": [_g(c, "plddt") for c in muestras],
                "criterion": "mayor pLDDT medio entre las muestras",
            }

            pdb, n_res = _cif_to_pdb(cif)
            return {
                "success": bool(cif),
                "cif": cif,
                "pdb": pdb,
                "iptm": _g(result, "iptm") if is_complex else None,
                "plddt": _g(result, "plddt"),
                "ptm": _g(result, "ptm"),
                "n_residues": n_res,
                "model": "esmfold2" if is_complex else "esmfold2-single",
                "sampler_config": cfg,
                "ensemble": seleccion,
                "error": None,
            }
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}


# A module-level `predict` Function so the backend can call
# modal.Function.from_name("bioql-esmfold2-service", "predict").remote(payload)
# without instantiating the class explicitly.
@app.function(
    image=esmfold2_image,
    gpu="a100-80gb",
    timeout=3600,
    scaledown_window=300,
    volumes={"/results": results_vol, "/hf_cache": hf_cache_vol},
)
def predict(payload: dict) -> dict:
    return ESMFold2Service().predict.local(payload)
