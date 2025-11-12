# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
API Routes for BioQL Lab Notebook
"""

import json
from datetime import datetime

from app import db
from flask import Blueprint, jsonify, request
from models import Experiment, Protocol, Sample, Tag

api_bp = Blueprint("api", __name__)


# Experiment Routes
@api_bp.route("/experiments", methods=["GET"])
def get_experiments():
    """Get all experiments"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return jsonify([exp.to_dict() for exp in experiments])


@api_bp.route("/experiments/<int:experiment_id>", methods=["GET"])
def get_experiment(experiment_id):
    """Get a specific experiment"""
    experiment = Experiment.query.get_or_404(experiment_id)
    return jsonify(experiment.to_dict())


@api_bp.route("/experiments", methods=["POST"])
def create_experiment():
    """Create a new experiment"""
    data = request.get_json()

    experiment = Experiment(
        title=data.get("title", ""),
        description=data.get("description", ""),
        status=data.get("status", "planning"),
        objective=data.get("objective", ""),
        hypothesis=data.get("hypothesis", ""),
        materials=data.get("materials", ""),
        protocol_steps=json.dumps(data.get("protocol", [])),
        observations=data.get("observations", ""),
        analysis=data.get("analysis", ""),
        conclusions=data.get("conclusions", ""),
        notes=data.get("notes", ""),
    )

    # Handle tags
    tag_names = data.get("tags", [])
    for tag_name in tag_names:
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
        experiment.tags.append(tag)

    db.session.add(experiment)
    db.session.commit()

    return jsonify(experiment.to_dict()), 201


@api_bp.route("/experiments/<int:experiment_id>", methods=["PUT"])
def update_experiment(experiment_id):
    """Update an existing experiment"""
    experiment = Experiment.query.get_or_404(experiment_id)
    data = request.get_json()

    # Update fields
    experiment.title = data.get("title", experiment.title)
    experiment.description = data.get("description", experiment.description)
    experiment.status = data.get("status", experiment.status)
    experiment.objective = data.get("objective", experiment.objective)
    experiment.hypothesis = data.get("hypothesis", experiment.hypothesis)
    experiment.materials = data.get("materials", experiment.materials)
    experiment.protocol_steps = json.dumps(data.get("protocol", []))
    experiment.observations = data.get("observations", experiment.observations)
    experiment.analysis = data.get("analysis", experiment.analysis)
    experiment.conclusions = data.get("conclusions", experiment.conclusions)
    experiment.notes = data.get("notes", experiment.notes)
    experiment.updated_at = datetime.utcnow()

    # Update tags
    if "tags" in data:
        experiment.tags.clear()
        for tag_name in data["tags"]:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            experiment.tags.append(tag)

    db.session.commit()
    return jsonify(experiment.to_dict())


@api_bp.route("/experiments/<int:experiment_id>", methods=["DELETE"])
def delete_experiment(experiment_id):
    """Delete an experiment"""
    experiment = Experiment.query.get_or_404(experiment_id)
    db.session.delete(experiment)
    db.session.commit()
    return jsonify({"message": "Experiment deleted successfully"}), 200


@api_bp.route("/experiments/recent", methods=["GET"])
def get_recent_experiments():
    """Get recent experiments"""
    limit = request.args.get("limit", 5, type=int)
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).limit(limit).all()
    return jsonify([exp.to_dict() for exp in experiments])


# Protocol Routes
@api_bp.route("/protocols", methods=["GET"])
def get_protocols():
    """Get all protocols"""
    protocols = Protocol.query.order_by(Protocol.title).all()
    return jsonify([protocol.to_dict() for protocol in protocols])


@api_bp.route("/protocols/<int:protocol_id>", methods=["GET"])
def get_protocol(protocol_id):
    """Get a specific protocol"""
    protocol = Protocol.query.get_or_404(protocol_id)
    return jsonify(protocol.to_dict())


@api_bp.route("/protocols", methods=["POST"])
def create_protocol():
    """Create a new protocol"""
    data = request.get_json()

    protocol = Protocol(
        title=data.get("title", ""),
        description=data.get("description", ""),
        steps=data.get("steps", ""),
        category=data.get("category", ""),
    )

    db.session.add(protocol)
    db.session.commit()

    return jsonify(protocol.to_dict()), 201


# Sample Routes
@api_bp.route("/samples", methods=["GET"])
def get_samples():
    """Get all samples"""
    samples = Sample.query.order_by(Sample.created_at.desc()).all()
    return jsonify([sample.to_dict() for sample in samples])


@api_bp.route("/samples/<int:sample_id>", methods=["GET"])
def get_sample(sample_id):
    """Get a specific sample"""
    sample = Sample.query.get_or_404(sample_id)
    return jsonify(sample.to_dict())


@api_bp.route("/samples", methods=["POST"])
def create_sample():
    """Create a new sample"""
    data = request.get_json()

    sample = Sample(
        sample_id=data.get("sample_id", ""),
        name=data.get("name", ""),
        sample_type=data.get("sample_type", ""),
        description=data.get("description", ""),
        location=data.get("location", ""),
        status=data.get("status", "Available"),
        quantity=data.get("quantity", ""),
        concentration=data.get("concentration", ""),
        notes=data.get("notes", ""),
    )

    db.session.add(sample)
    db.session.commit()

    return jsonify(sample.to_dict()), 201


# Tag Routes
@api_bp.route("/tags", methods=["GET"])
def get_tags():
    """Get all tags with usage counts"""
    tags = Tag.query.all()
    return jsonify([tag.to_dict() for tag in tags])


# Dashboard Routes
@api_bp.route("/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    """Get dashboard statistics"""
    total_experiments = Experiment.query.count()
    total_protocols = Protocol.query.count()
    total_samples = Sample.query.count()

    # Get recent activity (experiments from last 7 days)
    from datetime import timedelta

    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = Experiment.query.filter(Experiment.created_at >= week_ago).count()

    # Get recent activities
    recent_experiments = Experiment.query.order_by(Experiment.created_at.desc()).limit(5).all()
    activities = []
    for exp in recent_experiments:
        activities.append(
            {
                "action": (
                    "Experiment Created" if exp.status == "planning" else "Experiment Updated"
                ),
                "description": exp.title,
                "date": exp.created_at.isoformat(),
            }
        )

    return jsonify(
        {
            "totalExperiments": total_experiments,
            "totalProtocols": total_protocols,
            "totalSamples": total_samples,
            "recentActivity": recent_activity,
            "recentActivities": activities,
        }
    )


# BioQL Query Route
@api_bp.route("/bioql/query", methods=["POST"])
def execute_bioql_query():
    """Execute a BioQL query"""
    data = request.get_json()
    query = data.get("query", "")

    # Simple query parser (this would be much more sophisticated in production)
    # For now, just search in title and description
    search_terms = query.lower().split()

    results = []
    experiments = Experiment.query.all()

    for exp in experiments:
        title_lower = exp.title.lower()
        desc_lower = (exp.description or "").lower()

        if any(term in title_lower or term in desc_lower for term in search_terms):
            results.append(exp.to_dict())

    return jsonify(results)


# Health check
@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})
