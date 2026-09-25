"""
nir_differential.py — desplazamiento de lambda_max por sitio, EN DIFERENCIAL.

QUE CALCULA
-----------
Para cada sitio de mutacion propuesto: cuanto mueve la absorcion del cromoforo
neutralizar la cadena lateral de ese residuo. Mismo cromoforo, MISMA geometria,
distinto campo electrostatico del bolsillo (incrustacion QM/MM con cargas
puntuales Amber14 reales de OpenMM, no cargas formales).

POR QUE EN DIFERENCIAL Y NO EN ABSOLUTO
----------------------------------------
MEDIDO sobre este mismo cromoforo: el lambda_max ABSOLUTO calculado da 102 nm
frente a 585 nm reales -- un factor SEIS. Ampliar la base lo empeora. A este
nivel de teoria el valor absoluto no sirve para nada.

Pero el ERROR es comun a todas las variantes: mismo cromoforo, mismo espacio
activo, misma base, mismo protocolo. Al restar, se cancela. Por eso el Delta se
aplica sobre la energia de la REFERENCIA MEDIDA (KillerRed a 585 nm), no sobre
el absoluto calculado:

    lambda_variante = 1239.84 / (E_referencia_medida + Delta_calculado)

MEDIDO en la serie n->pi* de carbonilos: error absoluto 1.348 eV, error
diferencial 0.080 eV. Cancelacion de 16.8x.

EL ERROR QUE COSTO ENCONTRAR
-----------------------------
Convertir a nanometros DESDE el absoluto calculado de 12 eV comprime el
desplazamiento unas 30 veces: los mismos 0.045 eV daban 0.37 nm en vez de 12.6.
La conversion tiene que anclarse en la referencia medida o el resultado es
correcto en eV e inutil en nm.

LIMITES, DECLARADOS
-------------------
  * Modelo PURAMENTE ELECTROSTATICO: no mueve geometria ni reoptimiza el
    cromoforo. Sirve para RANKEAR sitios; no es el numero final que va al banco.
  * Los desplazamientos NO son aditivos: sumar los efectos individuales
    sobreestima. Las combinaciones hay que calcularlas, y este modulo las
    calcula si se le piden.
  * OpenMM y pyscf NO pueden convivir en el mismo proceso (dos runtimes OpenMP
    -> numeros corruptos en silencio). Las cargas se sacan en un subproceso y la
    parte cuantica en otro.

-- MOLEVERA / BIOQL
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "differential_shifts",
    "make_spectral_fn",
    "electronic_cis",
    "REFERENCE_LAMBDA_NM",
    "CANCELLATION_EVIDENCE",
    "CROSS_METHOD_VALIDATION",
]

# VALIDACION CRUZADA ENTRE METODOS
# --------------------------------
# MEDIDO 2026-08-30. Misma perturbacion (+1 de carga formal repartido en 20
# atomos del entorno), mismo sistema, tres metodos:
#
#   metodo   S1 silvestre   fraccion del desplazamiento
#   ------   ------------   ---------------------------
#   CIS         2.876 eV           +0.01747
#   CASCI      10.011 eV           +0.01681
#   CASSCF      0.430 eV           -0.01942
#   experimental 2.12 eV
#
# CIS y CASCI coinciden al 4% y en el mismo signo. CASSCF discrepa en SIGNO, y
# ademas da un S1 absoluto de 0.43 eV, que es imposible para este cromoforo: el
# CASSCF promediado en estados convergio a una solucion patologica. El metodo
# roto era el falsador, no el diferencial.
#
# Por eso el primario pasa a ser CIS: su absoluto es defendible (2.88 frente a
# 2.12 experimental), asi que el factor de transferencia relativa es 0.74 en vez
# del 0.21 que salia con CASCI, y se extrapola mucho menos. CASCI sigue
# disponible: es 10x mas barato (4.5s frente a 55s) y sirve de contraste.
#
# NO usar CASSCF con esta configuracion como referencia sin comprobar antes que
# converge a algo fisico.
# ADVERTENCIA MEDIDA 2026-08-31: CASCI NO SIRVE COMO CONTRASTE AQUI.
# Ante perturbaciones de campo SIMETRICAS (+1 y -1 sobre los mismos atomos) la
# respuesta debe ser casi simetrica en regimen lineal. Medido:
#
#   metodo   delta(+1)   delta(-1)   asimetria
#   CIS       +0.05023    -0.04726     0.94x   <- fisico
#   CASCI     +0.16824    -0.53856     3.20x   <- NO fisico
#   CIS       +0.01664    -0.01593     0.96x   (segundo juego de atomos)
#   CASCI     +0.15690    -0.43222     2.75x
#
# La ventana CAS(8,8) no describe bien el sistema bajo campo. El "desacuerdo
# entre metodos" que se venia reportando como incertidumbre del diferencial era
# en buena parte esta asimetria, no una limitacion del modelo.
# CASCI se conserva por su coste (4.5 s frente a 55 s) pero NO se usa como
# falsador del diferencial.
CASCI_ASYMMETRY_WARNING = {
    "measured": "2026-08-31",
    "symmetric_perturbation_response": {
        "cis": {"plus": 0.05023, "minus": -0.04726, "asymmetry": 0.94},
        "casci": {"plus": 0.16824, "minus": -0.53856, "asymmetry": 3.20},
    },
    "conclusion": (
        "CASCI responde 3.2x mas a un campo negativo que a uno "
        "positivo identico. Eso no es fisica del cromoforo: es la "
        "ventana activa. NO usar como contraste del diferencial"
    ),
    "cis_is_linear": True,
}

# CAUSA DEL S1 ABSURDO, MEDIDA 2026-09-24 (pi_orientation.py): AVAS sobre "2pz"
# usa el eje z GLOBAL. En el marco del cristal la ventana CAS(8,8) dejaba fuera el
# HOMO (0.8 % dentro en LBV/4E04). Con el plano conjugado en xy: HOMO 84 %, LUMO
# 97 %, S1 de 14.35 a 3.43 eV, misma energia RHF. La asimetria 3.2x NO se re-midio.
# Las plantillas _QUANTUM y _SPECTRAL ya orientan la geometria en la ruta CASCI.
# Los valores de abajo son el registro historico de los sintomas y no se tocan.
# El metodo del diferencial. NO es una preferencia: sobre este cromoforo
# CASCI+AVAS da S1 = 14.37 eV contra 2.12 eV medidos (6.8x) y responde 3.2x mas
# a un campo negativo que a uno positivo identico. Eso no es fisica, es la
# ventana CAS(8,8). Los sintomas en el resultado son inconfundibles:
# desplazamientos de +/-195 nm por anular UNA cadena lateral, error de
# aditividad de 221 nm, y el sitio 203 saliendo al AZUL cuando la mutacion
# medida desplaza al ROJO. CIS/TDA da 2.88 eV y su curva de respuesta esta
# validada con 45 calculos en 5 bases (ver BASIS_CONVERGENCE).
DIFFERENTIAL_METHOD = "tda"
DIFFERENTIAL_METHOD_EVIDENCE = {
    "chosen": "tda",
    "rejected": "casci+avas",
    "s1_wt_ev": {"tda": 2.876, "casci": 14.367, "experimental": 2.12},
    "casci_error_factor": 6.8,
    "why": (
        "CASCI+AVAS con CAS(8,8) no describe el cromoforo bajo campo: "
        "asimetria 3.2x ante perturbacion simetrica y S1 absoluto 6.8x por "
        "encima del medido. Ya estaba escrito en CASCI_ASYMMETRY_WARNING y "
        "la ruta de produccion lo usaba igualmente"
    ),
}

# ── Convergencia de base y regimen de perturbacion, MEDIDOS ────────────────
# 45 calculos: 5 bases x 9 magnitudes de perturbacion (-4 a +4), TDA en GPU.
#
# Lo que se creia "no convergencia" eran DOS cosas distintas, y ninguna era el
# metodo fallando:
#
#  1. Se comparaba el COCIENTE de asimetria entre tres puntos sueltos. Ese
#     estadistico divide dos numeros que casi se cancelan, asi que cerca de
#     cero se dispara aunque la diferencia absoluta sea diminuta. La cantidad
#     fisica es la PENDIENTE de la curva de respuesta.
#  2. Se usaba STO-3G, una base minima que se sale 8.9 nm de las balanceadas.
#
# Con difusas, el diferencial CONVERGE: de 468 a 714 funciones se mueve 0.20 nm.
BASIS_CONVERGENCE = {
    "measured": "2026-09-01",
    "protocol": (
        "9 magnitudes de perturbacion por base (-4 a +4), pendiente "
        "por minimos cuadrados en |q|<=1; TDA en GPU (A100)"
    ),
    "slope_ev_per_charge": {
        "sto-3g": {"n_ao": 138, "slope": 0.048732, "nm_at_1_charge": -13.1},
        "6-31g": {"n_ao": 252, "slope": 0.016688, "nm_at_1_charge": -4.57},
        "6-31g*": {"n_ao": 372, "slope": 0.008860, "nm_at_1_charge": -2.44},
        "6-31+g*": {"n_ao": 468, "slope": 0.015332, "nm_at_1_charge": -4.20},
        "aug-cc-pvdz": {"n_ao": 714, "slope": 0.014597, "nm_at_1_charge": -4.00},
    },
    "converged": True,
    "convergence_evidence": (
        "6-31+G* -> aug-cc-pVDZ mueve el desplazamiento "
        "0.20 nm (4.8% en pendiente) al pasar de 468 a "
        "714 funciones de base"
    ),
    "numerical_precision_mev": 0.68,
    "numerical_precision_nm": 0.2,
    "basis_uncertainty_nm": 0.2,
    "unbalanced_basis_note": (
        "6-31G* es el atipico (-2.44 nm) porque anade "
        "POLARIZACION sin DIFUSAS, y las difusas son las "
        "que mandan en una propiedad de respuesta. Al "
        "anadirlas (6-31+G*) el valor vuelve a su sitio"
    ),
    "minimal_basis_rejected": ("STO-3G se sale 8.9 nm: NO usar para el " "diferencial"),
}

# Regimen de validez de la perturbacion. A |q|=4 con base difusa el estado S1
# CRUZA con otro y el delta se va a -0.315 eV donde deberia ser ~+0.05: un solo
# punto fuera de regimen hundio un ajuste de 9 puntos de R2=0.996 a R2=0.14.
# Por eso hay un tope, y por eso se declara en vez de devolver el numero roto.
PERTURBATION_MAX_CHARGE = 2.0
PERTURBATION_REGIME = {
    "safe_abs_charge": 1.0,
    "max_abs_charge": PERTURBATION_MAX_CHARGE,
    "r2_by_window": {"|q|<=1": 0.9956, "|q|<=2": 0.9800, "|q|<=4": 0.1379},
    "residual_mev_by_window": {"|q|<=1": 0.68, "|q|<=2": 2.62, "|q|<=4": 93.10},
    "failure_mode": (
        "cruce de estados: a |q|=4 con base difusa el S1 deja de "
        "ser el mismo estado y el delta cambia de signo"
    ),
}


def perturbation_in_regime(abs_charge: float) -> Dict[str, Any]:
    """Dice si una perturbacion cae en el regimen donde el delta es valido.

    No es una advertencia decorativa: fuera de regimen el S1 cruza con otro
    estado y el numero que sale NO es el desplazamiento de la banda, es otra
    transicion. Devolverlo como si lo fuera es peor que no devolver nada.
    """
    q = abs(float(abs_charge))
    if q <= PERTURBATION_REGIME["safe_abs_charge"]:
        return {"in_regime": True, "window": "|q|<=1", "expected_residual_mev": 0.68}
    if q <= PERTURBATION_MAX_CHARGE:
        return {
            "in_regime": True,
            "window": "|q|<=2",
            "expected_residual_mev": 2.62,
            "note": ("fuera de la ventana mas segura: el residuo sube de " "0.68 a 2.62 meV"),
        }
    return {
        "in_regime": False,
        "window": f"|q|={q:.1f}",
        "reason": PERTURBATION_REGIME["failure_mode"],
        "what_would_be_needed": (f"una perturbacion de |q| <= " f"{PERTURBATION_MAX_CHARGE:.0f}"),
    }


CROSS_METHOD_VALIDATION = {
    "date": "2026-08-30",
    "perturbation": "+1 de carga formal repartido en 20 atomos del entorno",
    "experimental_s1_ev": 2.12,
    "methods": [
        {
            "method": "cis",
            "s1_wt_ev": 2.876,
            "fraction": 0.01747,
            "seconds_per_point": 55,
            "usable": True,
        },
        {
            "method": "casci",
            "s1_wt_ev": 10.011,
            "fraction": 0.01681,
            "seconds_per_point": 4.5,
            "usable": True,
        },
        {
            "method": "casscf",
            "s1_wt_ev": 0.430,
            "fraction": -0.01942,
            "seconds_per_point": 413,
            "usable": False,
            "why_not": (
                "S1 absoluto de 0.43 eV: imposible. El promediado de "
                "estados convergio a una solucion patologica"
            ),
        },
    ],
    "agreement_cis_casci_pct": 3.9,
    "superseded_by": (
        "CASCI_ASYMMETRY_WARNING: la coincidencia que se cita "
        "abajo se midio con UNA sola perturbacion positiva. Con "
        "el par simetrico completo, CASCI se revela asimetrico "
        "3.2x y no vale como contraste"
    ),
    "conclusion": (
        "dos metodos independientes coinciden en signo y magnitud "
        "del desplazamiento fraccional; el diferencial es estable. "
        "La discrepancia venia del falsador, no del modelo"
    ),
}


HERE = os.path.dirname(os.path.abspath(__file__))

# Referencia MEDIDA. Sin ella no hay diferencial que anclar.
REFERENCE_LAMBDA_NM = float(os.environ.get("BIOQL_NIR_REF_LAMBDA_NM", "585.0"))
EV_NM = 1239.84

CANCELLATION_EVIDENCE = {
    "system": "serie n->pi* de carbonilos (formaldehido, acetaldehido, acetona)",
    "absolute_error_ev": 1.348,
    "differential_error_ev": 0.080,
    "cancellation_factor": 16.8,
    "reading": (
        "el error sistematico es comun a variantes tratadas con el mismo "
        "protocolo, asi que se cancela al restar"
    ),
}

_CLEAN_OMP = {
    "KMP_DUPLICATE_LIB_OK": "FALSE",
    "OMP_NUM_THREADS": "4",
    "MKL_NUM_THREADS": "4",
    "PYTHONHASHSEED": "0",
}


def _na(reason: str, needed: Optional[str] = None):
    try:
        from result_contract import NotAvailable

        return NotAvailable(reason=reason, what_would_be_needed=needed)
    except Exception:  # noqa: BLE001
        return {"available": False, "reason": reason, "what_would_be_needed": needed}


def _run(script: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """Ejecuta un paso en subproceso limpio y devuelve su JSON."""
    env = dict(os.environ)
    env.update(_CLEAN_OMP)
    env["PYTHONPATH"] = HERE + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=HERE,
    )
    for line in reversed((p.stdout or "").splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError(f"sin resultado (rc={p.returncode}): {(p.stderr or '')[-300:]}")


# Paso 1 — cargas del bolsillo. OpenMM vive SOLO aqui.
_CHARGES = r"""
import sys, json, warnings; warnings.filterwarnings("ignore")
p = json.loads(sys.stdin.read())
from structural_review import _fetch_pdb_text
from nir_qm_region import build_qm_region, qm_region_xyz
import quantum_binding_cycle as Q
pdb = p.get("pdb_text") or _fetch_pdb_text(p["pdb_id"])
reg = build_qm_region(pdb, p["resname"])
if not reg.get("available"):
    print(json.dumps({"ok": False, "reason": reg.get("reason")})); raise SystemExit
