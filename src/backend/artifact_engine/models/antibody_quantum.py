"""
Artifact model for the antibody discovery pipeline (`quantum_antibody_discovery`).

The pipeline builds an scFv the way a protein engineer would: it picks a human
germline framework, designs the six CDR loops (the heavy-chain third loop on a
variational quantum circuit), scores the pool for humanness, immunogenicity and
sequence liabilities, keeps a handful of candidates, and then runs the usual
downstream panels -- developability, affinity, ADMET/PK, a trial template.

So the chapters follow that order, and the derivations are all recomputed here
from the run's own strings and arrays:

  * the heavy and light chains are REBUILT from the selected germline framework
    regions plus the designed CDRs, and compared character by character with the
    sequences the run stored;
  * each finalist's CDR-H3 is looked for among the 32 loops the VQE stage
    actually designed, and the nearest designed loop is found by Hamming
    distance when it is not there;
  * the position of each finalist inside the 32-long score arrays is recovered
    from its own recorded scores, which is what exposes the identifier collision
    between the candidate pool and the finalists;
  * the drawn structure is parsed and compared against the designed chains, the
    declared binding-site sphere and the declared G12C mutation;
  * the recorded molecular mass is compared with the mass of its own amino-acid
    composition;
  * the clinical phase chain is multiplied out.

Several of those checks fail on a real run. They are kept, and each failure has
a sentence of its own that says plainly what did not add up.

MOLEVERA / BIOQL
"""

import math
from typing import Any, Dict, List, Optional, Tuple

try:  # inside the package, as build.py imports it
    from .. import facts as F
except ImportError:  # loaded straight from its path, as the check script does
    from artifact_engine import facts as F

PIPELINE = "quantum_antibody_discovery"
TITLE = {"es": "Anticuerpo cuántico", "en": "Quantum antibody"}

ST = "stages"
S_TA = f"{ST}.target_analysis"
S_IG = f"{ST}.iglm_proposer"
S_TG = f"{ST}.trained_target_antibody_generator"
S_FW = f"{ST}.framework_selection"
S_CD = f"{ST}.cdr_design_vqe"
S_HU = f"{ST}.humanization_scoring"
S_IM = f"{ST}.immunogenicity_screening"
S_DV = f"{ST}.developability_assessment"
S_CG = f"{ST}.candidate_generation"
S_IT = f"{ST}.iterative_optimization"
S_BA = f"{ST}.binding_affinity"
S_SP = f"{ST}.structure_prediction"
S_AP = f"{ST}.admet_tox_pk"
S_CT = f"{ST}.clinical_trial_simulation"
S_QS = f"{ST}.quantum_sequence_state"
S_RP = f"{ST}.report"
BEST = "best_candidate"

ALIASES = {
    "ta": S_TA,
    "ig": S_IG,
    "tg": S_TG,
    "fw": S_FW,
    "cd": S_CD,
    "hu": S_HU,
    "im": S_IM,
    "dv": S_DV,
    "cg": S_CG,
    "it": S_IT,
    "ba": S_BA,
    "sp": S_SP,
    "ap": S_AP,
    "ct": S_CT,
    "qs": S_QS,
    "b": BEST,
    "rep": "report",
    "md": "metadata",
    "in": "input",
    "qc": "quantum_core_optimization",
    "qp": "quantum_provenance",
    "qcas": "enhancements.quantum_cascade",
    "dl": "enhancements.downloads",
    "qcv": "quantum_cell_validation",
    "cl": "clinical_trial",
    "dk": "docking",
    "m3": "mol_3d",
    "ad": "admet",
    "a92": "admet_92_parameters",
    "ph": "pharmacology",
    "tx": "toxicology",
    "px": "protenix_structure",
    "iters": "iterations",
}

# average residue masses (Da), for recomputing the mass of a written sequence
_RESIDUE_DA = {
    "G": 57.0519,
    "A": 71.0788,
    "S": 87.0782,
    "P": 97.1167,
    "V": 99.1326,
    "T": 101.1051,
    "C": 103.1388,
    "L": 113.1594,
    "I": 113.1594,
    "N": 114.1038,
    "D": 115.0886,
    "Q": 128.1307,
    "K": 128.1741,
    "E": 129.1155,
    "M": 131.1926,
    "H": 137.1411,
    "F": 147.1766,
    "R": 156.1875,
    "Y": 163.1760,
    "W": 186.2132,
}
_WATER_DA = 18.0153

_FR = ("FR1", "FR2", "FR3", "FR4")
_CDR_H = ("cdr_h1", "cdr_h2", "cdr_h3")
_CDR_L = ("cdr_l1", "cdr_l2", "cdr_l3")

# the flat ADMET aliases each candidate repeats next to its admet block
_ADMET_FLAT = (
    "admet_parameters_count",
    "admet_advertised_panel",
    "admet_score",
    "half_life_days",
    "clearance_ml_day_kg",
    "vd_L",
    "sc_bioavailability_pct",
    "fcrn_binding",
    "administration_route",
    "molecular_weight_kda",
    "herg",
    "herg_ic50_um",
    "herg_ic50_uM",
    "herg_pic50",
    "ames",
    "ames_mutagenicity",
    "caco2",
    "caco2_perm",
    "caco2_permeability",
    "bbb",
    "bbb_penetration",
    "oral_bioavailability",
    "oral_bioavailability_pct",
    "bioavailability",
    "cyp3a4",
    "cyp2d6",
    "cyp2c9",
    "cyp1a2",
    "cyp2c19",
    "dili",
    "hepatotoxicity",
    "cardiotoxicity",
    "nephrotoxicity",
    "ppb",
    "plasma_protein_binding",
    "solubility",
    "aqueous_solubility",
    "logs",
    "clearance",
    "half_life",
)


def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    if str(r.get("pipeline") or "").startswith("quantum_antibody"):
        return True
    st = r.get("stages")
    return isinstance(st, dict) and "cdr_design_vqe" in st and "framework_selection" in st


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("result"), dict):
        inner = result["result"]
        if "stages" in inner or "pipeline" in inner:
            return inner
    return result


def subject(r: Dict[str, Any]) -> str:
    bits = [
        str(r.get("antibody_type") or F.get(r, "metadata.antibody_format") or "").strip(),
        f"anti-{r.get('target')}" if r.get("target") else "",
        str(r.get("pdb_id") or "").strip(),
        str(F.get(r, "report.lead_candidate") or "").strip(),
    ]
    return " · ".join(b for b in bits if b)


# ── small derivations, all from the run's own values ────────────────────────────────
def cands(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in (r.get("candidates") or []) if isinstance(c, dict)]


def _each(r: Dict[str, Any], *suffixes: str) -> List[str]:
    """The same sub-path on every candidate and on the top-level copy of candidate 0."""
    out: List[str] = []
    n = len(cands(r))
    for s in suffixes:
        out += [f"candidates[{i}].{s}" for i in range(n)]
        out.append(f"{BEST}.{s}")
    return out


def rebuild(r: Dict[str, Any], c: Dict[str, Any]) -> Tuple[str, str]:
    """The heavy and light chains as the framework regions plus the designed CDRs."""
    vh_fr = F.get(r, f"{S_FW}.vh_framework_regions") or {}
    vl_fr = F.get(r, f"{S_FW}.vl_framework_regions") or {}
    if not all(isinstance(vh_fr.get(k), str) for k in _FR) or not all(
        isinstance(vl_fr.get(k), str) for k in _FR
    ):
        return "", ""
    h = [
        vh_fr["FR1"],
        c.get("cdr_h1"),
        vh_fr["FR2"],
        c.get("cdr_h2"),
        vh_fr["FR3"],
        c.get("cdr_h3"),
        vh_fr["FR4"],
    ]
    light = [
        vl_fr["FR1"],
        c.get("cdr_l1"),
        vl_fr["FR2"],
        c.get("cdr_l2"),
        vl_fr["FR3"],
        c.get("cdr_l3"),
        vl_fr["FR4"],
    ]
    if any(not isinstance(x, str) for x in h + light):
        return "", ""
    return "".join(h), "".join(light)


