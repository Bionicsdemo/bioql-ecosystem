"""
Artifact model for the therapeutic mRNA pipeline (`mrna_therapeutic`).

Chapters follow the pipeline's own stages. Each one declares:
  * `claims` -- the paths of the result JSON it is responsible for, so coverage
    can prove every value in the run appears somewhere;
  * `scene` -- what the page animates, built here from the run's own sequences
    and coordinates (never invented);
  * `beats` -- bilingual templates whose numbers resolve from those paths.

Derivations are recomputed from the run's data and labelled: translating the CDS
and comparing it with the designed protein, finding the UTR/CDS/poly(A)
boundaries inside the full transcript, GC along the transcript, codon counts.

MOLEVERA / BIOQL
"""

from collections import Counter
from typing import Any, Callable, Dict, List, Optional

from .. import facts as F

PIPELINE = "mrna_therapeutic"
TITLE = {"es": "mRNA terapéutico", "en": "Therapeutic mRNA"}

S1, S2, S3 = (
    "stages.1_protein_design",
    "stages.2_structure_prediction",
    "stages.3_activation_classification",
)
S4, S5, S6, S7 = (
    "stages.4_mrna_optimization",
    "stages.5_bionics_gpu",
    "stages.6_quantum_cascade",
    "stages.7_safety_verdict",
)
ALIASES = {
    "p": S1,
    "s": S2,
    "a": S3,
    "m": S4,
    "b": S5,
    "q": S6,
    "v": S7,
    "st": "structure_3d",
    "rn": "rna_3d",
    "op": "optimization",
    "in": "input",
}

_BASES = "UCAG"
_AAS = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
CODON = {
    a + b + c: _AAS[16 * i + 4 * j + k]
    for i, a in enumerate(_BASES)
    for j, b in enumerate(_BASES)
    for k, c in enumerate(_BASES)
}
THREE = {
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
    "SEC": "U",
    "PYL": "O",
    "MSE": "M",
}


def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    return str(r.get("pipeline", "")).startswith("mrna_therapeutic") or any(
        str(k).startswith("4_mrna") for k in (r.get("stages") or {})
    )


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if (
        isinstance(result, dict)
        and isinstance(result.get("result"), dict)
        and "stages" in result["result"]
    ):
        return result["result"]
    return result


def rna(s: Any) -> str:
    return (s or "").upper().replace("T", "U") if isinstance(s, str) else ""


def translate(cds: str) -> str:
    s = rna(cds)
    return "".join(CODON.get(s[i : i + 3], "X") for i in range(0, len(s) - 2, 3))


def subject(r: Dict[str, Any]) -> str:
    mode = r.get("construct_mode") or F.get(r, "input.construct_mode") or "mRNA"
    targets = [t for t in (F.get(r, "input.target_receptors") or []) if t and t != "unspecified"]
    return f"{mode}" + (f" → {', '.join(map(str, targets))}" if targets else "")


# ── scenes ─────────────────────────────────────────────────────────────────────────
def scene_protein(r: Dict[str, Any], mesh_key: Optional[str]) -> Dict[str, Any]:
    seq = F.fasta_sequence(F.get(r, f"{S1}.protein_with_signal_fasta")) or ""
    sig = int(F.get(r, f"{S1}.signal_length_aa") or 0)
    doms = []
    for name, rng in (F.get(r, f"{S1}.domain_map") or {}).items():
        if (
            isinstance(rng, dict)
            and isinstance(rng.get("start"), int)
            and isinstance(rng.get("end"), int)
        ):
            doms.append({"name": name, "start": rng["start"] + sig, "end": rng["end"] + sig})
    cys = [i for i, c in enumerate(seq) if c == "C"]
    return {
        "type": "protein_chain",
        "seq": seq,
        "signal": sig,
        "domains": doms,
        "cys": cys,
        "mesh": mesh_key,
    }