xyz = [c for _, c in reg["atom_spec"]]
cen = [sum(v[i] for v in xyz)/len(xyz) for i in range(3)]
ch = Q.protein_point_charges(pdb, cen, cutoff_angstrom=p.get("cutoff", 12.0))
if not ch.get("available"):
    print(json.dumps({"ok": False, "reason": ch.get("reason")})); raise SystemExit
# Cargas de la cadena lateral de cada sitio: es lo que la mutacion cambia.
from structural_review import _parse_atoms
atoms, _ = _parse_atoms(pdb)
BB = {"N","CA","C","O"}
import math
sel = {}
for pos in p["positions"]:
    sc = [(a["x"],a["y"],a["z"]) for a in atoms
          if a["chain"] == p.get("chain","A") and str(a["resi"]).strip() == str(pos)
          and a["name"] not in BB]
    ii = []
    for k, c in enumerate(ch["coords_angstrom"]):
        for s in sc:
            if math.dist(c, s) <= 0.35:
                ii.append(k); break
    sel[str(pos)] = ii
print(json.dumps({"ok": True, "geom": qm_region_xyz(reg),
                  "charge": reg["formal_charge"], "n_atoms": reg["n_atoms_total"],
                  "coords": ch["coords_angstrom"], "charges": ch["charges_e"],
                  "sel": sel}))
"""

# Paso 2 — parte cuantica. pyscf vive SOLO aqui.
_QUANTUM = r"""
import sys, json, warnings, numpy as np, time; warnings.filterwarnings("ignore")
p = json.loads(sys.stdin.read())
from pyscf import gto, scf, mcscf, fci
from pyscf.mcscf import avas
from pyscf.qmmm import mm_charge
coords = np.array(p["coords"]); q0 = np.array(p["charges"])

METODO = str(p.get("method", "tda")).lower()

# AVAS sobre "2pz" solo ve el sistema pi si el plano conjugado es el plano xy
# (pi_orientation.py, MEDIDO 2026-09-24: en el marco del cristal la ventana
# dejaba fuera el HOMO). Rotacion rigida, aplicada tambien a las cargas. TDA/CIS
# no dependen del marco y no se tocan.
if METODO not in ("tda", "cis"):
    from pi_orientation import orient_atom_string
    p["geom"], coords, _pi_info = orient_atom_string(p["geom"], coords)

