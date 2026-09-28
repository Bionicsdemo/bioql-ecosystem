"""
Pipeline de macrociclos peptídicos: de la secuencia al triaje, con su contabilidad.

Es el pipeline nº 9 de BioQL y sigue el contrato de la plataforma: `result` con
`pipeline`, `status`, `timestamp`, `target` (string) y `stages`, servido por
`streaming_pipeline_response`, que es quien pone el `ps-<12hex>`, el audit trail
y las post-etapas universales.

Lo que este pipeline NO hace, y conviene decirlo antes que después: no predice
potencia. Los scores de docking de macrociclos correlacionan mal con afinidad
medida, y aquí ni siquiera se dockea salvo que llegue una estructura de target.
Lo que produce es una PRIORIZACIÓN para ensayo, con la población conservada y
cada descarte explicado.

ETAPAS
------
1 build       ciclación real y comprobada (macrocycle_builder)
2 conformers  ensemble con torsiones de macrociclo (macrocycle_conformers)
3 properties  espacio bRo5 y área polar conformacional (macrocycle_filters)
4 quantum     triaje: dónde hace falta cuántico y dónde sería teatro
5 rank        orden con la incertidumbre dentro

MOLEVERA / BIOQL
"""

from __future__ import annotations

import importlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

PIPELINE = "macrocycle_design"


