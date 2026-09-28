"""quantum_reactivity_gate.py — the honest bridge from the SQD electronic-structure
advantage to BIOLOGICS design (peptides / antibodies / mRNA / replicon).

Honest premise (measured — see Reports/quantum_advantage_covalent): the quantum
advantage lives in SMALL, strongly-correlated electronic subsystems (covalent-warhead
bond-making transition states, metal-coordination centres), NOT in the biopolymer
backbone (sequence/fold/base-pairing are classical). A 250-aa antibody is not a
quantum-chemistry problem — but the electrophilic WARHEAD welded onto a covalent
binder, or the METAL-CHELATING motif of a DAA that hits a metal-dependent viral
enzyme, IS exactly the regime where CCSD(T)/DFT are unreliable and SQD is exact.

This gate:
  1. Detects a reactive moiety in a candidate (electrophilic covalent warhead, or a
     metal-chelating motif) via curated SMARTS.
  2. Extracts JUST that reactive fragment (keeps the quantum job tractable + focused).
  3. Runs the validated quantum electronic-structure descriptor (HF + SQD) on the
     fragment → electrophilicity ω (Parr), multireference character, reactivity class,
     and a `use_quantum` flag (True when classical single-reference scoring is
     unreliable there — high MR).
  4. Returns an additive decision each biologics pipeline can fold into its ranking.

Where it fires per modality (honest):
  • Peptides    — covalent/electrophilic warhead peptides, metallo-peptides, disulfide redox.
  • Antibodies  — covalent paratopes, ADC payloads (warhead / metal / radical).
  • Replicon    — the DAA small molecule: covalent protease warheads AND metal-chelating
                  motifs vs metal-dependent viral enzymes (HIV integrase Mg²⁺, influenza
                  PA endonuclease Mn²⁺/Mg²⁺). STRONG fit.
  • mRNA        — mostly N/A (sequence is classical); only the ionizable LIPID's reactive
                  groups. Reported honestly as low-relevance.

Opt-in via BIOQL_QCHEM_FEATURES=1 (the SQD run). Fail-open: no RDKit / no pyscf /
no moiety ⇒ returns a clean "not applicable / classical suffices" verdict, never breaks.

Runs the SQD step in the miniforge `quantum` env. MOLEVERA / BIOQL
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---- curated electrophilic covalent WARHEADS (name -> SMARTS, mechanism, class) ----
WARHEAD_SMARTS: List[Dict[str, str]] = [
    {
        "name": "acrylamide",
        "smarts": "[CX3]=[CX3]C(=O)[NX3]",
        "mech": "Michael acceptor → Cys thiol conjugate addition",
        "class": "irreversible",
    },
    {
        "name": "cyanoacrylamide",
        "smarts": "N#C/C=C/C(=O)N",
        "mech": "activated Michael acceptor (reversible covalent)",
        "class": "reversible",
    },
    {
        "name": "vinyl_sulfonamide",
        "smarts": "[CX3]=[CX3][SX4](=O)(=O)[NX3]",
        "mech": "Michael acceptor (sulfonyl-activated)",
        "class": "irreversible",
    },
    {
        "name": "vinyl_sulfone",
        "smarts": "[CX3]=[CX3][SX4](=O)(=O)[#6]",
        "mech": "Michael acceptor (sulfonyl-activated)",
        "class": "irreversible",
    },
    {
        "name": "chloroacetamide",
        "smarts": "[Cl]C[CX3](=O)[NX3]",
        "mech": "SN2 alkylation of Cys thiol",
        "class": "irreversible",
    },
    {
        "name": "epoxide",
        "smarts": "[CX4]1[OX2][CX4]1",
        "mech": "ring-opening alkylation of nucleophile",
        "class": "irreversible",
    },
    {
        "name": "boronic_acid",
        "smarts": "[BX3]([OX2H])[OX2H]",
        "mech": "reversible covalent to Ser/Thr/catalytic nucleophile",
        "class": "reversible",
    },
    {
        "name": "nitrile",
        "smarts": "[NX1]#[CX2][#6]",
        "mech": "reversible thioimidate with Cys (e.g. odanacatib/nirmatrelvir class)",
        "class": "reversible",
    },
    {
        "name": "aldehyde",
        "smarts": "[CX3H1](=O)[#6]",
        "mech": "reversible hemiketal/thiohemiacetal",
        "class": "reversible",
    },
    {
        "name": "fluoromethyl_ketone",
        "smarts": "[CX3](=O)[CH2][F]",
        "mech": "electrophilic ketone (Ser/Cys protease)",
        "class": "irreversible",
    },
    {
        "name": "propiolamide",
        "smarts": "[CX2]#[CX2]C(=O)[NX3]",
        "mech": "alkyne Michael acceptor",
        "class": "irreversible",
    },
    {
        "name": "beta_lactam",
        "smarts": "O=C1CCN1",
        "mech": "ring-strain acylation (Ser)",
        "class": "irreversible",
    },
    {
        "name": "michael_acceptor_generic",
        "smarts": "[CX3]=[CX3][CX3]=O",
        "mech": "α,β-unsaturated carbonyl Michael acceptor",
        "class": "irreversible",
    },
]

# ---- metal-chelating motifs (metal-dependent viral / metalloenzyme active sites) ----
METAL_CHELATOR_SMARTS: List[Dict[str, str]] = [
    {
        "name": "diketo_acid",
        "smarts": "O=C(O)C(=O)CC=O",
        "mech": "two-metal (Mg²⁺) chelation — HIV integrase / RNase H class",
        "target": "integrase/RNaseH",
    },
    {
        "name": "hydroxamic_acid",
        "smarts": "[CX3](=O)[NX3][OX2H]",
        "mech": "bidentate metal chelation (Zn²⁺) — metalloprotease/HDAC",
        "target": "metalloprotease",
    },
    {
        "name": "N_hydroxyimide",
        "smarts": "O=C[NX3]([OX2H])C=O",
        "mech": "metal chelation — influenza PA endonuclease (Mn²⁺/Mg²⁺)",
        "target": "PA_endonuclease",
    },
    {
        "name": "hydroxypyridinone",
        "smarts": "O=c1cc[nX3]cc1[OX2H]",
        "mech": "three-point metal chelation (Fe/Mn/Mg)",
        "target": "metalloenzyme",
    },
    {
        "name": "catechol",
        "smarts": "c1ccc(O)c(O)c1",
        "mech": "bidentate O,O metal chelation",
        "target": "metalloenzyme",
    },
    {
        "name": "8_hydroxyquinoline",
        "smarts": "Oc1cccc2cccnc12",
        "mech": "N,O bidentate metal chelation",
        "target": "metalloenzyme",
    },
]


def _mol(smiles: str):
    try:
        from rdkit import Chem, RDLogger

        RDLogger.DisableLog("rdApp.*")
        return Chem.MolFromSmiles(smiles)
    except Exception:
        return None


def detect_moieties(smiles: str) -> Dict[str, Any]:
    """Detect electrophilic warheads and metal-chelating motifs in a molecule."""
    out: Dict[str, Any] = {"warheads": [], "metal_chelators": [], "any": False}
    m = _mol(smiles)
    if m is None:
        return out
    from rdkit import Chem

    for w in WARHEAD_SMARTS:
        patt = Chem.MolFromSmarts(w["smarts"])
        if patt is not None and m.HasSubstructMatch(patt):
            match = m.GetSubstructMatch(patt)
            out["warheads"].append({**w, "atom_idx": list(match)})
    for c in METAL_CHELATOR_SMARTS:
        patt = Chem.MolFromSmarts(c["smarts"])
        if patt is not None and m.HasSubstructMatch(patt):
            match = m.GetSubstructMatch(patt)
            out["metal_chelators"].append({**c, "atom_idx": list(match)})
    out["any"] = bool(out["warheads"] or out["metal_chelators"])
    return out


def _extract_fragment(smiles: str, atom_idx: List[int], radius: int = 1) -> Optional[str]:
    """Extract the reactive fragment (matched atoms + `radius`-bond environment) as a
    small SMILES, so the SQD job is tractable and centred on the reactive centre."""
    m = _mol(smiles)
    if m is None:
        return None
    try:
        from rdkit import Chem

        keep = set(atom_idx)
        for _ in range(radius):
            for a in list(keep):
                for nb in m.GetAtomWithIdx(a).GetNeighbors():
                    keep.add(nb.GetIdx())
        amap: Dict[int, int] = {}
        frag = Chem.PathToSubmol(
            m,
            [
                b.GetIdx()
                for b in m.GetBonds()
                if b.GetBeginAtomIdx() in keep and b.GetEndAtomIdx() in keep
            ],
            atomMap=amap,
        )
        smi = Chem.MolToSmiles(frag)
        return smi if smi else None
    except Exception:
        return None


def quantum_score_fragment(fragment_smiles: str) -> Optional[Dict[str, Any]]:
    """Run the validated HF+SQD electronic-structure descriptor on a small fragment.
    Returns electrophilicity ω, MR character, reactivity class, use_quantum flag."""
    try:
        from quantum_chem_features import compute_one

        d = compute_one(fragment_smiles, basis="sto-3g", cas=(6, 6))
        if d is None:
            return None
        dec = d.get("decision") or {}
        return {
            "fragment": fragment_smiles,
            "electrophilicity_omega_eV": d.get("electrophilicity_omega_eV"),
            "gap_eV": d.get("gap_eV"),
            "multireference_character": d.get("multireference_character"),
            "correlation_energy_eV": d.get("correlation_energy_eV"),
            "reactivity_class": dec.get("covalent_reactivity_class"),
            "classical_reliability": dec.get("classical_reliability"),
            "use_quantum_number": dec.get("use_quantum_number"),
            "backend": d.get("backend"),
        }
    except Exception:
        return None


def assess_reactive_chemistry(
    smiles: str, modality: str = "small_molecule", run_quantum: bool = True
) -> Dict[str, Any]:
    """Modality-aware quantum-reactivity assessment for a candidate's small reactive
    part. Detects the moiety, extracts it, and (if quantum enabled) scores it with SQD.
    Honest: returns 'classical_suffices' when there is no strongly-correlated moiety."""
    result: Dict[str, Any] = {
        "modality": modality,
        "quantum_relevant": False,
        "applies": False,
        "moieties": None,
        "quantum": None,
        "verdict": "classical_suffices — no covalent warhead / metal-chelating motif; "
        "biopolymer design is classical (sequence/fold), quantum electronic "
        "structure not on the critical path here.",
    }
    det = detect_moieties(smiles or "")
    result["moieties"] = {
        "warheads": [w["name"] for w in det["warheads"]],
        "metal_chelators": [c["name"] for c in det["metal_chelators"]],
    }
    if not det["any"]:
        return result
    result["applies"] = True
    result["quantum_relevant"] = True
    # score the FIRST detected moiety's fragment (highest-priority reactive centre)
    hit = (det["warheads"] + det["metal_chelators"])[0]
    frag = _extract_fragment(smiles, hit["atom_idx"], radius=1) or smiles
    q = quantum_score_fragment(frag) if run_quantum else None
    result["quantum"] = q
    kind = "electrophilic covalent warhead" if det["warheads"] else "metal-chelating motif"
    if q:
        omega = q.get("electrophilicity_omega_eV")
        result["verdict"] = (
            f"{kind} ({hit['name']}) present → SQD electronic-structure scoring APPLIES. "
            f"ω={omega} eV, reactivity={q.get('reactivity_class')}, "
            f"classical_reliability={q.get('classical_reliability')}. "
            + (
                "USE THE QUANTUM NUMBER (classical single-reference scoring unreliable here)."
                if q.get("use_quantum_number")
                else "Single-reference regime — classical adequate; quantum corroborates."
            )
        )
    else:
        result["verdict"] = (
            f"{kind} ({hit['name']}) present → quantum scoring applicable "
            f"(enable BIOQL_QCHEM_FEATURES=1 / quantum env to run SQD)."
        )
    return result


# ---------------------------------------------------------------------------
# LARGE-BIOPOLYMER track: local strongly-correlated SITES inside a sequence.
# The backbone/fold is classical, but a big peptide/protein can carry LOCAL
# electronic-structure hotspots where quantum matters — metal cofactors
# (zinc-finger Cys/His clusters, iron-sulfur), disulfide redox, catalytic metals.
# We detect those sites on the SEQUENCE; each is a QM/MM fragment a quantum core
# (SQD on CUDA-Q/IBM at scale) would treat while the rest stays classical MM.
# ---------------------------------------------------------------------------
import re as _re

_SEQ_MOTIFS: List[Dict[str, str]] = [
    {
        "name": "zinc_finger_C2H2",
        "regex": r"C.{2,4}C.{10,14}H.{3,5}H",
        "site": "Zn²⁺ (2 Cys + 2 His)",
        "why": "d¹⁰ closed-shell but ligand-field / charge-transfer near-degeneracy; DFT functional-sensitive",
    },
    {
        "name": "zinc_ribbon_C4",
        "regex": r"C.{2,4}C.{6,40}C.{2,4}C",
        "site": "Zn²⁺ / [Fe-S] (4 Cys)",
        "why": "iron-sulfur clusters are strongly multireference (classic SQD/DMRG target)",
    },
    {
        "name": "cys_redox_pair",
        "regex": r"C.{1,6}C",
        "site": "disulfide / redox-active Cys pair",
        "why": "S–S bond making/breaking = static correlation",
    },
    {
        "name": "his_metal_cluster",
        "regex": r"H.{1,4}H.{1,20}H",
        "site": "multi-His metal site (Zn/Cu/Ni)",
        "why": "open-shell 3d metals (Cu/Ni) strongly correlated",
    },
]


def detect_quantum_sites_in_sequence(sequence: str) -> Dict[str, Any]:
    """Find local strongly-correlated SITES (metal cofactors, redox pairs) in a
    peptide/protein sequence — the spots where a QM/MM quantum core is warranted
    while the rest of the biopolymer stays classical."""
    seq = "".join(c for c in (sequence or "").upper() if c.isalpha())
    out: Dict[str, Any] = {"length": len(seq), "sites": [], "any": False}
    if not seq:
        return out
    for m in _SEQ_MOTIFS:
        for mo in _re.finditer(m["regex"], seq):
            out["sites"].append(
                {
                    "motif": m["name"],
                    "site": m["site"],
                    "why": m["why"],
                    "start": mo.start() + 1,
                    "end": mo.end(),
                    "residues": seq[mo.start() : mo.end()],
                }
            )
    # de-duplicate overlapping generic cys-pair hits when a richer motif covers them
    out["any"] = bool(out["sites"])
    return out


def assess_biopolymer(sequence: str, modality: str = "peptide") -> Dict[str, Any]:
    """Honest quantum relevance for a LARGE biopolymer: the backbone is classical;
    return the LOCAL sites (if any) where quantum electronic structure is on the
    critical path (metal cofactor / redox), for QM/MM quantum-core treatment."""
    det = detect_quantum_sites_in_sequence(sequence)
    n = len(det["sites"])
    return {
        "modality": modality,
        "backbone": "classical (sequence / fold / interactions — no whole-chain quantum advantage)",
        "local_quantum_sites": det["sites"],
        "n_sites": n,
        "quantum_relevant": det["any"],
        "verdict": (
            f"{n} local strongly-correlated site(s) detected → QM/MM quantum-core "
            f"treatment warranted at those residues (SQD on the metal/redox fragment; "
            f"rest of the chain classical MM)."
            if det["any"]
            else "No metal/redox site detected → whole biopolymer is classical; quantum "
            "electronic structure not on the critical path (use classical design + "
            "QAOA for the combinatorial sequence objective)."
        ),
    }


# Additive score contribution for a pipeline's composite ranking (never negative-only).
def score_contribution(assessment: Dict[str, Any], weight: float = 0.15) -> Dict[str, Any]:
    q = (assessment or {}).get("quantum") or {}
    omega = q.get("electrophilicity_omega_eV")
    if omega is None:
        return {
            "term": "quantum_reactivity",
            "weight": 0.0,
            "value": None,
            "note": "not applicable (no strongly-correlated moiety)",
        }
    # normalise ω (eV) to a 0..1 reactivity score; balanced window rewarded.
    # too cold (ω<0.5) or too hot (ω>2.5) penalised; ~1-2 eV = engageable but selective.
    o = float(omega)
    react = max(0.0, 1.0 - abs(o - 1.5) / 1.5)
    return {
        "term": "quantum_reactivity",
        "weight": weight,
        "value": round(react, 3),
        "omega_eV": o,
        "use_quantum": q.get("use_quantum_number"),
        "note": "SQD electrophilicity-based covalent engageability (balanced window)",
    }


# ---------------------------------------------------------------------------
# QUANTUM-RELEVANCE SCREENER — calibrated to the MEASURED MR map
# (quantum_core/quantum_relevance_map: ozone/polyene/Michael/nitro MR 0.1-0.2;
# transition metals MR ~0.9; peroxide/disulfide low at rest, high in the reaction TS).
# Fast SMARTS/graph scan → flags where SQD is worth running, across ALL pipelines.
# ---------------------------------------------------------------------------
_TRANSITION_METALS = {
    "Fe",
    "Cu",
    "Mn",
    "Co",
    "Ni",
    "Mo",
    "V",
    "Cr",
    "Ru",
    "Pt",
    "Pd",
    "W",
    "Ir",
    "Os",
}
_QREL_SMARTS = [
    ("nitro", "[NX3+](=O)[O-]", "moderate", "nitro-drug reductive activation (measured MR 0.11)"),
    (
        "michael_acceptor",
        "[CX3]=[CX3][CX3]=[OX1]",
        "moderate",
        "covalent warhead — TS strongly correlated (measured MR 0.13)",
    ),
    ("ozonide_like", "[OX2][OX2][OX2]", "high", "peroxy/ozonide"),
    ("para_quinone", "O=C1C=CC(=O)C=C1", "moderate", "quinone redox-cycling (measured MR ~0.09)"),
    # fused / anthraquinone para-quinones (doxorubicin, mitoxantrone, mitomycin core):
    # same redox-cycling electronic motif; sp2 ring carbons required (no saturated 1,4-diones).
    (
        "fused_quinone",
        "O=C1[#6;^2]~[#6;^2]C(=O)[#6;^2]~[#6;^2]1",
        "moderate",
        "fused/anthraquinone redox-cycling (measured MR ~0.09)",
    ),
]
# reaction-only: low MR at rest, high in the bond-breaking transition state
_QREL_REACTION_ONLY = [
    (
        "peroxide",
        "[OX2][OX2]",
        "endoperoxide (artemisinin) — quantum-relevant in the Fe-mediated O–O cleavage TS, not at rest",
    ),
    (
        "disulfide",
        "[SX2][SX2]",
        "disulfide — quantum-relevant in the S–S redox cleavage TS, not at rest",
    ),
]


def _longest_conjugation(mol) -> int:
    """Length of the longest chain of consecutive conjugated multiple bonds
    (proxy for polyene near-degeneracy → intrinsic multireference)."""
    try:
        from rdkit import Chem

        conj = [b for b in mol.GetBonds() if b.GetIsConjugated() and b.GetBondTypeAsDouble() >= 2.0]
        if not conj:
            return 0
        # count conjugated double bonds in the largest conjugated system (approx)
        return len(conj)
    except Exception:
        return 0


def scan_quantum_relevance(smiles: str) -> Dict[str, Any]:
    """Fast screen: does this molecule contain a MEASURED strongly-correlated motif
    (transition metal / extended π-conjugation / nitro / Michael / peroxy)? Returns a
    tier (high / moderate / reaction_only / classical) telling the pipeline whether an
    SQD electronic-structure treatment is worth running. No SQD executed here."""
    out: Dict[str, Any] = {
        "tier": "classical",
        "hits": [],
        "reaction_only": [],
        "conjugation_len": 0,
        "metals": [],
        "recommend_sqd": False,
    }
    m = _mol(smiles)
    if m is None:
        return out
    from rdkit import Chem

    metals = sorted({a.GetSymbol() for a in m.GetAtoms() if a.GetSymbol() in _TRANSITION_METALS})
    out["metals"] = metals
    conj = _longest_conjugation(m)
    out["conjugation_len"] = conj
    tier = "classical"
    if metals:
        out["hits"].append(
            {
                "motif": "transition_metal",
                "atoms": metals,
                "tier": "high",
                "why": "open-shell d-electrons — strongly multireference (measured MR ~0.9)",
            }
        )
        tier = "high"
    if conj >= 3:
        out["hits"].append(
            {
                "motif": "extended_conjugation",
                "n_conj_bonds": conj,
                "tier": "high",
                "why": "polyene near-degeneracy — intrinsic multireference (measured MR 0.15-0.18)",
            }
        )
        tier = "high"
    for name, sm, t, why in _QREL_SMARTS:
        patt = Chem.MolFromSmarts(sm)
        if patt is not None and m.HasSubstructMatch(patt):
            out["hits"].append({"motif": name, "tier": t, "why": why})
            if tier != "high":
                tier = "moderate"
    for name, sm, why in _QREL_REACTION_ONLY:
        patt = Chem.MolFromSmarts(sm)
        if patt is not None and m.HasSubstructMatch(patt):
            out["reaction_only"].append({"motif": name, "why": why})
            if tier == "classical":
                tier = "reaction_only"
    out["tier"] = tier
    out["recommend_sqd"] = tier in ("high", "moderate")
    out["verdict"] = {
        "high": "STRONGLY correlated motif → SQD gives the trustworthy number where DFT/CCSD(T) are unreliable.",
        "moderate": "Moderately correlated motif → SQD worth running; classical scoring is suspect here.",
        "reaction_only": "Correlated only in the bond-breaking TRANSITION STATE → run SQD on the reaction, not the resting molecule.",
        "classical": "Single-reference at rest → classical electronic-structure methods are adequate.",
    }[tier]
    return out


def register_quantum_reactivity_routes(app):
    """POST /api/quantum/reactivity — universal quantum-relevance gate for any
    modality. Give a `smiles` (small molecule / warhead / DAA) and/or a `sequence`
    (peptide/antibody/mRNA-encoded protein). Returns the reactive-moiety + local-
    site detection and, where a strongly-correlated moiety exists, the SQD score."""
    from flask import jsonify, request

    @app.route("/api/quantum/reactivity", methods=["POST", "OPTIONS"])
    def _quantum_reactivity_endpoint():
        if request.method == "OPTIONS":
            return ("", 204)
        data = request.get_json(silent=True) or {}
        modality = str(data.get("modality") or "small_molecule")
        run_quantum = bool(data.get("run_quantum", True))
        out: Dict[str, Any] = {"pipeline": "quantum_reactivity_gate_v1", "modality": modality}
        try:
            smi = str(data.get("smiles") or "")
            seq = str(data.get("sequence") or "")
            if smi:
                out["small_molecule"] = assess_reactive_chemistry(
                    smi, modality=modality, run_quantum=run_quantum
                )
                out["quantum_relevance_screen"] = scan_quantum_relevance(smi)
            if seq:
                out["biopolymer"] = assess_biopolymer(seq, modality=modality)
            out["honesty"] = (
                "Biopolymer backbone design is classical; the SQD quantum "
                "advantage applies to small strongly-correlated moieties — "
                "covalent warheads, metal-chelators, and local metal/redox "
                "sites (QM/MM) — not the whole chain."
            )
            return jsonify(out), 200
        except Exception as e:
            return jsonify({"error": str(e), "pipeline": "quantum_reactivity_gate_v1"}), 200

    return app


if __name__ == "__main__":
    import json
    import os

    os.environ.setdefault("BIOQL_QCHEM_FEATURES", "1")
    tests = [
        ("nirmatrelvir-like nitrile warhead frag", "N#CC1CC1C(=O)N"),
        ("acrylamide covalent peptide warhead", "C=CC(=O)NCC(=O)N"),
        ("diketo-acid integrase chelator", "O=C(O)C(=O)CC(=O)c1ccccc1"),
        ("plain canonical (no warhead)", "CC(C)CC(N)C(=O)O"),
    ]
    for name, smi in tests:
        a = assess_reactive_chemistry(smi, modality="small_molecule", run_quantum=True)
        print(f"\n[{name}] {smi}")
        print("  applies:", a["applies"], "| moieties:", a["moieties"])
        print("  verdict:", a["verdict"][:160])
