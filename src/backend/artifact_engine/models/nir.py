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
    """The fold this arm loaded, if it loaded one.

    It sits at `arms.<arm>.pdb_text`, beside the stages rather than inside the
    `structure` stage -- that stage records what was read from it (atom count,
    source) and not the file. Guessing `stages.structure.pdb` cost a 20-minute
    618-residue phytochrome its cartoon and left the report all value grids."""
    for path in (
        f"arms.{arm}.pdb_text",
        f"arms.{arm}.stages.structure.pdb_text",
        f"arms.{arm}.stages.structure.pdb",
    ):
        v = F.get(r, path)
        if F.is_pdb(v):
            return v, path
    return None, None


# The pocket measurements share one shape -- value, unit, method and the caveat the
# run attaches to it -- so they are read as a set rather than one by one.
_POCKET = (
    ("o2_accessibility", {"es": "oxígeno accesible", "en": "accessible oxygen"}),
    ("proton_wire", {"es": "cadena de protones", "en": "proton wire"}),
    ("redox_environment", {"es": "donadores redox", "en": "redox donors"}),
    ("electrostatics", {"es": "carga formal cercana", "en": "nearby formal charge"}),
    ("water_network", {"es": "red de aguas", "en": "water network"}),
    ("chromophore", {"es": "átomos del cromóforo", "en": "chromophore atoms"}),
)


# The QM region is a handful of named counts, which is a bar chart and not a grid.
_QM_COUNTS = (
    ("n_atoms_total", {"en": "atoms in region", "es": "átomos de la región"}, ""),
    ("n_electrons", {"en": "electrons", "es": "electrones"}, ""),
    ("n_heavy_observed", {"en": "heavy, observed", "es": "pesados observados"}, ""),
    ("n_heavy_template", {"en": "heavy, from template", "es": "pesados de plantilla"}, ""),
    ("n_hydrogens_added", {"en": "hydrogens added", "es": "hidrógenos añadidos"}, ""),
)


def _qm_items(r: Dict[str, Any], arm: str) -> List[Dict[str, Any]]:
    out = []
    for key, name, unit in _QM_COUNTS:
        v = F.get(r, f"arms.{arm}.qm_region.{key}")
        if isinstance(v, (int, float)):
            out.append({"name": name["en"], "value": float(v), "unit": unit, "key": key})
    return out


def _pocket_items(r: Dict[str, Any], arm: str) -> List[Dict[str, Any]]:
    """The pocket's own numbers, each with the unit the run gave it."""
    out = []
    for key, name in _POCKET:
        blk = F.get(r, f"arms.{arm}.stages.pocket.{key}")
        if not isinstance(blk, dict):
            continue
        v = blk.get("value")
        if isinstance(v, (int, float)):
            out.append(
                {
                    "name": name["en"],
                    "value": float(v),
                    "unit": str(blk.get("unit") or ""),
                    "key": key,
                }
            )
    return out


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