def s1(q):
    mol = gto.M(atom=p["geom"], basis=p["basis"], charge=p["charge"], verbose=0)
    mf = mm_charge(scf.RHF(mol), coords, q).run()
    if METODO in ("tda", "cis"):
        # El respaldo local DEBE correr el mismo metodo que el reparto. Si no,
        # perder la conexion cambia el metodo en silencio y el numero sale de
        # una ruta que el informe no declara.
        from pyscf import tdscf
        td = tdscf.TDA(mf); td.nstates = 2; td.verbose = 0
        td.conv_tol = 1e-8; td.kernel()
        return float(td.e[0]*27.211386245988), float(mf.e_tot), 0
    norb, nelec, orbs = avas.avas(mf, ["C 2pz","N 2pz","O 2pz"],
                                  threshold=0.2, minao="minao")
    nocc = nelec//2; ncore = (mol.nelectron-nelec)//2; k = p["frontier_k"]
    mc = mcscf.CASCI(mf, 2*k, 2*k); mc.mo_coeff = orbs; mc.ncore = ncore+nocc-k
    mc.fcisolver = fci.direct_spin1.FCI()
    fci.addons.fix_spin_(mc.fcisolver, shift=0.5, ss=0)
    mc.fcisolver.nroots = 2; mc.verbose = 0
    e = mc.kernel()[0]
    return float((e[1]-e[0])*27.211386245988), float(e[0]), int(2*k)

t0 = time.time()
s1_wt, e0_wt, nq = s1(q0)
out = {"ok": True, "s1_wt_ev": s1_wt, "e0_wt_ha": e0_wt, "n_qubits": nq,
       "wt_seconds": round(time.time()-t0, 1), "sites": [], "combos": []}
for site in p["sites"]:
    ii = p["sel"].get(str(site["position"])) or []
    if not ii:
        out["sites"].append({**site, "available": False,
                             "reason": "sin cargas asignadas a su cadena lateral"})
        continue
    q = q0.copy(); q[ii] = 0.0
    t = time.time()
    try:
        v, _e0, _ = s1(q)
        out["sites"].append({**site, "available": True, "delta_ev": v - s1_wt,
                             "seconds": round(time.time()-t, 1)})
    except Exception as ex:
        out["sites"].append({**site, "available": False,
                             "reason": f"{type(ex).__name__}: {str(ex)[:110]}"})
for combo in p.get("combos") or []:
    ii = []
    for pos in combo:
        ii += (p["sel"].get(str(pos)) or [])
    if not ii:
        continue
    q = q0.copy(); q[ii] = 0.0
    try:
        v, _e0, _ = s1(q)
        out["combos"].append({"positions": combo, "delta_ev": v - s1_wt})
    except Exception as ex:
        out["combos"].append({"positions": combo, "error": str(ex)[:90]})
