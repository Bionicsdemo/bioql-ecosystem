"""
PyMOL-grade cartoon meshes for any structure a pipeline returns.

The same route The Active Space used, made automatic: PyMOL draws the cartoon
(fancy helices, smooth loops) and exports it as OBJ; this module packs it into a
compact binary (int16 positions, int8 normals, uint32 indices, gzip) that the
page's `decodeMesh` reads, and sorts the triangles by residue so the page can
grow the chain residue by residue. Per residue it also records the secondary
structure PyMOL assigned and the B-factor, which for ESMFold / Boltz / AF
models is the pLDDT.

PyMOL runs as a subprocess (`pymol -cq`), so a crash or a missing PyMOL costs
only the 3D mesh of that structure, never the report: `cartoon()` returns None
with the reason in `last_error`.

MOLEVERA / BIOQL
"""

import base64
import gzip
import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

NUCLEOTIDES = {
    "A",
    "U",
    "G",
    "C",
    "T",
    "DA",
    "DT",
    "DG",
    "DC",
    "DU",
    "PSU",
    "1MA",
    "5MC",
    "OMG",
    "OMC",
}
last_error: Optional[str] = None


def pymol_binary() -> Optional[str]:
    env = os.environ.get("BIOQL_PYMOL")
    for cand in (env, "/opt/homebrew/bin/pymol", shutil.which("pymol")):
        if cand and os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def residues(pdb: str) -> Tuple[List[Dict[str, Any]], str]:
    """One anchor per residue (CA for protein, C4' or P for nucleic acid), in file order.

    Only the first MODEL is read. Returns (residues, kind) with kind 'protein' or 'rna'.
    """
    anchors: Dict[Tuple[str, str], Dict[str, Any]] = {}
    order: List[Tuple[str, str]] = []
    n_nuc = n_aa = 0
    for ln in pdb.splitlines():
        if ln.startswith("ENDMDL"):
            break
        if not ln.startswith(("ATOM  ", "HETATM")):
            continue
        name, resn = ln[12:16].strip(), ln[17:20].strip()
        chain, resi = ln[21].strip() or "A", ln[22:27].strip()
        key = (chain, resi)
        is_nuc = resn in NUCLEOTIDES
        want = ("C4'", "P") if is_nuc else ("CA",)
        if name not in want:
            continue
        try:
            xyz = [float(ln[30:38]), float(ln[38:46]), float(ln[46:54])]
            b = float(ln[60:66]) if ln[60:66].strip() else None
        except ValueError:
            continue
        cur = anchors.get(key)
        if cur is None:
            order.append(key)
            if is_nuc:
                n_nuc += 1
            else:
                n_aa += 1
        if cur is None or (is_nuc and name == "C4'"):
            anchors[key] = {"chain": chain, "resi": resi, "resn": resn, "p": xyz, "b": b}
    out = [anchors[k] for k in order]
    return out, ("rna" if n_nuc > n_aa else "protein")


_SCRIPT = r"""
from pymol import cmd
import json
cmd.load({pdb!r}, "m")
cmd.remove("solvent or inorganic or (hetatm and not polymer)")
cmd.hide("everything")
cmd.set("cartoon_fancy_helices", 1)
cmd.set("cartoon_smooth_loops", 1)
cmd.set("cartoon_sampling", {sampling})
cmd.set("cartoon_loop_radius", 0.28)
cmd.set("cartoon_oval_length", 1.45)
cmd.set("cartoon_oval_width", 0.28)
cmd.set("cartoon_rect_length", 1.55)
cmd.set("cartoon_rect_width", 0.42)
cmd.set("cartoon_dumbbell_length", 1.7)
cmd.set("cartoon_dumbbell_width", 0.24)
cmd.set("cartoon_ring_mode", 3)
cmd.set("cartoon_ring_finder", 1)
cmd.set("cartoon_nucleic_acid_mode", 4)
cmd.set("cartoon_tube_radius", 0.5)
if {is_protein}:
    cmd.dss("m")
cmd.show("cartoon", "polymer")
cmd.set_view((1,0,0, 0,1,0, 0,0,1, 0,0,-150, 0,0,0, 100,200,-20))
cmd.save({obj!r})
ss = {{}}
cmd.iterate("m and (name CA or name C4')", "ss_d[chain + ':' + resi] = ss", space={{"ss_d": ss}})
json.dump(ss, open({ssf!r}, "w"))
"""


def _read_obj(path: str):
    V, N, F = [], [], []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                V.append([float(t) for t in line.split()[1:4]])
            elif line.startswith("vn "):
                N.append([float(t) for t in line.split()[1:4]])
            elif line.startswith("f "):
                tri = []
                for tok in line.split()[1:4]:
                    a = tok.split("/")
                    tri.append(
                        (int(a[0]) - 1, int(a[2]) - 1 if len(a) > 2 and a[2] else int(a[0]) - 1)
                    )
                F.append(tri)
    return np.asarray(V, np.float64), np.asarray(N, np.float64), F


