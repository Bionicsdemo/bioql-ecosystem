"""
nir_protein_engine.py — motor de diseno de PROTEINA fotosensibilizadora NIR.

QUE ES EL PRODUCTO
------------------
Una proteina, no una molecula pequena. Se entrega como GEN en un vector de acido
nucleico autoamplificante, la celula la expresa, y desde ese momento se dosifica
con LUZ en vez de con farmaco. El cromoforo no se administra: se forma de los
propios residuos de la proteina (linaje GFP) o de un cofactor que la celula ya
produce (biliverdina, via hemo-oxigenasa). Por eso el sistema es monocomponente.

El activo final es una SECUENCIA de proteina.

DOS NIVELES, Y LA DIFERENCIA IMPORTA
-------------------------------------
`level="core"`  -> estructura electronica del cromoforo en su bolsillo:
                   espacio activo, QM/MM, S0/S1/T1, gap singlete-triplete, y
                   ranking. Es lo que se entrega en la capa de fisica.

`level="full"`  -> ademas: microambiente del bolsillo (agua, O2, redox,
                   electrostatica, cable de protones), veredicto de mecanismo
                   ROS, PROPUESTA DE MUTACIONES, developability de la proteina
                   terapeutica (inmunogenicidad incluida) y diseno del construto
                   saDNA con optimizacion de codones y sensado innato.

Por que el nivel completo no es un adorno: el propio analisis de la fisica
reconoce que DOS de los cinco objetivos no son estructura electronica —la tasa
de ISC exige acoplamiento espin-orbita y factores Franck-Condon, y la
fotoestabilidad exige superficies e intersecciones conicas—. Y si el mecanismo
resulta ser Tipo I, lo que decide es el microambiente del bolsillo: potencial
redox, estructura del agua, acceso de O2 y electrostatica. Un T1 bonito no
salva a un candidato al que el O2 no llega.

DONDE ENTRA LO CUANTICO, Y DONDE NO
------------------------------------
Solo en la estructura electronica del cromoforo, y solo cuando el caracter
multirreferencial lo justifica: `quantum_arm.sqd_arm(require_mr=True)` corta la
llamada a GPU cuando la correlacion es debil, porque ahi ya esta MEDIDO que el
metodo clasico es mejor Y mas barato (2.68 frente a 12.4 kcal/mol). Todo lo
demas —bolsillo, agua, redox, O2, secuencia, construto— es clasico, y decirlo
asi es lo que hace la propuesta creible.

CONTRATO DE SALIDA
------------------
Cada etapa devuelve Measured o NotAvailable con su razon. Una etapa que no se
pudo correr aparece como hueco DECLARADO, nunca como cero ni como estimacion.
Un ranking que presentase las cinco cantidades como si todas saliesen del mismo
calculo seria falso.

-- MOLEVERA / BIOQL
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "run_engine",
    "run_program",
    "detect_arm",
    "fold_sequence",
    "STAGES",
    "register_nir_engine_routes",
]

ENGINE = "nir_protein_engine_v1"

# Orden de etapas. `core` es el subconjunto de fisica; `full` lo envuelve.
# Etapas que NECESITAN coordenadas. El resto trabaja sobre la secuencia y debe
# correr aunque no haya estructura: declarar una dependencia que no existe
# ocultaria resultados calculables.
_NEEDS_STRUCTURE = ("pocket", "mechanism", "mutations")

STAGES: Dict[str, List[str]] = {
    "core": ["structure", "pocket", "electronic"],
    "full": [
        "structure",
        "pocket",
        "electronic",
        "mechanism",
        "mutations",
        "differential",
        "developability",
        "construct",
    ],
}


def _na(reason: str, needed: Optional[str] = None, attempted: Optional[str] = None):
    """NotAvailable del contrato, o un dict equivalente si el contrato no carga."""
    try:
        from result_contract import NotAvailable

        return NotAvailable(reason=reason, what_would_be_needed=needed, attempted_method=attempted)
    except Exception:  # noqa: BLE001
        return {
            "available": False,
            "reason": reason,
            "what_would_be_needed": needed,
            "attempted_method": attempted,
        }


def _as_dict(v: Any) -> Any:
    return v.to_dict() if hasattr(v, "to_dict") else v


# ── Etapa 0: estructura de partida ──────────────────────────────────────────
def _stage_structure(
    pdb_id: Optional[str],
    pdb_text: Optional[str],
    scaffold: Optional[str],
    fasta: Optional[str] = None,
) -> Dict[str, Any]:
    """Consigue el PDB. Sin estructura no hay bolsillo, y sin bolsillo no hay
    mecanismo: por eso esta etapa bloquea el resto en vez de seguir a medias."""
    if pdb_text:
        return {"ok": True, "pdb_text": pdb_text, "source": "suministrado por el llamador"}
    if fasta and not pdb_id:
        # Solo hay secuencia: se pliega y se DECLARA lo que se pierde.
        f = fold_sequence(fasta)
        if f.get("available"):
            return {
                "ok": True,
                "pdb_text": f["pdb_text"],
                "source": f"plegado con {f['backend']}",
                "folded_from_sequence": True,
                "plddt": f.get("plddt"),
                "degraded": f.get("degraded"),
                "scaffold": scaffold,
            }
        return {
            "ok": False,
            "value": _na(
                f"no se pudo plegar la secuencia: {f.get('reason')}",
                needed="un PDB, o un backend de plegamiento accesible",
            ),
        }
    if not pdb_id:
        return {
            "ok": False,
            "value": _na(
                "no se recibio ni `pdb_text` ni `pdb_id`",
                needed="una estructura del andamiaje (PDB) para localizar el cromoforo",
            ),
        }
    try:
        from structural_review import _fetch_pdb_text

        txt = _fetch_pdb_text(pdb_id)
        if not txt:
            return {"ok": False, "value": _na(f"no se pudo descargar el PDB {pdb_id}")}
        return {"ok": True, "pdb_text": txt, "source": f"RCSB {pdb_id}", "scaffold": scaffold}
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "value": _na(f"fallo al obtener la estructura: {type(e).__name__}: {str(e)[:140]}"),
        }


# ── Etapa 1: microambiente del bolsillo ─────────────────────────────────────
def _stage_pocket(pdb_text: str, selector: Dict[str, Any]) -> Any:
    try:
        from nir_pocket_microenvironment import pocket_microenvironment
    except Exception as e:  # noqa: BLE001
        return _na(
            f"modulo de microambiente no disponible: {str(e)[:120]}",
            needed="nir_pocket_microenvironment.py",
        )
    try:
        return pocket_microenvironment(pdb_text, selector)
    except Exception as e:  # noqa: BLE001
        return _na(f"el analisis de microambiente fallo: {type(e).__name__}: {str(e)[:140]}")


# ── Etapa 2: estructura electronica (unica etapa con brazo cuantico) ────────
# Presupuesto de la etapa electronica. Existe porque un cuelgue es peor que un
# hueco: MEDIDO 2026-08-28, la region QM del cromoforo (42 atomos) dejo el
# subproceso 15 min al 0% de CPU -- bloqueado, no calculando. Sin tope, el motor
# entero se queda esperando para siempre y el usuario no sabe si avanza. Con
# tope, se declara "excedio el presupuesto" y las demas etapas ya han corrido.
ELECTRONIC_BUDGET_S = int(os.environ.get("BIOQL_NIR_ELECTRONIC_BUDGET_S", "1200"))


def _stage_electronic(
    designs: List[Dict[str, Any]],
    reference: Optional[Dict[str, Any]],
    basis: str,
    allow_qpu: bool,
    budget_s: Optional[int] = None,
) -> Any:
    if not designs:
        return _na(
            "no se recibio ninguna geometria de region QM",
            needed="al menos un diseno {design_id, atom, charge, spin}",
        )
    try:
        from excited_state_pipeline import run_pipeline_isolated
    except Exception as e:  # noqa: BLE001
        return _na(f"pipeline de estados excitados no disponible: {str(e)[:120]}")
    presupuesto = int(budget_s or ELECTRONIC_BUDGET_S)
    try:
        res = run_pipeline_isolated(
            designs=designs,
            basis=basis,
            reference=reference,
            quantum_arm=True,
            allow_qpu=bool(allow_qpu),
            timeout=presupuesto,
        )
    except Exception as e:  # noqa: BLE001
        return _na(f"la etapa electronica fallo: {type(e).__name__}: {str(e)[:140]}")

    # El aislador devuelve `error` al agotar el presupuesto: se convierte en un
    # hueco DECLARADO en vez de dejar pasar un dict sin datos que parezca exito.
    if isinstance(res, dict) and res.get("error"):
        return _na(
            f"la etapa electronica no termino dentro del presupuesto de "
            f"{presupuesto}s: {str(res['error'])[:120]}",
            needed=(
                "reducir el espacio activo o la base, o subir " "BIOQL_NIR_ELECTRONIC_BUDGET_S"
            ),
            attempted=f"pipeline de estados excitados, base {basis}",
        )
    return res


# ── Etapa 3: mecanismo ROS ──────────────────────────────────────────────────
def _stage_mechanism(
    pocket: Any,
    electronic: Any,
    arm: str,
    quenches: Optional[bool],
    lifetime_ps: Optional[float],
    pdb_text: Optional[str] = None,
    resname: Optional[str] = None,
    chain: str = "A",
    basis: str = "sto-3g",
    budget_s: int = 3600,
) -> Any:
    """Veredicto Tipo I / Tipo II.

    RESPALDO ELECTRONICO ANADIDO 2026-08-31. Antes, si la cascada electronica no
    entregaba T1, esta etapa salia `indeterminate` por falta de datos y el bucle
    evolutivo se quedaba sin poder evaluar la ruta de ROS. Paso de verdad en el
    brazo C: 8 etapas completas, sitios propuestos, y el objetivo global
    imposible de decidir porque faltaba UN numero.
    Ese numero se puede calcular: CIS con singlet=False da el triplete.
    MEDIDO sobre el cromoforo CRQ: T1 = 2.106 eV, por encima del umbral de
    0.98 eV para sensibilizar oxigeno singlete. La ventana AVAS-pi daba 54 eV,
    que es imposible (ver T1_NOT_AVAILABLE_FROM_PI_WINDOW).
    """
    try:
        from nir_mechanism import ros_mechanism
    except Exception as e:  # noqa: BLE001
        return _na(f"modulo de mecanismo no disponible: {str(e)[:120]}")
    t1 = s1 = None
    if isinstance(electronic, dict):
        for rec in electronic.get("per_design") or []:
            st = rec.get("stages") or {}
            for k in ("t1_ev", "triplet_energy_ev"):
                v = st.get(k)
                if isinstance(v, dict) and v.get("value") is not None:
                    t1 = v["value"]
                    break
            for k in ("s1_ev", "excitation_ev"):
                v = st.get(k)
                if isinstance(v, dict) and v.get("value") is not None:
                    s1 = v["value"]
                    break
            if t1 is not None:
                break
    # Respaldo: si la cascada no dio T1, se calcula por CIS antes de rendirse.
    origen_electronico = "cascada electronica"
    respaldo = None
    if t1 is None and pdb_text and resname:
        try:
            from nir_differential import electronic_cis

            respaldo = electronic_cis(
                pdb_text=pdb_text, resname=resname, chain=chain, basis=basis, budget_s=budget_s
            )
            if respaldo.get("available"):
                t1 = respaldo.get("t1_ev")
                s1 = s1 if s1 is not None else respaldo.get("s1_ev")
                origen_electronico = "respaldo CIS/TDA (la cascada no dio T1)"
        except Exception as e:  # noqa: BLE001
            respaldo = {"available": False, "reason": f"{type(e).__name__}: {str(e)[:120]}"}

    try:
        r = ros_mechanism(
            t1_ev=t1,
            s1_ev=s1,
            excited_lifetime_ps=lifetime_ps,
            microenvironment=pocket,
            chromophore_quenches_singlet_o2=quenches,
            arm=arm,
        )
        if isinstance(r, dict):
            r["electronic_source"] = origen_electronico
            if respaldo is not None:
                r["cis_fallback"] = respaldo
        return r
    except Exception as e:  # noqa: BLE001
        return _na(f"el veredicto de mecanismo fallo: {type(e).__name__}: {str(e)[:140]}")


# ── Etapa 4: propuesta de mutaciones ────────────────────────────────────────
def _stage_mutations(pocket: Any, target: Dict[str, Any], arm: str) -> Any:
    try:
        from nir_mutation_proposal import propose_mutations
    except Exception as e:  # noqa: BLE001
        return _na(f"modulo de mutaciones no disponible: {str(e)[:120]}")
    try:
        return propose_mutations(microenvironment=pocket, electronic_target=target, arm=arm)
    except Exception as e:  # noqa: BLE001
        return _na(f"la propuesta de mutaciones fallo: {type(e).__name__}: {str(e)[:140]}")


# ── Etapa 5: developability de la proteina terapeutica ──────────────────────
def _stage_developability(seq: Optional[str]) -> Any:
    if not seq:
        return _na(
            "no se recibio secuencia de proteina",
            needed="la secuencia del andamiaje o de la variante a evaluar",
        )
    try:
        from nir_developability import developability
    except Exception as e:  # noqa: BLE001
        return _na(f"modulo de developability no disponible: {str(e)[:120]}")
    try:
        return developability(seq)
    except Exception as e:  # noqa: BLE001
        return _na(f"developability fallo: {type(e).__name__}: {str(e)[:140]}")


# ── Etapa 6: construto saDNA ────────────────────────────────────────────────
def _stage_construct(seq: Optional[str], vector: str) -> Any:
    if not seq:
        return _na("no se recibio secuencia de proteina para construir el gen")
    try:
        from nir_construct import design_construct
    except Exception as e:  # noqa: BLE001
        return _na(f"modulo de construto no disponible: {str(e)[:120]}")
    try:
        return design_construct(seq, optimize_codons=True, vector=vector)
    except Exception as e:  # noqa: BLE001
        return _na(f"el diseno del construto fallo: {type(e).__name__}: {str(e)[:140]}")


def _viz_payload(pdb: str, pocket: Any, mutations: Any) -> Dict[str, Any]:
    """Selecciones para pintar la escena 3D, derivadas de lo ya medido.

    No calcula nada nuevo: expone QUE resaltar (cromoforo, cadena de agua,
    donadores de electron, sitios propuestos) para que el visor pueda darle a
    cada cosa su color. Sin esto la tarjeta solo puede pintar el andamiaje
    entero en gris, que no dice nada de lo que el motor encontro.
    """

    def _plano(x):
        if isinstance(x, dict):
            return x
        if hasattr(x, "to_dict"):
            try:
                return x.to_dict()
            except Exception:  # noqa: BLE001
                return {}
        return {}

    pk = _plano(pocket)
    viz: Dict[str, Any] = {"available": True}

    cr = _plano(pk.get("chromophore"))
    viz["chromophore"] = {
        "residues": (_plano(cr.get("diagnostic")).get("residues") or []),
        "centroid": (_plano(cr.get("diagnostic")).get("centroid_xyz")),
    }

    wn = _plano(pk.get("water_network"))
    viz["water_chain"] = [
        {
            "label": w.get("water"),
            "hops": w.get("hops_from_chromophore"),
            "distance_A": w.get("distance_to_chromophore_A"),
        }
        for w in (_plano(wn.get("diagnostic")).get("chain") or [])
    ]

    rx = _plano(pk.get("redox_environment"))
    viz["donors"] = [
        {
            "residue": d.get("residue"),
            "atom": d.get("donor_atom"),
            "distance_A": d.get("distance_A"),
        }
        for d in (_plano(rx.get("diagnostic")).get("donors") or [])
    ]

    pw = _plano(pk.get("proton_wire"))
    viz["proton_wire"] = _plano(pw.get("diagnostic")).get("chain_residues") or []

    mt = _plano(mutations)
    viz["mutation_sites"] = [
        {
            "position": x.get("position"),
            "wild_type": x.get("wild_type"),
            "objective": x.get("objective"),
        }
        for x in (mt.get("sites") or [])
    ]
    viz["excluded"] = _plano(mt.get("chromophore_exclusion")).get("positions") or []
    viz["note"] = (
        "Selecciones derivadas de lo medido; el visor solo las colorea. "
        "Un residuo resaltado no es una prediccion validada: es donde "
        "el analisis encontro la evidencia que se cita en la tabla."
    )
    return viz


def fold_sequence(
    fasta_or_seq: str, name: str = "query", allow_external_msa: bool = True
) -> Dict[str, Any]:
    """Pliega una secuencia a estructura. Punto de entrada cuando solo hay FASTA.

    LO QUE SE PIERDE, Y HAY QUE DECIRLO
    ------------------------------------
    Un modelo de plegamiento devuelve la CADENA PROTEICA. No devuelve:
      * el CROMOFORO -- en la familia GFP se forma autocataliticamente de un
        tripeptido interno DESPUES de plegar, y el predictor no lo modela; en el
        linaje bilina es un cofactor que ni siquiera esta en la secuencia.
      * las AGUAS cristalograficas -- que es lo que sostiene la red de
        transferencia protonica: MEDIDO en iRFP, 66 aguas mantienen conectados
        129 nodos, y sin ellas ese analisis no existe.

    Esos dos son justo los datos que mas pesan en el diagnostico. Con FASTA se
    puede correr, pero las etapas de bolsillo y mecanismo salen degradadas y se
    declara cuales. Con estructura experimental el resultado es sustancialmente
    mejor, y eso no es una opinion: es que el dato no esta.
    """
    seq = "".join(
        ln.strip()
        for ln in (fasta_or_seq or "").splitlines()
        if ln.strip() and not ln.startswith(">")
    ).upper()
    seq = "".join(c for c in seq if c.isalpha())
    if len(seq) < 30:
        return _as_dict(
            _na(
                "la secuencia es demasiado corta o no se pudo leer",
                "un FASTA o una cadena de al menos 30 aminoacidos",
            )
        )
    validos = set("ACDEFGHIKLMNPQRSTVWY")
    raros = sorted(set(seq) - validos)
    if raros:
        return _as_dict(
            _na(
                f"la secuencia trae simbolos no estandar: {raros[:6]}",
                "solo los 20 aminoacidos canonicos",
            )
        )
    # Se usa el backend del proyecto, que ya tiene reintentos y respaldo a
    # Chai-1, en vez de llamar a Modal a pelo.
    # El plegador compartido escala a Boltz-2 CON MSA cuando el plegado de
    # secuencia unica no llega al suelo. Sin esa escalada, esta familia sale con
    # TM-score 0.16 contra el cristal: una estructura equivocada. Va ACTIVADA por
    # defecto porque sin ella el resultado no sirve. `allow_external_msa=False`
    # existe para el caso en que la secuencia no pueda salir de la maquina.
    import os as _os

    permitir = str(allow_external_msa).lower() in ("1", "true", "yes", "si")
    previo = _os.environ.get("BIOQL_FOLD_NO_EXTERNAL_MSA")
    if not permitir:
        _os.environ["BIOQL_FOLD_NO_EXTERNAL_MSA"] = "1"
    try:
        from esmfold2_backend import predict_structure_esmfold2

        r = predict_structure_esmfold2(seq)
    finally:
        if not permitir:
            if previo is None:
                _os.environ.pop("BIOQL_FOLD_NO_EXTERNAL_MSA", None)
            else:
                _os.environ["BIOQL_FOLD_NO_EXTERNAL_MSA"] = previo
    try:
        pdb = (r or {}).get("pdb")
        if r and r.get("success") and pdb:
            return {
                "available": True,
                "pdb_text": pdb,
                "length": len(seq),
                "backend": (r.get("backend") or "esmfold2"),
                "plddt": r.get("plddt"),
                "trustworthy": r.get("trustworthy"),
                "trust_reason": r.get("trust_reason"),
                "escalation": r.get("escalation"),
                "external_msa": {
                    "allowed": permitir,
                    "note": (
                        "el MSA se pide a un servicio externo. Sin el, "
                        "un plegado de secuencia unica de esta familia "
                        "dio TM-score 0.16 contra el cristal, o sea "
                        "equivocado. Autorizar con "
                        "allow_external_msa=True SOLO si la secuencia "
                        "puede salir"
                    ),
                },
                "degraded": {
                    "chromophore": (
                        "ausente: no se modela; en familia GFP se "
                        "forma autocataliticamente tras plegar, en "
                        "linaje bilina es cofactor"
                    ),
                    "waters": (
                        "ausentes: la red de transferencia protonica no " "se puede analizar"
                    ),
                    "impact": (
                        "las etapas de bolsillo y mecanismo saldran "
                        "degradadas y se declara cuales"
                    ),
                },
            }
        motivo = (r or {}).get("error") or "el backend no devolvio estructura"
    except Exception as e:  # noqa: BLE001
        motivo = f"{type(e).__name__}: {str(e)[:120]}"
    # Respaldo por las funciones DESPLEGADAS, via modal_compute_layer (hidrata el
    # handle y declara donde corrio). Antes pedia bioql-esmfold2::predict y
    # bioql-boltz2::fold con {"sequences": [...]}: ninguna de las dos existe en
    # produccion (consulta real 2026-09-24) y ese payload no lo acepta ninguna.
    import modal_compute_layer as _mcl

    for key, args in (
        ("fold_protein", (seq,)),
        ("fold_complex", ({"protein_sequence": seq, "use_msa_server": permitir},)),
    ):
        try:
            rr = _mcl.run(key, *args)
            r = (rr or {}).get("result") if (rr or {}).get("where_it_ran") == "modal" else None
            if not r:
                motivo = (rr or {}).get("why") or motivo
                continue
            pdb = (r or {}).get("pdb") or (r or {}).get("pdb_text")
            if pdb:
                plddt = (r or {}).get("plddt")
                if plddt is None:
                    plddt = ((r or {}).get("confidence") or {}).get("plddt")
                return {
                    "available": True,
                    "pdb_text": pdb,
                    "length": len(seq),
                    "backend": f"{rr.get('app')}::{rr.get('function')}",
                    "plddt": plddt,
                    "degraded": {
                        "chromophore": (
                            "ausente: no se modela; en familia GFP "
                            "se forma autocataliticamente tras "
                            "plegar, en linaje bilina es cofactor"
                        ),
                        "waters": (
                            "ausentes: la red de transferencia " "protonica no se puede analizar"
                        ),
                        "impact": (
                            "las etapas de bolsillo y mecanismo saldran "
                            "degradadas y se declara cuales"
                        ),
                    },
                }
            motivo = (r or {}).get("error") or motivo
        except Exception as e:  # noqa: BLE001
            motivo = f"{type(e).__name__}: {str(e)[:120]}"
            continue
    return _as_dict(
        _na(
            f"ningun backend de plegamiento respondio: {motivo}",
            "bioql-esmfold2 o bioql-boltz2 desplegados y accesibles",
        )
    )


_FORMULA_CACHE: Dict[str, Optional[str]] = {}


def _fetch_formula(resname: str) -> Optional[str]:
    """Formula quimica de un componente del PDB. None si no se puede."""
    r = (resname or "").strip().upper()
    if not r or r in ("HOH", "WAT"):
        return None
    if r in _FORMULA_CACHE:
        return _FORMULA_CACHE[r]
    try:
        import json as _j
        import urllib.request as _u

        with _u.urlopen(f"https://data.rcsb.org/rest/v1/core/chemcomp/{r}", timeout=25) as f:
            d = _j.load(f)
        out = (d.get("chem_comp") or {}).get("formula")
    except Exception:  # noqa: BLE001
        out = None
    _FORMULA_CACHE[r] = out
    return out


def _is_bilin_formula(formula: str) -> bool:
    """El esqueleto de una bilina: 33 carbonos, 4 nitrogenos, 6 oxigenos.

    Biliverdina C33H34N4O6, ficocianobilina C33H40N4O6, BLR C33H36N4O6. El
    hidrogeno varia con el estado de reduccion; el esqueleto no.
    """
    import re as _re

    f = (formula or "").upper().replace(" ", "")
    c = _re.search(r"C(\d+)", f)
    n = _re.search(r"N(\d+)", f)
    o = _re.search(r"O(\d+)", f)
    if not (c and n and o):
        return False
    if _re.search(r"(FE|MG|ZN|CU|MN|NI|CO)\d*", f):
        return False  # con metal es una porfirina, no una bilina libre
    return int(c.group(1)) == 33 and int(n.group(1)) == 4 and int(o.group(1)) == 6


def detect_arm(pdb_text: str) -> Dict[str, Any]:
    """Deduce el brazo de la PROPIA estructura. No hay que declararlo.

    El cofactor identifica el linaje sin ambiguedad:
      * bilina (LBV/BLA/BLV/CYC/PEB/PCB) -> bacteriofitocromo. Brazo B si la
        proteina es del linaje iRFP/miRFP, C si es un fitocromo con el cofactor
        sustituido. Se distingue por la longitud: iRFP es un fragmento GAF-PAS
        (~310 aa); un fitocromo completo es mayor.
      * cromoforo autocatalitico de familia GFP (CRQ/CRO/CR2/NRQ/CSY/GYS) ->
        brazo A.
    Si no se reconoce, se declara desconocido en vez de suponer uno: elegir mal
    el brazo aplica las reglas equivocadas (p.ej. permitir Tipo II donde el
    cofactor apaga el oxigeno singlete).
    """
    # COFACTORES, y si la CELULA DE MAMIFERO los produce. Esto decide si un
    # andamiaje es siquiera admisible: el requisito monocomponente prohibe todo
    # cofactor exogeno, y un candidato que lo exija se DESCALIFICA, no se
    # penaliza -- rompe la reivindicacion de la que depende el programa.
    #
    #   biliverdina IX-alfa (LBV/BLA/BLV): SI, via hemo-oxigenasa a partir del
    #     hemo. Es la ventaja del linaje iRFP/miRFP.
    #   ficocianobilina (CYC/PCB) y ficoeritrobilina (PEB): NO. Son de
    #     cianobacteria y planta. Un andamiaje tipo Cph1/smURFP las necesita, y
    #     por eso smURFP exige PCB exogena o ingenieria extra para aceptar
    #     biliverdina.
    # CODIGOS VERIFICADOS CONTRA EL PDB EL 2026-08-31, no escritos de memoria.
    # Dos errores que habia y que importan:
    #
    #   PCB  NO es ficocianobilina. En el PDB, PCB es
    #        4,4'-bis(metilsulfonil)-2,2',5,5'-tetraclorobifenilo: un bifenilo
    #        policlorado, un contaminante ambiental. Tenerlo en la lista de
    #        bilinas exogenas hacia que el sistema DESCALIFICARA un andamiaje
    #        por contener un contaminante. La ficocianobilina real es CYC.
    #   BLR  SI es una bilina (C33 H36 N4 O6, mismo esqueleto que la
    #        biliverdina C33 H34 N4 O6) pero su nombre en el PDB es IUPAC, no
    #        "biliverdin", asi que no aparecia en ninguna busqueda por nombre.
    ENDOGENOUS_BILIN = {"LBV", "BLA", "BLV", "BLR"}
    EXOGENOUS_BILIN = {"CYC", "PEB"}
    BILIN = ENDOGENOUS_BILIN | EXOGENOUS_BILIN
    GFP = {"CRQ", "CRO", "CR2", "NRQ", "CSY", "GYS", "CH6", "CFY"}
    try:
        from structural_review import _parse_atoms
    except Exception as e:  # noqa: BLE001
        return {"detected": False, "reason": f"no se pudo leer la estructura: {e}"}
    atoms, het = _parse_atoms(pdb_text)
    presentes = {a.get("resn") for a in het if a.get("resn") not in ("HOH",)}
    n_res = len({(a.get("chain"), a.get("resi")) for a in atoms})

    bil = presentes & BILIN
    gfp = presentes & GFP

    # RESPALDO POR FORMULA. Una lista de codigos siempre se queda corta: el PDB
    # tiene cientos de variantes y EYAM puede traer una que no este. El
    # esqueleto de una bilina es C33 N4 O6 (biliverdina C33H34N4O6,
    # ficocianobilina C33H40N4O6, BLR C33H36N4O6). Si aparece un HETATM
    # desconocido con esa formula, se trata como bilina y se DICE que se
    # reconocio por formula, no por codigo.
    por_formula = []
    if not bil and not gfp and presentes:
        for resn in sorted(presentes):
            f = _fetch_formula(resn)
            if f and _is_bilin_formula(f):
                por_formula.append({"resname": resn, "formula": f})
        if por_formula:
            bil = {por_formula[0]["resname"]}
    if gfp:
        return {
            "detected": True,
            "arm": "A",
            "chromophore": sorted(gfp)[0],
            "n_residues": n_res,
            "why": (
                "cromoforo de familia GFP formado autocataliticamente: "
                "sin cofactor externo, linaje KillerRed"
            ),
        }
    if bil:
        cof = sorted(bil)[0]
        arm = "B" if n_res <= 340 else "C"
        endog = bool(bil & ENDOGENOUS_BILIN)
        out = {
            "detected": True,
            "arm": arm,
            "chromophore": cof,
            "n_residues": n_res,
            "cofactor_endogenous": endog,
            "recognized_by": ("formula del PDB" if por_formula else "codigo en el registro"),
            "formula_match": (por_formula[0] if por_formula else None),
            "why": (
                f"cofactor de bilina ({cof}) y {n_res} residuos: "
                + (
                    "fragmento GAF-PAS, linaje iRFP/miRFP"
                    if arm == "B"
                    else "fitocromo completo, brazo de cofactor sustituido"
                )
            ),
        }
        if not endog:
            out["disqualified"] = True
            out["disqualification_reason"] = (
                f"{cof} (ficocianobilina/ficoeritrobilina) NO la producen las "
                "celulas de mamifero: exigiria administrarla, y eso rompe el "
                "requisito monocomponente. Se DESCALIFICA, no se penaliza"
            )
            out["what_would_be_needed"] = (
                "un andamiaje que una biliverdina IX-alfa (que la celula si "
                "fabrica via hemo-oxigenasa), o ingenieria del bolsillo para "
                "que acepte biliverdina en vez de PCB"
            )
        return out
    return {
        "detected": False,
        "n_residues": n_res,
        "hetatm_found": sorted(presentes)[:8],
        "reason": (
            "no se reconocio el cromoforo en la estructura; declarar "
            "`arm` y `chromophore` explicitamente"
        ),
        "what_would_be_needed": "el resname del cofactor o cromoforo",
    }


def _completeness(stages: Dict[str, Any]) -> Dict[str, Any]:
    """Contabilidad honesta de huecos: cuantas etapas sin dato, y por que.

    Se calcula en TODOS los caminos de salida, incluido el corto. Si faltase en
    alguno, un consumidor podria leer la ausencia de huecos como que no los hay.
    """
    huecos = [k for k, v in stages.items() if isinstance(v, dict) and v.get("available") is False]
    return {
        "stages_run": len(stages),
        "stages_unavailable": len(huecos),
        "unavailable": {k: stages[k].get("reason") for k in huecos},
        "note": (
            "Una etapa ausente se declara con su razon. No se rellena con "
            "cero ni se estima: un hueco declarado es utilizable, uno "
            "rellenado no."
        ),
    }


# ── Orquestador ─────────────────────────────────────────────────────────────
def run_engine(
    scaffold: Optional[str] = None,
    pdb_id: Optional[str] = None,
    pdb_text: Optional[str] = None,
    fasta: Optional[str] = None,
    chromophore: Optional[Dict[str, Any]] = None,
    designs: Optional[List[Dict[str, Any]]] = None,
    reference: Optional[Dict[str, Any]] = None,
    protein_seq: Optional[str] = None,
    arm: Optional[str] = None,
    level: str = "full",
    basis: str = "sto-3g",
    vector: str = "saRNA",
    chromophore_quenches_singlet_o2: Optional[bool] = None,
    excited_lifetime_ps: Optional[float] = None,
    electronic_target: Optional[Dict[str, Any]] = None,
    electronic_budget_s: Optional[int] = None,
    allow_qpu: bool = False,
) -> Dict[str, Any]:
    """Corre el motor. Ninguna etapa que falle detiene a las que no dependen de ella."""
    t0 = time.perf_counter()
    level = level if level in STAGES else "full"
    arm_auto = not arm  # sin brazo declarado -> se detecta
    out: Dict[str, Any] = {
        "engine": ENGINE,
        "arm": (arm or "?").upper(),
        "level": level,
        "stages_planned": STAGES[level],
        "stages": {},
    }

    # Coste visible desde el principio: el gasto de GPU no puede ser sorpresa.
    try:
        from quantum_arm import cost_reset

        cost_reset()
    except Exception:  # noqa: BLE001
        pass

    # 0 · estructura
    st = _stage_structure(pdb_id, pdb_text, scaffold, fasta)
    if not st.get("ok"):
        out["stages"]["structure"] = _as_dict(st.get("value"))
        # SOLO las etapas que de verdad necesitan coordenadas se declaran
        # dependientes. `developability` y `construct` trabajan sobre la
        # SECUENCIA, asi que deben correr igual: marcarlas como dependientes
        # ocultaria resultados que si se pueden calcular, que es otra forma de
        # dar informacion falsa.
        for s in _NEEDS_STRUCTURE:
            if s in out["stages_planned"]:
                out["stages"][s] = _as_dict(
                    _na(
                        "depende de la estructura, que no se pudo obtener",
                        needed="una estructura del andamiaje (pdb_id o pdb_text)",
                    )
                )
        out["stages"]["electronic"] = _as_dict(
            _stage_electronic(designs or [], reference, basis, allow_qpu, electronic_budget_s)
        )
        if level == "full":
            out["stages"]["differential"] = _as_dict(
                _na("depende de la estructura, que no se pudo obtener")
            )
            out["stages"]["developability"] = _as_dict(_stage_developability(protein_seq))
            out["stages"]["construct"] = _as_dict(_stage_construct(protein_seq, vector))
        try:
            from quantum_arm import cost_snapshot

            out["quantum_cost"] = cost_snapshot()
        except Exception:  # noqa: BLE001
            pass
        out["completeness"] = _completeness(out["stages"])
        out["wall_seconds"] = round(time.perf_counter() - t0, 2)
        return out

    pdb = st["pdb_text"]

    # La secuencia esta DENTRO de la estructura. Pedirsela aparte al llamador y
    # declarar dos etapas no disponibles cuando no la manda es un fallo de
    # cableado, no una limitacion: `developability` y `construct` trabajan sobre
    # la secuencia, y la estructura ya la contiene. Se deriva de la cadena del
    # cromoforo para que la numeracion case con la de los sitios propuestos.
    seq_source = "recibida en la llamada"
    if not protein_seq:
        try:
            from nir_evolve import sequence_from_structure

            _cad = (chromophore or {}).get("chain") or "A"
            _info = sequence_from_structure(pdb, chain=_cad) or {}
            if _info.get("sequence"):
                protein_seq = _info["sequence"]
                seq_source = (
                    f"derivada de la estructura, cadena {_cad}: " f"{len(protein_seq)} residuos"
                )
        except Exception as e:  # noqa: BLE001
            seq_source = f"no se pudo derivar de la estructura: {str(e)[:110]}"
    out["sequence_source"] = seq_source

    # AUTODETECCION: con la estructura basta. El brazo y el cromoforo salen del
    # propio PDB, asi que el llamador no tiene que saber de linajes.
    det = detect_arm(pdb)
    out["arm_detection"] = det
    if det.get("detected"):
        if not (chromophore or {}).get("resname") and not (chromophore or {}).get("hetatm"):
            chromophore = {"resname": det["chromophore"]}
        if arm_auto:
            out["arm"] = det["arm"]
            for _k, _v in (_ARM_FACTS.get(det["arm"]) or {}).items():
                if _k == "chromophore_note":
                    continue
                if (
                    _k == "chromophore_quenches_singlet_o2"
                    and chromophore_quenches_singlet_o2 is None
                ):
                    chromophore_quenches_singlet_o2 = _v
                elif _k == "excited_lifetime_ps" and excited_lifetime_ps is None:
                    excited_lifetime_ps = _v
    out["stages"]["structure"] = {
        "available": True,
        "source": st.get("source"),
        "atoms": pdb.count("ATOM") + pdb.count("HETATM"),
        "scaffold": scaffold,
    }
    if st.get("folded_from_sequence"):
        out["stages"]["structure"].update(
            {"folded_from_sequence": True, "plddt": st.get("plddt"), "degraded": st.get("degraded")}
        )
    out["pdb_text"] = pdb  # el front lo pinta en 3D

    # 1 · bolsillo
    pocket = _stage_pocket(pdb, chromophore or {"hetatm": True})
    out["stages"]["pocket"] = _as_dict(pocket)

    # 2 · electronica (unica con brazo cuantico, y con puerta de coste)
    # Si no se pasaron geometrias, se CONSTRUYE la region QM del cromoforo desde
    # la propia estructura. Antes el motor se quedaba sin etapa electronica solo
    # porque nadie le habia preparado el XYZ a mano, y el resultado era un "0
    # jobs cuanticos" que parecia contencion de gasto cuando en realidad era que
    # la etapa no habia corrido.
    auto_geom = None
    if not designs:
        try:
            from nir_qm_region import build_qm_region, qm_region_xyz

            # OJO: el analizador de bolsillo emite OBJETOS del contrato, no
            # dicts. Llamar .get() sobre un Measured revienta. Se normaliza
            # antes de leer, igual que ya se hace en nir_mechanism.
            def _plano(x):
                if isinstance(x, dict):
                    return x
                if hasattr(x, "to_dict"):
                    try:
                        return x.to_dict()
                    except Exception:  # noqa: BLE001
                        return {}
                return {}

            _rn = (chromophore or {}).get("resname")
            if not _rn:
                _cr = _plano(
                    (pocket if not isinstance(pocket, dict) else pocket).get("chromophore")
                    if isinstance(pocket, dict)
                    else None
                )
                _diag = _plano(_cr.get("diagnostic"))
                _res = (_diag.get("residues") or [None])[0]
                if _res:
                    _rn = str(_res)[:3]
            if _rn:
                reg = build_qm_region(pdb, _rn)
                out["qm_region"] = {k: v for k, v in reg.items() if k != "atom_spec"}
                if reg.get("available"):
                    auto_geom = qm_region_xyz(reg)
                    designs = [
                        {
                            "design_id": f"{_rn}_wt",
                            "atom": auto_geom,
                            "charge": int(reg.get("formal_charge") or 0),
                            "spin": 0,
                        }
                    ]
        except Exception as e:  # noqa: BLE001
            out["qm_region"] = {
                "available": False,
                "reason": f"no se pudo construir la region QM: {str(e)[:130]}",
            }

    # La etapa electronica va por CASCADA cuando hay geometria propia: espacio
    # activo pi (que es lo que hace direccionable el hardware real), linea base
    # clasica, emulador CUDA-Q y solicitud de QPU, en ese orden de ejecucion y
    # con la prioridad de RESULTADO invertida: manda el peldano mas alto que se
    # consiga, y se declara cual fue.
    # La cascada electronica NO se corre cuando el diferencial va a correr:
    # calcula el MISMO S1 y ademas el absoluto que produce ya sabemos que no
    # sirve (102 nm frente a 585 medidos). Correr las dos multiplicaba por
    # veinte el tiempo del ciclo para obtener un numero que no se usa. El
    # diferencial deja el S1 del silvestre en su salida, que es lo que hace
    # falta. `BIOQL_NIR_RUN_CASCADE=1` la reactiva para auditarla.
    _cascade_on = os.environ.get("BIOQL_NIR_RUN_CASCADE", "0") in ("1", "true", "True")
    electronic = None
    if auto_geom and (_cascade_on or level != "full"):
        try:
            from nir_electronic_cascade import electronic_cascade

            casc = electronic_cascade(
                atom=auto_geom,
                charge=int((out.get("qm_region") or {}).get("formal_charge") or 0),
                basis=basis,
                budget_s=int(electronic_budget_s or ELECTRONIC_BUDGET_S),
                allow_qpu=True,  # se SOLICITA siempre; decide el plano de control
                reference=reference,
                design_id=(designs[0].get("design_id") if designs else "chromophore"),
            )
            out["electronic_cascade"] = {k: v for k, v in casc.items() if k != "result"}
            electronic = casc.get("result") or _na(
                "ningun peldano de la cascada produjo valor; ver `electronic_cascade`",
                needed="ampliar el presupuesto o reducir la base",
            )
        except Exception as e:  # noqa: BLE001
            electronic = _na(f"la cascada electronica fallo: {type(e).__name__}: {str(e)[:120]}")
    if electronic is None and (_cascade_on or level != "full"):
        electronic = _stage_electronic(
            designs or [], reference, basis, allow_qpu, electronic_budget_s
        )
    if electronic is None:
        electronic = _na(
            "no se corrio por separado: el DIFERENCIAL calcula el mismo S1 y es "
            "el valor que se entrega. El absoluto de esta etapa falla por 6x "
            "(102 nm calculados frente a 585 medidos), asi que correrla aparte "
            "only anadia tiempo",
            needed="BIOQL_NIR_RUN_CASCADE=1 para auditarla explicitamente",
        )
    out["stages"]["electronic"] = _as_dict(electronic)

    if level == "full":
        _cof = (chromophore or {}).get("resname") or (
            (out.get("arm_detection") or {}).get("chromophore")
        )
        out["stages"]["mechanism"] = _as_dict(
            _stage_mechanism(
                pocket,
                electronic,
                out["arm"],
                chromophore_quenches_singlet_o2,
                excited_lifetime_ps,
                pdb_text=st.get("pdb_text"),
                resname=_cof,
                chain=(chromophore or {}).get("chain", "A"),
                basis=basis,
                budget_s=int(electronic_budget_s or 3600),
            )
        )
        out["stages"]["mutations"] = _as_dict(
            _stage_mutations(
                pocket,
                electronic_target
                or {
                    "delta_lambda_nm": 65,
                    "t1_ev_min": 0.98,
                    "slow_espt": out["arm"] == "B",
                    "improve_type_I": True,
                },
                out["arm"],
            )
        )
        # DIFERENCIAL: cuanto mueve lambda_max cada sitio propuesto. Es la
        # cantidad que se entrega, porque el absoluto falla por 6x y only la
        # diferencia se puede defender.
        try:
            from nir_differential import differential_shifts

            _mt = out["stages"].get("mutations") or {}
            _sites = _mt.get("sites") if isinstance(_mt, dict) else None
            _rn = (out.get("qm_region") or {}).get("resname") or (chromophore or {}).get("resname")
            if _sites and _rn:
                out["stages"]["differential"] = differential_shifts(
                    pdb_text=pdb,
                    resname=_rn,
                    sites=_sites,
                    reference_lambda_nm=(reference or {}).get("measured_lambda_max_nm"),
                    basis=basis,
                    budget_s=int(electronic_budget_s or ELECTRONIC_BUDGET_S),
                )
            else:
                out["stages"]["differential"] = _as_dict(
                    _na(
                        "no hay sitios propuestos o no se identifico el cromoforo",
                        needed="que la etapa de mutaciones produzca sitios",
                    )
                )
        except Exception as e:  # noqa: BLE001
            out["stages"]["differential"] = _as_dict(
                _na(f"el diferencial fallo: {type(e).__name__}: {str(e)[:130]}")
            )

        # DIFERENCIAL: cuanto mueve lambda_max cada sitio propuesto. Es la
        # cantidad que SE ENTREGA: el absoluto falla por 6x (102 nm calculados
        # frente a 585 medidos) y solo la diferencia se puede defender.
        try:
            from nir_differential import differential_shifts

            _mt = out["stages"].get("mutations") or {}
            _sites = _mt.get("sites") if isinstance(_mt, dict) else None
            _rn = (out.get("qm_region") or {}).get("resname") or (chromophore or {}).get("resname")
            if _sites and _rn:
                out["stages"]["differential"] = differential_shifts(
                    pdb_text=pdb,
                    resname=_rn,
                    sites=_sites,
                    reference_lambda_nm=(reference or {}).get("measured_lambda_max_nm"),
                    basis=basis,
                    budget_s=int(electronic_budget_s or ELECTRONIC_BUDGET_S),
                )
            else:
                out["stages"]["differential"] = _as_dict(
                    _na(
                        "no hay sitios propuestos o no se identifico el cromoforo",
                        needed="que la etapa de mutaciones produzca sitios",
                    )
                )
        except Exception as e:  # noqa: BLE001
            out["stages"]["differential"] = _as_dict(
                _na(f"el diferencial fallo: {type(e).__name__}: {str(e)[:130]}")
            )

        out["stages"]["developability"] = _as_dict(_stage_developability(protein_seq))
        out["stages"]["construct"] = _as_dict(_stage_construct(protein_seq, vector))

    try:
        from quantum_arm import cost_snapshot

        out["quantum_cost"] = cost_snapshot()
    except Exception:  # noqa: BLE001
        pass

    try:
        out["visualization"] = _viz_payload(pdb, pocket, out["stages"].get("mutations"))
    except Exception as e:  # noqa: BLE001
        out["visualization"] = {
            "available": False,
            "reason": f"no se pudo armar la escena: {str(e)[:120]}",
        }

    out["completeness"] = _completeness(out["stages"])
    out["wall_seconds"] = round(time.perf_counter() - t0, 2)
    return out


# ── Nivel de programa: los tres brazos en UNA sola llamada ──────────────────
#
# QUE CABE EN UN PROMPT Y QUE NO, Y POR QUE
# ------------------------------------------
# SI cabe: los TRES BRAZOS de un mismo ciclo. Son independientes y fallan por
#   razones distintas -- ese es justamente el motivo de correrlos a la vez.
#   Se lanzan en paralelo porque la etapa electronica pasa la mayor parte del
#   tiempo esperando a un subproceso, no ocupando el interprete.
#
# NO cabe: los TRES CICLOS. Y no es una limitacion de ingenieria que se pueda
#   levantar con mas maquina: entre un ciclo y el siguiente hay LABORATORIO.
#   El ciclo 2 se calibra contra la fotofisica MEDIDA del ciclo 1, y esa medida
#   tarda semanas. Encadenar los tres ciclos en una sola llamada exigiria
#   inventarse las mediciones intermedias, que es exactamente lo que el sello a
#   ciegas existe para impedir. Un ciclo por prompt no es una molestia del
#   diseño: es la frontera real del problema.

_ARMS_DEFAULT = ("A", "B", "C")

# Hechos del ANDAMIAJE, no entradas del usuario. Si el llamador no los declara,
# obligarle a pasarlos only consigue que el mecanismo salga "indeterminate" por
# un dato que ya se conoce. Cada uno se puede sobreescribir explicitamente.
_ARM_FACTS: Dict[str, Dict[str, Any]] = {
    "A": {
        # Cromoforo tipo GFP: no apaga oxigeno singlete.
        "chromophore_quenches_singlet_o2": False,
        "chromophore_note": (
            "cromoforo de familia GFP formado autocataliticamente "
            "de un tripeptido interno; sin cofactor"
        ),
    },
    "B": {
        # Biliverdina IX-alfa: apagador DOCUMENTADO de oxigeno singlete. Este
        # hecho es el que descarta Tipo II en este brazo por alto que sea T1.
        "chromophore_quenches_singlet_o2": True,
        # Los estados excitados de iRFP702/713/720 decaen en 600-700 ps
        # dominados por transferencia protonica en estado excitado.
        "excited_lifetime_ps": 650.0,
        "chromophore_note": (
            "biliverdina IX-alfa, producida por la celula via "
            "hemo-oxigenasa; apaga oxigeno singlete"
        ),
    },
    "C": {
        # Cofactor sustituido: se desconoce si apaga. NO se asume que no.
        "chromophore_note": (
            "cofactor no-bilina sustituido; su comportamiento "
            "frente al oxigeno singlete no se asume"
        ),
    },
}


def run_program(
    scaffolds: Optional[Dict[str, Dict[str, Any]]] = None,
    cycle: int = 1,
    arms: Optional[List[str]] = None,
    level: str = "full",
    basis: str = "sto-3g",
    electronic_budget_s: Optional[int] = None,
    allow_qpu: bool = False,
    measured_previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Un CICLO completo sobre los tres brazos, en una sola llamada.

    `scaffolds` = {"A": {"pdb_id": ..., "chromophore": {...}, "protein_seq": ...}, ...}
    Un brazo sin andamiaje declarado sale como hueco con su razon; no se inventa.
    """
    import concurrent.futures as _cf

    t0 = time.perf_counter()
    arms = [a.upper() for a in (arms or _ARMS_DEFAULT)]
    scaffolds = scaffolds or {}

    out: Dict[str, Any] = {
        "engine": ENGINE,
        "scope": "program",
        "cycle": int(cycle),
        "arms_requested": arms,
        "level": level,
        "cycle_boundary": {
            "same_prompt": "los tres brazos de este ciclo",
            "next_prompt_requires": (
                "la fotofisica MEDIDA de este ciclo. El siguiente ciclo se "
                "calibra contra ella, y esa medida viene del laboratorio: no se "
                "puede encadenar en la misma llamada sin inventarla"
            ),
            "why_not_all_cycles": (
                "Tres ciclos existen para comprobar si el metodo CORRIGE cuando "
                "se equivoca. Sin la medida real de por medio no hay nada contra "
                "lo que corregir, y el ejercicio pierde su sentido."
            ),
        },
    }

    def _uno(arm: str) -> Tuple[str, Dict[str, Any]]:
        cfg = dict(scaffolds.get(arm) or {})
        # Los hechos del andamiaje se rellenan solo si el llamador NO los dio.
        for _k, _v in (_ARM_FACTS.get(arm) or {}).items():
            if _k != "chromophore_note" and _k not in cfg:
                cfg[_k] = _v
        if not (cfg.get("pdb_id") or cfg.get("pdb_text")):
            return arm, {
                "available": False,
                "reason": f"no se declaro andamiaje para el brazo {arm}",
                "what_would_be_needed": "pdb_id o pdb_text de ese linaje",
            }
        try:
            return arm, run_engine(
                arm=arm,
                level=level,
                basis=basis,
                electronic_budget_s=electronic_budget_s,
                allow_qpu=allow_qpu,
                **{k: v for k, v in cfg.items() if k != "arm"},
            )
        except Exception as e:  # noqa: BLE001
            return arm, {
                "available": False,
                "reason": f"el brazo {arm} fallo: {type(e).__name__}: {str(e)[:130]}",
            }

    # Paralelo: la etapa electronica espera a un subproceso, no consume GIL.
    resultados: Dict[str, Any] = {}
    with _cf.ThreadPoolExecutor(max_workers=len(arms)) as ex:
        for arm, res in ex.map(_uno, arms):
            resultados[arm] = res
    out["arms"] = resultados

    # Comparacion entre brazos: es la razon de correrlos juntos.
    comp = []
    for arm in arms:
        r = resultados.get(arm) or {}
        st = r.get("stages") or {}
        mec = st.get("mechanism") or {}
        mut = st.get("mutations") or {}
        comp.append(
            {
                "arm": arm,
                "ran": r.get("available") is not False,
                "mechanism": mec.get("mechanism") if isinstance(mec, dict) else None,
                "limiting_factor": mec.get("limiting_factor") if isinstance(mec, dict) else None,
                "sites": (mut.get("n_returned") if isinstance(mut, dict) else None),
                "chromophore": (_ARM_FACTS.get(arm) or {}).get("chromophore_note"),
                "gaps": ((r.get("completeness") or {}).get("stages_unavailable")),
                "reason": r.get("reason"),
            }
        )
    out["cross_arm"] = {
        "rows": comp,
        "note": (
            "Los tres brazos fallan por razones DISTINTAS: A por la ley del "
            "gap de energia, B porque su cromoforo apaga el oxigeno singlete "
            "y su estado excitado se consume por transferencia protonica, y "
            "C porque el cambio de cofactor saca la absorcion del NIR. "
            "Compararlos en la misma corrida es lo que hace interpretable "
            "que uno falle."
        ),
    }

    # Coste agregado del ciclo entero.
    try:
        from quantum_arm import cost_snapshot

        out["quantum_cost_total"] = cost_snapshot()
    except Exception:  # noqa: BLE001
        pass

    out["wall_seconds"] = round(time.perf_counter() - t0, 2)
    return out


