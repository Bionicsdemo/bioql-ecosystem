# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Lab Notebook - Flask Backend Application
Main entry point for the Flask API server
"""

import os
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bioql_lab_notebook.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
CORS(app)
db = SQLAlchemy(app)

# Import models and routes after db initialization
from models import Experiment, Protocol, Sample, Tag
from routes import api_bp

# Register blueprints
app.register_blueprint(api_bp, url_prefix="/api")


# Serve frontend files
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    # Try to serve from frontend first
    if os.path.exists(f"../frontend/{path}"):
        return send_from_directory("../frontend", path)
    # Then try static
    elif os.path.exists(f"../static/{path}"):
        return send_from_directory("../static", path)
    # Then try js
    elif os.path.exists(f"../js/{path}"):
        return send_from_directory("../js", path)
    else:
        return jsonify({"error": "File not found"}), 404


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


# Database initialization
@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print("Database initialized.")


@app.cli.command()
def seed_db():
    """Seed the database with sample data."""
    # Clear existing data
    db.drop_all()
    db.create_all()

    # Create sample tags
    tags = [
        Tag(name="PCR"),
        Tag(name="western-blot"),
        Tag(name="cell-culture"),
        Tag(name="molecular-biology"),
        Tag(name="protein"),
        Tag(name="DNA-extraction"),
        Tag(name="ELISA"),
        Tag(name="immunology"),
    ]
    db.session.add_all(tags)

    # Create sample experiments
    experiments = [
        Experiment(
            title="PCR Amplification of Gene X",
            description="Amplifying the target gene region for sequencing analysis",
            status="completed",
            objective="Amplify the target gene region for downstream sequencing",
            hypothesis="The PCR will successfully amplify a 500bp fragment",
            materials="DNA template, primers, Taq polymerase, dNTPs, PCR buffer",
            observations="Clear band observed at expected size",
            analysis="PCR successfully amplified the target region",
            conclusions="The optimized PCR protocol works reliably for this target",
            notes="Consider increasing annealing temperature for better specificity",
            created_at=datetime(2024, 1, 15),
        ),
        Experiment(
            title="Western Blot Analysis - Protein Expression",
            description="Analyzing protein expression levels in treated vs control samples",
            status="in-progress",
            objective="Compare protein expression between treatment groups",
            hypothesis="Treatment will increase target protein expression by 2-fold",
            materials="Protein samples, antibodies, PVDF membrane, ECL reagent",
            created_at=datetime(2024, 1, 18),
        ),
        Experiment(
            title="Cell Culture Optimization",
            description="Testing different media conditions for optimal cell growth",
            status="planning",
            objective="Optimize growth conditions for maximum cell viability",
            created_at=datetime(2024, 1, 20),
        ),
    ]
    db.session.add_all(experiments)

    # Create sample protocols
    protocols = [
        Protocol(
            title="Standard PCR Protocol",
            description="General purpose PCR amplification",
            steps="1. Prepare master mix\n2. Add template DNA\n3. Run PCR cycle\n4. Analyze results",
            usage_count=25,
        ),
        Protocol(
            title="Western Blot Protocol",
            description="Protein detection via immunoblotting",
            steps="1. Sample preparation\n2. Gel electrophoresis\n3. Transfer\n4. Blocking\n5. Antibody incubation\n6. Detection",
            usage_count=15,
        ),
    ]
    db.session.add_all(protocols)

    # Create sample samples
    samples = [
        Sample(
            sample_id="S001",
            name="Tissue Sample A",
            sample_type="Tissue",
            location="Freezer -80C, Box 3",
            status="Available",
        ),
        Sample(
            sample_id="S002",
            name="DNA Extract B",
            sample_type="DNA",
            location="Fridge 4C, Rack 2",
            status="Available",
        ),
    ]
    db.session.add_all(samples)

    db.session.commit()
    print("Database seeded with sample data.")


if __name__ == "__main__":
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Run the development server
    app.run(debug=True, host="0.0.0.0", port=5000)
