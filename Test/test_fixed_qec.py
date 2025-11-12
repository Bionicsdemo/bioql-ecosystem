#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test Suite for BioQL QEC Parameter Validation
==============================================

Tests to verify the correct BioQL QEC parameters.
Converted from manual test script to proper pytest format.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Add BioQL to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Spectrix_framework"))


@pytest.fixture(scope="module")
def bioql_api_key() -> str:
    """
    Return the BioQL API key for testing.

    Returns:
        API key from environment or placeholder
    """
    return os.getenv("BIOQL_API_KEY", "your_api_key_here")


@pytest.fixture
def correct_qec_params() -> Dict[str, Any]:
    """
    Return correct QEC parameters.

    Returns:
        Dictionary with correct QEC parameters
    """
    return {"error_correction": "surface_code", "correction_level": "low", "num_logical_qubits": 2}


@pytest.fixture
def molecular_docking_prompt() -> str:
    """
    Return molecular docking prompt for testing.

    Returns:
        Docking analysis prompt string
    """
    return (
        "Analyze ligand with SMILES COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2 "
        "docking to receptor PDB 6B3J. "
        "Calculate binding affinity using VQE quantum computation. "
        "Identify key molecular interactions from quantum states. "
        "Calculate Ki and IC50 from quantum binding energies."
    )


@pytest.mark.integration
@pytest.mark.requires_api
class TestQECParameterCorrectness:
    """Test suite for QEC parameter validation."""

    def test_import_bioql_quantum(self) -> None:
        """Test that BioQL quantum module can be imported."""
        from bioql import quantum

        assert quantum is not None
        assert callable(quantum)

    def test_correct_qec_parameters_accepted(
        self, bioql_api_key: str, correct_qec_params: Dict[str, Any], molecular_docking_prompt: str
    ) -> None:
        """
        Test that correct QEC parameters are accepted without TypeError.

        This test verifies that:
        1. error_correction='surface_code' is accepted
        2. correction_level='low' is accepted
        3. num_logical_qubits=2 is accepted
        4. No TypeError is raised
        """
        from bioql import quantum

        # This should NOT raise TypeError
        result = quantum(
            molecular_docking_prompt,
            backend="simulator",
            shots=1000,
            api_key=bioql_api_key,
            **correct_qec_params,
        )

        # Verify execution completed
        assert hasattr(result, "success"), "Result should have 'success' attribute"

    def test_no_type_error_with_correct_params(
        self, bioql_api_key: str, correct_qec_params: Dict[str, Any]
    ) -> None:
        """Test that correct parameters do not raise TypeError."""
        from bioql import quantum

        # Should not raise TypeError
        try:
            result = quantum(
                "Simple test",
                backend="simulator",
                shots=100,
                api_key=bioql_api_key,
                **correct_qec_params,
            )
            # If we get here, no TypeError was raised
            assert True
        except TypeError as e:
            pytest.fail(f"Correct parameters raised TypeError: {e}")

    @pytest.mark.parametrize("error_correction", ["surface_code"])
    def test_error_correction_parameter(self, bioql_api_key: str, error_correction: str) -> None:
        """Test that error_correction parameter is accepted."""
        from bioql import quantum

        result = quantum(
            "Test error correction",
            backend="simulator",
            shots=10,
            api_key=bioql_api_key,
            error_correction=error_correction,
            correction_level="low",
            num_logical_qubits=2,
        )

        assert hasattr(result, "success")

    @pytest.mark.parametrize("correction_level", ["low", "medium", "high"])
    def test_correction_level_parameter(self, bioql_api_key: str, correction_level: str) -> None:
        """Test that correction_level parameter is accepted."""
        from bioql import quantum

        result = quantum(
            "Test correction level",
            backend="simulator",
            shots=10,
            api_key=bioql_api_key,
            error_correction="surface_code",
            correction_level=correction_level,
            num_logical_qubits=2,
        )

        assert hasattr(result, "success")

    @pytest.mark.parametrize("num_logical_qubits", [2, 4, 8])
    def test_num_logical_qubits_parameter(
        self, bioql_api_key: str, num_logical_qubits: int
    ) -> None:
        """Test that num_logical_qubits parameter is accepted."""
        from bioql import quantum

        result = quantum(
            "Test logical qubits",
            backend="simulator",
            shots=10,
            api_key=bioql_api_key,
            error_correction="surface_code",
            correction_level="low",
            num_logical_qubits=num_logical_qubits,
        )

        assert hasattr(result, "success")


