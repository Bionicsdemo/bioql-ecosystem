# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

# BioQL Ecosystem - Example Unit Test
# This is a template test file

import pytest


@pytest.mark.unit
def test_example():
    """Example test to verify pytest is working"""
    assert 1 + 1 == 2


@pytest.mark.unit
def test_mock_quantum_result(mock_quantum_result):
    """Test using a fixture"""
    assert mock_quantum_result["shots"] == 1000
    assert "counts" in mock_quantum_result
    assert sum(mock_quantum_result["counts"].values()) == 1000


# Add more unit tests here
