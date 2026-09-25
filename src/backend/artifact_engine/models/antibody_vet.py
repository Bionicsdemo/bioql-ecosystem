"""
Artifact model for the veterinary antibody pipeline
(`molevera_veterinary_antibody_design_v1`, and the older `molvera_...` spelling).

This pipeline designs an antibody for an ANIMAL, not for a person, and almost
everything that makes it veterinary is a decision about whose immune system the
molecule has to live in: the antigen is pulled from the target species' own
proteome, the variable-region framework is sourced for that species, the
constant tail is that species' isotype, and the human MHC machinery the rest of
BioQL owns is deliberately NOT reused -- so species immunogenicity comes back
uncomputed, with the pipeline's own reason.

The chapters follow that decision chain: antigen, framework, the loops the VQE
searched, the five candidates, the folded complex, what could not be measured in
this species, the PK priors borrowed from published veterinary products, the
quantum ledger, and the studies that would still have to be run.

Everything the page states as verified is recomputed here from the run's own
data: the variable domains are reassembled from their framework regions and
CDRs, the mature chains from their constant tails, the complex's residue count
from VH + VL + antigen, the affinity ranking from the raw VQE scores, the
interface from the drawn coordinates, the mean per-residue confidence from the
drawn PDB's own B-factor column, and the phase priors from their factors. Some
of those checks FAIL on the reference runs -- that is the point of having them.

MOLEVERA / BIOQL
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import facts as F

PIPELINE = "molevera_veterinary_antibody_design_v1"
PIPELINES = (
    "molevera_veterinary_antibody_design_v1",
    "molvera_veterinary_antibody_design_v1",
)
TITLE = {"es": "Anticuerpo veterinario", "en": "Veterinary antibody"}

ST = "stages"
S1 = f"{ST}.01_target_analysis"
S2 = f"{ST}.02_cdr_design"
S3 = f"{ST}.03_veterinary_framework"
S4 = f"{ST}.04_species_compatibility"
S5 = f"{ST}.05_developability"
S6 = f"{ST}.06_candidate_generation"
S7 = f"{ST}.07_binding_ranking"
S8 = f"{ST}.08_species_immunogenicity"
S9 = f"{ST}.09_structure_prediction"
S10 = f"{ST}.10_veterinary_pk_product"
S11 = f"{ST}.11_candidate_selection"
S12 = f"{ST}.12_development_package"
LEAD = "lead_candidate"

ALIASES = {
    "t": S1,
    "cd": S2,
    "fw": S3,
    "cp": S4,
    "dv": S5,
    "gn": S6,
    "bd": S7,
    "im": S8,
    "sp": S9,
    "pkst": S10,
    "sel": S11,
    "wp": S12,
    "ag": "antigen_identity",
    "vf": "veterinary_framework",
    "fr": "framework_regions",
    "L": LEAD,
    "q": "quantum_analyses",
    "qc": "quantum_contribution",
    "qp": "quantum_provenance",
    "ad": "admet",
    "tx": "toxicology",
    "ph": "pharmacology",
    "dk": "docking",
    "px": "protenix_structure",
    "st": "structure_3d",
    "cx": "complex_structure_3d",
    "si": "species_immunogenicity",
    "di": "deimmunization",
    "tpp": "veterinary_product_profile",
    "dp": "development_plan",
    "ct": "clinical_trial",
    "sm": "summary",
    "it": "iterations",
    "nmr": "nmr_spectrum",
    "sps": "species",
    "pg": "program",
}

CONTACT_A = 8.0  # CA-CA, the usual working definition of a residue-residue contact


def chain_label(r: Dict[str, Any], part: Dict[str, Any]) -> str:
    """What to write on a chain of the drawn complex: VH, VL or the target's own symbol."""
    if part["key"] == "antigen":
        return str(
            F.get(r, "target.symbol") or F.get(r, "complex_structure_3d.receptor") or "antigen"
        )
    return {"vh": "VH", "vl": "VL"}.get(part["key"] or "", f"chain {part['chain']}")


# ── the pipeline ──────────────────────────────────────────────────────────────────
def matches(result: Dict[str, Any]) -> bool:
    """True only for this pipeline, under either spelling of its id."""
    r = unwrap(result)
    p = str(r.get("pipeline") or "").strip().lower()
    if p in PIPELINES or p.startswith(
        ("molevera_veterinary_antibody", "molvera_veterinary_antibody")
    ):
        return True
    st = r.get("stages")
    return (
        isinstance(st, dict)
        and "03_veterinary_framework" in st
        and "08_species_immunogenicity" in st
        and isinstance(r.get("veterinary_framework"), dict)
    )


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("result"), dict):
        inner = result["result"]
        if "stages" in inner or "veterinary_framework" in inner:
            return inner
    return result


def subject(r: Dict[str, Any]) -> str:
    sp = F.get(r, "species.label") or F.get(r, "program.species.label") or ""
    taxon = F.get(r, "species.taxon_id")
    tgt = F.get(r, "target.symbol") or F.get(r, "target.name") or ""
    fmt = r.get("antibody_format") or ""
    head = f"{sp} ({taxon})" if sp and taxon else str(sp)
    return " · ".join(x for x in (head, f"anti-{tgt}" if tgt else "", str(fmt)) if x)


# ── small derivations over the run's own data ─────────────────────────────────────
def _num(x: Any) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def lead(r: Dict[str, Any]) -> Dict[str, Any]:
    c = F.get(r, LEAD)
    return c if isinstance(c, dict) else {}


def candidates(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in (r.get("candidates") or []) if isinstance(c, dict)]


def ca_residues(pdb: Any) -> List[Dict[str, Any]]:
    """One CA per residue of the first model: chain, number, name, xyz, B-factor."""
    if not isinstance(pdb, str):
        return []
    out: List[Dict[str, Any]] = []
    for ln in pdb.splitlines():
        if ln.startswith("ENDMDL"):
            break
        if not ln.startswith(("ATOM  ", "HETATM")) or ln[12:16].strip() != "CA":
            continue
        try:
            out.append(
                {
                    "chain": ln[21].strip() or "A",
                    "resi": ln[22:27].strip(),
                    "resn": ln[17:20].strip(),
                    "p": (float(ln[30:38]), float(ln[38:46]), float(ln[46:54])),
                    "b": float(ln[60:66]) if ln[60:66].strip() else None,
                }
            )
        except ValueError:
            continue
    return out


def chain_runs(res: Sequence[Dict[str, Any]]) -> List[Tuple[str, int, int]]:
    """(chain id, first index, end index) for each run of residues in file order."""
    runs: List[Tuple[str, int, int]] = []
    for i, x in enumerate(res):
        if runs and runs[-1][0] == x["chain"]:
            runs[-1] = (runs[-1][0], runs[-1][1], i + 1)
        else:
            runs.append((x["chain"], i, i + 1))
    return runs


