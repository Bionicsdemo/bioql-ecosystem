"""
Artifact model for the macrocycle design pipeline (`macrocycle_design`).

The subject of this run is a ring, so the page is built around whether that ring
is real. Three of the five chapters exist because the pipeline's failure modes
are silent ones: a macrocycle whose ring never closed is a linear peptide that
still computes descriptors and still docks; an ensemble that never converged
means the bioactive conformer was never in the box; and a population that shrank
between stages turns the final ranking into a ranking of whatever survived
embedding, which is not the same as whatever is good.

So the chapters are: what was asked and built, whether the rings closed, the
conformational ensembles and what they are missing, the property space these
compounds live in -- which is bRo5, not the rule of five -- and where the run
decided quantum chemistry would change an answer.

Four things are recomputed here rather than trusted: that the built count plus
the dropped count equals what was requested, that every drop carries a reason,
that the ensemble population is conserved, and that the compute budget's
percentages match the seconds it reports.

Nothing here claims potency. The run does not dock unless a structure arrives,
and macrocycle docking scores correlate poorly with measured affinity even when
they are computed, so the ranking is presented as triage for assay.

MOLEVERA / BIOQL
"""

from typing import Any, Dict, List

from .. import facts as F

PIPELINE = "macrocycle_design"
TITLE = {"es": "Macrociclos peptídicos", "en": "Peptide macrocycles"}

S1, S2 = "stages.1_build", "stages.2_conformers"
S3, S4 = "stages.3_properties", "stages.4_quantum_triage"
S4B, S5 = "stages.4b_quantum_run", "stages.5_rank"

ALIASES = {
    "b": S1,
    "c": S2,
    "p": S3,
    "q": S4,
    "qr": S4B,
    # El primer candidato que de verdad corrió: es de donde salen las cifras de
    # la región, que son el argumento entero de este escenario.
    "reg": f"{S4B}.results[0].region",
    "r": S5,
    "pop": f"{S2}.population",
    "conv": f"{S2}.convergence",
    "bud": "compute_budget",
    "top": "best_candidate",
}


def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    if not isinstance(r, dict):
        return False
    if str(r.get("pipeline", "")) == PIPELINE:
        return True
    # A run that lost its pipeline id is still this one if it carries the two
    # blocks only this pipeline writes.
    st = r.get("stages")
    return isinstance(st, dict) and "1_build" in st and "4_quantum_triage" in st


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("result"), dict):
        inner = result["result"]
        if "stages" in inner or str(inner.get("pipeline", "")) == PIPELINE:
            return dict(inner)
    return result


def subject(r: Dict[str, Any]) -> str:
    bits = [str(r.get("target") or "").strip()]
    cyc = str(r.get("cyclization") or "").replace("_", "-")
    if cyc:
        bits.append(cyc)
    n = F.get(r, f"{S1}.built")
    if n is not None:
        bits.append(f"{n} macrociclos")
    return " · ".join(b for b in bits if b)


def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """No structures to draw.

    This pipeline builds ligands, not folds: there is no protein PDB in the run
    unless a target structure was supplied, and a macrocycle conformer is a small
    molecule rather than a cartoon. Returning nothing is the honest answer, and
    every sentence that would have described a picture becomes a declared gap."""
    return []


