"""
Artifact model for the cross-modality comparison pipeline (`modality_comparison`).

This pipeline does not have stages: it runs one full discovery pipeline per
therapeutic modality against the same target, and then tries to lay their
numbers side by side. The interesting part is therefore not "what did each arm
do" but "which of these numbers may honestly be compared at all", so the report
follows that: the axis table first, then the handful of measurements that really
were produced by the same code on both leads, then the index built from them and
the verdict the pipeline refuses to give -- and only then a chapter per arm.

Everything the page states about comparability is re-derived here from the run's
own table rather than taken on trust: the aligned/partial axis counts are
recounted, each lead's molecular weight is recomputed from its own sequence, the
hydrophobic 9-mer scan is re-run, the cross-modality index is rebuilt from its
three descriptor terms, and the provenance of every ipTM is traced back to the
arm that produced it. Five of those checks reproduce the run exactly. The rest
fail, and the sentences they gate say plainly what does not add up -- most of
all that the one axis this run calls "fully comparable", structure pLDDT, is
null on both sides although both arms recorded a pLDDT from the same predictor.

MOLEVERA / BIOQL
"""

import math
from typing import Any, Dict, List, Optional, Tuple

try:
    from .. import facts as F
except ImportError:  # loaded standalone, by file path, outside the package
    from artifact_engine import facts as F

PIPELINE = "modality_comparison"
TITLE = {"es": "Comparación de modalidades", "en": "Modality comparison"}

CMP = "comparison"
AXES = f"{CMP}.axes"
AP = f"{CMP}.alignment_provenance"
IX = f"{CMP}.cross_modality_insilico_composite"
PEP, ANT = "arms.peptide", "arms.antibody"

ALIASES = {
    "c": CMP,
    "ax": AXES,
    "ap": AP,
    "ix": IX,
    "p": PEP,
    "a": ANT,
    "pb": f"{PEP}.best_candidate",
    "ab": f"{ANT}.best_candidate",
    "ps": f"{PEP}.stages",
    "asg": f"{ANT}.stages",
    "pv": "provenance.peptide",
    "av": "provenance.antibody",
}

# Average residue masses (Da) -- the same convention Biopython's ProtParam uses,
# so a molecular weight the run published from a sequence can be re-derived here.
AVG_MASS = {
    "A": 71.0788,
    "R": 156.1875,
    "N": 114.1038,
    "D": 115.0886,
    "C": 103.1388,
    "E": 129.1155,
    "Q": 128.1307,
    "G": 57.0519,
    "H": 137.1411,
    "I": 113.1594,
    "L": 113.1594,
    "K": 128.1741,
    "M": 131.1926,
    "F": 147.1766,
    "P": 97.1167,
    "S": 87.0782,
    "T": 101.1051,
    "W": 186.2132,
    "Y": 163.1760,
    "V": 99.1326,
}
WATER = 18.01528
# the hydrophobic set the shared 9-mer epitope scan uses
HYDRO = set("LIVFWMA")

THREE_TO_ONE = {
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
    "SEC": "U",
    "PYL": "O",
}

# How the published cross-modality index normalises each descriptor before the
# equal-weighted mean. Keyed by the term name the run itself records in
# `included_axes`, so a term this model does not know about disables the check
# rather than producing a wrong verdict.
_TERM_AXIS = {
    "hydrophobicity": "biophys_hydrophobicity_gravy",
    "stability": "biophys_instability_index",
    "net_charge": "biophys_net_charge_pH7_4",
    "complex_iptm": "complex_iptm_esmfold2",
    "complex_ptm": "complex_ptm_esmfold2",
}
_TERM_NORM = {
    "hydrophobicity": lambda v: 1 - (v + 2) / 4,
    "stability": lambda v: 1.0 if v < 40 else 1 - (v - 40) / 60,
    "net_charge": lambda v: 1 - abs(v) / 15,
    "complex_iptm": lambda v: v,
    "complex_ptm": lambda v: v,
}
# the terms that describe a folded structure rather than a bare sequence
_FOLD_TERMS = {"complex_iptm", "complex_ptm", "structure_plddt"}

ARM_ES = {"peptide": "péptido", "antibody": "anticuerpo"}
ARM_EN = {"peptide": "peptide", "antibody": "antibody"}


# ── identity ───────────────────────────────────────────────────────────────────────
def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    if str(r.get("pipeline", "")) == PIPELINE:
        return True
    # a comparison run is the only one carrying an axis table plus one arm per modality
    return (
        isinstance(r.get(CMP), dict)
        and isinstance(r[CMP].get("axes"), list)
        and isinstance(r.get("arms"), dict)
        and isinstance(r.get("compared_modalities"), list)
    )


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("result"), dict):
        inner = result["result"]
        if isinstance(inner.get(CMP), dict) or isinstance(inner.get("arms"), dict):
            return inner
    return result


def subject(r: Dict[str, Any]) -> str:
    mods = [str(m) for m in (r.get("compared_modalities") or []) if m]
    head = " vs ".join(mods) if mods else "modalities"
    tail = " · ".join(str(x) for x in (r.get("target"), r.get("indication")) if x)
    return f"{head} → {tail}" if tail else head


# ── small helpers on the run ───────────────────────────────────────────────────────
def _num(v: Any) -> Optional[float]:
    """A finite number, or None. NaN reaches this run's JSON, so it is filtered."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return None if math.isnan(v) or math.isinf(v) else float(v)


def arms(r: Dict[str, Any]) -> List[str]:
    """The modality names this run actually carries an arm for, in its own order."""
    named = [str(m) for m in (r.get("compared_modalities") or []) if isinstance(m, str)]
    present = [m for m in named if isinstance(F.get(r, f"arms.{m}"), dict)]
    if present:
        return present
    got = F.get(r, "arms")
    return [k for k in got if isinstance(k, str) and "." not in k] if isinstance(got, dict) else []


def axis_list(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [a for a in (F.get(r, AXES) or []) if isinstance(a, dict)]


def axis_index(r: Dict[str, Any], name: str) -> Optional[int]:
    for i, a in enumerate(axis_list(r)):
        if a.get("axis") == name:
            return i
    return None


def axis_value(r: Dict[str, Any], name: str, arm: str) -> Optional[float]:
    i = axis_index(r, name)
    return None if i is None else _num(F.get(r, f"{AXES}[{i}].{arm}.value"))


def lead_sequence(r: Dict[str, Any], arm: str) -> str:
    """The sequence the shared descriptors were computed on, rebuilt the same way:
    the peptide's own sequence, or the antibody's heavy chain followed by its light."""
    b = F.get(r, f"arms.{arm}.best_candidate")
    if not isinstance(b, dict):
        return ""
    if isinstance(b.get("sequence"), str):
        return b["sequence"]
    parts = [b.get("vh_sequence") or b.get("heavy_chain_sequence"), b.get("vl_sequence")]
    return "".join(p for p in parts if isinstance(p, str))


def _canon(seq: Any) -> str:
    return "".join(c for c in str(seq or "").upper() if c in AVG_MASS)


def mass_of(seq: Any) -> Optional[float]:
    s = _canon(seq)
    return round(sum(AVG_MASS[c] for c in s) + WATER, 1) if s else None


def epitope_scan(seq: Any) -> Optional[Dict[str, Any]]:
    """The run's own hydrophobic 9-mer scan, re-run here: a window counts when at
    least five of its nine residues are in LIVFWMA."""
    s = _canon(seq)
    n = len(s) - 9
    if n <= 0:
        return None
    hits = sum(1 for i in range(n) if sum(1 for a in s[i : i + 9] if a in HYDRO) >= 5)
    return {"epitope_count": hits, "scan_length": n, "epitope_density": round(hits / n, 4)}


def field(path: str, values: List[Optional[float]]) -> str:
    """A `{path}` template whose precision suits the magnitudes actually in the run:
    four significant figures by default, one decimal once the numbers are large
    enough that four figures would round them away."""
    mags = [abs(v) for v in values if v is not None]
    return "{%s|n1}" % path if mags and max(mags) >= 1000 else "{%s}" % path


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def index_terms(r: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
    """Rebuild the cross-modality index term by term. Returns (terms, unknown terms)."""
    included = [t for t in (F.get(r, f"{IX}.included_axes") or []) if isinstance(t, str)]
    terms: Dict[str, Dict[str, float]] = {}
    unknown: List[str] = []
    for t in included:
        axis, norm = _TERM_AXIS.get(t), _TERM_NORM.get(t)
        if not axis or not norm:
            unknown.append(t)
            continue
        cell: Dict[str, float] = {}
        for arm in arms(r):
            v = axis_value(r, axis, arm)
            if v is None:
                break
            cell[arm] = _clamp01(norm(v))
        if len(cell) == len(arms(r)) and cell:
            terms[t] = cell
        else:
            unknown.append(t)
    return terms, unknown


def cdr_spans(r: Dict[str, Any], mesh: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Locate each declared CDR on the modelled chain by searching for its exact
    sequence, so a loop is only drawn where the model really contains it."""
    if not mesh or not mesh.get("res"):
        return []
    one = "".join(THREE_TO_ONE.get(x.get("resn", ""), "X") for x in mesh["res"])
    out: List[Dict[str, Any]] = []
    b = F.get(r, f"{ANT}.best_candidate") or {}
    for key in ("cdr_h1", "cdr_h2", "cdr_h3", "cdr_l1", "cdr_l2", "cdr_l3"):
        s = b.get(key)
        if isinstance(s, str) and len(s) >= 5:
            i = one.find(s.upper())
            if i >= 0:
                out.append({"name": key.upper().replace("_", "-"), "from": i, "to": i + len(s)})
    return out


def _at(mesh: Optional[Dict[str, Any]], i: int) -> Optional[List[float]]:
    res = (mesh or {}).get("res") or []
    return res[i].get("p") if 0 <= i < len(res) else None


# ── scenes ─────────────────────────────────────────────────────────────────────────
def scene_cover(r: Dict[str, Any], mesh_key: Optional[str]) -> Dict[str, Any]:
    ax = axis_list(r)
    aligned = F.get(r, f"{AP}.aligned_axes") or []
    elapsed = _num(r.get("elapsed_s"))
    return {
        "type": "cover",
        "mesh": mesh_key,
        "stats": [
            {"es": "Diana", "en": "Target", "value": r.get("target"), "path": "target"},
            {
                "es": "Indicación",
                "en": "Indication",
                "value": r.get("indication"),
                "path": "indication",
            },
            {
                "es": "Modalidades",
                "en": "Modalities",
                "value": len(arms(r)),
                "path": "compared_modalities",
            },
            {"es": "Ejes", "en": "Axes", "value": len(ax), "path": AXES},
            {
                "es": "Ejes alineados",
                "en": "Aligned axes",
                "value": len(aligned),
                "path": f"{AP}.aligned_axes",
            },
            {
                "es": "Duración",
                "en": "Wall time",
                "value": round(elapsed / 60.0, 1) if elapsed else None,
                "unit": "min",
                "path": "elapsed_s",
            },
        ],
    }


def scene_axes(r: Dict[str, Any]) -> Dict[str, Any]:
    """One bar per axis: how many arms produced a number for it, out of how many
    arms ran. Green when the run marks the axis genuinely aligned."""
    names = arms(r)
    rules = []
    for a in axis_list(r):
        filled = sum(1 for m in names if _num(F.get(a, f"{m}.value")) is not None)
        rules.append(
            {
                "name": str(a.get("axis")),
                "value": filled,
                "limit": max(1, len(names)),
                "op": ">=",
                "pass": a.get("aligned") is True,
            }
        )
    return {
        "type": "rules",
        "rules": rules,
        "violations": sum(1 for x in rules if not x["pass"]),
        "drug_like": None,
        "brenk": len(F.get(r, f"{AP}.partial_axes") or []),
        "pains": None,
    }


