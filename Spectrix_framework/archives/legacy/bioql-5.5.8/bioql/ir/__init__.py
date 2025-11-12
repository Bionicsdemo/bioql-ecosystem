"""
BioQL Intermediate Representation (IR) Module

This module provides the core IR schema and validation utilities for BioQL.
"""

from .schema import (
    BioQLDomain,
    BioQLOperation,
    BioQLParameter,
    BioQLProgram,
    BioQLResult,
    DataType,
    DockingOperation,
    AlignmentOperation,
    Molecule,
    QuantumBackend,
    QuantumCircuit,
    QuantumGate,
    QuantumOptimizationOperation,
)
from .validators import (
    BioQLValidationError,
    ComplianceValidator,
    SchemaGenerator,
    SchemaValidator,
    compliance_validator,
    schema_generator,
    validator,
)

__all__ = [
    # Schema classes
    "BioQLDomain",
    "BioQLOperation",
    "BioQLParameter",
    "BioQLProgram",
    "BioQLResult",
    "DataType",
    "DockingOperation",
    "AlignmentOperation",
    "Molecule",
    "QuantumBackend",
    "QuantumCircuit",
    "QuantumGate",
    "QuantumOptimizationOperation",
    # Validation classes and instances
    "BioQLValidationError",
    "ComplianceValidator",
    "SchemaGenerator",
    "SchemaValidator",
    "compliance_validator",
    "schema_generator",
    "validator",
]