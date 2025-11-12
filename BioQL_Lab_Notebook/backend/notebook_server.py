# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Lab Notebook Backend Server
Flask REST API for managing lab notebooks and integrating with BioQL workflows
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

import requests
from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from loguru import logger

# Configuration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "bioql-lab-notebook-secret-key-change-in-production"
)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database configuration
DB_PATH = Path(__file__).parent / "notebooks.db"
BIOQL_API_URL = "http://167.71.86.90:5002"

# Logging configuration
logger.add("notebook_server.log", rotation="10 MB", retention="10 days", level="INFO")


# Database initialization
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Notebooks table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notebooks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Executions table for tracking BioQL command executions
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,
            notebook_id TEXT NOT NULL,
            command TEXT NOT NULL,
            result TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (notebook_id) REFERENCES notebooks (id)
        )
    """
    )

    # Templates table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            content TEXT NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Insert default templates
    default_templates = [
        {
            "id": str(uuid.uuid4()),
            "name": "Protein Analysis",
            "description": "Template for protein structure and function analysis",
            "content": json.dumps(
                {
                    "sections": [
                        {"title": "Objective", "content": ""},
                        {
                            "title": "Protein Selection",
                            "content": "@bioql get protein [PROTEIN_NAME]",
                        },
                        {"title": "Structure Analysis", "content": "@bioql analyze structure"},
                        {"title": "Function Prediction", "content": "@bioql predict function"},
                        {"title": "Results", "content": ""},
                        {"title": "Conclusion", "content": ""},
                    ]
                }
            ),
            "category": "protein",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Gene Expression Study",
            "description": "Template for analyzing gene expression patterns",
            "content": json.dumps(
                {
                    "sections": [
                        {"title": "Research Question", "content": ""},
                        {"title": "Gene Selection", "content": "@bioql search genes [KEYWORDS]"},
                        {"title": "Expression Analysis", "content": "@bioql analyze expression"},
                        {"title": "Pathway Enrichment", "content": "@bioql enrichment analysis"},
                        {"title": "Visualization", "content": "@bioql visualize heatmap"},
                        {"title": "Discussion", "content": ""},
                    ]
                }
            ),
            "category": "genomics",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Drug Discovery Pipeline",
            "description": "Template for drug discovery and screening workflows",
            "content": json.dumps(
                {
                    "sections": [
                        {"title": "Target Identification", "content": "@bioql identify target"},
                        {"title": "Compound Screening", "content": "@bioql screen compounds"},
                        {"title": "Binding Affinity", "content": "@bioql calculate binding"},
                        {"title": "ADMET Analysis", "content": "@bioql predict admet"},
                        {"title": "Lead Optimization", "content": ""},
                        {"title": "Results Summary", "content": ""},
                    ]
                }
            ),
            "category": "drug_discovery",
        },
    ]

    for template in default_templates:
        cursor.execute(
            """
            INSERT OR IGNORE INTO templates (id, name, description, content, category)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                template["id"],
                template["name"],
                template["description"],
                template["content"],
                template["category"],
            ),
        )

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# Database helper functions
def get_db():
    """Get database connection"""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Authentication decorator
