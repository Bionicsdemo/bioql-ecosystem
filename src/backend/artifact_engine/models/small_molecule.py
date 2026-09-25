"""
Artifact model for the small-molecule discovery pipeline (`CUSTOM_MOLECULE`).

The molecule itself is the star: the run already carries an MMFF94-optimised 3D
conformer as an MDL block, so the page draws the real atoms and bonds rather
than a picture of them. Around it the chapters follow the pipeline's stages --
properties and drug-likeness, ADMET, toxicology, pharmacokinetics, the target
structure and docking, the designed binders, the quantum work, the simulated
trial, and the composite score with its safety gate.

Two things are recomputed here and stated as checks: the atom counts of the 3D
block against the formula the pipeline reported, and the weighted sum of the
score breakdown against the composite score it published.

MOLEVERA / BIOQL
"""

from typing import Any, Dict, List, Optional

from .. import facts as F
from .. import molecule as MOL

PIPELINE = "CUSTOM_MOLECULE"
TITLE = {"es": "Molécula pequeña", "en": "Small molecule"}

S0, SQ = "stages.0_molecule_analysis", "stages.0c_qsvm_classification"
S1, S2, S3 = "stages.1_quantum_78_algorithms", "stages.2_admet", "stages.3_toxicology"
S4, S5, S6 = "stages.4_pharmacology", "stages.5_clinical_trial", "stages.6_docking"
S7, S7B, S7C = "stages.7_3d_structure", "stages.7b_protenix_structure", "stages.7c_complexa"
S7QC, S8 = "stages.7c_quantum_chemistry", "stages.8_scoring"
ALIASES = {
    "m": S0,
    "ad": f"{S2}.data",
    "tx": f"{S3}.data",
    "ph": f"{S4}.data",
    "cl": f"{S5}.data",
    "dk": S6,
    "px": S7B,
    "cx": S7C,
    "qc": S7QC,
    "sc": S8,
    "q78": S1,
    "qsvm": SQ,
    "d3": S7,
}


