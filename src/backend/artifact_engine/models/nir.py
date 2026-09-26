"""
Artifact model for the NIR photosensitiser programme (`nir_protein_engine`).

This run is unlike the other seven. The others carry a candidate and ask how
good it is; this one carries three scaffolds and asks which of them is even
allowed to work -- and its most important output is usually a refusal. Arm A is
bounded by the energy-gap law, arm B's own chromophore quenches the singlet
oxygen the design would need, and arm C risks pushing absorption out of the NIR
altogether. The run says so in its own words, and the page's job is to carry
those words rather than to find a number to put in their place.

So the chapters follow the programme's shape, not a pipeline's stages: the three
arms together first, because the run itself argues that a failure is only
interpretable next to the other two; then each arm on its own; then the two
things the programme is strict about and no chapter should soften -- that a
cycle cannot be chained without a measurement from the laboratory, and what the
quantum arm actually cost, including the GPU calls it declined to make.

Nothing here supplies `isc_rate` or `photostability`: the run declares both as
out of scope, and a sentence about either would have nowhere to read it from.

This programme writes its prose in Spanish, and the report's own language is
English. Translating it would put words in the run's mouth, which is the one
thing the engine must not do, so those fields are quoted verbatim inside an
English frame -- the same split `gap_reason` already makes, where the framing
is translated and the pipeline's explanation is not.

MOLEVERA / BIOQL
"""

from typing import Any, Dict, List

from .. import facts as F

PIPELINE = "nir_photosensitizer"
TITLE = {"es": "Fotosensibilizador NIR", "en": "NIR photosensitiser"}

ARMS = ("A", "B", "C")
ALIASES = {
    "x": "cross_arm",
    "b": "cycle_boundary",
    "q": "quantum_cost_total",
    "a": "arms.A",
    "bb": "arms.B",
    "c": "arms.C",
}


def matches(result: Dict[str, Any]) -> bool:
    r = unwrap(result)
    if not isinstance(r, dict):
        return False
    if str(r.get("engine", "")).startswith("nir_"):
        return True
    if str(r.get("program", "")).startswith("nir_"):
        return True
    # A run that lost its engine id is still this one if it carries the arm
    # triple and the cycle boundary, which nothing else writes.
    arms = r.get("arms")
    return isinstance(arms, dict) and set(arms) >= {"A", "B"} and "cycle_boundary" in r


def unwrap(result: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("result"), dict):
        inner = result["result"]
        if "arms" in inner or str(inner.get("engine", "")).startswith("nir_"):
            return dict(inner)
    return result


def subject(r: Dict[str, Any]) -> str:
    ran = [
        a
        for a in ARMS
        if (F.get(r, f"arms.{a}.available") is not False)
        and isinstance(F.get(r, f"arms.{a}"), dict)
    ]
    cycle = F.get(r, "cycle")
    bits = []
    if ran:
        bits.append("arm " + "/".join(ran) if len(ran) < 3 else "arms A/B/C")
    if cycle is not None:
        bits.append(f"cycle {cycle}")
    lvl = F.get(r, "level")
    if lvl:
        bits.append(str(lvl))
    return " · ".join(bits)


# ── what the run actually managed to do ──────────────────────────────────────────
def _arm_ran(r: Dict[str, Any], arm: str) -> bool:
    """An arm ran when it has stages, not merely when it has a block."""
    blk = F.get(r, f"arms.{arm}")
    if not isinstance(blk, dict):
        return False
    if blk.get("available") is False:
        return False
    return isinstance(blk.get("stages"), dict) and bool(blk["stages"])


def _pdb_in_arm(r: Dict[str, Any], arm: str):
    for p in (
        f"arms.{arm}.stages.structure.pdb",
        f"arms.{arm}.stages.structure.pdb_text",
        f"arms.{arm}.stages.structure.structure.pdb",
    ):
        v = F.get(r, p)
        if F.is_pdb(v):
            return v, p
    return None, None