def scene_shared(r: Dict[str, Any]) -> Dict[str, Any]:
    """The measurements produced by the same code on both leads, each arm's value
    scaled against the largest magnitude on that axis so the bars are readable."""
    names = arms(r)
    shared = [a for a in axis_list(r) if a.get("aligned") is True]
    items = []
    for a in shared:
        vals = {m: _num(F.get(a, f"{m}.value")) for m in names}
        top = max((abs(v) for v in vals.values() if v is not None), default=0.0) or 1.0
        for m in names:
            v = vals[m]
            if v is None:
                continue
            items.append(
                {
                    "group": str(a.get("axis")),
                    "name": f"{ARM_EN.get(m, m)} {a.get('axis')} {v:g}",
                    "value": round(abs(v) / top, 4),
                    "label": f"{v:g}",
                    "unit": a.get("unit"),
                    "note": a.get("method") or a.get("alignment_note"),
                }
            )
    return {
        "type": "endpoints",
        "model": F.get(r, f"{AXES}[0].method") or "same method on both leads",
        "n": len(items),
        "items": items,
    }


def scene_index(r: Dict[str, Any]) -> Dict[str, Any]:
    names = arms(r)
    vals = [(m, _num(F.get(r, f"{IX}.{m}"))) for m in names]
    ranked = sorted([(m, v) for m, v in vals if v is not None], key=lambda kv: -kv[1])
    return {
        "type": "ranking",
        "items": [
            {"rank": i + 1, "seq": ARM_EN.get(m, m), "score": v} for i, (m, v) in enumerate(ranked)
        ],
    }


def scene_variants(r: Dict[str, Any]) -> Dict[str, Any]:
    """Every peptide candidate the arm kept, with the single-residue changes it
    carries re-derived from the sequence it came from."""
    out = []
    for i, c in enumerate(F.get(r, f"{PEP}.candidates") or []):
        if not isinstance(c, dict):
            continue
        seq, orig = c.get("sequence"), c.get("original_sequence")
        if not isinstance(seq, str) or not _canon(seq) or len(_canon(seq)) != len(seq):
            continue  # a SMILES string in the sequence slot is not a peptide
        changes = []
        if isinstance(orig, str) and len(orig) == len(seq):
            changes = [
                {"pos": k + 1, "from": x, "to": y, "label": f"{x}{k + 1}{y}"}
                for k, (x, y) in enumerate(zip(orig, seq))
                if x != y
            ]
        out.append(
            {
                "original": orig if isinstance(orig, str) else seq,
                "optimized": seq,
                "score": _num(c.get("composite_score")) or _num(c.get("optimization_score")),
                "changes": changes,
                "path": f"{PEP}.candidates[{i}]",
            }
        )
    return {"type": "variants", "variants": out, "total": len(out), "history": []}


def scene_pep3d(r: Dict[str, Any], key: Optional[str], meshes: Dict[str, Any]) -> Dict[str, Any]:
    """The folded peptide, with the mutation it carries labelled at its real
    position -- the coordinate comes from the drawn structure, nothing else."""
    mesh = meshes.get(key or "")
    ann = []
    seq, orig = (
        F.get(r, f"{PEP}.best_candidate.sequence"),
        F.get(r, f"{PEP}.best_candidate.original_sequence"),
    )
    if mesh and isinstance(seq, str) and isinstance(orig, str) and len(seq) == len(orig):
        for k, (x, y) in enumerate(zip(orig, seq)):
            p = _at(mesh, k)
            if x != y and p:
                ann.append({"text": f"{x}{k + 1}{y}", "pos": p})
    return {
        "type": "cartoon",
        "mesh": key,
        "domains": [],
        "receptors": [str(r.get("target"))] if r.get("target") else [],
        "annotations": ann,
    }


def scene_binders(r: Dict[str, Any]) -> Dict[str, Any]:
    """Every antibody candidate the arm reported, by the confidence of its own
    predicted structure."""
    bs = []
    for c in F.get(r, f"{ANT}.candidates") or []:
        if not isinstance(c, dict):
            continue
        vh, vl = _num(c.get("vh_length")), _num(c.get("vl_length"))
        bs.append(
            {
                "id": c.get("candidate_id"),
                "len": int((vh or 0) + (vl or 0)) or None,
                "plddt": _num(F.get(c, "protenix_structure.plddt")),
                "iptm": _num(F.get(c, "scores.iptm")),
            }
        )
    plddts = [b["plddt"] for b in bs if b["plddt"] is not None]
    iptms = [b["iptm"] for b in bs if b["iptm"] is not None]
    return {
        "type": "binders",
        "binders": bs,
        "best_plddt": max(plddts) if plddts else None,
        "best_ipae": max(iptms) if iptms else None,
        "gpu": F.get(r, f"{ANT}.protenix_structure.gpu"),
    }


