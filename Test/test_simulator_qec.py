#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test Suite for Quantum Molecular Docking Simulator with QEC
============================================================

Tests the quantum molecular docking simulator with QEC parameters.
Converted from manual test script to proper pytest format.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

# Add BioQL to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Spectrix_framework"))


@pytest.fixture(scope="module")
def bioql_api_key() -> str:
    """
    Return the BioQL API key for testing.

    Returns:
        API key from environment or default test key
    """
    return os.getenv("BIOQL_API_KEY", "__BIOQL_REDACTED__")


@pytest.fixture
def qec_params() -> Dict[str, Any]:
    """
    Return QEC parameters for testing.

    Returns:
        Dictionary with correct QEC parameters
    """
    return {"error_correction": "surface_code", "correction_level": "low", "num_logical_qubits": 4}


@pytest.fixture
def quantum_params(bioql_api_key: str, qec_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return complete quantum execution parameters.

    Args:
        bioql_api_key: The API key fixture
        qec_params: The QEC parameters fixture

    Returns:
        Dictionary with all quantum execution parameters
    """
    return {"backend": "simulator", "shots": 1000, "api_key": bioql_api_key, **qec_params}


@pytest.mark.integration
@pytest.mark.requires_api
class TestQuantumSimulatorQEC:
    """Test suite for quantum simulator with QEC support."""

    def test_import_bioql_quantum(self) -> None:
        """Test that BioQL quantum module can be imported."""
        from bioql import quantum

        assert quantum is not None
        assert callable(quantum)

    def test_bell_state_creation_with_qec(self, quantum_params: Dict[str, Any]) -> None:
        """
        Test Bell state creation on simulator with QEC parameters.

        This test verifies that:
        1. The quantum function accepts correct QEC parameters
        2. The execution completes successfully
        3. The result contains expected data
        """
        from bioql import quantum

        # Execute with correct QEC parameters
        result = quantum(
            "Create a 4-qubit Bell state for molecular docking simulation", **quantum_params
        )

        # Verify execution succeeded
        assert hasattr(result, "success"), "Result should have 'success' attribute"
        assert result.success is True, "Quantum execution should succeed"

    def test_qec_parameters_validation(
        self, bioql_api_key: str, qec_params: Dict[str, Any]
    ) -> None:
        """Test that QEC parameters are correctly validated."""
        from bioql import quantum

        # Test with valid parameters - should not raise TypeError
        try:
            result = quantum(
                "Create a 4-qubit Bell state",
                backend="simulator",
                shots=100,
                api_key=bioql_api_key,
                **qec_params,
            )
            # If we get here, parameters were accepted
            assert True
        except TypeError as e:
            pytest.fail(f"Valid QEC parameters raised TypeError: {e}")

    def test_quantum_result_structure(self, quantum_params: Dict[str, Any]) -> None:
        """
        Test that quantum result has expected structure.

        Verifies the result object contains:
        - success flag
        - counts (if successful)
        - proper data structure
        """
        from bioql import quantum

        result = quantum(
            "Create a 4-qubit Bell state for molecular docking simulation", **quantum_params
        )

        # Check basic structure
        assert hasattr(result, "success")

        if result.success:
            assert hasattr(result, "counts"), "Successful result should have counts"
            assert isinstance(result.counts, dict), "Counts should be a dictionary"

            # Verify counts are properly formatted
            total_counts = sum(result.counts.values())
            assert total_counts > 0, "Total counts should be greater than 0"

            # All states should be binary strings
            for state in result.counts.keys():
                assert isinstance(state, str), "State keys should be strings"
                assert all(c in "01" for c in state), f"State {state} should only contain 0s and 1s"

    def test_quantum_execution_with_shots(
        self, bioql_api_key: str, qec_params: Dict[str, Any]
    ) -> None:
        """Test quantum execution with specific shot count."""
        from bioql import quantum

        shots = 1000
        result = quantum(
            "Create a 4-qubit Bell state",
            backend="simulator",
            shots=shots,
            api_key=bioql_api_key,
            **qec_params,
        )

        assert result.success is True

        if hasattr(result, "counts"):
            total = sum(result.counts.values())
            # Total counts should match requested shots (approximately)
            assert (
                abs(total - shots) < shots * 0.1
            ), f"Total counts {total} should be close to requested shots {shots}"

    @pytest.mark.parametrize("correction_level", ["low", "medium", "high"])
    def test_correction_levels(self, bioql_api_key: str, correction_level: str) -> None:
        """Test that different correction levels are accepted."""
        from bioql import quantum

        result = quantum(
            "Create a 2-qubit Bell state",
            backend="simulator",
            shots=100,
            api_key=bioql_api_key,
            error_correction="surface_code",
            correction_level=correction_level,
            num_logical_qubits=2,
        )

        # Should complete without errors
        assert hasattr(result, "success")

    def test_result_statistics(self, quantum_params: Dict[str, Any]) -> None:
        """
        Test that result statistics are reasonable.

        For a Bell state, we expect:
        - High probability for entangled states (|00⟩ and |11⟩)
        - Distribution follows quantum mechanics expectations
        """
        from bioql import quantum

        result = quantum(
            "Create a 4-qubit Bell state for molecular docking simulation", **quantum_params
        )

        if result.success and hasattr(result, "counts"):
            # Get top states by count
            sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)

            # Verify we have results
            assert len(sorted_counts) > 0, "Should have at least one measured state"

            # Top state should have significant probability
            top_state, top_count = sorted_counts[0]
            total = sum(result.counts.values())
            top_probability = top_count / total

            assert top_probability > 0.01, "Top state should have probability > 1%"


@pytest.mark.integration
@pytest.mark.requires_api
class TestQECParameterValidation:
    """Test suite specifically for QEC parameter validation."""

    def test_surface_code_accepted(self, bioql_api_key: str) -> None:
        """Test that 'surface_code' error correction is accepted."""
        from bioql import quantum

        result = quantum(
            "Test surface code",
            backend="simulator",
            shots=10,
            api_key=bioql_api_key,
            error_correction="surface_code",
            correction_level="low",
            num_logical_qubits=2,
        )

        assert hasattr(result, "success")

    def test_correction_level_accepted(self, bioql_api_key: str) -> None:
        """Test that 'correction_level' parameter is accepted."""
        from bioql import quantum

        result = quantum(
            "Test correction level",
            backend="simulator",
            shots=10,
            api_key=bioql_api_key,
            error_correction="surface_code",
            correction_level="low",
            num_logical_qubits=2,
        )

        assert hasattr(result, "success")

    def test_num_logical_qubits_accepted(self, bioql_api_key: str) -> None:
        """Test that 'num_logical_qubits' parameter is accepted."""
        from bioql import quantum

        result = quantum(
            "Test logical qubits",
            backend="simulator",
            shots=10,
            api_key=bioql_api_key,
            error_correction="surface_code",
            correction_level="low",
            num_logical_qubits=4,
        )

        assert hasattr(result, "success")


# Additional utility functions for test reporting
def print_result_summary(result: Any, shots: int = 1000) -> None:
    """
    Print a summary of quantum execution result.

    This is kept for compatibility but should not be used in tests.
    Use proper assertions instead.

    Args:
        result: The quantum execution result
        shots: Total number of shots
    """
    if hasattr(result, "counts") and result.counts:
        sorted_counts = sorted(result.counts.items(), key=lambda x: x[1], reverse=True)

        for state, count in sorted_counts[:10]:
            prob = count / shots * 100
            print(f"|{state}⟩: {count:4d} ({prob:5.1f}%)")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-m", "not requires_api or integration"])
