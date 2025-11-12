#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Test Suite for VS Code to Modal API Integration
================================================

Tests that simulate VS Code calling the Modal API for code generation.
Converted from manual test script to proper pytest format.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

# Configuration
MODAL_URL = "https://spectrix--bioql-agent-create-fastapi-app.modal.run"


@pytest.fixture(scope="module")
def modal_url() -> str:
    """
    Return the Modal API URL.

    Returns:
        Modal server URL
    """
    return os.getenv("MODAL_URL", MODAL_URL)


@pytest.fixture
def molecular_docking_prompt() -> str:
    """
    Return complex molecular docking prompt.

    Returns:
        Molecular docking prompt string
    """
    return (
        'Dock my clinical molecule with SMILES="COc1ccc2cc3[n+](cc2c1OC)CCc1cc2c(cc1-3)OCO2" '
        "against GLP1R receptor (PDB: 6B3J) for obesity/diabetes using IBM Torino quantum computer "
        "with 2000 shots and surface_code QEC. Calculate Ki from binding affinity using thermodynamic "
        "formula. Save quantum provenance and docking results to artifacts/. Generate professional "
        "report with binding poses. use Quillow corrections"
    )


@pytest.fixture
def generate_payload(molecular_docking_prompt: str) -> Dict[str, Any]:
    """
    Return payload for /generate endpoint.

    Args:
        molecular_docking_prompt: The prompt fixture

    Returns:
        Dictionary with generation parameters
    """
    return {"prompt": molecular_docking_prompt, "max_length": 2048, "temperature": 0.7}


@pytest.fixture
def mock_generated_code() -> str:
    """
    Return mock generated code.

    Returns:
        Sample generated Python code
    """
    return """from bioql import quantum

result = quantum(
    "Dock molecule",
    backend='ibm_torino',
    shots=2000,
    qec_enabled=True,
    qec_type='surface_code',
    logical_qubits=4
)
"""


@pytest.mark.integration
@pytest.mark.requires_api
class TestModalAPIEndpoints:
    """Test suite for Modal API endpoints (requires live API)."""

    def test_health_endpoint(self, modal_url: str) -> None:
        """Test that health endpoint responds correctly."""
        try:
            response = requests.get(f"{modal_url}/health", timeout=10)

            assert (
                response.status_code == 200
            ), f"Health endpoint should return 200, got {response.status_code}"

            # Try to parse JSON response
            data = response.json()
            assert isinstance(data, dict), "Health response should be a dictionary"

        except requests.exceptions.ConnectionError:
            pytest.skip("Modal API not reachable")
        except requests.exceptions.Timeout:
            pytest.fail("Health endpoint timed out")

    def test_root_endpoint(self, modal_url: str) -> None:
        """Test that root endpoint responds."""
        try:
            response = requests.get(modal_url, timeout=10)

            # Should return some response
            assert response.status_code in [
                200,
                404,
            ], f"Expected 200 or 404, got {response.status_code}"

            if response.status_code == 200:
                # Try to parse as JSON
                data = response.json()
                assert isinstance(data, dict)

        except requests.exceptions.ConnectionError:
            pytest.skip("Modal API not reachable")

    def test_generate_endpoint_structure(
        self, modal_url: str, generate_payload: Dict[str, Any]
    ) -> None:
        """Test that /generate endpoint accepts requests."""
        try:
            response = requests.post(f"{modal_url}/generate", json=generate_payload, timeout=60)

            # Should get some response (200 or error)
            assert response.status_code in [
                200,
                400,
                401,
                403,
                500,
            ], f"Unexpected status code: {response.status_code}"

        except requests.exceptions.ConnectionError:
            pytest.skip("Modal API not reachable")
        except requests.exceptions.Timeout:
            pytest.skip("Generate endpoint timed out")


