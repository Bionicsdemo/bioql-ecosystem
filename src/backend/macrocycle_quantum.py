"""
Dónde el cuántico decide algo en un macrociclo, y dónde sería decoración.

Este repo ya pagó una vez el precio del quantum-washing (19 fabricaciones
corregidas), así que este módulo está escrito al revés de lo habitual: lo primero
que hace es decir que NO hace falta. `triage()` devuelve `classical_suffices`
salvo que encuentre una razón concreta, y el pipeline gasta GPU cuántica solo
sobre lo que pasó ese filtro.

LAS CUATRO PLAZAS DONDE SÍ DECIDE
---------------------------------
Q1  Ranking energético de confórmeros. Lo que hace funcionar a un macrociclo es
    su población de confórmeros: la red de puentes de hidrógeno intramoleculares
    (que gobierna la permeabilidad), el equilibrio cis/trans de las amidas
    N-metiladas y la tensión transanular. MMFF94s es malo en las tres.
Q2  Barrera cis/trans de amida N-metilada: el estado de transición tiene carácter
    multireferencial, y la N-metilación es la herramienta principal de
    permeabilidad en esta química.
Q3  Ciclación por disulfuro o tioéter: el TS de ruptura S–S es multireferencial.
    El propio `quantum_reactivity_gate` ya lo declara así.
Q4  Selección de subconjunto diverso por QUBO/QAOA. Combinatorio, NO ventaja
    cuántica: a estos tamaños un solver clásico empata o gana, y se etiqueta.

DONDE NO SE USA, A PROPÓSITO
----------------------------
Scores de docking (empíricos), descriptores TPSA/cLogP/PAINS, generación de
secuencia, detección de bolsillo, filtros bRo5. Meter cuántico ahí es teatro.

SOLO DIFERENCIAS, NUNCA ENERGÍAS ABSOLUTAS
------------------------------------------
Está medido en este mismo repo, en el programa NIR: el error absoluto fue de
1,348 eV contra una puerta de 0,059 eV -- 23 veces demasiado grande para servir
de nada. El mismo protocolo, aplicado a la DIFERENCIA entre sistemas
emparentados, bajó a 0,08 eV; factor de cancelación 16,8. El ranking de
confórmeros es el régimen diferencial ideal, porque compara conformaciones de la
MISMA molécula: mismos átomos, mismo espacio activo, solo cambia la geometría.

Por eso `rank_conformers()` emite diferencias contra un confórmero de referencia
y `_forbid_absolute()` impide que una energía absoluta salga de aquí por
descuido. Un número absoluto de este módulo sería, con los datos que tenemos,
una cifra sin validez conocida.

MOLEVERA / BIOQL
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

HARTREE_EV = 27.211386245988
KCAL_PER_HARTREE = 627.5094740631

# Umbral por debajo del cual la diferencia calculada no se distingue del error del
# método. Es el diferencial medido en NIR, no una cifra elegida por comodidad.
DIFFERENTIAL_FLOOR_EV = 0.08


def _optional(nombre: str) -> Any:
    """Carga una dependencia opcional del backend por nombre.

    xtb, Modal y el gate de reactividad pueden no estar: sin ellos este módulo
    tiene que seguir siendo importable y decir por qué degrada, no reventar al
    importarse. Cargarlas por nombre además evita arrastrar medio `src/backend`
    -- 622 ficheros que no están bajo control de versiones y traen su propia
    deuda de tipos -- a la comprobación estática de este fichero.
    """
    import importlib

    return importlib.import_module(nombre)


# ── triaje: la pregunta es "¿hace falta?", no "¿cómo lo metemos?" ─────────────
@dataclass
class QuantumNeed:
    """Por qué un candidato se gana (o no) el cuántico, con la razón escrita."""

    applies: bool
    reasons: List[str] = field(default_factory=list)
    places: List[str] = field(default_factory=list)  # Q1..Q4
    gate: Optional[Dict[str, Any]] = None
    verdict: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applies": self.applies,
            "reasons": self.reasons,
            "places": self.places,
            "gate": self.gate,
            "verdict": self.verdict,
        }


def _has_n_methyl_amide(smiles: str) -> bool:
    """N-metilamida en el esqueleto: el motivo de Q2."""
    try:
        from rdkit import Chem

        m = Chem.MolFromSmiles(smiles or "")
        if m is None:
            return False
        patt = Chem.MolFromSmarts("[NX3;H0]([CH3])[CX3](=O)")
        return bool(m.HasSubstructMatch(patt))
    except Exception:
        return False


def triage(spec: Dict[str, Any], *, run_gate: bool = True) -> QuantumNeed:
    """¿Este macrociclo necesita cuántico, y para qué exactamente?

    `spec` es lo que devuelve `macrocycle_builder.MacrocycleSpec.to_dict()`.

    Devuelve `applies=False` por defecto. Cada motivo que lo activa queda
    escrito, para que el informe pueda decir por qué se gastó GPU cuántica en
    este candidato y no en el de al lado.
    """
    smiles = str(spec.get("smiles") or "")
    cyc = str(spec.get("cyclization") or "")
    need = QuantumNeed(applies=False)

    # Q3 — la ciclación misma es química de correlación fuerte
    if cyc in ("disulfide", "thioether"):
        need.places.append("Q3")
        need.reasons.append(
            f"la ciclación es {cyc}: el estado de transición de formación/ruptura "
            f"S–S es multireferencial, no un régimen de referencia única"
        )

    # Q2 — amida N-metilada: el equilibrio cis/trans decide la conformación
    if _has_n_methyl_amide(smiles):
        need.places.append("Q2")
        need.reasons.append(
            "hay amida N-metilada: su barrera cis/trans gobierna qué confórmero "
            "domina, y el TS tiene carácter multireferencial"
        )

    # Q1 — el ranking de confórmeros aplica a todo macrociclo, pero solo se gasta
    # en los que llegan al final del embudo; aquí se declara la elegibilidad.
    if spec.get("ring_size"):
        need.places.append("Q1")
        need.reasons.append(
            "es un macrociclo cerrado: el ranking de confórmeros es diferencial "
            "sobre la misma molécula, que es donde el error se cancela"
        )

    # El gate del repo tiene la última palabra sobre la química reactiva.
    if run_gate and smiles:
        try:
            import quantum_reactivity_gate as qrg

            need.gate = qrg.assess_reactive_chemistry(smiles, modality="peptide", run_quantum=False)
        except Exception as e:  # noqa: BLE001 — el gate no puede tumbar el triaje
            need.gate = {"available": False, "reason": f"{type(e).__name__}: {e}"}

    need.applies = bool(need.places)
    if not need.applies:
        need.verdict = (
            "classical_suffices — no se detectó ni ciclación por azufre, ni amida "
            "N-metilada, ni un macrociclo cerrado sobre el que rankear. Gastar "
            "cuántico aquí no cambiaría ninguna decisión."
        )
    else:
        need.verdict = f"cuántico aplicable en {'+'.join(need.places)}: " + "; ".join(need.reasons)
    return need


# ── el contrato diferencial ──────────────────────────────────────────────────
class AbsoluteEnergyRefused(RuntimeError):
    """Se intentó sacar de aquí una energía absoluta."""


def _forbid_absolute(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Impide que una energía absoluta salga de este módulo.

    No es celo: con el protocolo que tenemos, el error absoluto medido fue de
    1,348 eV. Publicar un número así como si significara algo es precisamente la
    fabricación que este repo ya tuvo que corregir una vez.
    """
    for clave in list(payload):
        if clave.endswith("_absolute") or clave in ("e_tot", "energy_hartree", "e_abs"):
            raise AbsoluteEnergyRefused(
                f"{clave!r}: este módulo solo emite diferencias. El error absoluto "
                f"medido del protocolo es 1,348 eV frente a 0,08 eV en diferencial."
            )
    return payload


