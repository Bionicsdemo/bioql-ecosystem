# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Ecosystem - Pytest Configuration
======================================

This file contains shared fixtures for all tests, including comprehensive
mocks for external APIs (IBM Quantum, Modal, Stripe, RDKit, PDB).
"""

import os

# Add project root to path
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all mocks - temporarily disabled until tests.mocks module is created
# from tests.mocks.api_mocks import (
#     MockIBMQuantum,
#     MockQuantumCircuit,
#     MockQuantumJob,
#     MockQuantumResult,
#     MockBackend,
#     MockModal,
#     MockModalFunction,
#     MockModalWorkflow,
#     MockStripe,
#     MockStripeCustomer,
#     MockStripeCharge,
#     MockStripeWebhook,
#     MockRDKit,
#     MockMolecule,
#     MockPDB,
#     MockProteinStructure,
#     create_quantum_mock_patches,
#     create_modal_mock_patches,
#     create_stripe_mock_patches,
#     create_rdkit_mock_patches,
#     create_pdb_mock_patches,
#     create_all_mock_patches,
# )


# ============================================================================
# Basic Configuration Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_api_key():
    """Provide test API key."""
    return os.getenv("BIOQL_API_KEY", "bioql_test_key")


@pytest.fixture(scope="session")
def test_backend():
    """Default test backend."""
    return "simulator"


@pytest.fixture
def test_data_dir(project_root):
    """Return test data directory."""
    data_dir = project_root / "tests" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ============================================================================
# IBM Quantum / Qiskit Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_quantum_result():
    """
    Provide a mock quantum computation result.

    Returns:
        dict: Mock result with counts and metadata
    """
    return {"counts": {"00": 500, "11": 500}, "shots": 1000, "backend": "aer_simulator"}


# ============================================================================
# Disabled Mock Fixtures (until tests.mocks module is created)
# ============================================================================
# All advanced mock fixtures have been temporarily disabled.
# Basic mock_quantum_result is available above.


# Add more shared fixtures as needed
