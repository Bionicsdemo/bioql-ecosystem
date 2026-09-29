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

# Tope de confórmeros que reciben tratamiento cuántico por candidato.
#
# Existe para que una calibración barata no dispare el escenario a miles de
# segundos, pero con 12 era el tope, y no el triaje, lo que dejaba el reparto en
# 75/25: los tres candidatos elegibles corrían enteros y aun así el cuántico no
# llegaba a su cuota. A 24 la calibración tiene margen para alcanzarla cuando el
# ensemble es caro, y sigue habiendo un techo duro: 24 geometrías a ~6 s son unos
# 140 s por candidato, que es lo que cuesta comprar ese 40%.
#
# Subirlo no es inflar el número. Cada confórmero de más es un confórmero
# ORDENADO a nivel cuántico, que es el producto de este escenario; lo que crece
# es la información, no el gasto decorativo.
_MAX_QM_CONF = 24

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


def _conformer_molblocks(r: Dict[str, Any], limit: int = 3) -> List[str]:
    """Confórmeros como molblocks, que es lo que el recorte de región necesita
    para poder casar átomo a átomo con el SMILES."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem

        m = Chem.AddHs(Chem.MolFromSmiles(r["spec"]["smiles"]))
        ps = AllChem.ETKDGv3()
        ps.useMacrocycleTorsions = True
        ps.randomSeed = 0xF00D
        ids = list(AllChem.EmbedMultipleConfs(m, numConfs=max(4, limit * 2), params=ps))
        if not ids:
            return []
        AllChem.MMFFOptimizeMoleculeConfs(m)
        return [Chem.MolToMolBlock(m, confId=c) for c in ids[:limit]]
    except Exception:  # noqa: BLE001
        return []


def _sin_lider() -> Dict[str, Any]:
    """Ningún candidato sobrevivió, así que no hay sobre quién correr esto."""
    return {
        "available": False,
        "reason": "ningún candidato llegó hasta aquí",
        "reason_en": "no candidate made it this far",
    }


def _streaming_wrapper() -> Any:
    """El envoltorio de la plataforma, buscado SIN reimportar el monolito.

    El servidor corre como `python script_executor_server.py`, así que dentro del
    proceso vivo ese módulo se llama `__main__`. Un
    `import_module("script_executor_server")` no lo encuentra cargado: lo IMPORTA
    OTRA VEZ -- 35 000 líneas, registrando cada blueprint de nuevo en una segunda
    instancia. Se vio en el log, con el arranque entero repetido.

    Así que se busca entre los módulos ya cargados, y solo se importa como último
    recurso, que es el caso de un test llamando a la ruta sin servidor detrás.
    """
    import sys

    for nombre in ("__main__", "script_executor_server"):
        mod = sys.modules.get(nombre)
        fn = getattr(mod, "streaming_pipeline_response", None) if mod else None
        if callable(fn):
            return fn
    return None


def _save_result_artifact(result: Dict[str, Any]) -> None:
    """Escribe `result.json` bajo la sesión, que es cosa del pipeline.

    El envoltorio genérico NO lo hace: persiste en job_results, pero el
    `~/.bioql/artifacts/<sesión>/result.json` del que vive el informe interactivo
    lo escribe cada pipeline. Sin esto el informe no tiene de dónde leer.
    """
    sid = str(result.get("_pipeline_session_id") or "").strip()
    if not sid:
        return
    try:
        pe = _mod("pipeline_enhancements")
        pe.save_pipeline_artifacts(sid, result=result)
        return
    except Exception:  # noqa: BLE001 — sin el helper, se escribe a mano
        pass
    try:
        import json as _json
        import os

        d = os.path.expanduser(f"~/.bioql/artifacts/{os.path.basename(sid)}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "result.json"), "w") as fh:
            _json.dump(result, fh, indent=1, default=str)
    except Exception:  # noqa: BLE001
        pass


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
        "note_es": (
            "cada candidato se comprueba contra la molécula: que el anillo exista "
            "de verdad y que la estereoquímica sobreviva al round-trip a SDF. Un "
            "anillo que no cerró es un péptido lineal y no entra."
        ),
        "note_en": (
            "every candidate is checked against the molecule: that the ring really "
            "exists and that the stereochemistry survives the round-trip to SDF. A "
            "ring that did not close is a linear peptide and does not get in."
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
        "note_es": (
            "el embebido falla sistemáticamente en los anillos grandes y "
            "tensionados, que son los interesantes. Por eso la población se "
            "cuadra y cada caída lleva su razón: un ranking sobre los que "
            "sobrevivieron sin decirlo estaría sesgado hacia lo fácil de embeber."
        ),
        "note_en": (
            "embedding fails systematically on the large, strained rings, which are "
            "the interesting ones. That is why the population is balanced and every "
            "drop carries its reason: a ranking over the survivors, unstated, would "
            "be biased towards whatever was easy to embed."
        ),
    }

    # ── 3. propiedades ──────────────────────────────────────────────────────
    for r, ens in zip(construidos, ensembles):
        smi = r["spec"]["smiles"]
        r["bro5"] = mf.bro5(smi)
        r["liabilities"] = mf.sequence_liabilities(r["spec"]["sequence"])
        r["ensemble"] = ens.to_dict()
    result["stages"]["3_properties"] = {
        "space_es": "bRo5 (Doak/Kihlberg), no la regla de cinco clásica",
        "space_en": "bRo5 (Doak/Kihlberg), not the classic rule of five",
        "why_es": (
            "el único Lipinski que había en el backend usa MW 200-600 y "
            "descalificaría a todos los macrociclos: la ciclosporina A pesa 1202 Da"
        ),
        "why_en": (
            "the only Lipinski filter the backend had uses MW 200-600 and would "
            "disqualify every macrocycle: ciclosporin A weighs 1202 Da"
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
        "note_es": (
            "el cuántico entra donde cambia una decisión: ranking de confórmeros, "
            "barrera cis/trans de amida N-metilada y química de ciclación por "
            "azufre. En scores de docking, descriptores o generación de secuencia "
            "no se usa, a propósito."
        ),
        "note_en": (
            "quantum goes where it changes a decision: conformer ranking, the "
            "cis/trans barrier of an N-methylated amide, and sulfur cyclisation "
            "chemistry. On docking scores, descriptors or sequence generation it is "
            "not used, deliberately."
        ),
        "budget": presupuesto.report(),
    }

    # ── 4b. cuántico de verdad, sobre la región que decide ──────────────────
    # Correr SQD sobre el macrociclo entero gastaba el cálculo en átomos que no
    # deciden nada: 64 pesados en un candidato de 8 residuos, de los que unos 15
    # son la región que gobierna el plegamiento. Con el recorte, lo que antes se
    # saltaba por tamaño corre en decenas de segundos.
    quantum_on = bool(data.get("run_quantum", True))
    top_k = int(data.get("quantum_top_k") or 2)
    q_resultados: List[Dict[str, Any]] = []
    q_saltados: List[Dict[str, Any]] = []
    elegibles = [r for r in construidos if r["quantum"]["applies"]]

    # Cuántos confórmeros reciben tratamiento cuántico.
    #
    # Con el recorte de región el SQD pasó a costar segundos, y con tres
    # confórmeros fijos el reparto salía 98/2: no porque el cuántico sobrara,
    # sino porque era un redondeo frente al ensemble. La palanca honesta no es
    # encarecer el cálculo, es ampliarlo: cada confórmero de más es un confórmero
    # ORDENADO a nivel cuántico, que es justo el producto de este escenario.
    #
    # Se calibra con el primer candidato, se mide lo que cuesta una geometría, y
    # con eso se elige el número para los siguientes. Si el usuario fija
    # `quantum_n_conf`, manda él y no se calibra nada.
    n_conf_fijo = data.get("quantum_n_conf")
    n_conf_base = int(n_conf_fijo or 3)
    seg_por_geom: Optional[float] = None
    plan_conf: List[Dict[str, Any]] = []

    for idx, r in enumerate(elegibles[:top_k] if quantum_on else []):
        n_conf = n_conf_base
        if n_conf_fijo is None and seg_por_geom and seg_por_geom > 0:
            restantes = max(1, min(top_k, len(elegibles)) - idx)
            falta = presupuesto.quantum_seconds_remaining_for_target() / restantes
            n_conf = max(n_conf_base, min(_MAX_QM_CONF, int(falta // seg_por_geom)))
        plan_conf.append(
            {
                "sequence": r["spec"]["sequence"],
                "n_conformers": n_conf,
                "calibrated": n_conf_fijo is None and seg_por_geom is not None,
            }
        )
        blocks = _conformer_molblocks(r, limit=n_conf)
        if len(blocks) < 2:
            q_saltados.append(
                {
                    "sequence": r["spec"]["sequence"],
                    "reason": "hacen falta al menos 2 confórmeros para una diferencia",
                }
            )
            continue
        # Una región o varias.
        #
        # El recorte simple ordena confórmeros mirando UN enlace: en un candidato
        # de 8 residuos, 15 átomos pesados de 64. Los otros 49 podían estar
        # diciendo otra cosa y nadie se enteraba. La descomposición parte la
        # molécula en clusters disjuntos y suma -- es la idea que Cleveland
        # Clinic y RIKEN usaron para llegar a 11 608 átomos, en pequeño y sin el
        # acoplamiento auto-consistente, que se declara ausente.
        #
        # Y no es un refinamiento cosmético: en la primera corrida los clusters
        # discreparon ENTRE SÍ en el signo para el mismo confórmero.
        multi = bool(data.get("quantum_multicluster", True))
        region = (
            mq.closure_clusters(
                r["spec"]["smiles"],
                blocks,
                radius=2,
                max_clusters=int(data.get("max_clusters") or 6),
            )
            if multi
            else mq.closure_region(r["spec"]["smiles"], blocks, radius=2)
        )
        if not region.get("available"):
            q_saltados.append(
                {
                    "sequence": r["spec"]["sequence"],
                    "reason": f"no se pudo recortar la región: {region.get('reason','')}",
                }
            )
            continue
        t_q = time.perf_counter()
        # La escalada a hardware no la decide el pipeline.
        #
        # `allow_qpu` y `allow_cudaq` van en la petición y por defecto están
        # apagados. No es una barrera técnica -- la cascada sabe subir sola desde
        # CPU -- es que los minutos de Heron son escasos y quien los gasta debe
        # ser quien los paga. Lo que sí hace el pipeline es DEJAR CONSTANCIA de
        # con qué permiso corrió, para que un resultado de simulador no se lea
        # nunca como uno de hardware.
        permisos = {
            "allow_qpu": bool(data.get("allow_qpu", False)),
            "allow_cudaq": bool(data.get("allow_cudaq", False)),
        }
        rk = (
            mq.rank_conformers_clusters(region, timeout_s=3600, **permisos)
            if multi
            else mq.rank_conformers(
                region["geometries"],
                method="sqd",
                charge=int(region.get("charge", 0)),  # la de la REGIÓN, no la de la molécula
                timeout_s=3600,
                **permisos,
            )
        )
        gastado = time.perf_counter() - t_q
        presupuesto.add_quantum(gastado)
        # Cuánto costó UNA geometría, que es lo que calibra el número de
        # confórmeros del siguiente candidato. Con varios clusters, una geometría
        # de confórmero cuesta tantas diagonalizaciones como clusters haya, y
        # dividir solo entre confórmeros dejaría la calibración corta por ese
        # factor -- y el presupuesto se pasaría de largo sin que nadie lo viera.
        n_geom = (
            len(region["clusters"]) * min(len(c["geometries"]) for c in region["clusters"])
            if multi
            else len(region["geometries"])
        )
        if n_geom:
            seg_por_geom = gastado / n_geom
        rk["sequence"] = r["spec"]["sequence"]
        rk["n_conformers_quantum"] = rk.get("n_total") or n_geom
        rk["region"] = (
            {
                **{k: v for k, v in region.items() if k not in ("clusters", "rejected")},
                "clusters": [
                    {k: v for k, v in c.items() if k != "geometries"} for c in region["clusters"]
                ],
                # el recorte simple expone estos dos y el informe los nombra: con
                # varios clusters, el que manda es el de más prioridad
                "anchor": region["clusters"][0]["anchor"],
                "anchor_en": region["clusters"][0]["anchor_en"],
                "why": region["clusters"][0]["why"],
                "why_en": region["clusters"][0]["why_en"],
                "n_heavy_region": region["n_heavy_in_clusters"],
                "n_caps": sum(c["n_caps"] for c in region["clusters"]),
                "n_absorbed_to_repair_boundary": 0,
                "charge": sum(c["charge"] for c in region["clusters"]),
                "n_electrons": sum(c["n_electrons"] for c in region["clusters"]),
            }
            if multi
            else {k: v for k, v in region.items() if k != "geometries"}
        )
        q_resultados.append(rk)
        r["quantum_energies"] = rk

    result["stages"]["4b_quantum_run"] = {
        "requested": quantum_on,
        "n_eligible": len(elegibles),
        "n_run": len(q_resultados),
        "n_skipped": len(q_saltados),
        "skipped": q_saltados,
        "conformer_plan": plan_conf,
        "escalation": {
            "allow_qpu": bool(data.get("allow_qpu", False)),
            "allow_cudaq": bool(data.get("allow_cudaq", False)),
            "note_es": (
                "la cascada sabe subir de CPU a CUDA-Q y a QPU, y NO lo hace sola: "
                "los dos peldaños gastan presupuesto real. Se suben pasando "
                "`allow_cudaq` o `allow_qpu` en la petición, y aquí queda escrito "
                "con cuál corrió, para que un resultado de simulador no se lea "
                "nunca como uno de hardware"
            ),
            "note_en": (
                "the cascade can climb from CPU to CUDA-Q and to QPU, and it does "
                "NOT do so on its own: both rungs spend real budget. They are "
                "enabled with `allow_cudaq` or `allow_qpu` in the request, and what "
                "it ran with is written here, so a simulator result is never read "
                "as a hardware one"
            ),
        },
        "seconds_per_geometry": round(seg_por_geom, 2) if seg_por_geom else None,
        "results": q_resultados,
        "differential_floor_ev": mq.DIFFERENTIAL_FLOOR_EV,
        "note_es": (
            "el cuántico corre sobre la REGIÓN de cierre, no sobre la molécula "
            "entera: en un candidato de 8 residuos son unos 15 átomos pesados de "
            "64, con sus hidrógenos y con cada enlace cortado capado. La frontera "
            "se repara antes de cortar, porque solo un enlace C-C simple se puede "
            "capar con un hidrógeno sin cambiar la química de lo que queda dentro. "
            "Solo se emiten diferencias entre confórmeros de la misma región, "
            "porque el error absoluto medido de este protocolo es 1,348 eV frente "
            "a 0,08 eV en diferencial"
        ),
        "note_en": (
            "quantum runs on the closure REGION, not the whole molecule: in an "
            "8-residue candidate that is about 15 heavy atoms out of 64, with their "
            "hydrogens and every severed bond capped. The boundary is repaired "
            "before cutting, because only a single C-C bond can be capped with one "
            "hydrogen without changing the chemistry of what stays inside. Only "
            "differences between conformers of the same region are emitted, because "
            "this protocol's measured absolute error is 1.348 eV against 0.08 eV "
            "differential"
        ),
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
        "not_a_potency_prediction_es": (
            "esto es una priorización para ensayo. No se ha dockeado ni medido "
            "afinidad, y los scores de docking de macrociclos correlacionan mal "
            "con afinidad real incluso cuando se calculan"
        ),
        "not_a_potency_prediction_en": (
            "this is triage for assay. Nothing was docked and no affinity was "
            "measured, and macrocycle docking scores correlate poorly with measured "
            "affinity even when they are computed"
        ),
    }

    # ── 6-11. lo que hace de esto un dossier y no un ranking ────────────────
    # El pipeline se paraba en el orden, y por eso su JSON tenía 173 campos
    # frente a los miles de los otros ocho: no estaba mal construido, hacía menos
    # ciencia. Estos escenarios no reimplementan nada -- enchufan motores que ya
    # estaban en el backend y ya estaban medidos.
    #
    # Todos son OPCIONALES y todos se declaran cuando no corren. `available:
    # False` con su razón es un resultado; un hueco no lo es.
    md = _mod("macrocycle_downstream")
    top_n = int(data.get("downstream_top_k") or 3)
    cabeza = ordenados[:top_n]
    smiles_cabeza = [r["spec"]["smiles"] for r in cabeza]

    t_gpu = time.perf_counter()

    # 6. ADMET
    result["stages"]["6_admet"] = md.admet_for(smiles_cabeza)

    # 7. síntesis, por candidato: es lo que decide si esto se puede pedir
    sintesis = [
        dict(
            md.synthesis_for(r["spec"]["smiles"], want_route=bool(data.get("synthesis_route"))),
            sequence=r["spec"]["sequence"],
        )
        for r in cabeza
    ]
    for r, sx in zip(cabeza, sintesis):
        r["synthesis"] = sx
    result["stages"]["7_synthesis"] = {
        "n_scored": len(sintesis),
        "per_candidate": sintesis,
        "note_es": (
            "un macrociclo peptídico se hace en fase sólida y se cicla al final. "
            "El paso que decide el rendimiento es esa ciclación, y SA no la modela"
        ),
        "note_en": (
            "a peptide macrocycle is made on solid phase and cyclised at the end. "
            "The step that decides the yield is that cyclisation, and SA does not "
            "model it"
        ),
    }

    # 8. toxicología y 9. PK: solo sobre el que encabeza, que es el que iría a
    # ensayo. Correrlos sobre toda la lista gastaría en candidatos que nadie va a
    # sintetizar.
    lider = cabeza[0] if cabeza else None
    result["stages"]["8_toxicology"] = (
        md.toxicology_for(lider["spec"]["smiles"], list(data.get("tox_species") or []) or None)
        if lider
        else _sin_lider()
    )
    result["stages"]["9_pharmacokinetics"] = (
        md.pharmacokinetics_for(
            lider["spec"]["smiles"], dose_mg=float(data.get("dose_mg") or 100.0)
        )
        if lider
        else _sin_lider()
    )

    # 10. estructura del target y docking
    quiere_docking = bool(data.get("run_docking", True))
    estructura = (
        md.target_structure(target, str(data.get("pdb_id") or ""), str(data.get("chain") or ""))
        if quiere_docking
        else {
            "available": False,
            "reason": "no se pidió docking en esta corrida",
            "reason_en": "docking was not requested in this run",
        }
    )
    docking: Dict[str, Any] = {
        "available": False,
        "reason": "sin receptor no se dockea",
        "reason_en": "with no receptor there is nothing to dock into",
    }
    if quiere_docking and estructura.get("available") and lider:
        docking = md.dock_macrocycle(
            estructura["pdb_text"],
            lider["spec"]["smiles"],
            num_poses=int(data.get("n_poses") or 10),
        )
        if docking.get("available"):
            docking["pocket_check"] = md.pocket_check(
                docking.get("ligand_atoms") or [], estructura.get("site_reference_xyz") or []
            )
            docking["sequence"] = lider["spec"]["sequence"]
    result["stages"]["10_docking"] = {
        "requested": quiere_docking,
        "target_structure": {
            k: v for k, v in estructura.items() if k not in ("pdb_text", "site_reference_xyz")
        },
        "docking": {k: v for k, v in docking.items() if k != "raw"},
        "affinity": md.affinity_status(),
        "note_es": (
            "el docking dice DÓNDE se posa, y la comprobación de bolsillo lo mide "
            "contra el sitio que ocupaba el ligando nativo. No dice con cuánta "
            "fuerza: no hay afinidad en este informe y se explica por qué"
        ),
        "note_en": (
            "docking says WHERE it sits, and the pocket check measures that against "
            "the site the native ligand occupied. It does not say how tightly: there "
            "is no affinity in this report and the reason is given"
        ),
    }
    # el receptor y la pose viajan aparte: son geometría para dibujar, no cifras
    if estructura.get("available"):
        result["target_structure_pdb"] = estructura["pdb_text"]
    if docking.get("available"):
        result["docking_pose_atoms"] = docking.get("ligand_atoms")

    presupuesto.add_gpu(time.perf_counter() - t_gpu)

    # 11. compuesto, con su desglose y con lo que le faltó
    extras = {
        "admet": result["stages"]["6_admet"],
        "toxicology": result["stages"]["8_toxicology"],
    }
    for c, r in zip(result["candidates"], ordenados):
        c["synthesis"] = r.get("synthesis")
        c["composite"] = md.composite(c, {**extras, "synthesis": r.get("synthesis") or {}})
    result["stages"]["11_composite_score"] = {
        "weights": md._PESOS,
        "scored": [
            {
                "sequence": c["sequence"],
                "score": c["composite"]["score"],
                "missing": c["composite"]["components_missing"],
            }
            for c in result["candidates"]
        ],
        "note_es": (
            "los pesos están escritos arriba para que se puedan discutir: un score "
            "cuyos pesos se esconden en el código no es un score, es una opinión "
            "con decimales. Se renormaliza sobre lo que SÍ se midió"
        ),
        "note_en": (
            "the weights are written out so they can be argued with: a score whose "
            "weights hide in the code is not a score, it is an opinion with decimals. "
            "It renormalises over what WAS measured"
        ),
    }

    result["best_candidate"] = result["candidates"][0] if result["candidates"] else None
    result["status"] = "completed"
    result["elapsed_s"] = round(time.perf_counter() - t0, 2)
    result["_pipeline_session_id"] = str(data.get("_pipeline_session_id") or "")
    result["compute_budget"] = presupuesto.report()
    result["disclaimer_es"] = (
        "Priorización in-silico para ensayo, no predicción de potencia. La química "
        "de ciclación está comprobada contra la molécula; el ensemble conformacional "
        "declara su convergencia; y el cuántico solo se aplica donde el triaje "
        "encuentra una razón."
    )
    result["disclaimer_en"] = (
        "In-silico triage for assay, not a potency prediction. The cyclisation "
        "chemistry is checked against the molecule; the conformational ensemble "
        "declares its convergence; and quantum is applied only where triage finds a "
        "reason for it."
    )
    _save_result_artifact(result)
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
            envoltura = _streaming_wrapper()
            if envoltura is None:
                raise RuntimeError("streaming_pipeline_response no disponible")
            return envoltura(run_macrocycle, data, pipeline_name=PIPELINE)
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