def mesh_targets(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A cartoon per arm that actually folded something.

    An arm declared unavailable has no structure, and every sentence that would
    have described one becomes a declared gap instead."""
    out = []
    for arm in ARMS:
        pdb, path = _pdb_in_arm(r, arm)
        if pdb:
            out.append({"key": f"arm{arm}", "pdb": pdb, "label": path})
    return out


# ── checks: recomputed here, never trusted ───────────────────────────────────────
def checks(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def add(cid: str, ok: bool, es: str, en: str, paths: List[str]) -> None:
        out.append({"id": cid, "ok": bool(ok), "es": es, "en": en, "paths": paths})

    # 1 -- the arms the run reports on are the arms it was asked for.
    asked = F.get(r, "arms_requested")
    got = F.get(r, "arms")
    if isinstance(asked, list) and isinstance(got, dict):
        same = {str(a).upper() for a in asked} == set(got)
        add(
            "arms_accounted",
            same,
            "Cada brazo pedido tiene su bloque de respuesta, y no hay bloques de más.",
            "Every arm asked for has a block in the answer, and there are no extra blocks.",
            ["arms_requested", "arms"],
        )

    # 2 -- the cross-arm table names the same arms as the arms block.
    rows = F.get(r, "cross_arm.rows")
    if isinstance(rows, list) and rows and isinstance(got, dict):
        named = {str(x.get("arm", "")).upper() for x in rows if isinstance(x, dict)}
        add(
            "cross_arm_complete",
            named == set(got),
            "La tabla comparativa cubre exactamente los mismos brazos que la corrida.",
            "The comparison table covers exactly the arms the run reports on.",
            ["cross_arm.rows", "arms"],
        )

    # 3 -- an arm the table marks as not run must not carry stage results, and an
    #      arm it marks as run must. This is the claim the whole page rests on.
    if isinstance(rows, list):
        disagree = []
        for x in rows:
            if not isinstance(x, dict):
                continue
            arm = str(x.get("arm", "")).upper()
            if arm and bool(x.get("ran")) != _arm_ran(r, arm):
                disagree.append(arm)
        if rows:
            add(
                "ran_flag_matches_stages",
                not disagree,
                "Lo que la tabla dice que corrió coincide con los brazos que dejaron etapas.",
                "What the table says ran matches the arms that actually left stages behind.",
                ["cross_arm.rows", "arms"],
            )

    # 4 -- the skipped-GPU share, recomputed from the two counts it is made of.
    q = F.get(r, "quantum_cost_total")
    if isinstance(q, dict):
        calls, skipped = q.get("modal_gpu_calls"), q.get("skipped_by_mr_gate")
        share = q.get("share_skipped")
        if isinstance(calls, (int, float)) and isinstance(skipped, (int, float)):
            total = (calls or 0) + (skipped or 0)
            if total:
                want = round(skipped / total, 4)
                ok = share is not None and abs(float(share) - want) < 0.01
                add(
                    "skipped_share",
                    ok,
                    f"La fracción de llamadas a GPU evitadas ({share}) es {skipped} de {total}.",
                    f"The share of GPU calls declined ({share}) is {skipped} out of {total}.",
                    [
                        "quantum_cost_total.share_skipped",
                        "quantum_cost_total.skipped_by_mr_gate",
                        "quantum_cost_total.modal_gpu_calls",
                    ],
                )
            else:
                add(
                    "no_quantum_spend",
                    (q.get("quantum_seconds") or 0) == 0,
                    "No se gastó GPU en esta corrida, y los segundos cuánticos lo confirman.",
                    "No GPU was spent on this run, and the quantum seconds agree.",
                    ["quantum_cost_total.modal_gpu_calls", "quantum_cost_total.quantum_seconds"],
                )
    return out


# ── the arms, as the run describes them ──────────────────────────────────────────
_ARM_ALIAS = {"A": "a", "B": "bb", "C": "c"}
_ARM_TITLE = {
    "A": {"es": "Brazo A — familia GFP", "en": "Arm A — the GFP family"},
    "B": {"es": "Brazo B — linaje iRFP", "en": "Arm B — the iRFP lineage"},
    "C": {"es": "Brazo C — fitocromo", "en": "Arm C — phytochrome"},
}


def _arm_chapter(r: Dict[str, Any], arm: str, _drawn=None) -> Dict[str, Any]:
    """One chapter per arm the run answered for.

    An arm that never ran still gets its chapter: the reason it did not run is
    the finding, and `what_would_be_needed` is the run telling the reader what
    would change that. Dropping it would hide the more interesting half.

    Only the module's own ALIASES reach a beat, so each arm addresses itself
    through the alias declared for it rather than a per-chapter one."""
    base = f"arms.{arm}"
    v = _ARM_ALIAS[arm]
    ran = _arm_ran(r, arm)

    rows = F.get(r, "cross_arm.rows") or []
    i = next(
        (
            n
            for n, x in enumerate(rows)
            if isinstance(x, dict) and str(x.get("arm", "")).upper() == arm
        ),
        None,
    )

    beats: List[Dict[str, Any]] = []
    if i is not None:
        beats.append(
            {
                "es": f"El cromóforo de este brazo: «{{x:rows[{i}].chromophore}}»",
                "en": f"This arm's chromophore, as the run describes it: «{{x:rows[{i}].chromophore}}»",
            }
        )
    if not ran:
        beats.append(
            {
                "es": f"Este brazo no corrió: «{{{v}:reason}}»",
                "en": f"This arm did not run: «{{{v}:reason}}»",
                "kind": "gap",
            }
        )
        beats.append(
            {
                "es": f"Para que corriera haría falta: «{{{v}:what_would_be_needed}}»",
                "en": f"Running it would need: «{{{v}:what_would_be_needed}}»",
                "kind": "note",
            }
        )
    else:
        beats.append(
            {
                "es": f"Corrió a nivel {{{v}:level}}, sobre las etapas {{{v}:stages_planned}}.",
                "en": f"It ran at {{{v}:level}} level, over the stages {{{v}:stages_planned}}.",
            }
        )
        if i is not None:
            beats.append(
                {
                    "es": f"El mecanismo que este brazo admite: «{{x:rows[{i}].mechanism}}»",
                    "en": f"The mechanism this arm allows: «{{x:rows[{i}].mechanism}}»",
                }
            )
            beats.append(
                {
                    "es": f"Lo que lo limita: «{{x:rows[{i}].limiting_factor}}»",
                    "en": f"What bounds it: «{{x:rows[{i}].limiting_factor}}»",
                }
            )
        beats.append(
            {
                "es": "La estructura de este brazo se dibuja aquí, residuo a residuo.",
                "en": "This arm's structure is drawn here, residue by residue.",
                "requires_mesh": f"arm{arm}",
                "focus": {"grow": True},
            }
        )

    scene: Dict[str, Any] = {"type": "panel", "root": base}
    if _drawn and f"arm{arm}" in _drawn:
        scene = {"type": "cartoon", "mesh": f"arm{arm}"}

    return {
        "id": f"arm_{arm.lower()}",
        "title": _ARM_TITLE.get(arm, {"es": f"Brazo {arm}", "en": f"Arm {arm}"}),
        "claims": [base] + ([f"cross_arm.rows[{i}]"] if i is not None else []),
        "scene": scene,
        "beats": beats,
    }


def chapters(
    r: Dict[str, Any], meshes: Dict[str, Any], mesh_keys: Dict[str, str]
) -> List[Dict[str, Any]]:
    """The programme's shape, not a pipeline's stages.

    The three arms come first as one picture, because the run's own cross-arm
    note argues that a single arm failing only means something beside the other
    two. Then each arm. Then the two things the programme refuses to soften."""
    chs: List[Dict[str, Any]] = []
    meshed = [a for a in ARMS if f"arm{a}" in (meshes or {})]

    cover: Dict[str, Any] = (
        {"type": "cover", "mesh": f"arm{meshed[0]}"}
        if meshed
        else {"type": "panel", "root": "cross_arm"}
    )
    chs.append(
        {
            "id": "program",
            "title": {"es": "El programa", "en": "The programme"},
            "claims": ["engine", "scope", "cycle", "arms_requested", "level", "wall_seconds"],
            "scene": cover,
            "beats": [
                {
                    "es": "Esta página explica un ciclo del motor {engine}, en su alcance de {scope}.",
                    "en": "This page explains one cycle of the {engine} engine, at {scope} scope.",
                },
                {
                    "es": "Es el ciclo {cycle} y se pidieron los brazos {arms_requested}.",
                    "en": "It is cycle {cycle}, and the arms asked for were {arms_requested}.",
                },
                {
                    "es": "Corrió a nivel {level} y tardó {wall_seconds|n2} s de reloj.",
                    "en": "It ran at {level} level and took {wall_seconds|n2} s of wall clock.",
                },
                {
                    "es": "Todo número de esta página se lee del resultado; lo que la corrida no "
                    "midió aparece como hueco con la razón que ella misma da.",
                    "en": "Every number here is read from the run; what it did not measure appears "
                    "as a gap carrying the run's own reason.",
                    "kind": "note",
                },
            ],
        }
    )

    chs.append(
        {
            "id": "arms",
            "title": {"es": "Los tres brazos, juntos", "en": "The three arms, together"},
            "claims": ["cross_arm"],
            "scene": {"type": "panel", "root": "cross_arm"},
            "beats": [
                {
                    "es": "Lo que la corrida dice sobre por qué se comparan: «{x:note}»",
                    "en": "The run's own note on why the three are compared: «{x:note}»",
                    "kind": "note",
                },
                {
                    "es": "La tabla cubre {x:rows|count} brazos.",
                    "en": "The table covers {x:rows|count} arms.",
                },
                {
                    "es": "Comprobado aquí: la tabla nombra exactamente los brazos sobre los que "
                    "la corrida informa, ni uno más.",
                    "en": "Checked here: the table names exactly the arms the run reports on, "
                    "and no others.",
                    "kind": "check",
                    "requires_check": "cross_arm_complete",
                },
                {
                    "es": "Comprobado aquí: lo que la tabla marca como corrido coincide con los "
                    "brazos que dejaron etapas detrás.",
                    "en": "Checked here: what the table marks as having run matches the arms that "
                    "actually left stages behind.",
                    "kind": "check",
                    "requires_check": "ran_flag_matches_stages",
                },
            ],
        }
    )

    for arm in ARMS:
        if isinstance(F.get(r, f"arms.{arm}"), dict):
            chs.append(_arm_chapter(r, arm, meshes or {}))

    chs.append(
        {
            "id": "boundary",
            "title": {"es": "Por qué el ciclo para aquí", "en": "Why the cycle stops here"},
            "claims": ["cycle_boundary"],
            "scene": {"type": "panel", "root": "cycle_boundary"},
            "beats": [
                {
                    "es": "Lo que cabe en esta misma llamada, en palabras de la corrida: «{b:same_prompt}»",
                    "en": "What fits in this one call, in the run's words: «{b:same_prompt}»",
                },
                {
                    "es": "Lo que el siguiente ciclo exige antes de empezar: «{b:next_prompt_requires}»",
                    "en": "What the next cycle needs before it can start: «{b:next_prompt_requires}»",
                },
                {
                    "es": "Por qué no los tres ciclos de una vez: «{b:why_not_all_cycles}»",
                    "en": "Why not all three cycles at once: «{b:why_not_all_cycles}»",
                    "kind": "note",
                },
            ],
        }
    )

    chs.append(
        {
            "id": "cost",
            "title": {"es": "Lo que costó el brazo cuántico", "en": "What the quantum arm cost"},
            "claims": ["quantum_cost_total"],
            "scene": {"type": "panel", "root": "quantum_cost_total"},
            "beats": [
                {
                    "es": "Llamadas a GPU en Modal: {q:modal_gpu_calls}. Trabajos en QPU externa: "
                    "{q:external_qpu_jobs}.",
                    "en": "Modal GPU calls: {q:modal_gpu_calls}. External QPU jobs: "
                    "{q:external_qpu_jobs}.",
                },
                {
                    "es": "Segundos de cómputo cuántico: {q:quantum_seconds|n2}.",
                    "en": "Seconds of quantum compute: {q:quantum_seconds|n2}.",
                },
                {
                    "es": "Llamadas a GPU que no se hicieron porque la correlación era débil: "
                    "{q:skipped_by_mr_gate}.",
                    "en": "GPU calls declined because the correlation was weak: "
                    "{q:skipped_by_mr_gate}.",
                },
                {
                    "es": "Nota de la corrida sobre ese contador: «{q:note}»",
                    "en": "The run's own note on that counter: «{q:note}»",
                    "kind": "note",
                },
                {
                    "es": "Comprobado aquí: la fracción evitada se rehízo desde las dos cuentas "
                    "de las que sale.",
                    "en": "Checked here: the declined share was recomputed from the two counts "
                    "it is made of.",
                    "kind": "check",
                    "requires_check": "skipped_share",
                },
                {
                    "es": "Comprobado aquí: esta corrida no gastó GPU, y los segundos cuánticos "
                    "lo confirman.",
                    "en": "Checked here: this run spent no GPU, and the quantum seconds agree.",
                    "kind": "check",
                    "requires_check": "no_quantum_spend",
                },
            ],
        }
    )
    return chs
