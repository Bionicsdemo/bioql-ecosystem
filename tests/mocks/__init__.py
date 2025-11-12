# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Test Mocks Package
========================

This package provides comprehensive mocks for all external APIs used in the BioQL ecosystem.

Available Mocks:
- IBM Quantum API (Qiskit)
- Modal API
- Stripe API
- RDKit Chemistry Operations
- PDB Protein Structure Fetching

Usage:
    Import mocks from this package and use with pytest fixtures:

    >>> from tests.mocks.api_mocks import MockIBMQuantum, MockStripe
    >>> mock_quantum = MockIBMQuantum()
    >>> result = mock_quantum.mock_job_result()
"""

from .api_mocks import (  # IBM Quantum Mocks; Modal Mocks; Stripe Mocks; RDKit Mocks; PDB Mocks
    MockBackend,
    MockIBMQuantum,
    MockModal,
    MockModalFunction,
    MockModalWorkflow,
    MockMolecule,
    MockPDB,
    MockProteinStructure,
    MockQuantumCircuit,
    MockQuantumJob,
    MockQuantumResult,
    MockRDKit,
    MockStripe,
    MockStripeCharge,
    MockStripeCustomer,
    MockStripeWebhook,
)

# Keep legacy imports for backward compatibility
try:
    from .mock_quantum_backend import MockIBMBackend, MockQuantumBackend
except ImportError:
    MockQuantumBackend = MockBackend
    MockIBMBackend = MockBackend

try:
    from .mock_stripe import MockStripeClient
except ImportError:
    MockStripeClient = MockStripe

try:
    from .mock_database import MockDatabase
except ImportError:
    MockDatabase = None

__all__ = [
    # IBM Quantum
    "MockIBMQuantum",
    "MockQuantumCircuit",
    "MockQuantumJob",
    "MockQuantumResult",
    "MockBackend",
    # Modal
    "MockModal",
    "MockModalFunction",
    "MockModalWorkflow",
    # Stripe
    "MockStripe",
    "MockStripeCustomer",
    "MockStripeCharge",
    "MockStripeWebhook",
    # RDKit
    "MockRDKit",
    "MockMolecule",
    # PDB
    "MockPDB",
    "MockProteinStructure",
    # Legacy
    "MockQuantumBackend",
    "MockIBMBackend",
    "MockStripeClient",
    "MockDatabase",
]

__version__ = "1.0.0"
