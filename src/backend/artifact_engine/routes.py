"""
Flask routes for the interactive report.

    POST /api/report/interactive   {result, session_id?, meshes?}  -> {url, summary, ...}
    GET  /api/report/interactive/health

Building one takes seconds (PyMOL runs once per structure), so the page is
written to the session's artifact directory and served by render_artifacts at
/api/artifacts/<session>/report.html -- the chat only needs the link.

The request carries a pipeline result the backend itself produced. Nothing is
fetched, and no model is called: the report is assembled from that JSON alone.

MOLEVERA / BIOQL
"""

import logging
import os
import threading
import time
from typing import Any, Dict

from flask import Blueprint, jsonify, request

log = logging.getLogger("artifact_engine")
report_bp = Blueprint("bioql_interactive_report", __name__)
_CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:3000")
_MAX_CONCURRENT = int(os.environ.get("BIOQL_REPORT_WORKERS", "2"))
_slots = threading.Semaphore(_MAX_CONCURRENT)


def _cors(resp):
    resp.headers.add("Access-Control-Allow-Origin", _CORS_ORIGIN)
    resp.headers.add("Access-Control-Allow-Headers", "*")
    resp.headers.add("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    return resp


@report_bp.route("/api/report/interactive", methods=["POST", "OPTIONS"])
def api_interactive_report():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    data = request.get_json(silent=True) or {}
    result = data.get("result") if isinstance(data.get("result"), dict) else data
    if not isinstance(result, dict) or not result:
        return _cors(jsonify({"success": False, "error": "send the pipeline result as JSON"})), 400

    session_id = str(data.get("session_id") or "").strip() or time.strftime("run-%Y%m%d-%H%M%S")
    session_id = os.path.basename(session_id)  # never escape the artifacts directory
    want_meshes = data.get("meshes", True) is not False

    if not _slots.acquire(blocking=False):
        return (
            _cors(
                jsonify(
                    {
                        "success": False,
                        "busy": True,
                        "error": f"{_MAX_CONCURRENT} reports are already being built; try again shortly",
                    }
                )
            ),
            429,
        )
    t0 = time.time()
    try:
        from artifact_engine import render

        out = render.render_to_file(result, session_id=session_id, meshes=want_meshes)
    except ValueError as e:
        return (
            _cors(
                jsonify(
                    {
                        "success": False,
                        "error": str(e),
                        "hint": "this pipeline has no artifact model yet",
                    }
                )
            ),
            422,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("interactive report failed")
        return (
            _cors(jsonify({"success": False, "error": f"{type(e).__name__}: {str(e)[:300]}"})),
            500,
        )
    finally:
        _slots.release()

    p = out["payload"]
    return _cors(
        jsonify(
            {
                "success": True,
                "url": out["url"],
                "session_id": out["session_id"],
                "title": out["title"],
                "summary": out["summary"],
                "pipeline": p["pipeline"],
                "digest": p["digest"],
                "bytes": out["bytes"],
                "chapters": [
                    {
                        "id": c["id"],
                        "title": c["title"],
                        "beats": len(c["beats"]),
                        "status": c["status"],
                    }
                    for c in p["chapters"]
                ],
                "coverage": p["coverage"],
                "checks": [{"id": c["id"], "ok": c["ok"]} for c in p["checks"]],
                "meshes": {
                    k: {"residues": v["n_res"], "triangles": v["nt"], "kind": v["kind"]}
                    for k, v in p["meshes"].items()
                },
                "mesh_notes": p["mesh_notes"],
                "elapsed_s": round(time.time() - t0, 1),
            }
        )
    )


@report_bp.route("/api/report/interactive/health", methods=["GET", "OPTIONS"])
def api_report_health():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    from artifact_engine import build, mesh

    return _cors(
        jsonify(
            {
                "success": True,
                "pipelines": [getattr(m, "PIPELINE", m.__name__) for m in build.MODELS],
                "pymol": mesh.pymol_binary() or "not found (structures will be reported as gaps)",
                "workers": _MAX_CONCURRENT,
                "artifacts_dir": os.path.expanduser(
                    os.environ.get("BIOQL_ARTIFACTS_DIR", "~/.bioql/artifacts")
                ),
            }
        )
    )


def register_interactive_report_routes(app):
    app.register_blueprint(report_bp)
    log.info("Interactive report routes registered (/api/report/interactive)")


# MOLEVERA / BIOQL