def scene_structure(
    r: Dict[str, Any], mesh_key: Optional[str], meshes: Dict[str, Any]
) -> Dict[str, Any]:
    """The drawn fold, with each domain located by its exact sequence and labelled where
    it sits, plus the chain measured end to end on the coordinates the folder produced."""
    spans, notes, measures = [], [], []
    m = meshes.get(mesh_key or "")
    if m:
        res = m["res"]
        one = "".join(THREE.get(x["resn"], "X") for x in res)
        for name, dseq in (F.get(r, f"{S1}.domain_sequences") or {}).items():
            if isinstance(dseq, str) and len(dseq) >= 5:
                i = one.find(dseq.upper())
                if i >= 0:
                    spans.append({"name": name, "from": i, "to": i + len(dseq)})
                    mid = res[min(len(res) - 1, i + len(dseq) // 2)]
                    notes.append(
                        {"text": name, "pos": [mid["p"][0], mid["p"][1] + 3.0, mid["p"][2]]}
                    )
        if len(res) >= 2:
            first, last = res[0], res[-1]
            d = sum((x - y) ** 2 for x, y in zip(first["p"], last["p"])) ** 0.5
            measures.append(
                {"from": first["p"], "to": last["p"], "label": f"N\u2192C {d:.1f} \u00c5"}
            )
            notes.append(
                {
                    "text": f"N \u00b7 {first['resn']}{first['resi']}",
                    "pos": [first["p"][0], first["p"][1] + 2.2, first["p"][2]],
                }
            )
            notes.append(
                {
                    "text": f"C \u00b7 {last['resn']}{last['resi']}",
                    "pos": [last["p"][0], last["p"][1] + 2.2, last["p"][2]],
                }
            )
    return {
        "type": "cartoon",
        "mesh": mesh_key,
        "domains": spans,
        "annotations": notes,
        "measures": measures,
        "receptors": list((F.get(r, f"{S2}.receptor_panel") or {}).keys()),
    }


def scene_transcript(r: Dict[str, Any]) -> Dict[str, Any]:
    full, cds = rna(F.get(r, f"{S4}.full_mrna_sequence")), rna(F.get(r, f"{S4}.best_cds_sequence"))
    u5, u3 = rna(F.get(r, f"{S4}.utr5")), rna(F.get(r, f"{S4}.utr3"))
    regions, cur = [], 0
    for name, seq in (("5'UTR", u5), ("CDS", cds), ("3'UTR", u3)):
        if seq and full:
            i = full.find(seq, cur)
            if i >= 0:
                regions.append({"name": name, "start": i, "end": i + len(seq)})
                cur = i + len(seq)
    if full and cur < len(full) and set(full[cur:]) == {"A"}:
        regions.append({"name": "poly(A)", "start": cur, "end": len(full)})
    gc, win = [], 60
    for i in range(0, max(0, len(full) - win + 1), max(1, win // 2)):
        w = full[i : i + win]
        gc.append(round((w.count("G") + w.count("C")) / win, 3))
    cand = [c for c in (F.get(r, f"{S4}.all_candidates") or []) if isinstance(c, dict)]
    return {
        "type": "transcript",
        "seq": full,
        "regions": regions,
        "gc": gc,
        "gc_window": win,
        "kozak": full.find("GCCACC") if full else -1,
        "candidates": cand,
        "codons": [cds[i : i + 3] for i in range(0, len(cds) - 2, 3)],
    }


def scene_translation(r: Dict[str, Any]) -> Dict[str, Any]:
    cds = rna(F.get(r, f"{S4}.best_cds_sequence"))
    got = translate(cds).rstrip("*")
    want = F.fasta_sequence(F.get(r, f"{S1}.protein_with_signal_fasta")) or ""
    usage = Counter(cds[i : i + 3] for i in range(0, len(cds) - 2, 3))
    return {
        "type": "translation",
        "cds": cds,
        "protein": got,
        "expected": want,
        "identical": bool(got) and got == want,
        "n_codons": len(cds) // 3,
        "usage": sorted(usage.items(), key=lambda kv: -kv[1])[:24],
    }


def scene_rna3d(r: Dict[str, Any], keys: Dict[str, str]) -> Dict[str, Any]:
    els = [e for e in (F.get(r, "rna_3d.elements") or []) if isinstance(e, dict)]
    return {
        "type": "rna3d",
        "elements": [
            {
                "name": e.get("name"),
                "n": e.get("n_residues"),
                "mesh": keys.get(str(e.get("name"))),
                "score": e.get("ranking_score"),
                "engine": e.get("engine"),
            }
            for e in els
        ],
        "skipped": [
            {"name": s.get("name"), "n": s.get("n_residues"), "reason": s.get("reason")}
            for s in (F.get(r, "rna_3d.skipped") or [])
            if isinstance(s, dict)
        ],
    }


def scene_quantum(r: Dict[str, Any]) -> Dict[str, Any]:
    qc = F.get(r, f"{S6}.quantum_compute") or {}
    return {
        "type": "quantum",
        "n_qubits": qc.get("n_qubits"),
        "n_terms": qc.get("n_terms"),
        "n_contacts": qc.get("n_contacts"),
        "n_residues": qc.get("n_residues"),
        "energy": qc.get("vqe_energy_Ha"),
        "reference": qc.get("reference_energy_Ha"),
        "backend": qc.get("backend"),
        "algorithms": F.get(r, f"{S6}.algorithms"),
        "sequence_state": F.get(r, f"{S4}.quantum_sequence_state"),
        "structure_opt": F.get(r, f"{S4}.quantum_structure_optimization"),
    }


def scene_safety(r: Dict[str, Any]) -> Dict[str, Any]:
    imm = F.get(r, f"{S7}.immunogenicity") or {}
    return {
        "type": "safety",
        "epitopes": imm.get("mhc_epitope_count"),
        "risk": imm.get("risk_level"),
        "hydrophobic": imm.get("hydrophobic_9mer_count"),
        "loop_accessibility": F.get(r, f"{S7}.loop_accessibility"),
        "roadmap": F.get(r, f"{S7}.experimental_roadmap"),
        "verdict": F.get(r, f"{S7}.verdict"),
        "criteria": F.get(r, "optimization.acceptance_criteria"),
        "gaps": F.get(r, "optimization.gaps"),
        "metrics": F.get(r, "optimization.final_metrics"),
    }


# ── chapters ───────────────────────────────────────────────────────────────────────
def receptor_beats(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One sentence per receptor in the panel: its measured ipTM, or why there is none.

    The panel's keys are whatever the run recorded, so these templates are generated
    from the run itself -- a receptor the pipeline never looked at can never get a
    sentence, and one it looked at but could not score says so."""
    out: List[Dict[str, Any]] = []
    for rec in F.get(r, f"{S2}.receptor_panel") or {}:
        if "." in rec or "[" in rec:  # not addressable as a path; the annex still carries it
            continue
        out.append(
            {
                "es": f"Receptor {rec}: ipTM medio {{s:receptor_panel.{rec}.mean_iptm|n3}} sobre "
                f"{{s:receptor_panel.{rec}.n_seeds}} semilla(s), tomado como {{s:receptor_panel.{rec}.applicability}}.",
                "en": f"Receptor {rec}: mean ipTM {{s:receptor_panel.{rec}.mean_iptm|n3}} over "
                f"{{s:receptor_panel.{rec}.n_seeds}} seed(s), taken as {{s:receptor_panel.{rec}.applicability}}.",
                "focus": {"receptor": rec},
                "gap": [f"{S2}.receptor_panel.{rec}"],
                "gap_es": f"Receptor {rec}, sin ipTM",
                "gap_en": f"Receptor {rec}, no ipTM",
            }
        )
    return out


def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    prot = mesh_keys.get("protein")
    return [
        {
            "id": "overview",
            "title": {"es": "La corrida", "en": "The run"},
            "claims": [
                "pipeline",
                "timestamp",
                "construct_mode",
                "input",
                "summary",
                "images",
                "downloads",
                "visualizations",
            ],
            "scene": {
                "type": "cover",
                "mesh": prot,
                "images": [i for i in (r.get("images") or []) if isinstance(i, dict)],
            },
            "beats": [
                {
                    "es": "Esta página explica una corrida del pipeline {pipeline} en modo {construct_mode}, registrada el {timestamp}.",
                    "en": "This page explains one run of the {pipeline} pipeline in {construct_mode} mode, recorded on {timestamp}.",
                },
                {
                    "es": "El objetivo declarado: {in:target_receptors}.",
                    "en": "The stated target: {in:target_receptors}.",
                },
                {
                    "es": "El diseño entrega una proteína de {p:mature_length_aa} aminoácidos y un mRNA de {m:full_mrna_length_nt} nucleótidos que la codifica.",
                    "en": "The design yields a {p:mature_length_aa}-amino-acid protein and a {m:full_mrna_length_nt}-nucleotide mRNA that encodes it.",
                },
                {
                    "es": "Cada número de esta página se lee del resultado de la corrida; cada dato del resultado aparece en algún capítulo o en el anexo.",
                    "en": "Every number on this page is read from the run's result; every value in that result appears in some chapter or in the annex.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "design",
            "title": {"es": "La proteína diseñada", "en": "The designed protein"},
            "claims": [S1],
            "scene": scene_protein(r, prot),
            "beats": [
                {
                    "es": "Al traducirse, la cadena mide {p:mature_length_aa} aminoácidos de proteína madura más {p:signal_length_aa} de péptido señal.",
                    "en": "As translated, the chain is {p:mature_length_aa} amino acids of mature protein plus {p:signal_length_aa} of signal peptide.",
                    "tech": {"es": "diseño: {p:design_note}", "en": "design: {p:design_note}"},
                },
                {
                    "es": "El péptido señal ({p:signal_type}) la dirige a secreción y se corta al salir de la célula.",
                    "en": "The signal peptide ({p:signal_type}) routes it to secretion and is cleaved on the way out.",
                    "focus": {"cleave": True},
                },
                {
                    "es": "Masa del monómero: {p:monomer_mw_kda} kDa, calculada con {p:mw_method}.",
                    "en": "Monomer mass: {p:monomer_mw_kda} kDa, computed with {p:mw_method}.",
                    "tech": {
                        "es": "estado oligomérico: {p:oligomeric_state_note}",
                        "en": "oligomeric state: {p:oligomeric_state_note}",
                    },
                },
                {
                    "es": "El diseño se reparte en {p:domain_map|count} dominio(s); la animación los separa y los nombra.",
                    "en": "The design is split into {p:domain_map|count} domain(s); the animation separates and names them.",
                    "focus": {"domains": True},
                },
                {
                    "es": "Cisteínas de la región diseñada en {p:disulfide_check.loop_cys_positions}; riesgo de emparejamiento: {p:disulfide_check.pairing_risk}.",
                    "en": "Cysteines in the designed region at {p:disulfide_check.loop_cys_positions}; mispairing risk: {p:disulfide_check.pairing_risk}.",
                    "focus": {"cys": True},
                },
                {
                    "es": "Superficie accesible del lazo: {p:loop_sasa_A2} Å², por {p:loop_sasa_method}.",
                    "en": "Loop accessible surface: {p:loop_sasa_A2} Å², by {p:loop_sasa_method}.",
                    "tech": {"es": "{p:loop_sasa_note}", "en": "{p:loop_sasa_note}"},
                },
            ],
        },
        {
            "id": "structure",
            "title": {"es": "La forma en 3D", "en": "The 3D shape"},
            "claims": ["structure_3d", S2],
            "scene": scene_structure(r, prot, meshes),
            "beats": [
                {
                    "es": "{st:method} predice la estructura; PyMOL la dibuja y aquí se construye residuo a residuo.",
                    "en": "{st:method} predicts the structure; PyMOL draws it, and here it is built residue by residue.",
                    "focus": {"grow": True},
                    "requires_mesh": "protein",
                    "gap": ["structure_3d"],
                    "gap_es": "Esta corrida no tiene estructura 3D",
                    "gap_en": "This run has no 3D structure",
                },
                {
                    "es": "Confianza media del modelo, pLDDT {st:plddt|n1} sobre 100: el color va de baja a alta por residuo.",
                    "en": "Mean model confidence, pLDDT {st:plddt|n1} out of 100: colour runs low to high per residue.",
                    "focus": {"color": "plddt"},
                    "requires_mesh": "protein",
                    "tech": {"es": "{st:display_note}", "en": "{st:display_note}"},
                },
                {
                    "es": "Un segundo plegador, {st:boltz2_crosscheck.engine}, llega por su cuenta a pLDDT {st:boltz2_crosscheck.plddt|n1} y pTM {st:boltz2_crosscheck.ptm|n2}.",
                    "en": "A second folder, {st:boltz2_crosscheck.engine}, independently reaches pLDDT {st:boltz2_crosscheck.plddt|n1} and pTM {st:boltz2_crosscheck.ptm|n2}.",
                },
                {
                    "es": "Los {p:domain_sequences|count} dominio(s) se localizan sobre la estructura buscando su secuencia exacta.",
                    "en": "The {p:domain_sequences|count} domain(s) are located on the structure by searching for their exact sequence.",
                    "focus": {"color": "domains"},
                    "requires_mesh": "protein",
                },
            ]
            + receptor_beats(r),
        },
        {
            "id": "activation",
            "title": {"es": "¿Activa el receptor?", "en": "Does it activate the receptor?"},
            "claims": [S3],
            "scene": {"type": "panel", "root": S3},
            "beats": [
                {
                    "es": "{a:stage}: el pipeline evalúa si el constructo activaría su receptor.",
                    "en": "{a:stage}: the pipeline judges whether the construct would activate its receptor.",
                },
                {
                    "es": "Clasificador Hyaline: {a:hyaline_gnn.note}.",
                    "en": "Hyaline classifier: {a:hyaline_gnn.note}.",
                    "gap": ["stages.3_activation_classification.hyaline_gnn"],
                    "gap_es": "Sin clasificación de activación",
                    "gap_en": "No activation classification",
                },
                {
                    "es": "Controles del método (no de esta corrida): {a:controls_note}.",
                    "en": "Method controls (not from this run): {a:controls_note}.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "transcript",
            "title": {"es": "El mRNA, base por base", "en": "The mRNA, base by base"},
            "claims": [S4],
            "scene": scene_transcript(r),
            "beats": [
                {
                    "es": "Las cuatro partes suman exactamente el largo del transcrito, comprobado aquí sobre la secuencia.",
                    "en": "The four parts add up to exactly the transcript length, checked here against the sequence.",
                    "kind": "check",
                    "requires_check": "lengths",
                    "focus": {"regions": True},
                },
                {
                    "es": "El transcrito completo mide {m:full_mrna_length_nt} nt: 5'UTR {m:length_breakdown_nt.utr5}, ORF {m:length_breakdown_nt.orf}, 3'UTR {m:length_breakdown_nt.utr3} y poli(A) {m:length_breakdown_nt.polya}.",
                    "en": "The full transcript is {m:full_mrna_length_nt} nt: 5'UTR {m:length_breakdown_nt.utr5}, ORF {m:length_breakdown_nt.orf}, 3'UTR {m:length_breakdown_nt.utr3} and poly(A) {m:length_breakdown_nt.polya}.",
                    "focus": {"regions": True},
                    "tech": {
                        "es": "sistema de expresión: {m:expression_system}",
                        "en": "expression system: {m:expression_system}",
                    },
                },
                {
                    "es": "Química del transcrito: {m:modifications}. La caperuza protege el extremo 5' y la uridina modificada baja la alarma inmune innata.",
                    "en": "Transcript chemistry: {m:modifications}. The cap protects the 5' end and the modified uridine lowers innate immune alarm.",
                    "focus": {"region": "5'UTR"},
                },
                {
                    "es": "El 5'UTR de {m:utr5_length_nt} nt termina en el contexto Kozak que el ribosoma reconoce justo antes del AUG.",
                    "en": "The {m:utr5_length_nt}-nt 5'UTR ends in the Kozak context the ribosome reads just before the AUG.",
                    "focus": {"kozak": True},
                    "requires_check": "kozak",
                },
                {
                    "es": "La región codificante ocupa {m:cds_length_nt} nt, optimizada para {m:expression_system}.",
                    "en": "The coding region spans {m:cds_length_nt} nt, optimised for {m:expression_system}.",
                    "focus": {"region": "CDS"},
                },
                {
                    "es": "De {m:all_candidates|count} candidatos de codones, {m:n_candidates_passing} pasan la ventana de aceptación; el elegido tiene CAI {m:best_cai|n4}, GC {m:best_gc|pct} y homopolímero máximo {m:best_homopolymer}.",
                    "en": "Of {m:all_candidates|count} codon candidates, {m:n_candidates_passing} clear the acceptance window; the chosen one has CAI {m:best_cai|n4}, GC {m:best_gc|pct} and longest homopolymer {m:best_homopolymer}.",
                    "focus": {"candidates": True},
                },
                {
                    "es": "Después del codón de parada vienen el 3'UTR y la cola de {m:polya_length} adeninas, que sostienen el transcrito dentro de la célula.",
                    "en": "After the stop codon come the 3'UTR and the {m:polya_length}-adenine tail, which keep the transcript alive inside the cell.",
                    "focus": {"region": "poly(A)"},
                },
            ],
        },
        {
            "id": "translation",
            "title": {"es": "Del mRNA a la proteína", "en": "From mRNA to protein"},
            "claims": [],
            "scene": scene_translation(r),
            "beats": [
                {
                    "es": "El ribosoma lee la región codificante en tripletes: {m:cds_length_nt} nucleótidos son {p:mature_length_aa} aminoácidos más la señal y el codón de parada.",
                    "en": "The ribosome reads the coding region in triplets: {m:cds_length_nt} nucleotides give {p:mature_length_aa} amino acids plus the signal and the stop codon.",
                    "focus": {"ribosome": True},
                },
                {
                    "es": "Comprobación hecha aquí: traducir el CDS de la corrida devuelve exactamente la proteína diseñada.",
                    "en": "Checked here: translating the run's CDS returns exactly the designed protein.",
                    "kind": "check",
                    "requires_check": "translation",
                },
                {
                    "es": "Los codones más usados y su frecuencia se cuentan sobre los {m:cds_length_nt} nt del propio CDS.",
                    "en": "The most-used codons and their counts are tallied over the CDS's own {m:cds_length_nt} nt.",
                    "focus": {"usage": True},
                    "kind": "note",
                },
            ],
        },
        {
            "id": "rna3d",
            "title": {"es": "La forma del propio ARN", "en": "The shape of the RNA itself"},
            "claims": ["rna_3d"],
            "scene": scene_rna3d(r, mesh_keys),
            "beats": [
                {
                    "es": "{rn:engine} pliega los elementos cortos y estructurados del transcrito: {rn:n_folded} plegados, {rn:n_skipped} omitidos.",
                    "en": "{rn:engine} folds the transcript's short structured elements: {rn:n_folded} folded, {rn:n_skipped} skipped.",
                    "gap": ["rna_3d"],
                    "gap_es": "Sin estructura 3D del ARN",
                    "gap_en": "No RNA 3D structure",
                },
                {
                    "es": "El mRNA completo no se pliega: {rn:full_mrna_3d_reason}.",
                    "en": "The full mRNA is not folded: {rn:full_mrna_3d_reason}.",
                    "kind": "note",
                },
                {
                    "es": "Política del módulo: {rn:policy.folds}; nunca {rn:policy.never_folds}.",
                    "en": "Module policy: {rn:policy.folds}; never {rn:policy.never_folds}.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "engines",
            "title": {"es": "Los motores que opinaron", "en": "The engines that weighed in"},
            "claims": [S5],
            "scene": {"type": "panel", "root": S5},
            "beats": [
                {"es": "{b:stage}.", "en": "{b:stage}."},
                {
                    "es": "BioHNet da una puntuación de acoplamiento de {b:biohnet.docking_score|n2}, en unidades de {b:biohnet.docking_score_units}.",
                    "en": "BioHNet gives a docking score of {b:biohnet.docking_score|n2}, in units of {b:biohnet.docking_score_units}.",
                },
                {
                    "es": "Razonamiento terapéutico por {b:txgemma.engine}.",
                    "en": "Therapeutic reasoning by {b:txgemma.engine}.",
                },
            ],
        },
        {
            "id": "quantum",
            "title": {"es": "La parte cuántica", "en": "The quantum part"},
            "claims": [S6, f"{S4}.quantum_sequence_state", f"{S4}.quantum_structure_optimization"],
            "scene": scene_quantum(r),
            "beats": [
                {
                    "es": "El paso cuántico cifra el plegado como un problema de energía: {q:quantum_compute.n_residues} residuos y {q:quantum_compute.n_contacts} contactos se vuelven {q:quantum_compute.n_qubits} cúbits y {q:quantum_compute.n_terms} términos.",
                    "en": "The quantum step casts folding as an energy problem: {q:quantum_compute.n_residues} residues and {q:quantum_compute.n_contacts} contacts become {q:quantum_compute.n_qubits} qubits and {q:quantum_compute.n_terms} terms.",
                    "tech": {
                        "es": "hamiltoniano: {q:quantum_compute.hamiltonian_source} · variacional válido: {q:quantum_compute.variational_ok}",
                        "en": "Hamiltonian: {q:quantum_compute.hamiltonian_source} · variational bound holds: {q:quantum_compute.variational_ok}",
                    },
                    "focus": {"register": True},
                    "gap": ["stages.6_quantum_cascade"],
                    "gap_es": "Sin paso cuántico en esta corrida",
                    "gap_en": "No quantum step in this run",
                },
                {
                    "es": "Hamiltoniano: {q:quantum_compute.hamiltonian_source}.",
                    "en": "Hamiltonian: {q:quantum_compute.hamiltonian_source}.",
                },
                {
                    "es": "Energía variacional {q:quantum_compute.vqe_energy_Ha|n4} Ha frente a la referencia {q:quantum_compute.reference_energy_Ha|n4} Ha ({q:quantum_compute.reference_kind}).",
                    "en": "Variational energy {q:quantum_compute.vqe_energy_Ha|n4} Ha against the reference {q:quantum_compute.reference_energy_Ha|n4} Ha ({q:quantum_compute.reference_kind}).",
                    "focus": {"energy": True},
                },
                {
                    "es": "Dónde corrió: {q:quantum_compute.backend}. {q:backend_note}",
                    "en": "Where it ran: {q:quantum_compute.backend}. {q:backend_note}",
                    "kind": "note",
                },
                {
                    "es": "La secuencia también se carga en un estado cuántico: {m:quantum_sequence_state.n_qubits} cúbits con codificación {m:quantum_sequence_state.encoding}, recuperada sin pérdida.",
                    "en": "The sequence is also loaded into a quantum state: {m:quantum_sequence_state.n_qubits} qubits with {m:quantum_sequence_state.encoding} encoding, read back without loss.",
                    "focus": {"sequence_state": True},
                },
                {
                    "es": "Y QAOA revisa la elección de codones sinónimos: {m:quantum_structure_optimization.method}.",
                    "en": "And QAOA revisits the synonymous-codon choice: {m:quantum_structure_optimization.method}.",
                },
            ],
        },
        {
            "id": "safety",
            "title": {
                "es": "Seguridad y qué falta medir",
                "en": "Safety, and what is still unmeasured",
            },
            "claims": [S7, "optimization"],
            "scene": scene_safety(r),
            "beats": [
                {
                    "es": "Inmunogenicidad predicha: {v:immunogenicity.mhc_epitope_count} epítopos MHC-II, riesgo {v:immunogenicity.risk_level}, con {v:immunogenicity.method}.",
                    "en": "Predicted immunogenicity: {v:immunogenicity.mhc_epitope_count} MHC-II epitopes, risk {v:immunogenicity.risk_level}, using {v:immunogenicity.method}.",
                    "focus": {"meter": "immunogenicity"},
                    "tech": {
                        "es": "{v:immunogenicity.disclaimer}",
                        "en": "{v:immunogenicity.disclaimer}",
                    },
                },
                {
                    "es": "Accesibilidad del lazo: {v:loop_accessibility|n2}.",
                    "en": "Loop accessibility: {v:loop_accessibility|n2}.",
                },
                {
                    "es": "El ciclo de optimización corrió {op:iterations_run} iteración(es) y paró por {op:converged_reason}; métricas finales: {op:final_metrics}.",
                    "en": "The optimisation loop ran {op:iterations_run} iteration(s) and stopped because {op:converged_reason}; final metrics: {op:final_metrics}.",
                    "focus": {"criteria": True},
                },
                {
                    "es": "Criterios no medidos en esta corrida: {op:gaps}. Por eso all_criteria_met es {op:all_criteria_met}.",
                    "en": "Criteria not measured in this run: {op:gaps}. That is why all_criteria_met is {op:all_criteria_met}.",
                    "kind": "gap",
                },
                {
                    "es": "Veredicto del pipeline: {v:verdict}",
                    "en": "Pipeline verdict: {v:verdict}",
                },
                {
                    "es": "Lo que sigue es experimental, no computacional: {v:experimental_roadmap.gate_1}",
                    "en": "What comes next is experimental, not computational: {v:experimental_roadmap.gate_1}",
                    "focus": {"roadmap": True},
                },
            ],
        },
    ]


def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Which structures in this result deserve a PyMOL cartoon."""
    out = []
    pdb = F.get(r, "structure_3d.pdb")
    if F.is_pdb(pdb):
        out.append({"key": "protein", "pdb": pdb, "label": "structure_3d.pdb"})
    for i, e in enumerate(F.get(r, "rna_3d.elements") or []):
        if isinstance(e, dict) and F.is_pdb(e.get("pdb")):
            out.append(
                {
                    "key": str(e.get("name") or f"rna{i}"),
                    "pdb": e["pdb"],
                    "label": f"rna_3d.elements[{i}].pdb",
                }
            )
    return out


def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Arithmetic the page states as verified, recomputed from the run's own data."""
    out = []
    lb = F.get(r, f"{S4}.length_breakdown_nt") or {}
    full = rna(F.get(r, f"{S4}.full_mrna_sequence"))
    parts = [lb.get(k) for k in ("utr5", "orf", "utr3", "polya")]
    if all(isinstance(x, (int, float)) for x in parts):
        total = sum(parts)
        out.append(
            {
                "id": "lengths",
                "ok": total == lb.get("sum_check") == (len(full) or total),
                "es": f"{' + '.join(str(int(x)) for x in parts)} = {int(total)} nt, y la secuencia completa mide {len(full)} nt",
                "en": f"{' + '.join(str(int(x)) for x in parts)} = {int(total)} nt, and the full sequence is {len(full)} nt",
                "paths": [f"{S4}.length_breakdown_nt", f"{S4}.full_mrna_sequence"],
            }
        )
    u5, cds = rna(F.get(r, f"{S4}.utr5")), rna(F.get(r, f"{S4}.best_cds_sequence"))
    if u5 and cds:
        ok = u5.endswith("GCCACC") and cds.startswith("AUG")
        out.append(
            {
                "id": "kozak",
                "ok": ok,
                "es": (
                    "el 5'UTR termina en GCCACC y el CDS empieza en AUG"
                    if ok
                    else "el 5'UTR NO termina en el contexto Kozak GCCACC, o el CDS no empieza en AUG"
                ),
                "en": (
                    "the 5'UTR ends in GCCACC and the CDS starts at AUG"
                    if ok
                    else "the 5'UTR does NOT end in the GCCACC Kozak context, or the CDS does not start at AUG"
                ),
                "paths": [f"{S4}.utr5", f"{S4}.best_cds_sequence"],
            }
        )
    tr = scene_translation(r)
    if tr["cds"] and tr["expected"]:
        out.append(
            {
                "id": "translation",
                "ok": tr["identical"],
                "es": f"traducir el CDS da {len(tr['protein'])} aminoácidos"
                + (
                    " idénticos a la proteína diseñada"
                    if tr["identical"]
                    else " que NO coinciden con la proteína diseñada"
                ),
                "en": f"translating the CDS gives {len(tr['protein'])} amino acids"
                + (
                    " identical to the designed protein"
                    if tr["identical"]
                    else " that do NOT match the designed protein"
                ),
                "paths": [f"{S4}.best_cds_sequence", f"{S1}.protein_with_signal_fasta"],
            }
        )
    return out


# MOLEVERA / BIOQL
