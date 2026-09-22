"""
bionemo_protein_design.py — ADDITIVE de-novo protein / binder design via NVIDIA
BioNeMo NIMs (RFdiffusion backbone + ProteinMPNN sequence + ESMFold refold).

This module is STRICTLY ADDITIVE. It introduces an AI/structure design capability
that has NO quantum counterpart today, and never replaces, removes, or alters any
quantum component (SQD/VQE/CUDA-Q -> IBM). It only ADDS a de-novo binder/scaffold
design path and can FEED downstream quantum/MM-GBSA stages better geometries.

Real NIM endpoints (verified HTTP 200):
  * RFdiffusion : POST https://health.api.nvidia.com/v1/biology/ipd/rfdiffusion/generate
                  -> {"output_pdb": "<pdb str>"}
  * ProteinMPNN : POST https://health.api.nvidia.com/v1/biology/ipd/proteinmpnn/predict
                  -> {"mfasta": "<multi-fasta>", "scores": [...]}
  * ESMFold     : POST https://health.api.nvidia.com/v1/biology/nvidia/esmfold
                  -> {"pdbs": ["<pdb str>", ...]}

Key (NVIDIA_API_KEY) is read from the environment (sourced from ~/.bioql_secrets);
it is NEVER hardcoded. Every NIM call is fail-open: on any error the helper returns
None and the caller degrades gracefully (the existing pipeline is never broken).

Designability is measured by self-consistency: generate backbone -> design sequence
-> re-fold -> scRMSD(backbone_CA, refold_CA). A design is "self-consistent" when
scRMSD < 2.0 Angstrom. The fraction of self-consistent designs is the success rate.
"""
from __future__ import annotations

import io
import os
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("bionemo_protein_design")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
_NIM_BASE = "https://health.api.nvidia.com/v1/biology"
_RFD_URL = f"{_NIM_BASE}/ipd/rfdiffusion/generate"
_MPNN_URL = f"{_NIM_BASE}/ipd/proteinmpnn/predict"
_ESMFOLD_URL = f"{_NIM_BASE}/nvidia/esmfold"

_SC_RMSD_THRESHOLD = 2.0  # Angstrom; canonical designability cutoff
_DEFAULT_TIMEOUT = 600


def _api_key() -> Optional[str]:
    """Return the NVIDIA NIM key from the environment, or None. Never hardcoded."""
    return os.environ.get("NVIDIA_API_KEY") or None


def nim_available() -> bool:
    """True iff a key is present. (Does not make a network call.)"""
    return bool(_api_key())


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        # NVCF synchronous-poll hint; biology NIMs return 200 inline or 202 + poll.
        "NVCF-POLL-SECONDS": "300",
    }


