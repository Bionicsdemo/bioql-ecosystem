"""
The small molecule the run designed, as atoms and bonds the page can draw.

The pipelines already carry an optimised 3D conformer as an MDL MOL/SDF block
(RDKit MMFF94), so nothing is generated here: this reads that block. V2000 and
V3000 are both handled, since the fixed-width V2000 counts line breaks when an
atom count reaches four digits and some blocks come out as V3000.

Coordinates are centred and rounded; the page draws spheres and cylinders from
them, so a molecule costs a few kilobytes instead of a mesh.

MOLEVERA / BIOQL
"""

from typing import Any, Dict, List, Optional

# Covalent radii (Å) for the elements that appear in drug-like molecules, used
# only to size the spheres the page draws.
RADII = {
    "H": 0.31,
    "C": 0.76,
    "N": 0.71,
    "O": 0.66,
    "F": 0.57,
    "P": 1.07,
    "S": 1.05,
    "Cl": 1.02,
    "Br": 1.20,
    "I": 1.39,
    "B": 0.84,
    "Si": 1.11,
    "Se": 1.20,
}


def _v2000(lines: List[str]) -> Optional[Dict[str, Any]]:
    counts = lines[3]
    try:
        n_at, n_bd = int(counts[0:3]), int(counts[3:6])
    except ValueError:
        return None
    if n_at <= 0 or len(lines) < 4 + n_at + n_bd:
        return None
    atoms, bonds = [], []
    for ln in lines[4 : 4 + n_at]:
        try:
            atoms.append(
                {
                    "e": ln[31:34].strip() or "C",
                    "p": [float(ln[0:10]), float(ln[10:20]), float(ln[20:30])],
                }
            )
        except ValueError:
            return None
    for ln in lines[4 + n_at : 4 + n_at + n_bd]:
        try:
            bonds.append([int(ln[0:3]) - 1, int(ln[3:6]) - 1, int(ln[6:9] or 1)])
        except ValueError:
            continue
    return {"atoms": atoms, "bonds": bonds}


def _v3000(lines: List[str]) -> Optional[Dict[str, Any]]:
    atoms, bonds, mode = [], [], None
    for ln in lines:
        s = ln.strip()
        if s.startswith("M  V30 BEGIN ATOM"):
            mode = "a"
            continue
        if s.startswith("M  V30 BEGIN BOND"):
            mode = "b"
            continue
        if s.startswith("M  V30 END"):
            mode = None
            continue
        if not s.startswith("M  V30 ") or mode is None:
            continue
        f = s[7:].split()
        try:
            if mode == "a" and len(f) >= 5:
                atoms.append({"e": f[1], "p": [float(f[2]), float(f[3]), float(f[4])]})
            elif mode == "b" and len(f) >= 4:
                bonds.append([int(f[2]) - 1, int(f[3]) - 1, int(f[1])])
        except ValueError:
            continue
    return {"atoms": atoms, "bonds": bonds} if atoms else None


def parse(block: Any) -> Optional[Dict[str, Any]]:
    """Atoms, bonds and a formula from an MDL MOL/SDF block, or None."""
    if not isinstance(block, str) or "\n" not in block:
        return None
    lines = block.splitlines()
    if len(lines) < 5:
        return None
    parsed = _v3000(lines) if any("V30" in ln for ln in lines[:8]) else _v2000(lines)
    if not parsed or not parsed["atoms"]:
        return None
    atoms, bonds = parsed["atoms"], parsed["bonds"]
    n = len(atoms)
    cx, cy, cz = (sum(a["p"][i] for a in atoms) / n for i in range(3))
    for a in atoms:
        a["p"] = [round(a["p"][0] - cx, 3), round(a["p"][1] - cy, 3), round(a["p"][2] - cz, 3)]
        a["r"] = RADII.get(a["e"], 0.8)
    counts: Dict[str, int] = {}
    for a in atoms:
        counts[a["e"]] = counts.get(a["e"], 0) + 1
    bonds = [b for b in bonds if 0 <= b[0] < n and 0 <= b[1] < n]
    span = max((max(abs(a["p"][i]) for i in range(3)) for a in atoms), default=1.0)
    return {
        "atoms": atoms,
        "bonds": bonds,
        "n_atoms": n,
        "n_bonds": len(bonds),
        "counts": counts,
        "span": round(span, 2),
        "heavy": sum(1 for a in atoms if a["e"] != "H"),
    }


# MOLEVERA / BIOQL