def require_api_key(f):
    """Decorator to require API key authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            logger.warning("Request without API key")
            return jsonify({"error": "API key required"}), 401

        # In production, validate against stored API keys
        # For now, accept any non-empty API key
        g.user_id = api_key  # Using API key as user_id for simplicity
        return f(*args, **kwargs)

    return decorated_function


# Notebook endpoints
@app.route("/api/notebook/create", methods=["POST"])
@require_api_key
def create_notebook():
    """Create a new notebook"""
    try:
        data = request.json
        title = data.get("title", "Untitled Notebook")
        content = data.get("content", "")
        metadata = data.get("metadata", {})

        notebook_id = str(uuid.uuid4())
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO notebooks (id, user_id, title, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """,
            (notebook_id, g.user_id, title, content, json.dumps(metadata)),
        )

        db.commit()

        logger.info(f"Created notebook {notebook_id} for user {g.user_id}")

        return (
            jsonify(
                {
                    "id": notebook_id,
                    "title": title,
                    "content": content,
                    "metadata": metadata,
                    "created_at": datetime.utcnow().isoformat(),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating notebook: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notebook/<notebook_id>", methods=["GET"])
@require_api_key
def get_notebook(notebook_id):
    """Get a specific notebook"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT * FROM notebooks
            WHERE id = ? AND user_id = ?
        """,
            (notebook_id, g.user_id),
        )

        notebook = cursor.fetchone()

        if not notebook:
            return jsonify({"error": "Notebook not found"}), 404

        return jsonify(
            {
                "id": notebook["id"],
                "user_id": notebook["user_id"],
                "title": notebook["title"],
                "content": notebook["content"],
                "metadata": json.loads(notebook["metadata"]) if notebook["metadata"] else {},
                "created_at": notebook["created_at"],
                "updated_at": notebook["updated_at"],
            }
        )

    except Exception as e:
        logger.error(f"Error getting notebook {notebook_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notebook/<notebook_id>", methods=["PUT"])
@require_api_key
def update_notebook(notebook_id):
    """Update a notebook"""
    try:
        data = request.json
        db = get_db()
        cursor = db.cursor()

        # Check if notebook exists and belongs to user
        cursor.execute(
            """
            SELECT id FROM notebooks
            WHERE id = ? AND user_id = ?
        """,
            (notebook_id, g.user_id),
        )

        if not cursor.fetchone():
            return jsonify({"error": "Notebook not found"}), 404

        # Update notebook
        title = data.get("title")
        content = data.get("content")
        metadata = data.get("metadata")

        update_fields = []
        update_values = []

        if title is not None:
            update_fields.append("title = ?")
            update_values.append(title)

        if content is not None:
            update_fields.append("content = ?")
            update_values.append(content)

        if metadata is not None:
            update_fields.append("metadata = ?")
            update_values.append(json.dumps(metadata))

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.extend([notebook_id, g.user_id])

        cursor.execute(
            f"""
            UPDATE notebooks
            SET {', '.join(update_fields)}
            WHERE id = ? AND user_id = ?
        """,
            update_values,
        )

        db.commit()

        logger.info(f"Updated notebook {notebook_id}")

        # Broadcast update to collaborators via WebSocket
        socketio.emit(
            "notebook_updated",
            {"notebook_id": notebook_id, "updated_at": datetime.utcnow().isoformat()},
            room=notebook_id,
        )

        return jsonify({"message": "Notebook updated successfully"})

    except Exception as e:
        logger.error(f"Error updating notebook {notebook_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notebook/<notebook_id>", methods=["DELETE"])
@require_api_key
def delete_notebook(notebook_id):
    """Delete a notebook"""
    try:
        db = get_db()
        cursor = db.cursor()

        # Check if notebook exists and belongs to user
        cursor.execute(
            """
            SELECT id FROM notebooks
            WHERE id = ? AND user_id = ?
        """,
            (notebook_id, g.user_id),
        )

        if not cursor.fetchone():
            return jsonify({"error": "Notebook not found"}), 404

        # Delete notebook and associated executions
        cursor.execute("DELETE FROM executions WHERE notebook_id = ?", (notebook_id,))
        cursor.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))

        db.commit()

        logger.info(f"Deleted notebook {notebook_id}")

        return jsonify({"message": "Notebook deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting notebook {notebook_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notebooks", methods=["GET"])
@require_api_key
def list_notebooks():
    """List all notebooks for the user"""
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id, title, created_at, updated_at, metadata
            FROM notebooks
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """,
            (g.user_id,),
        )

        notebooks = cursor.fetchall()

        return jsonify(
            {
                "notebooks": [
                    {
                        "id": nb["id"],
                        "title": nb["title"],
                        "created_at": nb["created_at"],
                        "updated_at": nb["updated_at"],
                        "metadata": json.loads(nb["metadata"]) if nb["metadata"] else {},
                    }
                    for nb in notebooks
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error listing notebooks: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/execute", methods=["POST"])
@require_api_key
def execute_bioql():
    """Execute a BioQL command"""
    try:
        data = request.json
        command = data.get("command", "")
        notebook_id = data.get("notebook_id")

        if not command:
            return jsonify({"error": "Command is required"}), 400

        # Remove @bioql prefix if present
        command = command.strip()
        if command.startswith("@bioql"):
            command = command[6:].strip()

        logger.info(f"Executing BioQL command: {command}")

        # Call BioQL API
        try:
            response = requests.post(
                f"{BIOQL_API_URL}/api/execute", json={"query": command}, timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                status = "success"
            else:
                result = {"error": response.text}
                status = "error"

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling BioQL API: {str(e)}")
            result = {"error": f"Failed to connect to BioQL API: {str(e)}"}
            status = "error"

        # Store execution in database if notebook_id provided
        if notebook_id:
            execution_id = str(uuid.uuid4())
            db = get_db()
            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO executions (id, notebook_id, command, result, status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (execution_id, notebook_id, command, json.dumps(result), status),
            )

            db.commit()

        return jsonify(
            {
                "status": status,
                "command": command,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error executing BioQL command: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/paper", methods=["POST"])
@require_api_key
def export_paper():
    """Generate a paper/report from notebook content"""
    try:
        data = request.json
        notebook_id = data.get("notebook_id")
        format_type = data.get("format", "markdown")  # markdown, latex, pdf

        if not notebook_id:
            return jsonify({"error": "notebook_id is required"}), 400

        # Get notebook
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT * FROM notebooks
            WHERE id = ? AND user_id = ?
        """,
            (notebook_id, g.user_id),
        )

        notebook = cursor.fetchone()

        if not notebook:
            return jsonify({"error": "Notebook not found"}), 404

        # Get executions for this notebook
        cursor.execute(
            """
            SELECT * FROM executions
            WHERE notebook_id = ?
            ORDER BY created_at ASC
        """,
            (notebook_id,),
        )

        executions = cursor.fetchall()

        # Generate paper content
        paper_content = f"# {notebook['title']}\n\n"
        paper_content += f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        paper_content += "---\n\n"
        paper_content += "## Notebook Content\n\n"
        paper_content += notebook["content"] + "\n\n"

        if executions:
            paper_content += "## Executed Commands\n\n"
            for i, exec_row in enumerate(executions, 1):
                paper_content += f"### Command {i}\n\n"
                paper_content += f"**Command:** `@bioql {exec_row['command']}`\n\n"
                paper_content += f"**Status:** {exec_row['status']}\n\n"

                if exec_row["result"]:
                    paper_content += "**Result:**\n\n"
                    paper_content += "```json\n"
                    paper_content += json.dumps(json.loads(exec_row["result"]), indent=2)
                    paper_content += "\n```\n\n"

                paper_content += f"**Executed at:** {exec_row['created_at']}\n\n"
                paper_content += "---\n\n"

        # Add metadata
        if notebook["metadata"]:
            metadata = json.loads(notebook["metadata"])
            if metadata:
                paper_content += "## Metadata\n\n"
                for key, value in metadata.items():
                    paper_content += f"- **{key}:** {value}\n"
                paper_content += "\n"

        logger.info(f"Generated paper from notebook {notebook_id}")

        return jsonify(
            {
                "format": format_type,
                "content": paper_content,
                "filename": f"{notebook['title'].replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.md",
            }
        )

    except Exception as e:
        logger.error(f"Error exporting paper: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/templates", methods=["GET"])
