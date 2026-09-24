"""Orienta un cromoforo conjugado para que "2pz" signifique sus orbitales pi.

POR QUE EXISTE -- MEDIDO 2026-09-24.
Las etiquetas de orbitales atomicos de PySCF van fijas a los ejes del laboratorio:
"C 2pz" es el p del carbono a lo largo del eje z GLOBAL. AVAS sobre
["C 2pz", "N 2pz", "O 2pz"] selecciona el sistema pi solo si el plano conjugado
es el plano xy. Un cromoforo sacado de un cristal (marco del PDB) llega orientado
al azar, y ahi el bloque "pi" de AVAS es una mezcla de sigma y pi: la ventana de
frontera que se toma dentro puede dejar fuera el HOMO y el LUMO.

Medido sobre la region QM de LBV en 4E04 (80 atomos, 948 cargas Amber14,
RHF/STO-3G, AVAS umbral 0.2, ventana de frontera k=4, CASCI(8,8)):
    marco del cristal:   AVAS 59 orbitales / 86 e; HOMO 0.8 % dentro de la ventana,
                         LUMO 26 %; S1 = 14.35 eV
    plano pi en xy:      AVAS 52 orbitales / 70 e; HOMO 84 %, LUMO 97 %; S1 = 3.43 eV
    La energia RHF es identica en ambos marcos (-1913.354371 Ha): la rotacion no
    cambia nada fisico, solo lo que AVAS llama "pi".
Explica el S1 absurdo de CASCI+AVAS (14.35 eV aqui; 14.37 eV registrados en
nir_differential). NO explica el T1: con la geometria orientada el T1 del bloque pi
sigue saliendo absurdo (22.4 eV, medido 2026-09-24) y la regla T1_NOT_AVAILABLE sigue.

La rotacion es rigida (las distancias no cambian) y debe aplicarse tambien a las
cargas puntuales del entorno, con la misma matriz.
"""

from typing import Any, Dict, Sequence, Tuple

__all__ = ["orient_pi_plane", "orient_atom_string"]


def orient_pi_plane(symbols: Sequence[str], coords, extra=None) -> Tuple[Any, Any, Dict[str, Any]]:
    """Rota de modo que el plano del mayor grupo conjugado sea el plano xy.

    symbols: simbolos de elemento; coords: (n, 3) en Angstrom; extra: puntos (m, 3)
    que rotan con la molecula (cargas puntuales). Devuelve (coords, extra, info).

    El grupo conjugado es el mayor conjunto enlazado de C/N planos de tres
    vecinos (suma de angulos >= 350 grados) mas los C/N de dos vecinos unidos a
    dos de ellos. Si tiene menos de 4 atomos se usan todos los atomos pesados.
    """
    import numpy as np

    X = np.asarray(coords, dtype=float)
    sym = [str(s).strip().capitalize() for s in symbols]
    n = len(sym)
    heavy = [i for i in range(n) if sym[i] != "H"]

    def bonded(i: int, j: int) -> bool:
        cut = 1.25 if "H" in (sym[i], sym[j]) else 1.75
        return float(np.linalg.norm(X[i] - X[j])) <= cut

    nbrs = {i: [j for j in range(n) if j != i and bonded(i, j)] for i in heavy}

    def planar(i: int) -> bool:
        nb = nbrs[i]
        if len(nb) != 3:
            return False
        v = [X[j] - X[i] for j in nb]
        total = 0.0
        for a in range(3):
            for b in range(a + 1, 3):
                c = float(np.dot(v[a], v[b]) / (np.linalg.norm(v[a]) * np.linalg.norm(v[b])))
                total += float(np.degrees(np.arccos(max(-1.0, min(1.0, c)))))
        return total >= 350.0

    sp2 = {i for i in heavy if sym[i] in ("C", "N") and planar(i)}
    sp2 |= {
        i
        for i in heavy
        if sym[i] in ("C", "N") and len(nbrs[i]) == 2 and sum(j in sp2 for j in nbrs[i]) == 2
    }
    seen: set = set()
    best: list = []
    for s0 in sorted(sp2):
        if s0 in seen:
            continue
        comp, stack = [], [s0]
        seen.add(s0)
        while stack:
            i = stack.pop()
            comp.append(i)
            for j in nbrs[i]:
                if j in sp2 and j not in seen:
                    seen.add(j)
                    stack.append(j)
        if len(comp) > len(best):
            best = comp
    idx = sorted(best) if len(best) >= 4 else heavy
    P = X[idx]
    c = P.mean(axis=0)
    _, sv, vt = np.linalg.svd(P - c)
    normal = vt[2] / np.linalg.norm(vt[2])
    z = np.array([0.0, 0.0, 1.0])
    if float(normal @ z) < 0:
        normal = -normal
    v = np.cross(normal, z)
    s = float(np.linalg.norm(v))
    cth = float(normal @ z)
    if s < 1e-12:
        R = np.eye(3)
    else:
        K = np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])
        R = np.eye(3) + K + K @ K * ((1.0 - cth) / s**2)
    Xr = (X - c) @ R.T + c
    Er = None if extra is None else (np.asarray(extra, dtype=float) - c) @ R.T + c
    info = {
        "n_plane_atoms": len(idx),
        "from_conjugated_cluster": len(best) >= 4,
        "plane_rms_A": float(sv[2] / np.sqrt(len(idx))),
        "tilt_before_deg": float(np.degrees(np.arccos(min(1.0, abs(cth))))),
    }
    return Xr, Er, info


def orient_atom_string(atom: str, extra=None) -> Tuple[str, Any, Dict[str, Any]]:
    """orient_pi_plane sobre una geometria en formato "S x y z; S x y z" (o por lineas).

    Devuelve la geometria en el mismo formato, los puntos extra rotados y la info.
    """
    parts = [t.strip() for t in str(atom).replace("\n", ";").split(";") if t.strip()]
    symbols = [t.split()[0] for t in parts]
    coords = [[float(x) for x in t.split()[1:4]] for t in parts]
    Xr, Er, info = orient_pi_plane(symbols, coords, extra)
    out = "; ".join(f"{s} {x:.6f} {y:.6f} {z:.6f}" for s, (x, y, z) in zip(symbols, Xr))
    return out, Er, info
