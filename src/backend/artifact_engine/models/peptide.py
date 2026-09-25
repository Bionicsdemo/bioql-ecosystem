"""
Artifact model for the peptide discovery pipeline (`PEPTIDE_DISCOVERY`).

This pipeline generates peptides, mutates them, and ranks what survives, so the
report follows that loop rather than a list of stages: the sequences that were
generated, the single-residue changes that were tried and which stuck, the
properties of each survivor, the folded structure of the best one, the interface
confidence against the target, and the composite score with its peptide bonus.

Mutations are re-derived here by comparing each candidate against the sequence
it came from, so the page shows the change at its real position instead of
trusting a label.

MOLEVERA / BIOQL
"""

from typing import Any, Dict, List, Optional

from .. import facts as F

PIPELINE = "PEPTIDE_DISCOVERY"
TITLE = {"es": "Péptido", "en": "Peptide"}

ST = "stages"
S1, S2, S3 = f"{ST}.1_target_analysis", f"{ST}.2_quantum_generation", f"{ST}.3_variant_optimization"
S4, S45, S5 = f"{ST}.4_peptide_analysis", f"{ST}.4.5_protenix", f"{ST}.5_admet"
S6, S8, S9 = f"{ST}.6_toxicology", f"{ST}.8_clinical_trial", f"{ST}.9_docking"
S10, S11 = f"{ST}.10_3d_structure", f"{ST}.11_scoring"
BEST = "best_candidate"
ALIASES = {
    "ta": S1,
    "gen": S2,
    "opt_stage": S3,
    "dk": S9,
    "sc": S11,
    "b": BEST,
    "admet_stage": S5,
    "tox_stage": S6,
    "trial_stage": S8,
    "pp": f"{BEST}.analyses.peptide_properties",
    "px": f"{BEST}.analyses.protenix_structure",
    "cx": f"{BEST}.analyses.complexa_binders",
    "sm": "summary",
    "op": "optimization",
}

AA3 = {
    "A": "Ala",
    "R": "Arg",
    "N": "Asn",
    "D": "Asp",
    "C": "Cys",
    "Q": "Gln",
    "E": "Glu",
    "G": "Gly",
    "H": "His",
    "I": "Ile",
    "L": "Leu",
    "K": "Lys",
    "M": "Met",
    "F": "Phe",
    "P": "Pro",
    "S": "Ser",
    "T": "Thr",
    "W": "Trp",
    "Y": "Tyr",
    "V": "Val",
}


def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    return str(r.get("pipeline", "")) == PIPELINE or (
        isinstance(r.get("stages"), dict) and "2_quantum_generation" in r["stages"]
    )


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if (
        isinstance(result, dict)
        and isinstance(result.get("result"), dict)
        and "stages" in result["result"]
    ):
        return result["result"]
    return result


def subject(r: Dict[str, Any]) -> str:
    seq = F.get(r, f"{BEST}.sequence") or ""
    tgt = r.get("target") or ""
    return " → ".join(x for x in (str(seq)[:24], str(tgt)) if x)


def diff(a: Any, b: Any) -> List[Dict[str, Any]]:
    """The single-residue changes between two sequences of the same length."""
    if not isinstance(a, str) or not isinstance(b, str) or len(a) != len(b):
        return []
    return [
        {
            "pos": i + 1,
            "from": x,
            "to": y,
            "label": f"{x}{i + 1}{y}",
            "from3": AA3.get(x, x),
            "to3": AA3.get(y, y),
        }
        for i, (x, y) in enumerate(zip(a, b))
        if x != y
    ]


# ── scenes ─────────────────────────────────────────────────────────────────────────
def scene_generated(r: Dict[str, Any]) -> Dict[str, Any]:
    peps = [p for p in (F.get(r, f"{S2}.peptides") or []) if isinstance(p, dict)]
    return {
        "type": "sequences",
        "items": [{"seq": p.get("sequence"), "source": p.get("source")} for p in peps],
        "n": F.get(r, f"{S2}.candidates_generated"),
        "jobs": len(F.get(r, f"{S2}.ibm_job_ids") or []),
    }