def get_templates():
    """Get experiment templates"""
    try:
        db = get_db()
        cursor = db.cursor()

        category = request.args.get("category")

        if category:
            cursor.execute(
                """
                SELECT * FROM templates
                WHERE category = ?
                ORDER BY name ASC
            """,
                (category,),
            )
        else:
            cursor.execute("SELECT * FROM templates ORDER BY category, name ASC")

        templates = cursor.fetchall()

        return jsonify(
            {
                "templates": [
                    {
                        "id": t["id"],
                        "name": t["name"],
                        "description": t["description"],
                        "content": json.loads(t["content"]),
                        "category": t["category"],
                        "created_at": t["created_at"],
                    }
                    for t in templates
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        return jsonify({"error": str(e)}), 500


# WebSocket events for real-time collaboration
@socketio.on("join_notebook")
def handle_join_notebook(data):
    """Join a notebook room for real-time collaboration"""
    notebook_id = data.get("notebook_id")
    user_id = data.get("user_id")

    if notebook_id:
        join_room(notebook_id)
        emit(
            "user_joined",
            {
                "user_id": user_id,
                "notebook_id": notebook_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=notebook_id,
        )

        logger.info(f"User {user_id} joined notebook {notebook_id}")


@socketio.on("leave_notebook")
def handle_leave_notebook(data):
    """Leave a notebook room"""
    notebook_id = data.get("notebook_id")
    user_id = data.get("user_id")

    if notebook_id:
        leave_room(notebook_id)
        emit(
            "user_left",
            {
                "user_id": user_id,
                "notebook_id": notebook_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=notebook_id,
        )

        logger.info(f"User {user_id} left notebook {notebook_id}")


@socketio.on("notebook_edit")
def handle_notebook_edit(data):
    """Broadcast notebook edits to collaborators"""
    notebook_id = data.get("notebook_id")
    user_id = data.get("user_id")
    changes = data.get("changes")

    if notebook_id:
        emit(
            "notebook_changes",
            {"user_id": user_id, "changes": changes, "timestamp": datetime.utcnow().isoformat()},
            room=notebook_id,
            include_self=False,
        )


@socketio.on("cursor_position")
def handle_cursor_position(data):
    """Broadcast cursor position for collaborative editing"""
    notebook_id = data.get("notebook_id")
    user_id = data.get("user_id")
    position = data.get("position")

    if notebook_id:
        emit(
            "cursor_update",
            {"user_id": user_id, "position": position},
            room=notebook_id,
            include_self=False,
        )


@app.route("/api/collaborate", methods=["POST"])
@require_api_key
def collaborate():
    """REST endpoint to initiate collaboration session"""
    try:
        data = request.json
        notebook_id = data.get("notebook_id")

        if not notebook_id:
            return jsonify({"error": "notebook_id is required"}), 400

        # Verify notebook exists and user has access
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id FROM notebooks
            WHERE id = ? AND user_id = ?
        """,
            (notebook_id, g.user_id),
        )

        if not cursor.fetchone():
            return jsonify({"error": "Notebook not found"}), 404

        # Generate collaboration session
        session_id = str(uuid.uuid4())

        return jsonify(
            {
                "session_id": session_id,
                "notebook_id": notebook_id,
                "websocket_url": f"ws://localhost:5003",
                "instructions": 'Connect to WebSocket and emit "join_notebook" event with notebook_id',
            }
        )

    except Exception as e:
        logger.error(f"Error creating collaboration session: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "service": "BioQL Lab Notebook API",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# Root endpoint
@app.route("/")
def index():
    """Serve the login page"""
    base_dir = Path(__file__).parent
    return send_from_directory(base_dir / "frontend", "login.html")


@app.route("/<path:filename>")
def serve_static(filename):
    """Serve static files from frontend, js, and static directories"""
    base_dir = Path(__file__).parent

    # Try frontend directory first
    frontend_path = base_dir / "frontend" / filename
    if frontend_path.exists() and frontend_path.is_file():
        return send_from_directory(base_dir / "frontend", filename)

    # Try js directory
    js_path = base_dir / "js" / filename
    if js_path.exists() and js_path.is_file():
        return send_from_directory(base_dir / "js", filename)

    # Try static directory
    static_path = base_dir / "static" / filename
    if static_path.exists() and static_path.is_file():
        return send_from_directory(base_dir / "static", filename)

    # Return 404 if not found
    return "File not found", 404


@app.route("/api/info", methods=["GET"])
def api_info():
    """API information endpoint"""
    return jsonify(
        {
            "service": "BioQL Lab Notebook API",
            "version": "1.0.0",
            "endpoints": {
                "notebooks": {
                    "POST /api/notebook/create": "Create new notebook",
                    "GET /api/notebook/<id>": "Get notebook",
                    "PUT /api/notebook/<id>": "Update notebook",
                    "DELETE /api/notebook/<id>": "Delete notebook",
                    "GET /api/notebooks": "List all user notebooks",
                },
                "execution": {"POST /api/execute": "Execute BioQL command"},
                "export": {"POST /api/export/paper": "Generate paper from notebook"},
                "templates": {"GET /api/templates": "Get experiment templates"},
                "collaboration": {"POST /api/collaborate": "Initiate collaboration session"},
                "health": {"GET /health": "Health check"},
            },
            "authentication": "Include X-API-Key header with all requests",
        }
    )


if __name__ == "__main__":
    # Initialize database
    init_db()

    logger.info("Starting BioQL Lab Notebook Server on port 5003")

    # Run server with SocketIO
    socketio.run(app, host="0.0.0.0", port=5003, debug=True)
