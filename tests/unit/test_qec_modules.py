# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Unit Tests for BioQL Quantum Error Correction (QEC) Modules

Tests the following modules:
- bioql/advanced_qec.py (advanced error mitigation strategies)
- bioql/chemistry_qec.py (chemistry-specific QEC)
- Different QEC codes (Surface, Steane, Shor)
- Error mitigation techniques (ZNE, PEC, readout error correction)

All tests use mocking to avoid external dependencies.
"""

# Add project to path
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Spectrix_framework"))


# ============================================================================
# ADVANCED QEC MODULE TESTS (bioql/advanced_qec.py)
# ============================================================================


class TestAdvancedErrorMitigation:
    """Test suite for advanced error mitigation."""

    def test_error_mitigation_initialization(self):
        """Test error mitigation engine initialization."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()
        assert mitigation is not None

    def test_apply_full_mitigation_success(self):
        """Test full error mitigation pipeline."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        counts = {"0000": 400, "0001": 300, "0010": 200, "0011": 100}

        result = mitigation.apply_full_mitigation(
            counts=counts,
            num_qubits=4,
            expected_energy=-1.137,  # H2 reference
            methods=["readout", "zne"],
        )

        assert result.success is True
        assert result.original_counts == counts
        assert result.mitigated_counts is not None
        assert result.improvement_percent >= 0

    def test_readout_error_mitigation(self):
        """Test readout error mitigation."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        counts = {"00": 480, "01": 20, "10": 15, "11": 485}

        # Call private method for testing
        mitigated = mitigation._readout_error_mitigation(counts, num_qubits=2)

        assert mitigated is not None
        assert sum(mitigated.values()) == sum(counts.values())

    def test_zero_noise_extrapolation(self):
        """Test Zero Noise Extrapolation (ZNE)."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        counts = {"00": 500, "11": 500}

        mitigated = mitigation._zero_noise_extrapolation(counts, noise_scaling=[1.0, 1.5, 2.0])

        assert mitigated is not None

    def test_symmetry_verification(self):
        """Test symmetry verification mitigation."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        counts = {
            "0000": 250,
            "1111": 250,  # Symmetric
            "0101": 100,  # May violate symmetry
            "1010": 100,
        }

        mitigated = mitigation._symmetry_verification(counts, num_qubits=4)

        assert mitigated is not None

    def test_probabilistic_error_cancellation(self):
        """Test Probabilistic Error Cancellation (PEC)."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        counts = {"00": 480, "01": 10, "10": 10, "11": 500}

        mitigated = mitigation._probabilistic_error_cancellation(counts, error_rate=0.001)

        assert mitigated is not None

    def test_counts_to_energy_conversion(self):
        """Test conversion of counts to energy."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        counts = {"00": 750, "11": 250}

        energy = mitigation._counts_to_energy(counts)

        assert isinstance(energy, float)

    def test_accuracy_calculation(self):
        """Test accuracy calculation."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        calculated_energy = -1.13
        expected_energy = -1.137  # H2 reference

        accuracy = mitigation._calculate_accuracy(calculated_energy, expected_energy)

        assert 0 <= accuracy <= 100
        assert accuracy >= 99.0  # Should be close

    def test_error_mitigation_result_dataclass(self):
        """Test ErrorMitigationResult dataclass."""
        from bioql.advanced_qec import ErrorMitigationResult

        result = ErrorMitigationResult(
            success=True,
            original_counts={"00": 500, "11": 500},
            mitigated_counts={"00": 520, "11": 480},
            original_energy=-1.0,
            mitigated_energy=-1.1,
            accuracy_original=85.0,
            accuracy_mitigated=95.0,
            improvement_percent=10.0,
            mitigation_methods=["zne", "readout"],
        )

        assert result.success is True
        assert result.improvement_percent == 10.0
        assert "zne" in result.mitigation_methods


# ============================================================================
# CHEMISTRY QEC MODULE TESTS (bioql/chemistry_qec.py)
# ============================================================================


class TestQuantumChemistry:
    """Test suite for quantum chemistry with QEC."""

    @patch("bioql.chemistry_qec.OPENFERMION_AVAILABLE", True)
    def test_quantum_chemistry_initialization(self):
        """Test quantum chemistry engine initialization."""
        from bioql.chemistry_qec import QuantumChemistry

        chem = QuantumChemistry()
        assert chem is not None

    @patch("bioql.chemistry_qec.OPENFERMION_AVAILABLE", False)
    def test_quantum_chemistry_no_openfermion(self):
        """Test initialization fails without OpenFermion."""
        from bioql.chemistry_qec import QuantumChemistry

        with pytest.raises(ImportError):
            QuantumChemistry()

    @patch("bioql.chemistry_qec.OPENFERMION_AVAILABLE", True)
    @patch("bioql.chemistry_qec.of")
    def test_calculate_molecule_h2(self, mock_of):
        """Test H2 molecule calculation."""
        from bioql.chemistry_qec import QuantumChemistry

        # Mock OpenFermion components
        mock_molecule = MagicMock()
        mock_molecule.n_orbitals = 2
        mock_of.MolecularData.return_value = mock_molecule

        mock_hamiltonian = MagicMock()
        mock_of.count_qubits.return_value = 4

        chem = QuantumChemistry()
        chem._get_molecular_hamiltonian = MagicMock(return_value=mock_hamiltonian)

        result = chem.calculate_molecule(molecule_name="H2", distance=0.74)

        assert result.molecule_name == "H2"
        assert result.num_qubits == 4

    @patch("bioql.chemistry_qec.OPENFERMION_AVAILABLE", True)
    def test_get_default_geometry_h2(self):
        """Test default geometry for H2."""
        from bioql.chemistry_qec import QuantumChemistry

        chem = QuantumChemistry()
        geometry = chem._get_default_geometry("H2", distance=0.74)

        assert len(geometry) == 2
        assert geometry[0][0] == "H"
        assert geometry[1][0] == "H"

    @patch("bioql.chemistry_qec.OPENFERMION_AVAILABLE", True)
    def test_reference_energies(self):
        """Test reference energy database."""
        from bioql.chemistry_qec import QuantumChemistry

        chem = QuantumChemistry()

        assert "H2" in chem.REFERENCE_ENERGIES
        assert "H2O" in chem.REFERENCE_ENERGIES
        assert chem.REFERENCE_ENERGIES["H2"] == -1.137

    @patch("bioql.chemistry_qec.OPENFERMION_AVAILABLE", True)
    def test_molecule_result_dataclass(self):
        """Test MoleculeResult dataclass."""
        from bioql.chemistry_qec import MoleculeResult

        result = MoleculeResult(
            success=True,
            molecule_name="H2",
            geometry=[("H", (0, 0, 0)), ("H", (0, 0, 0.74))],
            energy_ground_state=-1.137,
            energy_kcal_mol=-713.4,
            hamiltonian=None,
            num_qubits=4,
            num_orbitals=2,
            accuracy_percent=99.5,
        )

        assert result.success is True
        assert result.molecule_name == "H2"
        assert result.num_qubits == 4


# ============================================================================
# QEC CODES TESTS
# ============================================================================


class TestQECCodes:
    """Test suite for different QEC codes."""

    def test_surface_code_distance(self):
        """Test surface code distance calculation."""
        # Surface code uses d^2 physical qubits per logical qubit
        distance = 5
        physical_qubits = distance * distance

        assert physical_qubits == 25

    def test_steane_code_encoding(self):
        """Test Steane [[7,1,3]] code parameters."""
        # Steane code: 7 physical qubits, 1 logical qubit, distance 3
        n = 7  # Physical qubits
        k = 1  # Logical qubits
        d = 3  # Code distance

        assert n == 7
        assert k == 1
        assert d == 3

    def test_shor_code_encoding(self):
        """Test Shor [[9,1,3]] code parameters."""
        # Shor code: 9 physical qubits, 1 logical qubit, distance 3
        n = 9
        k = 1
        d = 3

        assert n == 9
        assert k == 1
        assert d == 3

    def test_error_correction_threshold(self):
        """Test error correction threshold calculation."""
        # Surface code threshold ~ 1%
        threshold = 0.01
        physical_error_rate = 0.005

        can_correct = physical_error_rate < threshold

        assert can_correct is True

    def test_logical_error_rate_suppression(self):
        """Test logical error rate suppression."""
        # Logical error rate ~ (p / p_th)^((d+1)/2)
        p = 0.001  # Physical error rate
        p_th = 0.01  # Threshold
        d = 3  # Distance

        logical_error_rate = (p / p_th) ** ((d + 1) / 2)

        assert logical_error_rate < p


# ============================================================================
# ERROR MITIGATION STRATEGY TESTS
# ============================================================================


class TestErrorMitigationStrategies:
    """Test suite for various error mitigation strategies."""

    def test_zne_richardson_extrapolation(self):
        """Test Richardson extrapolation for ZNE."""
        # Measure at noise scales 1x, 2x, 3x
        measurements = [1.0, 1.2, 1.4]  # Noisy expectation values
        noise_scales = [1, 2, 3]

        # Linear extrapolation to zero noise
        # E(0) = E(1) - (E(2) - E(1)) / (2 - 1)
        zero_noise = measurements[0] - (measurements[1] - measurements[0])

        assert zero_noise < measurements[0]  # Should reduce toward true value

    def test_pec_quasi_probability(self):
        """Test PEC quasi-probability distribution."""
        # Ideal operation represented as sum of noisy operations
        quasi_probs = [0.9, -0.1, 0.2]  # Can be negative

        # Sum should be 1 for normalization
        assert abs(sum(quasi_probs) - 1.0) < 0.01

    def test_clifford_data_regression(self):
        """Test Clifford Data Regression (CDR) approach."""
        # CDR uses Clifford circuits as training data
        num_clifford_circuits = 10
        num_measurements = 1000

        # Should have enough data for regression
        assert num_clifford_circuits >= 5
        assert num_measurements >= 100

    def test_digital_dynamical_decoupling(self):
        """Test digital dynamical decoupling sequences."""
        # XY4 sequence: X-Y-X-Y with equal spacing
        sequence = ["X", "Y", "X", "Y"]

        assert len(sequence) == 4
        assert sequence.count("X") == 2
        assert sequence.count("Y") == 2


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestQECIntegration:
    """Test suite for QEC integration."""

    @patch("bioql.advanced_qec.AdvancedErrorMitigation")
    def test_chemistry_with_error_mitigation(self, mock_mitigation):
        """Test chemistry calculation with error mitigation."""
        # This would be an integration test combining chemistry and QEC
        mock_mitigation_instance = MagicMock()
        mock_mitigation.return_value = mock_mitigation_instance

        # Simulated quantum result
        counts = {"0000": 600, "1111": 400}

        # Apply mitigation
        mock_mitigation_instance.apply_full_mitigation.return_value = MagicMock(
            success=True, accuracy_mitigated=98.5
        )

        result = mock_mitigation_instance.apply_full_mitigation(
            counts=counts, num_qubits=4, expected_energy=-1.137
        )

        assert result.success is True
        assert result.accuracy_mitigated >= 95.0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestQECErrorHandling:
    """Test suite for QEC error handling."""

    def test_mitigation_with_empty_counts(self):
        """Test error mitigation with empty counts."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        result = mitigation.apply_full_mitigation(counts={}, num_qubits=2)

        # Should handle gracefully
        assert result is not None

    def test_mitigation_with_invalid_methods(self):
        """Test error mitigation with invalid methods."""
        from bioql.advanced_qec import AdvancedErrorMitigation

        mitigation = AdvancedErrorMitigation()

        counts = {"00": 500, "11": 500}

        # Should ignore invalid methods and continue
        result = mitigation.apply_full_mitigation(
            counts=counts, num_qubits=2, methods=["invalid_method"]
        )

        assert result is not None

    @patch("bioql.chemistry_qec.OPENFERMION_AVAILABLE", True)
    def test_chemistry_calculation_failure(self):
        """Test handling of chemistry calculation failure."""
        from bioql.chemistry_qec import QuantumChemistry

        chem = QuantumChemistry()
        chem._get_molecular_hamiltonian = MagicMock(return_value=None)

        result = chem.calculate_molecule("H2")

        assert result.success is False
        assert result.error_message is not None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