print(json.dumps(out))
"""


# Energia de la referencia medida, en eV. Es el ancla de toda la conversion.
def _ref_ev(ref_nm: float) -> float:
    return EV_NM / ref_nm


# Banda fisica admisible para el resultado. Un fotosensibilizador de esta
# familia no absorbe ni en el ultravioleta duro ni mas alla del infrarrojo
# cercano; fuera de aqui el numero no describe nada real.
LAMBDA_MIN_NM = 300.0
LAMBDA_MAX_NM = 1400.0


def _lambda_from_delta(delta_ev: float, ref_nm: float):
    """Convierte un desplazamiento de energia en longitud de onda.

    OJO AL POLO. La expresion tiene una singularidad en delta_ev = -E_ref: el
    denominador pasa por cero y cambia de signo. MEDIDO 2026-08-30: una
    combinacion de tres sustituciones dio -9809 nm, una longitud de onda
    NEGATIVA, y salia como si fuera un resultado. No hay guardia posible por
    debajo del polo: ahi la formula ya no describe nada.

    Devuelve None cuando el resultado no es fisico, para que el llamador lo
    declare en vez de propagar un numero inventado.
    """
    den = _ref_ev(ref_nm) + delta_ev
    if den <= 1e-6:
        return None
    lam = EV_NM / den
    if not (LAMBDA_MIN_NM <= lam <= LAMBDA_MAX_NM):
        return None
    return lam


def _quantum_leg(
    geom: str,
    coords,
    charges,
    charge: int,
    cas_norb: int,
    cas_nelec: int,
    basis: str,
    mr_value: Optional[float] = None,
    force: bool = False,
    timeout: int = 14400,
) -> Dict[str, Any]:
    """Pata CUANTICA: SQD sobre CUDA-Q (A100) con las MISMAS cargas del bolsillo.

    `sqd_embedded` resuelve el fragmento DOS veces -- en el campo de las cargas
    y en vacio -- y devuelve todos los niveles (HF, CCSD, CCSD(T), CASCI exacto
    y SQD) para las dos patas. Eso es justo lo que el diferencial necesita: el
    valor cuantico viaja SIEMPRE junto al clasico sobre el mismo fragmento y el
    mismo espacio activo, asi que si coinciden se dice y no se reclama ventaja.

    PUERTA DE COSTE — anadida 2026-08-29 tras un fallo REAL.
    ---------------------------------------------------------
    La primera version de esta funcion decia en su docstring que llamaba a la
    puerta de multirreferencia "de forma implicita". NO LA LLAMABA. Resultado
    medido: 2.25 horas de A100 (~$4.73) gastadas sin comprobar si el caso
    justificaba el gasto. Es exactamente el mismo defecto que se habia
    corregido en `quantum_arm.sqd_arm` -- repetido aqui.

    Ahora se consulta ANTES de enviar nada. Si la correlacion es debil, no se
    llama: ahi el metodo clasico ya esta MEDIDO como mejor Y mas barato
    (2.68 frente a 12.4 kcal/mol), asi que gastar compraria un resultado peor.
    `force=True` la salta a peticion explicita, y queda constancia de que se
    salto.
    """
    # La pata corre en Modal o en Brev, segun salud (modal_compute_layer, BIOQL_COMPUTE_PREFER).
    try:
        import modal_compute_layer
        from quantum_arm import _COST
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"computo remoto no disponible: {str(e)[:100]}"}
    # ── PUERTA: no se gasta A100 sin justificarlo ───────────────────────────
    if not force:
        try:
            from quantum_arm import sqd_is_warranted

            g = sqd_is_warranted(smiles=None, mr_value=mr_value)
            if g.get("warranted") is False:
                _COST.skipped += 1
                return {
                    "available": False,
                    "gate": g,
                    "reason": ("no se envio a A100: " + g["statement"]),
                    "what_would_be_needed": (
                        "caracter multirreferencial por encima del umbral, o "
                        "force=True para saltarse la puerta a proposito"
                    ),
                }
        except Exception:  # noqa: BLE001
            pass

    try:
        f = modal_compute_layer.function("bioql-ewf-sqd", "sqd_embedded")
        _COST.modal_calls += 1
        t = time.time()
        # `remote()` NO acepta plazo: espera al de la propia funcion remota, que
        # puede ser mucho mayor. El `timeout` de esta firma era decorativo — se
        # declaraba un presupuesto de 4 h que nadie aplicaba, y una pata
        # cuantica lenta bloqueaba indefinidamente los 13 sitios y las 5
        # combinaciones YA calculados. Con spawn + get el presupuesto se cumple.
        mano = f.spawn(
            atom=geom,
            mm_coords=coords,
            mm_charges=charges,
            basis=basis,
            cas_norb=cas_norb,
            cas_nelec=cas_nelec,
            charge=int(charge),
            spin=0,
            classical_reference=True,
        )
        r = mano.get(timeout=int(timeout))
        _COST.seconds += time.time() - t
        return {
            "available": True,
            "backend": "CUDA-Q A100 (Modal) · sqd_embedded",
            "result": r,
            "seconds": round(time.time() - t, 1),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "available": False,
            "reason": f"la pata cuantica fallo: {type(e).__name__}: {str(e)[:150]}",
            "budget_s": int(timeout),
            "what_would_be_needed": (
                f"que SQD termine dentro del presupuesto de {int(timeout)} s, "
                f"o subirlo a proposito. El resto del diferencial NO depende "
                f"de esta pata y se entrega igual"
            ),
        }


def make_spectral_fn(
    pdb_id: Optional[str] = None,
    pdb_text: Optional[str] = None,
    resname: str = "CRQ",
    chain: str = "A",
    reference_lambda_nm: Optional[float] = None,
    basis: str = "sto-3g",
    frontier_k: int = 4,
    budget_s: int = 900,
    method: str = "cis",
) -> Dict[str, Any]:
    """Fabrica el `spectral_fn` que consume el bucle evolutivo.

    Devuelve {"fn": callable, "cache": dict, "stats": dict, ...}. La funcion
    recibe una lista de mutaciones y devuelve el desplazamiento REAL en nm de
    esa COMBINACION -- calculado, no sumado. Los efectos no son aditivos y
    sumarlos sobreestima: medido, cinco sitios que suman +99.7 nm dan +29.8 nm
    juntos.

    CACHE OBLIGATORIA. Sin ella el bucle recalcula la misma combinacion en cada
    generacion: los supervivientes se cruzan entre si, asi que las mismas
    parejas reaparecen. Cada evaluacion cuesta ~15 s de QM, de modo que la cache
    es la diferencia entre minutos y horas.

    MODELO DE LA MUTACION: se escala la carga de la cadena lateral por la razon
    de cargas formales. Invertir (ASP- -> LYS+) es un cambio de 2, no de 1;
    tratarlo como neutralizacion subestima diez veces -- medido, GLU68 pasa de
    +2.4 a +24.5 nm.
    """
    import math

    FORMAL = {"ASP": -1.0, "GLU": -1.0, "LYS": 1.0, "ARG": 1.0, "HIS": 0.5}
    ref = float(reference_lambda_nm or REFERENCE_LAMBDA_NM)
    estado: Dict[str, Any] = {"available": False}

    try:
        chg = _run(
            _CHARGES,
            {
                "pdb_id": pdb_id,
                "pdb_text": pdb_text,
                "resname": resname,
                "chain": chain,
                "positions": [],
            },
            timeout=budget_s,
        )
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"no se pudieron obtener las cargas: {str(e)[:130]}"}
    if not chg.get("ok"):
        return {"available": False, "reason": chg.get("reason")}

    cache: Dict[str, float] = {}
    brillo: Dict[str, float] = {}
    stats = {
        "calls": 0,
        "cache_hits": 0,
        "computed": 0,
        "failed": 0,
        "seconds": 0.0,
        "degraded": 0,
        "budget_s": int(budget_s),
        "escalations": [],
    }
    # Fichero donde persiste la densidad convergida del silvestre entre
    # subprocesos. El SCF no depende de la ventana activa, asi que sigue
    # sirviendo de punto de partida aunque el CAS cambie.
    import tempfile as _tf

    _fd, _dm_path = _tf.mkstemp(suffix=".npy", prefix="nir_dm_")
    os.close(_fd)
    os.unlink(_dm_path)  # que no exista hasta que el silvestre lo escriba

    base: Dict[str, Any] = {
        "s1_wt_ev": None,
        "k": int(frontier_k),
        "budget": int(budget_s),
        "dm_path": _dm_path,
        "method": str(method or "cis").lower(),
    }

    # CALIBRACION DEL PRESUPUESTO — anadida tras un fallo REAL (2026-08-30):
    # sobre un cromoforo de 80 atomos, 32 de 32 calculos fallaron por tiempo.
    # No era falta de sitio ni de cargas (se encontraban bien): un only punto
    # excedia 1200 s con la ventana CAS(8,8), y el bucle pedia 32 con 900 s.
    #
    # La respuesta no es rendirse ni subir el tope a ciegas. Es MEDIR el primer
    # punto y adaptarse:
    #   1. se cronometra el calculo del silvestre,
    #   2. si no cabe, se REDUCE la ventana activa (k=4 -> 3 -> 2) y se reintenta,
    #   3. cada degradacion queda registrada en `stats["escalations"]`.
    # Una ventana menor es una aproximacion mas basta, y por eso se declara --
    # pero un numero aproximado y dicho es utilizable, y un fallo no.
    _K_LADDER = (int(frontier_k), 3, 2)

    def _sel_for(positions: List[int]) -> Dict[str, List[int]]:
        """Indices de carga de la cadena lateral de cada posicion."""
        try:
            r = _run(
                _CHARGES,
                {
                    "pdb_id": pdb_id,
                    "pdb_text": pdb_text,
                    "resname": resname,
                    "chain": chain,
                    "positions": list(positions),
                },
                timeout=budget_s,
            )
            return r.get("sel") or {} if r.get("ok") else {}
        except Exception:  # noqa: BLE001
            return {}

    def fn(muts: Sequence[Dict[str, Any]]) -> Optional[float]:
        stats["calls"] += 1
        clave = ",".join(sorted(f"{m['position']}{m.get('to','')}" for m in muts))
        if clave in cache:
            stats["cache_hits"] += 1
            return cache[clave]

        pos = [int(m["position"]) for m in muts]
        sel = _sel_for(pos)
        if not any(sel.get(str(p)) for p in pos):
            stats["failed"] += 1
            return None

        # DESPLAZAMIENTO ADITIVO DE CARGA FORMAL.
        #
        # Antes esto era una RAZON, qnew/qwt, y estaba mal en dos casos que no
        # son raros sino los mas comunes:
        #
        #   PHE -> TYR  : ambos neutros, qwt = 0 -> el codigo caia en el "else"
        #                 y ponia factor 0.0, que NO significa "sin cambio":
        #                 significa BORRAR toda la carga del residuo. Una
        #                 sustitucion neutra-a-neutra salia como la perturbacion
        #                 electrostatica mas violenta posible. MEDIDO: +388 nm
        #                 de la nada.
        #   ALA -> LYS  : de neutro a cargado. Multiplicando no se puede crear
        #                 carga desde cero, asi que tambien caia en 0.0 y
        #                 borraba el residuo en vez de cargarlo.
        #
        # Aditivo cubre los cuatro casos con una sola regla: se reparte la
        # DIFERENCIA de carga formal entre los atomos del residuo. Neutro a
        # neutro da diferencia 0 y por tanto ningun cambio, que es la respuesta
        # correcta: este modelo only ve carga formal, y ahi no la hay.
        deltas_q = {}
        sin_firma = []
        for m in muts:
            qwt = FORMAL.get((m.get("wild_type") or "").upper(), 0.0)
            qnew = FORMAL.get((m.get("to") or "").upper(), 0.0)
            dq = qnew - qwt
            deltas_q[str(m["position"])] = dq
            if abs(dq) < 1e-9:
                sin_firma.append(f"{m.get('wild_type')}{m['position']}{m.get('to')}")

        # Escalera de degradacion: se intenta con la ventana pedida y, si el
        # tiempo no da, con ventanas menores. Solo se declara fallo cuando NI
        # SIQUIERA la mas basta cabe.
        r = None
        t = time.time()
        for _i, _k in enumerate(_K_LADDER):
            if _k <= 0 or (_i and _k >= base["k"]):
                continue
            _to = int(base["budget"] * (1.0 if _i == 0 else 1.5))
            try:
                r = _run(
                    _SPECTRAL,
                    {
                        "geom": chg["geom"],
                        "charge": chg["charge"],
                        "coords": chg["coords"],
                        "charges": chg["charges"],
                        "sel": sel,
                        "charge_deltas": deltas_q,
                        "basis": basis,
                        "frontier_k": _k,
                        # la densidad convergida del silvestre vive
                        # entre subprocesos: cada combinacion nueva
                        # arranca de ahi en vez de desde cero
                        "dm_path": base.get("dm_path"),
                        "method": base.get("method", "cis"),
                        # al cambiar de ventana el silvestre cambia:
                        # se recalcula en el mismo subproceso.
                        "s1_wt_ev": (base["s1_wt_ev"] if _k == base["k"] else None),
                    },
                    timeout=_to,
                )
            except Exception:  # noqa: BLE001
                r = None
            if r and r.get("ok"):
                if _k != base["k"]:
                    stats["degraded"] += 1
                    stats["escalations"].append(
                        {
                            "from_k": base["k"],
                            "to_k": _k,
                            "reason": (
                                f"CAS({2*base['k']},{2*base['k']}) excedio "
                                f"{_to}s en este sistema"
                            ),
                            "caveat": (
                                "ventana activa menor = aproximacion mas basta; "
                                "los deltas siguen siendo comparables entre si "
                                "porque TODOS se recalculan con esta ventana"
                            ),
                        }
                    )
                    base["k"] = _k  # el resto del bucle usa la misma ventana
                    base["s1_wt_ev"] = r.get("s1_wt_ev")
                    cache.clear()  # lo cacheado con la ventana vieja no vale
                break
            r = None
        stats["seconds"] += time.time() - t
        if not r or not r.get("ok"):
            stats["failed"] += 1
            return None
        if base["s1_wt_ev"] is None:
            base["s1_wt_ev"] = r.get("s1_wt_ev")
        de_raw = float(r["delta_ev"])
        s1_wt = r.get("s1_wt_ev")

        # TRANSFERENCIA RELATIVA, NO ABSOLUTA.
        #
        # El S1 que sale de esta ventana vale ~10 eV; la referencia MEDIDA de
        # esta familia son 2.12 eV (585 nm). El limite de nivel de teoria ya
        # estaba documentado en el modulo electronico, pero la conversion lo
        # ignoraba: sumaba un delta absoluto calculado sobre una transicion casi
        # 5 veces mas energetica de lo que es en realidad. Por eso una sola
        # inversion de carga daba -2.91 eV, MAS que toda la energia de la
        # referencia, y la longitud de onda salia negativa.
        #
        # Lo que si se transfiere entre niveles de teoria es la FRACCION en que
        # se mueve la transicion. Se aplica esa fraccion a la referencia medida:
        #
        #     delta_efectivo = delta_calculado * (E_referencia / E_calculado)
        #
        # Es una aproximacion de primer orden y se declara como tal. El delta
        # crudo viaja tambien en las estadisticas, para que nada quede escondido.
        de = de_raw
        escala = None
        if s1_wt and abs(float(s1_wt)) > 1e-6:
            escala = _ref_ev(ref) / float(s1_wt)
            de = de_raw * escala

        lam = _lambda_from_delta(de, ref)
        if lam is None:
            # fuera de la banda fisica o pasado el polo: no se devuelve numero
            stats["failed"] += 1
            stats.setdefault("unphysical", []).append(
                {
                    "mutations": clave,
                    "delta_ev": round(de, 4),
                    "delta_ev_raw": round(de_raw, 4),
                    "scale": escala,
                    "reason": (
                        f"la conversion cae fuera de {LAMBDA_MIN_NM:.0f}-"
                        f"{LAMBDA_MAX_NM:.0f} nm o pasa el polo en "
                        f"delta_ev = -{_ref_ev(ref):.3f} eV"
                    ),
                }
            )
            return None
        dl = lam - ref
        if sin_firma:
            stats.setdefault("no_formal_charge_change", [])
            for x in sin_firma:
                if x not in stats["no_formal_charge_change"]:
                    stats["no_formal_charge_change"].append(x)
        stats.setdefault(
            "theory_transfer",
            {
                "mode": "fraccion de la transicion, no delta absoluto",
                "s1_computed_ev": s1_wt,
                "e_reference_ev": round(_ref_ev(ref), 4),
                "scale": escala,
                "caveat": (
                    "aproximacion de primer orden: el nivel de teoria da un "
                    "S1 mucho mas alto que el real, asi que se transfiere la "
                    "fraccion en que se mueve, no los eV. Los valores son "
                    "salida de modelo y necesitan contraste en banco"
                ),
            },
        )
        stats.setdefault("raw_deltas", {})[clave] = round(de_raw, 4)
        # Brillo relativo al silvestre: >1 absorbe mas, <1 menos. Se guarda con
        # la MISMA clave que el desplazamiento para que el bucle pueda pesar las
        # dos cosas sobre el mismo candidato.
        _br = r.get("brightness_ratio") if isinstance(r, dict) else None
        if _br is not None:
            brillo[clave] = float(_br)
        cache[clave] = dl
        stats["computed"] += 1
        return dl

    def brightness_fn(muts: Sequence[Dict[str, Any]]) -> Optional[float]:
        """Brillo de la combinacion respecto al silvestre. None si no se midio.

        Devuelve None en vez de 1.0 a proposito: 1.0 significa "igual de
        brillante", y eso es una afirmacion. No haberlo medido es otra cosa.
        """
        clave = ",".join(sorted(f"{m['position']}{m.get('to','')}" for m in muts))
        return brillo.get(clave)

    estado.update(
        {
            "available": True,
            "fn": fn,
            "brightness_fn": brightness_fn,
            "brightness": brillo,
            "cache": cache,
            "stats": stats,
            "reference_lambda_nm": ref,
            "base": base,
            "n_point_charges": len(chg.get("charges") or []),
            "qm_region_atoms": chg.get("n_atoms"),
            "method": (
                "delta de S1 por incrustacion QM/MM sobre la "
                "COMBINACION real, anclado en la referencia medida"
            ),
            "backend": "pyscf CIS/TDA con incrustacion de cargas · OpenMM Amber14",
        }
    )
    return estado


# Paso espectral: una combinacion, en subproceso limpio (pyscf a solas).
_SPECTRAL = r"""
import sys, json, warnings, numpy as np; warnings.filterwarnings("ignore")
p = json.loads(sys.stdin.read())
from pyscf import gto, scf, mcscf, fci
from pyscf.mcscf import avas
from pyscf.qmmm import mm_charge
coords = np.array(p["coords"]); q0 = np.array(p["charges"])