# ── checks: recomputed from the run's own numbers ─────────────────────────────
def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def add(cid: str, ok: bool, es: str, en: str, paths: List[str]) -> None:
        out.append({"id": cid, "ok": bool(ok), "es": es, "en": en, "paths": paths})

    # 1 -- nobody vanished between the request and the build.
    req = F.get(r, f"{S1}.requested")
    built = F.get(r, f"{S1}.built")
    drop = F.get(r, f"{S1}.dropped")
    if isinstance(req, int) and isinstance(built, int) and isinstance(drop, int):
        add(
            "build_accounted",
            req == built + drop,
            f"Se pidieron {req} y se contabilizan {built} construidos más {drop} caídos.",
            f"{req} were asked for and {built} built plus {drop} dropped are accounted for.",
            [f"{S1}.requested", f"{S1}.built", f"{S1}.dropped"],
        )

    # 2 -- every drop says why. A candidate that disappears without a reason is a
    #      candidate the reader cannot argue with.
    drops = F.get(r, f"{S1}.drops")
    if isinstance(drops, list):
        sin = [d for d in drops if isinstance(d, dict) and not d.get("reason")]
        add(
            "drops_explained",
            not sin,
            f"Cada uno de los {len(drops)} descartes trae su razón.",
            f"Each of the {len(drops)} drops carries its reason.",
            [f"{S1}.drops"],
        )

    # 3 -- the ensemble population is conserved. This is the one that stops the
    #      final ranking from silently being a ranking of the easy-to-embed.
    pop = F.get(r, f"{S2}.population")
    if isinstance(pop, dict):
        n_in, n_out, n_drop = pop.get("n_in"), pop.get("n_out"), pop.get("n_dropped")
        if isinstance(n_in, int) and isinstance(n_out, int) and isinstance(n_drop, int):
            add(
                "ensemble_population_conserved",
                n_in == n_out + n_drop and not pop.get("dropped_without_reason"),
                f"Entraron {n_in} al embebido y salen {n_out} más {n_drop} caídos.",
                f"{n_in} entered embedding and {n_out} plus {n_drop} dropped come out.",
                [f"{S2}.population"],
            )

    # 4 -- the budget's percentages are the seconds it reports, not a separate claim.
    bud = F.get(r, "compute_budget")
    if isinstance(bud, dict) and isinstance(bud.get("achieved"), dict):
        secs = bud.get("seconds") or {}
        g, q = secs.get("gpu"), secs.get("quantum")
        got = bud["achieved"]
        if isinstance(g, (int, float)) and isinstance(q, (int, float)) and (g + q) > 0:
            want = round(q / (g + q), 3)
            add(
                "budget_arithmetic",
                abs(float(got.get("quantum", -1)) - want) < 0.01,
                f"La fracción cuántica declarada ({got.get('quantum')}) es {q} s de {g + q} s.",
                f"The declared quantum share ({got.get('quantum')}) is {q} s out of {g + q} s.",
                ["compute_budget.achieved", "compute_budget.seconds"],
            )
    return out


# ── scenes ────────────────────────────────────────────────────────────────────
def _scene_candidates(r: Dict[str, Any]) -> Dict[str, Any]:
    """Ring size per candidate: the one number that says what was built."""
    items = []
    for c in (r.get("candidates") or [])[:20]:
        if not isinstance(c, dict):
            continue
        n = c.get("ring_size")
        if isinstance(n, (int, float)):
            items.append(
                {
                    "name": str(c.get("sequence") or c.get("rank")),
                    "value": float(n),
                    "unit": "átomos",
                }
            )
    return {"type": "endpoints", "items": items} if items else {"type": "panel", "root": S1}


def _scene_properties(r: Dict[str, Any]) -> Dict[str, Any]:
    """The bRo5 axes of the leading candidate, each against its own limit."""
    d = F.get(r, "best_candidate.descriptors")
    if not isinstance(d, dict):
        return {"type": "panel", "root": S3}
    rules = []
    for campo, etiqueta, limite in (
        ("mw", "MW", 1000),
        ("clogp", "cLogP", 10),
        ("hbd", "HBD", 6),
        ("hba", "HBA", 15),
        ("tpsa", "TPSA", 250),
        ("rotb", "rot. bonds", 20),
    ):
        v = d.get(campo)
        if isinstance(v, (int, float)):
            rules.append({"name": etiqueta, "value": float(v), "limit": float(limite)})
    return {"type": "rules", "rules": rules} if rules else {"type": "panel", "root": S3}