@dataclass
class ConformerEnergy:
    conformer_id: int
    delta_ev: Optional[float]
    method: str
    reference_id: int
    below_floor: bool = False
    note: str = ""


def rank_conformers(
    conformer_xyz: List[str],
    *,
    charge: int = 0,
    method: str = "xtb",
    reference: int = 0,
    timeout_s: int = 120,
) -> Dict[str, Any]:
    """Ordena confórmeros por energía RELATIVA al de referencia.

    `method="xtb"` es el peldaño clásico y está instalado y verificado
    (GFN2-xTB 6.7.1). El peldaño cuántico entra por `method="sqd"` a través de
    `modal_compute_layer`, y si no está disponible se DEGRADA a xtb diciéndolo,
    nunca en silencio.

    Toda diferencia por debajo de `DIFFERENTIAL_FLOOR_EV` se marca
    `below_floor=True`: es indistinguible del error del método y el orden entre
    esos confórmeros no significa nada.
    """
    t0 = time.perf_counter()
    out: Dict[str, Any] = {
        "method_requested": method,
        "method_used": None,
        "reference_conformer": reference,
        "unit": "eV (diferencia contra el confórmero de referencia)",
        "differential_floor_ev": DIFFERENTIAL_FLOOR_EV,
        "energies": [],
        "degradations": [],
        "absolute_energies_emitted": False,
    }
    if not conformer_xyz:
        out["error"] = "no se recibió ningún confórmero"
        return out

    usar = method
    if method == "sqd":
        ok, por_que = _quantum_available()
        if not ok:
            out["degradations"].append(
                f"se pidió SQD y se usó xtb: {por_que}. El orden sigue siendo "
                f"diferencial, pero con el peldaño clásico."
            )
            usar = "xtb"

    if usar == "xtb":
        crudas, err = _xtb_energies(conformer_xyz, charge=charge, timeout_s=timeout_s)
    else:
        crudas, err = _sqd_energies(conformer_xyz, charge=charge, timeout_s=timeout_s)
    if err:
        out["error"] = err
        return out

    out["method_used"] = usar
    ref = crudas[reference]
    if ref is None:
        out["error"] = f"el confórmero de referencia {reference} no dio energía"
        return out

    for i, e in enumerate(crudas):
        if e is None:
            out["energies"].append(
                ConformerEnergy(
                    i, None, usar, reference, note="no convergió; se declara, no se rellena"
                ).__dict__
            )
            continue
        d_ev = (e - ref) * HARTREE_EV
        out["energies"].append(
            ConformerEnergy(
                conformer_id=i,
                delta_ev=round(d_ev, 4),
                method=usar,
                reference_id=reference,
                below_floor=abs(d_ev) < DIFFERENTIAL_FLOOR_EV,
                note=(
                    "por debajo del suelo diferencial: el orden frente a la "
                    "referencia no es significativo"
                    if abs(d_ev) < DIFFERENTIAL_FLOOR_EV
                    else ""
                ),
            ).__dict__
        )

    n_sig = sum(1 for e in out["energies"] if e["delta_ev"] is not None and not e["below_floor"])
    out["n_significant"] = n_sig
    out["n_total"] = len(conformer_xyz)
    out["honest_note"] = (
        f"{n_sig} de {len(conformer_xyz)} confórmeros se separan del de referencia "
        f"por encima de {DIFFERENTIAL_FLOOR_EV} eV. El resto está dentro del error "
        f"del método y su orden relativo no debe leerse como un ranking."
    )
    out["wall_seconds"] = round(time.perf_counter() - t0, 3)
    return _forbid_absolute(out)