import os
# AVAS sobre "2pz" exige el plano conjugado en xy (pi_orientation.py, 2026-09-24).
# Solo en la ruta CASCI+AVAS; CIS/TDA no dependen del marco.
if str(p.get("method") or "cis").lower() not in ("tda", "cis"):
    from pi_orientation import orient_atom_string
    p["geom"], coords, _pi_info = orient_atom_string(p["geom"], coords)

# La geometria NO cambia entre combinaciones: only cambian las cargas puntuales
# del entorno. Se construye la molecula UNA vez.
mol = gto.M(atom=p["geom"], basis=p["basis"], charge=p["charge"], verbose=0)

# MEDIDO 2026-08-30 sobre este mismo sistema (42 atomos QM, 685 cargas
# puntuales, 138 funciones de base): el SCF se llevaba el 90% del tiempo (13.8s
# de 15.4s). No era la ventana activa — AVAS tarda 0.02s y CASCI 1.6s — asi que
# bajar el tamano del CAS no arreglaba nada, que es justo por lo que la escalera
# de degradacion no servia.
#
# Dos cambios, medidos, que NO tocan el resultado:
#
#  1. DENSITY FITTING. Aproxima los integrales de dos electrones. En una energia
#     absoluta eso seria discutible; aqui NO, porque lo que se usa es el DELTA
#     entre dos configuraciones de carga con la MISMA geometria y la MISMA base,
#     y el error se cancela igual que se cancela el del nivel de teoria. MEDIDO:
#     el S1 absoluto se mueve 0.6 meV y el DELTA no se mueve nada (0.00 meV).
#     2.8x mas rapido.
#  2. ARRANQUE EN CALIENTE. La densidad convergida del silvestre sirve de punto
#     de partida para cada mutante, porque la perturbacion es pequena. Exacto:
#     converge al mismo sitio, only que en menos ciclos.
#
# Juntos: 14.0s -> 4.5s por combinacion (3.1x), con el mismo delta.
DM_PATH = p.get("dm_path") or ""

METODO = str(p.get("method") or "cis").lower()
OSC = []   # fuerza de oscilador de cada llamada a s1, en orden

def s1(q, dm0=None, guardar_dm=False):
    mf = mm_charge(scf.RHF(mol).density_fit(), coords, q)
    mf.kernel(dm0=dm0)
    if guardar_dm and DM_PATH:
        try:
            np.save(DM_PATH, mf.make_rdm1())
        except Exception:
            pass
    if METODO == "cis":
        # CIS/TDA sobre HF. Ver CROSS_METHOD_VALIDATION: da un S1 absoluto
        # defendible (2.88 eV frente a 2.12 experimental) en vez de los 10 eV
        # de CASCI, asi que la transferencia relativa extrapola mucho menos.
        from pyscf import tdscf
        td = tdscf.TDA(mf); td.nstates = 3; td.verbose = 0
        td.kernel()
        # La fuerza de oscilador del estado brillante ES el observable que
        # gobierna el coeficiente de extincion, y hasta ahora se calculaba y se
        # tiraba. Desplazar al rojo apagando el cromoforo es el modo de fallo
        # clasico: sin este numero el bucle no puede verlo.
        try:
            fo = td.oscillator_strength()
            ib = int(np.argmax(fo))
            OSC.append(float(fo[ib]))
        except Exception:
            OSC.append(None)
        return float(td.e[0] * 27.211386245988)
    norb, nelec, orbs = avas.avas(mf, ["C 2pz","N 2pz","O 2pz"],
                                  threshold=0.2, minao="minao")
    nocc = nelec//2; ncore = (mol.nelectron-nelec)//2; k = p["frontier_k"]
    mc = mcscf.CASCI(mf, 2*k, 2*k); mc.mo_coeff = orbs; mc.ncore = ncore+nocc-k
    mc.fcisolver = fci.direct_spin1.FCI()
    fci.addons.fix_spin_(mc.fcisolver, shift=0.5, ss=0)
    mc.fcisolver.nroots = 2; mc.verbose = 0
    e = mc.kernel()[0]
    return float((e[1]-e[0])*27.211386245988)

try:
    dm_wt = None
    if DM_PATH and os.path.exists(DM_PATH):
        try:
            dm_wt = np.load(DM_PATH)
        except Exception:
            dm_wt = None

    wt = p.get("s1_wt_ev")
    if wt is None:
        # primera vez con esta ventana: se calcula el silvestre y se guarda su
        # densidad para que todas las combinaciones siguientes arranquen de ahi
        wt = s1(q0, dm0=dm_wt, guardar_dm=True)
        if DM_PATH and os.path.exists(DM_PATH):
            try:
                dm_wt = np.load(DM_PATH)
            except Exception:
                pass

    q = q0.copy()
    for pos, dq in (p.get("charge_deltas") or {}).items():
        ii = (p["sel"] or {}).get(pos) or []
        if ii and abs(float(dq)) > 1e-9:
            # la diferencia de carga formal se reparte entre los atomos del
            # residuo: no se escala lo que hay, se anade lo que cambia
            q[ii] = q0[ii] + float(dq) / len(ii)
    v = s1(q, dm0=dm_wt)
    _f_wt = OSC[0] if len(OSC) >= 2 else None
    _f_var = OSC[-1] if OSC else None
    print(json.dumps({"ok": True, "s1_wt_ev": wt, "s1_ev": v,
                      "f_wt": _f_wt, "f_variant": _f_var,
                      "brightness_ratio": (None if not _f_wt or not _f_var
                                           else round(_f_var / _f_wt, 4)),
                      "delta_ev": v - wt,
                      "method": METODO,
                      "accel": {"density_fit": True,
                                "warm_start": dm_wt is not None}}))
except Exception as ex:
    print(json.dumps({"ok": False, "reason": f"{type(ex).__name__}: {str(ex)[:160]}"}))