def _scene_ensembles(r: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    for c in (r.get("candidates") or [])[:20]:
        if not isinstance(c, dict):
            continue
        n = c.get("n_conformers")
        if isinstance(n, (int, float)):
            items.append(
                {
                    "name": str(c.get("sequence") or c.get("rank")),
                    "value": float(n),
                    "unit": "confórmeros",
                }
            )
    return {"type": "endpoints", "items": items} if items else {"type": "panel", "root": S2}


def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "run",
            "title": {"es": "La corrida", "en": "The run"},
            "claims": [
                "pipeline",
                "status",
                "timestamp",
                "target",
                "indication",
                "cyclization",
                "elapsed_s",
                "quantum_backend",
                "disclaimer_es",
                "disclaimer_en",
            ],
            "scene": _scene_candidates(r),
            "beats": [
                {
                    "es": "Esta página explica una corrida de {pipeline} contra {target}.",
                    "en": "This page explains one run of {pipeline} against {target}.",
                },
                {
                    "es": "El cierre pedido fue {cyclization}, y la corrida tardó {elapsed_s|n1} s.",
                    "en": "The cyclisation asked for was {cyclization}, and the run took "
                    "{elapsed_s|n1} s.",
                },
                {
                    "es": "Indicación declarada: {indication?}.",
                    "en": "Stated indication: {indication?}.",
                },
                {"es": "{disclaimer_es}", "en": "{disclaimer_en}", "kind": "note"},
            ],
        },
        {
            "id": "build",
            "title": {"es": "¿Cerró el anillo?", "en": "Did the ring close?"},
            "claims": [S1],
            "scene": {"type": "panel", "root": S1},
            "beats": [
                {
                    "es": "Se pidieron {b:requested} macrociclos; {b:built} pasaron la "
                    "comprobación y {b:dropped} cayeron.",
                    "en": "{b:requested} macrocycles were asked for; {b:built} passed the "
                    "check and {b:dropped} were dropped.",
                },
                {"es": "{b:note_es}", "en": "{b:note_en}", "kind": "note"},
                {
                    "es": "Comprobado aquí: los construidos más los caídos son los pedidos.",
                    "en": "Checked here: the built plus the dropped are the ones requested.",
                    "kind": "check",
                    "requires_check": "build_accounted",
                },
                {
                    "es": "Comprobado aquí: cada descarte trae la razón por la que cayó.",
                    "en": "Checked here: every drop carries the reason it fell.",
                    "kind": "check",
                    "requires_check": "drops_explained",
                },
            ],
        },
        {
            "id": "ensembles",
            "title": {
                "es": "Los confórmeros, y lo que falta",
                "en": "The conformers, and what is missing",
            },
            "claims": [S2],
            "scene": _scene_ensembles(r),
            "beats": [
                {
                    "es": "Se pidieron {c:n_conformers_requested} confórmeros por candidato.",
                    "en": "{c:n_conformers_requested} conformers were asked for per candidate.",
                },
                {
                    "es": "Entraron {pop:n_in} candidatos al embebido y salieron {pop:n_out}; "
                    "{pop:n_dropped} cayeron.",
                    "en": "{pop:n_in} candidates entered embedding and {pop:n_out} came out; "
                    "{pop:n_dropped} were dropped.",
                },
                {
                    "es": "Comprobado aquí: la población se conserva y ningún candidato "
                    "desaparece sin explicación.",
                    "en": "Checked here: the population is conserved and no candidate "
                    "vanishes unexplained.",
                    "kind": "check",
                    "requires_check": "ensemble_population_conserved",
                },
                {
                    "es": "Sobre la convergencia: {conv:note_es}",
                    "en": "On convergence: {conv:note_en}",
                    "kind": "note",
                },
                {"es": "{c:note_es}", "en": "{c:note_en}", "kind": "note"},
            ],
        },
        {
            "id": "properties",
            "title": {"es": "El espacio donde viven", "en": "The space they live in"},
            "claims": [S3],
            "scene": _scene_properties(r),
            "beats": [
                {
                    "es": "El espacio evaluado es {p:space_es}.",
                    "en": "The space evaluated is {p:space_en}.",
                },
                {"es": "{p:why_es}", "en": "{p:why_en}", "kind": "note"},
                {
                    "es": "{p:n_within_bro5} de {p:n_total} candidatos caen dentro de ese espacio.",
                    "en": "{p:n_within_bro5} of {p:n_total} candidates fall inside it.",
                },
                {
                    "es": "El candidato que encabeza pesa {top:descriptors.mw|n1} Da, con "
                    "cLogP {top:descriptors.clogp|n2} y TPSA {top:descriptors.tpsa|n1} Å².",
                    "en": "The leading candidate weighs {top:descriptors.mw|n1} Da, with "
                    "cLogP {top:descriptors.clogp|n2} and TPSA {top:descriptors.tpsa|n1} Å².",
                },
            ],
        },
        {
            "id": "quantum",
            "title": {"es": "Dónde hacía falta el cuántico", "en": "Where quantum was needed"},
            "claims": [S4, S4B, "compute_budget"],
            "scene": {"type": "panel", "root": S4},
            "beats": [
                {
                    "es": "El triaje halló {q:n_eligible} candidatos donde el cuántico "
                    "cambiaría una decisión, y {q:n_classical_suffices} donde lo "
                    "clásico basta.",
                    "en": "Triage found {q:n_eligible} candidates where quantum would change "
                    "a decision, and {q:n_classical_suffices} where classical suffices.",
                },
                {
                    "es": "Las plazas que aplican en esta corrida: {q:places}.",
                    "en": "The places that apply in this run: {q:places}.",
                },
                {"es": "{q:note_es}", "en": "{q:note_en}", "kind": "note"},
                {
                    "es": "Reparto de cómputo conseguido: {bud:achieved.gpu|pct} en GPU y "
                    "{bud:achieved.quantum|pct} en cuántico.",
                    "en": "Compute split achieved: {bud:achieved.gpu|pct} on GPU and "
                    "{bud:achieved.quantum|pct} on quantum.",
                },
                {"es": "{bud:note_es}", "en": "{bud:note_en}", "kind": "note"},
                {
                    "es": "De los elegibles se corrieron {qr:n_run} y se saltaron "
                    "{qr:n_skipped}.",
                    "en": "Of those eligible, {qr:n_run} were run and {qr:n_skipped} "
                    "were skipped.",
                },
                {"es": "{qr:note_es}", "en": "{qr:note_en}", "kind": "note"},
                {
                    "es": "El cálculo no se hace sobre la molécula entera sino sobre la "
                    "región de cierre: {reg:n_heavy_region} átomos pesados de "
                    "{reg:n_heavy_molecule}, anclados en {reg:anchor}.",
                    "en": "The calculation does not run on the whole molecule but on the "
                    "closure region: {reg:n_heavy_region} heavy atoms out of "
                    "{reg:n_heavy_molecule}, anchored at {reg:anchor_en}.",
                },
                {"es": "Por qué ahí: {reg:why}", "en": "Why there: {reg:why_en}", "kind": "note"},
                {
                    "es": "Los {reg:n_caps} enlaces cortados se capan con hidrógeno, y antes "
                    "de cortar se absorbieron {reg:n_absorbed_to_repair_boundary} átomos "
                    "para que ningún corte cayera sobre un enlace que un hidrógeno no puede "
                    "restituir.",
                    "en": "The {reg:n_caps} severed bonds are capped with hydrogen, and "
                    "before cutting, {reg:n_absorbed_to_repair_boundary} atoms were absorbed "
                    "so that no cut landed on a bond a hydrogen cannot restore.",
                },
                {"es": "{reg:caveat}", "en": "{reg:caveat_en}", "kind": "note"},
                {
                    "es": "Por debajo de {qr:differential_floor_ev} eV la diferencia no se "
                    "distingue del error del método, y ese orden no significa nada.",
                    "en": "Below {qr:differential_floor_ev} eV a difference is "
                    "indistinguishable from the method's own error, and that order means "
                    "nothing.",
                    "kind": "note",
                },
                {
                    "es": "Comprobado aquí: los porcentajes del presupuesto son los segundos "
                    "que declara, no una cifra aparte.",
                    "en": "Checked here: the budget's percentages are the seconds it reports, "
                    "not a separate claim.",
                    "kind": "check",
                    "requires_check": "budget_arithmetic",
                },
            ],
        },
        {
            "id": "ranking",
            "title": {"es": "El orden, y lo que no es", "en": "The order, and what it is not"},
            "claims": [S5, "candidates", "best_candidate"],
            "scene": _scene_candidates(r),
            "beats": [
                {
                    "es": "Se ordenan {candidates|count} candidatos por {r:ordered_by}.",
                    "en": "{candidates|count} candidates are ordered by {r:ordered_by}.",
                },
                {
                    "es": "Encabeza {top:sequence}, un anillo de {top:ring_size} átomos con "
                    "{top:n_conformers} confórmeros únicos.",
                    "en": "{top:sequence} leads, a {top:ring_size}-atom ring with "
                    "{top:n_conformers} unique conformers.",
                },
                {
                    "es": "{r:not_a_potency_prediction_es}",
                    "en": "{r:not_a_potency_prediction_en}",
                    "kind": "note",
                },
            ],
        },
    ]


# MOLEVERA / BIOQL