def scene_variants(r: Dict[str, Any]) -> Dict[str, Any]:
    vs = [v for v in (F.get(r, f"{S3}.variants") or []) if isinstance(v, dict)]
    out = []
    for v in vs:
        ch = diff(v.get("original"), v.get("optimized"))
        out.append(
            {
                "original": v.get("original"),
                "optimized": v.get("optimized"),
                "score": v.get("score"),
                "changes": ch,
            }
        )
    return {
        "type": "variants",
        "variants": out,
        "total": F.get(r, f"{S3}.total_variants"),
        "history": F.get(r, "optimization.iteration_history") or [],
    }


def scene_candidates(r: Dict[str, Any]) -> Dict[str, Any]:
    cs = [c for c in (r.get("candidates") or []) if isinstance(c, dict)]
    return {
        "type": "ranking",
        "items": [
            {
                "rank": c.get("rank"),
                "seq": c.get("sequence"),
                "score": c.get("optimization_score"),
                "mw": c.get("molecular_weight_da"),
                "charge": c.get("net_charge"),
                "half_life_h": c.get("serum_half_life_hours"),
                "protease": c.get("protease_resistance"),
                "aggregation": c.get("aggregation_risk"),
                "changes": diff(c.get("original_sequence"), c.get("sequence")),
            }
            for c in cs
        ],
    }


def scene_structure(r: Dict[str, Any], mesh_keys: Dict[str, str]) -> Dict[str, Any]:
    pp = F.get(r, f"{BEST}.analyses.peptide_properties") or {}
    return {
        "type": "cartoon",
        "mesh": mesh_keys.get("peptide"),
        "domains": [],
        "seq": F.get(r, f"{BEST}.sequence"),
        "props": {
            k: pp.get(k)
            for k in (
                "length",
                "molecular_weight_da",
                "net_charge",
                "isoelectric_point",
                "gravy_score",
                "hydrophobic_ratio",
                "aromatic_ratio",
            )
        },
    }


def scene_score(r: Dict[str, Any]) -> Dict[str, Any]:
    bd = F.get(r, f"{S11}.score_breakdown") or {}
    return {
        "type": "score",
        "composite": F.get(r, f"{S11}.composite_score"),
        "parts": [
            {
                "name": k,
                "score": v.get("score"),
                "weight": v.get("weight"),
                "weighted": v.get("weighted"),
            }
            for k, v in bd.items()
            if isinstance(v, dict)
        ],
        "klass": F.get(r, f"{S11}.drug_candidate_class"),
        "flags": F.get(r, f"{S11}.safety_flags") or [],
        "bonus": F.get(r, f"{S11}.peptide_bonus"),
        "gate": {},
    }


