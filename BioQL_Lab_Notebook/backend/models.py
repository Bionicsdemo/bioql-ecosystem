# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Database Models for BioQL Lab Notebook
"""

from datetime import datetime

from app import db

# Association table for many-to-many relationship between experiments and tags
experiment_tags = db.Table(
    "experiment_tags",
    db.Column("experiment_id", db.Integer, db.ForeignKey("experiment.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class Experiment(db.Model):
    """Experiment model representing a lab notebook experiment"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        db.String(50), default="planning"
    )  # planning, in-progress, completed, on-hold, archived

    # Experiment details
    objective = db.Column(db.Text)
    hypothesis = db.Column(db.Text)
    materials = db.Column(db.Text)
    protocol_steps = db.Column(db.Text)  # JSON string of protocol steps

    # Results
    observations = db.Column(db.Text)
    analysis = db.Column(db.Text)
    conclusions = db.Column(db.Text)
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))

    # Relationships
    tags = db.relationship(
        "Tag", secondary=experiment_tags, backref=db.backref("experiments", lazy="dynamic")
    )
    attachments = db.relationship(
        "Attachment", backref="experiment", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Convert experiment to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "objective": self.objective,
            "hypothesis": self.hypothesis,
            "materials": self.materials,
            "protocol_steps": self.protocol_steps,
            "observations": self.observations,
            "analysis": self.analysis,
            "conclusions": self.conclusions,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "tags": [tag.name for tag in self.tags],
            "attachments": [att.to_dict() for att in self.attachments],
        }


class Protocol(db.Model):
    """Protocol model for reusable experimental procedures"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.Text)  # Detailed protocol steps
    category = db.Column(db.String(100))
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))

    def to_dict(self):
        """Convert protocol to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "steps": self.steps,
            "category": self.category,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Sample(db.Model):
    """Sample model for tracking biological samples"""

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    sample_type = db.Column(db.String(100))  # tissue, DNA, RNA, protein, cells, etc.
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Available")  # Available, In Use, Depleted
    quantity = db.Column(db.String(100))
    concentration = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    def to_dict(self):
        """Convert sample to dictionary"""
        return {
            "id": self.id,
            "sample_id": self.sample_id,
            "name": self.name,
            "sample_type": self.sample_type,
            "description": self.description,
            "location": self.location,
            "status": self.status,
            "quantity": self.quantity,
            "concentration": self.concentration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "notes": self.notes,
        }


class Tag(db.Model):
    """Tag model for categorizing experiments"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert tag to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "count": self.experiments.count(),
        }


class Attachment(db.Model):
    """Attachment model for files associated with experiments"""

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey("experiment.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)

    def to_dict(self):
        """Convert attachment to dictionary"""
        return {
            "id": self.id,
            "filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "description": self.description,
        }


class User(db.Model):
    """User model for authentication and authorization"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    full_name = db.Column(db.String(200))
    role = db.Column(db.String(50), default="researcher")  # researcher, admin, viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