def _mod(nombre: str) -> Any:
    return importlib.import_module(nombre)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seeds(data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Las secuencias a ciclar, con su tipo de cierre.

    Puede venir una lista explícita (`sequences`) o una semilla que se diversifica.
    No se inventan candidatos: si no llega nada utilizable, la etapa lo dice.
    """
    cyc = str(data.get("cyclization") or "head_to_tail")
    seqs = data.get("sequences") or []
    if isinstance(seqs, str):
        seqs = [seqs]
    if seqs:
        return [(str(s), cyc) for s in seqs if str(s).strip()]
    semilla = str(data.get("seed_peptide") or data.get("peptide") or "").strip()
    if not semilla:
        return []
    n = int(data.get("n_candidates") or 8)
    return _diversify(semilla, cyc, n)


def _diversify(semilla: str, cyc: str, n: int) -> List[Tuple[str, str]]:
    """Diversificación conservadora alrededor de una semilla.

    N-metilación y sustitución L->D en posiciones sucesivas: son las dos palancas
    clásicas de permeabilidad en macrociclos, y ambas están soportadas por el
    constructor. No se toca la composición, así que la comparación contra la
    semilla sigue siendo interpretable.
    """
    base = [c for c in semilla.upper() if c.isalpha()]
    if len(base) < 2:
        return []
    fuera: List[Tuple[str, str]] = [("-".join(base), cyc)]
    for i in range(len(base)):
        if len(fuera) >= n:
            break
        v = list(base)
        v[i] = f"NMe:{v[i]}"
        fuera.append(("-".join(v), cyc))
    for i in range(len(base)):
        if len(fuera) >= n:
            break
        v = list(base)
        v[i] = f"D:{v[i]}"
        fuera.append(("-".join(v), cyc))
    return fuera[:n]


def run_macrocycle(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Una corrida completa. Devuelve (result, http_status)."""
    t0 = time.perf_counter()
    target = data.get("target")
    if isinstance(target, dict):  # el wrapper lo aplanaría igual
        target = target.get("name") or target.get("gene") or str(target)
    target = str(target or "").strip() or "sin target declarado"

    result: Dict[str, Any] = {
        "pipeline": PIPELINE,
        "status": "running",
        "timestamp": _now(),
        "target": target,
        "indication": str(data.get("indication") or ""),
        "cyclization": str(data.get("cyclization") or "head_to_tail"),
        "quantum_backend": "sin ejecutar (el triaje decide si hace falta)",
        "stages": {},
        "candidates": [],
    }

    semillas = _seeds(data)
    if not semillas:
        result["status"] = "failed"
        result["error"] = (
            "no llegó ninguna secuencia ni semilla. Este pipeline cicla péptidos: "
            "necesita `sequences` (lista) o `seed_peptide` (una secuencia) para "
            "tener algo que ciclar. No inventa candidatos."
        )
        return result, 400

    try:
        mb = _mod("macrocycle_builder")
        mc = _mod("macrocycle_conformers")
        mf = _mod("macrocycle_filters")
        mq = _mod("macrocycle_quantum")
    except Exception as e:  # noqa: BLE001
        result["status"] = "failed"
        result["error"] = f"no se pudieron cargar los módulos de macrociclos: {e}"
        return result, 500

    presupuesto = mq.ComputeBudget()
    n_conf = int(data.get("n_conformers") or 120)

    # ── 1. construir y comprobar el cierre ───────────────────────────────────
    construidos: List[Dict[str, Any]] = []
    fallos_build: List[Dict[str, Any]] = []
    for seq, cyc in semillas:
        try:
            r = mb.build_and_verify(seq, cyc)
        except Exception as e:  # noqa: BLE001
            fallos_build.append(
                {
                    "sequence": seq,
                    "cyclization": cyc,
                    "reason": f"{type(e).__name__}: {str(e)[:140]}",
                }
            )
            continue
        if not r["ring"]["ok"]:
            fallos_build.append(
                {
                    "sequence": seq,
                    "cyclization": cyc,
                    "reason": r["ring"].get("reason", "el anillo no cerró"),
                }
            )
            continue
        if not r["roundtrip"]["ok"]:
            fallos_build.append(
                {
                    "sequence": seq,
                    "cyclization": cyc,
                    "reason": r["roundtrip"].get("reason", "estereoquímica perdida"),
                }
            )
            continue
        construidos.append(r)

    result["stages"]["1_build"] = {
        "requested": len(semillas),
        "built": len(construidos),
        "dropped": len(fallos_build),
        "drops": fallos_build,
        "note": (
            "cada candidato se comprueba contra la molécula: que el anillo exista "
            "de verdad y que la estereoquímica sobreviva al round-trip a SDF. Un "
            "anillo que no cerró es un péptido lineal y no entra."
        ),
    }
    if not construidos:
        result["status"] = "failed"
        result["error"] = "ningún candidato superó la comprobación de cierre de anillo"
        return result, 200

    # ── 2. ensemble conformacional ──────────────────────────────────────────
    ensembles: List[Any] = []
    for r in construidos:
        ens = mc.embed_ensemble(
            r["spec"]["smiles"], n_conf=n_conf, cyclization=r["spec"]["cyclization"]
        )
        ensembles.append(ens)
        presupuesto.add_gpu(ens.wall_seconds)  # CPU/GPU clásico
    poblacion = mc.population_conserved(len(construidos), ensembles)
    result["stages"]["2_conformers"] = {
        "n_conformers_requested": n_conf,
        "population": poblacion,
        "failure_by_ring": mc.failure_by_ring(ensembles),
        "convergence": mc.convergence_note(ensembles),
        "note": (
            "el embebido falla sistemáticamente en los anillos grandes y "
            "tensionados, que son los interesantes. Por eso la población se "
            "cuadra y cada caída lleva su razón: un ranking sobre los que "
            "sobrevivieron sin decirlo estaría sesgado hacia lo fácil de embeber."
        ),
    }

    # ── 3. propiedades ──────────────────────────────────────────────────────
    for r, ens in zip(construidos, ensembles):
        smi = r["spec"]["smiles"]
        r["bro5"] = mf.bro5(smi)
        r["liabilities"] = mf.sequence_liabilities(r["spec"]["sequence"])
        r["ensemble"] = ens.to_dict()
    result["stages"]["3_properties"] = {
        "space": "bRo5 (Doak/Kihlberg), no la regla de cinco clásica",
        "why": (
            "el único Lipinski que había en el backend usa MW 200-600 y "
            "descalificaría a todos los macrociclos: la ciclosporina A pesa 1202 Da"
        ),
        "n_within_bro5": sum(1 for r in construidos if r["bro5"]["ok"]),
        "n_total": len(construidos),
    }

    # ── 4. triaje cuántico ──────────────────────────────────────────────────
    triajes = []
    for r in construidos:
        need = mq.triage(r["spec"], run_gate=True)
        r["quantum"] = need.to_dict()
        triajes.append(need)
        if need.applies:
            presupuesto.sent_to_quantum += 1
        else:
            presupuesto.skipped_by_triage += 1
    result["stages"]["4_quantum_triage"] = {
        "n_eligible": sum(1 for t in triajes if t.applies),
        "n_classical_suffices": sum(1 for t in triajes if not t.applies),
        "places": sorted({p for t in triajes for p in t.places}),
        "note": (
            "el cuántico entra donde cambia una decisión: ranking de confórmeros, "
            "barrera cis/trans de amida N-metilada y química de ciclación por "
            "azufre. En scores de docking, descriptores o generación de secuencia "
            "no se usa, a propósito."
        ),
        "budget": presupuesto.report(),
    }

    # ── 5. orden ────────────────────────────────────────────────────────────
    def clave(r: Dict[str, Any]) -> Tuple[int, int, float]:
        return (
            0 if r["bro5"]["ok"] else 1,
            r["liabilities"]["n_findings"],
            -float(r["ensemble"].get("n_after_dedup") or 0),
        )

    ordenados = sorted(construidos, key=clave)
    result["candidates"] = [
        {
            "rank": i + 1,
            "sequence": r["spec"]["sequence"],
            "smiles": r["spec"]["smiles"],
            "cyclization": r["spec"]["cyclization"],
            "ring_size": r["spec"]["ring_size"],
            "content_hash": r["spec"]["content_hash"],
            "bro5_ok": r["bro5"]["ok"],
            "bro5_violations": r["bro5"]["n_violations"],
            "descriptors": r["bro5"]["descriptors"],
            "liabilities": r["liabilities"]["n_findings"],
            "n_conformers": r["ensemble"].get("n_after_dedup"),
            "ensemble_converged": r["ensemble"].get("converged"),
            "quantum": r["quantum"],
        }
        for i, r in enumerate(ordenados)
    ]
    result["stages"]["5_rank"] = {
        "ordered_by": "espacio bRo5, luego liabilities de secuencia, luego tamaño del ensemble",
        "not_a_potency_prediction": (
            "esto es una priorización para ensayo. No se ha dockeado ni medido "
            "afinidad, y los scores de docking de macrociclos correlacionan mal "
            "con afinidad real incluso cuando se calculan"
        ),
    }

    result["best_candidate"] = result["candidates"][0] if result["candidates"] else None
    result["status"] = "completed"
    result["elapsed_s"] = round(time.perf_counter() - t0, 2)
    result["compute_budget"] = presupuesto.report()
    result["disclaimer"] = (
        "Priorización in-silico para ensayo, no predicción de potencia. La química "
        "de ciclación está comprobada contra la molécula; el ensemble conformacional "
        "declara su convergencia; y el cuántico solo se aplica donde el triaje "
        "encuentra una razón."
    )
    return result, 200


def register_macrocycle_routes(app: Any) -> None:
    """Expone el pipeline con el mismo patrón que el resto de la plataforma."""
    from flask import jsonify, request

    @app.route("/api/pipeline/macrocycle", methods=["POST", "OPTIONS"])
    def _macrocycle():
        if request.method == "OPTIONS":
            return ("", 204)
        data = request.get_json(force=True, silent=True) or {}
        try:
            # Por nombre, igual que el resto de dependencias de la plataforma: el
            # monolito son 35 000 líneas y arrastrarlo al type-check de este
            # fichero no aporta nada, además de que el wrapper es opcional.
            srv = _mod("script_executor_server")
            return srv.streaming_pipeline_response(run_macrocycle, data, pipeline_name=PIPELINE)
        except Exception:  # noqa: BLE001 — sin el wrapper, la ciencia igual corre
            res, code = run_macrocycle(data)
            return jsonify(res), code

    app.add_url_rule(
        "/api/quantum/macrocycle",
        "_macrocycle_alias",
        _macrocycle,
        methods=["POST", "OPTIONS"],
    )
    print("[MACROCYCLE] pipeline cargado (/api/pipeline/macrocycle)")


__all__ = ["run_macrocycle", "register_macrocycle_routes", "PIPELINE"]

# MOLEVERA / BIOQL