def mosaic(r: Dict[str, Any], c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The lead chain written out in the pieces it was assembled from."""
    vh_fr = F.get(r, f"{S_FW}.vh_framework_regions") or {}
    vl_fr = F.get(r, f"{S_FW}.vl_framework_regions") or {}
    vh_g = c.get("vh_germline") or "VH"
    vl_g = c.get("vl_germline") or "VL"
    out: List[Dict[str, Any]] = []
    for fr, cdr, germ, tag in ((vh_fr, _CDR_H, vh_g, "H"), (vl_fr, _CDR_L, vl_g, "L")):
        parts = [
            (fr.get("FR1"), f"{germ} FR1"),
            (c.get(cdr[0]), f"CDR-{tag}1 (VQE)"),
            (fr.get("FR2"), f"{germ} FR2"),
            (c.get(cdr[1]), f"CDR-{tag}2 (VQE)"),
            (fr.get("FR3"), f"{germ} FR3"),
            (c.get(cdr[2]), f"CDR-{tag}3 (VQE)"),
            (fr.get("FR4"), f"{germ} FR4"),
        ]
        out += [{"seq": s, "source": src} for s, src in parts if isinstance(s, str) and s]
    return out


def pool_index(r: Dict[str, Any], c: Dict[str, Any]) -> Optional[int]:
    """Where a finalist sits inside the 32-long score arrays.

    Recovered from the candidate's own recorded numbers: the position where BOTH
    its humanisation score and its VQE energy appear. Two independent arrays
    agreeing on one index is what makes this a position and not a coincidence."""
    hs = F.get(r, f"{S_HU}.humanization_scores") or []
    en = F.get(r, f"{S_CD}.vqe_energies") or []
    h, e = c.get("humanization_score"), c.get("vqe_energy")
    if not isinstance(h, (int, float)) or not isinstance(e, (int, float)):
        return None
    for i, x in enumerate(hs):
        if isinstance(x, (int, float)) and abs(x - h) < 1e-12:
            if i < len(en) and isinstance(en[i], (int, float)) and abs(en[i] - e) < 1e-12:
                return i
    return None


def _hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def nearest_designed(r: Dict[str, Any], loop: Any) -> Tuple[Optional[str], Optional[int]]:
    """The designed CDR-H3 closest to a finalist's loop, and how many residues differ."""
    tops = [t for t in (F.get(r, f"{S_CD}.top_cdr_h3_sequences") or []) if isinstance(t, str)]
    if not isinstance(loop, str) or not tops:
        return None, None
    same = [t for t in tops if len(t) == len(loop)]
    if not same:
        return None, None
    best = min(same, key=lambda t: _hamming(t, loop))
    return best, _hamming(best, loop)


def composition_mass(seq: str) -> Optional[float]:
    if not seq or any(x not in _RESIDUE_DA for x in seq):
        return None
    return sum(_RESIDUE_DA[x] for x in seq) + _WATER_DA


def drawn(r: Dict[str, Any]) -> Dict[str, Any]:
    """The one structure this run stored, parsed: chain, sequence, centroid."""
    try:
        from .. import mesh as _mesh
    except ImportError:
        from artifact_engine import mesh as _mesh

    pdb = F.get(r, "mol_3d.protein_pdb")
    if not F.is_pdb(pdb):
        return {}
    try:
        res, kind = _mesh.residues(pdb)
    except Exception:
        return {}
    if len(res) < 3:
        return {}
    three = {
        "ALA": "A",
        "ARG": "R",
        "ASN": "N",
        "ASP": "D",
        "CYS": "C",
        "GLN": "Q",
        "GLU": "E",
        "GLY": "G",
        "HIS": "H",
        "ILE": "I",
        "LEU": "L",
        "LYS": "K",
        "MET": "M",
        "PHE": "F",
        "PRO": "P",
        "SER": "S",
        "THR": "T",
        "TRP": "W",
        "TYR": "Y",
        "VAL": "V",
        "MSE": "M",
    }
    cen = [sum(x["p"][k] for x in res) / len(res) for k in range(3)]
    return {
        "res": res,
        "kind": kind,
        "n": len(res),
        "seq": "".join(three.get(x["resn"], "X") for x in res),
        "centroid": cen,
        "copies": sum(1 for _, v in F.flatten(r) if F.is_pdb(v)),
    }


def site(r: Dict[str, Any]) -> Dict[str, Any]:
    s = F.get(r, "docking.binding_site") or F.get(r, "mol_3d.binding_site") or {}
    return s if isinstance(s, dict) else {}


def free_cys(r: Dict[str, Any], c: Dict[str, Any]) -> Dict[str, int]:
    """Cysteines beyond the two the germline framework contributes to each domain."""
    vh_fr = F.get(r, f"{S_FW}.vh_framework_regions") or {}
    vl_fr = F.get(r, f"{S_FW}.vl_framework_regions") or {}
    out = {}
    for tag, fr, seq in (("vh", vh_fr, c.get("vh_sequence")), ("vl", vl_fr, c.get("vl_sequence"))):
        base = sum(v.count("C") for v in fr.values() if isinstance(v, str))
        total = seq.count("C") if isinstance(seq, str) else 0
        out[tag] = total - base
    return out


# ── scenes ─────────────────────────────────────────────────────────────────────────
def scene_cover(r: Dict[str, Any], mesh_key: Optional[str]) -> Dict[str, Any]:
    def stat(es, en, path, unit=None):
        v = F.get(r, path)
        return (
            None
            if v in (None, "", [], {})
            else {"es": es, "en": en, "value": v, "unit": unit, "path": path}
        )

    stats = [
        stat("Formato", "Format", "antibody_type"),
        stat("Blanco", "Target", "target_description"),
        stat("Candidatos reportados", "Candidates reported", "report.candidates_evaluated"),
        stat("Nota compuesta del líder", "Lead composite score", "composite_score"),
        stat("Clase", "Class", "drug_candidate_class"),
        stat("Tiempo total", "Total time", "total_time_seconds", "s"),
    ]
    return {
        "type": "cover",
        "mesh": mesh_key,
        "images": [],
        "stats": [s for s in stats if s],
    }


def scene_antigen(
    r: Dict[str, Any], mesh_key: Optional[str], meshes: Dict[str, Any]
) -> Dict[str, Any]:
    """The antigen as it was drawn, with the declared binding-site centre marked
    in the same frame -- so the reader can see where the run says the site is."""
    notes: List[Dict[str, Any]] = []
    measures: List[Dict[str, Any]] = []
    m = meshes.get(mesh_key or "")
    s = site(r)
    if m and m.get("res"):
        res = m["res"]
        c = m.get("center") or [0.0, 0.0, 0.0]
        first, last = res[0], res[-1]
        notes.append(
            {
                "text": f"N · {first['resn']}{first['resi']}",
                "pos": [first["p"][0], first["p"][1] + 2.4, first["p"][2]],
            }
        )
        notes.append(
            {
                "text": f"C · {last['resn']}{last['resi']}",
                "pos": [last["p"][0], last["p"][1] + 2.4, last["p"][2]],
            }
        )
        mut = next((x for x in res if x["resi"] == "12"), None)
        if mut:
            notes.append(
                {"text": f"{mut['resn']}12", "pos": [mut["p"][0], mut["p"][1] + 2.4, mut["p"][2]]}
            )
        if all(isinstance(s.get(k), (int, float)) for k in ("center_x", "center_y", "center_z")):
            pos = [s["center_x"] - c[0], s["center_y"] - c[1], s["center_z"] - c[2]]
            rad = s.get("radius")
            notes.append(
                {
                    "text": "binding_site"
                    + (f" · r {rad} Å" if isinstance(rad, (int, float)) else ""),
                    "pos": pos,
                }
            )
            if mut:
                d = math.dist(mut["p"], pos)
                measures.append(
                    {
                        "from": mut["p"],
                        "to": pos,
                        "label": f"{mut['resn']}12 → binding_site · {d:.1f} Å",
                    }
                )
    return {
        "type": "cartoon",
        "mesh": mesh_key,
        "domains": [],
        "receptors": [x for x in [r.get("target")] if x],
        "annotations": notes,
        "measures": measures,
        "pdb_id": r.get("pdb_id"),
        "site": s,
    }


def scene_design(r: Dict[str, Any]) -> Dict[str, Any]:
    cs = cands(r)
    items = mosaic(r, cs[0]) if cs else []
    items += [
        {"seq": t, "source": "cdr_design_vqe"}
        for t in (F.get(r, f"{S_CD}.top_cdr_h3_sequences") or [])
        if isinstance(t, str)
    ]
    return {
        "type": "sequences",
        "items": items,
        "n": F.get(r, f"{S_CD}.total_evaluated"),
        "jobs": len(F.get(r, f"{S_CD}.ibm_job_ids") or []),
    }


def scene_quantum(r: Dict[str, Any]) -> Dict[str, Any]:
    en = [x for x in (F.get(r, f"{S_CD}.vqe_energies") or []) if isinstance(x, (int, float))]
    return {
        "type": "quantum",
        "n_qubits": F.get(r, f"{S_QS}.n_qubits"),
        "n_terms": None,
        "n_contacts": None,
        "n_residues": F.get(r, f"{S_QS}.n_residues"),
        "energy": min(en) if en else None,
        "reference": None,
        "backend": r.get("quantum_backend"),
        "algorithms": F.get(r, "enhancements.quantum_cascade.algorithms") or {},
        "encoding": F.get(r, f"{S_QS}.encoding"),
        "jobs": (F.get(r, "simulator_job_ids") or []) + (F.get(r, "ibm_job_ids") or []),
    }


def scene_humanness(r: Dict[str, Any]) -> Dict[str, Any]:
    """Both proxy scores for the whole pool, labelled by array position.

    Deliberately NOT labelled with candidate_ids: the pool's identifiers do not
    line up with these positions (see the `id_alignment` check)."""
    hs = F.get(r, f"{S_HU}.humanization_scores") or []
    ims = F.get(r, f"{S_IM}.scores") or []
    items: List[Dict[str, Any]] = []
    for i, v in enumerate(hs):
        if isinstance(v, (int, float)):
            items.append(
                {
                    "group": "humanization",
                    "name": f"#{i + 1}",
                    "value": round(v, 4),
                    "label": F.get(r, f"{S_HU}.score_type"),
                    "unit": None,
                    "note": None,
                }
            )
    for i, v in enumerate(ims):
        if isinstance(v, (int, float)):
            items.append(
                {
                    "group": "immunogenicity",
                    "name": f"#{i + 1}",
                    "value": round(v, 4),
                    "label": F.get(r, f"{S_IM}.score_type"),
                    "unit": None,
                    "note": None,
                }
            )
    return {
        "type": "endpoints",
        "model": F.get(r, f"{S_HU}.scoring_method"),
        "n": len(hs),
        "score": F.get(r, f"{S_HU}.threshold"),
        "items": items,
    }


def scene_ranking(r: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    for c in cands(r):
        comp = F.get(c, "developability.developability_liabilities.composition") or {}
        items.append(
            {
                "rank": c.get("rank"),
                "id": c.get("candidate_id"),
                "seq": c.get("cdr_h3"),
                "score": F.get(c, "scores.composite_score"),
                "mw": c.get("mw"),
                "charge": comp.get("net_charge_approx"),
                "half_life_h": None,
                "protease": None,
                "aggregation": F.get(c, "developability.aggregation_propensity.value"),
                "developability": F.get(c, "developability.developability_score"),
                "humanization": c.get("humanization_score"),
                "immunogenicity": F.get(c, "scores.immunogenicity_score"),
                "changes": [],
            }
        )
    return {"type": "ranking", "items": items}


def scene_developability(r: Dict[str, Any]) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for c in cands(r):
        v = F.get(c, "developability.developability_score")
        if isinstance(v, (int, float)):
            items.append(
                {
                    "group": "liability scan",
                    "name": c.get("candidate_id"),
                    "value": v,
                    "label": F.get(c, "developability.provenance"),
                    "unit": None,
                    "note": f"{F.get(c, 'developability.n_liabilities')} liabilities",
                }
            )
    comp = F.get(r, f"{BEST}.developability.developability_liabilities.composition") or {}
    for k, v in comp.items():
        if isinstance(v, (int, float)):
            items.append(
                {
                    "group": "CDR-H3 composition",
                    "name": k,
                    "value": v,
                    "label": None,
                    "unit": None,
                    "note": None,
                }
            )
    for k in ("aggregation_propensity", "viscosity_150mgml", "thermal_stability_tm"):
        blk = F.get(r, f"{BEST}.developability.{k}") or {}
        if isinstance(blk, dict) and blk.get("value") is None:
            items.append(
                {
                    "group": "not measured",
                    "name": k,
                    "value": None,
                    "label": blk.get("units"),
                    "unit": blk.get("units"),
                    "note": blk.get("null_reason"),
                }
            )
    return {
        "type": "endpoints",
        "model": F.get(r, f"{S_DV}.method"),
        "n": len(F.get(r, f"{S_DV}.candidates") or []),
        "items": items,
    }


def scene_binding(r: Dict[str, Any]) -> Dict[str, Any]:
    be = F.get(r, f"{S_BA}.binding_energies") or []
    kd = F.get(r, f"{S_BA}.kd_estimates_nm") or []
    unit = F.get(r, f"{S_BA}.binding_energy_units")
    items: List[Dict[str, Any]] = []
    for i, v in enumerate(be):
        if isinstance(v, (int, float)):
            items.append(
                {
                    "group": "VQE binding score",
                    "name": f"#{i + 1}",
                    "value": round(v, 4),
                    "label": unit,
                    "unit": unit,
                    "note": None,
                }
            )
    for i, v in enumerate(kd):
        if isinstance(v, (int, float)):
            items.append(
                {
                    "group": "Kd proxy (uncalibrated)",
                    "name": f"#{i + 1}",
                    "value": v,
                    "label": "kd_estimates_nm",
                    "unit": "nM",
                    "note": None,
                }
            )
    return {
        "type": "endpoints",
        "model": F.get(r, f"{S_BA}.stage"),
        "n": len(be),
        "items": items,
    }


def scene_pk(r: Dict[str, Any]) -> Dict[str, Any]:
    days = F.get(r, "admet.excretion.half_life_days")
    return {
        "type": "pk",
        "half_life_h": round(days * 24, 2) if isinstance(days, (int, float)) else None,
        "bioavailability": F.get(r, "admet.absorption.sc_bioavailability_pct.value"),
        "score": F.get(r, "admet_92_parameters.n_endpoints"),
        "pk": {
            k: F.get(r, f"admet.{k}") or {}
            for k in ("absorption", "distribution", "metabolism", "excretion")
        },
        "pd": {
            k: F.get(r, f"admet_92_parameters.{k}") or {}
            for k in ("absorption", "distribution", "metabolism", "excretion", "toxicity")
        },
    }


def scene_clinic(r: Dict[str, Any]) -> Dict[str, Any]:
    risk = F.get(r, "clinical_trial.clinical_risk") or {}
    parts = []
    for k, name in (
        ("phase_1_to_2", "phase 1 → 2"),
        ("phase_2_to_3", "phase 2 → 3"),
        ("phase_3_to_approval", "phase 3 → approval"),
    ):
        blk = risk.get(k)
        if isinstance(blk, dict) and isinstance(blk.get("value"), (int, float)):
            parts.append(
                {
                    "name": name,
                    "score": blk["value"],
                    "weight": None,
                    "weighted": None,
                    "ci90": blk.get("ci90"),
                }
            )
    return {
        "type": "score",
        "composite": F.get(r, "clinical_trial.clinical_risk.cumulative_approval.value"),
        "parts": parts,
        "klass": r.get("clinical_verdict"),
        "flags": F.get(r, "toxicology.safety_flags") or [],
        "gate": {
            "recommendation": F.get(r, "quantum_cell_validation.recommendation"),
            "all_domains_pass": F.get(r, "quantum_cell_validation.all_domains_pass"),
            "overall_score": F.get(r, "quantum_cell_validation.overall_score"),
            "domain_scores": F.get(r, "quantum_cell_validation.domain_scores") or {},
        },
    }


# ── chapters ───────────────────────────────────────────────────────────────────────
def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    ag = mesh_keys.get("antigen")
    return [
        {
            "id": "run",
            "title": {"es": "El encargo", "en": "The brief"},
            "claims": [
                "pipeline",
                "status",
                "success",
                "target",
                "target_description",
                "indication",
                "antibody_type",
                "input",
                "metadata",
                "elapsed_s",
                "total_time_seconds",
                "report",
                S_RP,
                "enhancements.downloads",
                "enhancements.engine",
            ],
            "scene": scene_cover(r, ag),
            "beats": [
                {
                    "es": "Una corrida del pipeline {pipeline} contra {target_description}, pidiendo un {antibody_type}: un anticuerpo de cadena única, las dos mitades variables unidas en una sola proteína.",
                    "en": "A run of the {pipeline} pipeline against {target_description}, asking for an {antibody_type}: a single-chain antibody, the two variable halves joined into one protein.",
                    "tech": {
                        "es": "versión {md:pipeline_version} · registrada el {md:timestamp} · {total_time_seconds|n1} s de extremo a extremo",
                        "en": "version {md:pipeline_version} · recorded on {md:timestamp} · {total_time_seconds|n1} s end to end",
                    },
                },
                {
                    "es": "La estructura de partida fue {in:pdb_id}, pedida explícitamente en la entrada; la indicación se dejó vacía.",
                    "en": "The starting structure was {in:pdb_id}, explicitly requested in the input; the indication was left empty.",
                    "tech": {
                        "es": "verificación cruzada con Boltz-2: {in:boltz2_crosscheck} · energía libre de unión: {in:compute_binding_free_energy}",
                        "en": "Boltz-2 cross-check: {in:boltz2_crosscheck} · binding free energy: {in:compute_binding_free_energy}",
                    },
                },
                {
                    "es": "Terminó en {status} y llevó {rep:candidates_evaluated} candidatos hasta el informe; el líder es {rep:lead_candidate}.",
                    "en": "It ended in {status} and carried {rep:candidates_evaluated} candidates through to the report; the lead is {rep:lead_candidate}.",
                    "tech": {
                        "es": "{rep:total_simulator_jobs} trabajos de simulador, {rep:total_ibm_jobs} de hardware IBM, {rep:fallback_count} caídas a ruta clásica",
                        "en": "{rep:total_simulator_jobs} simulator jobs, {rep:total_ibm_jobs} IBM hardware jobs, {rep:fallback_count} falls back to the classical path",
                    },
                    "focus": {"stats": True},
                },
                {
                    "es": "La corrida dejó {dl:files|count} archivos descargables bajo la sesión {dl:session_id}.",
                    "en": "The run left {dl:files|count} downloadable files under session {dl:session_id}.",
                    "kind": "note",
                },
                {
                    "es": "Cada número de esta página se lee del resultado de la corrida; lo que ningún capítulo reclama aparece en el anexo de datos.",
                    "en": "Every number on this page is read from the run's result; whatever no chapter claims appears in the data annex.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "antigen",
            "title": {
                "es": "El antígeno, y la única estructura que hay",
                "en": "The antigen, and the only structure there is",
            },
            "claims": [
                S_TA,
                S_SP,
                "target_context",
                "requested_pdb_id",
                "pdb_id",
                "mol_3d",
                "protenix_structure",
            ]
            + _each(
                r,
                "mol_3d",
                "protenix_structure",
                "analyses.mol_3d",
                "analyses.protenix_structure",
                "pdb_id",
            ),
            "scene": scene_antigen(r, ag, meshes),
            "beats": [
                {
                    "es": "El blanco es {ta:target}, tomado de la estructura {ta:pdb_id} con {ta:antigen_length} residuos en la cadena A; el pipeline la considera de drogabilidad {ta:druggability}.",
                    "en": "The target is {ta:target}, taken from structure {ta:pdb_id} with {ta:antigen_length} residues in chain A; the pipeline rates its druggability {ta:druggability}.",
                    "tech": {
                        "es": "origen de la estructura: {ta:structure_source} · contexto del antígeno: {ta:antigen_context_source} · epítopo: {ta:epitope_residues}",
                        "en": "structure source: {ta:structure_source} · antigen context: {ta:antigen_context_source} · epitope: {ta:epitope_residues}",
                    },
                },
                {
                    "es": "Lo que ves es esa estructura, {m3:pdb_id}, dibujada por PyMOL residuo a residuo; llegó por {m3:source}, no la predijo esta corrida.",
                    "en": "What you see is that structure, {m3:pdb_id}, drawn by PyMOL residue by residue; it arrived by {m3:source}, this run did not predict it.",
                    "focus": {"grow": True},
                    "requires_mesh": "antigen",
                    "gap": [f"{S_SP}.predictions[0]", "mol_3d"],
                    "gap_es": "Esta corrida no tiene ninguna estructura predicha que dibujar",
                    "gap_en": "This run has no predicted structure to draw",
                },
                {
                    "es": "Comprobado sobre los átomos: el residuo 12 de la cadena dibujada es una cisteína, que es la mutación G12C que nombra {target_description}.",
                    "en": "Checked on the atoms: residue 12 of the drawn chain is a cysteine, the G12C mutation that {target_description} names.",
                    "kind": "check",
                    "requires_check": "g12c",
                    "focus": {"residue": 12},
                },
                {
                    "es": "Pero lo dibujado es el antígeno que se pidió, no un anticuerpo: ninguna de las cadenas diseñadas aparece en esa estructura, aunque el bloque la marque como {m3:is_antibody}.",
                    "en": "But what is drawn is the antigen that was asked for, not an antibody: neither designed chain appears in that structure, although the block marks it as {m3:is_antibody}.",
                    "kind": "gap",
                    "requires_failed_check": "drawn_is_antibody",
                },
                {
                    "es": "El plegado de los candidatos se intentó con {sp:method} ({sp:model_requested}) sobre {sp:gpu} y falló en los {sp:predictions|count}: {sp:predictions[0].error}.",
                    "en": "Folding the candidates was attempted with {sp:method} ({sp:model_requested}) on {sp:gpu} and failed for all {sp:predictions|count}: {sp:predictions[0].error}.",
                    "tech": {
                        "es": "respuesta del servicio: {sp:predictions[0].response}",
                        "en": "service response: {sp:predictions[0].response}",
                    },
                    "gap": [S_SP],
                    "gap_es": "Sin predicción de estructura",
                    "gap_en": "No structure prediction",
                },
                {
                    "es": "El sitio de unión declarado tampoco señala un epítopo: la comprobación de al lado mide su distancia al centroide de la cadena y cuenta cuántos residuos caen dentro de su esfera de {dk:binding_site.radius} Å.",
                    "en": "Nor does the declared binding site point at an epitope: the check beside this measures how far its centre is from the chain's centroid and counts how many residues fall inside its {dk:binding_site.radius} Å sphere.",
                    "kind": "gap",
                    "requires_failed_check": "site_is_epitope",
                    "focus": {"site": True},
                },
                {
                    "es": "Por eso no hay afinidad anticuerpo-antígeno en esta corrida, y el resultado lo dice con sus palabras: {m3:binding_affinity_honest.null_reason}",
                    "en": "That is why there is no antibody-antigen affinity in this run, and the result says so in its own words: {m3:binding_affinity_honest.null_reason}",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "design",
            "title": {
                "es": "Armazón humano, lazos cuánticos",
                "en": "Human scaffold, quantum loops",
            },
            "claims": [S_IG, S_TG, S_FW, S_CD, "quantum_core_optimization"]
            + _each(
                r,
                "vh_sequence",
                "vl_sequence",
                "vh_germline",
                "vl_germline",
                "cdr_h1",
                "cdr_h2",
                "cdr_h3",
                "cdr_l1",
                "cdr_l2",
                "cdr_l3",
                "cdr_h3_length",
                "vh_length",
                "vl_length",
                "is_vhh",
                "format",
                "mw",
                "vqe_energy",
            ),
            "scene": scene_design(r),
            "beats": [
                {
                    "es": "El armazón no se inventa: se toman las cuatro regiones marco de la línea germinal humana {fw:selected_vh_germline} para la cadena pesada y {fw:selected_vl_germline} para la ligera.",
                    "en": "The scaffold is not invented: the four framework regions are taken from the human germline {fw:selected_vh_germline} for the heavy chain and {fw:selected_vl_germline} for the light one.",
                    "tech": {
                        "es": "razón de la elección: {fw:selection_rationale} · puntuación del marco pesado {fw:vh_score|n2}",
                        "en": "why they were chosen: {fw:selection_rationale} · heavy framework score {fw:vh_score|n2}",
                    },
                    "focus": {"framework": True},
                },
                {
                    "es": "Marcos humanos por decisión, no por casualidad: {fw:selection_note}",
                    "en": "Human frameworks by decision, not by accident: {fw:selection_note}",
                    "kind": "note",
                },
                {
                    "es": "Los seis lazos CDR son lo que cambia entre candidatos: el de {cd:stage} evaluó {cd:total_evaluated} y guardó los {cd:top_cdr_h3_sequences|count} mejores CDR-H3.",
                    "en": "The six CDR loops are what changes between candidates: {cd:stage} evaluated {cd:total_evaluated} and kept the best {cd:top_cdr_h3_sequences|count} CDR-H3 loops.",
                    "tech": {
                        "es": "{cd:n_qubits} cúbits, {cd:n_layers} capas, {cd:shots} disparos · condicionado a la estructura {cd:pdb_id} · trabajo {cd:ibm_job_ids}",
                        "en": "{cd:n_qubits} qubits, {cd:n_layers} layers, {cd:shots} shots · conditioned on structure {cd:pdb_id} · job {cd:ibm_job_ids}",
                    },
                    "focus": {"loops": True},
                },
                {
                    "es": "Las energías variacionales van en {cd:energy_unit}: no son kcal/mol, sólo sirven para ordenar entre sí los lazos de esta corrida.",
                    "en": "The variational energies are in {cd:energy_unit}: they are not kcal/mol, they only order this run's loops against each other.",
                    "kind": "note",
                },
                {
                    "es": "Comprobado aquí: pegando marco y lazos en orden se reconstruye carácter por carácter la cadena pesada y la ligera de los cuatro candidatos.",
                    "en": "Checked here: gluing framework and loops in order rebuilds, character by character, the heavy and light chains of all four candidates.",
                    "kind": "check",
                    "requires_check": "chain_rebuild",
                    "focus": {"mosaic": True},
                },
                {
                    "es": "La palanca cuántica de este pipeline no es química: {qc:lever}, aplicada a {qc:applied_to}, con el núcleo {qc:quantum_optimized_core}.",
                    "en": "This pipeline's quantum lever is not chemistry: {qc:lever}, applied to {qc:applied_to}, with the core {qc:quantum_optimized_core}.",
                    "tech": {"es": "{qc:note}", "en": "{qc:note}"},
                    "focus": {"core": True},
                },
                {
                    "es": "Pero ese núcleo no llegó a todos los candidatos: la comprobación de al lado dice en cuántos lazos diseñados está y de cuáles candidatos falta.",
                    "en": "But that core did not reach every candidate: the check beside this says how many designed loops carry it and which candidates are missing it.",
                    "kind": "gap",
                    "requires_failed_check": "core_graft",
                },
                {
                    "es": "Y los lazos que llegan al final no salen tal cual de esa lista: cada uno se parece a un diseñado con sustituciones encima, y la comprobación dice a cuántas está de su vecino más cercano.",
                    "en": "And the loops that reach the end do not come straight from that list: each resembles a designed one with substitutions on top, and the check says how far each is from its nearest neighbour.",
                    "kind": "gap",
                    "requires_failed_check": "cdr_provenance",
                },
                {
                    "es": "Los dos generadores de secuencias entrenados no estuvieron disponibles, así que los lazos vienen sólo del circuito: {ig:engine} quedó en {ig:reason}.",
                    "en": "Both trained sequence generators were unavailable, so the loops come from the circuit alone: {ig:engine} ended in {ig:reason}.",
                    "tech": {
                        "es": "{tg:engine} ({tg:checkpoint_name}): {tg:reason}",
                        "en": "{tg:engine} ({tg:checkpoint_name}): {tg:reason}",
                    },
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "quantum",
            "title": {"es": "Dónde corrió la parte cuántica", "en": "Where the quantum part ran"},
            "claims": [
                "quantum_backend",
                "backend",
                "execution_mode",
                "quantum_hardware",
                "on_real_quantum_hardware",
                "is_real_hardware",
                "quantum_provenance",
                "ibm_job_ids",
                "simulator_job_ids",
                "fallback_count",
                "enhancements.quantum_cascade",
                S_QS,
            ],
            "scene": scene_quantum(r),
            "beats": [
                {
                    "es": "Nada de esto corrió en hardware cuántico: el sustrato fue {qp:substrate}, en modo {qp:mode}, y hardware real {is_real_hardware}.",
                    "en": "None of this ran on quantum hardware: the substrate was {qp:substrate}, in {qp:mode} mode, and real hardware {is_real_hardware}.",
                    "tech": {"es": "{qp:hardware_note}", "en": "{qp:hardware_note}"},
                    "focus": {"backend": True},
                },
                {
                    "es": "Los identificadores de trabajo lo confirman: {rep:total_simulator_jobs} de simulador y {rep:total_ibm_jobs} de hardware IBM; el primero es {rep:simulator_job_ids[0]}.",
                    "en": "The job identifiers confirm it: {rep:total_simulator_jobs} simulator and {rep:total_ibm_jobs} IBM hardware; the first is {rep:simulator_job_ids[0]}.",
                    "kind": "note",
                },
                {
                    "es": "La secuencia completa también se carga en un estado cuántico: {qs:n_residues} residuos se vuelven {qs:n_qubits} cúbits con codificación {qs:encoding}.",
                    "en": "The whole sequence is also loaded into a quantum state: {qs:n_residues} residues become {qs:n_qubits} qubits with {qs:encoding} encoding.",
                    "tech": {"es": "sobre {qs:backend}", "en": "on {qs:backend}"},
                    "focus": {"register": True},
                },
                {
                    "es": "Comprobado aquí: esos residuos son exactamente la cadena pesada más la ligera del líder, y los cúbits son cinco por residuo.",
                    "en": "Checked here: those residues are exactly the lead's heavy plus light chain, and the qubits are five per residue.",
                    "kind": "check",
                    "requires_check": "seq_state",
                },
                {
                    "es": "Una cascada aparte corrió cuatro algoritmos en {qcas:lane} sobre {qcas:n_qubits} cúbits: QSVM clasifica la molécula como {qcas:algorithms.QSVM.classification} con confianza {qcas:algorithms.QSVM.confidence|n2}.",
                    "en": "A separate cascade ran four algorithms on {qcas:lane} over {qcas:n_qubits} qubits: QSVM classes the molecule as {qcas:algorithms.QSVM.classification} with confidence {qcas:algorithms.QSVM.confidence|n2}.",
                    "tech": {
                        "es": "{qcas:quantum_provenance.substrate} · reutilizado de una corrida previa: {qcas:cached}",
                        "en": "{qcas:quantum_provenance.substrate} · reused from an earlier run: {qcas:cached}",
                    },
                    "focus": {"cascade": True},
                },
                {
                    "es": "Parte de los bloques no se calculó en esta corrida: alguno declara más segundos de los que duró el pipeline entero.",
                    "en": "Some blocks were not computed in this run: one of them declares more seconds than the whole pipeline lasted.",
                    "kind": "gap",
                    "requires_failed_check": "elapsed",
                },
            ],
        },
        {
            "id": "humanness",
            "title": {"es": "¿Se parece a un anticuerpo humano?", "en": "Does it look human?"},
            "claims": [S_HU, S_IM]
            + _each(
                r,
                "humanization_score",
                "immunogenicity_risk",
                "scores.humanization_score",
                "scores.immunogenicity_score",
                "scores.immunogenicity_risk",
                "scores.ada_risk",
                "scores.crs_risk",
            ),
            "scene": scene_humanness(r),
            "beats": [
                {
                    "es": "Un anticuerpo que el paciente reconoce como ajeno deja de funcionar; por eso se puntúa cuán humano parece. El método es {hu:scoring_method} sobre {hu:n_qubits} cúbits.",
                    "en": "An antibody the patient recognises as foreign stops working; that is why humanness is scored. The method is {hu:scoring_method} on {hu:n_qubits} qubits.",
                    "tech": {
                        "es": "referencia: {hu:human_reference} · umbral {hu:threshold|n2} · trabajo {hu:ibm_job_ids}",
                        "en": "reference: {hu:human_reference} · threshold {hu:threshold|n2} · job {hu:ibm_job_ids}",
                    },
                    "focus": {"group": "humanization"},
                },
                {
                    "es": "El número no es identidad germinal: es {hu:score_type}. {hu:interpretation}",
                    "en": "The number is not germline identity: it is {hu:score_type}. {hu:interpretation}",
                    "kind": "note",
                },
                {
                    "es": "La identidad germinal de verdad no está: {hu:germline_identity.null_reason}",
                    "en": "The real germline identity is absent: {hu:germline_identity.null_reason}",
                    "kind": "gap",
                },
                {
                    "es": "El tamizado de inmunogenicidad puntúa el riesgo de epítopo T con el mismo tipo de núcleo cuántico, sobre {im:n_qubits} cúbits, con umbrales {im:risk_threshold_low|n2} y {im:risk_threshold_high|n2}.",
                    "en": "The immunogenicity screen scores T-cell epitope liability with the same kind of quantum kernel, on {im:n_qubits} qubits, with thresholds {im:risk_threshold_low|n2} and {im:risk_threshold_high|n2}.",
                    "tech": {"es": "{im:disclaimer}", "en": "{im:disclaimer}"},
                    "focus": {"group": "immunogenicity"},
                },
                {
                    "es": "El líder queda en riesgo {b:immunogenicity_risk} con puntuación {b:scores.immunogenicity_score|n3}; riesgo de anticuerpos antifármaco {b:scores.ada_risk} y de liberación de citocinas {b:scores.crs_risk}.",
                    "en": "The lead lands at {b:immunogenicity_risk} risk with score {b:scores.immunogenicity_score|n3}; anti-drug antibody risk {b:scores.ada_risk} and cytokine release risk {b:scores.crs_risk}.",
                    "focus": {"lead": True},
                },
                {
                    "es": "Las barras van por posición en el arreglo, no por identificador: en esta corrida un mismo identificador señala dos moléculas distintas según en qué lista se lea.",
                    "en": "The bars are labelled by array position, not by identifier: in this run one identifier points at two different molecules depending on which list you read it in.",
                    "kind": "gap",
                    "requires_failed_check": "id_alignment",
                },
            ],
        },
        {
            "id": "candidates",
            "title": {"es": "Los cuatro que quedaron", "en": "The four that were kept"},
            "claims": [
                "candidates",
                BEST,
                "composite_score",
                "drug_candidate_class",
                "compound_class",
                S_CG,
                S_IT,
                "iterations",
            ],
            "scene": scene_ranking(r),
            "beats": [
                {
                    "es": "El ciclo buscó en un fondo de {cg:pool_searched} secuencias y nombró {cg:num_candidates} identificadores; al informe llegan {rep:candidates_evaluated}.",
                    "en": "The loop searched a pool of {cg:pool_searched} sequences and named {cg:num_candidates} identifiers; {rep:candidates_evaluated} reach the report.",
                    "tech": {
                        "es": "{it:n_iterations} de {it:max_iterations} iteraciones · convergió: {it:converged} · {it:per_iteration[0].n_viable} viables",
                        "en": "{it:n_iterations} of {it:max_iterations} iterations · converged: {it:converged} · {it:per_iteration[0].n_viable} viable",
                    },
                    "focus": {"pool": True},
                },
                {
                    "es": "Gana {b:candidate_id}: {b:vh_length} residuos de cadena pesada y {b:vl_length} de ligera, con un CDR-H3 de {b:cdr_h3_length}, nota compuesta {composite_score|n4} y clase {drug_candidate_class}.",
                    "en": "The winner is {b:candidate_id}: {b:vh_length} heavy-chain residues and {b:vl_length} light-chain, with a {b:cdr_h3_length}-residue CDR-H3, composite score {composite_score|n4} and class {drug_candidate_class}.",
                    "tech": {"es": "{b:scores.composite_note}", "en": "{b:scores.composite_note}"},
                    "focus": {"rank": 1},
                },
                {
                    "es": "Comprobado aquí: el orden del ranking es descendente por nota compuesta y su primero es el mismo candidato que la corrida guarda como líder.",
                    "en": "Checked here: the ranking is in descending composite order and its first entry is the same candidate the run stores as the lead.",
                    "kind": "check",
                    "requires_check": "ranking_order",
                },
                {
                    "es": "La nota compuesta va de {composite_score|n4} a la del último: {rep:ranking[3].composite_score|n4}. Es un orden relativo dentro de esta corrida, no una escala absoluta.",
                    "en": "The composite runs from {composite_score|n4} down to the last one's {rep:ranking[3].composite_score|n4}. It is a relative order within this run, not an absolute scale.",
                    "kind": "note",
                },
                {
                    "es": "La masa que se reporta para cada candidato no es la de su composición de aminoácidos: la comprobación de al lado da las dos cifras y la constante por residuo que las separa.",
                    "en": "The mass reported for each candidate is not that of its amino-acid composition: the check beside this gives both figures and the per-residue constant that separates them.",
                    "kind": "gap",
                    "requires_failed_check": "mass_composition",
                },
                {
                    "es": "Cada candidato arrastra además su propia copia de todos los paneles de aguas abajo, que es de donde sale el tamaño de este resultado.",
                    "en": "Each candidate also carries its own copy of every downstream panel, which is where this result's size comes from.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "developability",
            "title": {"es": "¿Se puede fabricar?", "en": "Can it be manufactured?"},
            "claims": [S_DV]
            + _each(
                r,
                "developability",
                "viability",
                "safety_disqualified",
                "clinical_viable",
                "safety_flags",
            ),
            "scene": scene_developability(r),
            "beats": [
                {
                    "es": "Un anticuerpo que se agrega en el vial no llega a la clínica. El método aquí es {dv:method} sobre {dv:candidates|count} candidatos, buscando motivos de secuencia problemáticos.",
                    "en": "An antibody that aggregates in the vial never reaches the clinic. The method here is {dv:method} over {dv:candidates|count} candidates, looking for problem sequence motifs.",
                    "tech": {
                        "es": "motivos de {b:developability.developability_liabilities.method} · procedencia: {b:developability.provenance}",
                        "en": "motifs from {b:developability.developability_liabilities.method} · provenance: {b:developability.provenance}",
                    },
                    "focus": {"group": "liability scan"},
                },
                {
                    "es": "El líder marca {b:developability.n_liabilities} responsabilidades y puntuación {b:developability.developability_score|n2}, calculada como {b:developability.developability_score_basis}.",
                    "en": "The lead shows {b:developability.n_liabilities} liabilities and a score of {b:developability.developability_score|n2}, computed as {b:developability.developability_score_basis}.",
                    "focus": {"lead": True},
                },
                {
                    "es": "El escaneo mira sólo el CDR-H3: {b:developability.developability_liabilities.composition.length} residuos, carga neta {b:developability.developability_liabilities.composition.net_charge_approx}, pI {b:developability.developability_liabilities.composition.pI|n2} y {b:developability.developability_liabilities.composition.cysteine_count} cisteínas.",
                    "en": "The scan looks only at the CDR-H3: {b:developability.developability_liabilities.composition.length} residues, net charge {b:developability.developability_liabilities.composition.net_charge_approx}, pI {b:developability.developability_liabilities.composition.pI|n2} and {b:developability.developability_liabilities.composition.cysteine_count} cysteines.",
                    "focus": {"group": "CDR-H3 composition"},
                },
                {
                    "es": "Y por mirar sólo ese lazo se le escapan las cisteínas del resto de la cadena: contadas sobre la secuencia entera hay candidatos con un número impar, es decir con un tiol sin pareja que se oxida o forma puentes cruzados.",
                    "en": "And by looking only at that loop it misses the cysteines in the rest of the chain: counted over the whole sequence some candidates come out odd, that is with an unpaired thiol that oxidises or forms cross-links.",
                    "kind": "gap",
                    "requires_failed_check": "free_cys",
                },
                {
                    "es": "Las tres medidas que de verdad deciden la fabricabilidad están vacías: {b:developability.aggregation_propensity.null_reason}",
                    "en": "The three measurements that actually decide manufacturability are empty: {b:developability.aggregation_propensity.null_reason}",
                    "tech": {
                        "es": "viscosidad: {b:developability.viscosity_150mgml.null_reason} · Tm: {b:developability.thermal_stability_tm.null_reason}",
                        "en": "viscosity: {b:developability.viscosity_150mgml.null_reason} · Tm: {b:developability.thermal_stability_tm.null_reason}",
                    },
                    "kind": "gap",
                    "focus": {"group": "not measured"},
                },
                {
                    "es": "El propio paso lo dice: {dv:disclaimer}",
                    "en": "The step itself says so: {dv:disclaimer}",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "binding",
            "title": {
                "es": "La afinidad que no se midió",
                "en": "The affinity that was not measured",
            },
            "claims": [S_BA, "docking"]
            + _each(
                r,
                "docking",
                "analyses.docking",
                "analyses.docking_multi",
                "kd_nM",
                "affinity_rank",
                "kd_calibrated",
                "kd_disclaimer",
                "scores.binding_energy",
                "scores.binding_energy_units",
                "scores.vqe_binding_energy_relative",
                "scores.affinity_rank",
                "scores.kd_nm",
                "scores.kd_nm_uncalibrated_proxy",
                "scores.kd_calibrated",
                "scores.kd_disclaimer",
            ),
            "scene": scene_binding(r),
            "beats": [
                {
                    "es": "El paso {ba:stage} puntúa las {ba:binding_energies|count} secuencias del fondo en {ba:n_qubits} cúbits y devuelve {ba:binding_energy_units}.",
                    "en": "The {ba:stage} step scores the pool's {ba:binding_energies|count} sequences on {ba:n_qubits} qubits and returns {ba:binding_energy_units}.",
                    "tech": {
                        "es": "trabajo {ba:ibm_job_ids} · calibrado a kcal/mol: {ba:calibrated_kcal_mol}",
                        "en": "job {ba:ibm_job_ids} · calibrated to kcal/mol: {ba:calibrated_kcal_mol}",
                    },
                    "focus": {"group": "VQE binding score"},
                },
                {
                    "es": "El líder queda en el puesto {b:scores.affinity_rank} con energía relativa {b:scores.vqe_binding_energy_relative|n4} y un Kd de referencia de {b:scores.kd_nm_uncalibrated_proxy|n4} nM.",
                    "en": "The lead comes in at rank {b:scores.affinity_rank} with relative energy {b:scores.vqe_binding_energy_relative|n4} and a reference Kd of {b:scores.kd_nm_uncalibrated_proxy|n4} nM.",
                    "focus": {"group": "Kd proxy (uncalibrated)"},
                },
                {
                    "es": "Ese Kd no es una afinidad: {b:scores.kd_disclaimer}",
                    "en": "That Kd is not an affinity: {b:scores.kd_disclaimer}",
                    "kind": "note",
                },
                {
                    "es": "El acoplamiento contra el antígeno terminó en {dk:status} pero sin número: el método declarado es {dk:method}.",
                    "en": "Docking against the antigen ended in {dk:status} but with no number: the declared method is {dk:method}.",
                    "tech": {
                        "es": "{dk:kd_nM_honest.null_reason}",
                        "en": "{dk:kd_nM_honest.null_reason}",
                    },
                    "kind": "gap",
                },
                {
                    "es": "Sin estructura del complejo no hay ipTM, y sin ipTM el término de unión desaparece de la nota compuesta: por eso el orden final descansa en un rango ordinal.",
                    "en": "With no complex structure there is no ipTM, and with no ipTM the binding term drops out of the composite: so the final order rests on an ordinal rank.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "admet",
            "title": {"es": "Qué le hace el cuerpo", "en": "What the body does to it"},
            "claims": [S_AP, "admet", "admet_92_parameters", "toxicology", "pharmacology"]
            + _each(
                r,
                "admet",
                "admet_profile",
                "admet_92_parameters",
                "analyses.admet",
                "analyses.admet_92_parameters",
                "analyses.toxicology",
                "toxicology",
                "analyses.pharmacology",
                "pharmacology",
                *_ADMET_FLAT,
            ),
            "scene": scene_pk(r),
            "beats": [
                {
                    "es": "Para un biológico la farmacocinética no se predice molécula a molécula: se toma de la literatura por formato. Ruta {ad:administration_route}, masa {ad:molecular_weight_kda|n1} kDa.",
                    "en": "For a biologic the pharmacokinetics is not predicted molecule by molecule: it is taken from the literature by format. Route {ad:administration_route}, mass {ad:molecular_weight_kda|n1} kDa.",
                    "tech": {"es": "{ad:pk_basis}", "en": "{ad:pk_basis}"},
                    "focus": {"curve": True},
                },
                {
                    "es": "Vida media {ad:excretion.half_life_days|n2} días, aclaramiento {ad:metabolism.clearance_ml_day_kg.value|n1} {ad:metabolism.clearance_ml_day_kg.units}, volumen de distribución {ad:distribution.vd_L.value|n1} L y biodisponibilidad subcutánea {ad:absorption.sc_bioavailability_pct.value|n1}%.",
                    "en": "Half-life {ad:excretion.half_life_days|n2} days, clearance {ad:metabolism.clearance_ml_day_kg.value|n1} {ad:metabolism.clearance_ml_day_kg.units}, volume of distribution {ad:distribution.vd_L.value|n1} L and subcutaneous bioavailability {ad:absorption.sc_bioavailability_pct.value|n1}%.",
                    "tech": {
                        "es": "{ad:excretion.half_life_basis} · reciclaje por FcRn: {ad:excretion.fcrn_recycling}",
                        "en": "{ad:excretion.half_life_basis} · FcRn recycling: {ad:excretion.fcrn_recycling}",
                    },
                    "focus": {"group": "excretion"},
                },
                {
                    "es": "Un anticuerpo no pasa por el citocromo P450 ni se absorbe por boca, y el bloque lo marca así: CYP3A4 {ad:metabolism.cyp3a4}, biodisponibilidad oral {ad:absorption.oral_bioavailability}.",
                    "en": "An antibody does not go through cytochrome P450 and is not absorbed by mouth, and the block marks it so: CYP3A4 {ad:metabolism.cyp3a4}, oral bioavailability {ad:absorption.oral_bioavailability}.",
                    "focus": {"group": "metabolism"},
                },
                {
                    "es": "Aun así un segundo modelo, {a92:model}, corre sobre un SMILES peptídico de la misma molécula y sí devuelve números: hERG {a92:toxicity.herg.value|n3} ({a92:toxicity.herg.interpretation}), AMES {a92:toxicity.ames.value|n3}, daño hepático {a92:toxicity.dili.value|n3}.",
                    "en": "Even so a second model, {a92:model}, runs on a peptide SMILES of the same molecule and does return numbers: hERG {a92:toxicity.herg.value|n3} ({a92:toxicity.herg.interpretation}), AMES {a92:toxicity.ames.value|n3}, liver injury {a92:toxicity.dili.value|n3}.",
                    "tech": {
                        "es": "hERG validado en {a92:toxicity.herg.validation.measured.dataset}: {a92:toxicity.herg.validation.measured.metric} {a92:toxicity.herg.validation.measured.value|n3} sobre {a92:toxicity.herg.validation.measured.n_test} compuestos · {a92:validation_summary.source}",
                        "en": "hERG validated on {a92:toxicity.herg.validation.measured.dataset}: {a92:toxicity.herg.validation.measured.metric} {a92:toxicity.herg.validation.measured.value|n3} over {a92:toxicity.herg.validation.measured.n_test} compounds · {a92:validation_summary.source}",
                    },
                    "focus": {"group": "toxicity"},
                },
                {
                    "es": "Las dos lecturas no pueden ser ambas verdad para la misma molécula, y el bloque además no tiene el tamaño que su nombre anuncia.",
                    "en": "Both readings cannot be true of the same molecule, and the block is also not the size its name announces.",
                    "kind": "gap",
                    "requires_failed_check": "admet_panel",
                },
                {
                    "es": "La toxicología propia del formato termina en {tx:status} y queda en {tx:overall_safety}: riesgo de anticuerpos antifármaco {tx:ada_risk}, de citocinas {tx:cytokine_release_risk}, y toxicidad sobre el propio blanco {tx:on_target_toxicity}.",
                    "en": "The format's own toxicology ends in {tx:status} and stands at {tx:overall_safety}: anti-drug antibody risk {tx:ada_risk}, cytokine risk {tx:cytokine_release_risk}, and on-target toxicity {tx:on_target_toxicity}.",
                    "tech": {"es": "{tx:risk_flag_basis}", "en": "{tx:risk_flag_basis}"},
                },
                {
                    "es": "Lo que no se pudo estimar se dice: {tx:hepatotoxicity_risk.null_reason}",
                    "en": "What could not be estimated is stated: {tx:hepatotoxicity_risk.null_reason}",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "clinic",
            "title": {"es": "La clínica que se supone", "en": "The clinic that is assumed"},
            "claims": [S_CT, "clinical_trial", "clinical_verdict", "quantum_cell_validation"]
            + _each(r, "clinical_trial", "analyses.clinical_trial", "clinical_verdict"),
            "scene": scene_clinic(r),
            "beats": [
                {
                    "es": "El ensayo no se simula molécula a molécula: se rellena una plantilla por formato e indicación. Fase 1 {cl:phase_1.design}, fase 2 {cl:phase_2.design}, fase 3 {cl:phase_3.design}.",
                    "en": "The trial is not simulated molecule by molecule: a template is filled in by format and indication. Phase 1 {cl:phase_1.design}, phase 2 {cl:phase_2.design}, phase 3 {cl:phase_3.design}.",
                    "tech": {
                        "es": "{ct:trial_design_template._note}",
                        "en": "{ct:trial_design_template._note}",
                    },
                    "focus": {"phases": True},
                },
                {
                    "es": "Las probabilidades de paso vienen de tasas publicadas para la cohorte, no de esta molécula: {cl:clinical_risk.phase_1_to_2.value|n3} de fase 1 a 2, {cl:clinical_risk.phase_2_to_3.value|n3} de 2 a 3 y {cl:clinical_risk.phase_3_to_approval.value|n3} de 3 a aprobación.",
                    "en": "The transition probabilities come from published cohort base rates, not from this molecule: {cl:clinical_risk.phase_1_to_2.value|n3} phase 1 to 2, {cl:clinical_risk.phase_2_to_3.value|n3} 2 to 3 and {cl:clinical_risk.phase_3_to_approval.value|n3} 3 to approval.",
                    "tech": {
                        "es": "{cl:clinical_risk.phase_1_to_2.provenance}",
                        "en": "{cl:clinical_risk.phase_1_to_2.provenance}",
                    },
                    "focus": {"bars": True},
                },
                {
                    "es": "Comprobado aquí: multiplicadas una tras otra dan exactamente la probabilidad acumulada de aprobación que la corrida guarda.",
                    "en": "Checked here: multiplied one after another they give exactly the cumulative approval probability the run stores.",
                    "kind": "check",
                    "requires_check": "clinical_chain",
                },
                {
                    "es": "Esa acumulada es {cl:clinical_risk.cumulative_approval.value|n3}, con los límites del 90% en {cl:clinical_risk.cumulative_approval.ci90}.",
                    "en": "That cumulative figure is {cl:clinical_risk.cumulative_approval.value|n3}, with the 90% bounds at {cl:clinical_risk.cumulative_approval.ci90}.",
                    "tech": {
                        "es": "{cl:clinical_risk.disclaimer}",
                        "en": "{cl:clinical_risk.disclaimer}",
                    },
                },
                {
                    "es": "La pauta de dosis no encaja con la farmacocinética de la propia corrida: el intervalo entre dosis es muchas vidas medias, así que entre una y otra no quedaría fármaco.",
                    "en": "The dosing schedule does not fit the run's own pharmacokinetics: the interval between doses is many half-lives, so no drug would remain from one to the next.",
                    "kind": "gap",
                    "requires_failed_check": "dosing",
                },
                {
                    "es": "La validación celular deja {qcv:overall_score|n3} de puntuación global y recomienda {qcv:recommendation}: el dominio de actividad se queda en {qcv:domain_scores.activity|n3} y el de estabilidad genómica en {qcv:domain_scores.genomic_stability|n3}.",
                    "en": "Cell validation leaves an overall score of {qcv:overall_score|n3} and recommends {qcv:recommendation}: the activity domain sits at {qcv:domain_scores.activity|n3} and genomic stability at {qcv:domain_scores.genomic_stability|n3}.",
                    "tech": {
                        "es": "{qcv:validation_status} · {qcv:overall_score_note}",
                        "en": "{qcv:validation_status} · {qcv:overall_score_note}",
                    },
                    "focus": {"gate": True},
                },
                {
                    "es": "Aun así el veredicto es {clinical_verdict}: {cl:verdict}, con ruta regulatoria {cl:regulatory_path}, mientras la probabilidad global de éxito y el número de sujetos siguen sin calcular.",
                    "en": "The verdict is nonetheless {clinical_verdict}: {cl:verdict}, with regulatory path {cl:regulatory_path}, while the overall success probability and the subject count remain uncomputed.",
                    "focus": {"verdict": True},
                },
            ],
        },
    ]


def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One cartoon. The run stores the same structure once per candidate; drawing it
    eleven times would only repeat the same picture."""
    pdb = F.get(r, "mol_3d.protein_pdb") or F.get(r, f"{BEST}.mol_3d.protein_pdb")
    if not F.is_pdb(pdb):
        return []
    return [{"key": "antigen", "pdb": pdb, "label": "mol_3d.protein_pdb"}]


# ── checks: arithmetic and string work redone here, against the run's own data ──────
def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cs = cands(r)
    lead = cs[0] if cs else {}

    # 1 -- the chains are the framework plus the designed loops
    if cs:
        bad = [
            c.get("candidate_id")
            for c in cs
            if rebuild(r, c) != (c.get("vh_sequence"), c.get("vl_sequence"))
        ]
        vh, vl = rebuild(r, lead)
        out.append(
            {
                "id": "chain_rebuild",
                "ok": not bad and bool(vh),
                "es": (
                    f"marco + CDR reconstruyen las {len(cs)} cadenas pesadas ({len(vh)} aa) y ligeras "
                    f"({len(vl)} aa) exactamente"
                    if not bad and vh
                    else f"la reconstrucción NO coincide en: {', '.join(str(x) for x in bad)}"
                ),
                "en": (
                    f"framework + CDRs rebuild all {len(cs)} heavy ({len(vh)} aa) and light "
                    f"({len(vl)} aa) chains exactly"
                    if not bad and vh
                    else f"the rebuild does NOT match for: {', '.join(str(x) for x in bad)}"
                ),
                "paths": [
                    f"{S_FW}.vh_framework_regions",
                    f"{S_FW}.vl_framework_regions",
                    f"{BEST}.vh_sequence",
                    f"{BEST}.vl_sequence",
                ],
            }
        )

    # 2 -- the quantum sequence state is the lead's own chain, five qubits per residue
    nres, nq = F.get(r, f"{S_QS}.n_residues"), F.get(r, f"{S_QS}.n_qubits")
    hl, ll = lead.get("vh_length"), lead.get("vl_length")
    if all(isinstance(x, int) for x in (nres, nq, hl, ll)):
        ok = nres == hl + ll and nq == 5 * nres
        out.append(
            {
                "id": "seq_state",
                "ok": ok,
                "es": f"{hl} + {ll} = {hl + ll} residuos frente a los {nres} del estado cuántico, y {nq} cúbits frente a 5 × {nres} = {5 * nres}",
                "en": f"{hl} + {ll} = {hl + ll} residues against the quantum state's {nres}, and {nq} qubits against 5 × {nres} = {5 * nres}",
                "paths": [
                    f"{S_QS}.n_residues",
                    f"{S_QS}.n_qubits",
                    f"{BEST}.vh_length",
                    f"{BEST}.vl_length",
                ],
            }
        )

    # 3 -- the loops that were kept are the loops that were designed
    tops = [t for t in (F.get(r, f"{S_CD}.top_cdr_h3_sequences") or []) if isinstance(t, str)]
    if cs and tops:
        miss_es, miss_en, n_missing = [], [], 0
        for c in cs:
            if c.get("cdr_h3") in tops:
                continue
            n_missing += 1
            cid = c.get("candidate_id")
            near, dist = nearest_designed(r, c.get("cdr_h3"))
            if near is None:
                miss_es.append(str(cid))
                miss_en.append(str(cid))
            else:
                miss_es.append(
                    f"{cid} está a {dist} "
                    + ("sustitución" if dist == 1 else "sustituciones")
                    + f" de {near}"
                )
                miss_en.append(
                    f"{cid} is {dist} "
                    + ("substitution" if dist == 1 else "substitutions")
                    + f" from {near}"
                )
        out.append(
            {
                "id": "cdr_provenance",
                "ok": not n_missing,
                "es": (
                    f"los {len(cs)} CDR-H3 finales están entre los {len(tops)} diseñados"
                    if not n_missing
                    else f"{n_missing} de {len(cs)} CDR-H3 finales NO están entre los {len(tops)} diseñados: "
                    + "; ".join(miss_es)
                ),
                "en": (
                    f"all {len(cs)} final CDR-H3 loops are among the {len(tops)} designed"
                    if not n_missing
                    else f"{n_missing} of {len(cs)} final CDR-H3 loops are NOT among the {len(tops)} designed: "
                    + "; ".join(miss_en)
                ),
                "paths": [f"{S_CD}.top_cdr_h3_sequences", f"{BEST}.cdr_h3"],
            }
        )

    # 4 -- the QAOA core the run says it grafted into every candidate
    core = F.get(r, "quantum_core_optimization.quantum_optimized_core")
    if isinstance(core, str) and core and cs:
        without = [c.get("candidate_id") for c in cs if core not in str(c.get("cdr_h3") or "")]
        n_top = sum(1 for t in tops if core in t)
        out.append(
            {
                "id": "core_graft",
                "ok": not without,
                "es": (
                    f"el núcleo {core} está en los {len(cs)} CDR-H3 finales y en {n_top} de {len(tops)} diseñados"
                    if not without
                    else f"el núcleo {core} está en {n_top} de {len(tops)} lazos diseñados pero falta en {', '.join(str(x) for x in without)}"
                ),
                "en": (
                    f"the core {core} is in all {len(cs)} final CDR-H3 loops and in {n_top} of {len(tops)} designed ones"
                    if not without
                    else f"the core {core} is in {n_top} of {len(tops)} designed loops but missing from {', '.join(str(x) for x in without)}"
                ),
                "paths": [
                    "quantum_core_optimization.quantum_optimized_core",
                    "quantum_core_optimization.applied_to",
                    f"{BEST}.cdr_h3",
                ],
            }
        )

    # 5 -- do the pool's identifiers point at the pool's scores?
    ids = F.get(r, f"{S_CG}.candidate_ids") or []
    if cs and ids:
        clash_es, clash_en = [], []
        for c in cs:
            pi, cid = pool_index(r, c), c.get("candidate_id")
            if pi is None or cid not in ids:
                continue
            if ids.index(cid) != pi:
                clash_es.append(
                    f"{cid}: sus puntuaciones están en la posición {pi + 1}, su identificador en la {ids.index(cid) + 1}"
                )
                clash_en.append(
                    f"{cid}: its scores sit at position {pi + 1}, its identifier at {ids.index(cid) + 1}"
                )
        out.append(
            {
                "id": "id_alignment",
                "ok": not clash_es,
                "es": (
                    "cada identificador final apunta a la misma posición del fondo que sus puntuaciones"
                    if not clash_es
                    else "el identificador no señala la misma molécula en las dos listas -- "
                    + "; ".join(clash_es)
                ),
                "en": (
                    "each final identifier points at the same pool position as its scores"
                    if not clash_en
                    else "the identifier does not name the same molecule in both lists -- "
                    + "; ".join(clash_en)
                ),
                "paths": [
                    f"{S_CG}.candidate_ids",
                    f"{S_HU}.humanization_scores",
                    f"{S_CD}.vqe_energies",
                ],
            }
        )

    # 6 -- the mass that is reported against the mass of the written sequence
    if cs:
        offenders, constant, det_es, det_en = [], 0, "", ""
        for c in cs:
            seq = f"{c.get('vh_sequence') or ''}{c.get('vl_sequence') or ''}"
            got, want = c.get("mw"), composition_mass(seq)
            if not isinstance(got, (int, float)) or want is None:
                continue
            if abs(got - want) / want > 0.005:
                offenders.append(c.get("candidate_id"))
            if got == 110 * len(seq):
                constant += 1
            if not det_es:
                det_es = (
                    f"{c.get('candidate_id')} registra {got:.0f} Da, su composición pesa {want:.0f} Da, "
                    f"y 110 Da × {len(seq)} residuos = {110 * len(seq)} Da exactos"
                )
                det_en = (
                    f"{c.get('candidate_id')} records {got:.0f} Da, its composition weighs {want:.0f} Da, "
                    f"and 110 Da × {len(seq)} residues = exactly {110 * len(seq)} Da"
                )
        out.append(
            {
                "id": "mass_composition",
                "ok": not offenders,
                "es": (
                    "la masa registrada coincide con la de la composición de la secuencia"
                    if not offenders
                    else f"la masa de {len(offenders)} de {len(cs)} candidatos se aparta más de 0.5% de la de su "
                    f"composición, y los {constant} son exactamente 110 Da por residuo: {det_es}"
                ),
                "en": (
                    "the recorded mass matches the mass of the sequence's composition"
                    if not offenders
                    else f"the mass of {len(offenders)} of {len(cs)} candidates is more than 0.5% away from its "
                    f"composition's, and all {constant} are exactly 110 Da per residue: {det_en}"
                ),
                "paths": [f"{BEST}.mw", f"{BEST}.vh_sequence", f"{BEST}.vl_sequence"],
            }
        )

    # 7 -- cysteines beyond the germline pair
    if cs:
        odd = []
        for c in cs:
            extra = free_cys(r, c)
            n = extra.get("vh", 0) + extra.get("vl", 0)
            if n % 2 == 1:
                odd.append(f"{c.get('candidate_id')} (+{n})")
        out.append(
            {
                "id": "free_cys",
                "ok": not odd,
                "es": (
                    "ningún candidato añade cisteínas sueltas a las del marco germinal"
                    if not odd
                    else f"{len(odd)} de {len(cs)} candidatos añaden un número impar de cisteínas a las 4 del marco: "
                    + ", ".join(odd)
                    + "; el escaneo de responsabilidades sólo mira el CDR-H3 y no las ve"
                ),
                "en": (
                    "no candidate adds loose cysteines to the germline framework's"
                    if not odd
                    else f"{len(odd)} of {len(cs)} candidates add an odd number of cysteines to the framework's 4: "
                    + ", ".join(odd)
                    + "; the liability scan looks only at CDR-H3 and does not see them"
                ),
                "paths": [
                    f"{BEST}.vh_sequence",
                    f"{BEST}.cdr_h2",
                    f"{BEST}.developability.developability_liabilities.composition.cysteine_count",
                ],
            }
        )

    # 8, 9, 10 -- what the drawn structure actually is
    dr = drawn(r)
    if dr:
        vh, vl = lead.get("vh_sequence") or "", lead.get("vl_sequence") or ""
        found = bool(vh and vh in dr["seq"]) or bool(vl and vl in dr["seq"])
        out.append(
            {
                "id": "drawn_is_antibody",
                "ok": found,
                "es": (
                    f"la cadena dibujada ({dr['n']} residuos) contiene la secuencia del candidato"
                    if found
                    else f"la cadena dibujada tiene {dr['n']} residuos y no contiene ni la pesada ({len(vh)} aa) "
                    f"ni la ligera ({len(vl)} aa); la misma estructura está guardada {dr['copies']} veces"
                ),
                "en": (
                    f"the drawn chain ({dr['n']} residues) contains the candidate's sequence"
                    if found
                    else f"the drawn chain has {dr['n']} residues and contains neither the heavy ({len(vh)} aa) "
                    f"nor the light ({len(vl)} aa) chain; the same structure is stored {dr['copies']} times"
                ),
                "paths": ["mol_3d.protein_pdb", "mol_3d.is_antibody", f"{BEST}.vh_sequence"],
            }
        )

        mut = next((x for x in dr["res"] if x["resi"] == "12"), None)
        if mut:
            out.append(
                {
                    "id": "g12c",
                    "ok": mut["resn"] == "CYS",
                    "es": f"el residuo 12 de la cadena dibujada es {mut['resn']}, y la corrida declara {r.get('target_description')}",
                    "en": f"residue 12 of the drawn chain is {mut['resn']}, and the run declares {r.get('target_description')}",
                    "paths": ["mol_3d.protein_pdb", "target_description"],
                }
            )

        s = site(r)
        if all(
            isinstance(s.get(k), (int, float))
            for k in ("center_x", "center_y", "center_z", "radius")
        ):
            c = [s["center_x"], s["center_y"], s["center_z"]]
            d = math.dist(c, dr["centroid"])
            inside = sum(1 for x in dr["res"] if math.dist(x["p"], c) <= s["radius"])
            ok = d > 2.0 and inside < dr["n"] * 0.5
            out.append(
                {
                    "id": "site_is_epitope",
                    "ok": ok,
                    "es": (
                        f"el sitio declarado está a {d:.1f} Å del centroide y su esfera de {s['radius']} Å "
                        f"selecciona {inside} de {dr['n']} residuos"
                    ),
                    "en": (
                        f"the declared site sits {d:.1f} Å from the centroid and its {s['radius']} Å sphere "
                        f"selects {inside} of {dr['n']} residues"
                    ),
                    "paths": [
                        "docking.binding_site",
                        "mol_3d.protein_pdb",
                        f"{S_TA}.epitope_residues",
                    ],
                }
            )

    # 11 -- the ranking is the order it says it is
    ranking = [x for x in (F.get(r, "report.ranking") or []) if isinstance(x, dict)]
    scores = [x.get("composite_score") for x in ranking]
    if len(ranking) > 1 and all(isinstance(x, (int, float)) for x in scores):
        sorted_ok = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
        lead_ok = (
            ranking[0].get("candidate_id")
            == F.get(r, "report.lead_candidate")
            == lead.get("candidate_id")
        )
        out.append(
            {
                "id": "ranking_order",
                "ok": sorted_ok and lead_ok,
                "es": (
                    f"las {len(ranking)} notas bajan de {scores[0]:.4f} a {scores[-1]:.4f} y el primero es "
                    f"{ranking[0].get('candidate_id')}, el mismo que best_candidate"
                ),
                "en": (
                    f"the {len(ranking)} scores fall from {scores[0]:.4f} to {scores[-1]:.4f} and the first is "
                    f"{ranking[0].get('candidate_id')}, the same as best_candidate"
                ),
                "paths": ["report.ranking", "report.lead_candidate", f"{BEST}.candidate_id"],
            }
        )

    # 12 -- the clinical chain multiplies out
    risk = F.get(r, "clinical_trial.clinical_risk") or {}
    ps = [
        F.get(risk, f"{k}.value") for k in ("phase_1_to_2", "phase_2_to_3", "phase_3_to_approval")
    ]
    cum = F.get(risk, "cumulative_approval.value")
    if all(isinstance(x, (int, float)) for x in ps) and isinstance(cum, (int, float)):
        prod = ps[0] * ps[1] * ps[2]
        out.append(
            {
                "id": "clinical_chain",
                "ok": abs(prod - cum) <= 0.001,
                "es": f"{ps[0]} × {ps[1]} × {ps[2]} = {prod:.5f}, y la acumulada guardada es {cum}",
                "en": f"{ps[0]} × {ps[1]} × {ps[2]} = {prod:.5f}, and the stored cumulative figure is {cum}",
                "paths": ["clinical_trial.clinical_risk"],
            }
        )

    # 13 -- the ADMET panel against its own name and its own counters
    a92 = F.get(r, "admet_92_parameters") or {}
    if a92:
        real = 0
        for grp in ("absorption", "distribution", "metabolism", "excretion", "toxicity"):
            g = a92.get(grp) or {}
            real += sum(
                1
                for v in g.values()
                if isinstance(v, dict) and isinstance(v.get("value"), (int, float))
            )
        declared = a92.get("n_endpoints")
        adv, cnt = F.get(r, "admet.advertised_panel"), F.get(r, "admet.parameters_count")
        ok = real == declared == adv == cnt
        out.append(
            {
                "id": "admet_panel",
                "ok": ok,
                "es": (
                    f"el bloque se llama admet_92_parameters, declara {declared} puntos finales, "
                    f"{real} traen un valor real, el panel anunciado es {adv} y parameters_count dice {cnt}"
                ),
                "en": (
                    f"the block is named admet_92_parameters, declares {declared} endpoints, "
                    f"{real} carry a real value, the advertised panel is {adv} and parameters_count says {cnt}"
                ),
                "paths": [
                    "admet_92_parameters.n_endpoints",
                    "admet.advertised_panel",
                    "admet.parameters_count",
                ],
            }
        )

    # 14 -- the dosing interval against the half-life the same run recorded
    days = F.get(r, "clinical_trial.phase_1.pk_half_life_days")
    every = {"QD": 1.0, "BID": 0.5, "Q2D": 2.0, "QW": 7.0, "Q2W": 14.0, "Q3W": 21.0, "Q4W": 28.0}
    iv = every.get(str(F.get(r, "clinical_trial.phase_1.dosing_interval") or "").upper())
    if isinstance(days, (int, float)) and days > 0 and iv:
        n = iv / days
        out.append(
            {
                "id": "dosing",
                "ok": n <= 5,
                "es": (
                    f"la pauta {F.get(r, 'clinical_trial.phase_1.dosing_interval')} son {iv:.0f} días "
                    f"y la vida media registrada {days} días: {n:.0f} vidas medias entre dosis"
                ),
                "en": (
                    f"the {F.get(r, 'clinical_trial.phase_1.dosing_interval')} schedule is {iv:.0f} days "
                    f"and the recorded half-life {days} days: {n:.0f} half-lives between doses"
                ),
                "paths": [
                    "clinical_trial.phase_1.dosing_interval",
                    "clinical_trial.phase_1.pk_half_life_days",
                    "admet.excretion.half_life_days",
                ],
            }
        )

    # 15 -- nothing inside the run may take longer than the run
    total = r.get("total_time_seconds")
    if isinstance(total, (int, float)):
        longer = [
            (p, v)
            for p, v in F.flatten(r)
            if p.endswith("elapsed_s")
            and isinstance(v, (int, float))
            and v > total
            and not p.startswith("candidates")
        ]
        out.append(
            {
                "id": "elapsed",
                "ok": not longer,
                "es": (
                    f"ningún bloque declara más de los {total} s que duró la corrida"
                    if not longer
                    else f"la corrida duró {total} s pero {longer[0][0]} declara {longer[0][1]} s"
                ),
                "en": (
                    f"no block declares more than the {total} s the run lasted"
                    if not longer
                    else f"the run lasted {total} s but {longer[0][0]} declares {longer[0][1]} s"
                ),
                "paths": ["total_time_seconds"] + ([longer[0][0]] if longer else []),
            }
        )

    return out


# MOLEVERA / BIOQL