def _xtb_energies(xyzs: List[str], *, charge: int, timeout_s: int):
    """Peldaño clásico: GFN2-xTB. Devuelve (energías en Hartree, error)."""
    try:
        xtb_engine = _optional("xtb_engine")
    except Exception as e:  # noqa: BLE001
        return [], f"xtb_engine no importable: {type(e).__name__}: {e}"
    caps = xtb_engine.capabilities()
    if not caps.get("ready"):
        return [], f"xtb no está listo: falta {caps.get('missing')}"
    energias: List[Optional[float]] = []
    for xyz in xyzs:
        try:
            r = xtb_engine.compute_single_point_energy(xyz, charge=charge, timeout_s=timeout_s)
            energia = r.get("energy_hartree") if isinstance(r, dict) else None
            energias.append(float(energia) if energia is not None else None)
        except Exception:  # noqa: BLE001 — un confórmero que falla no tumba el lote
            energias.append(None)
    return energias, None


def _quantum_available() -> Tuple[bool, str]:
    """¿Está viva la ruta cuántica en GPU?"""
    try:
        mcl = _optional("modal_compute_layer")
        st = mcl.app_status() if hasattr(mcl, "app_status") else {}
        apps = st.get("apps") or {}
        q = apps.get("quantum_gpu") or {}
        if q.get("deployed"):
            return True, ""
        return False, f"quantum_gpu no desplegada: {q.get('reason', 'sin razón declarada')}"
    except Exception as e:  # noqa: BLE001
        return False, f"modal_compute_layer no disponible: {type(e).__name__}: {e}"


