"""
EWF de verdad, en esta máquina, para cualquier pipeline que lo quiera.

QUÉ ES ESTO Y POR QUÉ NO ESTÁ EN `ewf_sqd_pipeline.py`
------------------------------------------------------
El repo ya implementaba el método de Cleveland Clinic / RIKEN (arXiv:2512.17130):
fragmentación de función de onda embebida (EWF) con clusters, el clásico resuelve
los fáciles y SQD los entrelazados. Eso es lo que permitió llegar a 11 608 átomos
sin meter 11 608 átomos en un ordenador cuántico.

No se enchufa ahí por dos razones concretas:

1. `ewf_sqd_pipeline.py` NO está bajo control de versiones y `/opt/bioql` tiene una
   copia 221 líneas más nueva que es la que carga el backend vivo. Editar el repo
   ahí no hace nada. Este módulo es nuevo, así que resuelve desde el repo y lo que
   se escriba aquí sí corre.
2. Aquel módulo delega TODO en Modal, y el workspace de Modal está deshabilitado.
   Vayesta, en cambio, compila en macOS -- pese a un comentario del propio repo que
   dice que no -- y corre aquí mismo. Medido sobre glicilglicina en sto-3g:

       RHF    -298.11232694 Ha
       EWF    -298.45908359 Ha     (14 fragmentos IAO con baño)
       CCSD   -298.47041961 Ha
       EWF - CCSD = +7.11 kcal/mol, o el 96.8 % de la correlación CCSD

LO QUE ESTO SÍ ES, Y LO QUE NO
------------------------------
Es EWF completo: fragmentación IAO, baño de orbitales por fragmento construido
desde la matriz de densidad de campo medio, y partición democrática de la energía.
El baño ES el acoplamiento -- cada cluster ve su entorno a través de él -- y por eso
esto no se parece a trocear átomos y sumar.

No es la corrida del paper: allí los clusters duros se resuelven con SQD en
hardware, y aquí el solver por defecto de Vayesta es CCSD. `hard_clusters()`
devuelve exactamente cuáles merecerían SQD y con cuántos orbitales, para que ese
peldaño se suba cuando haya con qué. Decir en qué punto se está es la diferencia
entre un método y una foto de un método.

MOLEVERA / BIOQL
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Umbral de orbitales activos por encima del cual un cluster merece SQD.
# Es el mismo que usa el resto del repo (`hard_orb_threshold`), y no se elige
# aquí por gusto: por debajo de eso, CCSD ya es prácticamente exacto y gastar
# cuántico no cambiaría ninguna decisión.
HARD_ORB_THRESHOLD = 6

# Umbral del baño. 1e-5 es el del paper para sistemas pequeños; 1e-4 abre la mano
# y hace tratables las moléculas grandes. Se declara con el resultado porque
# cambia lo que significa el número.
BATH_DEFAULT = 1e-4


def available() -> Dict[str, Any]:
    """¿Se puede hacer EWF en este proceso, y con qué?"""
    fuera: Dict[str, Any] = {"vayesta": False, "pyscf": False}
    try:
        import pyscf

        fuera["pyscf"] = True
        fuera["pyscf_version"] = pyscf.__version__
    except Exception as e:  # noqa: BLE001
        fuera["pyscf_error"] = f"{type(e).__name__}: {e}"
    try:
        # Vayesta parsea sys.argv al importarse y choca con gunicorn; el repo ya
        # tenía esta precaución en `ewf_sqd_pipeline` y se conserva.
        import sys

        _argv, sys.argv = sys.argv, ["bioql"]
        try:
            import vayesta
            import vayesta.ewf  # noqa: F401
        finally:
            sys.argv = _argv
        fuera["vayesta"] = True
        fuera["vayesta_version"] = getattr(vayesta, "__version__", "?")
    except Exception as e:  # noqa: BLE001
        fuera["vayesta_error"] = f"{type(e).__name__}: {e}"
    fuera["ok"] = bool(fuera["vayesta"] and fuera["pyscf"])
    return fuera


# ── entradas: de lo que tienen los pipelines a una lista de átomos ───────────
def atoms_from_molblock(molblock: str) -> List[Tuple[str, Tuple[float, float, float]]]:
    """Átomos con sus coordenadas desde un MOL/SDF 3D, hidrógenos incluidos.

    Los hidrógenos NO son opcionales: un fragmento sin ellos tiene la valencia
    incompleta y su energía es la de otra cosa. Este mismo error ya se cometió
    una vez en el recorte de regiones de macrociclos.
    """
    from rdkit import Chem

    m = Chem.MolFromMolBlock(molblock, removeHs=False)
    if m is None or m.GetNumConformers() == 0:
        return []
    conf = m.GetConformer()
    fuera = []
    for a in m.GetAtoms():
        p = conf.GetAtomPosition(a.GetIdx())
        fuera.append((a.GetSymbol(), (float(p.x), float(p.y), float(p.z))))
    return fuera


def atoms_from_pdb(pdb_text: str, chain: str = "") -> List[Tuple[str, Tuple[float, float, float]]]:
    """Átomos desde un PDB. Sin hidrógenos si el fichero no los trae, y se dice."""
    fuera = []
    for ln in (pdb_text or "").splitlines():
        if not ln.startswith(("ATOM", "HETATM")):
            continue
        if chain and ln[21] != chain:
            continue
        el = (ln[76:78].strip() or ln[12:16].strip()[:1]).capitalize()
        try:
            fuera.append((el, (float(ln[30:38]), float(ln[38:46]), float(ln[46:54]))))
        except ValueError:
            continue
    return fuera


# ── el cálculo ───────────────────────────────────────────────────────────────
def embed(
    atoms: Sequence[Tuple[str, Tuple[float, float, float]]],
    *,
    basis: str = "sto-3g",
    charge: int = 0,
    spin: int = 0,
    bath_threshold: float = BATH_DEFAULT,
    density_fit: bool = True,
    max_atoms: int = 400,
) -> Dict[str, Any]:
    """EWF sobre la molécula entera: campo medio, fragmentación IAO y baño.

    Devuelve las energías y el desglose por cluster. Nunca inventa un número: si
    el campo medio no converge o Vayesta no está, sale `available: False` con la
    razón, porque un EWF sobre un RHF que no convergió no es un resultado peor,
    es un resultado de otra cosa.
    """
    t0 = time.perf_counter()
    disp = available()
    if not disp["ok"]:
        return {
            "available": False,
            "reason": disp.get("vayesta_error") or disp.get("pyscf_error") or "EWF no disponible",
            "backends": disp,
        }
    if not atoms:
        return {"available": False, "reason": "no se recibió ningún átomo"}
    if len(atoms) > max_atoms:
        return {
            "available": False,
            "reason": (
                f"{len(atoms)} átomos superan el tope de {max_atoms} de esta llamada. "
                f"El método escala con el número de CLUSTERS, no con la molécula, "
                f"pero el campo medio previo sí crece y hay que acotarlo a propósito"
            ),
            "n_atoms": len(atoms),
        }

    import sys

    _argv, sys.argv = sys.argv, ["bioql"]
    try:
        import pyscf.gto
        import pyscf.scf
        import vayesta.ewf

        mol = pyscf.gto.M(
            atom=[(s, p) for s, p in atoms], basis=basis, charge=charge, spin=spin, verbose=0
        )
        mf = pyscf.scf.RHF(mol)
        if density_fit:
            mf = mf.density_fit()
        mf.kernel()
        t_hf = time.perf_counter() - t0
        if not mf.converged:
            return {
                "available": False,
                "reason": (
                    "el campo medio no convergió, y un EWF construido sobre un RHF "
                    "no convergido no es un resultado peor: es el de otra molécula"
                ),
                "n_atoms": len(atoms),
                "n_basis": int(mol.nao_nr()),
                "hf_seconds": round(t_hf, 1),
            }

        t1 = time.perf_counter()
        ewf = vayesta.ewf.EWF(mf, bath_options=dict(threshold=float(bath_threshold)))
        with ewf.iao_fragmentation() as frag:
            frag.add_all_atomic_fragments()
        ewf.kernel()
        t_ewf = time.perf_counter() - t1
    except Exception as e:  # noqa: BLE001
        return {
            "available": False,
            "reason": f"EWF falló: {type(e).__name__}: {str(e)[:180]}",
            "n_atoms": len(atoms),
        }
    finally:
        sys.argv = _argv

    clusters: List[Dict[str, Any]] = []
    for fr in ewf.fragments:
        c = getattr(fr, "cluster", None)
        clusters.append(
            {
                "id": int(getattr(fr, "id", len(clusters))),
                "name": str(getattr(fr, "name", "")),
                "norb_active": int(getattr(c, "norb_active", 0) or 0),
                "hard": int(getattr(c, "norb_active", 0) or 0) > HARD_ORB_THRESHOLD,
            }
        )
    duros = [c for c in clusters if c["hard"]]

    return {
        "available": True,
        "method": "EWF (Vayesta) / fragmentación IAO con baño de orbitales",
        "engine": f"vayesta {disp.get('vayesta_version')} · pyscf {disp.get('pyscf_version')}",
        "basis": basis,
        "bath_threshold": float(bath_threshold),
        "density_fit": bool(density_fit),
        "n_atoms": len(atoms),
        "n_basis": int(mol.nao_nr()),
        "e_hf_Ha": float(mf.e_tot),
        "e_ewf_Ha": float(ewf.e_tot),
        "e_corr_Ha": float(ewf.e_corr),
        "n_fragments": len(clusters),
        "n_hard_clusters": len(duros),
        "hard_orb_threshold": HARD_ORB_THRESHOLD,
        "clusters": clusters,
        "hf_seconds": round(t_hf, 1),
        "ewf_seconds": round(t_ewf, 1),
        "wall_seconds": round(time.perf_counter() - t0, 1),
        "solver_note_es": (
            f"los clusters se resuelven con el solver por defecto de Vayesta (CCSD). "
            f"{len(duros)} de {len(clusters)} superan los {HARD_ORB_THRESHOLD} orbitales "
            f"activos y son los que en el método del paper irían a SQD; aquí no han "
            f"ido, y por eso se listan en vez de darlo por hecho"
        ),
        "solver_note_en": (
            f"clusters are solved with Vayesta's default solver (CCSD). {len(duros)} of "
            f"{len(clusters)} exceed {HARD_ORB_THRESHOLD} active orbitals and are the "
            f"ones the paper's method would send to SQD; here they did not go, which is "
            f"why they are listed rather than assumed"
        ),
        "caveat_es": (
            "el baño de orbitales ES el acoplamiento: cada cluster ve su entorno a "
            "través de él, y por eso esto no es trocear átomos y sumar. La energía "
            "total es la de la molécula entera, no una diferencia"
        ),
        "caveat_en": (
            "the orbital bath IS the coupling: each cluster sees its environment "
            "through it, which is why this is not chopping atoms up and adding. The "
            "total energy is the whole molecule's, not a difference"
        ),
    }


def hard_clusters(resultado: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Los clusters que merecerían SQD, ordenados por tamaño de espacio activo."""
    return sorted(
        (c for c in (resultado.get("clusters") or []) if c.get("hard")),
        key=lambda c: -int(c.get("norb_active") or 0),
    )


