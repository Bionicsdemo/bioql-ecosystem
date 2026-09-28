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

    razones: List[str] = []
    if usar == "xtb":
        crudas, err = _xtb_energies(conformer_xyz, charge=charge, timeout_s=timeout_s)
    else:
        crudas, err, razones = _sqd_energies(conformer_xyz, charge=charge, timeout_s=timeout_s)
    if err:
        out["error"] = err
        return out

    out["method_used"] = usar
    ref = crudas[reference]
    if ref is None:
        por_que = (razones[reference] if reference < len(razones) else "") or "sin causa registrada"
        out["error"] = (
            f"el confórmero de referencia {reference} no dio energía ({por_que}); "
            f"sin referencia no hay diferencial que publicar"
        )
        out["failure_reasons"] = [r for r in razones if r]
        return out

    for i, e in enumerate(crudas):
        if e is None:
            detalle = (razones[i] if i < len(razones) else "") or "no convergió"
            out["energies"].append(
                ConformerEnergy(
                    i,
                    None,
                    usar,
                    reference,
                    note=f"{detalle}; se declara, no se rellena",
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


def _sqd_energies(xyzs: List[str], *, charge: int, timeout_s: int, n_act_orb: int = 6):
    """Peldaño cuántico real: pyscf sobre la geometría -> SQD por la cascada.

    La primera versión de esto llamaba a `quantum_gpu` con `{"xyz", "charge"}`, y
    esa función es `cudaq_statevector(qasm_or_spec, shots)`: toma un CIRCUITO, no
    una molécula. Habría devuelto error en cada confórmero y el llamante habría
    degradado a xtb creyendo que la ruta cuántica estaba caída.

    El camino verdadero es el que ya usa el resto del repo: campo medio con pyscf
    y `sqd_cascade.run(mf, n_act_orb=...)`, que elige peldaño (CPU -> CUDA-Q ->
    QPU) y NUNCA sube solo: `allow_qpu` y `allow_cudaq` son False por defecto
    porque los dos gastan presupuesto real.

    No se implementa ningún sustituto clásico disfrazado: si la cascada no da
    valor, ese confórmero sale como None y el llamante lo declara.
    """
    try:
        pyscf_gto = _optional("pyscf.gto")
        pyscf_scf = _optional("pyscf.scf")
        cascade = _optional("sqd_cascade")
    except Exception as e:  # noqa: BLE001
        return [], f"la ruta SQD no está disponible: {type(e).__name__}: {e}"

    energias: List[Optional[float]] = []
    razones: List[str] = []
    for xyz in xyzs:
        try:
            cuerpo = "\n".join(xyz.strip().splitlines()[2:])  # quita cabecera XYZ
            mol = pyscf_gto.M(atom=cuerpo, basis="sto-3g", charge=charge, spin=0, verbose=0)
            mf = pyscf_scf.RHF(mol).run()
            r = cascade.run(mf, n_act_orb=n_act_orb, allow_qpu=False, allow_cudaq=False)
            energia = (r or {}).get("e_sqd")
            energias.append(float(energia) if energia is not None else None)
            razones.append("" if energia is not None else "la cascada SQD no devolvió e_sqd")
        except Exception as e:  # noqa: BLE001 — un confórmero que falla no tumba el lote
            # Se ANOTA por qué. Tragarse esto es lo que hizo que dos candidatos
            # salieran con "0 de 0 significativos" y ninguna explicación: la
            # región tenía un número impar de electrones y pyscf la rechazaba.
            energias.append(None)
            razones.append(f"{type(e).__name__}: {str(e).splitlines()[0][:160]}")
    return energias, None, razones


# ── QM/MM: el cuántico solo donde decide, lo demás clásico ───────────────────
# Anclas por orden de prioridad. Cada una es una razón distinta para gastar
# cuántico, y todas están declaradas en el gate de reactividad del repo.
_ANCLAS = (
    (
        "S-S",
        "[SX2][SX2]",
        "enlace disulfuro: el TS de ruptura S–S es multireferencial",
        "disulfide bond: the S–S cleavage TS is multireferential",
    ),
    (
        "C-S",
        "[CX4][SX2][CX4]",
        "puente tioéter: el enlace C–S del cierre",
        "thioether bridge: the C–S bond of the closure",
    ),
    (
        "N-Me amida",
        "[NX3;H0]([CH3])[CX3]=O",
        "amida N-metilada: su equilibrio cis/trans decide qué confórmero domina",
        "N-methylated amide: its cis/trans equilibrium decides which conformer dominates",
    ),
    (
        "amida",
        "[NX3][CX3]=O",
        "amida del esqueleto: en un cierre head-to-tail la nueva es químicamente "
        "idéntica a las demás, así que se toma la primera y se dice",
        "backbone amide: in a head-to-tail closure the new one is chemically identical "
        "to the rest, so the first is taken and that is stated",
    ),
)

# Longitud del enlace C–H con que se capa un enlace cortado.
_CAP_CH = 1.09

# Cuántas rondas de absorción se permiten antes de rendirse y decirlo.
_MAX_REPARACIONES = 6


def _cortable(mol, dentro: int, fuera: int) -> bool:
    """¿Se puede cortar este enlace de frontera y capar con un hidrógeno?

    Solo si es C-C, de orden uno y no aromático. Es la condición que hace que un
    único H restituya la valencia sin cambiar la química de lo que queda dentro.
    """
    b = mol.GetBondBetweenAtoms(int(dentro), int(fuera))
    if b is None or b.GetIsAromatic() or b.GetBondTypeAsDouble() != 1.0:
        return False
    return bool(
        mol.GetAtomWithIdx(int(dentro)).GetAtomicNum() == 6
        and mol.GetAtomWithIdx(int(fuera)).GetAtomicNum() == 6
    )


def closure_region(smiles: str, molblocks: List[str], radius: int = 2) -> Dict[str, Any]:
    """Recorta la región que de verdad decide, y deja el resto a la GPU.

    Correr SQD sobre el macrociclo entero gasta el cálculo en átomos que no
    deciden nada: en un candidato de 8 residuos son 64 átomos pesados, y la
    región que importa son 9. Lo que cambia entre confórmeros y gobierna el
    plegamiento está concentrado en el enlace de cierre y en las amidas
    N-metiladas; el resto es andamiaje que el campo de fuerzas describe bien.

    Dos condiciones para que la diferencia signifique algo:

    1. El conjunto de átomos es EL MISMO en todos los confórmeros. Solo cambia la
       geometría, que es el régimen donde el error se cancela -- el mismo que
       midió NIR: 1,348 eV de error absoluto frente a 0,08 eV en diferencial.
    2. Los enlaces cortados se capan con hidrógeno a lo largo del enlace
       original. Un corte sin capar deja radicales y el número no significa nada.

    Devuelve las geometrías recortadas y DECLARA qué se cortó, porque una región
    es una aproximación y el lector tiene que poder discutirla.
    """
    try:
        from rdkit import Chem
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"rdkit no disponible: {e}"}
    if not molblocks:
        return {"available": False, "reason": "no se recibió ninguna conformación"}

    plano = Chem.MolFromSmiles(smiles or "")
    if plano is None:
        return {"available": False, "reason": "el SMILES no es una molécula válida"}

    ancla_nombre = ancla_por_que = ancla_why_en = ""
    match: Tuple[int, ...] = ()
    for nombre, smarts, por_que, why_en in _ANCLAS:
        patt = Chem.MolFromSmarts(smarts)
        hits = plano.GetSubstructMatches(patt) if patt else ()
        if hits:
            ancla_nombre, ancla_por_que, ancla_why_en, match = nombre, por_que, why_en, hits[0]
            break
    if not match:
        return {
            "available": False,
            "reason": "no se encontró ni disulfuro, ni tioéter, ni amida donde anclar",
        }

    # crecimiento por enlaces desde el ancla
    nucleo = set(match)
    for _ in range(max(0, int(radius))):
        nucleo |= {n.GetIdx() for i in list(nucleo) for n in plano.GetAtomWithIdx(i).GetNeighbors()}

    # Reparación de la frontera. Crecer por radio y cortar lo que cruce es
    # ingenuo: la primera versión de esto cortaba un C=O y dos amidas, y capar un
    # doble enlace con UN hidrógeno deja un radical -- la región salía con 63
    # electrones, pyscf la rechazaba por paridad y el confórmero se perdía sin
    # que nadie dijera por qué.
    #
    # La regla del átomo-enlace en QM/MM es que solo se corta un enlace C-C
    # SIMPLE y no aromático: apolar, de orden uno, y capable con un hidrógeno sin
    # cambiar la química de lo que queda dentro. Cualquier otro enlace de
    # frontera (doble, aromático, o a heteroátomo) se resuelve absorbiendo el
    # átomo de fuera, nunca cortándolo.
    absorbidos = 0
    for _ in range(_MAX_REPARACIONES):
        pendientes = {
            nb.GetIdx()
            for i in nucleo
            for nb in plano.GetAtomWithIdx(i).GetNeighbors()
            if nb.GetIdx() not in nucleo and not _cortable(plano, i, nb.GetIdx())
        }
        if not pendientes:
            break
        nucleo |= pendientes
        absorbidos += len(pendientes)
    else:
        return {
            "available": False,
            "reason": (
                "la frontera de la región no se estabilizó: quedaban "
                "enlaces que no son C-C simples y cortarlos daría "
                "una región con la química cambiada"
            ),
        }
    nucleo_ord = sorted(nucleo)

    # enlaces que cruzan la frontera: a estas alturas todos son C-C simples, y
    # cada uno se capa con un H sobre la dirección del enlace original
    cortes = []
    for i in nucleo_ord:
        for nb in plano.GetAtomWithIdx(i).GetNeighbors():
            if nb.GetIdx() not in nucleo:
                cortes.append((i, nb.GetIdx()))

    # Carga formal de la REGIÓN, que no tiene por qué ser la de la molécula: un
    # recorte que atrapa media cadena de lisina se lleva su carga con él.
    carga_region = sum(plano.GetAtomWithIdx(i).GetFormalCharge() for i in nucleo_ord)

    # Las geometrías llevan los átomos pesados de la región, SUS HIDRÓGENOS y las
    # capas. Los hidrógenos no son decorado: la primera versión escribía solo
    # pesados más capas, y eso no es la región -- es un fragmento deshidrogenado
    # con la capa electrónica abierta. Salía impar, pyscf lo rechazaba, y el
    # único candidato que "funcionó" había calculado esa otra cosa.
    geometrias: List[str] = []
    n_electrones = None
    for mbk in molblocks:
        m3d = Chem.MolFromMolBlock(mbk, removeHs=False)
        if m3d is None:
            continue
        # RemoveHs conserva el orden relativo de lo que queda, así que el k-ésimo
        # pesado de m3d es el átomo k del SMILES plano.
        pesados = [a.GetIdx() for a in m3d.GetAtoms() if a.GetAtomicNum() > 1]
        if len(pesados) != plano.GetNumAtoms():
            return {
                "available": False,
                "reason": (
                    "la conformación no casa átomo a átomo con el SMILES; "
                    "sin esa correspondencia el recorte sería de otra molécula"
                ),
            }
        conf = m3d.GetConformer()
        incluidos: List[int] = []
        for i in nucleo_ord:
            j = pesados[i]
            incluidos.append(j)
            incluidos += [
                n.GetIdx() for n in m3d.GetAtomWithIdx(j).GetNeighbors() if n.GetAtomicNum() == 1
            ]
        lineas = []
        carga_nuclear = 0
        for j in incluidos:
            pos = conf.GetAtomPosition(j)
            at = m3d.GetAtomWithIdx(j)
            carga_nuclear += at.GetAtomicNum()
            lineas.append(f"{at.GetSymbol()} {pos.x:.5f} {pos.y:.5f} {pos.z:.5f}")
        for dentro, fuera in cortes:
            a, b = conf.GetAtomPosition(pesados[dentro]), conf.GetAtomPosition(pesados[fuera])
            vx, vy, vz = b.x - a.x, b.y - a.y, b.z - a.z
            d = (vx * vx + vy * vy + vz * vz) ** 0.5 or 1.0
            f = _CAP_CH / d
            carga_nuclear += 1
            lineas.append(f"H {a.x + vx * f:.5f} {a.y + vy * f:.5f} {a.z + vz * f:.5f}")
        n_electrones = carga_nuclear - carga_region
        geometrias.append(f"{len(lineas)}\nregión de cierre\n" + "\n".join(lineas))

    # Paridad, contada sobre la geometría que de verdad se emite y no sobre una
    # fórmula que puede desviarse de ella.
    if n_electrones is not None and n_electrones % 2:
        return {
            "available": False,
            "reason": (
                f"la región saldría con {n_electrones} electrones, impar: "
                f"es una capa abierta y RHF no la describe. Se declara en "
                f"vez de forzar un espín que nadie ha medido"
            ),
        }

    return {
        "available": bool(geometrias),
        "anchor": ancla_nombre,
        "why": ancla_por_que,
        "why_en": ancla_why_en,
        "n_heavy_region": len(nucleo_ord),
        "n_heavy_molecule": plano.GetNumHeavyAtoms(),
        "n_caps": len(cortes),
        "charge": carga_region,
        "n_electrons": n_electrones,
        "n_absorbed_to_repair_boundary": absorbidos,
        "radius_bonds": int(radius),
        "atom_indices": nucleo_ord,
        "geometries": geometrias,
        "caveat": (
            "una región QM es una aproximación declarada: los enlaces cortados se "
            "capan con hidrógeno y el entorno queda fuera. Vale para COMPARAR "
            "confórmeros de la misma molécula, que es para lo que se usa, no para "
            "dar una energía de la molécula entera"
        ),
        "caveat_en": (
            "a QM region is a declared approximation: severed bonds are capped with "
            "hydrogen and the surroundings are left out. It is good for COMPARING "
            "conformers of the same molecule, which is what it is used for, not for "
            "giving an energy of the whole molecule"
        ),
    }


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

    def quantum_seconds_remaining_for_target(self) -> float:
        """Segundos de cuántico que faltan para que el reparto alcance su objetivo.

        Sirve para decidir CUÁNTOS confórmeros mandar al peldaño cuántico, no
        para inflar el número: cada segundo que esto autoriza compra un
        confórmero más ordenado a nivel QM. Si ya se pasó, devuelve 0.
        """
        if self.target_quantum <= 0:
            return 0.0
        objetivo = self.gpu_seconds * (self.target_quantum / max(self.target_gpu, 1e-9))
        return max(0.0, objetivo - self.quantum_seconds)

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
            r["note_es"] = "el reparto conseguido está dentro de lo planeado"
            r["note_en"] = "the achieved split is within what was planned"
        elif desvio < 0:
            # Quedarse corto tiene DOS causas distintas y confundirlas era el
            # propio informe mintiendo: que el triaje descartara a los candidatos,
            # o que los eligiera y el cómputo cuántico no llegara a correr.
            if self.quantum_seconds <= 0 and self.sent_to_quantum > 0:
                r["note_es"] = (
                    f"el triaje declaró {self.sent_to_quantum} candidatos elegibles para "
                    f"cuántico y NO se ejecutó ninguno: no se gastó un solo segundo. El "
                    f"0% no es que no hiciera falta, es que está pendiente."
                )
                r["note_en"] = (
                    f"triage declared {self.sent_to_quantum} candidates eligible for "
                    f"quantum and NONE were run: not one second was spent. The 0% does "
                    f"not mean it was unnecessary, it means it is pending."
                )
                r["quantum_eligible_but_not_run"] = self.sent_to_quantum
            else:
                r["note_es"] = (
                    f"el cuántico se quedó en {got_q:.0%} frente al {self.target_quantum:.0%} "
                    f"planeado, porque {self.skipped_by_triage} de "
                    f"{self.skipped_by_triage + self.sent_to_quantum} candidatos no pasaron "
                    f"el triaje. Se declara en vez de rellenarlo con cálculos que no "
                    f"cambiarían ninguna decisión."
                )
                r["note_en"] = (
                    f"quantum came in at {got_q:.0%} against the {self.target_quantum:.0%} "
                    f"planned, because {self.skipped_by_triage} of "
                    f"{self.skipped_by_triage + self.sent_to_quantum} candidates did not "
                    f"pass triage. It is declared rather than padded with calculations "
                    f"that would change no decision."
                )
        else:
            r["note_es"] = (
                f"el cuántico llegó al {got_q:.0%}, por encima del {self.target_quantum:.0%} "
                f"planeado: {self.sent_to_quantum} candidatos pasaron el triaje."
            )
            r["note_en"] = (
                f"quantum reached {got_q:.0%}, above the {self.target_quantum:.0%} "
                f"planned: {self.sent_to_quantum} candidates passed triage."
            )
        return r


# MOLEVERA / BIOQL