def _arm_chapters(r: Dict[str, Any], arm: str, drawn) -> List[Dict[str, Any]]:
    """The chapters one arm earns.

    An arm that never ran earns exactly one: the reason it did not is the
    finding, and `what_would_be_needed` is the run saying what would change it.
    An arm that ran earns as many as it has evidence for -- how it was
    recognised, the fold, the pocket it measured, the region it handed to
    quantum chemistry, and whatever it failed to compute -- because those are
    separate claims and a reader checks them separately."""
    base = f"arms.{arm}"
    v = _ARM_ALIAS[arm]
    ran = _arm_ran(r, arm)
    title = _ARM_TITLE.get(arm, {"es": f"Brazo {arm}", "en": f"Arm {arm}"})

    rows = F.get(r, "cross_arm.rows") or []
    i = next(
        (
            n
            for n, x in enumerate(rows)
            if isinstance(x, dict) and str(x.get("arm", "")).upper() == arm
        ),
        None,
    )
    chromo = (
        [
            {
                "es": f"El cromóforo de este brazo: «{{x:rows[{i}].chromophore}}»",
                "en": f"This arm's chromophore, as the run describes it: "
                f"«{{x:rows[{i}].chromophore}}»",
            }
        ]
        if i is not None
        else []
    )

    if not ran:
        return [
            {
                "id": f"arm_{arm.lower()}",
                "title": title,
                "claims": [base] + ([f"cross_arm.rows[{i}]"] if i is not None else []),
                "scene": {"type": "panel", "root": base},
                "beats": chromo
                + [
                    {
                        "es": f"Este brazo no corrió: «{{{v}:reason}}»",
                        "en": f"This arm did not run: «{{{v}:reason}}»",
                        "kind": "gap",
                    },
                    {
                        "es": f"Para que corriera haría falta: «{{{v}:what_would_be_needed}}»",
                        "en": f"Running it would need: «{{{v}:what_would_be_needed}}»",
                        "kind": "note",
                    },
                ],
            }
        ]

    meshed = f"arm{arm}" in (drawn or {})
    chs: List[Dict[str, Any]] = []

    # ── how the engine knew which arm this is ───────────────────────────────────
    chs.append(
        {
            "id": f"arm_{arm.lower()}",
            "title": title,
            "claims": [
                f"{base}.arm_detection",
                f"{base}.sequence_source",
                f"{base}.arm",
                f"{base}.engine",
                f"{base}.level",
                f"{base}.stages_planned",
                f"{base}.wall_seconds",
                f"{base}.quantum_cost",
                f"{base}.visualization",
            ]
            + ([f"cross_arm.rows[{i}]"] if i is not None else []),
            "scene": (
                {"type": "cartoon", "mesh": f"arm{arm}"}
                if meshed
                else {"type": "panel", "root": f"{base}.arm_detection"}
            ),
            "beats": chromo
            + [
                {
                    "es": f"El motor reconoció este brazo solo: «{{{v}:arm_detection.why}}»",
                    "en": f"The engine recognised this arm on its own: «{{{v}:arm_detection.why}}»",
                },
                {
                    "es": f"Cromóforo {{{v}:arm_detection.chromophore}} sobre {{{v}:arm_detection.n_residues}} residuos; "
                    f"el cofactor es endógeno: {{{v}:arm_detection.cofactor_endogenous}}.",
                    "en": f"Chromophore {{{v}:arm_detection.chromophore}} over {{{v}:arm_detection.n_residues}} residues; "
                    f"the cofactor is endogenous: {{{v}:arm_detection.cofactor_endogenous}}.",
                    "tech": {
                        "es": f"reconocido por: {{{v}:arm_detection.recognized_by}}",
                        "en": f"recognised by: {{{v}:arm_detection.recognized_by}}",
                    },
                },
                {
                    "es": f"Corrió a nivel {{{v}:level}} sobre {{{v}:stages_planned}}, en {{{v}:wall_seconds|n1}} s.",
                    "en": f"It ran at {{{v}:level}} level over {{{v}:stages_planned}}, in {{{v}:wall_seconds|n1}} s.",
                },
                # describes the picture, not a value, so it cites nothing and says so
                {
                    "es": "La estructura se dibuja aquí, residuo a residuo.",
                    "en": "The structure is drawn here, residue by residue.",
                    "kind": "note",
                    "requires_mesh": f"arm{arm}",
                    "focus": {"grow": True},
                },
            ],
        }
    )

    # ── the fold it loaded ──────────────────────────────────────────────────────
    if isinstance(F.get(r, f"{base}.stages.structure"), dict):
        chs.append(
            {
                "id": f"arm_{arm.lower()}_structure",
                "title": {"es": "La estructura que cargó", "en": "The structure it loaded"},
                "claims": [f"{base}.stages.structure", f"{base}.pdb_text"],
                "scene": (
                    {"type": "cartoon", "mesh": f"arm{arm}"}
                    if meshed
                    else {"type": "panel", "root": f"{base}.stages.structure"}
                ),
                "beats": [
                    {
                        "es": f"La estructura viene de {{{v}:stages.structure.source}} y trae "
                        f"{{{v}:stages.structure.atoms|int}} átomos.",
                        "en": f"The structure comes from {{{v}:stages.structure.source}} and carries "
                        f"{{{v}:stages.structure.atoms|int}} atoms.",
                    },
                    {
                        "es": "Nada de lo que sigue se midió sobre un modelo: todo sale de esta estructura.",
                        "en": "Nothing that follows was measured on a model: it all comes off this structure.",
                        "kind": "note",
                        "requires_mesh": f"arm{arm}",
                    },
                ],
            }
        )

    # ── the pocket, which is where this arm's physics is decided ───────────────
    items = _pocket_items(r, arm)
    if items:
        # The count of quantities is something this file would be computing, not
        # something the run states, so it is not put in a sentence as if it were.
        beats: List[Dict[str, Any]] = [
            {
                "es": "El bolsillo alrededor del cromóforo se midió magnitud a magnitud, y "
                "cada una llega con el método que la produjo y con lo que no demuestra.",
                "en": "The pocket around the chromophore was measured one quantity at a time, "
                "each arriving with the method behind it and with what it does not show.",
                "kind": "note",
            }
        ]
        for it in items:
            k = it["key"]
            beats.append(
                {
                    "es": f"{it['name'].capitalize()}: {{{v}:stages.pocket.{k}.value|n2}} "
                    f"{{{v}:stages.pocket.{k}.unit}}.",
                    "en": f"{it['name'].capitalize()}: {{{v}:stages.pocket.{k}.value|n2}} "
                    f"{{{v}:stages.pocket.{k}.unit}}.",
                    "tech": {
                        "es": f"método: {{{v}:stages.pocket.{k}.method}}",
                        "en": f"method: {{{v}:stages.pocket.{k}.method}}",
                    },
                }
            )
            beats.append(
                {
                    "es": f"Lo que esa cifra no dice: «{{{v}:stages.pocket.{k}.notes}}»",
                    "en": f"What that figure does not say: «{{{v}:stages.pocket.{k}.notes}}»",
                    "kind": "note",
                }
            )
        chs.append(
            {
                "id": f"arm_{arm.lower()}_pocket",
                "title": {"es": "El bolsillo, medido", "en": "The pocket, measured"},
                "claims": [f"{base}.stages.pocket"],
                "scene": {"type": "endpoints", "items": items},
                "beats": beats,
            }
        )

    # ── the region handed to quantum chemistry ─────────────────────────────────
    if isinstance(F.get(r, f"{base}.qm_region"), dict):
        chs.append(
            {
                "id": f"arm_{arm.lower()}_qm",
                "title": {
                    "es": "La región que fue a química cuántica",
                    "en": "The region handed to quantum chemistry",
                },
                "claims": [f"{base}.qm_region"],
                "scene": (
                    {"type": "endpoints", "items": _qm_items(r, arm)}
                    if _qm_items(r, arm)
                    else {"type": "panel", "root": f"{base}.qm_region"}
                ),
                "beats": [
                    {
                        "es": f"Se aisló {{{v}:qm_region.resname}} en la cadena {{{v}:qm_region.chain}}: "
                        f"{{{v}:qm_region.n_atoms_total|int}} átomos y {{{v}:qm_region.n_electrons|int}} electrones.",
                        "en": f"It isolated {{{v}:qm_region.resname}} on chain {{{v}:qm_region.chain}}: "
                        f"{{{v}:qm_region.n_atoms_total|int}} atoms and {{{v}:qm_region.n_electrons|int}} electrons.",
                        "tech": {
                            "es": f"método: {{{v}:qm_region.method}}",
                            "en": f"method: {{{v}:qm_region.method}}",
                        },
                    },
                    {
                        "es": f"De los pesados, {{{v}:qm_region.n_heavy_observed|int}} se observan y "
                        f"{{{v}:qm_region.n_heavy_template|int}} vienen de la plantilla; se añadieron "
                        f"{{{v}:qm_region.n_hydrogens_added|int}} hidrógenos.",
                        "en": f"Of the heavy atoms {{{v}:qm_region.n_heavy_observed|int}} are observed and "
                        f"{{{v}:qm_region.n_heavy_template|int}} come from the template; "
                        f"{{{v}:qm_region.n_hydrogens_added|int}} hydrogens were added.",
                    },
                    {
                        "es": f"Carga formal {{{v}:qm_region.formal_charge}}, capa cerrada: "
                        f"{{{v}:qm_region.closed_shell}}.",
                        "en": f"Formal charge {{{v}:qm_region.formal_charge}}, closed shell: "
                        f"{{{v}:qm_region.closed_shell}}.",
                    },
                    {
                        "es": f"«{{{v}:qm_region.electron_count_note}}»",
                        "en": f"«{{{v}:qm_region.electron_count_note}}»",
                        "kind": "note",
                    },
                ],
            }
        )

    # ── and what it could not compute ──────────────────────────────────────────
    if isinstance(F.get(r, f"{base}.stages.electronic"), dict) or isinstance(
        F.get(r, f"{base}.completeness"), dict
    ):
        chs.append(
            {
                "id": f"arm_{arm.lower()}_missing",
                "title": {"es": "Lo que no consiguió calcular", "en": "What it could not compute"},
                "claims": [
                    f"{base}.stages.electronic",
                    f"{base}.completeness",
                    f"{base}.electronic_cascade",
                ],
                "scene": {"type": "panel", "root": f"{base}.completeness"},
                "beats": [
                    {
                        "es": f"Etapas que corrieron: {{{v}:completeness.stages_run|int}}. "
                        f"Sin resultado: {{{v}:completeness.stages_unavailable|int}}.",
                        "en": f"Stages that ran: {{{v}:completeness.stages_run|int}}. "
                        f"Without a result: {{{v}:completeness.stages_unavailable|int}}.",
                    },
                    {
                        "es": f"La etapa electrónica no dio valor: «{{{v}:stages.electronic.reason}}»",
                        "en": f"The electronic stage produced no value: «{{{v}:stages.electronic.reason}}»",
                        "kind": "gap",
                    },
                    {
                        "es": f"Lo que haría falta: «{{{v}:stages.electronic.what_would_be_needed}}»",
                        "en": f"What it would take: «{{{v}:stages.electronic.what_would_be_needed}}»",
                        "kind": "note",
                    },
                    {
                        "es": f"«{{{v}:completeness.note}}»",
                        "en": f"«{{{v}:completeness.note}}»",
                        "kind": "note",
                    },
                ],
            }
        )
    return chs


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
            chs.extend(_arm_chapters(r, arm, meshes or {}))

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