def _nearest(points: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    try:
        from scipy.spatial import cKDTree

        return cKDTree(anchors).query(points)[1]
    except Exception:
        out = np.empty(len(points), np.int64)
        for s in range(0, len(points), 4096):
            d = ((points[s : s + 4096, None, :] - anchors[None, :, :]) ** 2).sum(-1)
            out[s : s + 4096] = d.argmin(1)
        return out


def pack(obj_path: str, center: np.ndarray, anchors: np.ndarray) -> Tuple[Dict[str, Any], bytes]:
    V, N, F = _read_obj(obj_path)
    if not F:
        raise ValueError("PyMOL wrote an empty mesh")
    span = float(np.abs(V - center).max()) if len(V) else 1.0
    scale = max(0.002, span / 32000.0)
    Fa = np.asarray(F, np.int64)  # (n_tri, 3, 2): vertex and normal index per corner
    vi, ni = Fa[:, :, 0].ravel(), Fa[:, :, 1].ravel()
    P_all = np.round((V[vi] - center) / scale).astype(np.int32)
    Nv = np.where(
        (ni < len(N))[:, None],
        N[np.clip(ni, 0, max(len(N) - 1, 0))] if len(N) else 0.0,
        [0.0, 0.0, 1.0],
    )
    norm = np.linalg.norm(Nv, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    N_all = np.round(Nv / norm * 127).astype(np.int32)
    # the same (position, normal) corner is one vertex
    uniq, inverse = np.unique(np.concatenate([P_all, N_all], axis=1), axis=0, return_inverse=True)
    P = uniq[:, :3].astype(np.int32)
    Nn = uniq[:, 3:].astype(np.int8)
    tris = inverse.reshape(-1, 3).astype(np.uint32)
    cent = P[tris].mean(axis=1) * scale
    near = _nearest(cent, anchors - center)
    order = np.argsort(near, kind="stable")
    tris = tris[order]
    near = near[order]
    res_end: Dict[int, int] = {}
    for t, r in enumerate(near):
        res_end[int(r)] = t + 1
    meta = {"scale": scale, "nv": int(len(P)), "nt": int(len(tris)), "resEnd": res_end}
    blob = P.astype(np.int16).tobytes() + Nn.tobytes() + tris.astype(np.uint32).tobytes()
    return meta, gzip.compress(blob, 9)


def cartoon(pdb: str, sampling: int = 8, timeout: int = 240) -> Optional[Dict[str, Any]]:
    """Mesh + per-residue data for one structure, or None (reason in `last_error`)."""
    global last_error
    last_error = None
    res, kind = residues(pdb)
    if len(res) < 3:
        last_error = f"structure has {len(res)} residues with a backbone anchor"
        return None
    exe = pymol_binary()
    if not exe:
        last_error = "PyMOL not found (set BIOQL_PYMOL)"
        return None
    anchors = np.asarray([r["p"] for r in res], np.float64)
    center = anchors.mean(axis=0)
    with tempfile.TemporaryDirectory(prefix="bioql_mesh_") as tmp:
        pdb_path, obj, ssf, script = (
            os.path.join(tmp, n) for n in ("m.pdb", "m.obj", "ss.json", "run.py")
        )
        with open(pdb_path, "w") as fh:
            fh.write(pdb)
        with open(script, "w") as fh:
            fh.write(
                _SCRIPT.format(
                    pdb=pdb_path,
                    obj=obj,
                    ssf=ssf,
                    sampling=int(sampling),
                    is_protein=kind == "protein",
                )
            )
        try:
            r = subprocess.run(
                [exe, "-cq", script], capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            last_error = f"PyMOL took longer than {timeout} s"
            return None
        if not os.path.exists(obj) or os.path.getsize(obj) == 0:
            last_error = f"PyMOL produced no mesh: {(r.stderr or r.stdout)[-300:]}"
            return None
        try:
            meta, blob = pack(obj, center, anchors)
        except Exception as e:
            last_error = f"packing failed: {type(e).__name__}: {e}"
            return None
        ss_by_key = {}
        if os.path.exists(ssf):
            try:
                ss_by_key = json.load(open(ssf))
            except ValueError:
                ss_by_key = {}
    bvals = [r["b"] for r in res]
    known = [b for b in bvals if b is not None]
    b_scale = 100.0 if known and max(known) <= 1.0 else 1.0
    meta.update(
        {
            "b64": base64.b64encode(blob).decode("ascii"),
            "kind": kind,
            "center": [round(float(x), 3) for x in center],
            "n_res": len(res),
            "res": [
                {
                    "chain": r["chain"],
                    "resi": r["resi"],
                    "resn": r["resn"],
                    "ss": (ss_by_key.get(f"{r['chain']}:{r['resi']}") or "L")[:1] or "L",
                    "b": None if r["b"] is None else round(r["b"] * b_scale, 2),
                    "p": [round(float(x - c), 3) for x, c in zip(r["p"], center)],
                }
                for r in res
            ],
            "gz_bytes": len(blob),
        }
    )
    return meta


# MOLEVERA / BIOQL