"""


# ── El paso cuantico, en paralelo ──────────────────────────────────────────
# El plazo se agotaba porque los N sitios se calculan en SERIE dentro de un
# unico subproceso: con 372 AO cada CASCI son minutos, y doce seguidos no caben
# en ningun presupuesto razonable. Repartidos, el coste total es el del sitio
# mas lento. El metodo no cambia (mismo CASCI + AVAS, mismas cargas), solo
# cambia donde corre; si no hay reparto disponible se vuelve al subproceso.


def _quantum_remoto(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Reparte silvestre + sitios + combinaciones, uno por contenedor.

    Devuelve None (no lanza) si el reparto no esta disponible, para que el
    llamante caiga al subproceso local sin enterarse.
    """
    if os.environ.get("BIOQL_NIR_NO_MODAL", "").strip().lower() in ("1", "true", "si"):
        return None
    try:
        import modal_compute_layer

        fn = modal_compute_layer.function("bioql-nir-differential", "site_s1")
    except Exception:  # noqa: BLE001
        return None

    base = {
        "geom": payload["geom"],
        "charge": payload["charge"],
        "coords": payload["coords"],
        "charges": payload["charges"],
        "basis": payload["basis"],
        "frontier_k": payload["frontier_k"],
        "method": payload.get("method", DIFFERENTIAL_METHOD),
    }
    sel = payload.get("sel") or {}

    cargas = [{**base, "tag": "wt", "zero_idx": []}]
    sitios = list(payload.get("sites") or [])
    for i, sitio in enumerate(sitios):
        ii = sel.get(str(sitio.get("position"))) or []
        cargas.append({**base, "tag": f"s{i}", "zero_idx": list(ii)})
    combos = list(payload.get("combos") or [])
    for j, combo in enumerate(combos):
        ii: List[int] = []
        for pos in combo:
            ii += list(sel.get(str(pos)) or [])
        cargas.append({**base, "tag": f"c{j}", "zero_idx": ii})

    t0 = time.time()
    # Envio individual en vez de `map`: un `map` colgado no dice en que se
    # colgo — el proceso se queda bloqueado en la red sin CPU y sin tareas
    # visibles del otro lado, y por fuera es indistinguible de estar
    # calculando. Con envios sueltos se sabe cual falta y uno que se pierda no
    # se lleva por delante a los otros doce.
    espera_s = int(os.environ.get("BIOQL_NIR_MODAL_TIMEOUT", "5400"))
    try:
        manos = [(c["tag"], fn.spawn(c)) for c in cargas]
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"el reparto fallo al enviar: {type(e).__name__}: {str(e)[:150]}")

    # Los contenedores viven en Modal, pero QUIEN RECOGE es este proceso. Si la
    # maquina se cierra o el proceso muere, el calculo termina y el resultado se
    # tira. Guardar los identificadores permite volver a engancharse: la llamada
    # se recupera con `modal.FunctionCall.from_id(id).get()`.
    _libreta = os.environ.get("BIOQL_NIR_CALL_IDS")
    if _libreta:
        try:
            with open(_libreta, "w") as fh:
                json.dump(
                    {
                        "app": "bioql-nir-differential",
                        "function": "site_s1",
                        "started": time.time(),
                        "calls": {t: m.object_id for t, m in manos},
                    },
                    fh,
                    indent=1,
                )
            print(
                f"[NIR] identificadores guardados en {_libreta}: se puede "
                f"recoger mas tarde aunque muera este proceso",
                flush=True,
            )
        except Exception as e:  # noqa: BLE001
            print(f"[NIR] no se pudieron guardar los identificadores: {e}", flush=True)
    res: Dict[str, Any] = {}
    for etiqueta, mano in manos:
        try:
            res[etiqueta] = mano.get(timeout=espera_s)
        except Exception as e:  # noqa: BLE001
            res[etiqueta] = {
                "ok": False,
                "tag": etiqueta,
                "reason": f"{type(e).__name__}: {str(e)[:150]}",
            }
        print(
            f"[NIR] {etiqueta}: {'ok' if res[etiqueta].get('ok') else res[etiqueta].get('reason','?')[:70]}"
            f" · {len(res)}/{len(manos)} · {time.time() - t0:.0f}s",
            flush=True,
        )

    wt = res.get("wt") or {}
    if not wt.get("ok"):
        raise RuntimeError(f"el silvestre fallo: {wt.get('reason', 'sin razon')}")
    s1_wt = float(wt["s1_ev"])

    out: Dict[str, Any] = {
        "ok": True,
        "s1_wt_ev": s1_wt,
        "e0_wt_ha": wt.get("e0_ha"),
        "n_qubits": wt.get("n_qubits"),
        "wt_seconds": wt.get("seconds"),
        "sites": [],
        "combos": [],
        "executed_on": "modal · un contenedor por configuracion de cargas",
        "wall_seconds": round(time.time() - t0, 1),
        "n_parallel": len(cargas),
    }
    for i, sitio in enumerate(sitios):
        r = res.get(f"s{i}") or {}
        if not (sel.get(str(sitio.get("position"))) or []):
            out["sites"].append(
                {**sitio, "available": False, "reason": "sin cargas asignadas a su cadena lateral"}
            )
        elif r.get("ok"):
            out["sites"].append(
                {
                    **sitio,
                    "available": True,
                    "delta_ev": float(r["s1_ev"]) - s1_wt,
                    "seconds": r.get("seconds"),
                }
            )
        else:
            out["sites"].append(
                {**sitio, "available": False, "reason": r.get("reason", "sin resultado")}
            )
    for j, combo in enumerate(combos):
        r = res.get(f"c{j}") or {}
        if r.get("ok"):
            out["combos"].append({"positions": combo, "delta_ev": float(r["s1_ev"]) - s1_wt})
        else:
            out["combos"].append({"positions": combo, "error": r.get("reason", "sin resultado")})
    return out