# ── chapters ───────────────────────────────────────────────────────────────────────
def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "overview",
            "title": {"es": "El blanco y el encargo", "en": "The target and the brief"},
            "claims": [
                "pipeline",
                "pipeline_id",
                "target",
                "target_description",
                "metadata",
                "indication",
                "n_candidates",
                "optimize_for",
                "timestamp",
                "quantum_backend",
                "execution_mode",
                "quantum_hardware",
                "on_real_quantum_hardware",
                "ibm_job_ids",
                "trained_generator",
                "pipeline_architecture",
                "summary",
                S1,
                "quantum_core_optimization",
                "quantum_circuits",
                "simulator_job_ids",
                "provenance",
            ],
            "scene": scene_generated(r),
            "beats": [
                {
                    "es": "Una corrida de {pipeline} contra {target}, pidiendo {n_candidates} candidatos optimizados para {optimize_for}, el {timestamp}.",
                    "en": "A run of {pipeline} against {target}, asking for {n_candidates} candidates optimised for {optimize_for}, on {timestamp}.",
                },
                {
                    "es": "Indicación declarada: {indication}.",
                    "en": "Stated indication: {indication}.",
                },
                {
                    "es": "La arquitectura del pipeline es un ciclo: {pipeline_architecture}.",
                    "en": "The pipeline's architecture is a loop: {pipeline_architecture}.",
                    "kind": "note",
                },
                {
                    "es": "Corrió en {quantum_backend}; sobre hardware cuántico real: {on_real_quantum_hardware}.",
                    "en": "It ran on {quantum_backend}; on real quantum hardware: {on_real_quantum_hardware}.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "generation",
            "title": {"es": "De dónde salen los péptidos", "en": "Where the peptides come from"},
            "claims": [S2],
            "scene": scene_generated(r),
            "beats": [
                {
                    "es": "La generación produjo {gen:candidates_generated} péptidos de partida.",
                    "en": "Generation produced {gen:candidates_generated} starting peptides.",
                    "focus": {"sequences": True},
                    "gap": [S2],
                    "gap_es": "Sin generación de péptidos",
                    "gap_en": "No peptide generation",
                },
                {
                    "es": "Cada secuencia dice de dónde vino: {gen:peptides[0].source}.",
                    "en": "Each sequence records where it came from: {gen:peptides[0].source}.",
                },
                {
                    "es": "Se registraron {ibm_job_ids|count} identificadores de trabajo del lado cuántico.",
                    "en": "{ibm_job_ids|count} job identifiers were recorded on the quantum side.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "optimization",
            "title": {"es": "Una letra a la vez", "en": "One letter at a time"},
            "claims": [S3, "optimization"],
            "scene": scene_variants(r),
            "beats": [
                {
                    "es": "Se probaron {opt_stage:total_variants} variantes: cada una cambia aminoácidos de la secuencia de partida y se vuelve a puntuar.",
                    "en": "{opt_stage:total_variants} variants were tried: each changes amino acids of the starting sequence and is scored again.",
                    "focus": {"variants": True},
                    "gap": [S3],
                    "gap_es": "Sin optimización de variantes",
                    "gap_en": "No variant optimisation",
                },
                {
                    "es": "Los cambios que se ven aquí están recalculados comparando cada variante con su original, letra por letra.",
                    "en": "The changes shown here are recomputed by comparing each variant with its original, letter by letter.",
                    "kind": "note",
                    "requires_check": "mutations",
                },
                {
                    "es": "El ciclo corrió {op:iterations} iteración(es) y convergió: {op:converged}; mejora {op:improvement_pct|n2}%.",
                    "en": "The loop ran {op:iterations} iteration(s) and converged: {op:converged}; improvement {op:improvement_pct|n2}%.",
                },
                {
                    "es": "En la primera vuelta, de {op:iteration_history[0].evaluated} evaluados pasaron la puerta de seguridad {op:iteration_history[0].passed_safety} y quedaron {op:iteration_history[0].viable} viables.",
                    "en": "On the first pass, of {op:iteration_history[0].evaluated} evaluated, {op:iteration_history[0].passed_safety} cleared the safety gate and {op:iteration_history[0].viable} stayed viable.",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "candidates",
            "title": {"es": "Los que quedaron", "en": "The ones that survived"},
            "claims": [
                "candidates",
                "best_candidate",
                "best_candidate_full",
                "drug_candidate_class",
            ],
            "scene": scene_candidates(r),
            "beats": [
                {
                    "es": "Quedaron {candidates|count} candidatos ordenados por su puntuación.",
                    "en": "{candidates|count} candidates remain, ranked by score.",
                    "focus": {"ranking": True},
                },
                {
                    "es": "El mejor es {b:sequence}, de {pp:length} aminoácidos y {b:molecular_weight_da|n1} Da.",
                    "en": "The best is {b:sequence}, {pp:length} amino acids and {b:molecular_weight_da|n1} Da.",
                },
                {
                    "es": "Viene de {b:original_sequence} y conserva los cambios que mejoraron su puntuación.",
                    "en": "It comes from {b:original_sequence} and keeps the changes that improved its score.",
                    "focus": {"changes": True},
                },
                {
                    "es": "Propiedades que deciden si un péptido sobrevive en el cuerpo: carga neta {b:net_charge}, punto isoeléctrico {pp:isoelectric_point|n2}, hidrofobicidad GRAVY {pp:gravy_score|n2}.",
                    "en": "The properties that decide whether a peptide survives in the body: net charge {b:net_charge}, isoelectric point {pp:isoelectric_point|n2}, GRAVY hydrophobicity {pp:gravy_score|n2}.",
                },
                {
                    "es": "Vida media en suero {b:serum_half_life_hours|n1} h, resistencia a proteasas {b:protease_resistance}, riesgo de agregación {b:aggregation_risk}.",
                    "en": "Serum half-life {b:serum_half_life_hours|n1} h, protease resistance {b:protease_resistance}, aggregation risk {b:aggregation_risk}.",
                },
            ],
        },
        {
            "id": "structure",
            "title": {"es": "La forma del mejor", "en": "The shape of the best one"},
            "claims": [
                S45,
                S10,
                f"{BEST}.analyses.protenix_structure",
                f"{BEST}.analyses.chai1_structure",
                f"{BEST}.mol_3d",
                "mol_3d",
                "structure_3d",
                "enhancements",
                "protenix_structure",
                "complexa_binders",
                "images",
            ],
            "scene": scene_structure(r, mesh_keys),
            "beats": [
                {
                    "es": "El péptido plegado, dibujado por PyMOL y construido residuo a residuo.",
                    "en": "The folded peptide, drawn by PyMOL and built residue by residue.",
                    "focus": {"grow": True},
                    "requires_mesh": "peptide",
                    "gap": [f"{BEST}.analyses.protenix_structure", "structure_3d"],
                    "gap_es": "Sin estructura del péptido",
                    "gap_en": "No peptide structure",
                },
                {
                    "es": "Confianza del modelo: pLDDT {px:plddt|n1}, pTM {px:ptm|n3}, ipTM {px:iptm|n3}.",
                    "en": "Model confidence: pLDDT {px:plddt|n1}, pTM {px:ptm|n3}, ipTM {px:iptm|n3}.",
                    "focus": {"color": "plddt"},
                },
                {
                    "es": "Complexa no diseñó uniones para este blanco: {cx:reason}.",
                    "en": "Complexa designed no binders for this target: {cx:reason}.",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "docking",
            "title": {"es": "¿Se pega al blanco?", "en": "Does it stick to the target?"},
            "claims": [S9],
            "scene": {"type": "panel", "root": S9},
            "beats": [
                {
                    "es": "Contra {dk:pdb_id}, de {dk:pdb_source}: confianza de interfaz ipTM {dk:interface_confidence_iptm|n3}.",
                    "en": "Against {dk:pdb_id}, from {dk:pdb_source}: interface confidence ipTM {dk:interface_confidence_iptm|n3}.",
                    "gap": [S9],
                    "gap_es": "Sin acoplamiento",
                    "gap_en": "No docking",
                },
                {
                    "es": "No hay energía de unión, y la corrida explica por qué: {dk:binding_affinity_kcal_honest.null_reason}.",
                    "en": "There is no binding energy, and the run explains why: {dk:binding_affinity_kcal_honest.null_reason}.",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "safety",
            "title": {"es": "ADMET, toxicidad y ensayo", "en": "ADMET, toxicity and trial"},
            "claims": [S4, S5, S6, S8, "toxicology", "admet", "pharmacology", "clinical_trial"],
            "scene": {"type": "panel", "root": S5},
            "beats": [
                {
                    "es": "{admet_stage:stage}: {admet_stage:status}.",
                    "en": "{admet_stage:stage}: {admet_stage:status}.",
                    "gap": [S5],
                    "gap_es": "Sin ADMET",
                    "gap_en": "No ADMET",
                },
                {
                    "es": "{tox_stage:stage}: {tox_stage:status}.",
                    "en": "{tox_stage:stage}: {tox_stage:status}.",
                },
                {
                    "es": "{trial_stage:stage}: {trial_stage:status}.",
                    "en": "{trial_stage:stage}: {trial_stage:status}.",
                },
            ],
        },
        {
            "id": "score",
            "title": {"es": "La nota final", "en": "The final score"},
            "claims": [S11, "composite_score", "score_breakdown"],
            "scene": scene_score(r),
            "beats": [
                {
                    "es": "Puntuación compuesta {sc:composite_score|n4}, clase {sc:drug_candidate_class}, por el método {sc:hybrid_method}.",
                    "en": "Composite score {sc:composite_score|n4}, class {sc:drug_candidate_class}, by the {sc:hybrid_method} method.",
                    "focus": {"bars": True},
                },
                {
                    "es": "Comprobado aquí: la suma ponderada de las partes, más el bono de péptido, da esa puntuación.",
                    "en": "Checked here: the weighted parts plus the peptide bonus give that score.",
                    "kind": "check",
                    "requires_check": "composite",
                },
                {
                    "es": "Pero esas partes no suman la nota publicada: rehechas aquí dan otra cifra. El desglose está en «datos».",
                    "en": "But those parts do not add up to the published score: redone here they give a different figure. The breakdown is under «datos».",
                    "kind": "gap",
                    "requires_failed_check": "composite",
                },
                {
                    "es": "Un péptido recibe un bono de {sc:peptide_bonus|n4} sobre la nota base.",
                    "en": "A peptide receives a {sc:peptide_bonus|n4} bonus over the base score.",
                    "kind": "note",
                },
                {
                    "es": "Los pesos vienen de {sc:weight_justification}.",
                    "en": "The weights come from {sc:weight_justification}.",
                    "kind": "note",
                },
                {
                    "es": "Señales de seguridad: {sc:safety_flags}.",
                    "en": "Safety flags: {sc:safety_flags}.",
                },
            ],
        },
    ]


def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    for p in (
        f"{BEST}.analyses.chai1_structure.pdb",
        "structure_3d.pdb",
        f"{BEST}.mol_3d.protein_pdb",
        "mol_3d.protein_pdb",
    ):
        pdb = F.get(r, p)
        if F.is_pdb(pdb):
            return [{"key": "peptide", "pdb": pdb, "label": p}]
    return []


def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    # the mutations the run labelled, against the sequences it stored
    labelled = F.get(r, f"{BEST}.mutations")
    derived = [
        c["label"]
        for c in diff(F.get(r, f"{BEST}.original_sequence"), F.get(r, f"{BEST}.sequence"))
    ]
    if isinstance(labelled, list) and derived:
        ok = [str(x) for x in labelled] == derived
        out.append(
            {
                "id": "mutations",
                "ok": ok,
                "es": f"comparar la secuencia con su original da {', '.join(derived)}, y la corrida anota "
                + (f"lo mismo" if ok else f"{', '.join(map(str, labelled))}"),
                "en": f"comparing the sequence with its original gives {', '.join(derived)}, and the run records "
                + ("the same" if ok else f"{', '.join(map(str, labelled))}"),
                "paths": [f"{BEST}.sequence", f"{BEST}.original_sequence", f"{BEST}.mutations"],
            }
        )
    bd = F.get(r, f"{S11}.score_breakdown") or {}
    comp = F.get(r, f"{S11}.composite_score")
    bonus = F.get(r, f"{S11}.peptide_bonus") or 0
    parts = [
        v
        for v in bd.values()
        if isinstance(v, dict) and isinstance(v.get("weighted"), (int, float))
    ]
    if parts and isinstance(comp, (int, float)):
        total = sum(v["weighted"] for v in parts) + (
            bonus if isinstance(bonus, (int, float)) else 0
        )
        ok = abs(total - comp) <= 0.005
        out.append(
            {
                "id": "composite",
                "ok": ok,
                "es": f"las {len(parts)} partes ponderadas más el bono {bonus} suman {total:.4f}, y la nota publicada es {comp:.4f}",
                "en": f"the {len(parts)} weighted parts plus the {bonus} bonus add up to {total:.4f}, and the published score is {comp:.4f}",
                "paths": [
                    f"{S11}.score_breakdown",
                    f"{S11}.peptide_bonus",
                    f"{S11}.composite_score",
                ],
            }
        )
    return out


# MOLEVERA / BIOQL