def register_nir_engine_routes(app):
    """Expone el motor. Ninguna salida nombra cliente ni documentos."""
    from flask import jsonify, request

    @app.route("/api/nir/engine", methods=["POST"])
    def _nir_engine():
        p = request.get_json(force=True, silent=True) or {}
        return jsonify(
            run_engine(
                scaffold=p.get("scaffold"),
                pdb_id=p.get("pdb_id"),
                pdb_text=p.get("pdb_text"),
                fasta=p.get("fasta") or p.get("sequence"),
                chromophore=p.get("chromophore"),
                designs=p.get("designs"),
                reference=p.get("reference"),
                protein_seq=p.get("protein_seq"),
                arm=p.get("arm", "A"),
                level=p.get("level", "full"),
                basis=p.get("basis", "sto-3g"),
                vector=p.get("vector", "saRNA"),
                chromophore_quenches_singlet_o2=p.get("chromophore_quenches_singlet_o2"),
                excited_lifetime_ps=p.get("excited_lifetime_ps"),
                electronic_target=p.get("electronic_target"),
                electronic_budget_s=p.get("electronic_budget_s"),
                allow_qpu=bool(p.get("allow_qpu", False)),
            )
        )

    @app.route("/api/nir/program", methods=["POST"])
    def _nir_program():
        p = request.get_json(force=True, silent=True) or {}
        return jsonify(
            run_program(
                scaffolds=p.get("scaffolds"),
                cycle=int(p.get("cycle", 1)),
                arms=p.get("arms"),
                level=p.get("level", "full"),
                basis=p.get("basis", "sto-3g"),
                electronic_budget_s=p.get("electronic_budget_s"),
                allow_qpu=bool(p.get("allow_qpu", False)),
                measured_previous=p.get("measured_previous"),
            )
        )

    @app.route("/api/nir/stages", methods=["GET"])
    def _nir_stages():
        return jsonify({"engine": ENGINE, "stages": STAGES})

    print("[NIR] Motor de proteina cargado (/api/nir/engine, /api/nir/program, /api/nir/stages)")