def _quantum(payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """Reparto si se puede, subproceso local si no. Misma salida en ambos."""
    try:
        r = _quantum_remoto(payload)
        if r is not None:
            return r
    except Exception as e:  # noqa: BLE001
        # Un fallo del reparto no debe tumbar la etapa: se anota y se sigue.
        print(f"[NIR] reparto no disponible, se usa el subproceso local: {e}")
    payload = {**payload, "method": payload.get("method", DIFFERENTIAL_METHOD)}
    r = _run(_QUANTUM, payload, timeout=timeout)
    r["executed_on"] = (
        f"cpu-local · subproceso unico, sitios en serie · " f"metodo {payload['method']}"
    )
    return r


def differential_shifts(
    pdb_id: Optional[str] = None,
    pdb_text: Optional[str] = None,
    resname: str = "CRQ",
    chain: str = "A",
    sites: Optional[Sequence[Dict[str, Any]]] = None,
    reference_lambda_nm: Optional[float] = None,
    basis: str = "sto-3g",
    frontier_k: int = 4,
    top_combos: int = 3,
    quantum: bool = True,
    budget_s: int = 3600,
) -> Dict[str, Any]:
    """Desplazamiento de lambda_max por sitio, anclado en la referencia medida."""
    t0 = time.perf_counter()
    ref = float(reference_lambda_nm or REFERENCE_LAMBDA_NM)
    out: Dict[str, Any] = {
        "module": "nir_differential",
        "reference_lambda_nm": ref,
        "method": (
            "Delta de S1 por incrustacion QM/MM (cargas Amber14 de OpenMM) "
            "aplicado sobre la energia de la referencia MEDIDA"
        ),
        "backend": "pyscf CIS/TDA con incrustacion de cargas · OpenMM Amber14",
        "cancellation_evidence": CANCELLATION_EVIDENCE,
        # Lo MEDIDO viaja con el resultado, no se queda en el modulo: una
        # tarjeta que no puede mostrar en que base converge ni con que metodo
        # se calculo obliga al lector a creerse el numero.
        "basis_convergence": BASIS_CONVERGENCE,
        "method_evidence": DIFFERENTIAL_METHOD_EVIDENCE,
        "perturbation_regime": PERTURBATION_REGIME,
        "limits": {
            "electrostatic_only": (
                "no mueve geometria ni reoptimiza el cromoforo: "
                "sirve para RANKEAR sitios, no es el numero final"
            ),
            "not_additive": (
                "los desplazamientos NO se suman: las combinaciones se "
                "calculan, y aqui se calculan las mejores"
            ),
            "absolute_lambda_not_usable": (
                "el absoluto calculado falla por 6x "
                "(102 nm vs 585 nm medidos); por eso only "
                "se usa la diferencia"
            ),
        },
    }
    if not sites:
        return {
            **out,
            **_as(
                _na("no se recibio ningun sitio que evaluar", "la salida de nir_mutation_proposal")
            ),
        }
    if not (pdb_id or pdb_text):
        return {**out, **_as(_na("no se recibio estructura", "pdb_id o pdb_text"))}

    posiciones = sorted({int(s["position"]) for s in sites if s.get("position") is not None})
    try:
        chg = _run(
            _CHARGES,
            {
                "pdb_id": pdb_id,
                "pdb_text": pdb_text,
                "resname": resname,
                "chain": chain,
                "positions": posiciones,
            },
            timeout=budget_s,
        )
    except Exception as e:  # noqa: BLE001
        return {
            **out,
            **_as(_na(f"no se pudieron obtener las cargas del bolsillo: {str(e)[:140]}")),
        }
    if not chg.get("ok"):
        return {**out, **_as(_na(f"cargas no disponibles: {chg.get('reason')}"))}

    out["qm_region_atoms"] = chg.get("n_atoms")
    out["n_point_charges"] = len(chg.get("charges") or [])

    unicos, vistos = [], set()
    for s in sites:
        k = (s.get("position"), s.get("objective"))
        if k in vistos:
            continue
        vistos.add(k)
        unicos.append(
            {
                "position": s.get("position"),
                "wild_type": s.get("wild_type"),
                "suggested": s.get("suggested"),
                "objective": s.get("objective"),
            }
        )

    try:
        qm = _quantum(
            {
                "geom": chg["geom"],
                "charge": chg["charge"],
                "coords": chg["coords"],
                "charges": chg["charges"],
                "sel": chg["sel"],
                "sites": unicos,
                "basis": basis,
                "frontier_k": frontier_k,
                "combos": [],
            },
            timeout=budget_s,
        )
    except Exception as e:  # noqa: BLE001
        return {**out, **_as(_na(f"la parte cuantica fallo: {str(e)[:150]}"))}

    filas = []
    for s in qm.get("sites") or []:
        if not s.get("available"):
            filas.append(s)
            continue
        lam = _lambda_from_delta(s["delta_ev"], ref)
        if lam is None:
            # La guarda del polo: un delta que cancela la energia de la
            # referencia manda la longitud de onda al infinito. Eso no es un
            # desplazamiento gigante, es que el modelo lineal dejo de valer
            # ahi. Se declara y NO se convierte.
            filas.append(
                {
                    **s,
                    "available": False,
                    "lambda_nm": None,
                    "delta_lambda_nm": None,
                    "reason": (
                        f"delta de {s['delta_ev']:+.4f} eV fuera del "
                        f"rango convertible sobre una referencia de "
                        f"{ref:.0f} nm: la conversion pasa por un polo "
                        f"y el desplazamiento no es interpretable"
                    ),
                }
            )
            continue
        filas.append({**s, "lambda_nm": round(lam, 1), "delta_lambda_nm": round(lam - ref, 1)})
    filas.sort(key=lambda r: -(r.get("delta_lambda_nm") or -1e9))

    rojos = [r for r in filas if (r.get("delta_lambda_nm") or 0) > 0]
    out.update(
        {
            "available": True,
            # Donde corrio de verdad: el reparto y el subproceso local dan el mismo
            # numero, pero no el mismo tiempo, y la tarjeta debe poder decirlo.
            "executed_on": qm.get("executed_on"),
            "parallel_containers": qm.get("n_parallel"),
            "quantum_wall_seconds": qm.get("wall_seconds"),
            "s1_wt_ev": qm.get("s1_wt_ev"),
            "n_qubits_if_mapped": qm.get("n_qubits"),
            "sites": filas,
            "n_evaluated": len(filas),
            "n_red_shifting": len(rojos),
            "best_single_nm": (rojos[0]["delta_lambda_nm"] if rojos else None),
            "naive_sum_top5_nm": (
                round(sum(r["delta_lambda_nm"] for r in rojos[:5]), 1) if rojos else None
            ),
            "gate_target_nm": 65.0,
            "sum_caveat": (
                "la suma de efectos individuales SOBREESTIMA: la "
                "electrostatica no es aditiva. Se calcula la combinacion "
                "real por separado"
            ),
        }
    )

    # Combinacion real de los mejores: es lo que decide si se llega al gate.
    if len(rojos) >= 2 and top_combos > 0:
        combos = [[r["position"] for r in rojos[:n]] for n in range(2, min(len(rojos), 5) + 1)]
        try:
            qm2 = _quantum(
                {
                    "geom": chg["geom"],
                    "charge": chg["charge"],
                    "coords": chg["coords"],
                    "charges": chg["charges"],
                    "sel": chg["sel"],
                    "sites": [],
                    "basis": basis,
                    "frontier_k": frontier_k,
                    "combos": combos,
                },
                timeout=budget_s,
            )
            cs = []
            for c in qm2.get("combos") or []:
                if "delta_ev" not in c:
                    cs.append(c)
                    continue
                lam = _lambda_from_delta(c["delta_ev"], ref)
                if lam is None:
                    cs.append(
                        {
                            "positions": c["positions"],
                            "delta_ev": c["delta_ev"],
                            "lambda_nm": None,
                            "delta_lambda_nm": None,
                            "reason": (
                                "la conversion pasa por un polo: la "
                                "combinacion cae fuera del regimen "
                                "donde el delta es interpretable"
                            ),
                        }
                    )
                    continue
                ingenua = sum(
                    r["delta_lambda_nm"] for r in rojos if r["position"] in c["positions"]
                )
                cs.append(
                    {
                        "positions": c["positions"],
                        "delta_ev": c["delta_ev"],
                        "lambda_nm": round(lam, 1),
                        "delta_lambda_nm": round(lam - ref, 1),
                        "naive_sum_nm": round(ingenua, 1),
                        "additivity_error_nm": round((lam - ref) - ingenua, 1),
                        "clears_gate": (lam - ref) >= 65.0,
                    }
                )
            out["combinations"] = cs
            ok = [c for c in cs if c.get("clears_gate")]
            out["gate_verdict"] = {
                "clears": bool(ok),
                "best_combo_nm": max(
                    (c["delta_lambda_nm"] for c in cs if "delta_lambda_nm" in c), default=None
                ),
                "statement": (
                    "alguna combinacion alcanza los +65 nm del gate"
                    if ok
                    else "ninguna combinacion evaluada alcanza los +65 nm"
                ),
            }
        except Exception as e:  # noqa: BLE001
            out["combinations"] = {
                "available": False,
                "reason": f"no se pudieron calcular: {str(e)[:130]}",
            }

    # ── PATA CUANTICA sobre el mismo fragmento y las mismas cargas ─────────
    if quantum:
        # El presupuesto de la pata cuantica sale del mismo `budget_s` de la
        # llamada, no de un valor fixed escondido en la firma: quien pide el
        # diferencial decide cuanto esta dispuesto a esperar por ella.
        q = _quantum_leg(
            chg["geom"],
            chg["coords"],
            chg["charges"],
            chg["charge"],
            cas_norb=2 * frontier_k,
            cas_nelec=2 * frontier_k,
            basis=basis,
            timeout=int(budget_s),
        )
        out["quantum"] = q
        if q.get("available"):
            r = q.get("result") or {}
            out["quantum_vs_classical"] = {
                "note": (
                    "el valor cuantico viaja junto al clasico sobre el MISMO "
                    "fragmento y el MISMO espacio activo. Si coinciden se dice "
                    "y NO se reclama ventaja: en un fragmento monorreferencial "
                    "reproducir al clasico es una comprobacion de correccion, "
                    "no una victoria"
                ),
                "levels": {k: v for k, v in r.items() if isinstance(v, (int, float, str))},
            }
    else:
        out["quantum"] = _as(_na("no se solicito la ruta cuantica en esta llamada", "quantum=True"))

    try:
        from quantum_arm import cost_snapshot

        out["quantum_cost"] = cost_snapshot()
    except Exception:  # noqa: BLE001
        pass

    out["wall_seconds"] = round(time.perf_counter() - t0, 1)
    return out


def _as(v: Any) -> Dict[str, Any]:
    return v.to_dict() if hasattr(v, "to_dict") else (v if isinstance(v, dict) else {})


# ---------------------------------------------------------------------------
# ESTADOS S1 Y T1 POR CIS
# ---------------------------------------------------------------------------
# MEDIDO 2026-08-31 sobre el cromoforo CRQ con su entorno de cargas:
#
#     S1 = 2.876 eV      T1 = 2.106 eV      gap S1-T1 = 0.770 eV
#
# El T1 es lo que decide si el cromoforo puede sensibilizar oxigeno singlete
# (umbral 0.98 eV). La ventana AVAS-pi devolvia 54 eV para T1, un valor absurdo
# documentado en T1_NOT_AVAILABLE_FROM_PI_WINDOW: esa ventana no contiene los
# orbitales del triplete mas bajo, y proyectar sobre S=1 devuelve el espin
# correcto de un espacio equivocado sin levantar ningun error.
#
# CIS con singlet=False si da el triplete, en el rango fisico, y por el mismo
# precio que el singlete. Con esto la etapa de mecanismo deja de salir
# `indeterminate` por falta de datos electronicos.
_ELECTRONIC_CIS = r"""
import sys, json, warnings, numpy as np; warnings.filterwarnings("ignore")
p = json.loads(sys.stdin.read())
from pyscf import gto, scf, tdscf
from pyscf.qmmm import mm_charge
coords = np.array(p["coords"]); q = np.array(p["charges"])
try:
    mol = gto.M(atom=p["geom"], basis=p.get("basis", "sto-3g"),
                charge=p["charge"], verbose=0)
    mf = mm_charge(scf.RHF(mol).density_fit(), coords, q); mf.kernel()
    ts = tdscf.TDA(mf); ts.singlet = True;  ts.nstates = 3; ts.verbose = 0; ts.kernel()
    H = 27.211386245988
    s1 = float(ts.e[0] * H)

    # T1 POR DeltaSCF CON DFT SIN RESTRICCION, no por TDA.
    # MEDIDO 2026-08-31 sobre la biliverdina, tres metodos y dos fracasos:
    #   TDA sobre RHF   T1 = +0.181 eV, gap S1-T1 de 2.08 eV -> imposible
    #   DeltaSCF UHF    T1 = -2.204 eV, <S^2> = 4.46         -> basura
    #   DeltaSCF UKS    T1 = +0.472 eV, <S^2> = 2.165        -> LIMPIO
    # La contaminacion de espin es lo que separa un numero utilizable de uno
    # que no lo es, y el DFT sin restriccion la sufre mucho menos que HF. El
    # <S^2> viaja en la salida: si se aleja de 2.0 el T1 no se usa.
    t1 = None
    s2 = None
    t1_metodo = "no disponible"
    try:
        from pyscf import dft
        mol_t = gto.M(atom=p["geom"], basis=p.get("basis", "sto-3g"),
                      charge=p["charge"], spin=2, verbose=0)
        mol_s = gto.M(atom=p["geom"], basis=p.get("basis", "sto-3g"),
                      charge=p["charge"], spin=0, verbose=0)
        xc = p.get("xc", "b3lyp")
        rks = mm_charge(dft.RKS(mol_s).density_fit(), coords, q); rks.xc = xc
        rks.kernel()
        uks = mm_charge(dft.UKS(mol_t).density_fit(), coords, q); uks.xc = xc
        uks.kernel()
        if rks.converged and uks.converged:
            s2 = float(uks.spin_square()[0])
            t1 = float((uks.e_tot - rks.e_tot) * H)
            t1_metodo = f"DeltaSCF UKS/{xc}"
    except Exception as _te:
        t1_metodo = f"DeltaSCF UKS fallo: {type(_te).__name__}"
    if t1 is None:
        tt = tdscf.TDA(mf); tt.singlet = False; tt.nstates = 3
        tt.verbose = 0; tt.kernel()
        t1 = float(tt.e[0] * H)
        t1_metodo = "TDA sobre RHF (respaldo; propenso a inestabilidad)"
    f = ts.oscillator_strength()
    ib = int(np.argmax(f))
    print(json.dumps({"ok": True, "s1_ev": s1, "t1_ev": t1,
                      "t1_method": t1_metodo, "t1_spin_squared": s2,
                      "singlet_triplet_gap_ev": s1 - t1,
                      "bright_state_ev": float(ts.e[ib] * H),
                      "oscillator_strength": float(f[ib]),
                      "method": "CIS/TDA sobre HF con incrustacion QM/MM"}))
except Exception as ex:
    print(json.dumps({"ok": False, "reason": f"{type(ex).__name__}: {str(ex)[:180]}"}))
"""


# Suelos de plausibilidad para el triplete. No son constantes fisicas: son el
# punto por debajo del cual el numero deja de poder interpretarse como un
# triplete y pasa a ser sintoma de un problema de metodo.
TRIPLET_INSTABILITY_FLOOR_EV = 0.30
TRIPLET_GAP_MAX_EV = 1.50
# Desviacion maxima de <S^2> respecto a 2.0 para aceptar un triplete de DeltaSCF.
# MEDIDO: UKS/B3LYP sobre biliverdina da 2.165 (aceptable, 8% de contaminacion);
# UHF sobre el mismo sistema da 4.46, que es casi un quintuplete.
SPIN_CONTAMINATION_MAX = 0.5


def electronic_cis(
    pdb_id=None, pdb_text=None, resname="CRQ", chain="A", basis="sto-3g", budget_s=1800
):
    """S1 y T1 del cromoforo en su entorno. Devuelve NotAvailable con razon."""
    try:
        chg = _run(
            _CHARGES,
            {
                "pdb_id": pdb_id,
                "pdb_text": pdb_text,
                "resname": resname,
                "chain": chain,
                "positions": [],
            },
            timeout=budget_s,
        )
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"no se pudieron obtener las cargas: {str(e)[:130]}"}
    if not chg.get("ok"):
        return {"available": False, "reason": chg.get("reason")}
    try:
        r = _run(
            _ELECTRONIC_CIS,
            {
                "geom": chg["geom"],
                "charge": chg["charge"],
                "coords": chg["coords"],
                "charges": chg["charges"],
                "basis": basis,
            },
            timeout=budget_s,
        )
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"{type(e).__name__}: {str(e)[:130]}"}
    if not r.get("ok"):
        return {"available": False, "reason": r.get("reason")}
    r["available"] = True
    r["qm_region_atoms"] = chg.get("n_atoms")
    r["n_point_charges"] = len(chg.get("charges") or [])
    r["singlet_oxygen_threshold_ev"] = 0.98

    # INESTABILIDAD DE TRIPLETE. Un T1 que colapsa hacia cero NO es un triplete
    # de baja energia: es la firma de que la referencia RHF es inestable frente
    # a la rotura de simetria de espin, cosa habitual en sistemas pi extendidos.
    # MEDIDO 2026-08-31: el cromoforo CRQ dio T1 = 2.106 eV (sano, gap S1-T1 de
    # 0.770 eV) y la biliverdina T1 = 0.101 eV con S1 = 2.242, es decir un gap
    # de 2.14 eV. Un gap singlete-triplete asi de grande en un sistema pi
    # conjugado no es fisico.
    #
    # Esto importa porque de T1 depende la conclusion "sensibiliza oxigeno
    # singlete o no", y afirmar que NO lo hace a partir de un artefacto seria
    # descartar un andamiaje por un fallo de metodo.
    # CONTAMINACION DE ESPIN. MEDIDO 2026-08-31 sobre la biliverdina: el
    # DeltaSCF con UHF dio T1 = -2.204 eV, un triplete POR DEBAJO del singlete
    # fundamental, con <S^2> = 4.46 cuando un triplete puro vale 2.0. Ese
    # numero no es un triplete de baja energia: es la senal de que la
    # referencia de capa cerrada no es el estado fundamental y todo lo
    # construido sobre ella (S1 incluido) deja de ser fiable.
    #
    # Un T1 negativo NUNCA se puede leer como "no sensibiliza": significa que
    # el tratamiento monorreferencial se ha desmoronado.
    t1 = float(r["t1_ev"])
    s1 = float(r["s1_ev"])
    gap = s1 - t1
    s2 = r.get("t1_spin_squared")
    if s2 is not None:
        # Con DeltaSCF el criterio bueno es <S^2>, no el gap: mide DIRECTAMENTE
        # si el estado calculado es un triplete o una mezcla sin sentido.
        sospechoso = abs(float(s2) - 2.0) > SPIN_CONTAMINATION_MAX
        r["t1_spin_check"] = {
            "spin_squared": round(float(s2), 4),
            "pure_triplet": 2.0,
            "tolerance": SPIN_CONTAMINATION_MAX,
            "clean": not sospechoso,
            "why": (
                "<S^2> mide si el estado es de verdad un triplete. Lejos "
                "de 2.0 no es un triplete de baja energia: es una mezcla "
                "que no describe nada"
            ),
        }
    else:
        sospechoso = (t1 < TRIPLET_INSTABILITY_FLOOR_EV) or (gap > TRIPLET_GAP_MAX_EV)
    if t1 < 0:
        sospechoso = True
        r["negative_triplet"] = True
        r["negative_triplet_note"] = (
            "T1 NEGATIVO: el triplete sale por debajo del singlete de "
            "referencia. Eso no significa que no sensibilice, significa que la "
            "referencia de capa cerrada NO es el estado fundamental. Hace falta "
            "un tratamiento multirreferencial"
        )
    r["triplet_instability_suspected"] = bool(sospechoso)
    if sospechoso:
        r["can_sensitize_singlet_oxygen"] = None
        r["t1_reliable"] = False
        r["t1_warning"] = (
            f"T1 = {t1:.3f} eV con un gap S1-T1 de {gap:.3f} eV. Un triplete "
            f"por debajo de {TRIPLET_INSTABILITY_FLOOR_EV} eV, o un gap por "
            f"encima de {TRIPLET_GAP_MAX_EV} eV en un sistema pi conjugado, "
            f"apunta a INESTABILIDAD DE TRIPLETE de la referencia RHF, no a un "
            f"triplete real de baja energia. NO se concluye si sensibiliza o no"
        )
        r["what_would_settle_it"] = (
            "una referencia sin restriccion de espin (UHF/UKS) y comprobar la "
            "estabilidad, o un metodo multirreferencia sobre un espacio activo "
            "que SI contenga los orbitales del triplete"
        )
    else:
        r["can_sensitize_singlet_oxygen"] = t1 >= 0.98
        r["t1_reliable"] = True
    r["singlet_triplet_gap_ev"] = gap
    r["caveat"] = (
        "CIS sobreestima las energias de excitacion; el T1 sirve "
        "para decidir si SUPERA el umbral de 0.98 eV, no como valor "
        "espectroscopico"
    )
    return r


