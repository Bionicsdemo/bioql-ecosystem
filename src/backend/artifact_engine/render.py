"""
One run in, one self-contained page out.

`render()` builds the report payload (build.py), draws the PyMOL meshes
(mesh.py) and inlines both into the page shell, so the file that lands in
~/.bioql/artifacts/<session>/ opens anywhere with no server behind it: the
result, the meshes, the sentences and the data annex all travel inside it.

Only Three.js is fetched from a CDN. Everything else is in the file.

MOLEVERA / BIOQL
"""

import json
import math
import os
import time
from typing import Any, Dict, Optional

from . import build as _build
from . import mesh as _mesh

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "page")
ARTIFACTS = os.path.expanduser(os.environ.get("BIOQL_ARTIFACTS_DIR", "~/.bioql/artifacts"))


def _finite(v: Any) -> Any:
    """NaN and the infinities, which JSON has no words for, written as null.

    `json.dumps` emits the bare tokens `NaN` and `Infinity` by default. No browser's
    `JSON.parse` accepts either, so one non-finite number anywhere in a run threw at
    the very top of the page and left the reader a blank screen -- which is how the
    modality comparison report, whose run carries a NaN composite score, had been
    arriving. Null is what the rest of the page already reads as "not in this run".
    """
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_finite(x) for x in v]
    return v


def _safe_json(payload: Dict[str, Any]) -> str:
    """JSON for a <script type="application/json"> block: no tag can escape it."""
    return (
        # allow_nan=False makes anything _finite missed fail the build loudly, rather
        # than ship a page that cannot start
        json.dumps(_finite(payload), ensure_ascii=False, default=str, allow_nan=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render(
    result: Dict[str, Any], session_id: str = "", meshes: bool = True, mesh_timeout: int = 240
) -> Dict[str, Any]:
    """Build the payload and the page. Returns {payload, html, summary}."""

    def mesh_fn(pdb: str) -> Optional[Dict[str, Any]]:
        return _mesh.cartoon(pdb, timeout=mesh_timeout)

    payload = _build.build(
        result, mesh_fn=mesh_fn if meshes else None, session_id=session_id, want_meshes=meshes
    )
    shell = open(os.path.join(PAGE, "shell.html"), encoding="utf-8").read()
    app = open(os.path.join(PAGE, "report.js"), encoding="utf-8").read()
    # the document's own language is English, like the report it opens on
    title = f"{payload['title']['en']} · {payload.get('subject') or payload['pipeline']}"
    html = (
        shell.replace("__TITLE__", title.replace("<", "&lt;"))
        .replace("__PAYLOAD__", _safe_json(payload))
        .replace("__APP__", app)
    )
    return {
        "payload": payload,
        "html": html,
        "summary": _build.summary(payload),
        "title": title,
        "bytes": len(html.encode("utf-8")),
    }


def render_to_file(
    result: Dict[str, Any], session_id: str, name: str = "report.html", **kw
) -> Dict[str, Any]:
    """Render and save under the session's artifact directory; returns its served URL."""
    out = render(result, session_id=session_id, **kw)
    d = os.path.join(ARTIFACTS, session_id or time.strftime("run-%Y%m%d-%H%M%S"))
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(out["html"])
    out["path"] = path
    out["url"] = f"/api/artifacts/{os.path.basename(d)}/{name}"
    out["session_id"] = os.path.basename(d)
    return out


# MOLEVERA / BIOQL