def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    return str(r.get("pipeline", "")) == PIPELINE or (
        isinstance(r.get("stages"), dict) and "0_molecule_analysis" in r["stages"]
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
    name = F.get(r, "best_candidate.name") or F.get(r, "molecule.smiles") or ""
    tgt = str(F.get(r, "target_name") or F.get(r, "target") or "").split()[0:1]
    return " → ".join(x for x in (str(name)[:42], tgt[0] if tgt else "") if x)


def mol3d(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for p in (f"{S7}.mol_block", "mol_3d.ligand_sdf", "best_candidate.mol_3d.ligand_sdf"):
        m = MOL.parse(F.get(r, p))
        if m:
            m["path"] = p
            return m
    return None


# ── scenes ─────────────────────────────────────────────────────────────────────────
def scene_molecule(r: Dict[str, Any]) -> Dict[str, Any]:
    m = mol3d(r) or {}
    return {
        "type": "molecule",
        "atoms": m.get("atoms", []),
        "bonds": m.get("bonds", []),
        "span": m.get("span"),
        "formula": F.get(r, f"{S0}.properties.formula"),
        "motifs": F.get(r, f"{S0}.detected_motifs") or [],
        "properties": F.get(r, f"{S0}.properties") or {},
    }


def scene_druglike(r: Dict[str, Any]) -> Dict[str, Any]:
    p = F.get(r, f"{S0}.properties") or {}
    dl = F.get(r, f"{S0}.drug_likeness") or {}
    # Lipinski's four, each with the threshold the rule states
    rules = [
        ("MW", p.get("molecular_weight"), 500, "≤"),
        ("logP", p.get("logp"), 5, "≤"),
        ("TPSA", p.get("tpsa"), 140, "≤"),
        ("rot. bonds", p.get("num_rotatable_bonds"), 10, "≤"),
    ]
    return {
        "type": "rules",
        "rules": [
            {
                "name": n,
                "value": v,
                "limit": lim,
                "op": op,
                "pass": None if not isinstance(v, (int, float)) else v <= lim,
            }
            for n, v, lim, op in rules
        ],
        "violations": dl.get("lipinski_violations"),
        "brenk": dl.get("brenk_alerts"),
        "pains": dl.get("pains_alerts"),
        "drug_like": dl.get("drug_like"),
    }


def _endpoints(block: Any, keys: List[str]) -> List[Dict[str, Any]]:
    out = []
    for group in keys:
        g = (block or {}).get(group)
        if not isinstance(g, dict):
            continue
        for k, v in g.items():
            if isinstance(v, dict) and isinstance(v.get("value"), (int, float)):
                out.append(
                    {
                        "group": group,
                        "name": k,
                        "value": v["value"],
                        "label": v.get("label"),
                        "unit": v.get("unit"),
                        "note": v.get("interpretation"),
                    }
                )
    return out


def scene_admet(r: Dict[str, Any]) -> Dict[str, Any]:
    d = F.get(r, f"{S2}.data") or {}
    return {
        "type": "endpoints",
        "model": d.get("model"),
        "n": d.get("n_endpoints"),
        "items": _endpoints(
            d, ["absorption", "distribution", "metabolism", "excretion", "toxicity"]
        ),
    }


def scene_tox(r: Dict[str, Any]) -> Dict[str, Any]:
    d = F.get(r, f"{S3}.data") or {}
    return {
        "type": "endpoints",
        "model": d.get("method"),
        "n": None,
        "score": d.get("overall_score"),
        "items": _endpoints(
            d, ["acute_toxicity", "genotoxicity", "organ_toxicity", "special_toxicity"]
        ),
    }


def scene_pk(r: Dict[str, Any]) -> Dict[str, Any]:
    d = F.get(r, f"{S4}.data") or {}
    return {
        "type": "pk",
        "half_life_h": d.get("half_life_hours"),
        "bioavailability": d.get("bioavailability"),
        "score": d.get("overall_score"),
        "pk": d.get("pharmacokinetics") or {},
        "pd": d.get("pharmacodynamics") or {},
    }


def scene_target(r: Dict[str, Any], mesh_keys: Dict[str, str]) -> Dict[str, Any]:
    return {
        "type": "complex",
        "mesh": mesh_keys.get("target"),
        "ligand": (mol3d(r) or {}).get("atoms", []),
        "bonds": (mol3d(r) or {}).get("bonds", []),
        "site": F.get(r, "mol_3d.binding_site"),
        "pdb_id": F.get(r, "target_structure.pdb_id"),
        "affinity_kcal": F.get(r, f"{S6}.binding_affinity_kcal"),
        "poses": F.get(r, f"{S6}.poses_generated"),
    }


def scene_binders(r: Dict[str, Any]) -> Dict[str, Any]:
    bs = [b for b in (F.get(r, f"{S7C}.binders") or []) if isinstance(b, dict)]
    return {
        "type": "binders",
        "binders": [
            {
                "id": b.get("design_id"),
                "len": b.get("length"),
                "plddt": b.get("plddt"),
                "iptm": b.get("iptm"),
            }
            for b in bs
        ],
        "best_plddt": F.get(r, f"{S7C}.best_plddt"),
        "best_ipae": F.get(r, f"{S7C}.best_ipae"),
        "gpu": F.get(r, f"{S7C}.gpu"),
    }


def scene_score(r: Dict[str, Any]) -> Dict[str, Any]:
    bd = F.get(r, f"{S8}.score_breakdown") or {}
    return {
        "type": "score",
        "composite": F.get(r, f"{S8}.composite_score"),
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
        "klass": F.get(r, f"{S8}.drug_candidate_class"),
        "flags": F.get(r, f"{S8}.safety_flags") or [],
        "gate": F.get(r, "safety_gate") or {},
    }


# ── chapters ───────────────────────────────────────────────────────────────────────
def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "overview",
            "title": {"es": "La molécula y su blanco", "en": "The molecule and its target"},
            "claims": [
                "pipeline",
                "pipeline_id",
                "mode",
                "target",
                "target_name",
                "timestamp",
                "molecule",
                "compound_class",
                "pdb_id",
                "target_structure",
                "quantum_backend",
                "_quantum_backend_resolved",
                "_quantum_real_ibm",
                "quantum_chemistry_validated",
                SQ,
            ],
            "scene": scene_molecule(r),
            "beats": [
                {
                    "es": "Una corrida del pipeline {pipeline} sobre {target_name}, registrada el {timestamp}.",
                    "en": "A run of the {pipeline} pipeline against {target_name}, recorded on {timestamp}.",
                },
                {
                    "es": "La molécula candidata: {molecule.smiles}.",
                    "en": "The candidate molecule: {molecule.smiles}.",
                },
                {
                    "es": "Fórmula {m:properties.formula}, {m:properties.num_heavy_atoms} átomos pesados y {m:properties.molecular_weight|n1} Da.",
                    "en": "Formula {m:properties.formula}, {m:properties.num_heavy_atoms} heavy atoms and {m:properties.molecular_weight|n1} Da.",
                    "tech": {
                        "es": "logP {m:properties.logp|n2} · TPSA {m:properties.tpsa|n1} Å² · enlaces rotables {m:properties.num_rotatable_bonds}",
                        "en": "logP {m:properties.logp|n2} · TPSA {m:properties.tpsa|n1} Å² · rotatable bonds {m:properties.num_rotatable_bonds}",
                    },
                    "focus": {"spin": True},
                },
                {
                    "es": "El conformero en 3D que ves es el que la corrida guardó, optimizado con {d3:method}.",
                    "en": "The 3D conformer you see is the one the run stored, optimised with {d3:method}.",
                    "requires_check": "formula",
                },
                {
                    "es": "Clasificada como {compound_class} por {qsvm:stage}, que cayó a la ruta clásica: {qsvm:reason}.",
                    "en": "Classified as {compound_class} by {qsvm:stage}, which fell back to the classical path: {qsvm:reason}.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "druglike",
            "title": {"es": "¿Parece un fármaco?", "en": "Does it look like a drug?"},
            "claims": [],
            "scene": scene_druglike(r),
            "beats": [
                {
                    "es": "Las reglas de Lipinski miran masa, lipofilia, superficie polar y flexibilidad: esta molécula incumple {m:drug_likeness.lipinski_violations} de ellas.",
                    "en": "Lipinski's rules look at mass, lipophilicity, polar surface and flexibility: this molecule breaks {m:drug_likeness.lipinski_violations} of them.",
                    "focus": {"rules": True},
                },
                {
                    "es": "Alertas estructurales: {m:drug_likeness.brenk_alerts} de Brenk y {m:drug_likeness.pains_alerts} de PAINS, los patrones que suelen dar falsos positivos en ensayos.",
                    "en": "Structural alerts: {m:drug_likeness.brenk_alerts} Brenk and {m:drug_likeness.pains_alerts} PAINS -- the patterns that tend to give false positives in assays.",
                },
                {
                    "es": "Grupos químicos reconocidos en la estructura: {m:detected_motifs}.",
                    "en": "Chemical groups recognised in the structure: {m:detected_motifs}.",
                    "focus": {"motifs": True},
                },
                {
                    "es": "Anillos: {m:properties.num_rings} en total, {m:properties.num_aromatic_rings} aromáticos, y {m:properties.num_stereocenters} centros estereogénicos.",
                    "en": "Rings: {m:properties.num_rings} in all, {m:properties.num_aromatic_rings} aromatic, and {m:properties.num_stereocenters} stereocentres.",
                },
            ],
        },
        {
            "id": "admet",
            "title": {"es": "Qué le hace el cuerpo", "en": "What the body does to it"},
            "claims": [S2, "admet"],
            "scene": scene_admet(r),
            "beats": [
                {
                    "es": "{ad:n_endpoints} puntos finales ADMET predichos por {ad:model}: absorción, distribución, metabolismo, excreción y toxicidad.",
                    "en": "{ad:n_endpoints} ADMET endpoints predicted by {ad:model}: absorption, distribution, metabolism, excretion and toxicity.",
                    "tech": {
                        "es": "corrida en {ad:elapsed_s|n1} s",
                        "en": "computed in {ad:elapsed_s|n1} s",
                    },
                    "focus": {"endpoints": True},
                    "gap": [S2],
                    "gap_es": "Sin predicción ADMET",
                    "gap_en": "No ADMET prediction",
                },
                {
                    "es": "Absorción intestinal humana: {ad:absorption.hia.value|n2} ({ad:absorption.hia.label}).",
                    "en": "Human intestinal absorption: {ad:absorption.hia.value|n2} ({ad:absorption.hia.label}).",
                    "tech": {
                        "es": "interpretación del modelo: {ad:absorption.hia.interpretation} · solubilidad {ad:absorption.solubility.value|n2} {ad:absorption.solubility.unit}",
                        "en": "model reading: {ad:absorption.hia.interpretation} · solubility {ad:absorption.solubility.value|n2} {ad:absorption.solubility.unit}",
                    },
                    "focus": {"group": "absorption"},
                },
                {
                    "es": "Señales de toxicidad del mismo modelo: AMES {ad:toxicity.ames.value|n2}, daño hepático {ad:toxicity.dili.value|n2}, hERG {ad:toxicity.herg.value|n2}.",
                    "en": "Toxicity signals from the same model: AMES {ad:toxicity.ames.value|n2}, liver injury {ad:toxicity.dili.value|n2}, hERG {ad:toxicity.herg.value|n2}.",
                    "focus": {"group": "toxicity"},
                },
            ],
        },
        {
            "id": "tox",
            "title": {"es": "Toxicología", "en": "Toxicology"},
            "claims": [S3, "toxicology"],
            "scene": scene_tox(r),
            "beats": [
                {
                    "es": "Estudio de toxicología por {tx:method}, sobre {tx:backend}; puntuación global {tx:overall_score|n3}.",
                    "en": "Toxicology study by {tx:method}, on {tx:backend}; overall score {tx:overall_score|n3}.",
                    "tech": {
                        "es": "{tx:quantum_jobs|count} trabajo(s) cuántico(s) · en simulador: {tx:ran_on_simulator}",
                        "en": "{tx:quantum_jobs|count} quantum job(s) · on a simulator: {tx:ran_on_simulator}",
                    },
                    "focus": {"endpoints": True},
                    "gap": [S3],
                    "gap_es": "Sin estudio de toxicología",
                    "gap_en": "No toxicology study",
                },
                {
                    "es": "Dosis letal media oral estimada: {tx:acute_toxicity.ld50_oral.value|n1} {tx:acute_toxicity.ld50_oral.unit}, clase GHS {tx:acute_toxicity.ld50_oral.ghs_class}.",
                    "en": "Estimated oral median lethal dose: {tx:acute_toxicity.ld50_oral.value|n1} {tx:acute_toxicity.ld50_oral.unit}, GHS class {tx:acute_toxicity.ld50_oral.ghs_class}.",
                    "tech": {
                        "es": "incertidumbre {tx:acute_toxicity.ld50_oral.uncertainty} · confianza {tx:acute_toxicity.ld50_oral.confidence}",
                        "en": "uncertainty {tx:acute_toxicity.ld50_oral.uncertainty} · confidence {tx:acute_toxicity.ld50_oral.confidence}",
                    },
                    "focus": {"group": "acute_toxicity"},
                },
                {
                    "es": "Corrió en simulador, no en hardware cuántico: {tx:ran_on_simulator}.",
                    "en": "It ran on a simulator, not on quantum hardware: {tx:ran_on_simulator}.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "pk",
            "title": {"es": "Farmacocinética", "en": "Pharmacokinetics"},
            "claims": [S4, "pharmacology"],
            "scene": scene_pk(r),
            "beats": [
                {
                    "es": "Biodisponibilidad predicha {ph:bioavailability|n1}% y vida media {ph:half_life_hours|n1} horas.",
                    "en": "Predicted bioavailability {ph:bioavailability|n1}% and half-life {ph:half_life_hours|n1} hours.",
                    "focus": {"curve": True},
                    "gap": [S4],
                    "gap_es": "Sin farmacocinética",
                    "gap_en": "No pharmacokinetics",
                },
                {
                    "es": "Unión a proteínas del plasma {ph:pharmacokinetics.distribution.ppb.value|n1}% y probabilidad de cruzar la barrera hematoencefálica {ph:pharmacokinetics.distribution.bbb_probability|n2}.",
                    "en": "Plasma protein binding {ph:pharmacokinetics.distribution.ppb.value|n1}% and blood-brain barrier crossing probability {ph:pharmacokinetics.distribution.bbb_probability|n2}.",
                },
                {
                    "es": "Puntuación global de farmacología: {ph:overall_score|n3}.",
                    "en": "Overall pharmacology score: {ph:overall_score|n3}.",
                },
            ],
        },
        {
            "id": "target",
            "title": {"es": "El blanco y el acoplamiento", "en": "The target and the docking"},
            "claims": [S6, "mol_3d", S7, S7B],
            "scene": scene_target(r, mesh_keys),
            "beats": [
                {
                    "es": "La proteína blanco es {target_structure.pdb_id}, tomada de {target_structure.source}; PyMOL la dibuja aquí con el ligando en su sitio de unión.",
                    "en": "The target protein is {target_structure.pdb_id}, taken from {target_structure.source}; PyMOL draws it here with the ligand at its binding site.",
                    "focus": {"grow": True},
                    "requires_mesh": "target",
                    "gap": ["mol_3d", "stages.6_docking"],
                    "gap_es": "Sin estructura del blanco",
                    "gap_en": "No target structure",
                },
                {
                    "es": "El acoplamiento no produjo resultado en esta corrida: {dk:status}, {dk:poses_generated} poses.",
                    "en": "Docking produced no result in this run: {dk:status}, {dk:poses_generated} poses.",
                    "kind": "gap",
                },
                {
                    "es": "Protenix pliega el complejo con {px:model_used} en {px:gpu}: pLDDT {px:confidence.plddt|n1}, pTM {px:confidence.ptm|n3}, ipTM {px:confidence.iptm|n3}.",
                    "en": "Protenix folds the complex with {px:model_used} on {px:gpu}: pLDDT {px:confidence.plddt|n1}, pTM {px:confidence.ptm|n3}, ipTM {px:confidence.iptm|n3}.",
                    "tech": {
                        "es": "{px:prediction_time_seconds|n1} s · trabajo {px:job_id} · puntuación de ranking {px:confidence.ranking_score|n3}",
                        "en": "{px:prediction_time_seconds|n1} s · job {px:job_id} · ranking score {px:confidence.ranking_score|n3}",
                    },
                    "focus": {"confidence": True},
                },
            ],
        },
        {
            "id": "binders",
            "title": {"es": "Uniones diseñadas", "en": "Designed binders"},
            "claims": [S7C, "complexa_binders"],
            "scene": scene_binders(r),
            "beats": [
                {
                    "es": "Complexa diseñó {cx:num_binders} proteínas que se unen al mismo blanco, en {cx:gpu}.",
                    "en": "Complexa designed {cx:num_binders} proteins that bind the same target, on {cx:gpu}.",
                    "focus": {"binders": True},
                    "gap": [S7C],
                    "gap_es": "Sin uniones diseñadas",
                    "gap_en": "No designed binders",
                },
                {
                    "es": "La mejor alcanza pLDDT {cx:best_plddt|n2} e ipAE {cx:best_ipae|n3}.",
                    "en": "The best reaches pLDDT {cx:best_plddt|n2} and ipAE {cx:best_ipae|n3}.",
                },
            ],
        },
        {
            "id": "quantum",
            "title": {"es": "La parte cuántica", "en": "The quantum part"},
            "claims": [
                S1,
                S7QC,
                "stages.7d_qaoa_weights",
                "ibm_job_ids",
                "execution_mode",
                "quantum_hardware",
                "on_real_quantum_hardware",
            ],
            "scene": {"type": "panel", "root": S1},
            "beats": [
                {
                    "es": "El lote de algoritmos cuánticos iba a correr en {q78:backend} y terminó en {q78:status}: ningún algoritmo llegó a ejecutarse.",
                    "en": "The quantum algorithm batch was to run on {q78:backend} and ended in {q78:status}: no algorithm ever executed.",
                    "kind": "gap",
                },
                {
                    "es": "La química cuántica ab initio tampoco corrió: {qc:reason}.",
                    "en": "The ab-initio quantum chemistry did not run either: {qc:reason}.",
                    "kind": "gap",
                },
                {
                    "es": "Por eso la validación por química cuántica queda en {sc:quantum_chemistry_validated}: la puerta no se cruzó.",
                    "en": "So the quantum-chemistry validation stands at {sc:quantum_chemistry_validated}: the gate was not passed.",
                    "kind": "note",
                },
            ],
        },
        {
            "id": "clinical",
            "title": {"es": "El ensayo simulado", "en": "The simulated trial"},
            "claims": [S5, "clinical_trial"],
            "scene": {"type": "panel", "root": f"{S5}.data"},
            "beats": [
                {
                    "es": "Fase I simulada: {cl:phase_1.design}, {cl:phase_1.sample_size} personas, objetivo {cl:phase_1.objective}.",
                    "en": "Simulated phase I: {cl:phase_1.design}, {cl:phase_1.sample_size} people, objective {cl:phase_1.objective}.",
                    "gap": [S5],
                    "gap_es": "Sin simulación de ensayo",
                    "gap_en": "No trial simulation",
                },
                {
                    "es": "Probabilidad global de aprobación: no se da un número, y la corrida dice por qué: {cl:overall_approval_probability.null_reason}",
                    "en": "Overall approval probability: no number is given, and the run says why: {cl:overall_approval_probability.null_reason}",
                    "kind": "gap",
                },
            ],
        },
        {
            "id": "score",
            "title": {
                "es": "La nota final y la puerta de seguridad",
                "en": "The final score and the safety gate",
            },
            "claims": [
                S8,
                "composite_score",
                "safety_gate",
                "candidates",
                "best_candidate",
                "best_candidate_full",
                "drug_candidate_class",
                "compound_class_confidence",
                "summary",
                "insights",
                "provenance",
                "recommendations",
            ],
            "scene": scene_score(r),
            "beats": [
                {
                    "es": "Puntuación compuesta {sc:composite_score|n3}, que la corrida clasifica como {sc:drug_candidate_class}.",
                    "en": "Composite score {sc:composite_score|n3}, which the run classes as {sc:drug_candidate_class}.",
                    "tech": {
                        "es": "pesos: {sc:scoring_weights}",
                        "en": "weights: {sc:scoring_weights}",
                    },
                    "focus": {"bars": True},
                },
                {
                    "es": "Comprobado aquí: la suma ponderada de las partes da exactamente esa puntuación.",
                    "en": "Checked here: the weighted parts add up to exactly that score.",
                    "kind": "check",
                    "requires_check": "composite",
                },
                {
                    "es": "Pero las partes no suman esa nota: rehechas aquí dan otra cifra, y la diferencia está en la corrida. El desglose exacto está en «datos».",
                    "en": "But the parts do not add up to that score: redone here they give a different figure, and the difference is in the run. The exact breakdown is under \u00abdatos\u00bb.",
                    "kind": "gap",
                    "requires_failed_check": "composite",
                },
                {
                    "es": "Los pesos no son arbitrarios: {sc:weight_justification}.",
                    "en": "The weights are not arbitrary: {sc:weight_justification}.",
                    "kind": "note",
                },
                {
                    "es": "El acoplamiento pesa {sc:scoring_weights.docking|n2} en esta corrida, así que la nota no depende de él.",
                    "en": "Docking carries weight {sc:scoring_weights.docking|n2} in this run, so the score does not rest on it.",
                    "kind": "note",
                },
                {
                    "es": "Señales de seguridad levantadas: {sc:safety_flags}.",
                    "en": "Safety flags raised: {sc:safety_flags}.",
                    "focus": {"flags": True},
                },
                {
                    "es": "Aun así la puerta de seguridad marca {safety_gate.severity} y descalificación {sc:safety_disqualified}: la contradicción está en la corrida, no en esta página.",
                    "en": "Yet the safety gate reads {safety_gate.severity} and disqualified {sc:safety_disqualified}: the contradiction is in the run, not on this page.",
                    "kind": "note",
                },
            ],
        },
    ]


def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    pdb = F.get(r, "mol_3d.protein_pdb") or F.get(r, "best_candidate.mol_3d.protein_pdb")
    return [{"key": "target", "pdb": pdb, "label": "mol_3d.protein_pdb"}] if F.is_pdb(pdb) else []


def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    m = mol3d(r)
    formula = F.get(r, f"{S0}.properties.formula")
    if m and isinstance(formula, str):
        import re

        want = {e: int(n or 1) for e, n in re.findall(r"([A-Z][a-z]?)(\d*)", formula) if e}
        ok = want == m["counts"]
        out.append(
            {
                "id": "formula",
                "ok": ok,
                "es": f"el bloque 3D tiene {m['n_atoms']} átomos y {m['n_bonds']} enlaces, y su cuenta por elemento "
                + (
                    "coincide con la fórmula " + formula
                    if ok
                    else f"NO coincide con {formula}: {m['counts']}"
                ),
                "en": f"the 3D block has {m['n_atoms']} atoms and {m['n_bonds']} bonds, and its per-element count "
                + (
                    "matches the formula " + formula
                    if ok
                    else f"does NOT match {formula}: {m['counts']}"
                ),
                "paths": [m["path"], f"{S0}.properties.formula"],
            }
        )
    bd = F.get(r, f"{S8}.score_breakdown") or {}
    comp = F.get(r, f"{S8}.composite_score")
    parts = [
        v
        for v in bd.values()
        if isinstance(v, dict) and isinstance(v.get("weighted"), (int, float))
    ]
    if parts and isinstance(comp, (int, float)):
        total = sum(v["weighted"] for v in parts)
        ok = abs(total - comp) <= 0.005
        out.append(
            {
                "id": "composite",
                "ok": ok,
                "es": f"las {len(parts)} partes ponderadas suman {total:.3f} y la puntuación compuesta es {comp:.3f}",
                "en": f"the {len(parts)} weighted parts add up to {total:.3f} and the composite score is {comp:.3f}",
                "paths": [f"{S8}.score_breakdown", f"{S8}.composite_score"],
            }
        )
    return out


# MOLEVERA / BIOQL