def register_nir_method_routes(app):
    """Expone lo MEDIDO sobre el propio metodo, para que sea auditable.

    Sin esto, la convergencia de base, la eleccion de metodo y el regimen de
    validez existen only dentro del modulo: quien lee una tarjeta tiene que
    creerse el numero en vez de poder comprobar de donde sale.
    """
    from flask import jsonify, request

    @app.route("/api/nir/method", methods=["GET"])
    def _nir_method():
        return jsonify(
            {
                "available": True,
                "differential_method": DIFFERENTIAL_METHOD,
                "method_evidence": DIFFERENTIAL_METHOD_EVIDENCE,
                "basis_convergence": BASIS_CONVERGENCE,
                "perturbation_regime": PERTURBATION_REGIME,
                "cancellation_evidence": CANCELLATION_EVIDENCE,
                "casci_warning": CASCI_ASYMMETRY_WARNING,
                "cross_method_validation": CROSS_METHOD_VALIDATION,
            }
        )

    @app.route("/api/nir/regime", methods=["GET", "POST"])
    def _nir_regime():
        """Dice si una perturbacion cae dentro del regimen valido."""
        p = request.get_json(force=True, silent=True) or {}
        q = p.get("charge", request.args.get("charge", 1.0))
        try:
            return jsonify(
                {"available": True, "charge": float(q), **perturbation_in_regime(float(q))}
            )
        except (TypeError, ValueError):
            return jsonify({"available": False, "reason": f"carga no numerica: {q!r}"})

    print("[NIR] Metodo y regimen expuestos (/api/nir/method, /api/nir/regime)")