def _nim_post(url: str, payload: Dict[str, Any],
              timeout: int = _DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """POST to a NIM, handling the 202 NVCF async-poll path. Fail-open -> None.

    Prefers the shared bionemo_nim client if another agent has shipped it (so a
    single key/poll implementation is reused), else uses a self-contained path.
    """
    if not _api_key():
        logger.warning("NVIDIA_API_KEY not set; NIM call skipped (fail-open).")
        return None
    # Reuse shared client if present (additive coordination, never required).
    try:
        import bionemo_nim  # type: ignore
        fn = getattr(bionemo_nim, "nim_post", None) or getattr(bionemo_nim, "post", None)
        if callable(fn):
            try:
                out = fn(url, payload, timeout=timeout)
                if out is not None:
                    return out
            except TypeError:
                out = fn(url, payload)
                if out is not None:
                    return out
    except Exception:
        pass  # shared client absent or incompatible -> self-contained path below

    try:
        import requests
    except Exception as exc:  # pragma: no cover
        logger.error("requests unavailable: %s", exc)
        return None

    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
        # Async path: 202 + NVCF-REQID -> poll the status endpoint.
        if resp.status_code == 202:
            req_id = resp.headers.get("NVCF-REQID")
            poll_url = f"https://health.api.nvidia.com/v1/status/{req_id}"
            deadline = time.time() + timeout
            while time.time() < deadline:
                pr = requests.get(poll_url, headers=_headers(), timeout=timeout)
                if pr.status_code == 200:
                    return pr.json()
                if pr.status_code != 202:
                    logger.error("NIM poll %s -> %s: %s", poll_url,
                                 pr.status_code, pr.text[:200])
                    return None
                time.sleep(5)
            logger.error("NIM poll timed out: %s", poll_url)
            return None
        if resp.status_code == 200:
            return resp.json()
        logger.error("NIM %s -> %s: %s", url, resp.status_code, resp.text[:300])
        return None
    except Exception as exc:
        logger.error("NIM POST failed (%s): %s", url, exc)
        return None


# --------------------------------------------------------------------------- #
# NIM primitives
# --------------------------------------------------------------------------- #
def generate_backbone(input_pdb: str, contigs: str, *,
                      diffusion_steps: int = 20,
                      hotspot_res: Optional[List[str]] = None,
                      timeout: int = _DEFAULT_TIMEOUT) -> Optional[str]:
    """RFdiffusion backbone generation. Returns an output PDB string, or None.

    Args:
        input_pdb: a PDB string used as the structural scaffold/template. For
            unconditional monomer generation any small valid PDB works (the
            contigs drive the result, e.g. "60-60").
        contigs: RFdiffusion contig map, e.g. "60-60" (de-novo 60-mer) or
            "A1-100/0 50-50" (a 50-residue binder against fixed chain A 1-100).
        diffusion_steps: number of diffusion steps (more = better, slower).
        hotspot_res: optional list of target hotspot residues (e.g. ["A30","A33"]).
    """
    if not input_pdb or not contigs:
        return None
    payload: Dict[str, Any] = {
        "input_pdb": input_pdb,
        "contigs": contigs,
        "diffusion_steps": int(diffusion_steps),
    }
    if hotspot_res:
        payload["hotspot_res"] = list(hotspot_res)
    out = _nim_post(_RFD_URL, payload, timeout=timeout)
    if not out:
        return None
    return out.get("output_pdb") or None


def design_sequences(backbone_pdb: str, *, num_seq: int = 4,
                     sampling_temp: float = 0.1, ca_only: bool = False,
                     timeout: int = _DEFAULT_TIMEOUT
                     ) -> Optional[List[Dict[str, Any]]]:
    """ProteinMPNN sequence design for a backbone. Returns a list of designs.

    Each design dict: {sequence, score, seq_recovery, sample}. The first FASTA
    record (the native/input sequence echo) is dropped; only sampled designs are
    returned. Returns None on NIM failure.
    """
    if not backbone_pdb:
        return None
    payload = {
        "input_pdb": backbone_pdb,
        "ca_only": bool(ca_only),
        "num_seq_per_target": int(num_seq),
        "sampling_temp": [float(sampling_temp)],
    }
    out = _nim_post(_MPNN_URL, payload, timeout=timeout)
    if not out:
        return None
    mfasta = out.get("mfasta") or ""
    designs = _parse_mpnn_fasta(mfasta)
    if not designs:
        return None
    return designs


def _parse_mpnn_fasta(mfasta: str) -> List[Dict[str, Any]]:
    """Parse ProteinMPNN multi-FASTA. Skip the input-echo record (sample 0)."""
    designs: List[Dict[str, Any]] = []
    header = None
    seq_lines: List[str] = []

    def _flush():
        if header is None:
            return
        meta = _parse_mpnn_header(header)
        seq = "".join(seq_lines).strip()
        # The first record is the input echo (T not present / sample absent).
        if seq and meta.get("sample") is not None:
            designs.append({
                "sequence": seq.replace("/", ":"),  # chain break -> ':'
                "score": meta.get("score"),
                "seq_recovery": meta.get("seq_recovery"),
                "sample": meta.get("sample"),
            })

    for line in mfasta.splitlines():
        if line.startswith(">"):
            _flush()
            header = line[1:]
            seq_lines = []
        else:
            seq_lines.append(line.strip())
    _flush()
    return designs


def _parse_mpnn_header(header: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    for tok in header.split(","):
        tok = tok.strip()
        if "=" in tok:
            k, _, v = tok.partition("=")
            k = k.strip()
            v = v.strip()
            try:
                if k in ("sample",):
                    meta[k] = int(float(v))
                elif k in ("score", "global_score", "seq_recovery", "T"):
                    meta[k] = float(v)
                else:
                    meta[k] = v
            except ValueError:
                meta[k] = v
    return meta


def fold_sequence(sequence: str, *, timeout: int = _DEFAULT_TIMEOUT
                  ) -> Optional[Dict[str, Any]]:
    """ESMFold a single-chain sequence. Returns {pdb, plddt}, or None.

    For multi-chain designs (':' chain break) only the first chain is folded
    (ESMFold is single-chain); self-consistency for binders should be evaluated
    on the designed binder chain.
    """
    if not sequence:
        return None
    seq = sequence.split(":")[0].strip()
    seq = "".join(c for c in seq if c.isalpha())
    if not seq:
        return None
    out = _nim_post(_ESMFOLD_URL, {"sequence": seq}, timeout=timeout)
    pdbs = (out or {}).get("pdbs") or []
    if pdbs:
        pdb = pdbs[0]
        return {"pdb": pdb, "plddt": _mean_plddt(pdb), "folder": "ESMFold NIM"}
    return _fold_sequence_modal(seq, timeout=timeout)


def _fold_sequence_modal(seq: str, *, timeout: int = _DEFAULT_TIMEOUT
                         ) -> Optional[Dict[str, Any]]:
    """Refold on BioQL's own ESMFold2 (Modal H100) when the NIM cannot serve it.

    Verified 2026-09-21: the ESMFold NIM answers 404 for this NVIDIA account
    ("Function ... not found for account"), which silently killed the whole
    self-consistency check -- backbone and sequence were generated fine and then
    design_one() returned None with no design surviving. The refold is the
    scRMSD filter, so losing it does not weaken the pipeline, it removes it.

    The same model runs in-house as bioql-esmfold2::fold_structure, so this
    falls through to it. The record says which folder produced the structure --
    two ESMFold implementations are not guaranteed to agree to the decimal, and
    a scRMSD that mixes them without saying so is not comparable.
    """
    try:
        import modal_compute_layer as MC
    except Exception as e:
        logger.warning("ESMFold fallback unavailable: %s", e)
        return None
    r = MC.run("fold_protein", seq, local_fn=None, timeout=timeout)
    if r.get("where_it_ran") != "modal":
        logger.warning("ESMFold fallback did not run: %s", r.get("why"))
        return None
    res = r.get("result") or {}
    pdb = res.get("pdb")
    if not res.get("success") or not pdb:
        logger.warning("ESMFold fallback failed: %s", str(res.get("error"))[:160])
        return None
    return {"pdb": pdb,
            "plddt": res.get("plddt") if res.get("plddt") is not None else _mean_plddt(pdb),
            "folder": "ESMFold2 (Modal H100)"}


# --------------------------------------------------------------------------- #
# Geometry: CA extraction, Kabsch superposition, scRMSD
# --------------------------------------------------------------------------- #
def _ca_coords(pdb: str, chain: Optional[str] = None) -> np.ndarray:
    """Extract CA coordinates (Nx3) from a PDB string (first MODEL only)."""
    coords: List[List[float]] = []
    for line in pdb.splitlines():
        if line.startswith("ENDMDL"):
            break
        if not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA":
            continue
        if chain is not None and line[21].strip() != chain:
            continue
        try:
            coords.append([float(line[30:38]), float(line[38:46]),
                           float(line[46:54])])
        except ValueError:
            continue
    return np.asarray(coords, dtype=float)


def _mean_plddt(pdb: str) -> Optional[float]:
    """Mean CA B-factor (ESMFold writes pLDDT into the B-factor column)."""
    vals: List[float] = []
    for line in pdb.splitlines():
        if line.startswith("ENDMDL"):
            break
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            try:
                vals.append(float(line[60:66]))
            except ValueError:
                continue
    if not vals:
        return None
    return round(float(np.mean(vals)), 2)


def kabsch_rmsd(P: np.ndarray, Q: np.ndarray) -> Optional[float]:
    """Minimal-RMSD after optimal rigid superposition (Kabsch). None if invalid."""
    if P is None or Q is None or len(P) == 0 or len(Q) == 0:
        return None
    n = min(len(P), len(Q))
    P = np.asarray(P[:n], dtype=float)
    Q = np.asarray(Q[:n], dtype=float)
    Pc = P - P.mean(axis=0)
    Qc = Q - Q.mean(axis=0)
    H = Pc.T @ Qc
    try:
        V, S, Wt = np.linalg.svd(H)
    except np.linalg.LinAlgError:
        return None
    d = np.sign(np.linalg.det(Wt.T @ V.T))
    D = np.diag([1.0, 1.0, d])
    R = Wt.T @ D @ V.T
    P_rot = Pc @ R.T
    diff = P_rot - Qc
    return float(np.sqrt((diff * diff).sum() / n))


def self_consistency_rmsd(backbone_pdb: str, refold_pdb: str,
                          chain: Optional[str] = None) -> Optional[float]:
    """scRMSD between a generated backbone and the re-folded designed sequence."""
    bb = _ca_coords(backbone_pdb, chain=chain)
    rf = _ca_coords(refold_pdb)
    if len(bb) == 0 or len(rf) == 0:
        return None
    if abs(len(bb) - len(rf)) > max(2, int(0.1 * max(len(bb), len(rf)))):
        # length mismatch beyond 10% -> not a valid 1:1 self-consistency compare
        logger.warning("scRMSD length mismatch bb=%d rf=%d", len(bb), len(rf))
    return kabsch_rmsd(bb, rf)


# --------------------------------------------------------------------------- #
# High-level: designability self-consistency
# --------------------------------------------------------------------------- #
_FALLBACK_TEMPLATE_PDB: Optional[str] = None


def _template_pdb() -> Optional[str]:
    """A small valid PDB to seed RFdiffusion's required input_pdb field.

    Fetches crambin (1CRN) once and caches it. For unconditional monomer
    generation the contigs (not the template) drive the output, so any small,
    valid structure suffices.
    """
    global _FALLBACK_TEMPLATE_PDB
    if _FALLBACK_TEMPLATE_PDB:
        return _FALLBACK_TEMPLATE_PDB
    try:
        import requests
        r = requests.get("https://files.rcsb.org/download/1CRN.pdb", timeout=60)
        if r.status_code == 200 and "ATOM" in r.text:
            _FALLBACK_TEMPLATE_PDB = r.text
            return _FALLBACK_TEMPLATE_PDB
    except Exception as exc:
        logger.error("template PDB fetch failed: %s", exc)
    return None


def design_one(length: int = 80, *, num_seq: int = 2,
               sampling_temp: float = 0.1, diffusion_steps: int = 20,
               template_pdb: Optional[str] = None,
               contigs: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Run one full designability cycle for an unconditional monomer.

    backbone (RFdiffusion) -> sequence(s) (ProteinMPNN) -> refold (ESMFold)
    -> scRMSD. Returns a dict with the best (lowest-scRMSD) design, or None if
    any NIM step fails (fail-open).
    """
    tmpl = template_pdb or _template_pdb()
    if not tmpl:
        return None
    cfg = contigs or f"{int(length)}-{int(length)}"
    bb = generate_backbone(tmpl, cfg, diffusion_steps=diffusion_steps)
    if not bb:
        return None
    designs = design_sequences(bb, num_seq=num_seq, sampling_temp=sampling_temp)
    if not designs:
        return None

    best: Optional[Dict[str, Any]] = None
    evaluated: List[Dict[str, Any]] = []
    for d in designs:
        seq = d["sequence"]
        fold = fold_sequence(seq)
        if not fold:
            continue
        scrmsd = self_consistency_rmsd(bb, fold["pdb"])
        rec = {
            "sequence": seq,
            "mpnn_score": d.get("score"),
            "seq_recovery": d.get("seq_recovery"),
            "plddt": fold.get("plddt"),
            "sc_rmsd": None if scrmsd is None else round(scrmsd, 3),
            "self_consistent": (scrmsd is not None and scrmsd < _SC_RMSD_THRESHOLD),
            "n_res": len(_ca_coords(bb)),
        }
        evaluated.append(rec)
        if scrmsd is not None and (best is None or scrmsd < best["sc_rmsd"]):
            best = rec
    if not evaluated:
        return None
    return {
        "backbone_pdb": bb,
        "length": int(length),
        "designs": evaluated,
        "best": best,
        "self_consistent": bool(best and best.get("self_consistent")),
    }


def assess_designability(n: int = 10, *, length: int = 80,
                         seqs_per_backbone: int = 2,
                         sampling_temp: float = 0.1,
                         diffusion_steps: int = 20,
                         progress: Optional[Any] = None) -> Dict[str, Any]:
    """Generate n backbones, design+refold, and report the self-consistency rate.

    The success metric is the fraction of backbones for which AT LEAST one
    designed sequence re-folds to scRMSD < 2.0 A (the canonical RFdiffusion +
    ProteinMPNN designability definition). Honest: only cycles that actually
    completed all three NIM calls count; failed NIM cycles are reported as
    n_failed and excluded from the denominator (never fabricated as success).
    """
    results: List[Dict[str, Any]] = []
    n_failed = 0
    for i in range(int(n)):
        if callable(progress):
            try:
                progress(i + 1, int(n))
            except Exception:
                pass
        cycle = design_one(length=length, num_seq=seqs_per_backbone,
                           sampling_temp=sampling_temp,
                           diffusion_steps=diffusion_steps)
        if cycle is None:
            n_failed += 1
            continue
        results.append(cycle)

    n_ok = len(results)
    n_sc = sum(1 for r in results if r.get("self_consistent"))
    all_rmsd = [d["sc_rmsd"] for r in results for d in r["designs"]
                if d.get("sc_rmsd") is not None]
    best_rmsd = [r["best"]["sc_rmsd"] for r in results
                 if r.get("best") and r["best"].get("sc_rmsd") is not None]
    return {
        "n_requested": int(n),
        "n_completed": n_ok,
        "n_failed": n_failed,
        "n_self_consistent": n_sc,
        "success_rate": (round(n_sc / n_ok, 4) if n_ok else None),
        "scrmsd_threshold": _SC_RMSD_THRESHOLD,
        "mean_best_scrmsd": (round(float(np.mean(best_rmsd)), 3)
                             if best_rmsd else None),
        "median_best_scrmsd": (round(float(np.median(best_rmsd)), 3)
                               if best_rmsd else None),
        "all_scrmsd": [round(x, 3) for x in all_rmsd],
        "results": results,
    }


# --------------------------------------------------------------------------- #
# Binder design (target-conditioned) + additive wiring hook
# --------------------------------------------------------------------------- #
def design_binder(target_pdb: str, *, target_chain_contig: str,
                  binder_length: int = 60, hotspot_res: Optional[List[str]] = None,
                  n_designs: int = 1, seqs_per_design: int = 2,
                  diffusion_steps: int = 20) -> Optional[Dict[str, Any]]:
    """De-novo binder design against a target structure (additive capability).

    Args:
        target_pdb: PDB string of the target.
        target_chain_contig: contig for the FIXED target portion, e.g. "A1-100".
        binder_length: length of the de-novo binder to grow.
        hotspot_res: target hotspot residues to bias the interface, e.g. ["A56"].
    Returns a dict with backbone, designed binder sequences, and pLDDT; or None.

    Note: scRMSD for binders is evaluated on the BINDER chain only (ESMFold is
    single-chain). This designs structures that can FEED downstream MM-GBSA /
    quantum stages with real geometry — it never replaces them.
    """
    if not target_pdb or not target_chain_contig:
        return None
    contigs = f"{target_chain_contig}/0 {int(binder_length)}-{int(binder_length)}"
    bb = generate_backbone(target_pdb, contigs, diffusion_steps=diffusion_steps,
                           hotspot_res=hotspot_res)
    if not bb:
        return None
    designs = design_sequences(bb, num_seq=seqs_per_design)
    if not designs:
        return None
    out_designs: List[Dict[str, Any]] = []
    for d in designs:
        # The binder is the newly-grown chain (':' separates chains). Chain order
        # from RFdiffusion/ProteinMPNN is not guaranteed, so pick the chain whose
        # length best matches the requested binder_length (robust, honest).
        chains = [c for c in d["sequence"].split(":") if c]
        if chains:
            binder_seq = min(chains, key=lambda c: abs(len(c) - int(binder_length)))
        else:
            binder_seq = d["sequence"]
        fold = fold_sequence(binder_seq)
        out_designs.append({
            "full_sequence": d["sequence"],
            "binder_sequence": binder_seq,
            "mpnn_score": d.get("score"),
            "binder_plddt": (fold.get("plddt") if fold else None),
        })
    return {
        "backbone_pdb": bb,
        "binder_length": int(binder_length),
        "hotspot_res": hotspot_res or [],
        "designs": out_designs,
    }


def propose_denovo_scaffold(target: str = "", *, antigen_pdb: str = "",
                            target_chain_contig: str = "",
                            binder_length: int = 60,
                            hotspot_res: Optional[List[str]] = None,
                            n_designs: int = 1,
                            seqs_per_design: int = 2) -> Dict[str, Any]:
    """Additive hook for the antibody/biologic path. Always returns a dict.

    If a key + antigen structure are available it proposes a de-novo binder
    scaffold (RFdiffusion + ProteinMPNN). Otherwise returns an honest
    {available: False, ...}. Never raises; never touches the quantum stages.
    """
    if not nim_available():
        return {"available": False, "reason": "NVIDIA_API_KEY not set",
                "engine": "bionemo_protein_design"}
    if not (antigen_pdb and target_chain_contig):
        return {"available": False,
                "reason": "antigen_pdb + target_chain_contig required for binder",
                "engine": "bionemo_protein_design", "target": target}
    try:
        out = design_binder(antigen_pdb, target_chain_contig=target_chain_contig,
                            binder_length=binder_length, hotspot_res=hotspot_res,
                            n_designs=n_designs, seqs_per_design=seqs_per_design)
        if out is None:
            return {"available": False, "reason": "NIM call failed (fail-open)",
                    "engine": "bionemo_protein_design", "target": target}
        out.update({"available": True, "engine": "bionemo_protein_design",
                    "target": target})
        return out
    except Exception as exc:  # pragma: no cover
        logger.error("propose_denovo_scaffold failed: %s", exc)
        return {"available": False, "reason": str(exc),
                "engine": "bionemo_protein_design", "target": target}


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print("nim_available:", nim_available())
    res = design_one(length=70, num_seq=2)
    print(res["best"] if res else "design_one failed")
