# BioQL Ecosystem - Pytest Configuration
# This file contains shared fixtures for all tests

import pytest
import os
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory"""
    return Path(__file__).parent.parent

@pytest.fixture(scope="session")
def test_api_key():
    """Provide test API key"""
    return os.getenv("BIOQL_API_KEY", "bioql_test_key")

@pytest.fixture(scope="session")
def test_backend():
    """Default test backend"""
    return "simulator"

@pytest.fixture
def mock_quantum_result():
    """Mock quantum computation result"""
    return {
        "counts": {"00": 500, "11": 500},
        "shots": 1000,
        "backend": "simulator"
    }

# Add more shared fixtures as needed
