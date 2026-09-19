#!/usr/bin/env python3
# Copyright 2024-2026 MOLEVERA / BIOQL — Apache-2.0
"""
Universal pipeline finalize hook — ADDITIVE, runs on EVERY pipeline result.
==========================================================================

One call that brings the audit-grade + compounding-moat layer to ALL modalities
(small-molecule / peptide / antibody / mRNA), not just mRNA:

  * provenance_ledger.build_bundle  -> result['provenance_manifest'] (tamper-verifiable
    integrity hash + every value engine-attributed)
  * foundation_data_logger.log_run  -> appends the validated run to the versioned corpus
  * decision_gonogo (when a clinical PoS block is present) -> result['program_decision']

Every step is GUARDED: a failure (or a missing optional engine) is logged and skipped —
it NEVER breaks the pipeline and NEVER fabricates a value. Idempotent-ish: safe to call once
per result at the return point.
"""
from __future__ import annotations
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("bioql.pipeline_finalize")

_AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")
_MOTIF_KEYS = ("binding_motif", "core_motif", "functional_motif", "binding_core",
               "active_motif", "epitope_core", "motif", "receptor_binding_motif")


def _lead_known_motifs(lead: Dict[str, Any], summary: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    """Collect binding-determinant MOTIFS to PRESERVE during peptide de-immunization,
    from existing lead/summary annotations. Strictly additive + safe: only keeps a
    value that is a real amino-acid SUBSTRING of the lead sequence (so the de-immunizer
    can locate it). Returns None when nothing valid is found → identical to prior
    behavior (N/C-terminal guard only). Never fabricates a motif."""
    if not isinstance(lead, dict):
        return None
    seq = (lead.get("sequence") or lead.get("optimized_sequence") or "").upper()
    if not seq:
        return None
    found: List[str] = []
    for src in (lead, summary if isinstance(summary, dict) else {}):
        for k in _MOTIF_KEYS:
            v = src.get(k)
            for cand in (v if isinstance(v, (list, tuple)) else [v]):
                if isinstance(cand, str):
                    c = cand.strip().upper()
                    if 3 <= len(c) <= len(seq) and _AA_RE.match(c) and c in seq and c not in found:
                        found.append(c)
    return found or None


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── Card top-level surfacing (WS-4.2/4.4) ────────────────────────────────────
# The frontend's extractPipelineData() (src/frontend/.../ChatMessage.tsx ~line 487)
# reads a SMALL SET of hardcoded top-level/`stages[...]` paths per card. Several
# pipelines compute the same data but nest it under a DIFFERENT stage key (e.g. the
# mRNA pipeline uses `2_structure_prediction` while the custom-molecule pipeline in
# script_executor_server.py uses `10_3d_structure`/`9_docking`/`2_admet`/`11_scoring`
# or `8_scoring` — confirmed via grep, see report), so the card silently renders
# empty even though the value was really computed. This is a small, EXPLICIT
# allowlist — not a generic deep-schema search — covering exactly the gaps found:
#   mol_3d              <- stages['10_3d_structure'].mol_block | best_candidate/candidate[0].mol_3d
#   docking             <- stages['9_docking'] | stages['6_docking'].data | best_candidate(.analyses).docking | candidate[0](.analyses).docking
#   admet               <- stages['2_admet'].data | best_candidate(.analyses).admet | candidate[0](.analyses).admet
#   drug_candidate_class<- stages['11_scoring'|'8_scoring'].drug_candidate_class | best_candidate.drug_candidate_class/compound_class
#   composite_score     <- stages['11_scoring'|'8_scoring'].composite_score | best_candidate.composite_score/score/scores.composite_score
#   images              <- visualizations.images | discovery.images  (top-level `images` alias — mRNA/replicon already do this ad hoc; this covers pipelines that don't)
#   structure_3d        <- stages['2_structure_prediction'] | best_candidate/candidate[0].structure_3d
#     + its `length_aa` specifically: confirmed real bug at script_executor_server.py
#       ~24481/~27605 where `structure_3d = {"pdb":..., "method":..., "sequence":...}`
#       is written at top level WITHOUT `length_aa` (frontend reads
#       `structure3dMeta.length_aa` at ChatMessage.tsx ~835/~2994) -> renders as if
#       0 aa. Fixed here by deriving it from the sequence already present, or copying
#       it from a nested structure_3d that has it.
# Every branch ONLY fills a key that is genuinely absent (or, for structure_3d,
# only backfills the missing length_aa field) — an already-present value (even
# partially populated, e.g. mRNA's own ad hoc `results["images"]` lift) is NEVER
# touched. Nothing here fabricates a value; it only relocates data that already
# exists, verbatim, somewhere else in this same result.
def _first_present(*vals: Any) -> Any:
    for v in vals:
        if v not in (None, {}, [], ""):
            return v
    return None


def _surface_top_level_cards(result: Dict[str, Any]) -> None:
    stages = result.get("stages") if isinstance(result.get("stages"), dict) else {}
    best = result.get("best_candidate") if isinstance(result.get("best_candidate"), dict) else {}
    best_an = best.get("analyses") if isinstance(best.get("analyses"), dict) else {}
    cands = result.get("candidates")
    cand0 = cands[0] if isinstance(cands, list) and cands and isinstance(cands[0], dict) else {}
    cand0_an = cand0.get("analyses") if isinstance(cand0.get("analyses"), dict) else {}
    s10 = stages.get("10_3d_structure") if isinstance(stages.get("10_3d_structure"), dict) else {}
    s9 = stages.get("9_docking") if isinstance(stages.get("9_docking"), dict) else {}
    s6 = stages.get("6_docking") if isinstance(stages.get("6_docking"), dict) else {}
    s2a = stages.get("2_admet") if isinstance(stages.get("2_admet"), dict) else {}
    s11 = stages.get("11_scoring") if isinstance(stages.get("11_scoring"), dict) else {}
    s8 = stages.get("8_scoring") if isinstance(stages.get("8_scoring"), dict) else {}

    # -- mol_3d --
    if not result.get("mol_3d"):
        _v = _first_present(s10.get("mol_block"), best.get("mol_3d"), cand0.get("mol_3d"))
        if _v:
            result["mol_3d"] = _v

    # -- docking --
    if not result.get("docking"):
        _v = _first_present(
            s9 or None, s6.get("data"),
            best_an.get("docking"), best.get("docking"),
            cand0_an.get("docking"), cand0.get("docking"),
        )
        if isinstance(_v, dict):
            result["docking"] = _v

    # -- admet --
    if not result.get("admet"):
        _v = _first_present(
            s2a.get("data"), best_an.get("admet"), best.get("admet"),
            cand0_an.get("admet"), cand0.get("admet"),
        )
        if isinstance(_v, dict):
            result["admet"] = _v

    # -- drug_candidate_class / composite_score --
    if not result.get("drug_candidate_class"):
        _v = _first_present(
            s11.get("drug_candidate_class"), s8.get("drug_candidate_class"),
            best.get("drug_candidate_class"), best.get("compound_class"),
            cand0.get("drug_candidate_class"), cand0.get("compound_class"),
        )
        if _v:
            result["drug_candidate_class"] = _v
    if result.get("composite_score") is None:
        _best_scores = best.get("scores") if isinstance(best.get("scores"), dict) else {}
        _v = _first_present(
            s11.get("composite_score"), s8.get("composite_score"),
            best.get("composite_score"), best.get("score"), _best_scores.get("composite_score"),
            cand0.get("composite_score"),
        )
        if _v is not None:
            result["composite_score"] = _v

    # -- images (top-level alias of visualizations.images / discovery.images) --
    if not result.get("images"):
        _viz = result.get("visualizations") if isinstance(result.get("visualizations"), dict) else {}
        _disc = result.get("discovery") if isinstance(result.get("discovery"), dict) else {}
        _v = _first_present(_viz.get("images"), _disc.get("images"))
        if isinstance(_v, list) and _v:
            result["images"] = _v

    # -- structure_3d (+ its length_aa specifically) --
    _s3d = result.get("structure_3d")
    _s2sp = stages.get("2_structure_prediction") if isinstance(stages.get("2_structure_prediction"), dict) else {}
    if isinstance(_s3d, dict):
        if not _s3d.get("length_aa"):
            _seq = _s3d.get("sequence")
            if isinstance(_seq, str) and _seq.strip():
                _s3d["length_aa"] = len(_seq.strip())
            else:
                for _node in (_s2sp, best.get("structure_3d"), cand0.get("structure_3d")):
                    if isinstance(_node, dict) and _node.get("length_aa"):
                        _s3d["length_aa"] = _node["length_aa"]
                        break
    else:
        _v = _first_present(_s2sp, best.get("structure_3d"), cand0.get("structure_3d"))
        if isinstance(_v, dict):
            result["structure_3d"] = _v


# ── Honest "not computed" placeholders for keys that stay entirely absent ───────
# Applied ONLY to keys where the frontend's existing truthy/shape gate (verified
# above per card, see report) safely no-ops on a bare {"available": False,
# "null_reason": ...} dict — i.e. it will NEVER be misread as a real result. `admet`,
# `mol_3d`, `drug_candidate_class` and `composite_score` are deliberately EXCLUDED:
# their cards render on a bare truthy/typeof-object check (ADMETRadarChart defaults
# missing sub-fields to 0, drawing a misleading all-zero radar; mol_3d/composite_score
# are read as a raw mol-block string / number with no shape gate at all), so writing
# a placeholder there risks the UI misrendering a "not computed" marker as a real
# (bad) result — the placeholder is skipped for those two to honor "never break".
_PLACEHOLDER_REASONS = {
    "docking": "no docking pose computed for this pipeline/run",
    "structure_3d": "no 3D structure folded for this pipeline/run",
}


def _placeholder_reason(result: Dict[str, Any], key: str) -> str:
    _skipped = result.get("systems_skipped")
    if isinstance(_skipped, list):
        for _s in _skipped:
            _txt = _s if isinstance(_s, str) else (
                _s.get("reason") if isinstance(_s, dict) else None)
            _name = _s.get("system") if isinstance(_s, dict) else _s
            if _txt and isinstance(_name, str) and key.split("_")[0] in _name.lower():
                return str(_txt)
    return _PLACEHOLDER_REASONS.get(key, "not computed for this pipeline")


def _fill_missing_card_placeholders(result: Dict[str, Any]) -> None:
    for _k in _PLACEHOLDER_REASONS:
        if _k not in result:
            result[_k] = {"available": False, "null_reason": _placeholder_reason(result, _k)}


# ── Universal biologic-sequence extraction (for MHC-II immunogenicity) ──────────
_AA20 = set("ACDEFGHIKLMNPQRSTVWY")
_SEQ_KEY = re.compile(
    r"sequence|peptide|fasta|protein|heavy|light|chain|vh|vl|cdr|antibody|antigen|"
    r"construct|lead|monomer|agonist", re.I)
# Keys that hold a PARENT/pre-modification sequence or a SUB-FRAGMENT of a chain —
# excluded from chain extraction so the epitope assessment never double-counts (e.g.
# `deimmunized_from` = the original, or `cdr_h2` = a loop already inside VH).
_EXCLUDE_KEY = re.compile(
    r"original|parent|deimmunized_from|_from|before|scaffold|wild.?type|template|"
    r"cdr|motif|fragment|epitope|window|preview|germline", re.I)


def _looks_like_protein(s: Any) -> bool:
    """Plausible protein AA sequence — NOT a SMILES, NOT a nucleotide string.
    Requires length 15..1500, only canonical AA letters, and >4 distinct residues
    (rules out ACGT/ACGU nucleotide CDS strings; SMILES fail on non-AA chars)."""
    if not isinstance(s, str):
        return False
    s = s.strip().upper()
    if len(s) < 15 or len(s) > 1500:
        return False
    if any(c not in _AA20 for c in s):
        return False
    return len(set(s)) > 4


def _extract_biologic_sequences(result: Any, limit: int = 3) -> List[str]:
    """Deep-walk the result for distinct biologic protein chains (peptide, antibody
    VH/VL, designed protein). Returns up to `limit` distinct valid AA sequences,
    longest first. Empty => no biologic sequence (e.g. a small molecule = SMILES)."""
    found: Dict[str, int] = {}

    def _walk(node: Any, key_hint: str = "") -> None:
        if isinstance(node, str):
            if (_looks_like_protein(node) and not _EXCLUDE_KEY.search(key_hint)
                    and (_SEQ_KEY.search(key_hint) or len(node) >= 30)):
                s = node.strip().upper()
                found[s] = len(s)
        elif isinstance(node, dict):
            for k, v in node.items():
                _walk(v, str(k))
        elif isinstance(node, (list, tuple)):
            for v in node:
                _walk(v, key_hint)

    _walk(result)
    return [s for s, _ in sorted(found.items(), key=lambda kv: -kv[1])][:limit]


# ── Small-molecule identifier extraction (for full-engine-output emission) ──────
_CHEMBL_RE = re.compile(r"^CHEMBL\d+$", re.I)
_SMILES_KEYS = ("smiles", "canonical_smiles", "ligand_smiles", "smile",
                "input_smiles", "mol_smiles", "query_smiles")
_CHEMBL_KEYS = ("molecule_chembl_id", "chembl_id", "parent_chembl_id",
                "molecule_id")


def _first_str_under_keys(node: Any, keys, validate, depth: int = 6) -> Optional[str]:
    """Deep-walk `node` and return the first non-empty string held under a key in
    `keys` that passes `validate(str)`. Read-only; never raises. Used to locate a
    SMILES / ChEMBL id already present in the pipeline result so the corresponding
    engine's FULL output can be emitted for its card — strictly from real data."""
    if depth <= 0:
        return None
    if isinstance(node, dict):
        for k, v in node.items():
            if str(k).lower() in keys and isinstance(v, str) and v.strip():
                c = v.strip()
                try:
                    if validate(c):
                        return c
                except Exception:
                    pass
        for v in node.values():
            r = _first_str_under_keys(v, keys, validate, depth - 1)
            if r:
                return r
    elif isinstance(node, (list, tuple)):
        for v in node:
            r = _first_str_under_keys(v, keys, validate, depth - 1)
            if r:
                return r
    return None


def _looks_like_target(s: str) -> bool:
    """Gate for a gene/protein SYMBOL pulled out of an arbitrary result dict.

    Deliberately strict: this string becomes a competitive-landscape query, and
    a false positive ("Parkinson disease" landing in the target slot) returns a
    landscape for the wrong thing, which is worse than returning none. Real
    symbols are short, have no spaces, and carry at least one letter --
    LRRK2, EGFR, KRAS, HBB, TP53, SLC6A4, mTOR.
    """
    s = s.strip()
    if not (1 < len(s) <= 15) or " " in s:
        return False
    if not any(c.isalpha() for c in s):
        return False
    # Not a sequence, a SMILES, an id or a path.
    if not all(c.isalnum() or c in "-_" for c in s):
        return False
    if s.lower() in {"none", "null", "unknown", "n/a", "na", "target", "protein",
                     "gene", "true", "false"}:
        return False
    # An all-letter string this long is far more likely a word than a symbol.
    if len(s) > 8 and s.isalpha():
        return False
    return True


def _looks_like_indication(s: str) -> bool:
    """Gate for a disease/indication phrase. Looser than the symbol gate -- real
    indications are words ("Parkinson disease", "non-small cell lung cancer") --
    but still bounded so a whole description never becomes the query."""
    s = s.strip()
    if not (3 <= len(s) <= 90):
        return False
    if s.lower() in {"none", "null", "unknown", "n/a", "na", "disease",
                     "indication", "condition", "true", "false"}:
        return False
    # Must read as prose/name, not as an identifier or a sequence blob.
    return any(c.isalpha() for c in s) and not s.startswith(("http", "/", "{"))


def _looks_like_smiles(s: str) -> bool:
    """Cheap SMILES sanity gate: short, and NOT a plain amino-acid chain (which would
    be a peptide/protein, not a small molecule). Avoids running small-molecule
    engines on a biologic sequence stored under a mislabeled key."""
    if not (1 <= len(s) <= 500):
        return False
    # A pure run of canonical AA letters with no SMILES punctuation = a protein, not SMILES.
    if len(s) >= 12 and all(c in _AA20 for c in s.upper()):
        return False
    return True


def _has_key_anywhere(node: Any, names, depth: int = 4) -> bool:
    """True if any key in `names` (with a truthy value) exists anywhere in `node`."""
    if depth <= 0 or not isinstance(node, (dict, list, tuple)):
        return False
    if isinstance(node, dict):
        for n in names:
            if node.get(n):
                return True
        return any(_has_key_anywhere(v, names, depth - 1) for v in node.values())
    return any(_has_key_anywhere(v, names, depth - 1) for v in node)


_LIT_FIELDS = ("literature_text", "assay_text", "reference_abstract",
               "source_abstract", "publication_text")


def _lit_text(cand):
    """Text the record deliberately carries a potency in, or nothing.

    Deliberate is the point: a potency is only ever read from a field a caller
    put there for that purpose, never scraped from whatever prose happens to
    be lying in the candidate.
    """
    for f in _LIT_FIELDS:
        v = (cand or {}).get(f)
        if isinstance(v, str) and len(v.strip()) > 40:
            return v
    return None


def _attach_efficacious_dose(result):
    """Derive the efficacious dose from potency + PBPK, for each candidate.

    The platform published `recommended_dose_mg` from a generative QNN head
    (range 5-1000 mg, 200 mg fallback) while a 14-compartment PBPK model sat
    unused beside it. That head is gone; this fills the gap with a derivation:

        potency -> target free concentration -> total via unbound fraction
                -> PBPK inverse solve -> dose

    It uses the DETERMINISTIC optimiser. Measured 2026-09-17 on identical PK
    input, the classical solve returned 169.7 mg three times out of three while
    QAOA-PK returned 217.7 / 218.7 / 215.9; end to end the divergence reached
    628.6 mg versus 3656.5 mg for the same molecule. A recommended dose cannot
    depend on which substrate answered first.

    When an input is missing the candidate gets an honest null with the reason,
    never a default. Never raises: a dose derivation must not take a pipeline
    down.
    """
    if not isinstance(result, dict):
        return result
    try:
        import efficacious_dose as _ED
    except Exception:
        return result

    seen = 0
    derived = 0
    for key in ("candidates", "all_candidates", "drug_candidates", "lead_compounds"):
        items = result.get(key)
        if not isinstance(items, list):
            continue
        for cand in items:
            if not isinstance(cand, dict):
                continue
            seen += 1
            try:
                # A potency stated in a paper is a measurement someone else
                # made; lifting it verbatim is legitimate where estimating one
                # is not. Only text the record explicitly carries is read.
                dose = _ED.efficacious_dose(cand, literature_text=_lit_text(cand))
            except Exception as exc:  # noqa: BLE001
                dose = {"available": False, "dose_mg": None,
                        "reason": "dose derivation failed: %s" % exc}
            cand["efficacious_dose"] = dose
            # The flat field the UI reads keeps its name, but now it is either a
            # derived number or absent -- never a sampled one.
            cand["recommended_dose_mg"] = dose.get("dose_mg")
            if dose.get("available"):
                derived += 1

    if seen:
        result["efficacious_dose_summary"] = {
            "candidates_seen": seen,
            "doses_derived": derived,
            "doses_absent": seen - derived,
            "method": "potency -> target exposure -> PBPK inverse solve (deterministic)",
            "note": ("An absent dose means an input was missing -- potency, unbound "
                     "fraction or molecular weight. It is not zero and not a default; "
                     "each candidate carries its own reason."),
        }
    return result


def finalize(result: Any, *, pipeline: Optional[str] = None,
             timestamp: Optional[str] = None) -> Any:
    """Attach audit provenance + log to the foundation corpus + (if a clinical PoS
    block exists) a decision-theoretic GO/NO-GO. Returns the (mutated) result.
    No-op-safe on anything that isn't a dict."""
    if not isinstance(result, dict):
        return result
    ts = timestamp or result.get("timestamp") or _ts()

    # Card top-level surfacing (WS-4.2) — relocate already-computed values from a
    # pipeline's own nested stage layout to the exact key the frontend cards read,
    # so a mismatched nesting doesn't render an empty card. Read-only where a key
    # is already present. Guarded: never breaks the response.
    try:
        _surface_top_level_cards(result)
    except Exception as e:
        logger.warning("[finalize] card surfacing skipped: %s", e)

    # Honest placeholders (WS-4.4) for the small subset of card keys where an
    # entirely-absent value is safe to mark explicitly (see _PLACEHOLDER_REASONS
    # docstring for why admet/mol_3d/drug_candidate_class/composite_score are
    # excluded). Uses the same null_reason vocabulary the frontend already unwraps.
    try:
        _fill_missing_card_placeholders(result)
    except Exception as e:
        logger.warning("[finalize] card placeholders skipped: %s", e)

    # Decision-theoretic GO/NO-GO — only when a real per-phase PoS block is present.
    if "program_decision" not in result:
        try:
            _ct = (result.get("clinical_trial") or result.get("clinical")
                   or (result.get("stages", {}) or {}).get("5_clinical_trial", {}).get("data"))
            if isinstance(_ct, dict) and _ct.get("phase_1_to_2"):
                from decision_gonogo import program_decision
                # value_if_approved = a LABELED market assumption (risk-adjusted NPV of an
                # approved drug in USD; ~$2.5B blockbuster-class). eNPV REQUIRES one — the
                # engine's disclaimer flags it as an assumption, not a measured value.
                result["program_decision"] = program_decision(
                    _ct, use_default_costs=True,
                    value_if_approved=float(((result.get("input") or {}).get("value_if_approved")) or 2.5e9))
        except Exception as e:
            logger.warning("[finalize] gonogo skipped: %s", e)

    # Foundation corpus — log every validated run (the compounding-data moat).
    try:
        from foundation_data_logger import log_run
        log_run(result, pipeline=pipeline)
    except Exception as e:
        logger.warning("[finalize] foundation log skipped: %s", e)

    # Lead de-immunization (AUTO-ADOPT) for antibody / peptide — preserve the
    # functional core (all 6 CDRs for antibodies, binding motif + N/C guard for
    # peptides) and adopt a strictly-better (fewer MHC-II epitopes) lead. mRNA does
    # this in-pipeline (guarded). Placed BEFORE the assessment so the reported epitope
    # burden reflects the adopted lead. Post-selection: conservative non-core swaps →
    # CDR/motif-driven biophysics unchanged; never breaks the run, never fabricates.
    if "deimmunization" not in result:
        try:
            _pl = (pipeline or "").upper()
            _lead = result.get("best_candidate")
            if not isinstance(_lead, dict):
                _c = result.get("candidates")
                _lead = _c[0] if isinstance(_c, list) and _c and isinstance(_c[0], dict) else None
            if isinstance(_lead, dict):
                import deimmunize_modalities as _dm
                _rep = None
                if "ANTIBODY" in _pl:
                    _rep = _dm.deimmunize_antibody_lead(_lead)
                elif "PEPTIDE" in _pl:
                    _motifs = _lead_known_motifs(_lead, result.get("summary"))
                    _rep = _dm.deimmunize_peptide_lead(_lead, result.get("summary"), known_motifs=_motifs)
                if _rep:
                    result["deimmunization"] = _rep
        except Exception as e:
            logger.warning("[finalize] lead de-immunization skipped: %s", e)

    # Universal MHC-II immunogenicity assessment (ADDITIVE, read-only). Every BIOLOGIC
    # pipeline (peptide / antibody / mRNA-encoded protein) gets a real epitope-burden
    # read from the same HistGBM/NetMHCIIpan-3.2 predictor (CV AUC ~0.79). A small
    # molecule honestly gets applicable=False — T-cell-epitope immunogenicity is a
    # peptide/protein property; small-molecule immunogenicity is haptenation, a distinct
    # mechanism not modeled here. Skipped if a modality already populated it (mRNA does).
    if "immunogenicity" not in result:
        try:
            _seqs = _extract_biologic_sequences(result)
            if not _seqs:
                result["immunogenicity"] = {
                    "available": False, "applicable": False,
                    "reason": ("No peptide/protein sequence in this result — MHC-II "
                               "T-cell-epitope immunogenicity does not apply to a small "
                               "molecule (its immunogenicity is haptenation, a distinct "
                               "mechanism not modeled here)."),
                }
            else:
                from immunogenicity_mhc import predict_immunogenicity
                _preds = [(s, predict_immunogenicity(s)) for s in _seqs]
                _preds = [(s, p) for s, p in _preds if p.get("available")]
                if _preds:
                    _base = dict(_preds[0][1])  # full assessment of the longest chain
                    _base["chains_assessed"] = len(_preds)
                    _base["epitope_count"] = sum(int(p.get("epitope_count") or 0)
                                                 for _, p in _preds)
                    _base["per_chain"] = [
                        {"length_aa": len(s), "epitope_count": p.get("epitope_count"),
                         "preview": s[:12] + ("…" if len(s) > 12 else "")}
                        for s, p in _preds]
                    # Surface a SCALAR value (epitope burden) so honest-value cards
                    # render the real number instead of "N/A — not available".
                    _base["value"] = _base.get("epitope_count")
                    _base["units"] = "MHC-II epitopes (burden across assessed chains)"
                    _base["is_estimate"] = True
                    _base["method"] = _base.get("method") or "NetMHCIIpan-3.2-derived HistGBM (HLA-DR panel)"
                    result["immunogenicity"] = _base
        except Exception as e:
            logger.warning("[finalize] immunogenicity assessment skipped: %s", e)

    # Universal Boltz-2 structure CROSS-CHECK (Modal A100 + cuEquivariance) — an
    # independent all-atom folder on the BIOLOGIC lead chain. mRNA folds in-pipeline
    # (nested under structure_3d → skipped here); this covers peptide/antibody. Small
    # molecules have no chain → skipped. Honest-or-N/A; default on (input
    # boltz2_crosscheck=off skips the ~1-3 min Modal round-trip); never raises.
    _nested_bz = bool((result.get("structure_3d") or {}).get("boltz2_crosscheck"))
    if "boltz2_crosscheck" not in result and not _nested_bz:
        try:
            # OPT-IN (default OFF): this Modal A100 fold adds ~1-3 min AFTER the results are
            # assembled — it kept the streaming connection open ("run never finishes") and
            # burned Modal on every biologic run. Now it only fires when explicitly requested
            # (input boltz2_crosscheck in on/true/1/yes). Design completion no longer waits on it.
            _flag = str((result.get("input") or {}).get("boltz2_crosscheck", "off")).lower()
            if _flag in ("on", "true", "1", "yes", "auto"):
                _seqs = _extract_biologic_sequences(result)
                if _seqs:
                    from boltz2_backend import predict_structure_boltz2
                    _bz = predict_structure_boltz2(_seqs[0])
                    if isinstance(_bz, dict) and _bz.get("success"):
                        _bc = _bz.get("confidence") or {}
                        result["boltz2_crosscheck"] = {
                            "model": "boltz-2",
                            "plddt": (_bc.get("plddt") * 100.0) if isinstance(_bc.get("plddt"), (int, float)) else None,
                            "ptm": _bc.get("ptm"),
                            "confidence_score": _bc.get("confidence_score"),
                            "cuequivariance": _bz.get("cuequivariance"),
                            "engine": _bz.get("engine"),
                            "chain_len_aa": len(_seqs[0]),
                            "agreement_note": ("Independent all-atom folder (Boltz-2, cuEquivariance-"
                                "accelerated, Modal A100) on the biologic lead chain — Boltz-2's own "
                                "confidence, not fabricated. Cross-validates the pipeline's structure."),
                        }
                    elif isinstance(_bz, dict):
                        result["boltz2_crosscheck"] = {"available": False,
                            "reason": _bz.get("reason") or _bz.get("error")}
        except Exception as e:
            logger.warning("[finalize] boltz2 cross-check skipped: %s", e)

    # Validation surfacing (ADDITIVE, read-only): inline the AUTHORITATIVE
    # validation_registry badge for each small-molecule chemistry calc that is
    # RELEVANT to this result, so the already-built chat cards (FEP / GenMol /
    # Metabolism / QuantumChem / Trust) light up from the single source of truth.
    # These four keys live only in validation_metrics.json and were never inlined
    # into the chat RESULT JSON, so their cards stayed dark. Real numbers only: a
    # key absent from the registry is skipped (never a fabricated stub). The block
    # is attached at the top level so deepFind() never SHADOWS a real engine block
    # (those appear earlier in DFS order); it only fills the gap. Fail-open.
    if "validations" not in result:
        try:
            import validation_registry as _vreg

            def _key_present(node, names, depth=4):
                if depth <= 0 or not isinstance(node, (dict, list)):
                    return False
                if isinstance(node, dict):
                    for _n in names:
                        v = node.get(_n)
                        if isinstance(v, str) and v.strip():
                            return True
                    return any(_key_present(v, names, depth - 1) for v in node.values())
                return any(_key_present(v, names, depth - 1) for v in node)

            _pl = (pipeline or "").upper()
            # Small-molecule chemistry context: a SMILES anywhere, or a pipeline whose
            # name implies small-molecule / drug / chem-physics work. All four calcs
            # are small-molecule-domain, so a pure antibody/mRNA run attaches nothing.
            _is_sm = _key_present(result, ("smiles", "canonical_smiles")) or any(
                _t in _pl for _t in ("SMALL", "MOLECULE", "DRUG", "GENERAT", "DESIGN",
                                     "ADMET", "QUANTUM", "VQE", "SQD", "FEP", "AFFINITY",
                                     "DOCK", "METAB", "CHEM"))
            if _is_sm:
                # GenMol is only relevant when molecules were actually generated/designed.
                _is_gen = any(_t in _pl for _t in ("GENERAT", "DESIGN")) or _key_present(
                    result, ("generated", "generative_genmol", "genmol"))
                # (result_key_for_card, registry_engine_key, relevant?)
                _candidates = [
                    ("fep_rbfe", "fep_rbfe", True),
                    ("generative_genmol", "generative_genmol", _is_gen),
                    ("site_of_metabolism", "site_of_metabolism", True),
                    ("pk_clearance", "pk_clearance", True),
                    ("pk_half_life", "pk_half_life", True),
                    ("quantum_chem_advantage_boundary", "quantum_chem_advantage_boundary", True),
                ]
                _vals = {}
                for _rk, _eng, _rel in _candidates:
                    if not _rel:
                        continue
                    # Skip keys with no REAL recorded entry — never ship a validated=False stub.
                    if _vreg.get(_eng) is None:
                        continue
                    _vals[_rk] = _vreg.summary(_eng)
                if _vals:
                    _vals["_source"] = "validation_registry (single source of truth)"
                    result["validations"] = _vals
        except Exception as e:
            logger.warning("[finalize] validation surfacing skipped: %s", e)

    # FULL engine-output emission (ADDITIVE) — the badge block above inlines only a
    # validation SUMMARY (validation_registry.summary, which DROPS the `extra` payload),
    # so the FEP / GenMol / Metabolism / QuantumChem / Selectivity cards have no data to
    # draw. Here we ALSO surface each engine's FULL output under the exact top-level key
    # its card deepFind()s, so those cards light up their viz:
    #   * fep   -> the authoritative `fep_rbfe_alchemical` registry ENTRY (metrics +
    #              extra.per_edge = the per-edge ΔΔG scatter) and `fep_rbfe` (rmse/pearson)
    #   * genmol-> `generative_genmol` registry ENTRY (validity/novelty/diversity metrics)
    #   * qchem -> `quantum_chem_advantage_boundary` registry ENTRY (extra.per_case bars)
    #   * metab -> the LIVE site_of_metabolism / pk_clearance / pk_half_life engine dicts
    #              (per-atom SOM probabilities + predicted CL/half-life) when a SMILES is
    #              present — the registry alone has no per-atom/per-compound output
    #   * select-> the LIVE selectivity_panel.profile_compound output when a ChEMBL id is
    #              present (Shape A: targets × pAct profile)
    # Every attach is GUARDED: an already-present live block is never overwritten, an
    # unrecorded registry key / failed engine is skipped (never a fabricated stub), and a
    # pure biologic run (no SMILES, no SM context) attaches nothing. Fail-open throughout;
    # consistent with the heavy guarded work this finalize already does (boltz2, MHC-II).
    try:
        import validation_registry as _vreg2

        _pl = (pipeline or "").upper()
        _smiles = _first_str_under_keys(result, _SMILES_KEYS, _looks_like_smiles)
        _is_sm = bool(_smiles) or any(
            _t in _pl for _t in ("SMALL", "MOLECULE", "DRUG", "GENERAT", "DESIGN",
                                 "ADMET", "QUANTUM", "VQE", "SQD", "FEP", "AFFINITY",
                                 "DOCK", "METAB", "CHEM", "SELECT"))
        if _is_sm:
            _is_gen = any(_t in _pl for _t in ("GENERAT", "DESIGN")) or _has_key_anywhere(
                result, ("generated", "generative_genmol", "genmol", "molecules"))
            # (a) Registry-backed FULL entries (no model load, no network) — the entry
            #     carries metrics + extra (per_edge / per_case), exactly what these cards read.
            _reg = [
                ("fep_rbfe_alchemical", "fep_rbfe_alchemical", True),
                ("fep_rbfe", "fep_rbfe", True),
                ("generative_genmol", "generative_genmol", _is_gen),
                ("quantum_chem_advantage_boundary", "quantum_chem_advantage_boundary", True),
            ]
            for _ck, _eng, _rel in _reg:
                if not _rel or _ck in result:
                    continue
                _entry = _vreg2.get(_eng)
                if isinstance(_entry, dict):
                    _e = dict(_entry)
                    _e.setdefault("engine", _eng)
                    _e["_source"] = "validation_registry (full recorded engine output)"
                    result[_ck] = _e

            # Opt-out for the heavier LIVE engine runs (default on; input
            # full_engine_emit='off' skips the model-load / ChEMBL round-trips).
            _flag = str((result.get("input") or {}).get("full_engine_emit", "auto")).lower()
            _live_ok = _flag not in ("off", "false", "0", "no")

            # (b) Metabolism — LIVE per-atom SOM + predicted clearance / half-life on the
            #     molecule's SMILES. Each engine independently guarded; partial is fine.
            if _live_ok and _smiles:
                if "site_of_metabolism" not in result:
                    try:
                        import metabolism_som as _msom
                        result["site_of_metabolism"] = _msom.predict_soms(_smiles)
                    except Exception as _e:
                        logger.warning("[finalize] SOM emit skipped: %s", _e)
                if "pk_clearance" not in result or "pk_half_life" not in result:
                    try:
                        import pk_pbpk as _pk
                        if "pk_clearance" not in result:
                            result["pk_clearance"] = _pk.predict_clearance(_smiles)
                        if "pk_half_life" not in result:
                            result["pk_half_life"] = _pk.predict_half_life(_smiles)
                    except Exception as _e:
                        logger.warning("[finalize] PK emit skipped: %s", _e)

            # (c) Selectivity — LIVE profile_compound from ChEMBL when a molecule ChEMBL id
            #     is present (Shape A the card consumes). Disk-cached; skipped if absent.
            if _live_ok and "selectivity_panel" not in result and "selectivity" not in result:
                try:
                    _cid = _first_str_under_keys(result, _CHEMBL_KEYS, _CHEMBL_RE.match)
                    if _cid:
                        import selectivity_panel as _selp
                        _prof = _selp.profile_compound(_cid.upper())
                        if isinstance(_prof, dict) and _prof.get("n_tested"):
                            result["selectivity_panel"] = _prof
                except Exception as _e:
                    logger.warning("[finalize] selectivity emit skipped: %s", _e)
    except Exception as e:
        logger.warning("[finalize] full engine output emission skipped: %s", e)

    # Universal ORIGINATING 1H NMR spectrum (ANCHOR-Q) — ADDITIVE, runs on EVERY
    # pipeline result so the ab-initio spectrum + data always accompany a design,
    # for BOTH modalities via one auto-detector:
    #   * biologic (peptide/antibody/protein sequence) -> conformation-resolved residue
    #     library (instant after warm; picks per-residue backbone state from structure
    #     phi/psi when a folded PDB is present). CSI-validated (beta Halpha downfield).
    #   * small molecule (SMILES) -> full-molecule GIAO (disk-cached).
    # Genuine quantum chemistry (GIAO), TMS-referenced, honestly uncalibrated; a purely
    # ADDITIVE characterization layer — it does NOT alter the design ranking. Reuses this
    # module's own battle-tested sequence/SMILES extractors. Default on (opt-out
    # BIOQL_NMR_LAYER=0); never overwrites an existing nmr_spectrum; fail-open.
    if "nmr_spectrum" not in result:
        try:
            from nmr_layer import nmr_layer
            _seqs = _extract_biologic_sequences(result)
            _pdb = None
            _s3d = result.get("structure_3d")
            if isinstance(_s3d, dict) and isinstance(_s3d.get("pdb"), str):
                _pdb = _s3d["pdb"]
            _nmr = None
            if _seqs:
                # De-novo designs cannot rely on an experimental PDB already
                # existing. If the pipeline has not retained its fold, generate
                # real coordinates on Modal and condition SPARTA+ on them.
                _nmr = nmr_layer(sequence=_seqs[0], pdb_text=_pdb, auto_fold=not bool(_pdb))
            if _nmr is None:
                _sm = _first_str_under_keys(result, _SMILES_KEYS, _looks_like_smiles)
                if _sm:
                    _nmr = nmr_layer(smiles=_sm)
            if _nmr:
                result["nmr_spectrum"] = _nmr
                from nmr_layer import nmr_quality_review
                result["nmr_quality_review"] = nmr_quality_review(_nmr)
        except Exception as e:
            logger.warning("[finalize] NMR spectrum skipped: %s", e)

    # Universal PREDICTED (forward) MS/MS spectrum — ADDITIVE, same pattern as the NMR layer.
    # Given the DESIGNED molecule/sequence, predict the MS/MS fragmentation spectrum you'd see
    # on an instrument (small molecule -> in-silico bond cleavage; peptide/antibody -> b/y ions).
    # A predicted characterization, not an input to sequence. Default on (BIOQL_MSMS_LAYER=0 to
    # disable); never overwrites; fail-open. Reuses this module's own sequence/SMILES extractors.
    if "msms_spectrum" not in result:
        try:
            from msms_layer import msms_layer
            _seqs = _extract_biologic_sequences(result)
            _ms = None
            if _seqs:
                _ms = msms_layer(sequence=_seqs[0])
            if _ms is None:
                _sm = _first_str_under_keys(result, _SMILES_KEYS, _looks_like_smiles)
                if _sm:
                    _ms = msms_layer(smiles=_sm)
            if _ms:
                result["msms_spectrum"] = _ms
        except Exception as e:
            logger.warning("[finalize] MS/MS spectrum skipped: %s", e)

    # Universal QSurfaceDock surface-patch QAP analysis — ADDITIVE, for any result carrying a
    # protein-protein/ligand COMPLEX (antibody-antigen, peptide-target, docking pose). Auto-picks
    # the interface chain pair, extracts physicochemical surface patches, solves the correspondence
    # as a QAP (linear complementarity + quadratic geometric consistency) on the quantum QUBO backend
    # vs the classical-linear baseline, and reports the QUANTUM ADVANTAGE. Cost-disciplined: bounded to
    # the LOCAL exact solver (n_patches=4 => 16 vars, $0 Modal); image render opt-in (BIOQL_QSURFACE_RENDER).
    # Default on (BIOQL_QSURFACE_LAYER=0 to disable); never overwrites; fail-open.
    if "qsurface_dock" not in result:
        try:
            from qsurface_layer import qsurface_layer
            # locate a complex PDB with >=2 chains anywhere in the result
            def _find_complex_pdb(node, depth=0):
                if depth > 6:
                    return None
                if isinstance(node, dict):
                    for k in ("complex_pdb", "structure_pdb", "pdb"):
                        v = node.get(k)
                        if isinstance(v, str) and "ATOM" in v[:3000]:
                            chains = set(l[21] for l in v.splitlines()
                                         if l.startswith("ATOM") and len(l) > 21)
                            if len(chains) >= 2:
                                return v
                    for v in node.values():
                        r = _find_complex_pdb(v, depth + 1)
                        if r:
                            return r
                elif isinstance(node, (list, tuple)):
                    for v in node[:25]:
                        r = _find_complex_pdb(v, depth + 1)
                        if r:
                            return r
                return None
            _cx = _find_complex_pdb(result)
            if _cx:
                _qs = qsurface_layer(_cx)
                if _qs:
                    result["qsurface_dock"] = _qs
        except Exception as e:
            logger.warning("[finalize] QSurfaceDock skipped: %s", e)

    # Universal QSurfaceDesign inverse-redesign suggestion — ADDITIVE, for any result carrying a
    # protein complex. Redesigns the interface residues via a QUBO (linear surface complementarity +
    # quadratic residue coupling) and reports a candidate Gen-1 with its QAP-objective change. Cost:
    # local exact solver ($0); refold opt-in (BIOQL_QSURFACE_REFOLD). Default on (BIOQL_QSURFACE_DESIGN=0
    # to disable); never overwrites; fail-open. Reuses the complex PDB located for QSurfaceDock above.
    if "qsurface_design" not in result:
        try:
            from qsurface_design_layer import qsurface_design_layer
            def _find_complex_pdb2(node, depth=0):
                if depth > 6:
                    return None
                if isinstance(node, dict):
                    for k in ("complex_pdb", "structure_pdb", "pdb"):
                        v = node.get(k)
                        if isinstance(v, str) and "ATOM" in v[:3000]:
                            ch = set(l[21] for l in v.splitlines() if l.startswith("ATOM") and len(l) > 21)
                            if len(ch) >= 2:
                                return v
                    for v in node.values():
                        r = _find_complex_pdb2(v, depth + 1)
                        if r:
                            return r
                elif isinstance(node, (list, tuple)):
                    for v in node[:25]:
                        r = _find_complex_pdb2(v, depth + 1)
                        if r:
                            return r
                return None
            _cx2 = _find_complex_pdb2(result)
            if _cx2:
                # antigen gene (for negative-design specificity vs off-target ortholog)
                _ai = result.get("antigen_identity") if isinstance(result.get("antigen_identity"), dict) else {}
                _gene = (_ai.get("gene") or (_ai.get("source_result") or {}).get("gene")
                         or (result.get("target") if isinstance(result.get("target"), str) else None))
                _qd = qsurface_design_layer(_cx2, antigen_gene=_gene)
                if _qd:
                    result["qsurface_design"] = _qd
        except Exception as e:
            logger.warning("[finalize] QSurfaceDesign skipped: %s", e)

    # Provenance ledger — LAST so it stamps the fully-assembled result.
    if "provenance_manifest" not in result:
        try:
            from provenance_ledger import build_bundle
            result["provenance_manifest"] = build_bundle(result, timestamp=ts)
        except Exception as e:
            logger.warning("[finalize] provenance skipped: %s", e)

    # Universal COMPETITIVE LANDSCAPE (ADDITIVE, read-only). Every pipeline,
    # every modality: what already exists against this target × indication, so
    # a result is never read as if it were first in its field. Free public
    # sources (ClinicalTrials.gov / OpenFDA / ChEMBL) + Gosset (assets incl.
    # preclinical and DISCONTINUED programmes, deal flow, company positioning,
    # approvals/designations/discontinuations). Written to the key the HTML
    # report's §18 already reads, so every pipeline gains the section without
    # touching 37 pipeline files.
    #
    # DELIBERATELY AFTER build_bundle, and this ordering is load-bearing: the
    # provenance manifest attributes every unstamped leaf as
    # engine="UNKNOWN", stamped=False. Running this before it put ~600 rows of
    # third-party market records into the manifest -- 155 KB of landscape
    # inflating the manifest by ~2 MB, measured 2026-09-13 -- and they are not
    # BioQL claims to attribute: they are external reference data that already
    # carries its own per-record source URLs from Gosset. So the landscape is
    # NOT covered by integrity_hash; it is cited data, not a computed claim.
    # Anything here that ever becomes a derived BioQL number must move above.
    #
    # Gated on a target being present: a pure-chemistry calc with no target
    # pays no network round-trip. Cached 6 h per target × indication inside
    # bioql_competitive_intelligence. Guarded like every block -- a failure is
    # declared, never fabricated, never fatal.
    if "competitive_landscape" not in result:
        try:
            _tgt = _first_str_under_keys(
                result,
                {"target", "target_name", "target_symbol", "gene", "gene_symbol",
                 "symbol", "uniprot_gene"},
                _looks_like_target)
            _ind = _first_str_under_keys(
                result,
                {"disease", "disease_name", "indication", "condition",
                 "disease_query"},
                _looks_like_indication)
            if not _tgt:
                result["competitive_landscape"] = {
                    "available": False,
                    "reason": ("no target/gene symbol present in this result, so "
                               "there is no target × indication to search a "
                               "landscape for"),
                }
            else:
                from bioql_competitive_intelligence import (
                    molevera_competitive_intelligence)
                _cl = molevera_competitive_intelligence(_tgt, _ind or "")
                result["competitive_landscape"] = _cl or {
                    "available": False,
                    "reason": ("every competitive source returned empty for "
                               "%s × %s" % (_tgt, _ind or "(no indication)")),
                }
        except Exception as e:
            logger.warning("[finalize] competitive landscape skipped: %s", e)
            result["competitive_landscape"] = {
                "available": False,
                "reason": "competitive landscape failed: %s: %s" % (
                    type(e).__name__, str(e)[:200]),
            }

    result = _attach_efficacious_dose(result)
    return result