def _sqd_energies(xyzs: List[str], *, charge: int, timeout_s: int):
    """Peldaño cuántico. No se implementa un sustituto clásico disfrazado: si la
    ruta no está, el llamante ya degradó a xtb y lo dijo."""
    try:
        mcl = _optional("modal_compute_layer")
    except Exception as e:  # noqa: BLE001
        return [], f"modal_compute_layer no importable: {type(e).__name__}: {e}"
    energias: List[Optional[float]] = []
    for xyz in xyzs:
        try:
            r = mcl.run("quantum_gpu", {"xyz": xyz, "charge": charge}, timeout=timeout_s)
            energia = (r or {}).get("energy_hartree")
            energias.append(float(energia) if energia is not None else None)
        except Exception:  # noqa: BLE001
            energias.append(None)
    return energias, None


# ── presupuesto 60/40, medido y no decorado ──────────────────────────────────
@dataclass
class ComputeBudget:
    """Reparto GPU / cuántico: planeado frente a conseguido.

    El objetivo es una política, no un adorno. Si para una petición concreta el
    cuántico no llega a su parte porque ningún candidato pasó el triaje, esto lo
    dice en vez de inventar cálculos para cuadrar el número. Un 40% alcanzado
    metiendo SQD donde no hace falta es exactamente el fallo que ya costó caro.
    """

    target_gpu: float = 0.60
    target_quantum: float = 0.40
    gpu_seconds: float = 0.0
    quantum_seconds: float = 0.0
    skipped_by_triage: int = 0
    sent_to_quantum: int = 0

    def add_gpu(self, seconds: float) -> None:
        self.gpu_seconds += max(0.0, float(seconds))

    def add_quantum(self, seconds: float) -> None:
        self.quantum_seconds += max(0.0, float(seconds))

    def report(self) -> Dict[str, Any]:
        total = self.gpu_seconds + self.quantum_seconds
        if total <= 0:
            return {
                "planned": {"gpu": self.target_gpu, "quantum": self.target_quantum},
                "achieved": None,
                "note": "no se gastó cómputo medible en esta corrida",
            }
        got_q = self.quantum_seconds / total
        desvio = got_q - self.target_quantum
        r = {
            "planned": {"gpu": self.target_gpu, "quantum": self.target_quantum},
            "achieved": {
                "gpu": round(self.gpu_seconds / total, 3),
                "quantum": round(got_q, 3),
            },
            "seconds": {
                "gpu": round(self.gpu_seconds, 1),
                "quantum": round(self.quantum_seconds, 1),
            },
            "candidates_skipped_by_triage": self.skipped_by_triage,
            "candidates_sent_to_quantum": self.sent_to_quantum,
            "deviation_from_target": round(desvio, 3),
        }
        if abs(desvio) < 0.10:
            r["note"] = "el reparto conseguido está dentro de lo planeado"
        elif desvio < 0:
            # Quedarse corto tiene DOS causas distintas y confundirlas era el
            # propio informe mintiendo: que el triaje descartara a los candidatos,
            # o que los eligiera y el cómputo cuántico no llegara a correr.
            if self.quantum_seconds <= 0 and self.sent_to_quantum > 0:
                r["note"] = (
                    f"el triaje declaró {self.sent_to_quantum} candidatos elegibles para "
                    f"cuántico y NO se ejecutó ninguno: no se gastó un solo segundo. El "
                    f"0% no es que no hiciera falta, es que está pendiente."
                )
                r["quantum_eligible_but_not_run"] = self.sent_to_quantum
            else:
                r["note"] = (
                    f"el cuántico se quedó en {got_q:.0%} frente al {self.target_quantum:.0%} "
                    f"planeado, porque {self.skipped_by_triage} de "
                    f"{self.skipped_by_triage + self.sent_to_quantum} candidatos no pasaron "
                    f"el triaje. Se declara en vez de rellenarlo con cálculos que no "
                    f"cambiarían ninguna decisión."
                )
        else:
            r["note"] = (
                f"el cuántico llegó al {got_q:.0%}, por encima del {self.target_quantum:.0%} "
                f"planeado: {self.sent_to_quantum} candidatos pasaron el triaje."
            )
        return r


# MOLEVERA / BIOQL
