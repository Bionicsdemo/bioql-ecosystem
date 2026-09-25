"""
The ray-traced still that opens a report.

A WebGL mesh is honest but it is not what a structure looks like in a paper. PyMOL's
own ray tracer is, so every report opens on one: the same structure the live scene
then draws, rendered once at build time and inlined as a data URI, so the page needs
no second request and works from a file.

Choices behind the numbers, since they are trade-offs rather than defaults:
  * 1280x860 at ray_trace_mode 0 with a 2x oversample lands a protein at roughly
    120-260 kB of PNG after quantisation -- large enough to fill a laptop stage,
    small enough that a report with three structures stays under a megabyte of
    image. Bigger sizes gain little: the still is shown at most 78% of the stage.
  * The background is a flat near-black matching the page (#0a0f14) rather than
    transparent: a transparent PNG of a ray trace carries its own antialiased edge,
    which fringes against any other background.
  * Ambient occlusion on, specular low, depth cue off. Depth cue fogs the far side of
    a fold into the background, which reads as detail loss rather than depth in a
    still this size.

PyMOL runs as a subprocess, so a crash, a missing PyMOL or a structure it dislikes
costs the poster and nothing else: `poster()` returns None and puts the reason in
`last_error`.

MOLEVERA / BIOQL
"""

import base64
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional

from .mesh import pymol_binary, residues

last_error: Optional[str] = None

# One recipe per style. `cartoon` is the fold; `surface` is the shape a ligand sees.
STYLES = {
    "cartoon": """
cmd.hide("everything")
cmd.show("cartoon", "polymer")
cmd.set("cartoon_fancy_helices", 1)
cmd.set("cartoon_smooth_loops", 1)
cmd.set("cartoon_highlight_color", "grey70")
cmd.set("cartoon_discrete_colors", 0)
cmd.set("cartoon_sampling", 14)
cmd.set("cartoon_ring_mode", 3)
cmd.set("cartoon_ring_finder", 1)
cmd.set("cartoon_nucleic_acid_mode", 4)
cmd.spectrum("count", "deepblue white orange", "polymer and name CA+C4'")
""",
    "surface": """
cmd.hide("everything")
cmd.show("surface", "polymer")
cmd.set("surface_quality", 1)
cmd.set("transparency", 0.08)
cmd.set("solvent_radius", 1.6)
cmd.color("grey70", "polymer")
cmd.spectrum("b", "blue_white_red", "polymer") if cmd.count_atoms("polymer and not b=0") else None
""",
}

_SCRIPT = r"""
from pymol import cmd
cmd.load({pdb!r}, "m")
cmd.remove("solvent or inorganic or (hetatm and not polymer)")
{style}
cmd.bg_color("bgcol")
cmd.set("ray_opaque_background", 1)
cmd.set("antialias", 2)
cmd.set("ray_trace_mode", 0)
cmd.set("ray_shadows", 0)
cmd.set("ambient", 0.18)
cmd.set("direct", 0.45)
cmd.set("reflect", 0.30)
cmd.set("specular", 0.12)
cmd.set("shininess", 22)
cmd.set("ambient_occlusion_mode", 1)
cmd.set("ambient_occlusion_scale", 12.0)
cmd.set("ambient_occlusion_smooth", 12)
cmd.set("depth_cue", 0)
cmd.set("ray_trace_fog", 0)
cmd.set("orthoscopic", 0)
cmd.set("field_of_view", 22)
cmd.orient("polymer")
cmd.zoom("polymer", {pad})
cmd.ray({w}, {h})
cmd.png({png!r}, dpi=150)
print("PYMOL_VERSION=%s" % cmd.get_version()[0])
"""


def _bg_color(hex_rgb: str) -> str:
    """A PyMOL colour definition for the page's own background."""
    h = hex_rgb.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return f'cmd.set_color("bgcol", [{r:.4f}, {g:.4f}, {b:.4f}])\n'


def _shrink(png: bytes, max_bytes: int) -> bytes:
    """Quantise to a palette if the PNG is over budget. Without Pillow, leave it be."""
    if len(png) <= max_bytes:
        return png
    try:
        import io

        from PIL import Image

        im = Image.open(io.BytesIO(png)).convert("RGB")
        for colors in (256, 192, 128, 96, 64):
            buf = io.BytesIO()
            im.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE).save(
                buf, format="PNG", optimize=True
            )
            if buf.tell() <= max_bytes:
                return buf.getvalue()
        return buf.getvalue()
    except Exception:
        return png


def poster(
    pdb: str,
    *,
    width: int = 1280,
    height: int = 860,
    style: str = "cartoon",
    background: str = "#0a0f14",
    pad: float = 3.0,
    max_bytes: int = 900_000,
    timeout: int = 300,
) -> Optional[Dict[str, Any]]:
    """A ray-traced PNG of one structure, base64-encoded, or None.

    Returns {"b64", "width", "height", "bytes", "style", "n_res", "kind",
    "pymol_version", "quantised"}; the reason for a None is in `last_error`.
    """
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
    recipe = STYLES.get(style)
    if recipe is None:
        last_error = f"unknown style {style!r}; known: {', '.join(sorted(STYLES))}"
        return None

    with tempfile.TemporaryDirectory(prefix="bioql_poster_") as tmp:
        pdb_path = os.path.join(tmp, "m.pdb")
        png_path = os.path.join(tmp, "m.png")
        script = os.path.join(tmp, "run.py")
        with open(pdb_path, "w") as fh:
            fh.write(pdb)
        with open(script, "w") as fh:
            fh.write(
                _SCRIPT.format(
                    pdb=pdb_path,
                    style=_bg_color(background) + recipe,
                    png=png_path,
                    w=int(width),
                    h=int(height),
                    pad=float(pad),
                )
            )
        try:
            proc = subprocess.run(
                [exe, "-cq", script], capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            last_error = f"PyMOL took longer than {timeout} s to ray trace"
            return None
        if not os.path.exists(png_path) or os.path.getsize(png_path) == 0:
            last_error = f"PyMOL produced no image: {(proc.stderr or proc.stdout)[-300:]}"
            return None
        raw = open(png_path, "rb").read()

    version = ""
    for line in (proc.stdout or "").splitlines():
        if line.startswith("PYMOL_VERSION="):
            version = line.split("=", 1)[1].strip()
    small = _shrink(raw, max_bytes)
    return {
        "b64": base64.b64encode(small).decode("ascii"),
        "width": int(width),
        "height": int(height),
        "bytes": len(small),
        "style": style,
        "kind": kind,
        "n_res": len(res),
        "pymol_version": version,
        "quantised": len(small) != len(raw),
    }


if __name__ == "__main__":  # a human should look at the result, not just its size
    import json
    import sys
    import time

    src = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.expanduser("~/.bioql/artifacts/ps-2ce50c85d5be/result.json")
    )
    d = json.load(open(src))
    pdb = d.get("structure_3d", {}).get("pdb") or ""
    t = time.time()
    img = poster(pdb)
    if not img:
        print("no poster:", last_error)
        raise SystemExit(1)
    out = "/tmp/bioql_poster.png"
    open(out, "wb").write(base64.b64decode(img["b64"]))
    print(
        f"{img['n_res']} {img['kind']} residues · {img['bytes'] / 1024:.0f} KB"
        f"{' (quantised)' if img['quantised'] else ''} · PyMOL {img['pymol_version']}"
        f" · {time.time() - t:.1f} s -> {out}"
    )

# MOLEVERA / BIOQL
