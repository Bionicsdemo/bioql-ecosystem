"""
render_artifacts.py — Downloadable artifact store for BioQL.

Rendering already exists on this machine:
  * /api/render/pymol  (pymol_flask_endpoint.py — real PyMOL, returns `image`)
  * /api/render/protein_3d, /api/render/molecule_2d (molecular_renderer.py)

This module adds the MISSING piece: a served artifact store so every pipeline
result can be downloaded and opened in desktop tools (PyMOL, ChimeraX, Blender)
or the local web viewer (3Dmol.js). Files live under ~/.bioql/artifacts/<session>/
and are served at /api/artifacts/<session>/<file>.

Copyright (c) 2026 MOLEVERA / BIOQL. All rights reserved.
"""

from __future__ import annotations

import logging
import os

from flask import Blueprint, jsonify, request, send_from_directory

log = logging.getLogger("render_artifacts")
artifacts_bp = Blueprint("bioql_artifacts", __name__)

ARTIFACTS_DIR = os.path.expanduser("~/.bioql/artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
_CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:3000")


def _cors(resp):
    resp.headers.add("Access-Control-Allow-Origin", _CORS_ORIGIN)
    resp.headers.add("Access-Control-Allow-Headers", "*")
    resp.headers.add("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    return resp


def _session_dir(session_id: str) -> str:
    sid = "".join(c for c in (session_id or "default") if c.isalnum() or c in "-_") or "default"
    d = os.path.join(ARTIFACTS_DIR, sid)
    os.makedirs(d, exist_ok=True)
    return d


def save_artifact(session_id: str, filename: str, content, binary: bool = False) -> str:
    """Save an artifact, return its download URL. Importable by pipelines."""
    d = _session_dir(session_id)
    safe_name = os.path.basename(filename)
    path = os.path.join(d, safe_name)
    with open(path, "wb" if binary else "w") as f:
        f.write(content)
    return f"/api/artifacts/{os.path.basename(d)}/{safe_name}"


@artifacts_bp.route("/api/artifacts/save", methods=["POST", "OPTIONS"])
def api_save_artifact():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    data = request.get_json() or {}
    fn = data.get("filename")
    if not fn:
        return _cors(jsonify({"success": False, "error": "no filename"})), 400
    url = save_artifact(data.get("session_id", "default"), fn, data.get("content", ""))
    return _cors(jsonify({"success": True, "url": url}))


@artifacts_bp.route("/api/artifacts/<session_id>/<path:filename>", methods=["GET"])
def api_serve_artifact(session_id, filename):
    return send_from_directory(_session_dir(session_id), os.path.basename(filename))


@artifacts_bp.route("/api/artifacts/health", methods=["GET"])
def api_artifacts_health():
    return _cors(jsonify({"status": "ok", "artifacts_dir": ARTIFACTS_DIR}))


def register_render_artifact_routes(app):
    app.register_blueprint(artifacts_bp)
    log.info("Artifact store routes registered (/api/artifacts/*)")

    # The interactive report is an artifact too: it is written into this store and
    # served by the route above, so it registers here rather than in the server
    # monolith. A missing or broken engine costs the report, never the store.
    try:
        from artifact_engine.routes import register_interactive_report_routes

        register_interactive_report_routes(app)
    except Exception as e:  # noqa: BLE001
        log.warning("interactive report routes not registered: %s: %s", type(e).__name__, e)
