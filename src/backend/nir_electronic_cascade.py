"""
nir_electronic_cascade.py — estructura electronica del cromoforo, en cascada.

ORDEN DE PRIORIDAD (declarado, no improvisado)
----------------------------------------------
  1. QPU REAL      -- es el objetivo. Si el plano de control la admite, manda.
  2. CUDA-Q        -- GPU en Modal. Es el emulador, y ademas es lo que ABRE la
                      puerta a la QPU: sin resultado de emulador la admision no
                      concede el paso.
  3. Clasico / ML   -- ultimo recurso, siempre declarado como tal.

POR QUE LA EJECUCION NO EMPIEZA POR LA QPU
-------------------------------------------
La prioridad es del RESULTADO, no del orden de arranque. La admision a QPU exige
siete puertas, y tres de ellas -- `baseline_complete`, `emulator_complete` y
`device_fit` -- solo se satisfacen CORRIENDO antes la linea base clasica y el
emulador. Mandar un trabajo a una maquina real sin comparador seria pagar por un
numero que despues nadie puede juzgar. Asi que se ejecuta base -> emulador ->
QPU, y el que manda en el informe es el ultimo que se consiguio.

POR QUE HAY QUE REDUCIR EL ESPACIO ACTIVO, Y POR QUE NO ES UNA CONCESION
------------------------------------------------------------------------
MEDIDO 2026-08-28: la region QM del cromoforo son 42 atomos. Con valencia
completa eso no cabe en ningun dispositivo existente, y la puerta `device_fit`
lo rechaza con razon. Pero la transicion que interesa -- la que fija lambda_max
-- es pi -> pi* sobre el puente conjugado. Los orbitales sigma no participan.

Seleccionar el sistema pi con AVAS sobre 2pz de C, N y O no es recortar para que
quepa: es elegir los orbitales que HACEN la transicion. Y de paso el espacio
pasa de intratable a ~10-14 orbitales, es decir 20-28 qubits, que si es
direccionable hoy. La reduccion es lo que convierte la QPU real en una opcion.

QUE NO SE HACE
--------------
No se emite un numero sin decir de donde salio. Cada intento deja constancia de
si se ejecuto, con que backend y por que se descarto, y el resultado final
declara en que peldano de la cascada se quedo. Un valor de CUDA-Q presentado
como si viniera de hardware seria fabricacion.

-- MOLEVERA / BIOQL
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

__all__ = [
    "PI_AO_LABELS",
    "AVAS_THRESHOLD",
    "AVAS_THRESHOLD_SWEEP",
    "FRONTIER_K",
    "THEORY_LEVEL_LIMIT",
    "T1_NOT_AVAILABLE_FROM_PI_WINDOW",
    "electronic_cascade",
    "cascade_policy",
]

# Sistema pi: 2pz de los atomos del puente conjugado. Declarado de antemano,
# nunca elegido caso por caso -- eso es justo lo que la politica congelada evita.
PI_AO_LABELS = ("C 2pz", "N 2pz", "O 2pz")

# Techo de orbitales activos para que el mapeo quepa en hardware real.
# Dos qubits por orbital espacial: 14 orbitales = 28 qubits.
MAX_ORBITALS_FOR_QPU = int(os.environ.get("BIOQL_NIR_MAX_ORB_QPU", "14"))

# UMBRAL DE AVAS — es una decision con consecuencias, no una constante fisica.
#
# MEDIDO 2026-08-28 sobre el cromoforo CRQ de KillerRed (42 atomos, sto-3g,
# HF convergido a -1119.040381 Ha). Barrido completo del umbral:
#
#     umbral   orbitales  electrones  qubits   cabe en hardware
#      0.20        31         48        62          no
#      0.40        26         48        52          no
#      0.60        22         44        44          no
#      0.80        16         32        32          no
#      0.90        11         22        22          SI
#      0.95         3          6         6          si, pero se queda en nada
#
# DOS COSAS QUE HAY QUE DECIR EN CLARO:
#
# 1. El sistema pi COMPLETO de este cromoforo son 31 orbitales y 48 electrones.
#    Eso son 62 qubits, y CAS(48,31) es intratable tanto para hardware actual
#    como para DMRG clasico. La idea de que "reducir a pi ya lo hace caber" es
#    FALSA para un cromoforo de este tamano: hay que truncar ademas dentro del
#    propio sistema pi, y eso es una aproximacion con coste, no algo gratis.
#
# 2. La seleccion es ABRUPTA justo donde operamos: de 0.90 a 0.95 el espacio
#    cae de 11 orbitales a 3. Un umbral elegido a ojo puede quedarse sin sistema
#    conjugado sin que nadie lo note. Por eso el valor viaja declarado y el
#    barrido queda aqui como evidencia de por que es este y no otro.
#
# 0.90 es el punto de operacion: CAS(22,11) = 22 qubits, direccionable hoy y
# tratable clasicamente, conservando los orbitales de frontera que dominan la
# transicion pi->pi*.
# CORRECCION MEDIDA 2026-08-28: 0.90 ERA UN VALOR EQUIVOCADO.
#
# Un umbral alto selecciona only orbitales OCUPADOS. CAS(22e,11o) son 11
# orbitales con 22 electrones, es decir COMPLETAMENTE LLENO: sin virtuales no
# hay excitaciones posibles. Se detecto porque DMRG-CASCI devolvio exactamente
# la energia HF (-1119.040381 Ha a seis decimales), que es imposible si hubiera
# correlacion. Un espacio lleno no da error: da un numero correcto para una
# pregunta que no es la nuestra.
#
# Contando ocupados y virtuales, ningun umbral sirve para este cromoforo:
#     umbral   orb  elec   ocupados  virtuales  qubits   utilizable
#      0.20     31    48      24         7        62     si, NO cabe
#      0.40     26    48      24         2        52     si, NO cabe
#      0.60     22    44      22         0        44     NO (lleno)
#      0.80     16    32      16         0        32     NO (lleno)
#      0.90     11    22      11         0        22     NO (lleno)
#
# Los que caben estan llenos; los que tienen virtuales no caben. Seleccionar por
# umbral NO resuelve este sistema: hay que tomar una VENTANA DE FRONTERA con k
# ocupados y k virtuales alrededor del HOMO/LUMO del sistema pi.
AVAS_THRESHOLD = float(os.environ.get("BIOQL_NIR_AVAS_THRESHOLD", "0.20"))
FRONTIER_K = int(os.environ.get("BIOQL_NIR_FRONTIER_K", "6"))  # CAS(12,12) = 24 qubits

# 2026-09-24 (pi_orientation.py): "2pz" es el eje z GLOBAL; en el marco del cristal
# el bloque "pi" de AVAS no era pi. electronic_cascade orienta ahora el plano
# conjugado en xy antes de AVAS. Eso corrige el S1, NO el T1: orientado, el T1 del
# bloque pi sigue absurdo (22.4 eV en LBV/4E04). La regla de abajo se mantiene.
#
# T1 NO SE PUEDE PEDIR AL BLOQUE PI DE AVAS -- MEDIDO 2026-08-29.
#
# Al pedir el triplete mas bajo con `fix_spin_(ss=2)` sobre la ventana de
# frontera del bloque AVAS-pi, salieron valores de ~54 eV para varios
# cofactores. Un T1 de 54 eV es fisicamente imposible: el triplete mas bajo de
# un cromoforo conjugado esta entre 1 y 2 eV.
#
# La causa: AVAS selecciona el subespacio 2pz, y la ventana de frontera que se
# toma dentro NO contiene necesariamente los orbitales que forman el triplete
# mas bajo. Proyectar sobre el sector S=1 de un subespacio que no lo soporta
# devuelve el estado de espin correcto de un espacio EQUIVOCADO, y el numero
# sale enorme sin que nada falle.
#
# ESE ES EL PATRON PELIGROSO: no hay excepcion, no hay aviso, solo un numero
# absurdo que un consumidor distraido publicaria.
#
# Regla: con AVAS-pi + ventana de frontera se pide S1 (singletes puros) y NADA
# mas. Para T1 hacen falta o un espacio activo que incluya los orbitales del
# triplete, o TDDFT de triplete sobre el sistema completo.
T1_NOT_AVAILABLE_FROM_PI_WINDOW = {
    "measured_absurd_values_ev": [54.488, 54.477, 51.329, 54.436],
    "physical_range_ev": [1.0, 2.0],
    "cause": (
        "la ventana de frontera del bloque AVAS-pi no contiene los "
        "orbitales del triplete mas bajo; proyectar sobre S=1 ahi da el "
        "espin correcto de un espacio equivocado"
    ),
    "rule": (
        "con AVAS-pi + ventana de frontera se pide S1 y nada mas; T1 exige "
        "otro espacio activo o TDDFT de triplete"
    ),
    "why_it_matters": (
        "no lanza excepcion ni aviso: devuelve un numero absurdo " "que parece un resultado"
    ),
}

# LIMITE MEDIDO DEL NIVEL DE TEORIA LOCAL -- leer antes de pedir un lambda_max.
#
# Sobre el cromoforo CRQ de KillerRed, ventana de frontera, spin proyectado:
#     base      nao    S1 calculado   lambda      referencia experimental
#     sto-3g    138      12.200 eV     102 nm          585 nm (2.12 eV)
#     6-31g     252      13.927 eV      89 nm          585 nm (2.12 eV)
#
# El error absoluto es de ~10 eV, un factor SEIS en longitud de onda. Y ampliar
# la base lo EMPEORA. La causa esta a la vista en las energias orbitales: el gap
# HF pi HOMO-LUMO en esta base es de 22 eV (-0.3427 a +0.4656 Ha), diez veces el
# real, y una CASCI sobre una ventana pequena no recupera esa diferencia porque
# le falta correlacion dinamica.
#
# CONSECUENCIA PARA EL ENTREGABLE, y es la parte que vale:
# esto es una demostracion MEDIDA SOBRE EL SISTEMA OBJETIVO de que la prediccion
# ABSOLUTA de lambda_max no es viable a este nivel de teoria. No es una cita de
# la literatura: es nuestro propio numero, sobre nuestro propio cromoforo,
# fallando por 6x en el unico caso donde SI hay valor experimental que lo
# desmienta. Es el argumento mas fuerte que tenemos a favor de la arquitectura
# DIFERENCIAL contra referencia medida, y sale de haber corrido el caso, no de
# haberlo supuesto.
#
# Para un lambda_max defendible harian falta base >= cc-pVDZ, correlacion
# dinamica (CASPT2/NEVPT2) y entorno proteico -- y aun asi el error publicado de
# esos metodos es 0.10-0.20 eV, frente a los 0.059 eV que exige el gate.
THEORY_LEVEL_LIMIT = {
    "system": "cromoforo CRQ de KillerRed (3GB3), ventana de frontera CAS(8,8)",
    "measurements": [
        {"basis": "sto-3g", "nao": 138, "s1_ev": 12.200, "lambda_nm": 102},
        {"basis": "6-31g", "nao": 252, "s1_ev": 13.927, "lambda_nm": 89},
    ],
    "experimental_reference": {"lambda_nm": 585, "s1_ev": 2.12},
    "hf_pi_gap_ev": 22.0,
    "verdict": (
        "la prediccion ABSOLUTA de lambda_max NO es viable a este nivel: "
        "error de ~10 eV, factor 6 en longitud de onda, y ampliar la base "
        "lo empeora"
    ),
    "reading": (
        "medido sobre el sistema objetivo, no citado de la literatura. "
        "Es la evidencia propia de que hay que trabajar en DIFERENCIAS "
        "contra una referencia medida al mismo nivel de teoria"
    ),
    "what_would_be_needed": (
        "base >= cc-pVDZ, correlacion dinamica "
        "(CASPT2/NEVPT2) y entorno proteico; aun asi el "
        "error publicado de esos metodos (0.10-0.20 eV) "
        "supera los 0.059 eV que exige el gate"
    ),
}

AVAS_THRESHOLD_SWEEP = {
    "system": "cromoforo CRQ de KillerRed (3GB3), 42 atomos, sto-3g",
    "hf_energy_ha": -1119.040381,
    "rows": [
        {"threshold": 0.20, "orbitals": 31, "electrons": 48, "qubits": 62, "fits": False},
        {"threshold": 0.40, "orbitals": 26, "electrons": 48, "qubits": 52, "fits": False},
        {"threshold": 0.60, "orbitals": 22, "electrons": 44, "qubits": 44, "fits": False},
        {"threshold": 0.80, "orbitals": 16, "electrons": 32, "qubits": 32, "fits": False},
        {"threshold": 0.90, "orbitals": 11, "electrons": 22, "qubits": 22, "fits": True},
        {"threshold": 0.95, "orbitals": 3, "electrons": 6, "qubits": 6, "fits": True},
    ],
    "operating_point": 0.90,
    "reading": (
        "el sistema pi completo son 31 orbitales / 62 qubits: NO cabe. "
        "Hay que truncar DENTRO del sistema pi, y eso es una aproximacion "
        "con coste. Ademas la seleccion es abrupta entre 0.90 y 0.95 "
        "(11 -> 3 orbitales), asi que el umbral es una decision que debe "
        "viajar declarada"
    ),
}

_STEPS = ("classical_baseline", "cudaq_emulator", "real_qpu")


def cascade_policy() -> Dict[str, Any]:
    """La politica, explicita y auditable."""
    return {
        "priority": ["real_qpu", "cudaq", "classical_or_ml"],
        "execution_order": list(_STEPS),
        "why_execution_differs": (
            "la prioridad es del RESULTADO; la admision a QPU exige linea base y "
            "emulador completos, asi que esos se corren primero"
        ),
        "active_space": {
            "criterion": "avas",
            "ao_labels": list(PI_AO_LABELS),
            "max_orbitals_for_qpu": MAX_ORBITALS_FOR_QPU,
            "avas_threshold": AVAS_THRESHOLD,
            "threshold_sweep": AVAS_THRESHOLD_SWEEP,
            "frontier_k": FRONTIER_K,
            "theory_level_limit": THEORY_LEVEL_LIMIT,
            "rationale": (
                "la transicion que fija lambda_max es pi->pi* sobre el "
                "puente conjugado; los orbitales sigma no participan. "
                "Pero el sistema pi COMPLETO de este cromoforo son 31 "
                "orbitales / 62 qubits y tampoco cabe: hay que truncar "
                "dentro del propio pi, y eso SI es una aproximacion con "
                "coste que se declara"
            ),
        },
    }


def _na(reason: str, needed: Optional[str] = None, attempted: Optional[str] = None):
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


def _qpu_gate(baseline_ok: bool, emulator_ok: bool, n_orbitals: Optional[int]) -> Dict[str, Any]:
    """Consulta la admision a QPU con las puertas que ya podemos satisfacer."""
    fit = n_orbitals is not None and n_orbitals <= MAX_ORBITALS_FOR_QPU
    politica = {
        "baseline_complete": bool(baseline_ok),
        "emulator_complete": bool(emulator_ok),
        "device_fit": fit,
    }
    try:
        from quantum_provider_control_plane import provider_statuses, qpu_admission

        adm = qpu_admission(politica)
        provs = []
        for p in provider_statuses():
            d = p.__dict__ if hasattr(p, "__dict__") else dict(p)
            provs.append(
                {
                    "name": d.get("name") or d.get("provider"),
                    "available": d.get("available"),
                    "detail": d.get("reason") or d.get("detail"),
                }
            )
        adm["providers"] = provs
        adm["device_fit_local"] = {
            "n_orbitals": n_orbitals,
            "n_qubits": (None if n_orbitals is None else 2 * n_orbitals),
            "max_orbitals": MAX_ORBITALS_FOR_QPU,
            "fits": fit,
            "note": ("dos qubits por orbital espacial en Jordan-Wigner o " "Bravyi-Kitaev"),
        }
        return adm
    except Exception as e:  # noqa: BLE001
        return {
            "admitted": False,
            "error": f"plano de control no disponible: {str(e)[:110]}",
            "device_fit_local": {"n_orbitals": n_orbitals, "fits": fit},
        }


def electronic_cascade(
    atom: str,
    charge: int = 0,
    spin: int = 0,
    basis: str = "sto-3g",
    budget_s: int = 1200,
    allow_qpu: bool = True,
    reference: Optional[Dict[str, Any]] = None,
    design_id: str = "chromophore",
) -> Dict[str, Any]:
    """Corre la cascada sobre UNA geometria y declara donde se quedo.

    Devuelve el mejor peldano alcanzado mas la traza completa de intentos.
    """
    t0 = time.perf_counter()
    out: Dict[str, Any] = {
        "module": "nir_electronic_cascade",
        "design_id": design_id,
        "policy": cascade_policy(),
        "attempts": {},
    }

    # AVAS sobre PI_AO_LABELS ("2pz") solo ve el sistema pi si el plano
    # conjugado es xy: pi_orientation.py, MEDIDO 2026-09-24. Rotacion rigida; la
    # energia no cambia. Se orienta UNA vez y todo lo que sigue usa esa geometria.
    try:
        from pi_orientation import orient_atom_string

        atom, _, out["pi_orientation"] = orient_atom_string(atom)
    except Exception as e:  # noqa: BLE001
        out["pi_orientation"] = {
            "available": False,
            "reason": f"{type(e).__name__}: {str(e)[:120]}",
        }

    # ── 1. Linea base clasica CON espacio activo pi ─────────────────────────
    # Es tambien lo que satisface `baseline_complete` en la admision a QPU.
    base: Any = None
    n_orb: Optional[int] = None
    try:
        from excited_state_pipeline import run_pipeline_isolated

        res = run_pipeline_isolated(
            timeout=budget_s,
            designs=[
                {"design_id": design_id, "atom": atom, "charge": int(charge), "spin": int(spin)}
            ],
            basis=basis,
            criterion="avas",
            avas_ao_labels=list(PI_AO_LABELS),
            avas_threshold=AVAS_THRESHOLD,
            reference=reference,
            quantum_arm=True,
            allow_qpu=False,
        )
        if isinstance(res, dict) and res.get("error"):
            out["attempts"]["classical_baseline"] = _as_dict(
                _na(
                    f"la linea base no termino en {budget_s}s: {str(res['error'])[:110]}",
                    needed="mas presupuesto, o una base menor",
                    attempted=f"AVAS sobre {list(PI_AO_LABELS)}, base {basis}",
                )
            )
        else:
            base = res
            for rec in res.get("per_design") or []:
                a = (rec.get("stages") or {}).get("active_space") or {}
                if a.get("n_orbitals"):
                    n_orb = int(a["n_orbitals"])
                    break
            out["attempts"]["classical_baseline"] = {
                "available": True,
                "n_orbitals": n_orb,
                "n_qubits_if_mapped": (None if n_orb is None else 2 * n_orb),
                "wall_seconds": res.get("wall_seconds"),
                "active_space_policy": res.get("active_space_policy"),
            }
    except Exception as e:  # noqa: BLE001
        out["attempts"]["classical_baseline"] = _as_dict(
            _na(f"la linea base fallo: {type(e).__name__}: {str(e)[:120]}")
        )

    baseline_ok = bool(base)

    # ── 2. Emulador CUDA-Q ──────────────────────────────────────────────────
    # El brazo cuantico ya corre dentro del pipeline sobre CUDA-Q, con la puerta
    # de multirreferencia decidiendo si el gasto se justifica. Aqui se recoge lo
    # que hizo, no se vuelve a lanzar: repetirlo seria pagar dos veces.
    emu = None
    if baseline_ok:
        for rec in base.get("per_design") or []:
            qa = rec.get("quantum_arm")
            if qa:
                emu = qa
                break
    if emu:
        out["attempts"]["cudaq_emulator"] = {"available": True, "detail": emu}
    else:
        out["attempts"]["cudaq_emulator"] = _as_dict(
            _na(
                "el brazo cuantico no produjo valor en esta geometria; la puerta de "
                "multirreferencia pudo cortarlo por correlacion debil, donde el "
                "metodo clasico ya esta medido como mejor y mas barato",
                needed="un sistema con caracter multirreferencial sobre el umbral",
            )
        )
    emulator_ok = bool(emu)

    # ── 3. QPU real ─────────────────────────────────────────────────────────
    if not allow_qpu:
        out["attempts"]["real_qpu"] = _as_dict(
            _na("no se solicito hardware real en esta llamada", needed="allow_qpu=True")
        )
    else:
        adm = _qpu_gate(baseline_ok, emulator_ok, n_orb)
        out["qpu_admission"] = adm
        if adm.get("admitted"):
            out["attempts"]["real_qpu"] = _as_dict(
                _na(
                    "admitido por el plano de control, pero el envio a hardware no "
                    "esta cableado en esta ruta todavia: el numero seguiria saliendo "
                    "del emulador y presentarlo como hardware seria falsearlo",
                    needed="cablear el envio al proveedor admitido y devolver su job id",
                    attempted="solicitud de admision a QPU",
                )
            )
        else:
            faltan = adm.get("missing_gates") or []
            out["attempts"]["real_qpu"] = _as_dict(
                _na(
                    "el plano de control NO admitio hardware real. Puertas sin "
                    f"satisfacer: {', '.join(faltan) if faltan else 'no declaradas'}",
                    needed=(
                        "completar esas puertas; `device_fit` depende del tamano "
                        "del espacio activo y las demas son de presupuesto, "
                        "seguridad y valor cientifico"
                    ),
                    attempted="solicitud de admision a QPU",
                )
            )

    # ── Peldano alcanzado ───────────────────────────────────────────────────
    alcanzado = None
    for paso in reversed(_STEPS):
        a = out["attempts"].get(paso)
        if isinstance(a, dict) and a.get("available"):
            alcanzado = paso
            break
    out["reached"] = alcanzado
    out["result"] = base if baseline_ok else None
    out["headline"] = {
        "step": alcanzado,
        "statement": {
            "real_qpu": "valor de hardware cuantico real",
            "cudaq_emulator": (
                "valor de emulador CUDA-Q sobre GPU, junto a su "
                "comparador clasico. NO es hardware real y no se "
                "presenta como tal"
            ),
            "classical_baseline": (
                "valor clasico. El brazo cuantico no aporto " "aqui, y se dice por que"
            ),
            None: "ningun peldano produjo valor; ver el motivo de cada intento",
        }[alcanzado],
    }
    out["wall_seconds"] = round(time.perf_counter() - t0, 2)
    return out
