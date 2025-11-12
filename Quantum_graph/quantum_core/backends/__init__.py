# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Quantum Backends Module
========================

Provides quantum execution infrastructure for Quantum_graph system.

Main Components:
- QuantumExecutor: Unified interface for executing circuits on multiple backends
- MolecularCircuitBuilder: Convert molecular data to quantum circuits
- BackendType: Enumeration of supported backends

Author: BioQL Team / Quantum_graph Integration
"""

from .circuit_builder import (
    CircuitBuilderError,
    MolecularCircuitBuilder,
    MolecularData,
    build_molecular_circuit,
    convert_molecular_data_to_circuit,
    create_drug_circuit,
    create_protein_circuit,
)
from .quantum_executor import (
    BACKEND_CONFIGS,
    BackendConfig,
    BackendType,
    QuantumExecutionError,
    QuantumExecutionResult,
    QuantumExecutor,
    execute_on_backend,
)

__all__ = [
    # Quantum Executor
    "QuantumExecutor",
    "QuantumExecutionResult",
    "BackendType",
    "BackendConfig",
    "BACKEND_CONFIGS",
    "QuantumExecutionError",
    "execute_on_backend",
    # Circuit Builder
    "MolecularCircuitBuilder",
    "MolecularData",
    "CircuitBuilderError",
    "build_molecular_circuit",
    "convert_molecular_data_to_circuit",
    "create_protein_circuit",
    "create_drug_circuit",
]

__version__ = "1.0.0"