def scene_fv(r: Dict[str, Any], key: Optional[str], meshes: Dict[str, Any]) -> Dict[str, Any]:
    mesh = meshes.get(key or "")
    doms = cdr_spans(r, mesh)
    ann = []
    for d in doms:
        p = _at(mesh, (d["from"] + d["to"]) // 2)
        if p:
            ann.append({"text": d["name"], "pos": p})
    return {
        "type": "cartoon",
        "mesh": key,
        "domains": doms,
        "receptors": [x for x in (F.get(r, f"{ANT}.pdb_id"),) if x],
        "annotations": ann,
    }


def scene_safety(r: Dict[str, Any]) -> Dict[str, Any]:
    """Safety and trial numbers from both arms, on the 0-1 scale each one uses."""
    items = []

    def add(group, name, value, unit=None, note=None, label=None):
        v = _num(value)
        if v is not None:
            items.append(
                {
                    "group": group,
                    "name": name,
                    "value": v,
                    "label": label,
                    "unit": unit,
                    "note": note,
                }
            )

    add(
        "peptide",
        "peptide toxicology",
        F.get(r, f"{PEP}.toxicology.overall_score"),
        note=F.get(r, f"{PEP}.toxicology.method"),
        label=F.get(r, f"{PEP}.toxicology.overall_safety"),
    )
    add(
        "peptide",
        "peptide approval",
        F.get(r, f"{PEP}.clinical_trial.regulatory.overall_success_probability"),
        note=F.get(r, f"{PEP}.clinical_trial.method"),
    )
    add(
        "peptide",
        "peptide composite",
        F.get(r, f"{PEP}.composite_score"),
        label=F.get(r, f"{PEP}.drug_candidate_class"),
    )
    add(
        "antibody",
        "antibody developability",
        F.get(r, f"{ANT}.best_candidate.developability.developability_score"),
        note=F.get(r, f"{ANT}.best_candidate.viability.developability_caveat"),
    )
    add(
        "antibody",
        "antibody immunogenicity",
        F.get(r, f"{ANT}.best_candidate.scores.immunogenicity_score"),
        label=F.get(r, f"{ANT}.best_candidate.immunogenicity_risk"),
        note=F.get(r, f"{ANT}.stages.immunogenicity_screening.disclaimer"),
    )
    add(
        "antibody",
        "antibody approval",
        F.get(r, f"{ANT}.clinical_trial.overall_success_probability"),
        note=F.get(r, f"{ANT}.clinical_trial.regulatory_path"),
    )
    add(
        "antibody",
        "antibody composite",
        F.get(r, f"{ANT}.composite_score"),
        label=F.get(r, f"{ANT}.drug_candidate_class"),
    )
    return {
        "type": "endpoints",
        "model": "in-silico, uncalibrated",
        "n": len(items),
        "items": items,
    }


def scene_quantum(r: Dict[str, Any]) -> Dict[str, Any]:
    h = F.get(r, f"{ANT}.stages.quantum_real_hamiltonian") or {}
    return {
        "type": "quantum",
        "n_qubits": h.get("n_qubits"),
        "n_terms": h.get("n_terms"),
        "n_contacts": h.get("n_contacts"),
        "n_residues": h.get("n_residues"),
        "energy": h.get("vqe_energy_Ha"),
        "reference": h.get("reference_energy_Ha"),
        "backend": h.get("lane") or h.get("backend"),
        "algorithms": [
            k
            for k in ("quantum_real_hamiltonian", "ewf_sqd", "quantum_sequence_state")
            if isinstance(F.get(r, f"{ANT}.stages.{k}"), dict)
        ],
    }


# ── generated beats ────────────────────────────────────────────────────────────────
def axis_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One sentence per axis of the run's own table, worded by how comparable the
    run itself says that axis is. An axis with no number on some arm becomes a gap
    that quotes the table's own note for it."""
    names = arms(r)
    out: List[Dict[str, Any]] = []
    for i, a in enumerate(axis_list(r)):
        name = str(a.get("axis") or "")
        if not name:
            continue
        vals = [_num(F.get(a, f"{m}.value")) for m in names]
        pairs_es = " y ".join(
            f"{ARM_ES.get(m, m)} {field(f'ax:[{i}].{m}.value', vals)}" for m in names
        )
        pairs_en = " and ".join(
            f"{ARM_EN.get(m, m)} {field(f'ax:[{i}].{m}.value', vals)}" for m in names
        )
        state = a.get("aligned")
        if state is True:
            es = f"Eje comparable, {name}: {pairs_es}, en {{ax:[{i}].unit}}."
            en = f"Comparable axis, {name}: {pairs_en}, in {{ax:[{i}].unit}}."
        elif state == "partial":
            es = (
                f"Mismo nombre, distinto alcance, {name}: {pairs_es}. "
                f"La corrida lo marca sólo parcialmente alineado."
            )
            en = (
                f"Same name, different scope, {name}: {pairs_en}. "
                f"The run marks it only partially aligned."
            )
        else:
            es = f"No comparable entre modalidades, {name}: {pairs_es}, en {{ax:[{i}].unit}}."
            en = f"Not comparable across modalities, {name}: {pairs_en}, in {{ax:[{i}].unit}}."
        out.append(
            {
                "es": es,
                "en": en,
                "tech": {
                    "es": f"Por qué: {{ax:[{i}].alignment_note}}",
                    "en": f"Why: {{ax:[{i}].alignment_note}}",
                },
                "focus": {"group": name},
                # only paths this axis really has: the arm's own words first, the
                # table's alignment note last, so a gap always quotes the run
                "gap": [
                    p
                    for p in [
                        f"{AXES}[{i}].{m}.{k}"
                        for m in names
                        for k in ("disclaimer", "reason", "note")
                    ]
                    + [f"{AXES}[{i}].{m}" for m in names]
                    + [f"{AXES}[{i}].alignment_note"]
                    if F.get(r, p) is not None
                ],
                "gap_es": f"Eje {name}, sin número en alguna rama",
                "gap_en": f"Axis {name}, no number on one of the arms",
            }
        )
    return out


def shared_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One sentence per measurement that really was produced by the same code on
    both leads, with what the number means attached."""
    names = arms(r)
    meaning = {
        "biophys_hydrophobicity_gravy": (
            "Hidrofobicidad GRAVY",
            "GRAVY hydrophobicity",
            "Cuanto más baja, menos se pega la cadena a sí misma y mejor se disuelve.",
            "The lower it is, the less the chain sticks to itself and the better it dissolves.",
        ),
        "biophys_instability_index": (
            "Índice de inestabilidad",
            "Instability index",
            "Por debajo de 40 el índice predice una cadena estable en el tubo.",
            "Below 40 the index predicts a chain that is stable in the tube.",
        ),
        "biophys_net_charge_pH7_4": (
            "Carga neta a pH 7,4",
            "Net charge at pH 7.4",
            "Una carga neta extrema a pH fisiológico complica la solubilidad y la "
            "farmacocinética.",
            "An extreme net charge at physiological pH complicates solubility and PK.",
        ),
        "biophys_isoelectric_point_pI": (
            "Punto isoeléctrico",
            "Isoelectric point",
            "Se reporta, no se puntúa: no hay una dirección mejor.",
            "It is reported, not scored: there is no better direction.",
        ),
        "biophys_molecular_weight_da": (
            "Masa molecular",
            "Molecular weight",
            "El tamaño difiere por construcción; describe, no califica.",
            "Size differs by construction; it describes, it does not grade.",
        ),
        "shared_epitope_density": (
            "Densidad de epítopos",
            "Epitope density",
            "Fracción de ventanas de nueve residuos ricas en hidrofóbicos, un proxy no "
            "calibrado de carga inmune que no apunta en la misma dirección para las dos "
            "modalidades.",
            "Fraction of nine-residue windows rich in hydrophobics, an uncalibrated proxy "
            "for immune load that does not point the same way for the two modalities.",
        ),
    }
    out: List[Dict[str, Any]] = []
    for i, a in enumerate(axis_list(r)):
        name = str(a.get("axis") or "")
        if a.get("aligned") is not True or name not in meaning:
            continue
        vals = [_num(F.get(a, f"{m}.value")) for m in names]
        if any(v is None for v in vals):
            continue
        pairs_es = " frente a ".join(
            f"{field(f'ax:[{i}].{m}.value', vals)} en el {ARM_ES.get(m, m)}" for m in names
        )
        pairs_en = " against ".join(
            f"{field(f'ax:[{i}].{m}.value', vals)} for the {ARM_EN.get(m, m)}" for m in names
        )
        es_name, en_name, es_meaning, en_meaning = meaning[name]
        out.append(
            {
                "es": f"{es_name}: {pairs_es}, en {{ax:[{i}].unit}}. {es_meaning}",
                "en": f"{en_name}: {pairs_en}, in {{ax:[{i}].unit}}. {en_meaning}",
                "tech": {
                    "es": f"Método: {{ax:[{i}].method}}",
                    "en": f"Method: {{ax:[{i}].method}}",
                },
                "focus": {"group": name},
            }
        )
    return out


# ── chapters ───────────────────────────────────────────────────────────────────────
def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    tgt, pep, fv = mesh_keys.get("target"), mesh_keys.get("pep"), mesh_keys.get("fv")
    i_plddt = axis_index(r, "structure_plddt")
    i_epi = axis_index(r, "shared_epitope_density")
    status_es = ", ".join(f"{ARM_ES.get(m, m)} {{arms_status.{m}}}" for m in arms(r))
    status_en = ", ".join(f"{ARM_EN.get(m, m)} {{arms_status.{m}}}" for m in arms(r))

    ch_axes_beats: List[Dict[str, Any]] = [
        {
            "es": "La comparación abre {c:axes|count} ejes. Sólo {ap:aligned_axes|count} "
            "se calculan con el mismo método en ambas ramas y {ap:partial_axes|count} "
            "comparte el nombre pero no el alcance; el resto no es comparable.",
            "en": "The comparison opens {c:axes|count} axes. Only {ap:aligned_axes|count} "
            "are computed with the same method on both arms and {ap:partial_axes|count} "
            "shares the name but not the scope; the rest are not comparable.",
            "tech": {
                "es": "Ejes alineados según la corrida: {ap:aligned_axes}.",
                "en": "Aligned axes as the run lists them: {ap:aligned_axes}.",
            },
        },
        {
            "es": "Recontado aquí sobre la tabla: los ejes marcados como alineados son "
            "exactamente los que la corrida enumera, y los parciales también.",
            "en": "Recounted here from the table: the axes marked aligned are exactly the "
            "ones the run enumerates, and so are the partial ones.",
            "kind": "check",
            "requires_check": "axis_alignment",
        },
    ]
    ch_axes_beats += axis_beats(r)
    ch_axes_beats.append(
        {
            "es": "El eje de confianza estructural es el único que la corrida llama "
            "plenamente comparable, y llega vacío en las dos ramas. Sin embargo cada rama "
            "sí midió pLDDT con el mismo predictor: {p:protenix_structure.plddt|n2} en el "
            "péptido y {a:protenix_structure.plddt|n2} en el anticuerpo.",
            "en": "The structure-confidence axis is the only one the run calls fully "
            "comparable, and it arrives empty on both arms. Yet each arm did measure pLDDT "
            "with the same predictor: {p:protenix_structure.plddt|n2} for the peptide and "
            "{a:protenix_structure.plddt|n2} for the antibody.",
            "tech": {
                "es": (
                    "Ambos vienen de {p:protenix_structure.model_used} sobre "
                    "{p:protenix_structure.gpu}; la tabla los buscó en "
                    "{ax:[%s].antibody.source} y no los encontró ahí." % i_plddt
                    if i_plddt is not None
                    else "Ambos vienen de {p:protenix_structure.model_used}."
                ),
                "en": (
                    "Both come from {p:protenix_structure.model_used} on "
                    "{p:protenix_structure.gpu}; the table looked for them in "
                    "{ax:[%s].antibody.source} and did not find them there." % i_plddt
                    if i_plddt is not None
                    else "Both come from {p:protenix_structure.model_used}."
                ),
            },
            "kind": "check",
            "requires_failed_check": "plddt_axis",
            "focus": {"group": "structure_plddt"},
        }
    )
    ch_axes_beats.append(
        {
            "es": "El co-plegado que habría dado una interfaz alineada no se hizo: el "
            "antígeno quedó como {ap:antigen_source}. Aun así las dos ramas llevan la "
            "estructura experimental {p:mol_3d.pdb_id} descargada de {p:mol_3d.source}, y "
            "la corrida no registra motivo del fallo.",
            "en": "The co-fold that would have produced an aligned interface was not run: "
            "the antigen was left as {ap:antigen_source}. Both arms nonetheless carry the "
            "experimental structure {p:mol_3d.pdb_id} downloaded from {p:mol_3d.source}, "
            "and the run records no reason for the failure.",
            "kind": "check",
            "requires_failed_check": "antigen_resolved",
        }
    )

    ch_shared_beats: List[Dict[str, Any]] = [
        {
            "es": "La corrida marca {ap:aligned_axes|count} ejes como calculados con el "
            "mismo código sobre las dos secuencias líder. Estos son los que además "
            "trajeron número en las dos ramas; ninguno está calibrado contra laboratorio.",
            "en": "The run marks {ap:aligned_axes|count} axes as computed with the same "
            "code on both lead sequences. These are the ones that also brought back a "
            "number on both arms; none of them is calibrated against the bench.",
        }
    ]
    ch_shared_beats += shared_beats(r)
    ch_shared_beats += [
        {
            "es": "Comprobado aquí: recalcular la masa de cada líder a partir de su propia "
            "secuencia reproduce el valor que la tabla publica.",
            "en": "Checked here: recomputing each lead's mass from its own sequence "
            "reproduces the value the table publishes.",
            "kind": "check",
            "requires_check": "mass_from_sequence",
        },
        {
            "es": "Comprobado aquí: repetir el barrido de nueve residuos sobre las mismas "
            "secuencias devuelve el mismo recuento y la misma densidad.",
            "en": "Checked here: repeating the nine-residue scan over the same sequences "
            "returns the same count and the same density.",
            "kind": "check",
            "requires_check": "epitope_scan",
        },
    ]
    if i_epi is not None:
        ch_shared_beats.append(
            {
                "es": "La densidad de epítopos se mide sobre ventanas muy distintas: "
                "{ax:[%s].peptide.scan_length} en el péptido frente a "
                "{ax:[%s].antibody.scan_length} en el anticuerpo. Una sola ventana no "
                "es una densidad, aunque la aritmética sea correcta." % (i_epi, i_epi),
                "en": "Epitope density is measured over very different windows: "
                "{ax:[%s].peptide.scan_length} for the peptide against "
                "{ax:[%s].antibody.scan_length} for the antibody. One window is not a "
                "density, however correct the arithmetic." % (i_epi, i_epi),
                "kind": "note",
                "focus": {"group": "shared_epitope_density"},
            }
        )
    ch_shared_beats.append(
        {
            "es": "Los descriptores del anticuerpo se calculan sobre {ab:vh_length} "
            "residuos de cadena pesada más {ab:vl_length} de ligera, no sobre la "
            "{ab:format} completa que la rama dice diseñar.",
            "en": "The antibody descriptors are computed over {ab:vh_length} heavy-chain "
            "residues plus {ab:vl_length} light-chain ones, not over the whole {ab:format} "
            "the arm says it designs.",
            "kind": "note",
        }
    )

    ch_index_beats: List[Dict[str, Any]] = [
        {
            "es": "Sobre los ejes que sí se miden igual, el índice in-silico da "
            "{ix:peptide|n4} al péptido y {ix:antibody|n4} al anticuerpo.",
            "en": "Over the axes that really are measured the same way, the in-silico index "
            "gives {ix:peptide|n4} to the peptide and {ix:antibody|n4} to the antibody.",
            "tech": {"es": "Qué es: {ix:label}", "en": "What it is: {ix:label}"},
        },
        {
            "es": "Entran tres términos, {ix:included_axes}, con peso {ix:weights}.",
            "en": "Three terms go in, {ix:included_axes}, weighted {ix:weights}.",
        },
        {
            "es": "Comprobado aquí: normalizar esos descriptores y promediarlos con esos "
            "pesos reproduce exactamente los dos índices publicados.",
            "en": "Checked here: normalising those descriptors and averaging them with "
            "those weights reproduces both published indices exactly.",
            "kind": "check",
            "requires_check": "index_arithmetic",
        },
        {
            "es": "El índice se describe como reflejo de la confianza del plegado más los "
            "descriptores de secuencia, pero en esta corrida sólo entraron descriptores de "
            "secuencia: {ix:included_axes}. Ningún término de estructura entró.",
            "en": "The index is described as reflecting fold confidence plus sequence "
            "descriptors, yet in this run only sequence descriptors went in: "
            "{ix:included_axes}. No structure term went in.",
            "kind": "check",
            "requires_failed_check": "composite_fold_term",
        },
        {
            "es": "Queda fuera, y la corrida dice por qué: {ix:excluded_axes}.",
            "en": "Left out, with the run's own reasons: {ix:excluded_axes}.",
        },
        {
            "es": "No hay veredicto cruzado, y es deliberado: {c:verdict_basis}",
            "en": "There is no cross-modality verdict, and that is deliberate: "
            "{c:verdict_basis}",
        },
        {
            "es": "La discusión de la propia corrida: {c:qualitative_discussion}",
            "en": "The run's own discussion: {c:qualitative_discussion}",
            "kind": "note",
        },
        {
            "es": "Por rama sí hay dictamen en una sola: el anticuerpo cierra en "
            "{c:per_arm_verdict.antibody}. La rama de péptido no emite ninguno, aunque su "
            "propia simulación clínica le asigna "
            "{p:clinical_trial.regulatory.overall_success_probability|pct} de probabilidad "
            "de éxito frente a {a:clinical_trial.overall_success_probability|pct} del "
            "anticuerpo.",
            "en": "Only one arm returns a call: the antibody closes at "
            "{c:per_arm_verdict.antibody}. The peptide arm returns none, although its own "
            "trial simulation assigns it "
            "{p:clinical_trial.regulatory.overall_success_probability|pct} success "
            "probability against the antibody's "
            "{a:clinical_trial.overall_success_probability|pct}.",
            "tech": {
                "es": "Vía regulatoria declarada: {p:clinical_trial.regulatory.pathway} "
                "y {a:clinical_trial.regulatory_path}; ambas simulaciones son in-silico.",
                "en": "Declared regulatory path: {p:clinical_trial.regulatory.pathway} "
                "and {a:clinical_trial.regulatory_path}; both simulations are in silico.",
            },
        },
    ]

    return [
        {
            "id": "run",
            "title": {"es": "La corrida", "en": "The run"},
            "claims": [
                "pipeline",
                "status",
                "success",
                "session_id",
                "target",
                "target_description",
                "indication",
                "compared_modalities",
                "arms_status",
                "errors",
                "best_candidate",
                "elapsed_s",
                "timestamp",
                "disclaimer",
                "downloads",
            ],
            "scene": scene_cover(r, tgt),
            "beats": [
                {
                    "es": "Esta página compara {compared_modalities|count} modalidades "
                    "terapéuticas contra una misma diana, {target}, en {indication}: no se "
                    "pregunta qué molécula es mejor sino qué números pueden compararse.",
                    "en": "This page compares {compared_modalities|count} therapeutic "
                    "modalities against one target, {target}, in {indication}: the question "
                    "is not which molecule is better but which numbers may be compared.",
                    "tech": {
                        "es": "Corrida {session_id} del pipeline {pipeline}, registrada el "
                        "{timestamp}.",
                        "en": "Run {session_id} of the {pipeline} pipeline, recorded on "
                        "{timestamp}.",
                    },
                },
                {
                    "es": "Cada modalidad se corrió como un pipeline de descubrimiento "
                    "entero y por separado; así quedaron: " + status_es + ".",
                    "en": "Each modality was run as a whole discovery pipeline of its own; "
                    "this is how they ended: " + status_en + ".",
                    "tech": {
                        "es": "Tiempo de pared {elapsed_s|n0} s en total: {pv:elapsed_s|n0} s "
                        "la rama de péptido y {av:elapsed_s|n0} s la de anticuerpo.",
                        "en": "Wall time {elapsed_s|n0} s in total: {pv:elapsed_s|n0} s for "
                        "the peptide arm and {av:elapsed_s|n0} s for the antibody arm.",
                    },
                },
                {
                    "es": "La corrida no devuelve un candidato único. {best_candidate.note}",
                    "en": "The run returns no single candidate. {best_candidate.note}",
                },
                {
                    "es": "Lo que la propia corrida advierte: {disclaimer}",
                    "en": "What the run itself warns: {disclaimer}",
                    "kind": "note",
                },
                {
                    "es": "La estructura que gira aquí es la diana experimental que las dos "
                    "ramas usaron, {p:mol_3d.pdb_id}, descargada de {p:mol_3d.source}.",
                    "en": "The structure turning here is the experimental target both arms "
                    "used, {p:mol_3d.pdb_id}, downloaded from {p:mol_3d.source}.",
                    "requires_mesh": "target",
                    "focus": {"color": "ss"},
                },
                {
                    "es": "Cada número de esta página se lee del resultado de la corrida; "
                    "cada valor del resultado aparece en algún capítulo o en el anexo.",
                    "en": "Every number on this page is read from the run's result; every "
                    "value in that result appears in some chapter or in the annex.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "axes",
            "title": {"es": "Qué se puede comparar", "en": "What may be compared"},
            "claims": [AXES, AP],
            "scene": scene_axes(r),
            "beats": ch_axes_beats,
        },
        {
            "id": "shared",
            "title": {
                "es": "Lo medido con el mismo código",
                "en": "Measured with the same code",
            },
            "claims": [],
            "scene": scene_shared(r),
            "beats": ch_shared_beats,
        },
        {
            "id": "index",
            "title": {
                "es": "El índice y el veredicto ausente",
                "en": "The index, and the missing verdict",
            },
            "claims": [
                IX,
                f"{CMP}.cross_modality_verdict",
                f"{CMP}.verdict_basis",
                f"{CMP}.qualitative_discussion",
                f"{CMP}.per_arm_verdict",
                f"{CMP}.csv_text",
            ],
            "scene": scene_index(r),
            "beats": ch_index_beats,
        },
        {
            "id": "peptide",
            "title": {"es": "La rama de péptido", "en": "The peptide arm"},
            "claims": [PEP],
            "scene": scene_variants(r),
            "beats": [
                {
                    "es": "La rama generó {p:summary.total_candidates_generated} péptidos de "
                    "partida, optimizó {p:summary.variants_optimized} variantes y llegó a "
                    "{p:summary.final_candidates_analyzed} candidatos analizados.",
                    "en": "The arm generated {p:summary.total_candidates_generated} starting "
                    "peptides, optimised {p:summary.variants_optimized} variants and ended "
                    "with {p:summary.final_candidates_analyzed} candidates analysed.",
                    "tech": {
                        "es": "Generación cuántica en {p:quantum_backend}, "
                        "{p:quantum_circuits.total_circuits} circuitos en total.",
                        "en": "Quantum generation on {p:quantum_backend}, "
                        "{p:quantum_circuits.total_circuits} circuits in all.",
                    },
                },
                {
                    "es": "El líder es {pb:sequence}, de {pb:molecular_weight_da|n1} Da, "
                    "que difiere de {pb:original_sequence} en la mutación {pb:mutations}.",
                    "en": "The lead is {pb:sequence}, {pb:molecular_weight_da|n1} Da, "
                    "differing from {pb:original_sequence} by the mutation {pb:mutations}.",
                    "focus": {"variants": True},
                },
                {
                    "es": "Sus propiedades: carga neta {pb:net_charge}, vida media en suero "
                    "{pb:serum_half_life_hours|n1} h, resistencia a proteasas "
                    "{pb:protease_resistance|low}, riesgo de agregación "
                    "{pb:aggregation_risk|low} y manufacturabilidad "
                    "{pb:manufacturability|low}.",
                    "en": "Its properties: net charge {pb:net_charge}, serum half-life "
                    "{pb:serum_half_life_hours|n1} h, protease resistance "
                    "{pb:protease_resistance|low}, aggregation risk "
                    "{pb:aggregation_risk|low} and manufacturability "
                    "{pb:manufacturability|low}.",
                    "tech": {
                        "es": "Estas tres últimas son categorías cualitativas in-silico, no "
                        "medidas: por eso el eje de developability no alinea.",
                        "en": "The last three are qualitative in-silico ratings, not "
                        "measurements: that is why the developability axis does not align.",
                    },
                },
                {
                    "es": "Su puntuación compuesta es {p:composite_score|n4}, clase "
                    "{p:drug_candidate_class}, repartida entre ADMET, toxicología, "
                    "farmacología, acoplamiento y confianza estructural con pesos "
                    "{ps:11_scoring.scoring_weights}.",
                    "en": "Its composite score is {p:composite_score|n4}, class "
                    "{p:drug_candidate_class}, split across ADMET, toxicology, pharmacology, "
                    "docking and structure confidence with weights "
                    "{ps:11_scoring.scoring_weights}.",
                    "tech": {
                        "es": "Justificación de los pesos: "
                        "{ps:11_scoring.weight_justification}; método "
                        "{ps:11_scoring.hybrid_method}, {ps:11_scoring.quantum_pct|n0}% "
                        "cuántico y {ps:11_scoring.ai_pct|n0}% IA.",
                        "en": "Weight justification: "
                        "{ps:11_scoring.weight_justification}; method "
                        "{ps:11_scoring.hybrid_method}, {ps:11_scoring.quantum_pct|n0}% "
                        "quantum and {ps:11_scoring.ai_pct|n0}% AI.",
                    },
                },
                {
                    "es": "El bucle de optimización corrió {p:optimization.iterations} "
                    "iteraciones, cerró con {p:optimization.improvement_pct|n0}% de mejora y "
                    "declaró {p:optimization.viable_count} candidatos viables, sin puntuación "
                    "máxima definida en ninguna iteración. El líder de arriba sale igualmente.",
                    "en": "The optimisation loop ran {p:optimization.iterations} iterations, "
                    "closed with {p:optimization.improvement_pct|n0}% improvement and "
                    "declared {p:optimization.viable_count} viable candidates, with no "
                    "defined top score in any iteration. The lead above is reported anyway.",
                    "kind": "check",
                    "requires_failed_check": "peptide_viable",
                },
                {
                    "es": "No todos los {p:summary.final_candidates_analyzed} candidatos que "
                    "la rama cuenta como analizados llevan una secuencia de aminoácidos: el "
                    "resto guarda una cadena SMILES en ese mismo campo, sin puntuación ni "
                    "propiedades.",
                    "en": "Not all of the {p:summary.final_candidates_analyzed} candidates "
                    "the arm counts as analysed carry an amino-acid sequence: the rest keep "
                    "a SMILES string in that same field, with no score and no properties.",
                    "kind": "check",
                    "requires_failed_check": "peptide_sequences",
                },
            ],
        },
        {
            "id": "peptide3d",
            "title": {"es": "El péptido plegado", "en": "The folded peptide"},
            "claims": [
                f"{PEP}.structure_3d",
                f"{PEP}.mol_3d",
                f"{PEP}.protenix_structure",
                f"{PEP}.enhancements",
                f"{PEP}.stages.9_docking",
                f"{PEP}.stages.10_3d_structure",
                f"{PEP}.best_candidate.mol_3d",
                f"{PEP}.best_candidate.structure_cif",
                f"{PEP}.best_candidate.analyses.chai1_structure",
                f"{PEP}.best_candidate.analyses.protenix_structure",
                f"{PEP}.best_candidate.analyses.3d_structure",
            ],
            "scene": scene_pep3d(r, pep, meshes),
            "beats": [
                {
                    "es": "{p:structure_3d.method} pliega los "
                    "{pb:analyses.chai1_structure.n_residues} residuos del péptido; aquí la "
                    "cadena se construye residuo a residuo.",
                    "en": "{p:structure_3d.method} folds the peptide's "
                    "{pb:analyses.chai1_structure.n_residues} residues; here the chain is "
                    "built residue by residue.",
                    "tech": {
                        "es": "Ejecutado en "
                        "{pb:analyses.chai1_structure.structure_backend}; la corrida no "
                        "guarda pLDDT por residuo para este modelo.",
                        "en": "Run on {pb:analyses.chai1_structure.structure_backend}; the "
                        "run keeps no per-residue pLDDT for this model.",
                    },
                    "focus": {"grow": True},
                    "requires_mesh": "pep",
                    "gap": [
                        f"{PEP}.structure_3d",
                        f"{PEP}.best_candidate.analyses.chai1_structure",
                    ],
                    "gap_es": "Sin estructura 3D del péptido",
                    "gap_en": "No 3D structure for the peptide",
                },
                {
                    "es": "La mutación que distingue a este líder se marca sobre su propia "
                    "estructura, en la posición que ocupa en la cadena.",
                    "en": "The mutation that sets this lead apart is marked on its own "
                    "structure, at the position it occupies in the chain.",
                    "requires_mesh": "pep",
                    "focus": {"annotations": True},
                    "kind": "note",
                },
                {
                    "es": "Protenix predice el complejo con la diana y le da ipTM "
                    "{p:protenix_structure.iptm|n4}, pTM {p:protenix_structure.ptm|n4} y "
                    "pLDDT {p:protenix_structure.plddt|n2}.",
                    "en": "Protenix predicts the complex with the target and gives it ipTM "
                    "{p:protenix_structure.iptm|n4}, pTM {p:protenix_structure.ptm|n4} and "
                    "pLDDT {p:protenix_structure.plddt|n2}.",
                    "tech": {
                        "es": "Modelo {p:protenix_structure.model_used} sobre "
                        "{p:protenix_structure.gpu}, trabajo {p:protenix_structure.job_id}, "
                        "{p:protenix_structure.prediction_time_seconds|n1} s.",
                        "en": "Model {p:protenix_structure.model_used} on "
                        "{p:protenix_structure.gpu}, job {p:protenix_structure.job_id}, "
                        "{p:protenix_structure.prediction_time_seconds|n1} s.",
                    },
                },
                {
                    "es": "El acoplamiento no se resuelve con un programa de docking: "
                    "{ps:9_docking.method} usa ese mismo ipTM como confianza de unión. La corrida "
                    "lo explica así: {ps:9_docking.reason}",
                    "en": "Binding is not resolved with a docking program: "
                    "{ps:9_docking.method} uses that same ipTM as binding confidence. The run puts "
                    "it this way: {ps:9_docking.reason}",
                    "tech": {
                        "es": "Diana {ps:9_docking.target}, PDB {ps:9_docking.pdb_id} de "
                        "{ps:9_docking.pdb_source}, afinidad declarada "
                        "{ps:9_docking.binding_affinity_kcal|n2} kcal/mol.",
                        "en": "Target {ps:9_docking.target}, PDB {ps:9_docking.pdb_id} from "
                        "{ps:9_docking.pdb_source}, declared affinity "
                        "{ps:9_docking.binding_affinity_kcal|n2} kcal/mol.",
                    },
                },
                {
                    "es": "La afinidad que la rama publica es un proxy, no una medida: "
                    "{pb:predicted_binding_kd_nm|n1} nM de "
                    "{pb:predicted_binding_kd_nm_basis}.",
                    "en": "The affinity the arm publishes is a proxy, not a measurement: "
                    "{pb:predicted_binding_kd_nm|n1} nM from "
                    "{pb:predicted_binding_kd_nm_basis}.",
                },
                {
                    "es": "Dentro de la misma rama ese ipTM aparece dos veces y con dos "
                    "valores: {ps:9_docking.protenix_iptm|n4} en la etapa de acoplamiento y "
                    "{p:protenix_structure.iptm|n4} en la predicción de estructura. El que "
                    "viaja a la comparación es el segundo.",
                    "en": "Inside the same arm that ipTM appears twice, with two values: "
                    "{ps:9_docking.protenix_iptm|n4} in the docking stage and "
                    "{p:protenix_structure.iptm|n4} in the structure prediction. The one "
                    "that travels to the comparison is the second.",
                    "kind": "note",
                },
                {
                    "es": "Las coordenadas del ligando que acompañan a la diana no son una "
                    "pose: sus carbonos alfa están alineados en línea recta y equiespaciados, "
                    "es decir una cadena extendida de relleno, no un acoplamiento.",
                    "en": "The ligand coordinates shipped next to the target are not a pose: "
                    "their alpha carbons sit on a straight line at even spacing, that is a "
                    "placeholder extended chain, not a docking result.",
                    "kind": "check",
                    "requires_failed_check": "peptide_pose",
                },
            ],
        },
        {
            "id": "antibody",
            "title": {"es": "La rama de anticuerpo", "en": "The antibody arm"},
            "claims": [ANT],
            "scene": scene_binders(r),
            "beats": [
                {
                    "es": "La rama parte de germinales humanas, {ab:vh_germline} para la "
                    "cadena pesada y {ab:vl_germline} para la ligera, y diseña los bucles "
                    "que tocan al antígeno.",
                    "en": "The arm starts from human germlines, {ab:vh_germline} for the "
                    "heavy chain and {ab:vl_germline} for the light one, and designs the "
                    "loops that touch the antigen.",
                    "tech": {
                        "es": "Elección del andamiaje: "
                        "{asg:framework_selection.selection_rationale}",
                        "en": "Scaffold choice: " "{asg:framework_selection.selection_rationale}",
                    },
                },
                {
                    "es": "El bucle largo CDR-H3, {ab:cdr_h3}, de {ab:cdr_h3_length} "
                    "residuos, se elige entre {asg:cdr_design_vqe.total_evaluated} "
                    "secuencias evaluadas por VQE.",
                    "en": "The long CDR-H3 loop, {ab:cdr_h3}, {ab:cdr_h3_length} residues "
                    "long, is picked among {asg:cdr_design_vqe.total_evaluated} sequences "
                    "evaluated by VQE.",
                    "tech": {
                        "es": "{asg:cdr_design_vqe.n_qubits} cúbits, "
                        "{asg:cdr_design_vqe.n_layers} capas, "
                        "{asg:cdr_design_vqe.shots} disparos, energías en "
                        "{asg:cdr_design_vqe.energy_unit}; condicionado a estructura: "
                        "{asg:cdr_design_vqe.conditioned_on_structure}.",
                        "en": "{asg:cdr_design_vqe.n_qubits} qubits, "
                        "{asg:cdr_design_vqe.n_layers} layers, "
                        "{asg:cdr_design_vqe.shots} shots, energies in "
                        "{asg:cdr_design_vqe.energy_unit}; conditioned on structure: "
                        "{asg:cdr_design_vqe.conditioned_on_structure}.",
                    },
                },
                {
                    "es": "De {asg:candidate_generation.num_candidates} candidatos "
                    "construidos, la rama reporta {a:candidates|count} y elige "
                    "{ab:candidate_id} por su compuesta {a:composite_score|n4}, clase "
                    "{a:drug_candidate_class}.",
                    "en": "Of {asg:candidate_generation.num_candidates} candidates built, "
                    "the arm reports {a:candidates|count} and picks {ab:candidate_id} on "
                    "its composite {a:composite_score|n4}, class "
                    "{a:drug_candidate_class}.",
                    "tech": {
                        "es": "Nota de la propia compuesta: {ab:scores.composite_note}",
                        "en": "The composite's own note: {ab:scores.composite_note}",
                    },
                },
                {
                    "es": "Humanización {ab:humanization_score|n3} sobre el umbral de "
                    "{asg:humanization_scoring.threshold|n2} que la rama declara; cuanto "
                    "más alta, menos probable es que el paciente vea la molécula como "
                    "ajena.",
                    "en": "Humanisation {ab:humanization_score|n3} against the threshold of "
                    "{asg:humanization_scoring.threshold|n2} the arm declares; the higher it "
                    "is, the less likely a patient is to read the molecule as foreign.",
                    "tech": {
                        "es": "Método {asg:humanization_scoring.scoring_method} contra "
                        "{asg:humanization_scoring.human_reference}, con "
                        "{asg:humanization_scoring.n_qubits} cúbits. Lectura declarada: "
                        "{asg:humanization_scoring.interpretation}.",
                        "en": "Method {asg:humanization_scoring.scoring_method} against "
                        "{asg:humanization_scoring.human_reference}, on "
                        "{asg:humanization_scoring.n_qubits} qubits. Declared reading: "
                        "{asg:humanization_scoring.interpretation}.",
                    },
                },
                {
                    "es": "Developability: agregación "
                    "{ab:developability.aggregation_propensity.value|n3}, viscosidad a 150 "
                    "mg/ml {ab:developability.viscosity_150mgml.value|n1} cP y Tm "
                    "{ab:developability.thermal_stability_tm.value|n1} °C; sólo "
                    "{ab:developability.thresholds_passed_fraction|pct} de los umbrales "
                    "pasa, y la puntuación agregada queda en "
                    "{ab:developability.developability_score|n2}.",
                    "en": "Developability: aggregation "
                    "{ab:developability.aggregation_propensity.value|n3}, viscosity at 150 "
                    "mg/ml {ab:developability.viscosity_150mgml.value|n1} cP and Tm "
                    "{ab:developability.thermal_stability_tm.value|n1} °C; only "
                    "{ab:developability.thresholds_passed_fraction|pct} of the thresholds "
                    "pass, and the aggregate score still sits at "
                    "{ab:developability.developability_score|n2}.",
                    "tech": {
                        "es": "Advertencia de la rama: " "{ab:viability.developability_caveat}",
                        "en": "The arm's own caveat: {ab:viability.developability_caveat}",
                    },
                },
                {
                    "es": "La afinidad queda sin calibrar: rango {ab:affinity_rank} dentro de la "
                    "rama. La rama lo advierte: {ab:kd_disclaimer}",
                    "en": "Affinity stays uncalibrated: rank {ab:affinity_rank} inside the arm. "
                    "The arm itself warns: {ab:kd_disclaimer}",
                },
                {
                    "es": "El candidato que entra en la comparación no es el de mayor "
                    "confianza estructural de su propia rama: el líder se eligió por la "
                    "compuesta interna, que la comparación declara no comparable entre "
                    "modalidades.",
                    "en": "The candidate that enters the comparison is not the one with the "
                    "highest structure confidence in its own arm: the lead was picked on the "
                    "internal composite, which the comparison itself declares not comparable "
                    "across modalities.",
                    "kind": "check",
                    "requires_failed_check": "lead_is_best_iptm",
                },
            ],
        },
        {
            "id": "antibody3d",
            "title": {"es": "El Fv modelado", "en": "The modelled Fv"},
            "claims": [
                f"{ANT}.stages.chai1_structure",
                f"{ANT}.stages.structure_prediction",
                f"{ANT}.protenix_structure",
                f"{ANT}.mol_3d",
                f"{ANT}.docking",
                f"{ANT}.enhancements",
                f"{ANT}.pdb_id",
                f"{ANT}.target_context",
                f"{ANT}.best_candidate.protenix_structure",
                f"{ANT}.best_candidate.mol_3d",
                f"{ANT}.best_candidate.docking",
                f"{ANT}.best_candidate.analyses.mol_3d",
                f"{ANT}.best_candidate.analyses.protenix_structure",
                f"{ANT}.best_candidate.analyses.docking",
            ],
            "scene": scene_fv(r, fv, meshes),
            "beats": [
                {
                    "es": "{asg:chai1_structure.model} pliega las dos cadenas variables, "
                    "{asg:chai1_structure.chains_folded}, en un modelo de "
                    "{asg:chai1_structure.n_residues} residuos.",
                    "en": "{asg:chai1_structure.model} folds the two variable chains, "
                    "{asg:chai1_structure.chains_folded}, into a model of "
                    "{asg:chai1_structure.n_residues} residues.",
                    "focus": {"grow": True},
                    "requires_mesh": "fv",
                    "gap": [f"{ANT}.stages.chai1_structure"],
                    "gap_es": "Sin modelo 3D del Fv",
                    "gap_en": "No 3D model of the Fv",
                },
                {
                    "es": "Ese modelo llega a pLDDT {asg:chai1_structure.plddt|n4} e ipTM "
                    "{asg:chai1_structure.iptm|n4}, pero las únicas cadenas plegadas son "
                    "{asg:chai1_structure.chains_folded}: no hay antígeno dentro, así que "
                    "esa interfaz es la de las dos cadenas variables entre sí, no la de la "
                    "unión a la diana.",
                    "en": "That model reaches pLDDT {asg:chai1_structure.plddt|n4} and ipTM "
                    "{asg:chai1_structure.iptm|n4}, but the only chains folded are "
                    "{asg:chai1_structure.chains_folded}: there is no antigen inside, so "
                    "that interface is the one between the two variable chains, not the one "
                    "with the target.",
                    "tech": {
                        "es": "Ejecutado en {asg:chai1_structure.structure_backend}; estado "
                        "{asg:chai1_structure.status}.",
                        "en": "Run on {asg:chai1_structure.structure_backend}; status "
                        "{asg:chai1_structure.status}.",
                    },
                },
                {
                    "es": "Los bucles CDR se localizan sobre el modelo buscando su secuencia "
                    "exacta, así que sólo se dibujan donde el modelo realmente los contiene: "
                    "los tres de la pesada primero y los tres de la ligera después.",
                    "en": "The CDR loops are located on the model by searching for their "
                    "exact sequence, so they are only drawn where the model really contains "
                    "them: the heavy chain's three first, the light chain's three after.",
                    "requires_mesh": "fv",
                    "focus": {"color": "domains"},
                    "kind": "note",
                },
                {
                    "es": "Aparte, Protenix predice el complejo con {a:protenix_structure.pdb_id} "
                    "y da ipTM {a:protenix_structure.iptm|n4}, pTM "
                    "{a:protenix_structure.ptm|n4} y pLDDT {a:protenix_structure.plddt|n2}.",
                    "en": "Separately, Protenix predicts the complex with "
                    "{a:protenix_structure.pdb_id} and returns ipTM "
                    "{a:protenix_structure.iptm|n4}, pTM {a:protenix_structure.ptm|n4} and "
                    "pLDDT {a:protenix_structure.plddt|n2}.",
                    "tech": {
                        "es": "Modelo {a:protenix_structure.model_used} sobre "
                        "{a:protenix_structure.gpu}, trabajo {a:protenix_structure.job_id}.",
                        "en": "Model {a:protenix_structure.model_used} on "
                        "{a:protenix_structure.gpu}, job {a:protenix_structure.job_id}.",
                    },
                },
                {
                    "es": "Comprobado aquí: los dos ipTM que la tabla compara son exactamente "
                    "los que cada rama obtuvo de ese mismo predictor, así que la advertencia "
                    "de alcance distinto habla de cómo cada rama planteó el complejo, no del "
                    "programa que lo calculó.",
                    "en": "Checked here: the two ipTM values the table compares are exactly "
                    "the ones each arm obtained from that same predictor, so the different-"
                    "scope caveat is about how each arm posed the complex, not about the "
                    "program that computed it.",
                    "kind": "check",
                    "requires_check": "iptm_provenance",
                },
                {
                    "es": "El acoplamiento contra {a:docking.pdb_id}, de {a:docking.pdb_source}, "
                    "genera {a:docking.poses_generated} poses por {a:docking.method} y deja "
                    "kd_nM sin valor.",
                    "en": "Docking against {a:docking.pdb_id}, from {a:docking.pdb_source}, "
                    "generates {a:docking.poses_generated} poses by {a:docking.method} and "
                    "leaves kd_nM empty.",
                    "tech": {
                        "es": "Afinidad declarada {a:docking.binding_affinity_kcal|n2} "
                        "kcal/mol; estado {a:docking.status}.",
                        "en": "Declared affinity {a:docking.binding_affinity_kcal|n2} "
                        "kcal/mol; status {a:docking.status}.",
                    },
                },
            ],
        },
        {
            "id": "safety",
            "title": {
                "es": "Seguridad y clínica, rama por rama",
                "en": "Safety and clinic, arm by arm",
            },
            "claims": [
                f"{PEP}.admet",
                f"{PEP}.toxicology",
                f"{PEP}.pharmacology",
                f"{PEP}.clinical_trial",
                f"{PEP}.overall_approval_probability",
                f"{PEP}.estimated_timeline_months",
                f"{PEP}.recommended_dose_mg",
                f"{PEP}.best_candidate.admet",
                f"{PEP}.best_candidate.admet_profile",
                f"{PEP}.best_candidate.clinical_trial",
                f"{PEP}.best_candidate.clinical_trials",
                f"{ANT}.admet",
                f"{ANT}.admet_92_parameters",
                f"{ANT}.toxicology",
                f"{ANT}.pharmacology",
                f"{ANT}.clinical_trial",
                f"{ANT}.clinical_verdict",
                f"{ANT}.stages.admet_tox_pk",
                f"{ANT}.stages.clinical_trial_simulation",
            ],
            "scene": scene_safety(r),
            "beats": [
                {
                    "es": "Toxicología del péptido: {p:toxicology.overall_score|n2} sobre 1, "
                    "leído como {p:toxicology.overall_safety}, con inmunogenicidad "
                    "{p:toxicology.immunogenicity.risk|low}.",
                    "en": "Peptide toxicology: {p:toxicology.overall_score|n2} out of 1, read "
                    "as {p:toxicology.overall_safety}, with {p:toxicology.immunogenicity.risk|low} "
                    "immunogenicity.",
                    "tech": {
                        "es": "Método {p:toxicology.method}; nota sobre inmunogenicidad: "
                        "{p:toxicology.immunogenicity.note}",
                        "en": "Method {p:toxicology.method}; immunogenicity note: "
                        "{p:toxicology.immunogenicity.note}",
                    },
                    "focus": {"group": "peptide"},
                },
                {
                    "es": "Toxicología del anticuerpo: {a:toxicology.overall_safety}, con "
                    "riesgo de ADA {a:toxicology.ada_risk}, de liberación de citoquinas "
                    "{a:toxicology.cytokine_release_risk} y de reacción a la infusión "
                    "{a:toxicology.infusion_reaction_risk}.",
                    "en": "Antibody toxicology: {a:toxicology.overall_safety}, with ADA risk "
                    "{a:toxicology.ada_risk}, cytokine release {a:toxicology.cytokine_release_risk} "
                    "and infusion reaction {a:toxicology.infusion_reaction_risk}.",
                    "tech": {
                        "es": "Toxicidad en diana: {a:toxicology.on_target_toxicity}.",
                        "en": "On-target toxicity: {a:toxicology.on_target_toxicity}.",
                    },
                    "focus": {"group": "antibody"},
                },
                {
                    "es": "Los paneles ADMET no están completos y la corrida lo dice: el "
                    "péptido trae {p:admet.parameters_count} parámetros reales frente a los "
                    "{p:admet.advertised_panel_parameters} anunciados.",
                    "en": "The ADMET panels are not complete and the run says so: the peptide "
                    "carries {p:admet.parameters_count} real parameters against the "
                    "{p:admet.advertised_panel_parameters} advertised.",
                    "tech": {"es": "{p:admet.parameters_note}", "en": "{p:admet.parameters_note}"},
                    "kind": "gap",
                },
                {
                    "es": "En el anticuerpo casi todo el panel de molécula pequeña sale como "
                    "no aplicable: hERG, Ames, Caco-2 y barrera hematoencefálica quedan en "
                    "{ab:herg}, que es la respuesta correcta para un biológico.",
                    "en": "For the antibody almost the whole small-molecule panel comes back "
                    "not applicable: hERG, Ames, Caco-2 and blood-brain barrier all read "
                    "{ab:herg}, which is the right answer for a biologic.",
                    "kind": "note",
                },
                {
                    "es": "Farmacocinética del anticuerpo: vida media "
                    "{a:pharmacology.pharmacokinetics.half_life_days|n1} días, aclaramiento "
                    "{a:pharmacology.pharmacokinetics.clearance_ml_day_kg|n1} ml/día/kg y "
                    "biodisponibilidad subcutánea "
                    "{a:pharmacology.pharmacokinetics.sc_bioavailability_pct|n1}%, con unión "
                    "a FcRn {a:pharmacology.pharmacokinetics.fcrn_binding}.",
                    "en": "Antibody pharmacokinetics: half-life "
                    "{a:pharmacology.pharmacokinetics.half_life_days|n1} days, clearance "
                    "{a:pharmacology.pharmacokinetics.clearance_ml_day_kg|n1} ml/day/kg and "
                    "subcutaneous bioavailability "
                    "{a:pharmacology.pharmacokinetics.sc_bioavailability_pct|n1}%, with FcRn "
                    "binding {a:pharmacology.pharmacokinetics.fcrn_binding}.",
                    "tech": {
                        "es": "Esa vida media es la de una IgG completa reciclada por FcRn, "
                        "mientras que la masa que la rama declara, {ab:molecular_weight_kda|n1} "
                        "kDa, es la del Fv.",
                        "en": "That half-life is the one of a whole IgG recycled by FcRn, while "
                        "the mass the arm declares, {ab:molecular_weight_kda|n1} kDa, is the "
                        "Fv's.",
                    },
                    "focus": {"group": "antibody"},
                },
                {
                    "es": "Vida media del péptido en suero: {pb:serum_half_life_hours|n1} h, "
                    "frente a {a:pharmacology.pharmacokinetics.half_life_days|n1} días en el "
                    "anticuerpo. Esa distancia, de horas a semanas, es la que separa una "
                    "pauta diaria de una mensual; ninguna de las dos cifras está medida.",
                    "en": "Peptide serum half-life: {pb:serum_half_life_hours|n1} h, against "
                    "{a:pharmacology.pharmacokinetics.half_life_days|n1} days for the "
                    "antibody. That distance, hours to weeks, is what separates a daily "
                    "schedule from a monthly one; neither figure is measured.",
                    "focus": {"group": "peptide"},
                },
                {
                    "es": "La simulación clínica del anticuerpo llega a "
                    "{a:clinical_trial.overall_success_probability|pct} con "
                    "{a:clinical_trial.estimated_total_subjects} sujetos en "
                    "{a:clinical_trial.estimated_total_duration_years|n1} años, y cierra en "
                    "{a:clinical_verdict}.",
                    "en": "The antibody's trial simulation reaches "
                    "{a:clinical_trial.overall_success_probability|pct} with "
                    "{a:clinical_trial.estimated_total_subjects} subjects over "
                    "{a:clinical_trial.estimated_total_duration_years|n1} years, and closes at "
                    "{a:clinical_verdict}.",
                    "tech": {
                        "es": "Vía {a:clinical_trial.regulatory_path}, endpoint primario "
                        "{asg:clinical_trial_simulation.primary_endpoint}.",
                        "en": "Path {a:clinical_trial.regulatory_path}, primary endpoint "
                        "{asg:clinical_trial_simulation.primary_endpoint}.",
                    },
                },
                {
                    "es": "La del péptido llega a "
                    "{p:clinical_trial.regulatory.overall_success_probability|pct} en "
                    "{p:estimated_timeline_months} meses por la vía "
                    "{p:clinical_trial.regulatory.pathway}, y no emite veredicto.",
                    "en": "The peptide's reaches "
                    "{p:clinical_trial.regulatory.overall_success_probability|pct} over "
                    "{p:estimated_timeline_months} months by the "
                    "{p:clinical_trial.regulatory.pathway} path, and returns no verdict.",
                    "tech": {
                        "es": "Método {p:clinical_trial.method}; ninguna de las dos "
                        "simulaciones es un ensayo.",
                        "en": "Method {p:clinical_trial.method}; neither simulation is a trial.",
                    },
                },
                {
                    "es": "Ninguna dosis sale de aquí: la rama de péptido deja "
                    "recommended_dose_mg sin valor y la de anticuerpo sólo propone rangos "
                    "dentro de su propia simulación.",
                    "en": "No dose comes out of this: the peptide arm leaves "
                    "recommended_dose_mg empty and the antibody arm only proposes ranges "
                    "inside its own simulation.",
                    "kind": "gap",
                    "gap": [f"{PEP}.pharmacology.pharmacodynamics"],
                    "gap_es": "Sin compromiso de diana calculado",
                    "gap_en": "No target engagement computed",
                },
            ],
        },
        {
            "id": "quantum",
            "title": {"es": "Dónde corrió lo cuántico", "en": "Where the quantum part ran"},
            "claims": [
                "provenance",
                f"{PEP}.quantum_circuits",
                f"{PEP}.quantum_backend",
                f"{PEP}.quantum_hardware",
                f"{PEP}.execution_mode",
                f"{PEP}.on_real_quantum_hardware",
                f"{PEP}.ibm_job_ids",
                f"{PEP}.simulator_job_ids",
                f"{PEP}.quantum_cell_validation",
                f"{PEP}.best_candidate.analyses.quantum_sequence_state",
                f"{PEP}.best_candidate.analyses.quantum_real_hamiltonian",
                f"{PEP}.best_candidate.analyses.ewf_sqd",
                f"{ANT}.quantum_backend",
                f"{ANT}.quantum_hardware",
                f"{ANT}.backend",
                f"{ANT}.execution_mode",
                f"{ANT}.on_real_quantum_hardware",
                f"{ANT}.ibm_job_ids",
                f"{ANT}.simulator_job_ids",
                f"{ANT}.fallback_count",
                f"{ANT}.quantum_cell_validation",
                f"{ANT}.stages.quantum_real_hamiltonian",
                f"{ANT}.stages.ewf_sqd",
                f"{ANT}.stages.quantum_sequence_state",
            ],
            "scene": scene_quantum(r),
            "beats": [
                {
                    "es": "Las dos ramas corrieron en modo {pv:execution_mode}: la de "
                    "péptido sobre {p:quantum_backend} y la de anticuerpo sobre "
                    "{a:quantum_backend}. Ninguna tocó hardware cuántico real.",
                    "en": "Both arms ran in {pv:execution_mode} mode: the peptide one on "
                    "{p:quantum_backend} and the antibody one on {a:quantum_backend}. "
                    "Neither touched real quantum hardware.",
                    "tech": {
                        "es": "Trabajos de IBM registrados: {p:summary.total_ibm_jobs} en el "
                        "péptido y {a:report.total_ibm_jobs} en el anticuerpo. De simulador: "
                        "{p:simulator_job_ids|count} y {av:simulator_job_ids|count}, con "
                        "{av:fallback_count} caídas a respaldo.",
                        "en": "Recorded IBM jobs: {p:summary.total_ibm_jobs} on the peptide "
                        "arm and {a:report.total_ibm_jobs} on the antibody arm. Simulator "
                        "jobs: {p:simulator_job_ids|count} and {av:simulator_job_ids|count}, "
                        "with {av:fallback_count} fallbacks.",
                    },
                },
                {
                    "es": "El péptido corrió {p:quantum_circuits.total_circuits} circuitos: "
                    "{p:quantum_circuits.qsvm_drug_likeness.qubits} cúbits para la "
                    "drug-likeness, {p:quantum_circuits.qnn_binding_affinity.qubits} para la "
                    "afinidad y {p:quantum_circuits.vqe_molecular_energy.qubits} para la "
                    "energía molecular.",
                    "en": "The peptide arm ran {p:quantum_circuits.total_circuits} circuits: "
                    "{p:quantum_circuits.qsvm_drug_likeness.qubits} qubits for drug-likeness, "
                    "{p:quantum_circuits.qnn_binding_affinity.qubits} for affinity and "
                    "{p:quantum_circuits.vqe_molecular_energy.qubits} for molecular energy.",
                    "tech": {
                        "es": "Disparos: {p:quantum_circuits.qsvm_drug_likeness.shots} y "
                        "{p:quantum_circuits.vqe_molecular_energy.shots}.",
                        "en": "Shots: {p:quantum_circuits.qsvm_drug_likeness.shots} and "
                        "{p:quantum_circuits.vqe_molecular_energy.shots}.",
                    },
                },
                {
                    "es": "El anticuerpo plantea además un hamiltoniano del plegado: "
                    "{asg:quantum_real_hamiltonian.n_residues} residuos y "
                    "{asg:quantum_real_hamiltonian.n_contacts} contactos se vuelven "
                    "{asg:quantum_real_hamiltonian.n_qubits} cúbits y "
                    "{asg:quantum_real_hamiltonian.n_terms} términos.",
                    "en": "The antibody arm also poses a folding Hamiltonian: "
                    "{asg:quantum_real_hamiltonian.n_residues} residues and "
                    "{asg:quantum_real_hamiltonian.n_contacts} contacts become "
                    "{asg:quantum_real_hamiltonian.n_qubits} qubits and "
                    "{asg:quantum_real_hamiltonian.n_terms} terms.",
                    "tech": {
                        "es": "Origen del hamiltoniano: "
                        "{asg:quantum_real_hamiltonian.hamiltonian_source}; corrió en "
                        "{asg:quantum_real_hamiltonian.lane}.",
                        "en": "Hamiltonian source: "
                        "{asg:quantum_real_hamiltonian.hamiltonian_source}; ran on "
                        "{asg:quantum_real_hamiltonian.lane}.",
                    },
                    "focus": {"register": True},
                },
                {
                    "es": "La energía variacional queda en "
                    "{asg:quantum_real_hamiltonian.vqe_energy_Ha|n4} Ha frente a "
                    "{asg:quantum_real_hamiltonian.reference_energy_Ha|n4} Ha del "
                    "{asg:quantum_real_hamiltonian.reference_kind}: por encima de la "
                    "referencia, como exige el principio variacional. Lo que queda entre "
                    "las dos es el error del ansatz, no una magnitud física.",
                    "en": "The variational energy lands at "
                    "{asg:quantum_real_hamiltonian.vqe_energy_Ha|n4} Ha against "
                    "{asg:quantum_real_hamiltonian.reference_energy_Ha|n4} Ha for the "
                    "{asg:quantum_real_hamiltonian.reference_kind}: above the reference, as "
                    "the variational principle requires. What sits between the two is the "
                    "ansatz's error, not a physical quantity.",
                    "focus": {"energy": True},
                },
                {
                    "es": "También carga la secuencia entera en un estado cuántico: "
                    "{asg:quantum_sequence_state.n_residues} residuos en "
                    "{asg:quantum_sequence_state.n_qubits} cúbits con codificación "
                    "{asg:quantum_sequence_state.encoding}, recuperada sin pérdida.",
                    "en": "It also loads the whole sequence into a quantum state: "
                    "{asg:quantum_sequence_state.n_residues} residues in "
                    "{asg:quantum_sequence_state.n_qubits} qubits with "
                    "{asg:quantum_sequence_state.encoding} encoding, read back without loss.",
                    "tech": {
                        "es": "Ejecutado en {asg:quantum_sequence_state.backend}.",
                        "en": "Run on {asg:quantum_sequence_state.backend}.",
                    },
                },
                {
                    "es": "Y una química de fragmentos sobre "
                    "{asg:ewf_sqd.n_fragments} fragmentos y "
                    "{asg:ewf_sqd.n_orbitals_total} orbitales da una energía de correlación "
                    "de {asg:ewf_sqd.correlation_energy_Ha|n4} Ha sobre Hartree-Fock.",
                    "en": "And a fragment chemistry over {asg:ewf_sqd.n_fragments} fragments "
                    "and {asg:ewf_sqd.n_orbitals_total} orbitals gives a correlation energy "
                    "of {asg:ewf_sqd.correlation_energy_Ha|n4} Ha on top of Hartree-Fock.",
                    "tech": {
                        "es": "Método {asg:ewf_sqd.method}. {asg:ewf_sqd.note}",
                        "en": "Method {asg:ewf_sqd.method}. {asg:ewf_sqd.note}",
                    },
                },
                {
                    "es": "Nada de esto es equivalente entre ramas: cada una eligió sus "
                    "propios circuitos y su propio tamaño de registro, así que el trabajo "
                    "cuántico tampoco es un eje comparable.",
                    "en": "None of this is equivalent across arms: each picked its own "
                    "circuits and its own register size, so the quantum work is not a "
                    "comparable axis either.",
                    "kind": "note",
                },
            ],
        },
    ]


# ── meshes ─────────────────────────────────────────────────────────────────────────
def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The three distinct structures this run holds: the experimental target both
    arms aimed at, the folded peptide, and the modelled Fv. The rest of the PDB
    blocks in the result are copies of these."""
    out: List[Dict[str, Any]] = []
    wanted = [
        ("target", f"{PEP}.mol_3d.protein_pdb"),
        ("pep", f"{PEP}.structure_3d.pdb"),
        ("fv", f"{ANT}.stages.chai1_structure.pdb"),
    ]
    for key, path in wanted:
        pdb = F.get(r, path)
        if F.is_pdb(pdb):
            out.append({"key": key, "pdb": pdb, "label": path})
    if not any(t["key"] == "target" for t in out):
        alt = F.get(r, f"{ANT}.mol_3d.protein_pdb")
        if F.is_pdb(alt):
            out.append({"key": "target", "pdb": alt, "label": f"{ANT}.mol_3d.protein_pdb"})
    return out


# ── checks ─────────────────────────────────────────────────────────────────────────
def _ca_trace(pdb: Any) -> List[List[float]]:
    pts = []
    for ln in str(pdb or "").splitlines():
        if ln.startswith("ENDMDL"):
            break
        if ln.startswith(("ATOM  ", "HETATM")) and ln[12:16].strip() == "CA":
            try:
                pts.append([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])
            except ValueError:
                continue
    return pts


def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Arithmetic and provenance this page states as verified, recomputed here from
    the run's own data. Several of these fail on purpose."""
    out: List[Dict[str, Any]] = []
    names = arms(r)
    ax = axis_list(r)

    # 1. the aligned/partial bookkeeping, recounted from the table itself
    if ax:
        got_a = [str(a.get("axis")) for a in ax if a.get("aligned") is True]
        got_p = [str(a.get("axis")) for a in ax if a.get("aligned") == "partial"]
        said_a = [str(x) for x in (F.get(r, f"{AP}.aligned_axes") or [])]
        said_p = [str(x) for x in (F.get(r, f"{AP}.partial_axes") or [])]
        ok = got_a == said_a and got_p == said_p
        out.append(
            {
                "id": "axis_alignment",
                "ok": ok,
                "es": f"{len(got_a)} ejes alineados y {len(got_p)} parcial(es) contados sobre "
                f"la tabla"
                + (
                    "; coinciden con los que la corrida lista"
                    if ok
                    else "; NO coinciden con los que la corrida lista"
                ),
                "en": f"{len(got_a)} aligned axes and {len(got_p)} partial one(s) counted from "
                f"the table"
                + (
                    "; they match the ones the run lists"
                    if ok
                    else "; they do NOT match the ones the run lists"
                ),
                "paths": [AXES, f"{AP}.aligned_axes", f"{AP}.partial_axes"],
            }
        )

    # 2. each lead's molecular weight, recomputed from its own sequence
    i_mw = axis_index(r, "biophys_molecular_weight_da")
    if i_mw is not None:
        es_rows, en_rows, ok = [], [], True
        for m in names:
            got = mass_of(lead_sequence(r, m))
            said = axis_value(r, "biophys_molecular_weight_da", m)
            if got is None or said is None:
                continue
            if abs(got - said) > 1.0:
                ok = False
            es_rows.append(f"{ARM_ES.get(m, m)} {got:.1f} frente a {said:.1f} Da")
            en_rows.append(f"{ARM_EN.get(m, m)} {got:.1f} against {said:.1f} Da")
        if es_rows:
            out.append(
                {
                    "id": "mass_from_sequence",
                    "ok": ok,
                    "es": "masa recalculada desde la secuencia de cada líder: "
                    + "; ".join(es_rows)
                    + ("" if ok else " — difieren en más de 1 Da"),
                    "en": "mass recomputed from each lead's own sequence: "
                    + "; ".join(en_rows)
                    + ("" if ok else " — they differ by more than 1 Da"),
                    "paths": [f"{AXES}[{i_mw}]"] + [f"arms.{m}.best_candidate" for m in names],
                }
            )

    # 3. the shared hydrophobic 9-mer scan, re-run on the same sequences
    i_epi = axis_index(r, "shared_epitope_density")
    if i_epi is not None:
        es_rows, en_rows, ok, any_row = [], [], True, False
        for m in names:
            got = epitope_scan(lead_sequence(r, m))
            cell = F.get(r, f"{AXES}[{i_epi}].{m}") or {}
            said_n, said_len = cell.get("epitope_count"), cell.get("scan_length")
            said_d = _num(cell.get("value"))
            if got is None or said_n is None:
                continue
            any_row = True
            same = got["epitope_count"] == said_n and got["scan_length"] == said_len
            if said_d is not None:
                same = same and abs(got["epitope_density"] - said_d) < 1e-4
            ok = ok and same
            tail = f"{got['epitope_count']}/{got['scan_length']} = {got['epitope_density']}"
            es_rows.append(f"{ARM_ES.get(m, m)} {tail}")
            en_rows.append(f"{ARM_EN.get(m, m)} {tail}")
        if any_row:
            out.append(
                {
                    "id": "epitope_scan",
                    "ok": ok,
                    "es": "barrido de 9-meros rehecho aquí: "
                    + "; ".join(es_rows)
                    + ("" if ok else " — no reproduce lo publicado"),
                    "en": "nine-mer scan re-run here: "
                    + "; ".join(en_rows)
                    + ("" if ok else " — it does not reproduce what was published"),
                    "paths": [f"{AXES}[{i_epi}]"],
                }
            )

    # 4. the cross-modality index, rebuilt term by term
    terms, unknown = index_terms(r)
    if terms and not unknown:
        es_rows, en_rows, ok = [], [], True
        for m in names:
            said = _num(F.get(r, f"{IX}.{m}"))
            got = round(sum(terms[t][m] for t in terms) / len(terms), 4)
            if said is None:
                continue
            if abs(got - said) > 5e-4:
                ok = False
            es_rows.append(f"{ARM_ES.get(m, m)} {got:.4f} frente a {said:.4f}")
            en_rows.append(f"{ARM_EN.get(m, m)} {got:.4f} against {said:.4f}")
        if es_rows:
            out.append(
                {
                    "id": "index_arithmetic",
                    "ok": ok,
                    "es": f"índice rehecho sobre {len(terms)} términos ({', '.join(terms)}): "
                    + "; ".join(es_rows)
                    + ("" if ok else " — no coincide con el publicado"),
                    "en": f"index rebuilt over {len(terms)} terms ({', '.join(terms)}): "
                    + "; ".join(en_rows)
                    + ("" if ok else " — it does not match the published one"),
                    "paths": [IX, AXES],
                }
            )

    # 5. where each compared ipTM really came from
    i_iptm = axis_index(r, "interface_iptm")
    if i_iptm is not None:
        es_rows, en_rows, ok, any_row = [], [], True, False
        models = set()
        for m in names:
            said = axis_value(r, "interface_iptm", m)
            arm_v = _num(F.get(r, f"arms.{m}.protenix_structure.iptm"))
            mdl = F.get(r, f"arms.{m}.protenix_structure.model_used")
            if said is None or arm_v is None:
                continue
            any_row = True
            models.add(str(mdl))
            if abs(said - arm_v) > 1e-6:
                ok = False
            es_rows.append(f"{ARM_ES.get(m, m)} {said}")
            en_rows.append(f"{ARM_EN.get(m, m)} {said}")
        one_model = next(iter(models)) if len(models) == 1 else None
        ok = ok and one_model is not None
        if any_row:
            out.append(
                {
                    "id": "iptm_provenance",
                    "ok": ok,
                    "es": "los ipTM comparados son los de cada rama ("
                    + "; ".join(es_rows)
                    + ")"
                    + (
                        f", los dos de {one_model}"
                        if ok
                        else "; pero no vienen del mismo predictor"
                    ),
                    "en": "the compared ipTM values are each arm's own ("
                    + "; ".join(en_rows)
                    + ")"
                    + (
                        f", both from {one_model}"
                        if ok
                        else "; but they do not come from the same predictor"
                    ),
                    "paths": [f"{AXES}[{i_iptm}]"]
                    + [f"arms.{m}.protenix_structure" for m in names],
                }
            )

    # 6. the one axis the run calls fully comparable, against the arms' own pLDDT
    i_plddt = axis_index(r, "structure_plddt")
    if i_plddt is not None:
        axis_vals = {m: axis_value(r, "structure_plddt", m) for m in names}
        arm_vals = {m: _num(F.get(r, f"arms.{m}.protenix_structure.plddt")) for m in names}
        have_arm = [m for m in names if arm_vals[m] is not None]
        missing = [m for m in names if axis_vals[m] is None]
        ok = not missing or not have_arm
        out.append(
            {
                "id": "plddt_axis",
                "ok": ok,
                "es": (
                    "el eje de pLDDT trae valor en todas las ramas"
                    if ok
                    else "el eje de pLDDT está vacío en "
                    + ", ".join(ARM_ES.get(m, m) for m in missing)
                    + ", pero las ramas sí registran pLDDT: "
                    + "; ".join(f"{ARM_ES.get(m, m)} {arm_vals[m]}" for m in have_arm)
                ),
                "en": (
                    "the pLDDT axis carries a value on every arm"
                    if ok
                    else "the pLDDT axis is empty on "
                    + ", ".join(ARM_EN.get(m, m) for m in missing)
                    + ", yet the arms do record a pLDDT: "
                    + "; ".join(f"{ARM_EN.get(m, m)} {arm_vals[m]}" for m in have_arm)
                ),
                "paths": [f"{AXES}[{i_plddt}]"]
                + [f"arms.{m}.protenix_structure.plddt" for m in have_arm],
            }
        )

    # 7. the index's own inputs, against what its label promises
    included = [t for t in (F.get(r, f"{IX}.included_axes") or []) if isinstance(t, str)]
    if included:
        has_fold = any(t in _FOLD_TERMS for t in included)
        out.append(
            {
                "id": "composite_fold_term",
                "ok": has_fold,
                "es": f"el índice se construye con {len(included)} término(s) "
                f"({', '.join(included)})"
                + (
                    "; incluye confianza de plegado"
                    if has_fold
                    else "; ninguno describe el plegado"
                ),
                "en": f"the index is built from {len(included)} term(s) "
                f"({', '.join(included)})"
                + (
                    "; fold confidence is included"
                    if has_fold
                    else "; none of them describes the fold"
                ),
                "paths": [f"{IX}.included_axes", f"{IX}.label"],
            }
        )

    # 8. the antigen the aligned co-fold needed, against what the arms already hold
    folds = [F.get(r, f"{AP}.{m}_fold") or {} for m in names]
    ran = any(f.get("real_iptm") or f.get("model") for f in folds)
    gave_reason = any(isinstance(f.get("reason"), str) and f["reason"].strip() for f in folds)
    have_struct = [
        m
        for m in names
        if F.is_pdb(F.get(r, f"arms.{m}.mol_3d.protein_pdb"))
        and F.get(r, f"arms.{m}.mol_3d.pdb_id")
    ]
    if folds:
        ok = ran or not have_struct
        out.append(
            {
                "id": "antigen_resolved",
                "ok": ok,
                "es": (
                    "el co-plegado alineado se ejecutó"
                    if ran
                    else "el co-plegado alineado no se ejecutó, "
                    + ("con motivo registrado" if gave_reason else "sin motivo registrado")
                    + ", aunque la rama de "
                    + " y la de ".join(ARM_ES.get(m, m) for m in have_struct)
                    + " ya llevan descargada la estructura del antígeno"
                ),
                "en": (
                    "the aligned co-fold did run"
                    if ran
                    else "the aligned co-fold did not run, "
                    + ("with a recorded reason" if gave_reason else "with no recorded reason")
                    + ", although the "
                    + " and ".join(ARM_EN.get(m, m) for m in have_struct)
                    + " arms already carry the antigen structure downloaded"
                ),
                "paths": [AP] + [f"arms.{m}.mol_3d.pdb_id" for m in have_struct],
            }
        )

    # 9. what the peptide arm's own optimisation loop recorded
    opt = F.get(r, f"{PEP}.optimization")
    if isinstance(opt, dict) and opt:
        viable = _num(opt.get("viable_count"))
        hist = [h for h in (opt.get("iteration_history") or []) if isinstance(h, dict)]
        scored = [h for h in hist if _num(h.get("top_score")) is not None]
        evaluated = sum(int(_num(h.get("evaluated")) or 0) for h in hist)
        ok = bool(viable) and bool(scored)
        out.append(
            {
                "id": "peptide_viable",
                "ok": ok,
                "es": f"el bucle evaluó {evaluated} candidatos en {len(hist)} iteraciones y "
                f"registró {int(viable or 0)} viables, con puntuación máxima definida en "
                f"{len(scored)} de {len(hist)}",
                "en": f"the loop evaluated {evaluated} candidates over {len(hist)} iterations "
                f"and recorded {int(viable or 0)} viable, with a defined top score in "
                f"{len(scored)} of {len(hist)}",
                "paths": [f"{PEP}.optimization"],
            }
        )

    # 10. what the peptide arm counts as a candidate
    cands = [c for c in (F.get(r, f"{PEP}.candidates") or []) if isinstance(c, dict)]
    if cands:
        real = [
            c
            for c in cands
            if isinstance(c.get("sequence"), str)
            and c["sequence"]
            and len(_canon(c["sequence"])) == len(c["sequence"])
        ]
        declared = _num(F.get(r, f"{PEP}.summary.final_candidates_analyzed"))
        n_declared = int(declared) if declared is not None else len(cands)
        ok = len(real) == n_declared
        out.append(
            {
                "id": "peptide_sequences",
                "ok": ok,
                "es": f"{len(real)} de los {n_declared} candidatos declarados llevan una "
                f"secuencia de aminoácidos; el resto guarda un SMILES en ese campo",
                "en": f"{len(real)} of the {n_declared} declared candidates carry an "
                f"amino-acid sequence; the rest keep a SMILES string in that field",
                "paths": [f"{PEP}.candidates", f"{PEP}.summary.final_candidates_analyzed"],
            }
        )

    # 11. whether the lead that enters the comparison is its arm's most confident
    ab_c = [c for c in (F.get(r, f"{ANT}.candidates") or []) if isinstance(c, dict)]
    lead_id = F.get(r, f"{ANT}.best_candidate.candidate_id")
    scored = [(c.get("candidate_id"), _num(F.get(c, "scores.iptm"))) for c in ab_c]
    scored = [(i, v) for i, v in scored if v is not None]
    if len(scored) > 1 and lead_id:
        best_id, best_v = max(scored, key=lambda kv: kv[1])
        lead_v = dict(scored).get(lead_id)
        ok = best_id == lead_id
        out.append(
            {
                "id": "lead_is_best_iptm",
                "ok": ok,
                "es": f"el líder {lead_id} entra con ipTM {lead_v}; el mejor ipTM de la rama "
                f"es {best_v} ({best_id})",
                "en": f"the lead {lead_id} enters with ipTM {lead_v}; the arm's best ipTM is "
                f"{best_v} ({best_id})",
                "paths": [f"{ANT}.candidates", f"{ANT}.best_candidate.candidate_id"],
            }
        )

    # 12. whether the peptide "pose" beside the target is a pose at all
    lig = F.get(r, f"{PEP}.mol_3d.ligand_sdf")
    pts = _ca_trace(lig)
    if len(pts) >= 4:
        steps = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        spread = max(steps) - min(steps)
        end = math.dist(pts[0], pts[-1])
        contour = sum(steps)
        straight = contour > 0 and (end / contour) > 0.999
        ok = not (straight and spread < 0.05)
        out.append(
            {
                "id": "peptide_pose",
                "ok": ok,
                "es": f"los {len(pts)} carbonos alfa del ligando van a {min(steps):.2f}–"
                f"{max(steps):.2f} Å de paso y cubren {end:.1f} Å de los {contour:.1f} Å de "
                f"contorno" + ("" if ok else ": una cadena extendida recta, no una pose"),
                "en": f"the ligand's {len(pts)} alpha carbons step {min(steps):.2f}–"
                f"{max(steps):.2f} Å apart and span {end:.1f} Å of a {contour:.1f} Å contour"
                + ("" if ok else ": a straight extended chain, not a pose"),
                "paths": [f"{PEP}.mol_3d.ligand_sdf"],
            }
        )

    return out


# MOLEVERA / BIOQL