def chain_parts(r: Dict[str, Any], res: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Name each chain of the folded complex by matching its length to the run's own.

    A chain is called VH, VL or antigen only when its residue count equals the
    length the run itself recorded for that piece; anything else stays unnamed.
    """
    c = lead(r)
    want = [
        ("vh", _num(c.get("vh_length"))),
        ("vl", _num(c.get("vl_length"))),
        ("antigen", _num(F.get(r, "antigen_identity.length_aa"))),
    ]
    used: set = set()
    out: List[Dict[str, Any]] = []
    for cid, i, j in chain_runs(res):
        name = None
        for key, n in want:
            if key not in used and n is not None and int(n) == j - i:
                name = key
                used.add(key)
                break
        out.append({"key": name, "chain": cid, "from": i, "to": j, "n": j - i})
    return out


def part_span(parts: Sequence[Dict[str, Any]], key: str) -> Optional[Tuple[int, int]]:
    for p in parts:
        if p["key"] == key:
            return p["from"], p["to"]
    return None


def cdr_span(seq: Any, cdr: Any) -> Optional[Tuple[int, int]]:
    """Where a CDR sits inside its own variable domain, found by exact sequence."""
    if not isinstance(seq, str) or not isinstance(cdr, str) or len(cdr) < 3:
        return None
    i = seq.find(cdr)
    return (i, i + len(cdr)) if i >= 0 else None


def regions_of(seq: Any, frames: Any, cdrs: Sequence[Any], prefix: str) -> List[Dict[str, Any]]:
    """FR/CDR blocks of one variable domain, located by exact sequence match."""
    out: List[Dict[str, Any]] = []
    if not isinstance(seq, str):
        return out
    blocks: List[Tuple[str, Any]] = []
    fr = frames if isinstance(frames, dict) else {}
    for i, cdr in enumerate(cdrs):
        blocks.append((f"FR{i + 1}", fr.get(f"FR{i + 1}")))
        blocks.append((f"{prefix}{i + 1}", cdr))
    blocks.append(("FR4", fr.get("FR4")))
    pos = 0
    for name, part in blocks:
        if not isinstance(part, str) or not part:
            continue
        i = seq.find(part, pos)
        if i < 0:
            continue
        out.append({"name": name, "start": i, "end": i + len(part), "seq": part})
        pos = i + len(part)
    return out


def reference_cdrs(r: Dict[str, Any], chain: str) -> List[str]:
    """The loops of the framework the design was grafted onto, read back from it.

    The run stores the reference variable domain and the framework regions, so
    what sits between FR1/FR2, FR2/FR3 and FR3/FR4 in that reference is the
    framework's own CDR -- no external germline database is consulted.
    """
    ref = F.get(r, f"veterinary_framework.{chain}_reference_sequence")
    fr = F.get(r, f"framework_regions.{chain}")
    if not isinstance(ref, str) or not isinstance(fr, dict):
        return []
    out, pos = [], 0
    for a, b in (("FR1", "FR2"), ("FR2", "FR3"), ("FR3", "FR4")):
        fa, fb = fr.get(a), fr.get(b)
        if not isinstance(fa, str) or not isinstance(fb, str):
            return []
        ia = ref.find(fa, pos)
        ib = ref.find(fb, ia + len(fa)) if ia >= 0 else -1
        if ia < 0 or ib < 0:
            return []
        out.append(ref[ia + len(fa) : ib])
        pos = ib
    return out


def designed_cdrs(r: Dict[str, Any], chain: str) -> List[str]:
    c = lead(r)
    return [str(c.get(f"cdr_{chain[1]}{i}") or "") for i in (1, 2, 3)]


def ranks(values: Sequence[Any], best: str = "low") -> Dict[int, int]:
    """Position of each entry once the list is ordered; 1 is best."""
    pairs = [(i, _num(v)) for i, v in enumerate(values)]
    pairs = [(i, v) for i, v in pairs if v is not None]
    pairs.sort(key=lambda kv: kv[1] if best == "low" else -kv[1])
    return {i: k + 1 for k, (i, _) in enumerate(pairs)}


def selection_table(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every candidate with the two ranks the run says it selected on."""
    cands = candidates(r)
    if not cands:
        return []
    energy = [F.get(c, "scores.binding_energy") for c in cands]
    iptm = [F.get(c, "scores.iptm") for c in cands]
    ra, ri = ranks(energy, "low"), ranks(iptm, "high")
    out = []
    for i, c in enumerate(cands):
        a, b = ra.get(i), ri.get(i)
        out.append(
            {
                "id": c.get("candidate_id"),
                "cdr_h3": c.get("cdr_h3"),
                "energy": _num(energy[i]),
                "iptm": _num(iptm[i]),
                "affinity_rank": a,
                "iptm_rank": b,
                "composite": (a + b) / 2 if a and b else None,
                "liabilities": F.get(c, "developability.n_liabilities"),
                "mw": _num(c.get("mw")),
                "plddt": F.get(c, "protenix_structure.plddt"),
            }
        )
    return out


def selection_winners(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Who wins under each of the two rules this pipeline uses to describe itself.

    `stages.11.ranking_method` describes a lexicographic rule (affinity, then
    liabilities, then ipTM); the lead's own `selection_basis` sometimes describes a
    composite rule (the mean of the affinity and ipTM ranks). They are not the same
    rule, so both are recomputed and the run is judged against the one it names.
    """
    scored = [x for x in selection_table(r) if x["composite"] is not None]
    if not scored:
        return None
    basis = " ".join(str(x) for x in (F.get(r, f"{LEAD}.selection_basis") or []))
    return {
        "rows": scored,
        "composite": min(scored, key=lambda x: (x["composite"], x["affinity_rank"])),
        "lexicographic": min(
            scored,
            key=lambda x: (
                x["affinity_rank"],
                x["liabilities"] if isinstance(x["liabilities"], int) else 99,
                -(x["iptm"] or 0.0),
            ),
        ),
        "declared": "composite" if "composite rank" in basis.lower() else "lexicographic",
    }


def interface(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The antibody-antigen contacts implied by the coordinates that were drawn.

    The run names no epitope residue, so this is read off the model itself: the
    antigen residues whose CA sits within 8 A of a CA of the heavy-chain third
    loop, plus the closest approach.
    """
    res = ca_residues(F.get(r, "structure_3d.pdb"))
    if not res:
        return None
    parts = chain_parts(r, res)
    vh, ag = part_span(parts, "vh"), part_span(parts, "antigen")
    c = lead(r)
    span = cdr_span(c.get("vh_sequence"), c.get("cdr_h3"))
    if not vh or not ag or not span:
        return None
    loop = res[vh[0] + span[0] : vh[0] + span[1]]
    antigen = res[ag[0] : ag[1]]
    if not loop or not antigen:
        return None
    best, near = None, []
    for k, a in enumerate(antigen):
        d = min(math.dist(a["p"], ln["p"]) for ln in loop)
        if best is None or d < best[0]:
            best = (d, k, a)
        if d <= CONTACT_A:
            near.append({"i": k, "resn": a["resn"], "resi": a["resi"], "d": round(d, 2)})
    return {
        "n_contacts": len(near),
        "contacts": near[:12],
        "closest_A": round(best[0], 2) if best else None,
        "closest_label": f"{best[2]['resn']}{best[2]['resi']}" if best else "",
        "closest_index": ag[0] + best[1] if best else None,
        "loop_from": vh[0] + span[0],
        "loop_to": vh[0] + span[1],
        "n_antigen": len(antigen),
    }


def mean_b(res: Sequence[Dict[str, Any]]) -> Optional[float]:
    vals = [x["b"] for x in res if isinstance(x.get("b"), (int, float))]
    return sum(vals) / len(vals) if vals else None


def centroid(points: Sequence[Sequence[float]]) -> Optional[List[float]]:
    if not points:
        return None
    n = len(points)
    return [round(sum(p[k] for p in points) / n, 3) for k in range(3)]


# ── scenes ────────────────────────────────────────────────────────────────────────
def scene_cover(r: Dict[str, Any], key: Optional[str]) -> Dict[str, Any]:
    c = lead(r)
    stats = [
        ("candidatos", "candidates", r.get("candidate_count"), "", "candidate_count"),
        (
            "antígeno",
            "antigen",
            F.get(r, "antigen_identity.length_aa"),
            "aa",
            "antigen_identity.length_aa",
        ),
        ("VH", "VH", c.get("vh_length"), "aa", f"{LEAD}.vh_length"),
        ("VL", "VL", c.get("vl_length"), "aa", f"{LEAD}.vl_length"),
        (
            "ipTM",
            "ipTM",
            F.get(r, "protenix_structure.iptm"),
            "",
            "protenix_structure.iptm",
        ),
        (
            "cuántico medido",
            "measured quantum",
            F.get(r, "quantum_contribution.measured_quantum_pct"),
            "%",
            "quantum_contribution.measured_quantum_pct",
        ),
    ]
    return {
        "type": "cover",
        "mesh": key,
        "stats": [
            {"es": es, "en": en, "value": v, "unit": u, "path": p}
            for es, en, v, u, p in stats
            if v is not None
        ],
    }


def scene_antigen(r: Dict[str, Any], key: Optional[str], meshes: Dict[str, Any]) -> Dict[str, Any]:
    """The complex, with the antigen chain first so the camera flies to it."""
    m = meshes.get(key or "")
    doms, notes = [], []
    if m:
        parts = chain_parts(r, m.get("res") or [])
        order = {"antigen": 0, "vh": 1, "vl": 2}
        for p in sorted(parts, key=lambda x: order.get(x["key"] or "", 9)):
            doms.append({"name": chain_label(r, p), "from": p["from"], "to": p["to"]})
            pos = centroid([res["p"] for res in (m.get("res") or [])[p["from"] : p["to"]]])
            if pos:
                notes.append({"text": f"{doms[-1]['name']} · {p['n']} aa", "pos": pos})
    return {
        "type": "cartoon",
        "mesh": key,
        "domains": doms,
        "receptors": [x for x in [F.get(r, "target.symbol")] if x],
        "annotations": notes,
    }


def scene_framework(r: Dict[str, Any]) -> Dict[str, Any]:
    c = lead(r)
    items = [
        (c.get("vh_sequence"), "VH designed"),
        (F.get(r, "veterinary_framework.vh_reference_sequence"), "VH reference"),
        (c.get("vl_sequence"), "VL designed"),
        (F.get(r, "veterinary_framework.vl_reference_sequence"), "VL reference"),
    ]
    items = [{"seq": s, "source": src} for s, src in items if isinstance(s, str) and s]
    return {
        "type": "sequences",
        "items": items,
        "n": len(items),
        "jobs": 0,
        "stats": [
            {
                "es": "marco pesado",
                "en": "heavy constant",
                "value": F.get(
                    r, "veterinary_framework.constant_region_resolution.heavy.length_aa"
                ),
                "unit": "aa",
            },
            {
                "es": "marco ligero",
                "en": "light constant",
                "value": F.get(
                    r, "veterinary_framework.constant_region_resolution.light.length_aa"
                ),
                "unit": "aa",
            },
        ],
    }


def scene_cdrs(r: Dict[str, Any]) -> Dict[str, Any]:
    c = lead(r)
    seq = c.get("vh_sequence") if isinstance(c.get("vh_sequence"), str) else ""
    regions = regions_of(seq, F.get(r, "framework_regions.vh"), designed_cdrs(r, "vh"), "CDR-H")
    doms = [x for x in regions if x["name"].startswith("CDR")]
    return {
        "type": "protein_chain",
        "seq": seq,
        "signal": 0,
        "domains": [{"name": d["name"], "start": d["start"], "end": d["end"]} for d in doms],
        "cys": [i for i, a in enumerate(seq) if a == "C"],
        "mesh": None,
    }


def scene_candidates(r: Dict[str, Any]) -> Dict[str, Any]:
    """The five, in the order the run's own rule puts them."""
    big = float("inf")
    rows = sorted(
        selection_table(r),
        key=lambda x: (
            x["composite"] if x["composite"] is not None else big,
            x["affinity_rank"] if x["affinity_rank"] is not None else big,
        ),
    )
    return {
        "type": "ranking",
        "items": [
            {
                "rank": i + 1,
                "seq": x["cdr_h3"],
                "score": x["iptm"],
                "mw": x["mw"],
                "charge": x["composite"],
                "half_life_h": None,
                "protease": x["plddt"],
                "aggregation": x["liabilities"],
                "changes": x["affinity_rank"],
            }
            for i, x in enumerate(rows)
        ],
    }


def scene_structure(
    r: Dict[str, Any], key: Optional[str], meshes: Dict[str, Any]
) -> Dict[str, Any]:
    """The folded complex, with the loop that was searched labelled and measured."""
    m = meshes.get(key or "")
    doms, notes, lines = [], [], []
    if m:
        res = m.get("res") or []
        parts = chain_parts(r, res)
        for p in parts:
            doms.append({"name": chain_label(r, p), "from": p["from"], "to": p["to"]})
        face = interface(r)
        if face and res:
            loop = res[face["loop_from"] : face["loop_to"]]
            a = centroid([x["p"] for x in loop])
            b = res[face["closest_index"]]["p"] if face["closest_index"] is not None else None
            if a:
                notes.append({"text": "CDR-H3", "pos": [a[0], a[1] + 4.0, a[2]]})
            if a and b and face["closest_A"] is not None:
                lines.append(
                    {
                        "from": a,
                        "to": list(b),
                        "label": f"CDR-H3 → {face['closest_label']} · {face['closest_A']} Å",
                    }
                )
    return {
        "type": "cartoon",
        "mesh": key,
        "domains": doms,
        "receptors": [x for x in [F.get(r, "complex_structure_3d.receptor")] if x],
        "annotations": notes,
        "measures": lines,
    }


def scene_pk(r: Dict[str, Any]) -> Dict[str, Any]:
    half_days = _num(F.get(r, "admet.excretion.half_life_days.value"))
    bio = _num(F.get(r, "admet.absorption.sc_bioavailability_pct.value"))
    return {
        "type": "pk",
        "half_life_h": round(half_days * 24, 1) if half_days is not None else None,
        "bioavailability": bio,
        "score": None,
        "pk": F.get(r, "admet.pk_prior") or {},
        "pd": F.get(r, "pharmacology.pharmacodynamics") or {},
    }


def scene_quantum(r: Dict[str, Any]) -> Dict[str, Any]:
    h = F.get(r, "quantum_analyses.quantum_real_hamiltonian") or {}
    return {
        "type": "quantum",
        "n_qubits": h.get("n_qubits"),
        "n_terms": h.get("n_terms"),
        "n_contacts": h.get("n_contacts"),
        "n_residues": h.get("n_residues"),
        "energy": h.get("vqe_energy_Ha"),
        "reference": h.get("reference_energy_Ha"),
        "backend": F.get(r, "quantum_provenance.backend"),
        "algorithms": [
            x.get("algorithm") for x in (F.get(r, "quantum_contribution.stage_ledger") or [])
        ],
    }


def scene_development(r: Dict[str, Any]) -> Dict[str, Any]:
    p = "clinical_trial.ptrs_cohort_prior"
    rows = [
        ("phase", "P1->2", f"{p}.phase_1_to_2.value"),
        ("phase", "P2->3", f"{p}.phase_2_to_3.value"),
        ("phase", "P3->approval", f"{p}.phase_3_to_approval.value"),
        ("cumulative", "approval", f"{p}.cumulative_approval.value"),
    ]
    items = []
    for group, name, path in rows:
        v = _num(F.get(r, path))
        if v is not None:
            items.append(
                {
                    "group": group,
                    "name": name,
                    "value": v,
                    "label": name,
                    "unit": "",
                    "note": F.get(r, "clinical_trial.status"),
                }
            )
    return {
        "type": "endpoints",
        "model": F.get(r, f"{p}.cumulative_approval.method"),
        "n": len(items),
        "score": _num(F.get(r, "clinical_trial.development_summary.approval_probability.value")),
        "items": items,
    }


# ── generated beats (one per row the run actually has) ────────────────────────────
def work_package_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for i, w in enumerate(F.get(r, "development_plan.work_packages") or []):
        if not isinstance(w, dict) or not w.get("id"):
            continue
        out.append(
            {
                "es": f"{{dp:work_packages[{i}].id}} · {{dp:work_packages[{i}].name}}: "
                f"{{dp:work_packages[{i}].required}}.",
                "en": f"{{dp:work_packages[{i}].id}} · {{dp:work_packages[{i}].name}}: "
                f"{{dp:work_packages[{i}].required}}.",
                "kind": "gap",
                "focus": {"group": "phase"},
            }
        )
    return out


def ledger_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for i, s in enumerate(F.get(r, "quantum_contribution.stage_ledger") or []):
        if not isinstance(s, dict) or not s.get("stage"):
            continue
        out.append(
            {
                "es": f"{{qc:stage_ledger[{i}].stage}} corre con {{qc:stage_ledger[{i}].algorithm}} "
                f"y cuenta como {{qc:stage_ledger[{i}].compute_class}}; entrega salida cuántica: "
                f"{{qc:stage_ledger[{i}].delivers_quantum_output}}.",
                "en": f"{{qc:stage_ledger[{i}].stage}} runs on {{qc:stage_ledger[{i}].algorithm}} "
                f"and counts as {{qc:stage_ledger[{i}].compute_class}}; delivers quantum output: "
                f"{{qc:stage_ledger[{i}].delivers_quantum_output}}.",
                "tech": {
                    "es": f"Evidencia: {{qc:stage_ledger[{i}].evidence}}.",
                    "en": f"Evidence: {{qc:stage_ledger[{i}].evidence}}.",
                },
                "focus": {"register": True},
            }
        )
    return out


# ── chapters ──────────────────────────────────────────────────────────────────────
def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    cx = mesh_keys.get("complex")
    return [
        {
            "id": "overview",
            "title": {"es": "La corrida", "en": "The run"},
            "claims": [
                "success",
                "status",
                "pipeline",
                "pipeline_version",
                "signature",
                "program_id",
                "run_id",
                "created_at",
                "study_type",
                "modality",
                "program",
                "species",
                "antibody_format",
                "candidate_count",
                "summary",
                "honesty",
            ],
            "scene": scene_cover(r, cx),
            "beats": [
                {
                    "es": "Esta página explica una corrida del pipeline {pipeline} "
                    "(versión {pipeline_version}), registrada el {created_at}.",
                    "en": "This page explains one run of the {pipeline} pipeline "
                    "(version {pipeline_version}), recorded on {created_at}.",
                    "tech": {
                        "es": "Corrida {run_id}, programa {program_id}, tipo de estudio {study_type}.",
                        "en": "Run {run_id}, program {program_id}, study type {study_type}.",
                    },
                },
                {
                    "es": "El programa diseña un anticuerpo ({modality}) para {sps:label} "
                    "(taxón {sps:taxon_id}) contra {target.symbol}.",
                    "en": "The program designs an antibody ({modality}) for {sps:label} "
                    "(taxon {sps:taxon_id}) against {target.symbol}.",
                    "tech": {
                        "es": "Identificador del programa derivado así: {pg:program_id_source}.",
                        "en": "Program identifier derived as: {pg:program_id_source}.",
                    },
                },
                {
                    "es": "Que sea veterinario no es una etiqueta: el antígeno, el armazón variable "
                    "y la cola constante se buscan en la propia especie, y los modelos de MHC "
                    "humanos del resto de la plataforma no se reutilizan aquí.",
                    "en": "Being veterinary is not a label: the antigen, the variable framework and "
                    "the constant tail are all sourced from that species, and the human MHC models "
                    "the rest of the platform owns are not reused here.",
                    "kind": "note",
                },
                {
                    "es": "El formato es {antibody_format}; la corrida entrega {candidate_count} "
                    "candidatos y elige {sm:lead_candidate_id}.",
                    "en": "The format is {antibody_format}; the run produces {candidate_count} "
                    "candidates and picks {sm:lead_candidate_id}.",
                },
                {
                    "es": "Termina en estado {status}, con lectura {sm:readiness}.",
                    "en": "It ends in state {status}, read as {sm:readiness}.",
                    "tech": {
                        "es": "Éxito declarado: {success}. Firma {signature}.",
                        "en": "Declared success: {success}. Signature {signature}.",
                    },
                },
                {
                    "es": "En palabras de la corrida: {honesty}",
                    "en": "In the run's own words: {honesty}",
                    "kind": "note",
                },
                {
                    "es": "Cada número de esta página se lee del resultado de la corrida; cada valor "
                    "del resultado aparece en algún capítulo o en el anexo.",
                    "en": "Every number on this page is read from the run's result; every value in "
                    "that result appears in some chapter or in the annex.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "antigen",
            "title": {"es": "El antígeno de la especie", "en": "The species' own antigen"},
            "claims": ["antigen_identity", S1, "target"],
            "scene": scene_antigen(r, cx, meshes),
            "beats": [
                {
                    "es": "El antígeno es {ag:protein_name} de {ag:organism}: la entrada "
                    "{ag:accession} de UniProt, {ag:length_aa} aminoácidos. No es la proteína "
                    "humana homóloga, sino la de la especie que va a recibir el fármaco.",
                    "en": "The antigen is {ag:protein_name} from {ag:organism}: UniProt entry "
                    "{ag:accession}, {ag:length_aa} amino acids. Not the human homologue, but the "
                    "protein of the species that would receive the drug.",
                    "focus": {"color": "domains"},
                    "tech": {
                        "es": "Resuelto en vivo contra {ag:source}; {ag:source_url}; "
                        "sha256 de la secuencia {ag:sequence_sha256}.",
                        "en": "Resolved live against {ag:source}; {ag:source_url}; "
                        "sequence sha256 {ag:sequence_sha256}.",
                    },
                    "gap": ["antigen_identity"],
                    "gap_es": "Sin identidad de antígeno",
                    "gap_en": "No antigen identity",
                },
                {
                    "es": "La entrada no está revisada por curadores: {ag:selection_status}, con "
                    "existencia proteica {ag:protein_existence} y {ag:refseq_accessions|count} "
                    "referencias cruzadas en RefSeq.",
                    "en": "The entry is not curator-reviewed: {ag:selection_status}, with protein "
                    "existence {ag:protein_existence} and {ag:refseq_accessions|count} RefSeq "
                    "cross-references.",
                    "tech": {
                        "es": "Base de la selección: {ag:selection_basis}; puntuación de evidencia "
                        "{ag:selection_evidence_score}; confianza {ag:isoform_selection_confidence}.",
                        "en": "Selection basis: {ag:selection_basis}; evidence score "
                        "{ag:selection_evidence_score}; confidence {ag:isoform_selection_confidence}.",
                    },
                },
                {
                    "es": "De {ag:n_candidates} entradas posibles se eligió ésta por "
                    "{ag:isoform_resolution}; la descartada, {ag:alternatives_not_selected[0].accession}, "
                    "mide {ag:alternatives_not_selected[0].length_aa} aminoácidos y puntuó "
                    "{ag:alternatives_not_selected[0].evidence_score}.",
                    "en": "Of {ag:n_candidates} possible entries this one was taken by "
                    "{ag:isoform_resolution}; the one left out, "
                    "{ag:alternatives_not_selected[0].accession}, is "
                    "{ag:alternatives_not_selected[0].length_aa} amino acids and scored "
                    "{ag:alternatives_not_selected[0].evidence_score}.",
                    "tech": {
                        "es": "Para forzar otra isoforma: {ag:override_hint}",
                        "en": "To force another isoform: {ag:override_hint}",
                    },
                },
                {
                    "es": "Una isoforma distinta es una diana distinta: esa elección decide contra "
                    "qué superficie se diseñan las asas, y aquí se hizo automáticamente.",
                    "en": "A different isoform is a different target: the isoform choice decides "
                    "which surface the loops are designed against, and here it was made "
                    "automatically.",
                    "kind": "note",
                },
                {
                    "es": "Con la secuencia resuelta, el análisis de diana declara {t:antigen_length} "
                    "residuos, druggability {t:druggability} y clase de diana {t:target_class}.",
                    "en": "With the sequence resolved, target analysis records {t:antigen_length} "
                    "residues, druggability {t:druggability} and target class {t:target_class}.",
                    "tech": {
                        "es": "Contexto tomado de {t:antigen_context_source} ({t:antigen_accession}); "
                        "el antígeno entra al diseño como un vector de "
                        "{t:antigen_feature_vector|count} rasgos.",
                        "en": "Context taken from {t:antigen_context_source} ({t:antigen_accession}); "
                        "the antigen enters the design as a vector of "
                        "{t:antigen_feature_vector|count} features.",
                    },
                },
                {
                    "es": "El PDB experimental del antígeno queda como «{t:pdb_id}» y los residuos de "
                    "epítopo como «{t:epitope_residues}»: la corrida no nombra ni un residuo concreto "
                    "de epítopo.",
                    "en": 'The antigen\'s experimental PDB stays as "{t:pdb_id}" and the epitope '
                    'residues as "{t:epitope_residues}": the run never names a single epitope '
                    "residue.",
                    "kind": "gap",
                },
                {
                    "es": "El contexto de TargetRadar llega de {t:targetradar_context.source} para "
                    "{t:targetradar_context.gene_symbol}, sin puntuación compuesta ni clase de "
                    "tratabilidad.",
                    "en": "The TargetRadar context arrives from {t:targetradar_context.source} for "
                    "{t:targetradar_context.gene_symbol}, with no composite score and no "
                    "tractability class.",
                    "kind": "gap",
                },
                {
                    "es": "La cadena de antígeno que se plegó tiene los {ag:length_aa} residuos de la "
                    "entrada completa, aunque la propia base de selección cite una característica de "
                    "señal y una de cadena madura: se modeló también el trozo que se corta al "
                    "secretarse la citoquina.",
                    "en": "The antigen chain that was folded holds all {ag:length_aa} residues of the "
                    "full entry, even though the run's own selection basis cites a signal feature and "
                    "a mature-chain feature: the piece cut off when the cytokine is secreted was "
                    "modelled too.",
                    "kind": "check",
                    "requires_failed_check": "antigen_mature",
                    "focus": {"color": "domains"},
                },
            ],
        },
        {
            "id": "framework",
            "title": {
                "es": "El armazón de la especie",
                "en": "The species-matched framework",
            },
            "claims": [S3, S4, "veterinary_framework", "framework_regions"],
            "scene": scene_framework(r),
            "beats": [
                {
                    "es": "El armazón variable se busca en {vf:host_species} (taxón {vf:taxon_id}): "
                    "VH {vf:selected_vh_germline} y VL {vf:selected_vl_germline}. Sobre esos dos "
                    "esqueletos se injertan las asas.",
                    "en": "The variable framework is sourced from {vf:host_species} (taxon "
                    "{vf:taxon_id}): VH {vf:selected_vh_germline} and VL {vf:selected_vl_germline}. "
                    "The loops are grafted onto those two scaffolds.",
                    "tech": {
                        "es": "{vf:source.database} {vf:source.accession}, consultado "
                        "{vf:source.queried_at}; {vf:source_summary.entry_count} entradas devueltas "
                        "por la consulta {vf:source_summary.query}.",
                        "en": "{vf:source.database} {vf:source.accession}, queried "
                        "{vf:source.queried_at}; {vf:source_summary.entry_count} entries returned by "
                        "the query {vf:source_summary.query}.",
                    },
                    "gap": [S3, "veterinary_framework"],
                    "gap_es": "Sin armazón resuelto",
                    "gap_en": "No framework resolved",
                },
                {
                    "es": "La corrida no afirma que sean germinales: {vf:germline_status}.",
                    "en": "The run does not claim these are germline: {vf:germline_status}.",
                    "kind": "note",
                },
                {
                    "es": "La numeración y los límites de CDR salen de {vf:numbering_method}; el "
                    "estado es {vf:verification_status} en modo {vf:resolution_mode}.",
                    "en": "Numbering and CDR boundaries come from {vf:numbering_method}; the status "
                    "is {vf:verification_status} in {vf:resolution_mode} mode.",
                    "tech": {
                        "es": "VH {vf:framework_evidence.vh.accession} "
                        "({vf:framework_evidence.vh.entry_type}) y VL "
                        "{vf:framework_evidence.vl.accession} ({vf:framework_evidence.vl.entry_type}).",
                        "en": "VH {vf:framework_evidence.vh.accession} "
                        "({vf:framework_evidence.vh.entry_type}) and VL "
                        "{vf:framework_evidence.vl.accession} ({vf:framework_evidence.vl.entry_type}).",
                    },
                },
                {
                    "es": "ANARCI asigna especie {vf:framework_evidence.vh.anarci_species} al VH y "
                    "{vf:framework_evidence.vl.anarci_species} al VL, de acuerdo con el huésped "
                    "declarado {vf:host_species}.",
                    "en": "ANARCI assigns species {vf:framework_evidence.vh.anarci_species} to the VH "
                    "and {vf:framework_evidence.vl.anarci_species} to the VL, agreeing with the "
                    "declared host {vf:host_species}.",
                    "kind": "check",
                    "requires_check": "framework_species",
                },
                {
                    "es": "Los dos campos de la corrida no dicen lo mismo: la entrada se anota como "
                    "organismo {vf:framework_evidence.vh.organism}, pero la especie que ANARCI le "
                    "asigna es {vf:framework_evidence.vh.anarci_species} (VH) y "
                    "{vf:framework_evidence.vl.anarci_species} (VL). Todo lo que se apoye en «armazón "
                    "de la especie» hereda esa duda.",
                    "en": "The run's own two fields disagree: the entry is recorded as organism "
                    "{vf:framework_evidence.vh.organism}, yet the species ANARCI assigns to it is "
                    "{vf:framework_evidence.vh.anarci_species} (VH) and "
                    "{vf:framework_evidence.vl.anarci_species} (VL). Anything resting on "
                    '"species-matched framework" inherits that doubt.',
                    "kind": "check",
                    "requires_failed_check": "framework_species",
                },
                {
                    "es": "Las regiones marco conservadas son {fr:vh|count} bloques en VH y "
                    "{fr:vl|count} en VL; entre ellos van las tres asas de cada dominio.",
                    "en": "The conserved framework regions are {fr:vh|count} blocks in the VH and "
                    "{fr:vl|count} in the VL; the three loops of each domain sit between them.",
                },
                {
                    "es": "La cola constante la aporta el isotipo {vf:constant_region_resolution.fc_isotype}: "
                    "{vf:constant_region_resolution.heavy.length_aa} aminoácidos de cadena pesada y "
                    "{vf:constant_region_resolution.light.length_aa} de ligera, cadena "
                    "{vf:constant_region_resolution.light.chain_type}. Es la parte que habla con el "
                    "sistema inmune del animal.",
                    "en": "The constant tail comes from the {vf:constant_region_resolution.fc_isotype} "
                    "isotype: {vf:constant_region_resolution.heavy.length_aa} amino acids of heavy "
                    "chain and {vf:constant_region_resolution.light.length_aa} of light, chain "
                    "{vf:constant_region_resolution.light.chain_type}. This is the part that talks to "
                    "the animal's immune system.",
                    "tech": {
                        "es": "{vf:constant_region_resolution.heavy.database} "
                        "{vf:constant_region_resolution.heavy.accession} "
                        "({vf:constant_region_resolution.heavy.source_url}) y "
                        "{vf:constant_region_resolution.light.accession}; sha256 "
                        "{vf:constant_region_resolution.heavy.constant_region_sha256}.",
                        "en": "{vf:constant_region_resolution.heavy.database} "
                        "{vf:constant_region_resolution.heavy.accession} "
                        "({vf:constant_region_resolution.heavy.source_url}) and "
                        "{vf:constant_region_resolution.light.accession}; sha256 "
                        "{vf:constant_region_resolution.heavy.constant_region_sha256}.",
                    },
                },
                {
                    "es": "Convención de la cadena madura: {vf:mature_chain_convention}. Estado: "
                    "{vf:full_length_status}.",
                    "en": "Mature-chain convention: {vf:mature_chain_convention}. Status: "
                    "{vf:full_length_status}.",
                    "kind": "note",
                },
                {
                    "es": "Comprobado aquí sobre las secuencias: la cadena pesada completa es el VH "
                    "diseñado seguido de esa cola constante, y la ligera lo mismo.",
                    "en": "Checked here against the sequences: the full heavy chain is the designed VH "
                    "followed by that constant tail, and the light chain likewise.",
                    "kind": "check",
                    "requires_check": "chain_assembly",
                },
                {
                    "es": "La compatibilidad con la especie no se puntúa ({cp:status}): {cp:reason} "
                    "Residuos de marco preservados: {cp:framework_residues_preserved}.",
                    "en": "Species compatibility is not scored ({cp:status}): {cp:reason} "
                    "Framework residues preserved: {cp:framework_residues_preserved}.",
                    "kind": "gap",
                },
                {
                    "es": "Nota del propio paso: {fw:note}",
                    "en": "The step's own note: {fw:note}",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "cdrs",
            "title": {"es": "Las asas que buscó el VQE", "en": "The loops the VQE searched"},
            "claims": [S2],
            "scene": scene_cdrs(r),
            "beats": [
                {
                    "es": "El diseño de asas corre como {cd:stage}: {cd:total_evaluated} secuencias "
                    "evaluadas con un VQE de {cd:n_qubits} cúbits, {cd:n_layers} capas y "
                    "{cd:shots} disparos.",
                    "en": "Loop design runs as {cd:stage}: {cd:total_evaluated} sequences evaluated "
                    "with a VQE of {cd:n_qubits} qubits, {cd:n_layers} layers and {cd:shots} shots.",
                    "focus": {"domains": True},
                    "tech": {
                        "es": "Trabajo {cd:execution_job_ids} en {qp:backend}; hardware real: "
                        "{qp:is_real_hardware}.",
                        "en": "Job {cd:execution_job_ids} on {qp:backend}; real hardware: "
                        "{qp:is_real_hardware}.",
                    },
                    "gap": [S2],
                    "gap_es": "Sin diseño de CDR",
                    "gap_en": "No CDR design",
                },
                {
                    "es": "Las cinco mejores CDR-H3 fueron {cd:top_cdr_h3_sequences}, con energías "
                    "{cd:vqe_energies} en {cd:energy_unit}.",
                    "en": "The five best CDR-H3 loops were {cd:top_cdr_h3_sequences}, with energies "
                    "{cd:vqe_energies} in {cd:energy_unit}.",
                    "focus": {"domains": True},
                },
                {
                    "es": "El asa que quedó en el líder es {L:cdr_h3}, de {L:cdr_h3_length} residuos: "
                    "la tercera del dominio pesado, la única cuya búsqueda documenta este paso.",
                    "en": "The loop the lead kept is {L:cdr_h3}, {L:cdr_h3_length} residues long: the "
                    "third loop of the heavy domain, and the only one whose search this step records.",
                    "focus": {"domains": True},
                },
                {
                    "es": "Las otras cinco asas del líder son H1 {L:cdr_h1}, H2 {L:cdr_h2}, "
                    "L1 {L:cdr_l1}, L2 {L:cdr_l2} y L3 {L:cdr_l3}.",
                    "en": "The lead's other five loops are H1 {L:cdr_h1}, H2 {L:cdr_h2}, "
                    "L1 {L:cdr_l1}, L2 {L:cdr_l2} and L3 {L:cdr_l3}.",
                    "focus": {"domains": True},
                },
                {
                    "es": "Las seis asas se comparan aquí con las del armazón de referencia y sólo la "
                    "CDR-H3 cambia: es la única que el paso documenta haber buscado.",
                    "en": "The six loops are compared here with the reference framework's own and only "
                    "the CDR-H3 differs: the only one this step documents searching for.",
                    "kind": "check",
                    "requires_check": "cdr_origin",
                },
                {
                    "es": "Comparadas aquí con el armazón de referencia, las seis asas del líder son "
                    "distintas, no sólo la CDR-H3; el paso {cd:stage} sólo registra la búsqueda de la "
                    "CDR-H3, así que de dónde salieron las otras cinco no está en la corrida.",
                    "en": "Compared here with the reference framework, all six of the lead's loops "
                    "differ, not only the CDR-H3; step {cd:stage} records only the CDR-H3 search, so "
                    "where the other five came from is not in this run.",
                    "kind": "check",
                    "requires_failed_check": "cdr_origin",
                },
                {
                    "es": "El paso se declara condicionado por la estructura "
                    "({cd:conditioned_on_structure}) y el PDB de referencia es {cd:pdb_id}: no hay "
                    "estructura de partida que lo condicione.",
                    "en": "The step declares itself structure-conditioned "
                    "({cd:conditioned_on_structure}) and the reference PDB is {cd:pdb_id}: there is no "
                    "starting structure to condition it.",
                    "kind": "check",
                    "requires_failed_check": "cdr_conditioning",
                },
                {
                    "es": "Comprobado aquí: las cuatro regiones marco y las tres asas, en ese orden, "
                    "reconstruyen exactamente el VH y el VL del líder.",
                    "en": "Checked here: the four framework regions and the three loops, in that "
                    "order, rebuild the lead's VH and VL exactly.",
                    "kind": "check",
                    "requires_check": "grafting",
                },
            ],
        },
        {
            "id": "candidates",
            "title": {"es": "Los cinco candidatos", "en": "The five candidates"},
            "claims": [
                S5,
                S6,
                S7,
                "candidates",
                LEAD,
                "best_candidate",
                "docking",
            ],
            "scene": scene_candidates(r),
            "beats": [
                {
                    "es": "La generación de candidatos termina en {gn:status} y arma "
                    "{gn:candidate_count} anticuerpos completos ({gn:candidate_ids}).",
                    "en": "Candidate generation ends at {gn:status} and assembles "
                    "{gn:candidate_count} complete antibodies ({gn:candidate_ids}).",
                },
                {
                    "es": "El líder es {L:candidate_id} (interno {L:core_candidate_id}), un par VH/VL "
                    "completo y no un VHH ({L:is_vhh}); su puntuación de humanización queda vacía, "
                    "que es lo correcto cuando el objetivo no es parecerse a un humano.",
                    "en": "The lead is {L:candidate_id} (internally {L:core_candidate_id}), a full "
                    "VH/VL pair and not a VHH ({L:is_vhh}); its humanisation score stays empty, which "
                    "is the right answer when looking human is not the goal.",
                },
                {
                    "es": "El barrido de responsabilidades ({dv:method}) encuentra "
                    "{L:developability.n_liabilities} en la CDR-H3 del líder: "
                    "{L:developability.liabilities[0].liability} en la posición "
                    "{L:developability.liabilities[0].positions_0based} del asa (base 0) y "
                    "{L:developability.liabilities[1].liability} en la "
                    "{L:developability.liabilities[1].positions_0based}.",
                    "en": "The liability scan ({dv:method}) finds "
                    "{L:developability.n_liabilities} in the lead's CDR-H3: "
                    "{L:developability.liabilities[0].liability} at loop position "
                    "{L:developability.liabilities[0].positions_0based} (0-based) and "
                    "{L:developability.liabilities[1].liability} at "
                    "{L:developability.liabilities[1].positions_0based}.",
                    "tech": {
                        "es": "{L:developability.developability_liabilities.method}; "
                        "{L:developability.provenance}. {L:developability.developability_liabilities.disclaimer}",
                        "en": "{L:developability.developability_liabilities.method}; "
                        "{L:developability.provenance}. {L:developability.developability_liabilities.disclaimer}",
                    },
                },
                {
                    "es": "Un sequón N-X-S/T dentro del asa puede llevar un azúcar que estorbe la "
                    "unión; una pareja Asp-Gly puede isomerizarse y cambiar la forma del asa con el "
                    "tiempo. Por eso se cuentan.",
                    "en": "An N-X-S/T sequon inside the loop can carry a sugar that gets in the way of "
                    "binding; an Asp-Gly pair can isomerise and reshape the loop over time. That is "
                    "why they are counted.",
                    "kind": "note",
                },
                {
                    "es": "De ahí sale la nota de desarrollabilidad "
                    "{L:developability.developability_score|n3}: "
                    "{L:developability.developability_score_basis}.",
                    "en": "That is where the developability score "
                    "{L:developability.developability_score|n3} comes from: "
                    "{L:developability.developability_score_basis}.",
                },
                {
                    "es": "La composición del asa: {L:developability.developability_liabilities.composition.length} "
                    "residuos, carga neta {L:developability.developability_liabilities.composition.net_charge_approx}, "
                    "pI {L:developability.developability_liabilities.composition.pI}, "
                    "{L:developability.developability_liabilities.composition.aromatic_ratio|pct} aromáticos y "
                    "{L:developability.developability_liabilities.composition.cysteine_count} cisteínas.",
                    "en": "The loop's composition: {L:developability.developability_liabilities.composition.length} "
                    "residues, net charge {L:developability.developability_liabilities.composition.net_charge_approx}, "
                    "pI {L:developability.developability_liabilities.composition.pI}, "
                    "{L:developability.developability_liabilities.composition.aromatic_ratio|pct} aromatic and "
                    "{L:developability.developability_liabilities.composition.cysteine_count} cysteines.",
                    "tech": {
                        "es": "Residuos oxidables en el asa: Trp {L:developability.developability_liabilities.oxidation_prone.trp_count}, "
                        "Met {L:developability.developability_liabilities.oxidation_prone.met_count}.",
                        "en": "Oxidation-prone residues in the loop: Trp {L:developability.developability_liabilities.oxidation_prone.trp_count}, "
                        "Met {L:developability.developability_liabilities.oxidation_prone.met_count}.",
                    },
                },
                {
                    "es": "El barrido mira sólo la CDR-H3, no el anticuerpo entero: las cisteínas que "
                    "otros candidatos meten en otras asas quedan fuera de su ventana.",
                    "en": "The scan looks only at the CDR-H3, not at the whole antibody: cysteines "
                    "that other candidates put into other loops fall outside its window.",
                    "kind": "check",
                    "requires_failed_check": "liability_scope",
                },
                {
                    "es": "Tres medidas se dejan vacías a propósito: agregación "
                    "({L:developability.aggregation_propensity.null_reason}), viscosidad "
                    "({L:developability.viscosity_150mgml.null_reason}) y Tm "
                    "({L:developability.thermal_stability_tm.null_reason}).",
                    "en": "Three measurements are deliberately left empty: aggregation "
                    "({L:developability.aggregation_propensity.null_reason}), viscosity "
                    "({L:developability.viscosity_150mgml.null_reason}) and Tm "
                    "({L:developability.thermal_stability_tm.null_reason}).",
                    "kind": "gap",
                },
                {
                    "es": "El ranking de unión ({bd:stage}) puntúa los cinco con un VQE de "
                    "{bd:n_qubits} cúbits: {bd:binding_energies}, en unidades "
                    "{bd:binding_energy_units}. Calibrado en kcal/mol: {bd:calibrated_kcal_mol}.",
                    "en": "The binding ranking ({bd:stage}) scores all five with a VQE of "
                    "{bd:n_qubits} qubits: {bd:binding_energies}, in {bd:binding_energy_units} "
                    "units. Calibrated in kcal/mol: {bd:calibrated_kcal_mol}.",
                    "tech": {
                        "es": "Trabajo {bd:execution_job_ids}; método {dk:method}.",
                        "en": "Job {bd:execution_job_ids}; method {dk:method}.",
                    },
                },
                {
                    "es": "Comprobado aquí: el puesto {L:scores.affinity_rank} que la corrida da al "
                    "líder es el que sale de ordenar esas energías.",
                    "en": "Checked here: the rank {L:scores.affinity_rank} the run gives the lead is "
                    "the one that falls out of sorting those energies.",
                    "kind": "check",
                    "requires_check": "affinity_rank",
                },
                {
                    "es": "El líder queda {L:scores.affinity_rank} en afinidad relativa con "
                    "{L:scores.binding_energy|n4} y su ipTM estructural es {L:scores.iptm|n4}: dos "
                    "señales distintas, una de secuencia y otra de estructura.",
                    "en": "The lead comes {L:scores.affinity_rank} in relative affinity with "
                    "{L:scores.binding_energy|n4} and its structural ipTM is {L:scores.iptm|n4}: two "
                    "different signals, one from sequence and one from structure.",
                    "tech": {
                        "es": "Base de la selección: {L:selection_basis}.",
                        "en": "Selection basis: {L:selection_basis}.",
                    },
                },
                {
                    "es": "No se publica una Kd del líder: {L:scores.kd_disclaimer}",
                    "en": "No Kd is published for the lead: {L:scores.kd_disclaimer}",
                    "kind": "gap",
                },
                {
                    "es": "Aun así el paso de ranking sí publica Kd en nanomolar "
                    "({bd:kd_estimates_nm}) mientras el candidato dice "
                    "{dk:kd_nM_honest.null_reason} Son la misma cantidad contada dos veces.",
                    "en": "Even so the ranking step does publish Kd values in nanomolar "
                    "({bd:kd_estimates_nm}) while the candidate itself says "
                    "{dk:kd_nM_honest.null_reason} They are the same quantity told twice.",
                    "kind": "check",
                    "requires_failed_check": "kd_silence",
                },
                {
                    "es": "La energía libre de unión tampoco está: {dk:binding_affinity_kcal_honest.null_reason} "
                    "Confirmación experimental requerida: {dk:experimental_confirmation_required}.",
                    "en": "The binding free energy is missing too: {dk:binding_affinity_kcal_honest.null_reason} "
                    "Experimental confirmation required: {dk:experimental_confirmation_required}.",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "structure",
            "title": {"es": "El complejo plegado", "en": "The folded complex"},
            "claims": [
                S9,
                "structure_3d",
                "complex_structure_3d",
                "protenix_structure",
                "quantum_analyses.chai1_structure",
                f"{LEAD}.protenix_structure",
                f"{LEAD}.analyses.chai1_structure",
                f"{LEAD}.analyses.protenix_structure",
                "best_candidate.protenix_structure",
                "best_candidate.analyses.chai1_structure",
                "best_candidate.analyses.protenix_structure",
            ],
            "scene": scene_structure(r, cx, meshes),
            "beats": [
                {
                    "es": "{sp:method} predice la estructura de los {sp:predictions|count} candidatos "
                    "con {sp:model_requested} en GPU {sp:gpu}.",
                    "en": "{sp:method} predicts the structure of all {sp:predictions|count} candidates "
                    "with {sp:model_requested} on {sp:gpu} GPU.",
                    "focus": {"grow": True},
                    "gap": [S9, "structure_3d"],
                    "gap_es": "Sin predicción de estructura",
                    "gap_en": "No structure prediction",
                },
                {
                    "es": "Para el líder: pLDDT {px:plddt|n2} sobre 100, pTM {px:ptm|n4}, ipTM "
                    "{px:iptm|n4} y ranking {px:ranking_score|n4}. El ipTM es la confianza en la "
                    "interfaz, es decir en que las dos piezas se toquen como el modelo dice.",
                    "en": "For the lead: pLDDT {px:plddt|n2} out of 100, pTM {px:ptm|n4}, ipTM "
                    "{px:iptm|n4} and ranking {px:ranking_score|n4}. The ipTM is confidence in the "
                    "interface, that is, in the two pieces touching the way the model says.",
                    "focus": {},
                    "tech": {
                        "es": "{px:model_used}, GPU {px:gpu}, trabajo {px:job_id}, estado {px:status}.",
                        "en": "{px:model_used}, {px:gpu} GPU, job {px:job_id}, status {px:status}.",
                    },
                },
                {
                    "es": "Lo que se dibuja es otra predicción: {st:method} pliega el complejo entero "
                    "({q:chai1_structure.n_residues} residuos, cadenas {q:chai1_structure.chains_folded}) "
                    "con coordenadas reales ({q:chai1_structure.has_real_coordinates}).",
                    "en": "What is drawn is a different prediction: {st:method} folds the whole complex "
                    "({q:chai1_structure.n_residues} residues, chains {q:chai1_structure.chains_folded}) "
                    "with real coordinates ({q:chai1_structure.has_real_coordinates}).",
                    "requires_mesh": "complex",
                    "focus": {"color": "domains"},
                    "tech": {
                        "es": "Modelo {q:chai1_structure.model}, puntuación agregada "
                        "{q:chai1_structure.aggregate_score|n4}, candidato {q:chai1_structure.candidate_id}.",
                        "en": "Model {q:chai1_structure.model}, aggregate score "
                        "{q:chai1_structure.aggregate_score|n4}, candidate {q:chai1_structure.candidate_id}.",
                    },
                },
                {
                    "es": "Las coordenadas que ves vienen de {st:method} y el pLDDT {px:plddt|n2} de "
                    "{sp:method}: son dos modelos distintos del mismo complejo, y el dibujado no trae "
                    "pLDDT propio en la corrida.",
                    "en": "The coordinates you see come from {st:method} and the pLDDT {px:plddt|n2} "
                    "from {sp:method}: two different models of the same complex, and the drawn one "
                    "carries no pLDDT of its own in the run.",
                    "kind": "check",
                    "requires_failed_check": "drawn_confidence",
                    "focus": {"color": "plddt"},
                },
                {
                    "es": "Comprobado aquí: el complejo plegado tiene exactamente VH + VL + antígeno "
                    "residuos, en tres cadenas con esas longitudes.",
                    "en": "Checked here: the folded complex holds exactly VH + VL + antigen residues, "
                    "in three chains of those lengths.",
                    "kind": "check",
                    "requires_check": "complex_composition",
                    "focus": {"color": "domains"},
                },
                {
                    "es": "Medido aquí sobre esas coordenadas: la CDR-H3 llega a tocar el antígeno. La "
                    "corrida no nombra ningún residuo de epítopo, así que esta es la única interfaz "
                    "que puede señalarse, y sale del modelo, no de un experimento.",
                    "en": "Measured here on those coordinates: the CDR-H3 does reach the antigen. The "
                    "run names no epitope residue, so this is the only interface that can be pointed "
                    "at, and it comes from the model, not from an experiment.",
                    "kind": "check",
                    "requires_check": "interface",
                },
                {
                    "es": "En la escena, la línea discontinua mide esa distancia al residuo más "
                    "cercano del antígeno.",
                    "en": "In the scene, the dashed line measures that distance to the closest antigen "
                    "residue.",
                    "kind": "note",
                    "requires_check": "interface",
                    "requires_mesh": "complex",
                },
                {
                    "es": "El complejo es una predicción, no una estructura experimental: {cx:note} "
                    "Receptor {cx:receptor}, cadenas {cx:chains}.",
                    "en": "The complex is a prediction, not an experimental structure: {cx:note} "
                    "Receptor {cx:receptor}, chains {cx:chains}.",
                    "kind": "note",
                },
                {
                    "es": "La confianza de interfaz guardada con el complejo es {cx:iptm}.",
                    "en": "The interface confidence stored with the complex is {cx:iptm}.",
                    "gap": ["complex_structure_3d"],
                    "gap_es": "El complejo dibujado no guarda ipTM propio",
                    "gap_en": "The drawn complex stores no ipTM of its own",
                },
            ],
        },
        {
            "id": "immunogenicity",
            "title": {
                "es": "Lo que no se puede medir en esta especie",
                "en": "What cannot be measured in this species",
            },
            "claims": [
                S8,
                "species_immunogenicity",
                "immunogenicity",
                "deimmunization",
                "toxicology",
                f"{LEAD}.toxicology",
                "best_candidate.toxicology",
            ],
            "scene": {"type": "panel", "root": "species_immunogenicity"},
            "beats": [
                {
                    "es": "La inmunogenicidad en esta especie no se calculó ({si:status}) para "
                    "ninguno de los {si:candidate_ids|count} candidatos.",
                    "en": "Immunogenicity in this species was not computed ({si:status}) for any of "
                    "the {si:candidate_ids|count} candidates.",
                },
                {
                    "es": "La razón, en palabras del pipeline: {si:reason}",
                    "en": "The reason, in the pipeline's own words: {si:reason}",
                    "kind": "gap",
                },
                {
                    "es": "Esa negativa es la decisión veterinaria más importante de la corrida: un "
                    "modelo de MHC humano aplicado a un perro daría un número, y ese número no "
                    "significaría nada.",
                    "en": "That refusal is the most consequential veterinary decision in the run: a "
                    "human MHC model pointed at a dog would return a number, and the number would "
                    "mean nothing.",
                    "kind": "note",
                },
                {
                    "es": "Lo que haría falta: {si:required_validation}.",
                    "en": "What it would take: {si:required_validation}.",
                    "kind": "gap",
                },
                {
                    "es": "Por lo mismo no se de-inmunizó nada ({di:status}, disponible "
                    "{di:available}): {di:reason} Requiere {di:required_input}.",
                    "en": "For the same reason nothing was de-immunised ({di:status}, available "
                    "{di:available}): {di:reason} It needs {di:required_input}.",
                    "kind": "gap",
                },
                {
                    "es": "Sin ese modelo, el riesgo de anticuerpos anti-fármaco queda cualitativo: "
                    "nivel {tx:ada_risk.level}, medido {tx:ada_risk.is_measured}, cualitativo "
                    "{tx:ada_risk.is_qualitative}.",
                    "en": "Without that model, the anti-drug-antibody risk stays qualitative: level "
                    "{tx:ada_risk.level}, measured {tx:ada_risk.is_measured}, qualitative "
                    "{tx:ada_risk.is_qualitative}.",
                    "tech": {
                        "es": "Base: {tx:ada_risk.basis}",
                        "en": "Basis: {tx:ada_risk.basis}",
                    },
                },
                {
                    "es": "Ese «bajo» se apoya en que el armazón sea de la especie; la evidencia "
                    "ANARCI de esta misma corrida dice {vf:framework_evidence.vh.anarci_species}, así "
                    "que el argumento no se sostiene solo.",
                    "en": 'That "low" rests on the framework being the species\' own; the ANARCI '
                    "evidence in this same run says {vf:framework_evidence.vh.anarci_species}, so the "
                    "argument does not stand on its own.",
                    "kind": "check",
                    "requires_failed_check": "framework_species",
                },
                {
                    "es": "La incidencia de ADA que se cita, {tx:ada_risk.published_cohort_incidence_pct.value}% "
                    "(IC90 {tx:ada_risk.published_cohort_incidence_pct.ci90}), es de una cohorte "
                    "publicada, no de esta molécula: {tx:ada_risk.published_cohort_incidence_pct.character}.",
                    "en": "The ADA incidence quoted, {tx:ada_risk.published_cohort_incidence_pct.value}% "
                    "(90% CI {tx:ada_risk.published_cohort_incidence_pct.ci90}), is from a published "
                    "cohort, not from this molecule: {tx:ada_risk.published_cohort_incidence_pct.character}.",
                    "tech": {
                        "es": "{tx:ada_risk.published_cohort_incidence_pct.method}; específico de la "
                        "molécula: {tx:ada_risk.published_cohort_incidence_pct.molecule_specific}.",
                        "en": "{tx:ada_risk.published_cohort_incidence_pct.method}; molecule-specific: "
                        "{tx:ada_risk.published_cohort_incidence_pct.molecule_specific}.",
                    },
                },
                {
                    "es": "Liberación de citoquinas {tx:cytokine_release_risk.level}: "
                    "{tx:cytokine_release_risk.basis}",
                    "en": "Cytokine release {tx:cytokine_release_risk.level}: "
                    "{tx:cytokine_release_risk.basis}",
                },
                {
                    "es": "Reacción a la infusión {tx:infusion_reaction_risk.level}: "
                    "{tx:infusion_reaction_risk.basis}",
                    "en": "Infusion reaction {tx:infusion_reaction_risk.level}: "
                    "{tx:infusion_reaction_risk.basis}",
                },
                {
                    "es": "Toxicidad sobre la propia diana: {tx:on_target_toxicity}.",
                    "en": "On-target toxicity: {tx:on_target_toxicity}.",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "pk",
            "title": {
                "es": "Farmacocinética prestada",
                "en": "Borrowed pharmacokinetics",
            },
            "claims": [
                S10,
                "admet",
                "pharmacology",
                "veterinary_product_profile",
                f"{LEAD}.admet",
                f"{LEAD}.pharmacology",
                f"{LEAD}.analyses.admet",
                f"{LEAD}.analyses.pharmacology",
                f"{LEAD}.analyses.toxicology",
                f"{LEAD}.analyses.docking",
                "best_candidate.admet",
                "best_candidate.pharmacology",
                "best_candidate.analyses.admet",
                "best_candidate.analyses.pharmacology",
                "best_candidate.analyses.toxicology",
                "best_candidate.analyses.docking",
            ],
            "scene": scene_pk(r),
            "beats": [
                {
                    "es": "La PK no se predice molécula a molécula: es un prior de clase publicado "
                    "({ad:pk_prior.status}) para {ad:pk_prior.applies_to} en {ad:pk_prior.species_label}.",
                    "en": "PK is not predicted molecule by molecule: it is a published class prior "
                    "({ad:pk_prior.status}) for {ad:pk_prior.applies_to} in {ad:pk_prior.species_label}.",
                    "tech": {
                        "es": "{ad:pk_prior.grounding}",
                        "en": "{ad:pk_prior.grounding}",
                    },
                },
                {
                    "es": "Semivida {ad:excretion.half_life_days.value} días (IC90 "
                    "{ad:excretion.half_life_days.ci90}), aclaramiento "
                    "{ad:metabolism.clearance_ml_day_kg.value} mL/día/kg y volumen central "
                    "{ad:distribution.vd_ml_kg.value} mL/kg: un anticuerpo se recicla por FcRn y se "
                    "degrada como proteína, no por el hígado.",
                    "en": "Half-life {ad:excretion.half_life_days.value} days (90% CI "
                    "{ad:excretion.half_life_days.ci90}), clearance "
                    "{ad:metabolism.clearance_ml_day_kg.value} mL/day/kg and central volume "
                    "{ad:distribution.vd_ml_kg.value} mL/kg: an antibody is recycled by FcRn and "
                    "broken down as protein, not by the liver.",
                    "tech": {
                        "es": "{ad:excretion.half_life_days.method}; medido: "
                        "{ad:excretion.half_life_days.is_measured}; específico de la molécula: "
                        "{ad:excretion.half_life_days.molecule_specific}; degradación proteolítica: "
                        "{ad:metabolism.proteolytic_degradation}; sin CYP450: "
                        "{ad:metabolism.no_cyp450_metabolism}.",
                        "en": "{ad:excretion.half_life_days.method}; measured: "
                        "{ad:excretion.half_life_days.is_measured}; molecule-specific: "
                        "{ad:excretion.half_life_days.molecule_specific}; proteolytic degradation: "
                        "{ad:metabolism.proteolytic_degradation}; no CYP450: "
                        "{ad:metabolism.no_cyp450_metabolism}.",
                    },
                },
                {
                    "es": "Por vía subcutánea llega {ad:absorption.sc_bioavailability_pct.value}% "
                    "(IC90 {ad:absorption.sc_bioavailability_pct.ci90}) con pico a "
                    "{ad:absorption.tmax_sc_days.value} días; por vía oral, "
                    "{ad:absorption.oral_bioavailability}.",
                    "en": "Subcutaneously {ad:absorption.sc_bioavailability_pct.value}% "
                    "(90% CI {ad:absorption.sc_bioavailability_pct.ci90}) arrives, peaking at "
                    "{ad:absorption.tmax_sc_days.value} days; orally, "
                    "{ad:absorption.oral_bioavailability}.",
                    "tech": {
                        "es": "{ad:absorption.sc_bioavailability_pct.disclaimer}",
                        "en": "{ad:absorption.sc_bioavailability_pct.disclaimer}",
                    },
                },
                {
                    "es": "Los anclajes del prior son productos veterinarios reales: "
                    "{ad:pk_prior.sources}",
                    "en": "The prior is anchored on real veterinary products: {ad:pk_prior.sources}",
                    "kind": "note",
                },
                {
                    "es": "La masa con la que se elige ese perfil, {ad:molecular_weight_kda} kDa, "
                    "cuenta sólo los dominios variables; las cadenas maduras completas que la propia "
                    "corrida exporta son bastante más largas, y de la masa depende cómo se clasifica "
                    "el producto.",
                    "en": "The mass that profile is chosen by, {ad:molecular_weight_kda} kDa, counts "
                    "only the variable domains; the full mature chains the run itself exports are "
                    "considerably longer, and the mass is what the product gets classed by.",
                    "kind": "check",
                    "requires_failed_check": "mass_scope",
                    "tech": {
                        "es": "Base declarada de la masa: {ad:molecular_weight_basis}.",
                        "en": "Declared basis for the mass: {ad:molecular_weight_basis}.",
                    },
                },
                {
                    "es": "El perfil de clase de formato queda vacío: "
                    "{ad:reference_format_class_profile.absorption.sc_bioavailability_pct.null_reason}. "
                    "Y ese perfil es {ad:reference_profile_status}.",
                    "en": "The format-class profile comes back empty: "
                    "{ad:reference_format_class_profile.absorption.sc_bioavailability_pct.null_reason}. "
                    "And that profile is {ad:reference_profile_status}.",
                    "kind": "gap",
                },
                {
                    "es": "La traducción a la especie sigue sin validar ({ad:species_translation_status}): "
                    "{pkst:species_translation_note}",
                    "en": "Translation to the species is still unvalidated "
                    "({ad:species_translation_status}): {pkst:species_translation_note}",
                    "kind": "gap",
                },
                {
                    "es": "El mecanismo propuesto es {ph:mechanism}; el estado de la farmacología es "
                    "{ph:status}.",
                    "en": "The proposed mechanism is {ph:mechanism}; pharmacology status is "
                    "{ph:status}.",
                },
                {
                    "es": "La farmacodinámica no tiene ni un número: compromiso de diana "
                    "({ph:pharmacodynamics.target_engagement.null_reason}) y eficacia "
                    "({ph:pharmacodynamics.efficacy.null_reason}).",
                    "en": "Pharmacodynamics has not a single number: target engagement "
                    "({ph:pharmacodynamics.target_engagement.null_reason}) and efficacy "
                    "({ph:pharmacodynamics.efficacy.null_reason}).",
                    "kind": "gap",
                },
                {
                    "es": "El perfil de producto fija formato {tpp:antibody_format} e isotipo "
                    "{tpp:fc_isotype}, y deja sin definir indicación, vía, forma farmacéutica, "
                    "concentración, intervalo, almacenamiento y hospedador de producción.",
                    "en": "The product profile fixes the {tpp:antibody_format} format and the "
                    "{tpp:fc_isotype} isotype, and leaves indication, route, dosage form, "
                    "concentration, interval, storage and manufacturing host undefined.",
                    "kind": "gap",
                },
                {
                    "es": "La dosis es {tpp:dose_status} y hay {tpp:dose_calculations|count} cálculos "
                    "de dosis: {tpp:dose_note}",
                    "en": "The dose is {tpp:dose_status} and there are "
                    "{tpp:dose_calculations|count} dose calculations: {tpp:dose_note}",
                    "kind": "gap",
                },
                {
                    "es": "El paso veterinario de PK cierra como {pkst:status}.",
                    "en": "The veterinary PK step closes as {pkst:status}.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "quantum",
            "title": {"es": "Qué hizo la parte cuántica", "en": "What the quantum part did"},
            "claims": [
                "quantum_analyses",
                "quantum_contribution",
                "quantum_provenance",
                "execution_mode",
                "quantum_backend",
                "quantum_hardware",
                "on_real_quantum_hardware",
                "ibm_job_ids",
                "simulator_job_ids",
                "fallback_count",
                "iterations",
                "nmr_spectrum",
                f"{LEAD}.vqe_energy",
                f"{LEAD}.analyses.quantum_real_hamiltonian",
                f"{LEAD}.analyses.ewf_sqd",
                f"{LEAD}.analyses.quantum_sequence_state",
                f"{LEAD}.analyses.binding_free_energy_mmgbsa",
                "best_candidate.vqe_energy",
                "best_candidate.analyses.quantum_real_hamiltonian",
                "best_candidate.analyses.ewf_sqd",
                "best_candidate.analyses.quantum_sequence_state",
                "best_candidate.analyses.binding_free_energy_mmgbsa",
            ],
            "scene": scene_quantum(r),
            "beats": [
                {
                    "es": "El plegado se plantea como un problema de energía: "
                    "{q:quantum_real_hamiltonian.n_residues} residuos y "
                    "{q:quantum_real_hamiltonian.n_contacts} contactos se vuelven "
                    "{q:quantum_real_hamiltonian.n_qubits} cúbits y "
                    "{q:quantum_real_hamiltonian.n_terms} términos.",
                    "en": "Folding is cast as an energy problem: "
                    "{q:quantum_real_hamiltonian.n_residues} residues and "
                    "{q:quantum_real_hamiltonian.n_contacts} contacts become "
                    "{q:quantum_real_hamiltonian.n_qubits} qubits and "
                    "{q:quantum_real_hamiltonian.n_terms} terms.",
                    "focus": {"register": True},
                    "tech": {
                        "es": "Hamiltoniano: {q:quantum_real_hamiltonian.hamiltonian_source}; "
                        "modalidad {q:quantum_real_hamiltonian.modality}.",
                        "en": "Hamiltonian: {q:quantum_real_hamiltonian.hamiltonian_source}; "
                        "modality {q:quantum_real_hamiltonian.modality}.",
                    },
                    "gap": ["quantum_analyses"],
                    "gap_es": "Sin paso cuántico",
                    "gap_en": "No quantum step",
                },
                {
                    "es": "Energía variacional {q:quantum_real_hamiltonian.vqe_energy_Ha|n4} Ha frente "
                    "a {q:quantum_real_hamiltonian.reference_energy_Ha|n4} Ha, que es "
                    "{q:quantum_real_hamiltonian.reference_kind}.",
                    "en": "Variational energy {q:quantum_real_hamiltonian.vqe_energy_Ha|n4} Ha against "
                    "{q:quantum_real_hamiltonian.reference_energy_Ha|n4} Ha, which is "
                    "{q:quantum_real_hamiltonian.reference_kind}.",
                    "focus": {"energy": True},
                },
                {
                    "es": "Comprobado aquí: la energía variacional se queda por encima del estado "
                    "fundamental exacto, como debe ser, y la corrida lo marca como "
                    "{q:quantum_real_hamiltonian.variational_ok}.",
                    "en": "Checked here: the variational energy stays above the exact ground state, as "
                    "it must, and the run marks it {q:quantum_real_hamiltonian.variational_ok}.",
                    "kind": "check",
                    "requires_check": "variational",
                },
                {
                    "es": "Dónde corrió: {qp:backend}, modo {qp:execution_mode}, hardware cuántico "
                    "real: {qp:is_real_hardware}. Trabajos del motor: {qp:all_engine_job_ids}; "
                    "trabajos IBM: {ibm_job_ids|count}; reintentos de respaldo: {fallback_count}.",
                    "en": "Where it ran: {qp:backend}, mode {qp:execution_mode}, real quantum "
                    "hardware: {qp:is_real_hardware}. Engine jobs: {qp:all_engine_job_ids}; IBM jobs: "
                    "{ibm_job_ids|count}; fallbacks: {fallback_count}.",
                    "kind": "note",
                    "tech": {
                        "es": "{q:quantum_real_hamiltonian.resolved_plan.resolve_reason} "
                        "{q:quantum_real_hamiltonian.quantum_provenance.hardware_note}",
                        "en": "{q:quantum_real_hamiltonian.resolved_plan.resolve_reason} "
                        "{q:quantum_real_hamiltonian.quantum_provenance.hardware_note}",
                    },
                },
                {
                    "es": "La secuencia entera se carga además en un estado cuántico: "
                    "{q:quantum_sequence_state.n_residues} residuos en "
                    "{q:quantum_sequence_state.n_qubits} cúbits con codificación "
                    "{q:quantum_sequence_state.encoding}, y se recupera sin pérdida "
                    "({q:quantum_sequence_state.recovered_ok}).",
                    "en": "The whole sequence is also loaded into a quantum state: "
                    "{q:quantum_sequence_state.n_residues} residues on "
                    "{q:quantum_sequence_state.n_qubits} qubits with "
                    "{q:quantum_sequence_state.encoding} encoding, read back without loss "
                    "({q:quantum_sequence_state.recovered_ok}).",
                    "requires_check": "qubit_encoding",
                    "tech": {
                        "es": "Backend {q:quantum_sequence_state.backend}, alfabeto "
                        "{q:quantum_sequence_state.alphabet}.",
                        "en": "Backend {q:quantum_sequence_state.backend}, alphabet "
                        "{q:quantum_sequence_state.alphabet}.",
                    },
                },
                {
                    "es": "Y un cálculo de química cuántica embebida sobre el sitio activo: "
                    "{q:ewf_sqd.n_atoms} átomos y {q:ewf_sqd.n_orbitals_total} orbitales, energía "
                    "Hartree-Fock {q:ewf_sqd.hf_energy_Ha|n4} Ha y embebida "
                    "{q:ewf_sqd.ewf_embedding_energy_Ha|n4} Ha; {q:ewf_sqd.quantum_hard_fragments} de "
                    "{q:ewf_sqd.n_fragments} fragmentos caen en el régimen difícil.",
                    "en": "And an embedded quantum-chemistry calculation on the active site: "
                    "{q:ewf_sqd.n_atoms} atoms and {q:ewf_sqd.n_orbitals_total} orbitals, "
                    "Hartree-Fock energy {q:ewf_sqd.hf_energy_Ha|n4} Ha and embedded "
                    "{q:ewf_sqd.ewf_embedding_energy_Ha|n4} Ha; {q:ewf_sqd.quantum_hard_fragments} of "
                    "{q:ewf_sqd.n_fragments} fragments fall in the hard regime.",
                    "requires_check": "ewf_energy",
                    "tech": {
                        "es": "{q:ewf_sqd.method}; {q:ewf_sqd.note}; región: {q:ewf_sqd.region_prep}; "
                        "{q:ewf_sqd.time_s} s.",
                        "en": "{q:ewf_sqd.method}; {q:ewf_sqd.note}; region: {q:ewf_sqd.region_prep}; "
                        "{q:ewf_sqd.time_s} s.",
                    },
                },
                {
                    "es": "El sitio activo de ese cálculo es {q:ewf_sqd.active_region_residues} "
                    "residuo tomado por {q:ewf_sqd.active_site_seed}: es química de un punto del "
                    "complejo, no del anticuerpo entero.",
                    "en": "The active site of that calculation is {q:ewf_sqd.active_region_residues} "
                    "residue picked by {q:ewf_sqd.active_site_seed}: chemistry of one point of the "
                    "complex, not of the whole antibody.",
                    "kind": "note",
                },
                {
                    "es": "MM-GBSA no se pidió: "
                    "{q:binding_free_energy_mmgbsa.binding_affinity_kcal_honest.null_reason}",
                    "en": "MM-GBSA was not requested: "
                    "{q:binding_free_energy_mmgbsa.binding_affinity_kcal_honest.null_reason}",
                    "kind": "gap",
                },
                {
                    "es": "La fracción cuántica medida de esta corrida es {qc:measured_quantum_pct}%: "
                    "{qc:quantum_step_count} de {qc:eligible_step_count} pasos elegibles "
                    "({qc:quantum_steps}), frente a una meta permanente de {qc:standing_goal_pct}%.",
                    "en": "The measured quantum fraction of this run is {qc:measured_quantum_pct}%: "
                    "{qc:quantum_step_count} of {qc:eligible_step_count} eligible steps "
                    "({qc:quantum_steps}), against a standing goal of {qc:standing_goal_pct}%.",
                    "requires_check": "quantum_fraction",
                    "tech": {
                        "es": "{qc:measurement_basis} Paso clásico: {qc:ml_steps}.",
                        "en": "{qc:measurement_basis} Classical step: {qc:ml_steps}.",
                    },
                },
            ]
            + ledger_beats(r)
            + [
                {
                    "es": "{qc:honest_note}",
                    "en": "{qc:honest_note}",
                    "kind": "note",
                },
                {
                    "es": "El espectro de 1H se calcula ab initio ({nmr:method}) sobre "
                    "{nmr:n_residues_scored} residuos y da {nmr:spectrum_1h.n_peaks} picos a "
                    "{nmr:spectrum_1h.spectrometer_mhz} MHz. No es una medida ({nmr:is_measured}).",
                    "en": "The 1H spectrum is computed ab initio ({nmr:method}) over "
                    "{nmr:n_residues_scored} residues and gives {nmr:spectrum_1h.n_peaks} peaks at "
                    "{nmr:spectrum_1h.spectrometer_mhz} MHz. It is not a measurement "
                    "({nmr:is_measured}).",
                    "tech": {
                        "es": "{nmr:note} Validación: {nmr:validated}.",
                        "en": "{nmr:note} Validation: {nmr:validated}.",
                    },
                },
                {
                    "es": "Una sola pasada de diseño ({it:mode}, {it:n_iterations}); la convergencia "
                    "no se declara ({it:convergence_status}): {it:reason}",
                    "en": "A single design pass ({it:mode}, {it:n_iterations}); convergence is not "
                    "declared ({it:convergence_status}): {it:reason}",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "development",
            "title": {
                "es": "Lo que todavía habría que hacer",
                "en": "What would still have to be done",
            },
            "claims": [S11, S12, "development_plan", "clinical_trial", "report"],
            "scene": scene_development(r),
            "beats": [
                {
                    "es": "La selección final es {sel:lead_candidate_id} por {sel:ranking_method}; "
                    "confirmación experimental requerida: {sel:experimental_confirmation_required}.",
                    "en": "The final pick is {sel:lead_candidate_id} by {sel:ranking_method}; "
                    "experimental confirmation required: {sel:experimental_confirmation_required}.",
                },
                {
                    "es": "Comprobado aquí sobre los candidatos: bajo la regla que la corrida declara "
                    "para esta selección, ninguno le gana al elegido.",
                    "en": "Checked here across the candidates: under the rule the run declares for "
                    "this selection, none of them beats the one chosen.",
                    "kind": "check",
                    "requires_check": "lead_selection",
                },
                {
                    "es": "Recalculada esa misma regla sobre los mismos números, el candidato que gana "
                    "no es el que la corrida nombra líder.",
                    "en": "Recomputing that same rule on the same numbers, the candidate that wins is "
                    "not the one the run names as lead.",
                    "kind": "check",
                    "requires_failed_check": "lead_selection",
                },
                {
                    "es": "La corrida describe su selección de dos maneras que no son la misma regla: "
                    "{sel:ranking_method}, y «{L:selection_basis[0]}». Recalculadas aquí, cada una "
                    "elige un candidato distinto.",
                    "en": "The run describes its selection in two ways that are not the same rule: "
                    '{sel:ranking_method}, and "{L:selection_basis[0]}". Recomputed here, each one '
                    "picks a different candidate.",
                    "kind": "check",
                    "requires_failed_check": "selection_rule",
                },
                {
                    "es": "El paquete de desarrollo ({wp:status}) lista {dp:work_packages|count} "
                    "bloques de trabajo, que son estudios pendientes y no resultados: {dp:note}",
                    "en": "The development package ({wp:status}) lists {dp:work_packages|count} work "
                    "blocks, which are pending studies and not results: {dp:note}",
                },
            ]
            + work_package_beats(r)
            + [
                {
                    "es": "Lo que bloquea todo lo demás: {dp:blocking_gap}",
                    "en": "What blocks everything else: {dp:blocking_gap}",
                    "kind": "gap",
                },
                {
                    "es": "El desarrollo clínico está en {ct:status}, tipo {ct:study_type}, para "
                    "{ct:species.label}.",
                    "en": "Clinical development sits at {ct:status}, type {ct:study_type}, for "
                    "{ct:species.label}.",
                },
                {
                    "es": "Las probabilidades por fase son priores de cohorte, no simulaciones: "
                    "fase 1 a 2 {ct:ptrs_cohort_prior.phase_1_to_2.value} "
                    "(base humana {ct:ptrs_cohort_prior.phase_1_to_2.human_base_rate} × factor "
                    "veterinario {ct:ptrs_cohort_prior.phase_1_to_2.veterinary_uplift}), "
                    "2 a 3 {ct:ptrs_cohort_prior.phase_2_to_3.value}, "
                    "3 a aprobación {ct:ptrs_cohort_prior.phase_3_to_approval.value}.",
                    "en": "The per-phase probabilities are cohort priors, not simulations: "
                    "phase 1 to 2 {ct:ptrs_cohort_prior.phase_1_to_2.value} "
                    "(human base rate {ct:ptrs_cohort_prior.phase_1_to_2.human_base_rate} × "
                    "veterinary uplift {ct:ptrs_cohort_prior.phase_1_to_2.veterinary_uplift}), "
                    "2 to 3 {ct:ptrs_cohort_prior.phase_2_to_3.value}, "
                    "3 to approval {ct:ptrs_cohort_prior.phase_3_to_approval.value}.",
                    "focus": {"group": "phase"},
                    "tech": {
                        "es": "{ct:ptrs_cohort_prior.phase_1_to_2.method}. Fuentes: "
                        "{ct:ptrs_cohort_prior.sources}",
                        "en": "{ct:ptrs_cohort_prior.phase_1_to_2.method}. Sources: "
                        "{ct:ptrs_cohort_prior.sources}",
                    },
                },
                {
                    "es": "Comprobado aquí: cada probabilidad por fase es su base humana por su factor "
                    "veterinario, y el producto de las tres es la acumulada que se publica.",
                    "en": "Checked here: each phase probability is its human base rate times its "
                    "veterinary uplift, and the product of the three is the published cumulative.",
                    "kind": "check",
                    "requires_check": "ptrs_product",
                    "focus": {"group": "cumulative"},
                },
                {
                    "es": "Acumulada hasta aprobación {ct:development_summary.approval_probability.value} "
                    "(IC90 {ct:development_summary.approval_probability.ci90}), por "
                    "{ct:development_summary.approval_probability.method}; específico de la molécula: "
                    "{ct:development_summary.approval_probability.molecule_specific}.",
                    "en": "Cumulative to approval {ct:development_summary.approval_probability.value} "
                    "(90% CI {ct:development_summary.approval_probability.ci90}), by "
                    "{ct:development_summary.approval_probability.method}; molecule-specific: "
                    "{ct:development_summary.approval_probability.molecule_specific}.",
                    "focus": {"group": "cumulative"},
                },
                {
                    "es": "Ni la eficacia ni la seguridad reciben probabilidad propia, y las tres fases "
                    "están en {ct:phase_1.status}: {ct:note}",
                    "en": "Neither efficacy nor safety gets its own probability, and all three phases "
                    "sit at {ct:phase_1.status}: {ct:note}",
                    "kind": "gap",
                },
                {
                    "es": "El contexto del desarrollo animal: {ct:ptrs_cohort_prior.development_context.total_years.value} "
                    "años de candidato a aprobación y "
                    "{ct:ptrs_cohort_prior.development_context.investment_usd_millions.value} millones "
                    "de USD, {ct:ptrs_cohort_prior.development_context.investment_usd_millions.note}.",
                    "en": "The animal-development context: "
                    "{ct:ptrs_cohort_prior.development_context.total_years.value} years from candidate "
                    "to approval and "
                    "{ct:ptrs_cohort_prior.development_context.investment_usd_millions.value} million "
                    "USD, {ct:ptrs_cohort_prior.development_context.investment_usd_millions.note}.",
                    "tech": {
                        "es": "{ct:ptrs_cohort_prior.development_context.note}",
                        "en": "{ct:ptrs_cohort_prior.development_context.note}",
                    },
                },
                {
                    "es": "La vía regulatoria queda en {ct:regulatory.status}: {ct:regulatory.pathway}.",
                    "en": "The regulatory route stays at {ct:regulatory.status}: "
                    "{ct:regulatory.pathway}.",
                    "kind": "gap",
                },
                {
                    "es": "Cierre del informe, {report.title}: {report.recommendation}",
                    "en": "The report's own closing line, {report.title}: {report.recommendation}",
                    "kind": "note",
                },
            ],
        },
    ]


# ── the structures worth drawing ──────────────────────────────────────────────────
def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One cartoon: the antibody-antigen complex.

    structure_3d, complex_structure_3d and the chai-1 analysis carry the same
    coordinates in these runs, so the first one that is a real PDB is drawn once
    and every chapter points at it.
    """
    for p in (
        "structure_3d.pdb",
        "complex_structure_3d.pdb",
        "quantum_analyses.chai1_structure.pdb",
        f"{LEAD}.analyses.chai1_structure.pdb",
    ):
        pdb = F.get(r, p)
        if F.is_pdb(pdb):
            return [{"key": "complex", "pdb": pdb, "label": p}]
    return []


# ── arithmetic recomputed from the run ────────────────────────────────────────────
def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    c = lead(r)
    fr = F.get(r, "framework_regions") or {}

    # 1. the variable domains rebuilt from their own framework regions and loops
    rebuilt = {}
    for chain in ("vh", "vl"):
        regs = regions_of(
            c.get(f"{chain}_sequence"),
            fr.get(chain),
            designed_cdrs(r, chain),
            "CDR-H" if chain == "vh" else "CDR-L",
        )
        rebuilt[chain] = "".join(x["seq"] for x in regs)
    if rebuilt["vh"] and rebuilt["vl"]:
        ok = rebuilt["vh"] == c.get("vh_sequence") and rebuilt["vl"] == c.get("vl_sequence")
        out.append(
            {
                "id": "grafting",
                "ok": ok,
                "es": f"FR1+CDR1+FR2+CDR2+FR3+CDR3+FR4 da {len(rebuilt['vh'])} residuos de VH y "
                f"{len(rebuilt['vl'])} de VL, y la corrida declara {c.get('vh_length')} y "
                f"{c.get('vl_length')}"
                + ("" if ok else "; las secuencias reconstruidas NO coinciden"),
                "en": f"FR1+CDR1+FR2+CDR2+FR3+CDR3+FR4 gives {len(rebuilt['vh'])} VH residues and "
                f"{len(rebuilt['vl'])} VL, and the run declares {c.get('vh_length')} and "
                f"{c.get('vl_length')}" + ("" if ok else "; the rebuilt sequences do NOT match"),
                "paths": [f"{LEAD}.vh_sequence", f"{LEAD}.vl_sequence", "framework_regions"],
            }
        )

    # 2. the mature chains as variable domain + the sourced constant tail
    hc = F.get(r, "veterinary_framework.heavy_constant_region_sequence")
    lcst = F.get(r, "veterinary_framework.light_constant_region_sequence")
    fh, fl = c.get("full_heavy_chain_sequence"), c.get("full_light_chain_sequence")
    if (
        isinstance(hc, str)
        and isinstance(fh, str)
        and isinstance(fl, str)
        and isinstance(lcst, str)
    ):
        ok = (
            fh == str(c.get("vh_sequence") or "") + hc
            and fl == str(c.get("vl_sequence") or "") + lcst
        )
        out.append(
            {
                "id": "chain_assembly",
                "ok": ok,
                "es": f"pesada {c.get('vh_length')} + {len(hc)} = {len(fh)} residuos y ligera "
                f"{c.get('vl_length')} + {len(lcst)} = {len(fl)}"
                + ("" if ok else ", pero la concatenación NO reproduce las cadenas exportadas"),
                "en": f"heavy {c.get('vh_length')} + {len(hc)} = {len(fh)} residues and light "
                f"{c.get('vl_length')} + {len(lcst)} = {len(fl)}"
                + ("" if ok else ", but the concatenation does NOT reproduce the exported chains"),
                "paths": [
                    f"{LEAD}.full_heavy_chain_sequence",
                    f"{LEAD}.full_light_chain_sequence",
                    "veterinary_framework.heavy_constant_region_sequence",
                    "veterinary_framework.light_constant_region_sequence",
                ],
            }
        )

    # 3. the mass the PK profile uses, against the chains the run exports
    mw, nv = _num(c.get("mw")), (_num(c.get("vh_length")) or 0) + (_num(c.get("vl_length")) or 0)
    if mw and nv and isinstance(fh, str) and isinstance(fl, str):
        per = mw / nv
        full = len(fh) + len(fl)
        ok = abs(mw - per * full) < 1.0
        out.append(
            {
                "id": "mass_scope",
                "ok": ok,
                "es": f"la masa declarada, {mw / 1000:.1f} kDa, son {int(nv)} residuos × {per:.0f} Da: "
                f"sólo los dominios variables. Las cadenas maduras que exporta la corrida suman "
                f"{full} residuos, {per * full / 1000:.1f} kDa por par pesada+ligera",
                "en": f"the declared mass, {mw / 1000:.1f} kDa, is {int(nv)} residues × {per:.0f} Da: "
                f"the variable domains only. The mature chains the run exports add up to {full} "
                f"residues, {per * full / 1000:.1f} kDa per heavy+light pair",
                "paths": [
                    f"{LEAD}.mw",
                    "admet.molecular_weight_kda",
                    f"{LEAD}.full_heavy_chain_sequence",
                ],
            }
        )

    # 4. whose framework is it: the run's two species fields against each other
    host = F.get(r, "veterinary_framework.host_species")
    anarci = [
        F.get(r, f"veterinary_framework.framework_evidence.{x}.anarci_species")
        for x in ("vh", "vl")
    ]
    if host and all(isinstance(x, str) and x for x in anarci):
        ok = all(str(x).lower() in str(host).lower() for x in anarci)
        out.append(
            {
                "id": "framework_species",
                "ok": ok,
                "es": f"el huésped declarado es {host} y ANARCI asigna «{anarci[0]}» al VH y "
                f"«{anarci[1]}» al VL"
                + (": coinciden" if ok else ": los dos campos de la corrida no coinciden"),
                "en": f'the declared host is {host} and ANARCI assigns "{anarci[0]}" to the VH and '
                f'"{anarci[1]}" to the VL'
                + (": they agree" if ok else ": the run's two fields disagree"),
                "paths": [
                    "veterinary_framework.host_species",
                    "veterinary_framework.framework_evidence.vh.anarci_species",
                    "veterinary_framework.framework_evidence.vl.anarci_species",
                ],
            }
        )

    # 5. which loops actually changed, against what the CDR step documents
    ref = reference_cdrs(r, "vh") + reference_cdrs(r, "vl")
    des = designed_cdrs(r, "vh") + designed_cdrs(r, "vl")
    documented = 1 if F.get(r, f"{S2}.top_cdr_h3_sequences") else 0
    if len(ref) == 6 and all(des):
        changed = [i for i in range(6) if ref[i] != des[i]]
        names = ["H1", "H2", "H3", "L1", "L2", "L3"]
        ok = len(changed) == documented
        out.append(
            {
                "id": "cdr_origin",
                "ok": ok,
                "es": f"{len(changed)} de las 6 asas difieren del armazón de referencia "
                f"({', '.join(names[i] for i in changed)}), y el paso de diseño documenta la búsqueda "
                f"de {documented}",
                "en": f"{len(changed)} of the 6 loops differ from the reference framework "
                f"({', '.join(names[i] for i in changed)}), and the design step documents searching "
                f"for {documented}",
                "paths": [
                    f"{S2}.top_cdr_h3_sequences",
                    "veterinary_framework.vh_reference_sequence",
                    "veterinary_framework.vl_reference_sequence",
                    f"{LEAD}.cdr_h1",
                ],
            }
        )

    # 6. a step that says it was conditioned on a structure it does not name
    cond = F.get(r, f"{S2}.conditioned_on_structure")
    if isinstance(cond, bool):
        src = F.get(r, f"{S2}.structure_source")
        pdb_id = F.get(r, f"{S2}.pdb_id")
        ok = (not cond) or bool(src) or (isinstance(pdb_id, str) and pdb_id not in ("", "unknown"))
        out.append(
            {
                "id": "cdr_conditioning",
                "ok": ok,
                "es": f"conditioned_on_structure={cond} con structure_source={src!r} y pdb_id={pdb_id!r}"
                + ("" if ok else ": la estructura que condiciona el diseño no está nombrada"),
                "en": f"conditioned_on_structure={cond} with structure_source={src!r} and "
                f"pdb_id={pdb_id!r}"
                + ("" if ok else ": the structure said to condition the design is never named"),
                "paths": [
                    f"{S2}.conditioned_on_structure",
                    f"{S2}.structure_source",
                    f"{S2}.pdb_id",
                ],
            }
        )

    # 7. the affinity rank, recomputed from the raw scores
    energies = [e for e in (F.get(r, f"{S7}.binding_energies") or []) if _num(e) is not None]
    mine = _num(F.get(r, f"{LEAD}.scores.binding_energy"))
    declared = F.get(r, f"{LEAD}.scores.affinity_rank")
    if energies and mine is not None and isinstance(declared, int):
        # the candidate's own score is stored rounded; take the raw entry nearest to it
        raw = min(energies, key=lambda e: abs(_num(e) - mine))
        better = sum(1 for e in energies if _num(e) < _num(raw) - 1e-12)
        ok = better + 1 == declared
        out.append(
            {
                "id": "affinity_rank",
                "ok": ok,
                "es": f"{better} de {len(energies)} candidatos puntúan por debajo de {_num(raw):.4f}, "
                f"así que el líder es el número {better + 1}; la corrida dice {declared}",
                "en": f"{better} of {len(energies)} candidates score below {_num(raw):.4f}, so the "
                f"lead is number {better + 1}; the run says {declared}",
                "paths": [f"{S7}.binding_energies", f"{LEAD}.scores.affinity_rank"],
            }
        )

    # 8. the lead really is the best under the rule the run names, and the two rules
    #    the run uses to describe itself pick the same candidate
    win = selection_winners(r)
    lead_id = F.get(r, f"{LEAD}.candidate_id")
    if win and lead_id:
        rule = win["declared"]
        winner = win[rule]
        ok = winner["id"] == lead_id
        detail = "; ".join(
            f"{str(x['id'])[-3:]} {x['affinity_rank']}/{x['iptm_rank']}={x['composite']:.1f}"
            for x in win["rows"]
        )
        out.append(
            {
                "id": "lead_selection",
                "ok": ok,
                "es": f"afinidad/ipTM por candidato: {detail}. Regla declarada: {rule}; con ella gana "
                f"{str(winner['id'])[-3:]} y la corrida elige {str(lead_id)[-3:]}",
                "en": f"affinity/ipTM per candidate: {detail}. Declared rule: {rule}; under it "
                f"{str(winner['id'])[-3:]} wins and the run picks {str(lead_id)[-3:]}",
                "paths": ["candidates", f"{LEAD}.candidate_id", f"{LEAD}.selection_basis"],
            }
        )
        same = win["composite"]["id"] == win["lexicographic"]["id"]
        out.append(
            {
                "id": "selection_rule",
                "ok": same,
                "es": f"la corrida describe la selección de dos maneras: por rango compuesto gana "
                f"{str(win['composite']['id'])[-3:]}, por orden lexicográfico (afinidad, "
                f"responsabilidades, ipTM) gana {str(win['lexicographic']['id'])[-3:]}"
                + (": el mismo" if same else ": candidatos distintos"),
                "en": f"the run describes its selection two ways: by composite rank "
                f"{str(win['composite']['id'])[-3:]} wins, by the lexicographic order (affinity, "
                f"liabilities, ipTM) {str(win['lexicographic']['id'])[-3:]} wins"
                + (": the same one" if same else ": different candidates"),
                "paths": [f"{S11}.ranking_method", f"{LEAD}.selection_basis", "candidates"],
            }
        )

    # 9. a Kd the stage prints and the candidate refuses
    kds = F.get(r, f"{S7}.kd_estimates_nm")
    if isinstance(kds, list) and kds:
        ok = F.get(r, "docking.kd_nM") is not None
        vals = [x for x in (_num(v) for v in kds) if x is not None]
        out.append(
            {
                "id": "kd_silence",
                "ok": ok,
                "es": f"el paso de ranking publica {len(kds)} Kd en nM (de {min(vals):g} a "
                f"{max(vals):g}) mientras docking.kd_nM queda vacío"
                + ("" if ok else " y calibrado en kcal/mol es falso"),
                "en": f"the ranking step publishes {len(kds)} Kd values in nM ({min(vals):g} to "
                f"{max(vals):g}) while docking.kd_nM stays empty"
                + ("" if ok else " and calibrated-in-kcal/mol is false"),
                "paths": [f"{S7}.kd_estimates_nm", "docking.kd_nM", f"{S7}.calibrated_kcal_mol"],
            }
        )

    # 10. how much of the molecule the liability scan actually looked at
    scanned = _num(F.get(r, f"{LEAD}.developability.developability_liabilities.composition.length"))
    if scanned and isinstance(fh, str) and isinstance(fl, str):
        full = len(fh) + len(fl)
        blind = 0
        for cand in candidates(r):
            blind += sum(
                str(cand.get(f"cdr_{k}") or "").count("C") for k in ("h1", "h2", "l1", "l2", "l3")
            )
        ok = int(scanned) >= full
        out.append(
            {
                "id": "liability_scope",
                "ok": ok,
                "es": f"el barrido mira {int(scanned)} de {full} residuos de las cadenas maduras "
                f"({scanned / full:.1%}): sólo la CDR-H3. Fuera de esa ventana los candidatos meten "
                f"{blind} cisteínas en otras asas",
                "en": f"the scan looks at {int(scanned)} of {full} residues of the mature chains "
                f"({scanned / full:.1%}): the CDR-H3 only. Outside that window the candidates put "
                f"{blind} cysteines into other loops",
                "paths": [
                    f"{LEAD}.developability.developability_liabilities.composition.length",
                    f"{S5}.method",
                    f"{LEAD}.full_heavy_chain_sequence",
                ],
            }
        )

    # 11-13. what the drawn coordinates themselves say
    res = ca_residues(F.get(r, "structure_3d.pdb"))
    if res:
        parts = chain_parts(r, res)
        named = {p["key"]: p["n"] for p in parts if p["key"]}
        total = (
            (_num(c.get("vh_length")) or 0)
            + (_num(c.get("vl_length")) or 0)
            + (_num(F.get(r, "antigen_identity.length_aa")) or 0)
        )
        ok = len(named) == 3 and len(res) == int(total)
        out.append(
            {
                "id": "complex_composition",
                "ok": ok,
                "es": f"el complejo dibujado trae {len(res)} residuos en {len(parts)} cadena(s); "
                f"VH {c.get('vh_length')} + VL {c.get('vl_length')} + antígeno "
                f"{F.get(r, 'antigen_identity.length_aa')} = {int(total)}"
                + ("" if ok else ", que NO cuadra con lo dibujado"),
                "en": f"the drawn complex holds {len(res)} residues in {len(parts)} chain(s); "
                f"VH {c.get('vh_length')} + VL {c.get('vl_length')} + antigen "
                f"{F.get(r, 'antigen_identity.length_aa')} = {int(total)}"
                + ("" if ok else ", which does NOT match what was drawn"),
                "paths": ["structure_3d.pdb", f"{LEAD}.vh_length", "antigen_identity.length_aa"],
            }
        )

        ag = part_span(parts, "antigen")
        declared_len = _num(F.get(r, "antigen_identity.length_aa"))
        basis = F.get(r, "antigen_identity.selection_basis") or []
        mature_flag = any("mature" in str(x).lower() for x in basis)
        if ag and declared_len and mature_flag:
            folded = ag[1] - ag[0]
            ok = folded < declared_len
            out.append(
                {
                    "id": "antigen_mature",
                    "ok": ok,
                    "es": f"la base de selección cita una característica de cadena madura y la entrada "
                    f"mide {int(declared_len)} aminoácidos; la cadena de antígeno que se plegó tiene "
                    f"{folded}" + (", ya recortada" if ok else ", es decir la precursora completa"),
                    "en": f"the selection basis cites a mature-chain feature and the entry is "
                    f"{int(declared_len)} amino acids; the antigen chain that was folded has {folded}"
                    + (", already trimmed" if ok else ", that is, the full precursor"),
                    "paths": [
                        "antigen_identity.selection_basis",
                        "antigen_identity.length_aa",
                        "structure_3d.pdb",
                    ],
                }
            )

        b = mean_b(res)
        reported = _num(F.get(r, "protenix_structure.plddt"))
        if b is not None and reported is not None:
            own = _num(F.get(r, "structure_3d.plddt"))
            ok = own is not None and abs(b - reported) <= 2.0
            out.append(
                {
                    "id": "drawn_confidence",
                    "ok": ok,
                    "es": f"la columna B del modelo dibujado ({F.get(r, 'structure_3d.method')}) da una "
                    f"confianza media por residuo de {b:.1f}; el pLDDT que publica la corrida, "
                    f"{reported:g}, es del modelo de {F.get(r, f'{S9}.method')}, y structure_3d.plddt "
                    f"está vacío",
                    "en": f"the B-factor column of the drawn model ({F.get(r, 'structure_3d.method')}) "
                    f"gives a mean per-residue confidence of {b:.1f}; the pLDDT the run publishes, "
                    f"{reported:g}, belongs to the {F.get(r, f'{S9}.method')} model, and "
                    f"structure_3d.plddt is empty",
                    "paths": ["structure_3d.pdb", "structure_3d.plddt", "protenix_structure.plddt"],
                }
            )

    face = interface(r)
    if face and face["closest_A"] is not None:
        ok = face["n_contacts"] > 0
        out.append(
            {
                "id": "interface",
                "ok": ok,
                "es": f"en las coordenadas dibujadas, {face['n_contacts']} de los {face['n_antigen']} "
                f"residuos del antígeno quedan a {CONTACT_A:.0f} Å o menos de la CDR-H3 (CA-CA); el más "
                f"cercano es {face['closest_label']} a {face['closest_A']} Å",
                "en": f"in the drawn coordinates, {face['n_contacts']} of the {face['n_antigen']} "
                f"antigen residues sit within {CONTACT_A:.0f} A of the CDR-H3 (CA-CA); the closest is "
                f"{face['closest_label']} at {face['closest_A']} A",
                "paths": ["structure_3d.pdb", f"{LEAD}.cdr_h3", f"{S1}.epitope_residues"],
            }
        )

    # 14. the quantum ledger against its own fraction
    nq, ne = F.get(r, "quantum_contribution.quantum_step_count"), F.get(
        r, "quantum_contribution.eligible_step_count"
    )
    frac = _num(F.get(r, "quantum_contribution.measured_quantum_fraction"))
    ledger = F.get(r, "quantum_contribution.stage_ledger") or []
    if isinstance(nq, int) and isinstance(ne, int) and ne and frac is not None:
        counted = sum(
            1
            for s in ledger
            if isinstance(s, dict)
            and s.get("compute_class") == "quantum"
            and s.get("delivers_quantum_output")
        )
        ok = abs(nq / ne - frac) <= 0.001 and counted == nq and len(ledger) == ne
        out.append(
            {
                "id": "quantum_fraction",
                "ok": ok,
                "es": f"{counted} filas cuánticas de {len(ledger)} en el libro mayor, {nq}/{ne} = "
                f"{nq / ne:.3f} y la corrida publica {frac}",
                "en": f"{counted} quantum rows of {len(ledger)} in the ledger, {nq}/{ne} = "
                f"{nq / ne:.3f} and the run publishes {frac}",
                "paths": [
                    "quantum_contribution.stage_ledger",
                    "quantum_contribution.measured_quantum_fraction",
                ],
            }
        )

    # 15. the sequence register: five qubits per residue, and the residues are the design's
    nres = _num(F.get(r, "quantum_analyses.quantum_sequence_state.n_residues"))
    nqb = _num(F.get(r, "quantum_analyses.quantum_sequence_state.n_qubits"))
    if nres and nqb and nv:
        ok = int(nres) == int(nv) and int(nqb) == int(nres) * 5
        out.append(
            {
                "id": "qubit_encoding",
                "ok": ok,
                "es": f"{int(nres)} residuos cargados = VH {c.get('vh_length')} + VL "
                f"{c.get('vl_length')}, y {int(nqb)} cúbits son {int(nqb / nres)} por residuo"
                + ("" if ok else "; no cuadra con la codificación declarada"),
                "en": f"{int(nres)} residues loaded = VH {c.get('vh_length')} + VL "
                f"{c.get('vl_length')}, and {int(nqb)} qubits are {int(nqb / nres)} per residue"
                + ("" if ok else "; that does not match the declared encoding"),
                "paths": [
                    "quantum_analyses.quantum_sequence_state.n_residues",
                    "quantum_analyses.quantum_sequence_state.n_qubits",
                    f"{LEAD}.vh_length",
                ],
            }
        )

    # 16. the variational bound, and the embedding energy's own subtraction
    vqe = _num(F.get(r, "quantum_analyses.quantum_real_hamiltonian.vqe_energy_Ha"))
    refe = _num(F.get(r, "quantum_analyses.quantum_real_hamiltonian.reference_energy_Ha"))
    if vqe is not None and refe is not None:
        ok = vqe >= refe
        out.append(
            {
                "id": "variational",
                "ok": ok,
                "es": f"la energía VQE {vqe:.4f} Ha está {abs(vqe - refe):.4f} Ha por encima del estado "
                f"fundamental exacto {refe:.4f} Ha ({abs((vqe - refe) / refe):.1%} del valor)"
                + ("" if ok else ", es decir POR DEBAJO, lo que no puede ser"),
                "en": f"the VQE energy {vqe:.4f} Ha sits {abs(vqe - refe):.4f} Ha above the exact "
                f"ground state {refe:.4f} Ha ({abs((vqe - refe) / refe):.1%} of it)"
                + ("" if ok else ", that is BELOW it, which cannot happen"),
                "paths": [
                    "quantum_analyses.quantum_real_hamiltonian.vqe_energy_Ha",
                    "quantum_analyses.quantum_real_hamiltonian.reference_energy_Ha",
                ],
            }
        )
    hf = _num(F.get(r, "quantum_analyses.ewf_sqd.hf_energy_Ha"))
    emb = _num(F.get(r, "quantum_analyses.ewf_sqd.ewf_embedding_energy_Ha"))
    corr = _num(F.get(r, "quantum_analyses.ewf_sqd.correlation_energy_Ha"))
    if hf is not None and emb is not None and corr is not None:
        ok = abs((emb - hf) - corr) <= 1e-6
        out.append(
            {
                "id": "ewf_energy",
                "ok": ok,
                "es": f"{emb:.6f} − {hf:.6f} = {emb - hf:.6f} Ha de correlación, y la corrida anota "
                f"{corr:.6f}",
                "en": f"{emb:.6f} − {hf:.6f} = {emb - hf:.6f} Ha of correlation energy, and the run "
                f"records {corr:.6f}",
                "paths": [
                    "quantum_analyses.ewf_sqd.hf_energy_Ha",
                    "quantum_analyses.ewf_sqd.ewf_embedding_energy_Ha",
                    "quantum_analyses.ewf_sqd.correlation_energy_Ha",
                ],
            }
        )

    # 17. the phase priors: each factor, and their product
    p = "clinical_trial.ptrs_cohort_prior"
    phases = [
        (
            F.get(r, f"{p}.{k}.value"),
            F.get(r, f"{p}.{k}.human_base_rate"),
            F.get(r, f"{p}.{k}.veterinary_uplift"),
        )
        for k in ("phase_1_to_2", "phase_2_to_3", "phase_3_to_approval")
    ]
    cum = _num(F.get(r, f"{p}.cumulative_approval.value"))
    if all(_num(v) is not None for v, _, _ in phases) and cum is not None:
        prod = 1.0
        factors_ok = True
        for v, base, up in phases:
            prod *= _num(v)
            if _num(base) is not None and _num(up) is not None:
                factors_ok = factors_ok and abs(_num(base) * _num(up) - _num(v)) <= 0.001
        ok = factors_ok and abs(prod - cum) <= 0.005
        out.append(
            {
                "id": "ptrs_product",
                "ok": ok,
                "es": f"{' × '.join(f'{_num(v):g}' for v, _, _ in phases)} = {prod:.4f} y la acumulada "
                f"publicada es {cum:g}"
                + ("" if factors_ok else "; algún factor base × elevación no da su fase"),
                "en": f"{' × '.join(f'{_num(v):g}' for v, _, _ in phases)} = {prod:.4f} and the "
                f"published cumulative is {cum:g}"
                + ("" if factors_ok else "; some base rate × uplift does not give its phase"),
                "paths": [f"{p}.phase_1_to_2.value", f"{p}.cumulative_approval.value"],
            }
        )

    # 18. the candidate count, against the lists that carry it
    n = F.get(r, "candidate_count")
    lists = {
        "candidates": len(candidates(r)),
        f"{S6}.candidate_ids": len(F.get(r, f"{S6}.candidate_ids") or []),
        f"{S9}.predictions": len(F.get(r, f"{S9}.predictions") or []),
        f"{S7}.binding_energies": len(F.get(r, f"{S7}.binding_energies") or []),
        f"{S8}.candidate_ids": len(F.get(r, f"{S8}.candidate_ids") or []),
    }
    if isinstance(n, int):
        ok = all(v == n for v in lists.values())
        out.append(
            {
                "id": "candidate_count",
                "ok": ok,
                "es": f"candidate_count={n} y las listas traen "
                + ", ".join(f"{k.split('.')[-1]} {v}" for k, v in lists.items()),
                "en": f"candidate_count={n} and the lists carry "
                + ", ".join(f"{k.split('.')[-1]} {v}" for k, v in lists.items()),
                "paths": ["candidate_count"] + list(lists),
            }
        )
    return out


# MOLEVERA / BIOQL
