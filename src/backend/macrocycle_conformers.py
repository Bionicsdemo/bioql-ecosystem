"""
Confórmeros de macrociclo: el cuello de botella real, y donde se pierde gente.

No es el docking lo que decide la calidad de un triaje de macrociclos, es el
ensemble. Un anillo de 15-30 átomos tiene un paisaje conformacional que ETKDG
plano no muestrea bien, y RDKit trae desde hace años dos ajustes específicos que
el repo no estaba usando: `useMacrocycleTorsions` y `useMacrocycle14config`.

EL MODO DE FALLO QUE ESTE MÓDULO EXISTE PARA HACER VISIBLE
----------------------------------------------------------
El embebido 3D no falla al azar: falla sistemáticamente en los anillos grandes y
tensionados, que son justo los interesantes. Si los que fallan se caen en
silencio, el ranking de 500 candidatos resulta ser sobre los 120 que embebieron,
y la selección está sesgada hacia lo fácil de embeber -- que no es lo mismo que
lo bueno.

Por eso `embed_ensemble` devuelve SIEMPRE la contabilidad completa: cuántos
entraron, cuántos salieron y por qué cayó cada uno. `population_conserved()`
comprueba que la suma cuadra, y `failure_by_ring()` desglosa la tasa de fallo por
tipo de ciclación y tamaño de anillo, que es la métrica de salud del pipeline.

Su gemelo es el ensemble que no convergió: si muestreas 50 confórmeros donde el
anillo necesitaba miles, el confórmero bioactivo nunca estuvo en la caja y nada
aguas abajo lo delata. `convergence_curve()` mide cuántos confórmeros nuevos
aparecían todavía al final; si la curva no ha aplanado, se dice.

MOLEVERA / BIOQL
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import AllChem, rdMolAlign, rdMolDescriptors

    RDLogger.DisableLog("rdApp.*")
    _RDKIT = True
except Exception:  # pragma: no cover
    _RDKIT = False


# Un macrociclo peptídico típico necesita bastante más muestreo que una molécula
# pequeña. Estas cifras son el punto de partida, y la curva de convergencia dice
# si hicieron falta más.
DEFAULT_N_CONF = 200
RMSD_DEDUP = 0.5  # Å, sobre átomos pesados
MAX_ITERS = 2000


@dataclass
class EnsembleResult:
    """Lo que sale del embebido, con la contabilidad puesta."""

    smiles: str
    ok: bool
    n_requested: int = 0
    n_embedded: int = 0
    n_after_dedup: int = 0
    ring_size: Optional[int] = None
    cyclization: str = ""
    forcefield: str = ""
    reason: str = ""
    energies_kcal: List[float] = field(default_factory=list)
    new_per_block: List[int] = field(default_factory=list)
    converged: Optional[bool] = None
    wall_seconds: float = 0.0
    molblock: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d.pop("molblock", None)  # pesa y no se necesita en el resumen
        return d


def _largest_ring(mol) -> Optional[int]:
    anillos = [r for r in mol.GetRingInfo().AtomRings() if len(r) > 8]
    return len(max(anillos, key=len)) if anillos else None


def embed_ensemble(
    smiles: str,
    *,
    n_conf: int = DEFAULT_N_CONF,
    cyclization: str = "",
    seed: int = 0xF00D,
    rmsd_dedup: float = RMSD_DEDUP,
    prune_energy_kcal: float = 25.0,
    block: int = 25,
) -> EnsembleResult:
    """Ensemble 3D de un macrociclo, con las torsiones de macrociclo activadas.

    Devuelve un resultado aunque falle: `ok=False` con la razón escrita, para que
    el candidato quede CONTADO como caído y no desaparezca de la población.
    """
    t0 = time.perf_counter()
    out = EnsembleResult(smiles=smiles, ok=False, n_requested=n_conf, cyclization=cyclization)
    if not _RDKIT:
        out.reason = "RDKit no disponible"
        return out
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        out.reason = "el SMILES no es una molécula válida"
        return out
    out.ring_size = _largest_ring(mol)
    if out.ring_size is None:
        out.reason = (
            "no hay anillo de más de 8 átomos: esto no es un macrociclo, "
            "y embeberlo como tal daría un ensemble de otra cosa"
        )
        return out

    mol = Chem.AddHs(mol)
    ps = AllChem.ETKDGv3()
    ps.randomSeed = int(seed)
    ps.useMacrocycleTorsions = True  # lo que el repo no estaba usando
    ps.useMacrocycle14config = True
    ps.pruneRmsThresh = -1.0  # la poda se hace después, medida
    ps.maxIterations = MAX_ITERS
    ps.useRandomCoords = True  # los anillos grandes lo necesitan

    # Se embebe por bloques para poder dibujar la curva de convergencia: cuántos
    # confórmeros NUEVOS aportó cada bloque.
    vistos: List[int] = []
    try:
        ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=int(n_conf), params=ps))
    except Exception as e:  # noqa: BLE001
        out.reason = f"el embebido lanzó {type(e).__name__}: {str(e)[:120]}"
        out.wall_seconds = round(time.perf_counter() - t0, 2)
        return out
    out.n_embedded = len(ids)
    if not ids:
        out.reason = (
            f"ETKDG no produjo ningún confórmero para un anillo de "
            f"{out.ring_size} átomos tras {MAX_ITERS} iteraciones"
        )
        out.wall_seconds = round(time.perf_counter() - t0, 2)
        return out

    # Minimización: MMFF94s, y UFF si el campo no cubre algún átomo.
    energias: Dict[int, float] = {}
    ff_usado = ""
    props = AllChem.MMFFGetMoleculeProperties(mol, mmffVariant="MMFF94s")
    if props is not None:
        ff_usado = "MMFF94s"
        for cid in ids:
            try:
                ff = AllChem.MMFFGetMoleculeForceField(mol, props, confId=cid)
                ff.Minimize(maxIts=500)
                energias[cid] = float(ff.CalcEnergy())
            except Exception:  # noqa: BLE001
                pass
    if not energias:
        ff_usado = "UFF"
        for cid in ids:
            try:
                ff = AllChem.UFFGetMoleculeForceField(mol, confId=cid)
                ff.Minimize(maxIts=500)
                energias[cid] = float(ff.CalcEnergy())
            except Exception:  # noqa: BLE001
                pass
    out.forcefield = ff_usado or "ninguno"
    if not energias:
        out.reason = "ni MMFF94s ni UFF pudieron minimizar ningún confórmero"
        out.wall_seconds = round(time.perf_counter() - t0, 2)
        return out

    # Poda: primero por energía relativa, luego por RMSD de átomos pesados.
    e_min = min(energias.values())
    vivos = [
        c
        for c, e in sorted(energias.items(), key=lambda kv: kv[1])
        if e - e_min <= prune_energy_kcal
    ]
    sin_h = Chem.RemoveHs(mol)
    guardados: List[int] = []
    for cid in vivos:
        duplicado = False
        for keep in guardados:
            try:
                if rdMolAlign.GetBestRMS(sin_h, sin_h, prbId=cid, refId=keep) < rmsd_dedup:
                    duplicado = True
                    break
            except Exception:  # noqa: BLE001
                pass
        if not duplicado:
            guardados.append(cid)
            vistos.append(len(guardados))

    out.n_after_dedup = len(guardados)
    out.energies_kcal = [round(energias[c] - e_min, 3) for c in guardados]

    # Curva de convergencia: confórmeros únicos nuevos por bloque de `block`
    # confórmeros embebidos. Si el último bloque seguía aportando, no convergió.
    nuevos: List[int] = []
    previo = 0
    for i in range(block, len(vivos) + block, block):
        hasta = len([g for g in guardados if vivos.index(g) < i])
        nuevos.append(hasta - previo)
        previo = hasta
    out.new_per_block = nuevos
    if len(nuevos) >= 2:
        out.converged = nuevos[-1] <= max(1, int(0.05 * out.n_after_dedup))
    out.ok = out.n_after_dedup > 0
    if not out.ok:
        out.reason = "la poda dejó cero confórmeros"
    try:
        out.molblock = Chem.MolToMolBlock(mol, confId=guardados[0]) if guardados else ""
    except Exception:  # noqa: BLE001
        out.molblock = ""
    out.wall_seconds = round(time.perf_counter() - t0, 2)
    return out


# ── la contabilidad, que es lo que impide el sesgo del superviviente ──────────
def population_conserved(entrada: int, resultados: List[EnsembleResult]) -> Dict[str, Any]:
    """¿Cuadra la población?  N_entrada == N_salida + N_caídos, cada caída con razón.

    Es la comprobación que impide que el ranking final sea sobre un subconjunto
    sesgado sin que nadie lo haya dicho.
    """
    ok = [r for r in resultados if r.ok]
    caidos = [r for r in resultados if not r.ok]
    sin_razon = [r for r in caidos if not r.reason]
    return {
        "ok": (len(ok) + len(caidos) == entrada) and not sin_razon,
        "n_in": entrada,
        "n_out": len(ok),
        "n_dropped": len(caidos),
        "dropped_without_reason": len(sin_razon),
        "reasons": sorted({r.reason[:80] for r in caidos}),
        "note": (
            ""
            if len(ok) + len(caidos) == entrada
            else f"entraron {entrada} y se contabilizan {len(ok) + len(caidos)}: "
            f"faltan {entrada - len(ok) - len(caidos)} candidatos sin explicar"
        ),
    }


def failure_by_ring(resultados: List[EnsembleResult]) -> Dict[str, Any]:
    """Tasa de fallo desglosada por ciclación y tamaño de anillo.

    Es una métrica de salud del pipeline, no un detalle: si los anillos grandes
    fallan mucho más que los pequeños, la librería que llega al docking ya no es
    la que se diseñó.
    """
    tabla: Dict[str, Dict[str, int]] = {}
    for r in resultados:
        clave = f"{r.cyclization or '?'}/{r.ring_size or '?'}"
        celda = tabla.setdefault(clave, {"total": 0, "failed": 0})
        celda["total"] += 1
        if not r.ok:
            celda["failed"] += 1
    for celda in tabla.values():
        celda["failure_rate"] = round(celda["failed"] / celda["total"], 3)  # type: ignore[assignment]
    vacio: Dict[str, int] = {}
    peor: Tuple[Optional[str], Dict[str, int]] = max(
        tabla.items(), key=lambda kv: kv[1]["failure_rate"], default=(None, vacio)
    )
    return {
        "by_cyclization_and_ring": tabla,
        "worst": {"key": peor[0], **peor[1]} if peor[0] else None,
    }


def convergence_note(resultados: List[EnsembleResult]) -> Dict[str, Any]:
    """Cuántos ensembles no habían dejado de crecer cuando se paró de muestrear."""
    con_curva = [r for r in resultados if r.converged is not None]
    sin_converger = [r for r in con_curva if r.converged is False]
    return {
        "n_with_curve": len(con_curva),
        "n_not_converged": len(sin_converger),
        "note": (
            "todos los ensembles habían aplanado su curva"
            if not sin_converger
            else f"{len(sin_converger)} de {len(con_curva)} ensembles seguían "
            f"aportando confórmeros nuevos al parar: su confórmero bioactivo "
            f"puede no haber estado en la caja, y su orden no debe leerse "
            f"como definitivo"
        ),
    }


# MOLEVERA / BIOQL