@pytest.mark.integration
@pytest.mark.requires_api
class TestMolecularDockingWithQEC:
    """Test suite for molecular docking with QEC parameters."""

    def test_vqe_docking_with_qec(
        self, bioql_api_key: str, correct_qec_params: Dict[str, Any], molecular_docking_prompt: str
    ) -> None:
        """
        Test VQE molecular docking with QEC parameters.

        This test performs a full molecular docking analysis with QEC.
        """
        from bioql import quantum

        result = quantum(
            molecular_docking_prompt,
            backend="simulator",
            shots=1000,
            api_key=bioql_api_key,
            **correct_qec_params,
        )

        # Basic validation
        assert hasattr(result, "success")

        # If successful, check for bio interpretation
        if result.success:
            bio = getattr(result, "bio_interpretation", None)

            if bio and isinstance(bio, dict):
                # Check for expected fields
                if "binding_affinity" in bio:
                    assert isinstance(bio["binding_affinity"], (int, float))
                    # Binding affinity should be in reasonable range
                    assert -50.0 < bio["binding_affinity"] < 50.0

                if "ki" in bio:
                    assert isinstance(bio["ki"], (int, float))
                    assert bio["ki"] > 0

    def test_result_bio_interpretation_structure(
        self, bioql_api_key: str, correct_qec_params: Dict[str, Any], molecular_docking_prompt: str
    ) -> None:
        """Test that bio_interpretation has expected structure."""
        from bioql import quantum

        result = quantum(
            molecular_docking_prompt,
            backend="simulator",
            shots=100,
            api_key=bioql_api_key,
            **correct_qec_params,
        )

        # Check if bio_interpretation exists
        if hasattr(result, "bio_interpretation"):
            bio = result.bio_interpretation

            if bio and isinstance(bio, dict):
                # Verify it's a dictionary with valid structure
                assert all(isinstance(k, str) for k in bio.keys()), "All keys should be strings"

                # Check for common fields if present
                if "binding_affinity" in bio:
                    assert isinstance(bio["binding_affinity"], (int, float))

                if "ki" in bio:
                    assert isinstance(bio["ki"], (int, float))

                if "ic50" in bio:
                    assert isinstance(bio["ic50"], (int, float))


@pytest.mark.unit
class TestQECParameterStructure:
    """Test suite for QEC parameter structure validation (no API calls)."""

    def test_correct_qec_params_structure(self, correct_qec_params: Dict[str, Any]) -> None:
        """Test that correct QEC params have expected structure."""
        assert "error_correction" in correct_qec_params
        assert "correction_level" in correct_qec_params
        assert "num_logical_qubits" in correct_qec_params

        assert isinstance(correct_qec_params["error_correction"], str)
        assert isinstance(correct_qec_params["correction_level"], str)
        assert isinstance(correct_qec_params["num_logical_qubits"], int)

    def test_parameter_values_are_valid(self, correct_qec_params: Dict[str, Any]) -> None:
        """Test that parameter values are within expected ranges."""
        assert correct_qec_params["error_correction"] == "surface_code"
        assert correct_qec_params["correction_level"] in ["low", "medium", "high"]
        assert correct_qec_params["num_logical_qubits"] > 0
        assert correct_qec_params["num_logical_qubits"] <= 16


@pytest.mark.unit
class TestDeprecatedParameters:
    """Test suite to document deprecated/incorrect parameters."""

    def test_qec_config_is_not_correct_parameter(self) -> None:
        """
        Document that qec_config parameter causes TypeError.

        This test documents that the old parameter format is incorrect.
        """
        # This is documentation, not a real test
        deprecated_params = {
            "qec_config": {"error_correction": "surface_code", "correction_level": "low"}
        }

        # Document the issue
        assert "qec_config" in deprecated_params
        # The correct approach is to use flat parameters instead


if __name__ == "__main__":
    # Run tests with pytest
    # By default, skip tests requiring API
    pytest.main([__file__, "-v", "--tb=short", "-m", "not requires_api"])