def validate_against_ccsd(
    atoms: Sequence[Tuple[str, Tuple[float, float, float]]],
    *,
    basis: str = "sto-3g",
    bath_threshold: float = 1e-5,
    max_atoms_for_ccsd: int = 20,
) -> Dict[str, Any]:
    """EWF contra CCSD completo sobre el mismo sistema, cuando CCSD es alcanzable.

    Existe porque un método de embedding sin una referencia no es comprobable, y
    porque el número que importa no es la energía sino cuánta correlación
    recupera. Se limita a sistemas pequeños a propósito: CCSD sobre la molécula
    entera es justo lo que el embedding evita, y correrlo en grande para validar
    tendría el coste que se quería ahorrar.
    """
    if len(atoms) > max_atoms_for_ccsd:
        return {
            "available": False,
            "reason": (
                f"{len(atoms)} átomos: CCSD completo sobre esto es exactamente el "
                f"coste que el embedding evita, así que no se corre para validarlo"
            ),
        }
    r = embed(atoms, basis=basis, bath_threshold=bath_threshold, density_fit=False)
    if not r.get("available"):
        return r
    import sys

    _argv, sys.argv = sys.argv, ["bioql"]
    try:
        import pyscf.cc
        import pyscf.gto
        import pyscf.scf

        mol = pyscf.gto.M(atom=[(s, p) for s, p in atoms], basis=basis, verbose=0)
        mf = pyscf.scf.RHF(mol).run()
        cc = pyscf.cc.CCSD(mf).run()
    except Exception as e:  # noqa: BLE001
        return {**r, "validation": {"available": False, "reason": f"CCSD falló: {e}"}}
    finally:
        sys.argv = _argv

    HARTREE_KCAL = 627.509
    d = (r["e_ewf_Ha"] - float(cc.e_tot)) * HARTREE_KCAL
    pct = 100.0 * r["e_corr_Ha"] / float(cc.e_corr) if cc.e_corr else 0.0
    return {
        **r,
        "validation": {
            "available": True,
            "reference": "CCSD sobre la molécula entera, misma base",
            "e_ccsd_Ha": float(cc.e_tot),
            "e_corr_ccsd_Ha": float(cc.e_corr),
            "ewf_minus_ccsd_kcal": round(d, 3),
            "correlation_recovered_pct": round(pct, 1),
            "note_es": (
                f"EWF recupera el {pct:.1f} % de la correlación de CCSD y queda a "
                f"{d:+.2f} kcal/mol de él. La referencia es CCSD, no el experimento"
            ),
            "note_en": (
                f"EWF recovers {pct:.1f} % of CCSD's correlation and sits {d:+.2f} "
                f"kcal/mol from it. The reference is CCSD, not experiment"
            ),
        },
    }


__all__ = [
    "available",
    "atoms_from_molblock",
    "atoms_from_pdb",
    "embed",
    "hard_clusters",
    "validate_against_ccsd",
    "HARD_ORB_THRESHOLD",
]

# MOLEVERA / BIOQL