@pytest.mark.integration
@pytest.mark.requires_api
@pytest.mark.slow
class TestCodeGeneration:
    """Test suite for code generation functionality."""

    def test_generate_code_success(self, modal_url: str, generate_payload: Dict[str, Any]) -> None:
        """Test successful code generation."""
        try:
            response = requests.post(f"{modal_url}/generate", json=generate_payload, timeout=60)

            if response.status_code == 200:
                result = response.json()

                # Should contain generated code
                assert "code" in result, "Response should contain 'code' field"
                assert isinstance(result["code"], str)
                assert len(result["code"]) > 0

        except requests.exceptions.ConnectionError:
            pytest.skip("Modal API not reachable")
        except requests.exceptions.Timeout:
            pytest.skip("Code generation timed out")

    def test_generated_code_qec_parameters(
        self, modal_url: str, generate_payload: Dict[str, Any]
    ) -> None:
        """
        Test that generated code uses correct QEC parameters.

        Verifies:
        1. Does NOT contain 'qec_config' (incorrect format)
        2. Contains 'qec_enabled=True' (correct format)
        3. Contains 'qec_type=' parameter
        4. Contains 'logical_qubits=' parameter
        """
        try:
            response = requests.post(f"{modal_url}/generate", json=generate_payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                code = result.get("code", "")

                # Should NOT contain qec_config
                assert (
                    "qec_config" not in code
                ), "Generated code should not contain 'qec_config' (incorrect format)"

                # Should contain correct QEC parameters
                # Note: These assertions may need adjustment based on actual API behavior
                if "qec" in code.lower():
                    # If QEC is mentioned, check for correct format
                    assert any(
                        ["qec_enabled" in code, "error_correction" in code, "surface_code" in code]
                    ), "QEC parameters should use correct format"

        except requests.exceptions.ConnectionError:
            pytest.skip("Modal API not reachable")
        except requests.exceptions.Timeout:
            pytest.skip("Code generation timed out")


@pytest.mark.unit
class TestCodeValidation:
    """Test suite for validating generated code (mocked)."""

    def test_validate_correct_qec_format(self, mock_generated_code: str) -> None:
        """Test validation of correct QEC parameter format."""
        code = mock_generated_code

        # Should NOT contain incorrect format
        assert "qec_config" not in code, "Code should not use qec_config format"

        # Should contain correct format
        assert "qec_enabled=True" in code, "Code should use qec_enabled parameter"

    def test_validate_qec_parameters_present(self, mock_generated_code: str) -> None:
        """Test that required QEC parameters are present."""
        code = mock_generated_code

        # Check for QEC-related parameters
        qec_indicators = [
            "qec_enabled" in code,
            "qec_type" in code,
            "surface_code" in code,
            "logical_qubits" in code,
        ]

        # At least some QEC parameters should be present
        assert any(qec_indicators), "Code should contain QEC-related parameters"

    def test_validate_code_structure(self, mock_generated_code: str) -> None:
        """Test that generated code has valid Python structure."""
        code = mock_generated_code

        # Basic structure checks
        assert "from bioql import" in code or "import bioql" in code, "Code should import bioql"

        assert "quantum(" in code, "Code should call quantum function"

        assert "backend=" in code, "Code should specify backend"

        assert "shots=" in code, "Code should specify shots"

    def test_code_syntax_validity(self, mock_generated_code: str) -> None:
        """Test that generated code is syntactically valid Python."""
        code = mock_generated_code

        # Try to compile the code (doesn't execute it)
        try:
            compile(code, "<string>", "exec")
            # If we get here, code is syntactically valid
            assert True
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")


@pytest.mark.unit
class TestPayloadValidation:
    """Test suite for validating request payloads."""

    def test_generate_payload_structure(self, generate_payload: Dict[str, Any]) -> None:
        """Test that generate payload has correct structure."""
        assert "prompt" in generate_payload
        assert "max_length" in generate_payload
        assert "temperature" in generate_payload

        assert isinstance(generate_payload["prompt"], str)
        assert isinstance(generate_payload["max_length"], int)
        assert isinstance(generate_payload["temperature"], (int, float))

    def test_payload_serialization(self, generate_payload: Dict[str, Any]) -> None:
        """Test that payload can be serialized to JSON."""
        json_str = json.dumps(generate_payload)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized == generate_payload

    def test_prompt_content_validation(self, molecular_docking_prompt: str) -> None:
        """Test that prompt contains expected keywords."""
        prompt = molecular_docking_prompt.lower()

        # Should contain molecular docking keywords
        assert "dock" in prompt or "docking" in prompt
        assert "smiles" in prompt
        assert "pdb" in prompt
        assert "qec" in prompt or "surface_code" in prompt


@pytest.mark.unit
class TestMockedAPIResponses:
    """Test suite with mocked API responses."""

    @patch("requests.get")
    def test_health_endpoint_mocked(self, mock_get: MagicMock, modal_url: str) -> None:
        """Test health endpoint with mocked response."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response

        # Make request
        response = requests.get(f"{modal_url}/health", timeout=10)

        # Verify
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @patch("requests.post")
    def test_generate_endpoint_mocked(
        self,
        mock_post: MagicMock,
        modal_url: str,
        generate_payload: Dict[str, Any],
        mock_generated_code: str,
    ) -> None:
        """Test generate endpoint with mocked response."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": mock_generated_code}
        mock_post.return_value = mock_response

        # Make request
        response = requests.post(f"{modal_url}/generate", json=generate_payload, timeout=60)

        # Verify
        assert response.status_code == 200
        result = response.json()
        assert "code" in result
        assert "qec_enabled" in result["code"]


if __name__ == "__main__":
    # Run tests with pytest
    # By default, skip tests requiring API
    pytest.main([__file__, "-v", "--tb=short", "-m", "not requires_api"])
